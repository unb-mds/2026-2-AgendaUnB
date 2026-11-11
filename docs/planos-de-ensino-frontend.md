# Planos de ensino — S6-F01

Este guia registra a integração da Sprint 6. Para a evolução planejada, consulte os [contratos da Release 2](atualizacoes.md#contratos-da-release-2) e a decisão sobre tratamento de PDFs no [ADR-003](arquitetura/adrs/adr-003-minimizar-dados-de-planos.md).

A rota `/plano-de-ensino` oferece envio autenticado, acompanhamento por ID e histórico paginado de planos particulares. Usa a sessão Supabase pelo cliente compartilhado da API, sem chave de serviço nem URLs de arquivos. Visitantes recebem uma chamada para login e não fazem consultas privadas.

## Demonstração e envios reais

A página abre uma demonstração interativa com catálogo ilustrativo. Em **Catálogo de turmas**, escolha o período atual ou o seguinte e busque por matéria, código, professor ou número de turma. A demonstração usa semestres civis de Brasília até haver uma fonte de períodos letivos. **Minhas turmas** lista os vínculos autodeclarados e abre o plano de exemplo ou o envio simulado da oferta escolhida. O envio simulado exige que a oferta seja seguida e esteja disponível, inclusive quando vier do último catálogo válido. Deixar de seguir mantém as avaliações já incluídas na prévia da agenda.

Na demonstração, visitantes mantêm os vínculos apenas durante a visita. Com login, só os IDs dos vínculos de exemplo são salvos no navegador, separados por conta; planos e prévia não são persistidos. A demonstração não envia arquivos e não consulta o Followw. **Envios e histórico reais** continua usando o contrato particular existente, separado do catálogo. A validação real do vínculo no envio, a persistência no servidor e o catálogo de matérias e professores dependem da integração da [#70](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70) com a [#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69).

### Evidências locais da #71

| Cenário | Resultado no frontend |
| --- | --- |
| Buscar e distinguir ofertas | Passou: busca sem acentos por matéria, professor, código e número da turma, com homônimas e períodos distintos. |
| Seguir, recarregar e abrir o plano | Passou na demonstração: o vínculo permanece na mesma conta; a oferta do período correto abre o plano ou o envio simulado. |
| Deixar de seguir | Passou na demonstração: o vínculo é removido, e as avaliações já incluídas continuam na prévia. |
| Vazio, falha e cache desatualizado | Passou com fixtures: nova tentativa, data do cache, caminho manual e bloqueio do envio para oferta indisponível. |
| Teclado e layout (RNF07–RNF09) | Passou no Chrome a 360, 768 e 1365 px, nos temas claro e escuro. Foco, campos e cores principais do catálogo verificados; sem auditoria WCAG completa. |

Revisão local: Codex, com as skills `project-standards`, `impeccable` e `code-review`. O catálogo demonstrativo não usa credenciais nem chama endpoints do Followw. Os contratos, permissões e dados do fluxo particular existente não mudaram. PR, implantação, revisão humana e homologação de ponta a ponta continuam pendentes.

## Escopo e dependências reais

O protótipo fornecido orientou a composição (envio, orientações laterais, lista por disciplina), não seus dados ou funcionalidades futuras. O limite adotado é **10 MB / 10 páginas**, não os 20 MB ilustrativos do protótipo. Matrícula, catálogo, planos oficiais, revisão/edição/seleção de candidatos e confirmação na agenda estão fora desta entrega. Nenhuma chamada a `/confirm` é feita. O painel administrativo não foi alterado.

No backend deste checkout, `POST /syllabus/upload`, `GET /syllabus` e `GET /syllabus/{id}` estão implementados. O upload aceita `file`, `disciplina` e `turma`, **mas ainda não persiste `semestre` e `ano`**. A migração S6-D01 já prevê esses campos em `planos_ensino`; o roteador de upload ainda usa o rastreamento `Syllabus`. Portanto, a integração real completa depende do alinhamento de #40/S6-B02 com S6-D01. Não confundir os testes com respostas simuladas com validação de processamento real por IA.

A interface envia semestre/ano como campos multipart, porém só exibe esses metadados no histórico quando devolvidos pelo servidor. Não usa armazenamento local para simular persistência ou inventar um histórico. Uma listagem indisponível apresenta erro recuperável sem bloquear o upload nem o acompanhamento por ID.

## Contratos consumidos

Base: `VITE_API_URL` (padrão `http://127.0.0.1:8000/api/v1`). Todas as operações usam `Authorization: Bearer <access_token>`.

### Upload existente + extensão necessária

`POST /syllabus/upload`, `multipart/form-data`:

| Campo | Tipo | Uso |
| --- | --- | --- |
| `file` | PDF | Obrigatório, até 10 × 1024 × 1024 bytes |
| `disciplina` | string | Obrigatório na interface, até 200 caracteres |
| `semestre` | inteiro 1 ou 2 | Extensão pendente do backend |
| `ano` | inteiro 2000–2100 | Extensão pendente do backend |

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
