# AI-USAGE.md — Registro de uso de IA

Registro exigido pelo plano de ensino de MDS 2026/2. O princípio da disciplina é transparência, não proibição: não há penalidade por usar, há penalidade por não declarar e por não entender.

Cada integrante registra o próprio uso. Mantenha em ordem cronológica inversa (mais recente no topo).

**Onde o uso é esperado e deve ser registrado:** implementação, testes, documentação, exploração de bibliotecas e refatoração.

**Onde não é permitido:** arguições individuais presenciais, quizzes, avaliação por pares e o ensaio de reflexão crítica.

---

## Como preencher

Uma entrada por atividade relevante. Não precisa registrar autocompletar de editor ou consulta pontual de sintaxe — registre quando a IA produziu um artefato que entrou no repositório ou influenciou uma decisão.

```markdown
### [data] — [o que foi feito]
- **Quem:** nome
- **Ferramenta:** qual modelo/serviço
- **O que foi pedido:** em uma frase
- **O que entrou no repositório:** arquivos, PRs
- **O que foi verificado:** como você conferiu que estava certo
- **O que foi rejeitado ou corrigido:** o que a IA errou ou o que você decidiu não usar
```

O campo **verificado** é o mais importante. Sem ele, a entrada declara o uso mas não demonstra entendimento — e é entendimento que a disciplina avalia.

---

## Entradas

### 09/11/2026 — Sincronização da branch remota antes do push

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Publicar a `feat/geminiapi` para abrir PR, sem alterar o Supabase.
- **O que entrou no repositório:** Merge das atualizações já presentes na branch remota, preservando os 11 commits locais, as rotas de revisão legadas, limites de upload, autenticação/Storage da equipe e o worker privado. Conflitos de modelos, upload e documentação resolvidos; mocks de Storage restritos aos testes.
- **O que foi verificado:** 113 testes locais aprovados e 31 ignorados por exigirem PostgreSQL/HTTP local ou Gemini opt-in. Suíte executada com banco SQLite, sem habilitar integrações externas. Documentação estrita e ausência de marcadores de conflito verificadas. Nenhum comando de banco, migração ou configuração do Supabase foi executado nesta etapa; `.env` permanece fora do Git.
- **O que foi rejeitado ou corrigido:** O push inicial foi recusado porque o remoto continha atualizações da equipe. Foi preservado o histórico remoto em vez de sobrescrevê-lo. A sincronização do código não foi tratada como integração entre as avaliações legadas da API e os candidatos privados do worker; essa conciliação permanece para o próximo PR.

### 09/11/2026 — Leitura limitada e pré-validação de PDF com timeout

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI), PostgreSQL/Auth/Storage locais.
- **O que foi pedido:** Concluir os ajustes e testes restantes da S6-B01, continuar commits na `feat/geminiapi` e manter a nuvem intacta.
- **O que entrou no repositório:** Leitura de no máximo limite + 1 byte, parser em subprocesso descartável com timeout configurável, espera e operações de Storage/banco fora do event loop, testes de limite/travamento/responsividade/privacidade, métricas HTTP desde o upload, contrato de erros e checklist S6-B01 com evidências locais.
- **O que foi verificado:** **129 testes aprovados e um ignorado** (Gemini real, desabilitado nesta execução), incluindo PostgreSQL e transporte HTTP local nas portas 15322/15321. O parser travado foi encerrado sem processo órfão. `/health` respondeu durante validação e Storage bloqueados. Upload de 1,725s e chegada aos candidatos em 9,880s com provedor de referência; dois candidatos, zero eventos antes de revisar e um após confirmação, sem duplicação. Documentação estrita e diff verificados.
- **O que foi rejeitado ou corrigido:** Timeout apenas de thread deixaria o parser continuar; o processo filho é encerrado. O teste inicial de travamento carregava toda a aplicação ao importar seu inspector no Windows, consumindo o prazo antes de chegar à etapa simulada; o inspector passou a um módulo leve e o teste exige comprovação de entrada nessa etapa. `totalDurationMs` começa após a pré-validação; o relatório HTTP passou a registrar também o tempo desde o início do upload. Não houve chamada externa, migração do banco da aplicação, alteração de `.env` ou operação na nuvem.

### 09/11/2026 — Integração HTTP local e preparação da entrega à equipe

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI), Supabase local e Gemini API com PDF inteiramente sintético.
- **O que foi pedido:** Continuar desenvolvendo e testando localmente; levar as migrações ao projeto Supabase preparado por Felipe Couto Duque quando estiver disponível.
- **O que entrou no repositório:** Testes HTTP de Auth/Storage/PostgREST com JWT real, fluxo FastAPI/worker/PostgreSQL, teste de revisão explícita/idempotência, executor restrito à instância local descartável, relatório de métricas sem segredos e orientação de transição para o projeto da equipe.
- **O que foi verificado:** **121 testes passaram, nenhum ignorado**, com uma chamada real ao Gemini somente com PDF sintético. Download público/cruzado e upload em pasta alheia/subpasta/MIME inválido foram negados. Processamento Gemini total de 16,917s, incluindo fila, e última tentativa de 5,340s. O fluxo completo de checagens/revisão levou 20,563s e foi registrado separadamente. Zero eventos antes da revisão e um após confirmação; repetição não duplicou. Contas/objetos de teste foram removidos ao final.
- **O que foi rejeitado ou corrigido:** A aprovação SQL de RLS não foi tratada como aprovação do transporte HTTP. As chaves locais foram lidas do CLI só em memória, sem `.env` nem saída com valores; a suíte rejeita hosts remotos e exige opção explícita para Gemini real. Não houve vínculo/alteração em projeto na nuvem nem migração do banco da aplicação 14322.

### 09/11/2026 — Liberação condicionada à verificação do banco S6-D02

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Verificar o que falta para liberar a integração e rodar PostgreSQL local, mantendo commits na `feat/geminiapi`.
- **O que entrou no repositório:** Checagem de migração/RLS/privilégios/políticas/triggers/RPC/bucket antes de iniciar o worker, comando de auditoria local sem IA, testes de regressão e recuperação nativa com `SKIP LOCKED`/fencing, documentação atualizada para distinguir implementação local de implantação no destino.
- **O que foi verificado:** Suíte completa com **118 testes passando, nenhum ignorado**, incluindo 28 PostgreSQL na instância isolada 15322. O auditor retornou `ready: true` com oito verificações aprovadas nesse banco. Consulta somente de leitura no banco da aplicação 14322 identificou duas migrações pendentes: `20261109120000` e `20261109130000`. Documentação estrita e diff passaram. Não houve chamadas Gemini, habilitação de flags, alteração do banco da aplicação ou implantação remota.
- **O que foi rejeitado ou corrigido:** A flag `SYLLABUS_PRIVACY_READY` sozinha não bastava para detectar banco sem políticas. O worker agora recusa pré-requisitos ausentes, inclusive permissões indevidas por coluna ou RPC/política de Storage exposta a anônimos. A auditoria de metadados foi documentada como complemento, não substituta dos testes comportamentais de RLS.

### 09/11/2026 — Políticas e revisão transacional S6-D02

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Identificar/corrigir as pendências S6-D02, executar PostgreSQL local e continuar commits na `feat/geminiapi`.
- **O que entrou no repositório:** Migração de privacidade de planos, candidatos, avaliações e Storage, proteção de autoria/vínculo, RPC de revisão explícita e atômica, testes reais de acesso/rollback/idempotência/concorrência e guia de operação/contrato S6-B02.
- **O que foi verificado:** 26 testes PostgreSQL passaram em uma instância Supabase isolada na porta 15322, com todas as migrações aplicadas do zero. Testes incluem `anon`, dono, outro usuário, professor/admin, RLS de objetos do Storage, rollback e duas confirmações simultâneas sem duplicação. O banco já existente na porta 14322 foi preservado.
- **O que foi rejeitado ou corrigido:** A leitura pública de avaliações foi removida e a inserção direta de planos pelo cliente foi fechada para impedir metadados forjados. A inicialização ampla foi bloqueada pela revisão automática; a alternativa mais restrita `supabase db start`, somente PostgreSQL isolado, foi aceita. A aprovação local não foi tratada como implantação de políticas no ambiente real; flags continuam desativadas.

### 09/11/2026 — Medição de fila/retentativas e orçamento por modelo

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Continuar o fechamento dos critérios de processamento e registrar commits incrementais.
- **O que entrou no repositório:** `totalDurationMs` na consulta privada, medição de desvios em logs usando o tempo desde o envio, verificação de orçamento antes de reagendar uma falha e exigência de preços explícitos para modelo não padrão.
- **O que foi verificado:** Suíte completa com 88 testes passando e nove PostgreSQL ignorados sem banco local, incluindo espera de 31s na fila com tentativa rápida, preservação do erro de timeout quando o orçamento termina e cálculo de reserva com tarifas específicas do modelo. Documentação estrita, HTML gerado (tabelas/diagrama e parâmetros), diff e ausência de credenciais nos arquivos alterados foram conferidos. Nenhuma chamada ao provedor foi necessária nesta correção.
- **O que foi rejeitado ou corrigido:** Usar apenas a duração da última tentativa ocultava fila/retentativas na meta de 20s. Reagendar sem saldo substituía a causa original por erro genérico; agora a falha é finalizada com a causa correta.

### 09/11/2026 — Prazo total e encerramento de tentativas travadas

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI) e Gemini API com PDFs sintéticos.
- **O que foi pedido:** Retomar a implementação e continuar realizando commits na `feat/geminiapi`.
- **O que entrou no repositório:** Subprocesso por tentativa com prazo total de 18s, limpeza/encerramento após timeout, comunicação JSON validada e sem logs de conteúdo; benchmark atualizado para incluir a criação do subprocesso.
- **O que foi verificado:** Suíte completa com 82 testes passando e nove PostgreSQL ignorados sem banco local, incluindo subprocessos reais travados em Storage/parser/provedor, limpeza sem processos órfãos, exceções sanitizadas e persistência de timeout com tentativas/orçamento limitados. Nova execução Gemini identificou sete candidatos corretos em cinco PDFs sintéticos, sem omissões, extras ou datas inventadas persistidas. O documento de dez páginas levou 5,171s e o caso mais lento 6,933s, incluindo subprocessos. Documentação estrita e verificação do diff passaram.
- **O que foi rejeitado ou corrigido:** Timeout de rede por operação não limitava a leitura do PDF nem a tentativa inteira. A transação da fila permanece no processo pai e somente o trabalho sem banco roda no subprocesso; isso mantém a recuperação por lease e impede que o encerramento deixe uma transação de candidatos incompleta.

### 09/11/2026 — Ambiguidade de horários no extrator Gemini

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Continuar a implementação da issue e registrar commits na branch `feat/geminiapi`.
- **O que entrou no repositório:** Validação de horários alternativos/intervalos e horários explicitamente incertos, sem escolher um horário para o estudante; versão do processamento atualizada para `syllabus-v2`.
- **O que foi verificado:** 32 testes do processamento passaram, incluindo nove novos casos de horários; datas válidas permanecem intactas e horários únicos por extenso numérico são preservados.
- **O que foi rejeitado ou corrigido:** A presença de um horário no trecho não bastava quando o mesmo trecho continha outra alternativa. A escolha foi substituída por hora nula com marcação de ambiguidade.

### 09/11/2026 — Processamento de planos particulares com Gemini (S6-B01)

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI) e Gemini API (`gemini-3.5-flash-lite`, somente corpus sintético).
- **O que foi pedido:** Implementar extração de avaliações de PDFs em candidatos estruturados, com processamento persistente fora da requisição, sem criar compromissos.
- **O que entrou no repositório:** Worker SQL com lease/fencing e orçamento acumulado, integração REST Gemini, validação de evidências e datas, modelo ORM de candidatos, migração da fila, metadados no GET privado, corpus e benchmark sintéticos, testes e documentação operacional.
- **O que foi verificado:** 66 testes passaram e nove testes PostgreSQL foram ignorados sem configuração local; chamada real com cinco PDFs sintéticos identificou sete candidatos corretos, sem omissões, extras ou datas inventadas persistidas. Documento de dez páginas com conteúdo adicional concluiu em 4,143s; nenhum caso excedeu 20s. `mkdocs build --strict` e `git diff --check` passaram. Logs/erros próprios foram revisados para não registrar texto integral, respostas brutas ou credenciais. Worker desativado por padrão; nenhum PDF real, migração remota ou deploy foi realizado.
- **O que foi rejeitado ou corrigido:** O Gemini rejeitou o primeiro esquema JSON por complexidade; o esquema enviado foi simplificado, mantendo validação local completa. A avaliação passou a associar título literal com sufixo e página para não contar variações válidas como datas inventadas. O teste de upload foi isolado do Supabase configurado no `.env`. A S6-D02 não foi presumida pronta: integração real e homologação de RLS/PostgreSQL continuam pendentes.

### 19/10/2026 — Planejamento da Sprint 06 e histórico de issues por sprint

- **Quem:** Thomas Augusto Amorim de Araujo (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Propor issues de planos de ensino com IA, com pelo menos duas por área, realocar #38/#40 no planejamento e documentar as issues nas respectivas sprints.
- **O que entrou no repositório:** Histórico e textos das issues em `docs/sprints/sprint-1.md` a `sprint-5.md`; planejamento e oito textos de issues em `sprint-6.md`; navegação e índice atualizados.
- **O que foi verificado:** Consulta atual de todas as issues/milestones do GitHub, leitura de requisitos, visão, arquitetura, schemas e migrações. Preservados os checklists e estados históricos; #38 e #40 tratadas como backend pendente. Conferidos os 20 registros existentes e os textos/checklists históricos, as seis novas propostas e a distribuição de oito issues (2 frontend, 4 backend, 2 dados). Dependências e links locais validados; `git diff --check` e `mkdocs build --strict` passaram após corrigir links prévios para arquivos da raiz. Testes da aplicação não foram executados nesta alteração documental.
- **O que foi rejeitado ou corrigido:** A hipótese inicial de duas issues por pessoa foi substituída pela confirmação do solicitante: pelo menos duas por área. A #44 já está fechada; #39/#45 permanecem na Sprint 05. A estrutura atual não suporta o fluxo particular completo e as avaliações têm leitura pública, portanto não foi presumida implementação ou privacidade prontas. Não houve criação ou realocação remota de issues.

### 19/10/2026 — Sincronização da documentação com o estado pós-R1

- **Quem:** Thomas Augusto Amorim de Araujo (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Ler e atualizar a documentação com as mudanças recentes do projeto.
- **O que entrou no repositório:** Atualização dos guias de produto, arquitetura, requisitos, interface, padrões, contribuição e índice; documento `docs/atualizacoes.md` e navegação MkDocs. Sem alteração na implementação.
- **O que foi verificado:** Leitura das rotas React e FastAPI, cliente de RPCs, componentes de calendário e eventos salvos e migrações de moderação, cargos e Storage. Validados o YAML do MkDocs, os 17 destinos da navegação, os links locais Markdown e a contagem de 11 migrações.
- **O que foi rejeitado ou corrigido:** Removidas descrições de moderação como futura e de extração de PDF como pronta; distinguido vínculo salvo de inscrição e notificação de decisão de lembrete de proximidade. Corrigida a regra de domínio de professor e um exemplo de sombra incompatível com a regra de design. A nota v0.1.0 foi preservada como histórico.

### 18/09/2026 — Ajustes de autenticação, correções de UI e modularização do CSS

- **Quem:** Thomas Augusto Amorim de Araujo
- **Ferramenta:** Google Antigravity (Gemini)
- **O que foi pedido:** Criar SVG para o botão de entrada como visitante, implementar função de fechar modais no Esc e modularizar o CSS em arquivo separado como boa prática.
- **O que entrou no repositório:** `src/App.jsx` (lógica dos modais, fechamento via tecla `Esc`) e `src/styles/global.css` (novo arquivo com todo o CSS da aplicação).
- **O que foi verificado:** Execução com sucesso do `npm run build` confirmando que o Vite empacotou o CSS estático sem erros, verificação da abertura/fechamento dos modais no clique e no `Esc`, validação do contraste de texto do botão no tema claro.
- **O que foi rejeitado ou corrigido:** Correção da cor do texto do botão de login no tema claro para garantir legibilidade com `#1a1a2e`, e correção da sintaxe das propriedades de tipografia nos links da navbar.

### 15/09/2026 — Modelagem do banco de dados (objeto de estudo, não adotado)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic), interface web
- **O que foi pedido:** schema PostgreSQL para o Agenda UnB, com políticas de Row Level Security, a partir dos requisitos e da stack definida (Supabase + SPA Vite)
- **O que entrou no repositório:** **nada.** O schema gerado foi usado como objeto de estudo, para eu entender Row Level Security, modelagem de agenda acadêmica e as limitações de uma arquitetura sem servidor. A modelagem que for para o repositório será escrita por mim, com as decisões discutidas pela equipe
- **O que foi verificado:** o schema foi executado num PostgreSQL 16 real, não apenas revisado por leitura. Uma suíte de 17 verificações cobriu constraints, o trigger de restrição de domínio institucional e — o que mais importa — cenários de vazamento: aluno não matriculado tentando ler avaliações e o PDF de turma alheia, e usuário tentando gravar registro em nome de terceiro
- **O que aprendi com o estudo:** que RLS não é camada extra num SPA sem servidor, é a única camada de segurança; que a data de uma avaliação pertence à turma e não ao aluno, senão o mesmo plano de ensino é reprocessado por cada matriculado e as datas divergem entre colegas; e que extração automática precisa registrar origem e confiança no próprio schema, porque agenda com data errada é pior que agenda nenhuma
- **O que foi rejeitado ou corrigido:**
  - A primeira versão da coluna gerada `eventos.periodo` produzia um erro críptico do PostgreSQL em vez da mensagem clara da constraint, porque colunas geradas são avaliadas antes das constraints. Corrigido com `greatest()`
  - A primeira suíte de testes passava com um vazamento dentro: rodava como dono da tabela, e **RLS não se aplica ao dono**. O teste foi reescrito para assumir o papel `authenticated`
  - Duas lacunas encontradas só depois de testar cenários de abuso: não havia policies de Storage, e qualquer aluno inseria no catálogo institucional sem rastreabilidade
  - Conflitos identificados entre o schema estudado e o `docs/requisitos.md`, ainda **não resolvidos**: o RF01 permite e-mail pessoal enquanto o trigger restringe ao domínio da UnB; o RNF01 exige hash de senha, que o Supabase Auth gerencia internamente; os papéis do RF04 (`student`/`professor`/`admin`) divergem dos do schema. São decisões de equipe, não correções técnicas

### 09/09/2026 — Limpeza do versionamento (PR #2)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic), interface web
- **O que foi pedido:** diagnóstico do estado do repositório e correção do versionamento
- **O que entrou no repositório:** commits `1c65b8c`, `0f01481`, `eb9115d` — remoção de `node_modules` e `dist` do índice, ampliação do `.gitignore`, criação de `.env.example` e `.gitattributes`, correção do `package.json`
- **O que foi verificado:** a justificativa do PR não é teórica. Um clone limpo em Linux falhou no build com `Cannot find module @rollup/rollup-linux-x64-gnu`, provando que o `node_modules` versionado não substituía a instalação. Também foi verificado, em repositório isolado, que `git rm --cached` preserva os arquivos no disco de quem executa mas os remove do disco de quem faz `pull` — o que motivou o aviso ao grupo
- **O que foi rejeitado ou corrigido:** o diagnóstico inicial afirmava que o repositório tinha um único commit. Era erro de método — o clone havia sido feito com `--depth 1`. São 15 commits, e o grupo já usava branches de feature com PR. A correção foi registrada antes do PR ser aberto

---

## Nota de honestidade

Este arquivo foi redigido com auxílio da I.A. A estrutura e o texto das entradas contém ajuda da I.A; os fatos, as verificações e as correções descritas aconteceram de fato e podem ser conferidos no histórico do Git e nos arquivos citados.
