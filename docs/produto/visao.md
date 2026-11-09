---
title: "Visão do produto"
description: "Documento de visão do produto Agenda UnB, descrevendo propósito, escopo, posicionamento, stakeholders, recursos e prioridades."
---

**Versão** 2.0 (escopo planejado da Release 2)<br />**Equipe** Agenda UnB — Métodos de Desenvolvimento de Software, 2026/2

---

## 1. Introdução

### 1.1 Propósito

Este documento descreve a visão do produto Agenda UnB: qual problema ele resolve, para quem, e quais capacidades ele deve ter. Serve de referência comum para a equipe e de base para o backlog. Não detalha os requisitos funcionais e não funcionais, que estão em [requisitos](requisitos.md), nem os padrões de código, dados e API, que estão em [padrões](padroes.md). As decisões técnicas de arquitetura e infraestrutura estão consolidadas em [Architecture](../arquitetura/visao-geral.md). A identidade visual e as especificações de interface e design system estão em [DESIGN.md](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/DESIGN.md), [PRODUCT.md](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/PRODUCT.md) e [especificacao-frontend](../arquitetura/frontend.md). O planejamento ágil por sprint está em [sprints](../sprints/sprint-1.md), as entregas e notas de versão em [release-notes](../processo/release-notes/v0-1-0.md), e o registro de uso de IA em [AI-USAGE](../processo/uso-de-ia.md).

### 1.2 Escopo

O produto é uma aplicação web para a comunidade da Universidade de Brasília, cobrindo dois eixos principais: divulgação de eventos do campus e organização de prazos acadêmicos individuais.

Está fora do escopo: aplicativo nativo para celular e gestão acadêmica propriamente dita (notas, frequência, matrícula oficial).

### 1.3 Definições

| Termo | Significado |
| --- | --- |
| Evento | Atividade aberta do campus: palestra, calourada, semana universitária, prazo institucional, cultura ou esporte |
| Avaliação | Prova, trabalho ou entrega de uma turma específica |
| Plano de ensino | Documento em PDF ou texto bruto contendo a ementa e o cronograma de atividades da disciplina |
| Turma | Oferta de uma disciplina em um período letivo. O catálogo identifica a oferta e o usuário declara seu vínculo ao selecioná-la. |
| Campus | Localidade física da universidade atendida pelo sistema (Darcy Ribeiro, FGA, FCE, FUP e FAL) |

---

## 2. Posicionamento

### 2.1 Oportunidade de negócio

A informação que organiza a rotina de um estudante da UnB está fragmentada em canais que não se relacionam. A grade está no SIGAA. As datas de prova estão em um PDF de plano de ensino que geralmente é aberto apenas na primeira semana de aula. Os eventos circulam por meio do Instagram de centros acadêmicos, murais e grupos de WhatsApp.

Não existe um lugar único onde o estudante visualize de forma integrada o que vai acontecer com ele e com o campus nas próximas semanas.

### 2.2 Descrição do problema

|  |  |
| --- | --- |
| **Problema** | Informação acadêmica e institucional dispersa em múltiplos canais desconectados |
| **Afeta** | Estudantes de graduação/pós-graduação, professores e organizadores de eventos de todos os campi da UnB |
| **Impacto** | Prazos descobertos em cima da hora, provas esquecidas e eventos acadêmicos/culturais com baixa adesão por falhas de divulgação |
| **Ideia aplicada** | Um hub digital único que reúne eventos do campus e prazos de disciplinas do estudante, alimentado com baixa fricção e suporte a extração automatizada |

### 2.3 Declaração de posição do produto

|  |  |
| --- | --- |
| **Público** | Estudantes e professores da Universidade de Brasília (UnB) |
| **Razão** | Centralizar o acompanhamento de prazos de disciplinas e a descoberta de eventos de extensão, cultura e lazer |
| **Nome escolhido** | Agenda UnB |
| **O que é** | Hub digital acadêmico e de eventos da Universidade de Brasília (aplicação web responsiva) |
| **O que faz** | Reúne eventos dos campi e prazos acadêmicos na agenda pessoal. Ajuda a identificar provas e trabalhos a partir de planos de ensino e permite revisar as datas antes de importá-las. |
| **Distingue-se de** | Google Agenda, que exige cadastro manual de tudo e não possui catálogo institucional integrado; e do SIGAA, que não cobre eventos de forma eficiente nem centraliza o cronograma visual de avaliações em uma experiência de usuário moderna e acessível |
| **Resolução** | Centralização com baixa fricção, catálogo público acessível sem login, autenticação ágil (Google OAuth para estudantes e validação institucional `@unb.br` para professores) e extração assistida de cronogramas |

---

## 3. Stakeholders e usuários

### 3.1 Stakeholders

| Stakeholder | Interesse no produto |
| --- | --- |
| Estudantes de graduação e pós-graduação | Usuários principais da agenda pessoal e do catálogo de eventos; buscam não perder prazos e descobrir atividades |
| Centros acadêmicos, atléticas e grupos de extensão | Precisam de um canal de divulgação direto e unificado que alcance a comunidade além das redes sociais |
| Professores | Podem moderar eventos, contribuir com planos e revisar versões compartilhadas. A autoria de um perfil professor e a origem institucional são informações distintas. |
| Docente e monitores de MDS | Avaliam o projeto como produto de software e acompanham as práticas de engenharia e processo ágil |
| Equipe G8 | Constrói, documenta, testa e sustenta a aplicação |

### 3.2 Perfis de usuário

**Estudante (`student`)** — Acompanha eventos, gerencia compromissos privados, seleciona turmas no catálogo público e envia planos para revisão. Pode contribuir com uma versão revisada e avaliar ou importar candidatos de versões compartilhadas na turma. Autentica-se com e-mail e senha ou Google OAuth.

**Professor (`professor`)** — Perfil validado pela plataforma. Publica eventos, modera sugestões e pode contribuir com planos e editar versões compartilhadas conforme as permissões. A autoria docente aparece separada da procedência institucional comprovada.

**Administrador (`admin`)** — Possui acesso pleno ao painel administrativo da plataforma: visualiza e modera eventos públicos, gerencia categorias do sistema e possui privilégio exclusivo de alterar papéis/cargos de usuários (`student`, `professor`, `admin`).

**Visitante (`guest`)** — Usuário sem autenticação que consulta o catálogo público de eventos, com suporte a busca textual e filtros avançados por campus e categoria.

---

## 4. Visão geral do produto

### 4.1 Perspectiva

Aplicação web responsiva com catálogo público de eventos e área autenticada para agenda pessoal, turmas e planos. A agenda reúne compromissos privados e eventos públicos adicionados pelo usuário. O link original do evento é uma ação separada.

### 4.2 Suposições e dependências

- Estudantes possuem conta de e-mail ativa para autenticação (pessoal ou Google/institucional); professores possuem e-mail institucional sob o domínio `@unb.br`.
- O backend consulta apenas o catálogo público do Followw. O usuário escolhe a oferta manualmente e declara seu vínculo. Se a fonte falhar, vale o último catálogo válido. O envio de plano exige uma oferta disponível nesse catálogo.
- Planos começam privados. O autor pode compartilhar uma versão revisada com seguidores autenticados da turma. A plataforma distingue contribuição estudantil, autoria de perfil professor e origem institucional comprovada.
- A plataforma recebe PDF digital ou texto bruto. O PDF original é descartado após a extração local. O usuário revisa e autoriza separadamente o texto minimizado antes do processamento externo.
- A persistência relacional, autenticação e armazenamento de arquivos utilizam a infraestrutura gerenciada do Supabase (PostgreSQL, Auth e Storage), orquestrada por uma API REST em Python/FastAPI.

---

## 5. Recursos do produto

O detalhamento completo dos 21 requisitos funcionais está em [requisitos](requisitos.md).

| # | Recurso | Descrição |
| --- | --- | --- |
| R1 | Acesso e Perfis Diferenciados | Autenticação local (e-mail/senha), Google OAuth para estudantes, validação estrita com `@unb.br` para professores, moderação administrativa (`admin`) e modo visitante sem autenticação (RF01–RF04) |
| R2 | Agenda Unificada e Eventos Pessoais | Calendário visual com compromissos pessoais e gestão completa (CRUD) de prazos acadêmicos privados do usuário (RF08, RF09) |
| R3 | Catálogo Multi-campus de Eventos | Consulta pública de eventos dos campi (Darcy Ribeiro, FGA, FCE, FUP, FAL), com busca textual e filtros por categoria, campus e turno (RF14, RF15, RF19) |
| R4 | Publicação, moderação e administração | Professor e admin moderam sugestões. Somente admin gerencia papéis e categorias (RF10, RF11). |
| R5 | Seleção de turmas | Seleção manual de oferta do catálogo público Followw e vínculo autodeclarado (RF05). |
| R6 | Extração assistida de avaliações | Provas e trabalhos são extraídos como candidatos com evidência de origem (RF06). |
| R7 | Revisão, compartilhamento e colaboração | Revisão de candidatos, confirmação individual, compartilhamento voluntário e votação por versão (RF07). |
| R8 | Eventos públicos na agenda pessoal | Adicionar ou remover eventos públicos da agenda, consultar seu histórico e acessar separadamente o link original (RF12, RF13, RF18). |
| R9 | Lembretes na plataforma | Avisos persistentes 24 horas antes de eventos da própria agenda (RF17). |
| R10 | Exportação de calendário | Envio solicitado pelo usuário a uma agenda secundária Agenda UnB na conta Google de mesmo e-mail verificado. Reexportação idempotente e ICS complementar (RF21). |
| R11 | Design System e Bivalência de Temas | Alternância entre modo escuro (_Dark_) e claro (_Light_), ancorado na identidade "The Neon Campus" com estilo _halftone_, _glassmorphism_ e _glow_ em Azul `#008bff` (RF20, DESIGN.md, PRODUCT.md) |
| R12 | Coleta institucional | Agenda UnB Notícias como primeira fonte. Eventos completos seguem ao catálogo e exceções seguem para revisão (RF16). |

---

## 6. Restrições

**De equipe** — Seis integrantes com responsabilidades distribuídas entre frontend (2), backend (2) e banco de dados (2). Todos cursando a disciplina em paralelo a outras atividades acadêmicas.

**De prazo** — Semestre letivo 2026/2 com entregas intermediárias rígidas. A Release 1 foi entregue na Sprint 04 (28/09/2026), e o ciclo atual atende aos prazos da Release 2.

**De front-end** — SPA construída em React 19 com Vite 6 e React Router 7. A interface segue estritamente o Design System "The Neon Campus" ([DESIGN.md](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/DESIGN.md) e [PRODUCT.md](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/PRODUCT.md)): uso da cor primária Azul Glow `#008bff`, tipografia Orbitron (display) e Inter (body/labels), iconografia padronizada em Material Symbols, preenchimentos sólidos (flat) ou glassmorphism neutro, e proibição explícita de _linear gradients_ e sombras com opacidade superior a 20%.

**De back-end e API** — API REST desenvolvida em Python com FastAPI, SQLAlchemy 2 para ORM, Pydantic 2 para validação e httpx para comunicação assíncrona. Os endpoints seguem o padrão RESTful com prefixo `/api/v1` documentado em [padrões](padroes.md).

**De banco de dados e persistência** — PostgreSQL gerenciado via Supabase, migrações SQL versionadas em `supabase/migrations/` e RLS para isolamento dos dados. O plano persiste como texto e avaliações sob acesso autorizado. O PDF original só existe durante a extração local.

O ambiente virtual local `backend/venv`, usado pelo Makefile, executa **Python 3.14.4** (verificado em 08/11/2026). O backend não fixa uma versão no repositório; o CI de documentação usa Python 3.11. A proposta de implantação em 3.11 ainda exige validação de compatibilidade.

**De documentação e versionamento** — Documentação estática gerada via MkDocs Material e publicada no GitHub Pages através de workflow de CI/CD (`.github/workflows/docs.yml`).

---

## 7. Riscos e questões em aberto

| Item | Situação e Mitigação Consolidada |
| --- | --- |
| Legibilidade de planos | PDFs escaneados, protegidos ou corrompidos recebem orientação de recuperação por texto bruto ou cadastro manual (RNF10). |
| Disponibilidade de fontes | A falha do Followw preserva os vínculos e o último catálogo válido. A falha da Agenda UnB Notícias preserva os eventos já coletados. |
| Política de acesso e governança | Professores e admins moderam eventos. Admins gerenciam papéis e categorias. A edição de planos segue a propriedade e a visibilidade da versão. |

---

## 8. Prioridade dos recursos

A ordem de prioridade segue o planejamento por ciclos acordado pela equipe:

**Fase 1 — Essencial (Entregue na Release 1 - v0.1.0 / Sprint 04)**

- R1: Acesso com autenticação local, Google OAuth e perfis `student` / `professor` (RF01, RF02, RF03, RF04)
- R3: Catálogo público multi-campus de eventos com busca textual e filtros de campus, categoria e turno (RF14, RF15, RF19)
- R2: Gestão completa de eventos pessoais do estudante (CRUD / RF09)
- R4 (parcial): Criação de eventos públicos por professores e administradores (RF10)
- R11: Bivalência de temas (Dark / Light) com identidade "The Neon Campus" (RF20)

**Fase 2 — Release 2 (Sprints 7 e 8)**

- R5, R6 e R7: seleção de turma, extração assistida, revisão e compartilhamento de planos (RF05–RF07).
- R4: homologação da moderação por professor/admin e da gestão de papéis e categorias por admin (RF10, RF11).
- R8, R9, R10 e R12: eventos públicos na agenda e histórico, lembretes, exportação direta e coleta da Agenda UnB Notícias entram nesta entrega (RF12, RF13, RF16–RF18, RF21).

A Release 2 cobre a organização acadêmica e a exportação sob demanda. Matrícula oficial, atestados, notas, avisos privados do Followw/SIGAA e sincronização automática de calendário ficam fora do recorte.
