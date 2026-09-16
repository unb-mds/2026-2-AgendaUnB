# Documento de Visão — Agenda UnB

**Versão:** 0.1 (rascunho para revisão da equipe)
**Equipe:** G8 — Métodos de Desenvolvimento de Software, 2026/2

> Itens marcados com **[?]** são suposições a confirmar em reunião.

---

## 1. Introdução

### 1.1 Propósito

Este documento descreve a visão do produto Agenda UnB: qual problema ele resolve, para quem, e quais capacidades ele deve ter. Serve de referência comum para a equipe e de base para o backlog.

Não detalha os requisitos, que estão em `docs/requisitos.md`, nem os padrões de código e de dados, que estão em `docs/padroes.md`. As decisões técnicas de arquitetura serão registradas em `docs/Architecture.md`, hoje em branco. O planejamento por sprint está em `docs/sprints/`, e o registro de uso de IA em `AI-USAGE.md`, na raiz do repositório.

### 1.2 Escopo

O produto é uma aplicação web para a comunidade da Universidade de Brasília, cobrindo dois pontos principais: divulgação de eventos do campus e organização de prazos acadêmicos individuais.

Está fora do escopo: aplicativo nativo para celular e gestão acadêmica propriamente dita (notas, frequência, matrícula oficial).

### 1.3 Definições

| Termo | Significado |
|---|---|
| Evento | Atividade aberta do campus: palestra, calourada, semana universitária, prazo institucional |
| Avaliação | Prova, trabalho ou entrega de uma turma específica |
| Plano de ensino | Documento em PDF que o professor disponibiliza no início do semestre, contendo o cronograma da disciplina |
| Turma | Oferta de uma disciplina num semestre, identificada por código e professor |

---

## 2. Posicionamento

### 2.1 Oportunidade de negócio

A informação que organiza a rotina de um estudante da UnB está fragmentada em canais que não se relacionam. A grade está no SIGAA. As datas de prova estão em um PDF de plano de ensino que geralmente é aberto apenas na primeira semana de aula. Os eventos circulam por meio do Instagram de centro acadêmico, cartaz de mural e grupos de WhatsApp.

Não existe um lugar onde o estudante veja o que vai acontecer com ele nas próximas semanas.

### 2.2 Descrição do problema

| | |
|---|---|
| **Problema** | Informação acadêmica e institucional dispersa em múltiplos lugares desconectados |
| **Afeta** | Estudantes de graduação da UnB e também quem organiza eventos no campus |
| **Impacto** | Prazos descobertos em cima da hora, provas esquecidas, e eventos de extensão com baixa adesão por falta de divulgação eficaz |
| **Ideia aplicada** | Uma agenda única que reúna eventos do campus e prazos das disciplinas do próprio estudante, alimentada com o mínimo de esforço manual |

### 2.3 Declaração de posição do produto

| | |
|---|---|
| **Público** | Estudantes de graduação da UnB |
| **Razão** | Acompanhar prazos de disciplinas e eventos do campus espalhados em vários canais |
| **Nome escolhido** | Agenda UnB |
| **O que é** | Aplicação web de agenda acadêmica e institucional |
| **O que faz** | Reúne num só calendário os eventos do campus e as avaliações das turmas em que o estudante está matriculado, extraindo datas automaticamente dos planos de ensino |
| **Distingue-se de** | Google Agenda, que exige cadastro manual de tudo, e do SIGAA, que não cobre eventos nem cronograma de avaliações |
| **Resolução** | Alimentada a partir das fontes que a universidade já produz, apenas juntando tudo em um só lugar para melhor visualização |

---

## 3. Stakeholders e usuários

### 3.1 Stakeholders

| Stakeholder | Interesse no produto |
|---|---|
| Estudantes de graduação | Usuários principais, querem não perder prazos |
| Centros acadêmicos, ligas e grupos de extensão | Precisam de um canal de divulgação que alcance quem não os segue nas redes |
| Professores **[?]** | Origem indireta das datas, via plano de ensino; possível papel de validação |
| Docente de MDS | Avalia o projeto como produto e como processo |
| Equipe G8 | Constrói, documenta e mantém |

### 3.2 Perfis de usuário

**Estudante** — usa a agenda diariamente e quer o mínimo de configuração possível, podendo entrar e ver o que vem pela frente.

**Organizador de evento** — usa pontualmente, a fim de publicar eventos, e precisa de um fluxo rápido de cadastro.

**Administrador** — modera o que é publicado e mantém o catálogo de disciplinas e turmas consistente.

---

## 4. Visão geral do produto

### 4.1 Perspectiva

Aplicação web responsiva, de uso público para a parte de eventos e autenticado para a parte acadêmica. Substitui, para o estudante, a tarefa manual de transcrever datas do plano de ensino para um calendário pessoal.

### 4.2 Suposições e dependências

- Estudantes da UnB possuem e-mail institucional ativo.
- Os planos de ensino estão disponíveis em PDF com texto selecionável, e não como imagem escaneada. **[?]** Premissa ainda não verificada — ver seção 7.
- Os estudantes cadastrarão as próprias turmas, já que não há integração com o SIGAA.

---

## 5. Recursos do produto

O detalhamento está em `docs/requisitos.md`.

| # | Recurso | Descrição |
|---|---|---|
| R1 | Acesso com conta institucional | Autenticação via Google, restrita à comunidade UnB |
| R2 | Agenda unificada | Calendário único com eventos salvos e avaliações das turmas do estudante |
| R3 | Catálogo de eventos do campus | Consulta pública, com filtros por campus, categoria e período |
| R4 | Publicação e curadoria de eventos | Cadastro por membros da comunidade, com moderação |
| R5 | Vínculo com turmas | Estudante indica em quais turmas está matriculado |
| R6 | Extração automática de cronograma | Upload do plano de ensino, com leitura das datas de avaliação |
| R7 | Validação colaborativa | Colegas de turma confirmam ou contestam datas extraídas |
| R8 | Personalização individual | Ajustar, ocultar ou anotar um item sem afetar a agenda dos colegas |
| R9 | Lembretes | Aviso de proximidade de prazo |
| R10 | Exportação | Envio da agenda para calendários externos |

---

## 6. Restrições

**De equipe** — seis integrantes, com papéis distribuídos em duas frentes de front-end, duas de back-end e duas de banco de dados. Todos cursando a disciplina em paralelo a outras, com disponibilidade parcial.

**De prazo** — o semestre letivo de 2026/2, com entregas intermediárias em datas fixas. O prazo é rígido e não negociável.

**De front-end** — SPA em Vite + React, conforme já implementado no repositório. Uma mudança de framework a esta altura representaria retrabalho significativo e precisaria ser justificada em ADR.

**Não definidas** — a arquitetura de back-end, o banco de dados e a plataforma de hospedagem ainda não estão registrados em nenhum documento oficial do projeto até o momento. O `docs/Architecture.md` está em branco por enquanto, para fins de decisão em grupo.

---

## 7. Riscos e questões em aberto

| Item | Situação |
|---|---|
| Legibilidade dos planos de ensino | Se os PDFs forem imagens escaneadas, a extração automática exige OCR (Reconhecimento Óptico de Caracteres) e muda de custo |
| Escopo x prazo | 21 requisitos funcionais aprovados. Priorização explícita ainda não feita |
| Conflito no acesso | `docs/requisitos.md` (RF01) admite e-mail pessoal, o que é incompatível com uma agenda restrita à comunidade UnB. É necessário decidir qual prevalece |

---

## 8. Prioridade dos recursos **[?]**

Proposta de ordem, que deverá ser decidida pela equipe:

**Essencial** — R1, R3, R2 (parcial: apenas eventos). Entrega um produto utilizável e demonstrável.

**Importante** — R5, R8 e a entrada manual de avaliações. A agenda acadêmica funcionando sem automação.

**Desejável** — R6, R7, R9, R10. A automação, que é o diferencial, mas depende das duas camadas anteriores existirem.