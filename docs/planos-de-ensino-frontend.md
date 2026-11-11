# Planos de ensino — jornada particular S7-F03 (#73)

A rota `/plano-de-ensino` reúne seleção de turma, preparação de PDF/texto,
revisão e autorização do texto, revisão de avaliações e acesso à agenda.
Usuários autenticados consomem a API do projeto. Visitantes veem uma demonstração
com exemplos locais, identificada como tal, sem consultar dados particulares.

## Oferta e vínculo obrigatórios

O catálogo permite buscar por período, unidade, disciplina, professor ou turma.
Seguir uma oferta registra um vínculo autodeclarado no servidor. **Ver planos**
abre a oferta pelo UUID, preservando a distinção entre turmas e períodos.

Novos envios exigem uma oferta disponível que a conta segue. A interface consulta
`GET /class-offerings/{id}` e `GET /me/class-offerings` antes de habilitar os
formulários. Erros ou respostas inválidas bloqueiam o envio e oferecem nova consulta.
O backend verifica novamente disponibilidade e vínculo antes da extração e antes
da persistência. Sem vínculo retorna 403; oferta retirada retorna 409; sem
publicação do catálogo retorna 503. O último catálogo válido permanece utilizável
em falha da origem. [Operação do catálogo](arquitetura/catalogo-de-turmas.md).

Deixar de seguir preserva o histórico particular e os compromissos importados.
Consultar planos antigos não exige voltar a seguir a oferta.

## Preparação e autorização do texto

A base padrão da API é `/api/v1`, com proxy no desenvolvimento. `VITE_API_URL`
pode sobrescrevê-la. As chamadas particulares usam a sessão Supabase existente,
com `Authorization: Bearer <access_token>`.

| Operação | Entrada e comportamento |
| --- | --- |
| `POST /syllabus/upload` | Multipart com `file` e `offering_id`. PDF digital até 10 MiB e dez páginas. Metadados da disciplina/turma/período são derivados da oferta. |
| `POST /syllabus/text` | JSON com `text` e `offering_id`. Até 40.000 bytes UTF-8, com contador e bloqueio de excesso na interface. |
| `GET /syllabus/{id}/text` | Texto minimizado, referências de página quando disponíveis, destino e disponibilidade do provedor. |
| `POST /syllabus/{id}/extractions` | Páginas revisadas, hash do texto exato, autorização e declaração de elegibilidade; reprocessamento exige ação explícita adicional. |

O PDF é temporário, extraído localmente e descartado. Novos envios não guardam o
original no Storage. Texto bruto tem página de origem nula. A preparação não
chama o provedor. O usuário revisa o texto minimizado, remove informações
inadequadas e marca separadamente as declarações de revisão e autorização.
Editar o texto desmarca ambas. O provedor só pode processar o snapshot autorizado.
[Contrato de preparação, privacidade e operação](processamento-planos-s7.md).

A prévia é validada antes de renderizar os campos. Resposta malformada apresenta
erro com **Tentar carregar novamente**. Falhas de autorização com resultado incerto
bloqueiam outro envio até **Consultar autorização**, que reconsulta o estado salvo.
Uma nova ação exige novas declarações. O histórico é atualizado após autorizar.

## Histórico e progresso

`GET /syllabus?limit=10&offset=0` consulta o histórico paginado do próprio usuário;
`offering_id` filtra a oferta selecionada. O detalhe usa `GET /syllabus/{id}`.
O plano selecionado fica no parâmetro `plano` da URL, a oferta em `oferta` e a
página do histórico em `pagina`. Recarregar consulta os dados persistidos.

Os estados são `pendente`, `processando`, `concluido` e `falha`.
`authorizationRequired` distingue espera pela revisão humana da fila autorizada.
Contagem ausente não equivale a zero avaliações. Estados desconhecidos oferecem
nova consulta, sem presumir sucesso.

O detalhe consulta a partir de cinco segundos e o histórico a partir de quinze,
com espaçamento crescente até trinta segundos. As consultas não se sobrepõem.
Estado final interrompe o polling; falhas pausam até nova tentativa e abas ocultas
suspendem consultas ativas. Troca de plano/conta e saída da rota cancelam as
requisições. Controles de autorização ficam suspensos em falha de consulta.

## Revisão e confirmação das avaliações

O painel mostra os candidatos reais com estado persistido, página/trecho de
origem, sugestões e campos ambíguos. O usuário seleciona individualmente ou em
lote e corrige título, tipo, data, horário e fuso. A seleção em lote preserva
itens retirados da seleção. Confirmados, descartados e estados desconhecidos
ficam bloqueados para edição. Rascunhos e seleções são locais até a confirmação.

**Conferir selecionados** valida campos e direciona o foco ao primeiro erro.
Editar revoga essa conferência. A jornada por oferta exige também conferir a
identidade da turma. **Confirmar e importar** envia somente selecionados válidos
a `POST /syllabus/{id}/confirm`, com limite de 100 itens. O editor exige título
entre três e 200 caracteres, tipo Prova/Trabalho e data/hora com fuso explícito.

O contrato atual recebe `candidateId`, `title`, `startsAt`, `category` e
`description`. O evento usa a categoria existente `Acadêmico`; o tipo revisado
fica na descrição, junto do trecho, respeitando 10.000 caracteres. A procedência
é preservada pelo servidor. Esse contrato não altera o tipo do candidato original.

Cliques duplicados são bloqueados. Conflito ou resposta incerta exige
**Atualizar avaliações** antes de outro envio, reconciliando o estado persistido.
O backend protege a unicidade da confirmação e não restaura por retry um evento
já excluído. `Idempotency-Key` ainda não integra o contrato implementado.

Após confirmar, a jornada abre o calendário com nova consulta dos eventos
particulares. **Abrir Meus Eventos** navega para `/eventos?aba=meus`, que também
consulta os eventos persistidos. A conferência isolada não cria compromissos.

## Recuperação e alternativas

Falhas de envio preservam arquivo/texto e orientam consultar o histórico antes
de repetir. PDF inválido, protegido, corrompido ou escaneado sem texto recebe a
mensagem sanitizada do backend. Há alternativa por texto e cadastro manual em
Meus Eventos. Na falha do processamento, **Enviar outro PDF ou texto** retorna
à oferta correta e **Cadastrar prazos manualmente** abre a agenda pessoal.
Edições de texto ainda não autorizadas não são persistidas pelo navegador.

## Verificação local e limites

Os testes de navegador usam fixtures de Auth/API exclusivamente nos testes.
A aplicação autenticada usa serviços reais; o modo visitante usa exemplos locais.
Os testes da API usam SQLite em memória e fixtures de autenticação. Esses
resultados não comprovam implantação, permissões em PostgreSQL ou provedor real.

Com dependências instaladas, na pasta `frontend`:

```powershell
npm test
$env:E2E_PORT = '5188'
$env:E2E_BROWSER_CHANNEL = 'msedge'
npx playwright test --workers=2
npm run build
```

A suíte versionada permite outro navegador instalado por `E2E_BROWSER_CHANNEL`.
Capturas ficam em `frontend/test-results/`, ignorado pelo Git. Na pasta `backend`:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
.\venv\Scripts\python.exe -m pytest -q tests
```

Testes PostgreSQL e HTTP/provedor são opt-in. Use bases isoladas e os executores
documentados em [Processamento S7](processamento-planos-s7.md).

### Pendências para homologação da #73

- Demonstrar sem mocks a jornada seguir turma → enviar → revisar texto → autorizar
  → acompanhar → corrigir → importar → abrir na agenda, na versão implantada.
- Validar privacidade/permissões e concorrência no PostgreSQL de homologação.
- Medir RNF06 com transferência, preparação, fila e provedor, descontando somente
  a espera humana. Os testes locais não comprovam a meta de menos de vinte segundos.
- Registrar resultado por critério de aceite, PR, versão implantada e revisor humano
  na issue. Compartilhamento e votação permanecem nas entregas próprias da R2.

### Evidências consolidadas — 11/11/2026

| Verificação executada | Resultado |
| --- | --- |
| `npm test` | 25 testes aprovados. |
| Playwright completo, Edge, porta 5188, dois workers | 68 testes aprovados. Fixtures de Auth/API utilizadas apenas nos testes. |
| Backend completo com SQLite em memória | 165 testes aprovados, 55 ignorados; PostgreSQL e HTTP/provedor opt-in não executados. Um aviso de depreciação do TestClient/httpx. |
| `npm run build` | Aprovado. Aviso existente de bundle principal acima de 500 kB. |
| `git diff --check` | Sem erros. |
| Impeccable `polish` e `harden` | Inspecionados formulários, erros, seleção, autorização, confirmação, recuperação e navegação. Detector sem apontamentos no editor alterado. |
| Revisão visual | Editor em 360 px claro e 1365 px escuro; erro de prévia e sucesso de confirmação em celular. Testes também cobrem 768 px e ambos os temas. |
| Contraste dos tokens de texto revisados | Texto/secundário no card escuro: 14,77:1 e 8,47:1. No card claro: 17,06:1 e 6,22:1. Erro: 9,34:1 escuro e 7,49:1 claro. Cálculo dos pares de tokens; não substitui auditoria WCAG completa. |
| Links locais deste guia | Destinos conferidos e existentes. |
| Build da documentação | Não executado: MkDocs ausente no ambiente. |

Os cenários locais cobrem oferta válida/seguida, bloqueio sem oferta ou vínculo,
revisão e consentimento separados, recarga, histórico, candidatos reais no contrato,
correção/seleção parcial, confirmação, leitura da agenda e erros recuperáveis.
A jornada publicada sem fixtures, concorrência real em PostgreSQL e a meta RNF06
permanecem pendentes. A issue #73 deve continuar incompleta até suas evidências
de homologação e revisão humana serem registradas.

### Mensagens de commit sugeridas durante a implementação

```text
feat: exibir candidatos reais dos planos de ensino
feat: integrar selecao e correcao de avaliacoes
feat: confirmar avaliacoes pela api real
feat: conectar importacao de avaliacoes a agenda
feat: exigir oferta seguida no envio de planos
fix: fortalecer recuperacao da jornada de planos
fix: finalizar acessibilidade e documentacao de planos
```
