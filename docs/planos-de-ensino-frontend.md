# Planos de ensino — S6-F01

Este guia registra a integração da Sprint 6. Para a evolução planejada, consulte os [contratos da Release 2](atualizacoes.md#contratos-da-release-2) e a decisão sobre tratamento de PDFs no [ADR-003](arquitetura/adrs/adr-003-minimizar-dados-de-planos.md).

A rota `/plano-de-ensino` oferece envio autenticado, acompanhamento por ID e histórico paginado de planos particulares. Usa a sessão Supabase pelo cliente compartilhado da API, sem chave de serviço nem URLs de arquivos. Visitantes recebem uma chamada para login e não fazem consultas privadas.

## Demonstração e envios reais

A página abre uma demonstração interativa com catálogo ilustrativo. Em **Catálogo de turmas**, escolha o período atual ou o seguinte e busque por matéria, código, professor ou número de turma. A demonstração usa semestres civis de Brasília até haver uma fonte de períodos letivos. **Minhas turmas** lista os vínculos autodeclarados e abre o plano de exemplo ou o envio simulado da oferta escolhida. O envio simulado exige que a oferta seja seguida e esteja disponível, inclusive quando vier do último catálogo válido. Deixar de seguir mantém as avaliações já incluídas na prévia da agenda.

Na demonstração, visitantes mantêm os vínculos apenas durante a visita. Com login, só os IDs dos vínculos de exemplo são salvos no navegador, separados por conta; planos e prévia não são persistidos. A demonstração não envia arquivos e não consulta o Followw. **Catálogo e planos reais** usa a API autenticada do Agenda UnB, com vínculos persistidos no servidor, catálogo sincronizado e oferta obrigatória nos envios. Consulte o [guia de integração #70/#71](arquitetura/catalogo-de-turmas.md).

### Evidências locais da #71

| Cenário | Resultado no frontend |
| --- | --- |
| Buscar e distinguir ofertas | Passou: busca sem acentos por matéria, professor, código e número da turma, com homônimas e períodos distintos. |
| Seguir, recarregar e abrir o plano | Passou na demonstração: o vínculo permanece na mesma conta; a oferta do período correto abre o plano ou o envio simulado. |
| Deixar de seguir | Passou na demonstração: o vínculo é removido, e as avaliações já incluídas continuam na prévia. |
| Vazio, falha e cache desatualizado | Passou com fixtures: nova tentativa, data do cache, caminho manual e bloqueio do envio para oferta indisponível. |
| Teclado e layout (RNF07–RNF09) | Passou no Chrome a 360, 768 e 1365 px, nos temas claro e escuro. Foco, campos e cores principais do catálogo verificados; sem auditoria WCAG completa. |

Revisão local: Codex, com as skills `project-standards`, `impeccable` e `code-review`. O catálogo demonstrativo não usa credenciais nem chama endpoints do Followw. Na integração atual, o contrato de envio exige oferta disponível; a revisão particular mantém suas permissões. PR, implantação, revisão humana e homologação de ponta a ponta continuam pendentes.

## Escopo e dependências reais

O protótipo fornecido orientou a composição (envio, orientações laterais, lista por disciplina), não seus dados ou funcionalidades futuras. O limite adotado é **10 MB / 10 páginas**, não os 20 MB ilustrativos do protótipo. A integração atual inclui catálogo e confirmação de candidatos particulares; matrícula oficial continua fora do escopo. O painel administrativo não foi alterado.

No backend deste checkout, PDF e texto exigem `offering_id`. Disciplina, turma, ano e semestre são derivados da oferta disponível. O texto é preparado localmente, revisado e autorizado antes da IA; planos particulares podem ser revisados e confirmados na agenda pelo fluxo existente.

## Contratos consumidos

Base: `VITE_API_URL` (padrão `http://127.0.0.1:8000/api/v1`). Todas as operações usam `Authorization: Bearer <access_token>`.

### Upload vinculado à oferta

`POST /syllabus/upload`, `multipart/form-data`:

| Campo | Tipo | Uso |
| --- | --- | --- |
| `file` | PDF | Obrigatório, até 10 × 1024 × 1024 bytes |
| `offering_id` | UUID | Obrigatório; oferta disponível no catálogo |

Resposta esperada: 202 com `id`, `status`, `fileName`, `createdAt` e os metadados já presentes no schema de upload. O navegador define o boundary multipart; não definir `Content-Type: application/json` para esse corpo.

O frontend valida extensão, MIME (aceita MIME vazio quando o navegador não informa), tamanho e arquivo vazio. Assinatura, integridade, senha, texto selecionável e contagem de páginas são validados no servidor. Erros de validação preservam os campos e o arquivo selecionado. O envio tem limite de espera de 90 segundos e trava síncrona contra cliques duplicados; não há repetição automática de POST. Em falha de rede/timeout, orienta consultar o histórico antes de reenviar, pois o servidor pode ter recebido o arquivo.

### Listagem implementada

`GET /syllabus?limit=10&offset=0`:

```json
{
  "items": [{
    "id": "d79eeb53-aed8-4369-936b-156e01cc455c",
    "disciplina": "Métodos de Desenvolvimento de Software",
    "semestre": 2,
    "ano": 2026,
    "fileName": "plano-mds.pdf",
    "fileSize": 12345,
    "createdAt": "2026-10-30T15:00:00Z",
    "status": "concluido",
    "extractedEventsCount": 3,
    "errorMessage": null
  }],
  "total": 11
}
```

O backend filtra pelo usuário autenticado, aplica ordenação estável do mais recente ao mais antigo (`createdAt DESC`, `id DESC`) e retorna a contagem total dos próprios planos. `limit` aceita 1–100 (padrão 10); `offset` aceita valores não negativos (padrão 0). A página não envia um ID de usuário como autorização. `total` deve ser inteiro; respostas incompatíveis geram erro recuperável, não estado vazio.

### Detalhe existente

`GET /syllabus/{id}` usa os campos camelCase do `SyllabusDetailResponse` atual. A inclusão de `semestre` e `ano` é opcional na leitura. Contagem ausente é diferente de zero: apenas `concluido` com `extractedEventsCount: 0` apresenta “Nenhuma avaliação encontrada”. `falha` mostra orientação e `errorMessage` sanitizada pelo backend, renderizada como texto React, nunca HTML. Estados desconhecidos não são tratados como sucesso.

## Retomada e ciclo de consultas

- O ID é persistido na URL: `/plano-de-ensino?plano=<id>`. Paginação: `&pagina=2` (primeira página = 1).
- Recarregar consulta novamente esse ID com a sessão atual. A autorização de propriedade continua sendo responsabilidade da API.
- O detalhe consulta após 5 segundos, com espaçamento crescente até 30 segundos. O histórico consulta apenas quando há plano pendente/processando na página, começando em 15 segundos, também limitado a 30 segundos.
- Cada recurso agenda a próxima consulta somente após a anterior terminar. GET tem timeout de 30 segundos.
- Estado final ou desconhecido encerra polling. Erros pausam até “Tentar novamente”. Aba oculta suspende; ao voltar, consultas ativas retomam.
- Troca de página/ID, saída da rota e troca de conta cancelam requisições/timers. Dados da conta anterior são desmontados.
- A URL e o histórico deixam o plano identificável para integração futura da S6-F02. A tela informa que a revisão ainda não está disponível; não cria um botão de revisão sem destino funcional.
- A alternativa manual aponta para `/eventos?aba=meus`, onde o usuário pode usar “Criar Evento”, fluxo existente.

## Validação reproduzível

```bash
cd frontend
npm ci
npx playwright install chromium
npm test
npm run test:e2e
npm run build
```

Os testes de navegador interceptam o módulo Supabase **apenas no teste** e respondem à API com fixtures. Os mocks de autenticação são exclusivos dos testes. A demonstração interativa do produto usa exemplos locais explicitamente identificados e não contorna a autenticação dos envios reais. Cobrem multipart/autorização, duplo clique, erros, preservação dos campos, paginação, recarga, distinção vazio/falha, polling, aba oculta, logout, visitante, teclado e ausência de overflow em 360/768/1365 px nos dois temas. Screenshots são gravadas em `frontend/test-results/` (ignorado pelo Git).

Os testes de frontend simulam a API. Separadamente, upload, listagem, detalhe e privacidade foram verificados com duas contas temporárias no Supabase local: upload 202, listagem/detalhe 200, detalhe de outro usuário 404, exclusão cruzada sem efeito e exclusão pelo dono bem-sucedida. Contas e PDFs de teste foram removidos. Extração por IA e gravação de semestre/ano continuam fora dessa validação.


## Autenticação no Storage e migrações locais

O backend valida o token em `/auth/v1/user`, aplica o limite de corpo e a cota de 10 uploads por usuário em uma janela móvel de 5 dias. A gravação no Storage usa `SUPABASE_SERVICE_ROLE_KEY` somente no servidor; o navegador não pode enviar diretamente ao bucket. Sem essa configuração, o upload retorna erro de serviço. Respostas internas do Storage não são expostas ao cliente.

A migração `20261026120000_upload_planos_ensino.sql` prepara o rastreamento. A migração `20261026130000_storage_compensacao_planos.sql` acrescentou DELETE para o dono no bucket; `20261104000000_upload_apenas_backend.sql` remove a política de INSERT direto, fechando o contorno da cota. O backend compensa o arquivo se o banco rejeitar o registro.

As migrações S6-D02 de 29/10 foram alinhadas ao esquema de candidatos e planos. A política de Storage para o bucket `planos` é distinta da política de `syllabus_files` usada neste upload.

## Integração real de turmas — #70/#71

Use `/plano-de-ensino?modo=catalogo` após login para buscar por período, unidade,
nome, código, professor ou turma. Seguir/deixar de seguir persiste no servidor;
“Ver planos” abre a oferta pelo UUID, mantendo disciplinas homônimas e períodos
separados. A oferta deve continuar disponível para novos envios de PDF/texto.
Planos antigos continuam acessíveis pelo histórico e compromissos importados
permanecem na agenda ao deixar de seguir. O modo demonstrativo continua separado.
Os detalhes de operação e limites estão em [Catálogo de turmas](arquitetura/catalogo-de-turmas.md).

## Recuperação da jornada — S7-F03

Na jornada autenticada, o texto colado mostra o tamanho UTF-8 e bloqueia entradas
acima de 40.000 bytes. Uma falha de envio preserva o conteúdo e orienta consultar
o histórico antes de repetir. A preparação por texto e a organização manual
continuam disponíveis como alternativas a PDFs inválidos ou sem texto extraível.

A prévia do texto é validada antes de renderizar os campos. Uma resposta inválida
oferece nova consulta, sem habilitar a autorização. Falhas com resultado incerto
na autorização bloqueiam outro envio até usar **Consultar autorização**. Essa ação
reconsulta o estado persistido; as declarações de revisão e consentimento precisam
ser marcadas novamente para uma nova ação. O histórico é atualizado após autorizar.

Recarga e retorno à página consultam o plano pelo ID da URL. Edições locais ainda
não autorizadas não são persistidas pelo navegador. Acompanhamento e controles de
autorização ficam suspensos em falha de consulta, com ação de recuperação visível.
