---
title: "Uso de IA"
description: "Registro transparente do uso de inteligência artificial no projeto Agenda UnB, conforme exigido pelo plano de ensino de MDS."
---

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

### 09/11/2026 — S7-D01: turmas, vínculos, versões e isolamento dos planos (#69)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** leitura da documentação do projeto (visão, requisitos, padrões, arquitetura e planejamento da R2) e modelagem das ofertas de turma, vínculos, versões de plano e regras de isolamento, com testes e documentação.
- **O que entrou no repositório:** migração `20261109120000_turmas_vinculos_versoes.sql`, modelos em `backend/src/database/models.py`, `backend/tests/test_classes_database.py`, dicionário de dados, DER e `padroes.md` (PR #88).
- **O que foi verificado:** a migração foi aplicada sobre dados já existentes (plano, candidatos e evento importado), e confirmei que todos ganharam a versão 1. Os 6 testes novos passam no PostgreSQL e falham num banco sem a migração. A suíte completa passou com o banco local (71 testes), e o `supabase start` subiu do zero.
- **O que foi rejeitado ou corrigido:** a decisão de manter `avaliacoes` como tabela de candidatos e remover `candidatos_avaliacao` foi minha, confirmada com o Thomas e o Thomaz. Não aceitei deixar a unicidade de importação global, porque bloquearia colegas ao importar uma versão compartilhada. O compartilhamento do PDF ficou para a S8-B01, como diz o planejamento.

### 04/11/2026 — Correção das migrações da S6-D02 que impediam o `supabase start` (PR #63)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** descobrir por que a `dev` não subia o banco e corrigir.
- **O que entrou no repositório:** correção de nomes de coluna, tabela e bucket em `20261029153745_s6_d02_parte1_rls_tabelas.sql` e `20261029154524_s6_d02_parte2_rls_storage.sql`.
- **O que foi verificado:** reproduzi o erro (`column "proprietario_id" does not exist`), apliquei todas as migrações sem erro e testei que o dono vê os próprios planos, candidatos e PDFs, enquanto outro usuário e o visitante não veem nada.
- **O que foi rejeitado ou corrigido:** a função `confirmar_candidatos_transacional` também aponta para uma tabela inexistente, mas não a alterei, porque é do escopo do Luis. Registrei no PR para decisão do grupo.

### 28/10/2026 — S6-D01: planos particulares e candidatos (#53, PR #56) e compatibilização com o upload (#40)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** modelagem dos planos particulares, estados de processamento e candidatos com procedência; depois, a correção do conflito com a migração do upload (#40), que quebrava o `supabase start`.
- **O que entrou no repositório:** migração `20261027120000_planos_particulares_e_candidatos.sql`, ajustes de status e `professor_id` no módulo de upload e seus testes, DER e dicionário de dados.
- **O que foi verificado:** apliquei as migrações com dados anteriores à #40 e com uma linha criada pelo código da #40; as constraints, a conversão de status e a idempotência foram testadas, e o pytest do back-end continuou passando.
- **O que foi rejeitado ou corrigido:** a primeira versão criava colunas próprias (`proprietario_id`, `arquivo_caminho`) que duplicavam as da #40; adotei os nomes que o back-end já usava. Mantive os status em português, como no plano da Sprint 6, em vez dos valores em inglês.

### 14/10/2026 — Issues #41, #42 e #43: sugestão de eventos, RLS do painel admin e bucket de planos

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** migrações para as três issues.
- **O que entrou no repositório:** `20261014120000`, `20261014120100` e `20261014120200`.
- **O que foi verificado:** 50 testes em PostgreSQL simulando cada papel (visitante, aluno, professor, admin e back-end), e `supabase start` local antes do PR.
- **O que foi rejeitado ou corrigido:** durante a revisão, encontramos uma falha da minha migração de `profiles`: qualquer usuário logado podia se promover a admin pelo navegador. Ela foi fechada na #42 e reproduzida antes e depois da correção.

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
