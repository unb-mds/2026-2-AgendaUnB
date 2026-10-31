# Sprint 05 - Calendário, administração e preparação para planos de ensino

**Período:** 05/10/2026 - 18/10/2026

**Objetivo:** Evoluir a organização de eventos com calendário, moderação de sugestões e administração de usuários, preparar o armazenamento privado de planos de ensino e consolidar artefatos de produto e documentação técnica.

## Principais acontecimentos:

- Implementação da visualização mensal e semanal do calendário (#36).
- Implementação das páginas de administração e sugestões (#37), com operações disponíveis via RPCs Supabase.
- Modelagem de sugestões e contador de interessados (#41), políticas administrativas (#42) e bucket privado de planos de ensino (#43).
- Conclusão dos artefatos de Produto e UX (#44), conforme estado da issue no GitHub.
- Continuidade da documentação técnica (#39 e #45), que permanece aberta.
- Os endpoints FastAPI do painel (#38) e o upload de planos (#40) não foram concluídos nesta sprint e passam ao planejamento da Sprint 06, exclusivamente com trabalho de backend. As telas e o bucket existentes não serão refeitos.

## Entregas/resultados da Sprint:

- Calendário e telas de administração/sugestões entregues.
- Base de dados e políticas para moderação entregues.
- Bucket privado `syllabus_files` com RLS entregue.
- Artefatos de Produto e UX concluídos segundo a issue #44.
- #39 e #45 mantidas nesta sprint, ainda abertas; nenhuma outra issue foi realocada no planejamento.

## Definition of Done

O objetivo era integrar calendário e administração à aplicação e preparar a infraestrutura de planos. Há entregas concluídas e pendências documentais registradas. A milestone continua aberta no GitHub na consulta de 19/10/2026; este documento não a declara encerrada.

## Issues da sprint

Consulta ao GitHub em **19/10/2026**. Estado e checklists abaixo reproduzem o registro das issues nessa consulta; uma issue fechada não representa verificação independente de todos os critérios. As atribuições históricas foram preservadas.

| Issue | Estado no GitHub | Responsáveis |
| --- | --- | --- |
| [#36 — Visualização em Calendário](https://github.com/unb-mds/2026-2-AgendaUnB/issues/36) | Fechada | @Bielziin07 |
| [#37 — Painel de Administração (Eventos e Usuários)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/37) | Fechada | @Thomas4ugust0 |
| [#39 — Documentar Especificações de Frontend, Dados e Backend](https://github.com/unb-mds/2026-2-AgendaUnB/issues/39) | Aberta | @Thomas4ugust0, @marrathomaz, @pontesluis, @heitormontt, @Bielziin07, @felipecduque7 |
| [#41 — Modelagem para Sugestão de Eventos e Contador](https://github.com/unb-mds/2026-2-AgendaUnB/issues/41) | Fechada | @pontesluis, @felipecduque7 |
| [#42 — RLS e Políticas de Segurança do Painel Administrativo](https://github.com/unb-mds/2026-2-AgendaUnB/issues/42) | Fechada | @pontesluis, @felipecduque7 |
| [#43 — Criação de Buckets e RLS para Planos de Ensino](https://github.com/unb-mds/2026-2-AgendaUnB/issues/43) | Fechada | @pontesluis, @felipecduque7 |
| [#44 — Elaboração de Artefatos de Produto e UX](https://github.com/unb-mds/2026-2-AgendaUnB/issues/44) | Fechada | @Thomas4ugust0, @marrathomaz, @Bielziin07 |
| [#45 — Preenchimento de Lacunas na Documentação Técnica](https://github.com/unb-mds/2026-2-AgendaUnB/issues/45) | Aberta | @marrathomaz, @pontesluis, @heitormontt, @felipecduque7 |

## Texto das issues registradas

### #36 — Visualização em Calendário

**Origem:** [Issue #36](https://github.com/unb-mds/2026-2-AgendaUnB/issues/36).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Front-end.

Desenvolver uma opção de visualização tipo calendário (mensal e semanal) para que o usuário possa ver seus eventos pessoais e os eventos públicos aprovados distribuídos no tempo, alternando fluidamente com a visualização atual em formato de lista.
- [x] Criar componente base de calendário (mensal/semanal).
- [x] Integrar o calendário com os dados da API de eventos públicos e privados.
- [x] Adicionar controle (botão/toggle) para alternar entre as visões "Lista" e "Calendário".
- [x] Garantir que o componente seja responsivo e se adapte bem a dispositivos móveis.
- [x] Estilizar os itens do calendário para manter a identidade visual da aplicação (Glassmorphism / Halftone).
- [x] Implementar navegação de meses e semanas.
- [x] Criar estado de carregamento e transição suave durante a troca de visualizações.

### #37 — Painel de Administração (Eventos e Usuários)

**Origem:** [Issue #37](https://github.com/unb-mds/2026-2-AgendaUnB/issues/37).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Front-end.

Criar um painel central protegido, dedicado ao controle do sistema por administradores. O painel deve permitir a visualização de eventos sugeridos por estudantes para moderação (aprovação ou recusa com justificativa) e o gerenciamento geral de contas de usuários (com troca de privilégios).
- [x] Criar rota de frontend protegida (`/admin`) acessível exclusivamente para usuários com *role* de admin.
- [x] Desenvolver layout com sistema de abas ou menu lateral (Aba Eventos e Aba Usuários).
- [x] **Eventos:** Implementar listagem focada em eventos com status de submissão `pending`.
- [x] **Eventos:** Criar botões e funções de "Aprovar" e "Recusar" para cada item pendente.
- [x] **Eventos:** Desenvolver janela modal para obrigar o preenchimento da "Justificativa" ao recusar um evento.
- [x] **Usuários:** Implementar listagem tabular ou em cards de todos os usuários cadastrados na plataforma.
- [x] **Usuários:** Adicionar barra de busca para filtrar usuários específicos por nome ou e-mail.
- [x] **Usuários:** Criar um seletor interativo em cada linha para alterar o perfil de um usuário (*student*, *professor*, *admin*).

### #39 — Documentar Especificações de Frontend, Dados e Backend

**Origem:** [Issue #39](https://github.com/unb-mds/2026-2-AgendaUnB/issues/39).

**Estado:** Aberta.

**Labels:** documentation, 03. ALTA PRIORIDADE, Front-end, Back-end, Banco de dados.

Padronizar, atualizar e registrar as decisões arquiteturais, as regras de negócio validadas e os padrões técnicos construídos até então. Esse documento servirá como consolidação da base técnica e base de consulta para o time e avaliadores.
- [ ] Atualizar o diagrama de arquitetura do backend e a documentação final dos endpoints já criados na R1.
- [x] Documentar o DDL/modelo físico atualizado do banco de dados (listando as tabelas vigentes e RLS adotados).
- [x] Documentar as especificações de design construídas no Frontend (decisões do sistema Halftone, componentes reutilizáveis, etc).
- [x] Registrar o funcionamento do novo fluxo de sugestão/moderação e o controle de interesse em eventos (mudança na regra de inscrição).
- [x] Gerar os arquivos `.md` devidamente padronizados na pasta `docs/` para que sejam publicados no MkDocs.

### #41 — Modelagem para Sugestão de Eventos e Contador

**Origem:** [Issue #41](https://github.com/unb-mds/2026-2-AgendaUnB/issues/41).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Banco de dados.

Ajustar o esquema relacional e *constraints* do banco de dados para suportar a nova proposta: estudantes poderão enviar propostas de eventos para a base de dados em estado de análise e o sistema medirá métricas quantitativas nos botões de redirecionamento.
- [x] Criar script de migração SQL (`supabase/migrations/`) exclusivo para a tabela de eventos.
- [x] Adicionar e configurar validação que garanta que, se um estudante inserir um evento, este obrigatoriamente seja criado com *status* `pending`.
- [x] Adicionar a coluna do tipo `text` nomeada `justificativa_recusa` (nula por padrão).
- [x] Adicionar a coluna quantitativa `interessados_count` do tipo `integer` e definir restrição para valor padrão de `0`.
- [x] Testar a aplicação da migração no ambiente local via Supabase CLI.

### #42 — RLS e Políticas de Segurança do Painel Administrativo

**Origem:** [Issue #42](https://github.com/unb-mds/2026-2-AgendaUnB/issues/42).

**Estado:** Fechada.

**Labels:** 01. BAIXA PRIORIDADE, Banco de dados.

Garantir total isolamento das funções executadas no Painel Admin diretamente na camada de acesso ao banco (Row Level Security e RPCs). Isso garante que, mesmo diante de um erro no backend, acessos indevidos sejam interceptados pelo banco PostgreSQL.
- [x] Escrever migração SQL ativando ou atualizando Row Level Security (RLS) para o cenário de moderação.
- [x] Desenvolver RLS impedindo acesso não-admin à visualização ampla dos usuários cadastrados na tabela pública.
- [x] Desenvolver RLS determinando que apenas o dono e usuários `admin` consigam ler eventos não-aprovados (status `pending` ou `rejected`).
- [x] Criar Stored Procedure (RPC) para possibilitar a leitura das credenciais/roles diretamente da tabela sensível interna do *Supabase Auth* e realizar alteração do cargo.

### #43 — Criação de Buckets e RLS para Planos de Ensino

**Origem:** [Issue #43](https://github.com/unb-mds/2026-2-AgendaUnB/issues/43).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Banco de dados.

Construir e blindar o ambiente de armazenamento focado nos planos de ensino, prevenindo vazamentos de arquivos sensíveis e atendendo aos requisitos não-funcionais (RNF02) de privacidade de dados acadêmicos na plataforma.
- [x] Criar e instanciar um *bucket* dedicado, nomeado como `syllabus_files`, no Supabase Storage.
- [x] Configurar propriedades do bucket para bloquear totalmente acesso não autenticado e acesso público de leitura generalizada.
- [x] Criar política (RLS) limitando as operações de inserção (upload) no *bucket* para apenas usuários devidamente autenticados.
- [x] Criar política (RLS) obrigando que os usuários consigam realizar download (leitura do storage) exclusivamente de PDFs atrelados ao seu próprio `user_id`.
- [x] Criar política (RLS) estendendo acesso de leitura do bucket aos workers do sistema/backend para processamento.

### #44 — Elaboração de Artefatos de Produto e UX

**Origem:** [Issue #44](https://github.com/unb-mds/2026-2-AgendaUnB/issues/44).

**Estado:** Fechada.

**Labels:** documentation, 03. ALTA PRIORIDADE, Front-end, Back-end.

Mapear a jornada do usuário e consolidar a identidade e experiência visual da plataforma, criando artefatos que embasem as decisões de interface para o Painel de Admin, visualização de Calendário e fluxos de engajamento (Conferir Evento).
- [x] Desenvolver e documentar as Personas básicas no Figma da aplicação (ex: Estudante ansioso por prazos, Organizador de Eventos/CA, Administrador).
- [x] Construir o User Story Map (Mapeamento da Jornada do Usuário) desenhando o caminho de ponta a ponta desde o acesso à conversão.
- [x] Criar Wireframes (Protótipos de Alta Fidelidade) no Figma para as novas telas solicitadas (Calendário, Painel Administrativo de Eventos/Usuários).

### #45 — Preenchimento de Lacunas na Documentação Técnica

**Origem:** [Issue #45](https://github.com/unb-mds/2026-2-AgendaUnB/issues/45).

**Estado:** Aberta.

**Labels:** documentation, 03. ALTA PRIORIDADE, Back-end, Banco de dados.

Saneamento de dívidas técnicas de documentação. O projeto avançou para a R1, mas documentos fundamentais de engenharia estão ausentes ou desatualizados em relação ao que já foi implementado, prejudicando o entendimento do fluxo de trabalho.
- [x] Revisar o `documento-de-visao.md`, removendo trechos obsoletos (ex: afirmações de que a Arquitetura não foi definida ou está em branco) e atualizando o status do projeto.
- [x] Criar documento `modelo-de-dados.md` (ou adicionar seção robusta em Arquitetura) contendo o Diagrama Entidade-Relacionamento (DER) e o dicionário de dados das 7 tabelas atuais do Supabase. (se não tiver sido feito no documento de especificação do banco de dados)
- [x] Criar documento `api-specs.md` detalhando os contratos do backend (rotas, payloads esperados e códigos HTTP de resposta).
- [x] Criar documento `implantacao.md` para registrar o plano de Hospedagem e CI/CD (deploy do frontend, backend e homologação do banco), que ainda não existem formalmente no projeto.
