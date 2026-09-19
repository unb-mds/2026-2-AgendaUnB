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