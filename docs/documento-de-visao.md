# Documento de Visão — Agenda UnB

**Equipe:** Agenda UnB — Métodos de Desenvolvimento de Software, 2026/2  

---

## 1. Introdução

### 1.1 Propósito

Este documento descreve a visão do produto Agenda UnB: qual problema ele resolve, para quem, e quais capacidades ele deve ter. Serve de referência comum para a equipe e de base para o backlog. Não detalha os requisitos funcionais e não funcionais, que estão em [`requisitos.md`](requisitos.md), nem os padrões de código, dados e API, que estão em [`padroes.md`](padroes.md). As decisões técnicas de arquitetura e infraestrutura estão consolidadas em [`Architecture.md`](Architecture.md). A identidade visual e as especificações de interface e design system estão em [`DESIGN.md`](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/DESIGN.md), [`PRODUCT.md`](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/PRODUCT.md) e [`especificacao-frontend.md`](especificacao-frontend.md). O planejamento ágil por sprint está em [`sprints/`](sprints/sprint-1.md), as entregas e notas de versão em [`release-notes/`](release-notes/v0.1.0.md), e o registro de uso de IA em [`AI-USAGE.md`](AI-USAGE.md).

### 1.2 Escopo

O produto é uma aplicação web para a comunidade da Universidade de Brasília, cobrindo dois eixos principais: divulgação de eventos do campus e organização de prazos acadêmicos individuais.

Está fora do escopo: aplicativo nativo para celular e gestão acadêmica propriamente dita (notas, frequência, matrícula oficial).

### 1.3 Definições

| Termo | Significado |
|---|---|
| Evento | Atividade aberta do campus: palestra, calourada, semana universitária, prazo institucional, cultura ou esporte |
| Avaliação | Prova, trabalho ou entrega de uma turma específica |
| Plano de ensino | Documento em PDF ou texto bruto contendo a ementa e o cronograma de atividades da disciplina |
| Turma | Oferta de uma disciplina num semestre, identificada por código e professor |
| Campus | Localidade física da universidade atendida pelo sistema (Darcy Ribeiro, FGA, FCE, FUP e FAL) |

---

## 2. Posicionamento

### 2.1 Oportunidade de negócio

A informação que organiza a rotina de um estudante da UnB está fragmentada em canais que não se relacionam. A grade está no SIGAA. As datas de prova estão em um PDF de plano de ensino que geralmente é aberto apenas na primeira semana de aula. Os eventos circulam por meio do Instagram de centros acadêmicos, murais e grupos de WhatsApp.

Não existe um lugar único onde o estudante visualize de forma integrada o que vai acontecer com ele e com o campus nas próximas semanas.

### 2.2 Descrição do problema

| | |
|---|---|
| **Problema** | Informação acadêmica e institucional dispersa em múltiplos canais desconectados |
| **Afeta** | Estudantes de graduação/pós-graduação, professores e organizadores de eventos de todos os campi da UnB |
| **Impacto** | Prazos descobertos em cima da hora, provas esquecidas e eventos acadêmicos/culturais com baixa adesão por falhas de divulgação |
| **Ideia aplicada** | Um hub digital único que reúne eventos do campus e prazos de disciplinas do estudante, alimentado com baixa fricção e suporte a extração automatizada |

### 2.3 Declaração de posição do produto

| | |
|---|---|
| **Público** | Estudantes e professores da Universidade de Brasília (UnB) |
| **Razão** | Centralizar o acompanhamento de prazos de disciplinas e a descoberta de eventos de extensão, cultura e lazer |
| **Nome escolhido** | Agenda UnB |
| **O que é** | Hub digital acadêmico e de eventos da Universidade de Brasília (aplicação web responsiva) |
| **O que faz** | Reúne num só calendário os eventos abertos do campus e as avaliações das turmas do estudante, extraindo datas automaticamente de planos de ensino e oferecendo alternância entre temas claro e escuro |
| **Distingue-se de** | Google Agenda, que exige cadastro manual de tudo e não possui catálogo institucional integrado; e do SIGAA, que não cobre eventos de forma eficiente nem centraliza o cronograma visual de avaliações em uma experiência de usuário moderna e acessível |
| **Resolução** | Centralização com baixa fricção, catálogo público acessível sem login, autenticação ágil (Google OAuth para estudantes e validação institucional `@unb.br` para professores) e extração assistida de cronogramas |

---

## 3. Stakeholders e usuários

### 3.1 Stakeholders

| Stakeholder | Interesse no produto |
|---|---|
| Estudantes de graduação e pós-graduação | Usuários principais da agenda pessoal e do catálogo de eventos; buscam não perder prazos e descobrir atividades |
| Centros acadêmicos, atléticas e grupos de extensão | Precisam de um canal de divulgação direto e unificado que alcance a comunidade além das redes sociais |
| Professores | Usuários verificados (via e-mail institucional `@unb.br`), cadastram eventos oficiais e fornecem os planos de ensino de suas turmas |
| Docente e monitores de MDS | Avaliam o projeto como produto de software e acompanham as práticas de engenharia e processo ágil |
| Equipe G8 | Constrói, documenta, testa e sustenta a aplicação |

### 3.2 Perfis de usuário

**Estudante (`student`)** — Usuário principal da agenda. Acessa a plataforma para acompanhar eventos do campus, gerenciar compromissos privados, realizar upload do seu atestado de matrícula (PDF do SIGAA) para alocação automática em turmas e matérias, enviar planos de ensino particulares ou validar de forma colaborativa as avaliações de planos oficiais da sua turma. Autentica-se com e-mail e senha ou via Google OAuth.

**Professor (`professor`)** — Cadastro e autopromoção exigem e-mail institucional `@unb.br`; administradores podem atribuir o perfil a contas de outro domínio. Cria e gerencia eventos acadêmicos oficiais, poderá disponibilizar planos de ensino oficiais das suas turmas e possui acesso ao painel de moderação para visualizar e aprovar/rejeitar eventos submetidos pela comunidade.

**Administrador (`admin`)** — Possui acesso pleno ao painel administrativo da plataforma: visualiza e modera eventos públicos, gerencia categorias do sistema e possui privilégio exclusivo de alterar papéis/cargos de usuários (`student`, `professor`, `admin`).

**Visitante (`guest`)** — Usuário sem autenticação que consulta o catálogo público de eventos, com suporte a busca textual e filtros avançados por campus e categoria.

---

## 4. Visão geral do produto

### 4.1 Perspectiva

Aplicação web responsiva (SPA), de uso público para consulta do catálogo de eventos do campus e autenticado para a gestão de eventos pessoais, turmas e processamento de planos de ensino e atestados de matrícula. Substitui a transcrição manual de datas para calendários externos e automatiza a organização acadêmica do discente.

### 4.2 Suposições e dependências

- Estudantes possuem conta de e-mail ativa para autenticação (pessoal ou Google/institucional); o cadastro e a autopromoção de professores exigem `@unb.br`, com exceção para atribuição de cargo realizada por administrador.
- Os estudantes realizam o upload do seu atestado de matrícula emitido pelo SIGAA (formato PDF), permitindo que o parser extraia código de disciplina, nome da matéria e turma, vinculando o estudante automaticamente às suas respectivas ofertas sem necessidade de integração direta por API com o SIGAA.
- Para os cronogramas acadêmicos, adota-se o **Modelo Dual**: professores cadastram planos de ensino oficiais vinculados às turmas, enquanto estudantes podem submeter uploads particulares de planos de ensino diretamente para sua agenda pessoal.
- Os planos de ensino e atestados de matrícula submetidos são preferencialmente arquivos digitais em formato PDF com texto selecionável ou texto bruto (RF05). Casos de digitalizações em imagem sem camada de texto geram notificação clara de erro sem travar o sistema (RNF10), com suporte a inserção manual.
- A persistência relacional, autenticação e armazenamento de arquivos utilizam a infraestrutura gerenciada do Supabase (PostgreSQL, Auth e Storage), orquestrada por uma API REST em Python/FastAPI.

---

## 5. Recursos do produto

O detalhamento completo dos 21 requisitos funcionais está em [`requisitos.md`](requisitos.md).

| # | Recurso | Descrição |
|---|---|---|
| R1 | Acesso e Perfis Diferenciados | Autenticação local (e-mail/senha), Google OAuth para estudantes, `@unb.br` no cadastro/autopromoção de professores, com atribuição excepcional por admin, moderação administrativa (`admin`) e modo visitante sem autenticação (RF01–RF04) |
| R2 | Agenda Unificada e Eventos Pessoais | Calendário visual com compromissos pessoais e gestão completa (CRUD) de prazos acadêmicos privados do usuário (RF08, RF09) |
| R3 | Catálogo Multi-campus de Eventos | Consulta pública de eventos dos campi (Darcy Ribeiro, FGA, FCE, FUP, FAL), com busca textual e filtros por categoria, campus e turno (RF14, RF15, RF19) |
| R4 | Publicação e Painel Administrativo de Moderação | Cadastro de eventos públicos com painel de moderação para professores e admins aprovarem submissões comunitárias, e gestão de papéis restrita a administradores (RF10, RF11) |
| R5 | Alocação Automática de Turmas via Atestado | Upload do atestado de matrícula do SIGAA (PDF) para extrair matérias e turmas, alocando o aluno automaticamente nas suas disciplinas |
| R6 | Extração Automática de Cronograma (Modelo Dual) | Suporte a planos de ensino oficiais (submetidos por professores) e uploads particulares (submetidos por estudantes) para identificação automática de datas de provas e trabalhos (RF05, RF06) |
| R7 | Validação Colaborativa e Revisão Assistida | Alunos da mesma turma votam para confirmar ou contestar datas extraídas de planos compartilhados (validação colaborativa ativa), além de revisão assistida individual ("Human-in-the-loop") para uploads privados (RF07) |
| R8 | Inscrição Direta e Participação | Inscrição em eventos públicos com um clique, cancelamento e histórico de participação (RF12, RF13, RF18) |
| R9 | Notificações de Proximidade | Alertas prévios sobre provas, trabalhos e eventos com data próxima (RF17) |
| R10 | Exportação de Calendário | Geração de arquivo `.ics` para sincronização com Google Calendar, Outlook e Apple Calendar (RF21) |
| R11 | Design System e Bivalência de Temas | Alternância entre modo escuro (*Dark*) e claro (*Light*), ancorado na identidade "The Neon Campus" com estilo *halftone*, *glassmorphism* e *glow* em Azul `#008bff` (RF20, DESIGN.md, PRODUCT.md) |
| R12 | Coleta Automática Externa | Foco primário em notícias e feeds institucionais da UnB; fontes adicionais (SIGAA e Instagram) mantidas condicionadas à viabilidade técnica de scraping (RF16) |

---

## 6. Restrições

**De equipe** — Seis integrantes com responsabilidades distribuídas entre frontend (2), backend (2) e banco de dados (2). Todos cursando a disciplina em paralelo a outras atividades acadêmicas.

**De prazo** — Semestre letivo 2026/2 com entregas intermediárias rígidas. A Release 1 foi entregue na Sprint 04 (28/09/2026), e o ciclo atual atende aos prazos da Release 2.

**De front-end** — SPA construída em React 19 com Vite 6 e React Router 7. A interface segue estritamente o Design System "The Neon Campus" (`DESIGN.md` e `PRODUCT.md`): uso da cor primária Azul Glow `#008bff`, tipografia Orbitron (display) e Inter (body/labels), iconografia padronizada em Material Symbols, preenchimentos sólidos (flat) ou glassmorphism neutro, e proibição explícita de *linear gradients* e sombras com opacidade superior a 20%.

**De back-end e API** — API REST desenvolvida em Python 3.12 com FastAPI, SQLAlchemy 2 para ORM, Pydantic 2 para validação e httpx para comunicação assíncrona. Os endpoints seguem o padrão RESTful com prefixo `/api/v1` documentado em `docs/padroes.md`.

**De banco de dados e persistência** — PostgreSQL 15+ gerenciado via Supabase, estruturado por migrações SQL versionadas em `supabase/migrations/` e com políticas de Row Level Security (RLS) ativas em todas as tabelas. Arquivos de planos de ensino e atestados armazenados no Supabase Storage com acesso privado.

**De documentação e versionamento** — Documentação estática gerada via MkDocs Material e publicada no GitHub Pages através de workflow de CI/CD (`.github/workflows/docs.yml`).

---

## 7. Riscos e questões em aberto

| Item | Situação e Mitigação Consolidada |
|---|---|
| Legibilidade dos planos e atestados | O parser foca em arquivos PDF com texto selecionável e texto bruto (RF05), garantindo processamento rápido (RNF06 < 20s). Para arquivos escaneados ou corrompidos, o sistema emite instrução amigável de erro (RNF10) e permite preenchimento manual ou inserção de texto bruto. |
| Coleta externa (Web Scraping) | Redes sociais (Instagram) e SIGAA possuem alto risco de manutenção e bloqueios. A mitigação estratégica acordada prioriza feeds/portais oficiais de notícias da UnB, além de fortalecer a submissão descentralizada por professores e centros acadêmicos com fluxo de moderação. |
| Política de acesso e governança | Modelo de dupla autenticação consolidado: estudantes têm baixa fricção (Google OAuth ou e-mail pessoal/institucional); cadastro e autopromoção de professores exigem `@unb.br`, enquanto a atribuição por admin admite outro domínio. No painel administrativo, professores e admins podem aprovar eventos, mas somente administradores podem alterar papéis de usuários. |

---

## 8. Prioridade dos recursos

A ordem de prioridade segue o planejamento por ciclos acordado pela equipe:

**Fase 1 — Essencial (Entregue na Release 1 - v0.1.0 / Sprint 04)**
- R1: Acesso com autenticação local, Google OAuth e perfis `student` / `professor` (RF01, RF02, RF03, RF04)
- R3: Catálogo público multi-campus de eventos com busca textual e filtros de campus, categoria e turno (RF14, RF15, RF19)
- R2: Gestão completa de eventos pessoais do estudante (CRUD / RF09)
- R4 (parcial): Criação de eventos públicos por professores e administradores (RF10)
- R11: Bivalência de temas (Dark / Light) com identidade "The Neon Campus" (RF20)

**Fase 2 — Importante / Diferencial (Ciclo da Release 2)**
- R5: Upload de atestado de matrícula do SIGAA para alocação automática de turmas e matérias
- R6: Extração automática de planos de ensino no Modelo Dual (planos oficiais por professores e uploads particulares por estudantes) (RF05, RF06)
- R7: Validação colaborativa ativa por colegas de turma e revisão assistida "Human-in-the-loop" (RF07)
- R4 (completo): Painel de moderação por professores/admins e gestão de cargos por admins (RF11), já implementados após a R1.

**Fase 3 — Desejável / Expansão**
- R8: Inscrição direta e cancelamento em eventos com 1 clique (RF12, RF13) e histórico (RF18)
- R9: Lembretes e notificações de proximidade (RF17)
- R10: Exportação de calendário para `.ics` (RF21)
- R12: Coleta externa em portais institucionais (com fontes adicionais como SIGAA e Instagram se viável) (RF16)

## 9. Estado atual após a Sprint 05 — 18/10/2026

Além da base entregue, estão implementados o calendário mensal/semanal, os vínculos de eventos públicos salvos em Meus Eventos, o envio de sugestões estudantis, o painel de moderação, as notificações de decisão e o painel de usuários/cargos. A gestão administrativa usa RPCs Supabase protegidas no banco.

A navegação atual usa `/eventos`, `/evento/:id`, `/plano-de-ensino`, `/sugestoes` e `/admin`. A rota antiga `/segunda-pagina` redireciona. A página de planos é informativa: upload de PDF e parser ainda estão em preparação, apesar da infraestrutura de Storage já criada.

Salvar um evento público não representa inscrição. Notificações de sugestões não implementam lembretes de proximidade. A prioridade de automação acadêmica permanece no ciclo seguinte; os detalhes implementados e as migrações estão em [Atualizações pós-R1](atualizacoes.md).
