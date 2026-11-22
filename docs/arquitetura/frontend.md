---
title: "Especificação do frontend"
description: "Documentação da interface, identidade visual, rotas, fluxos de planos de ensino, notificações e responsividade do Agenda UnB."
---

## 1. Design e identidade visual

### 1.1 Referências visuais e recursos gráficos

A identidade visual do Agenda UnB foi construída a partir de referências de interfaces web modernas (como Awwwards) e iniciativas acadêmicas da disciplina de Métodos de Desenvolvimento de Software na UnB (como SuaGradeUnB e NoFluxoUnB), priorizando clareza, organização e baixo ruído visual.

Os vídeos principais da página inicial em estilo *halftone* (variantes para tema escuro e tema claro) foram renderizados a partir de um shader GLSL customizado em **Three.js** e **React Three Fiber** (`VideoTexture` + `ShaderPass` aplicando *dithering*, pixelização e retículas) e exportados para `.webm`, preservando a estética com baixo consumo de GPU no navegador.

### 1.2 Estilo Halftone e conceito "The Neon Campus"

O sistema adota o conceito visual **"The Neon Campus"**, combinando retículas *halftone*, superfícies translúcidas (*glassmorphism* com `backdrop-filter`) e a regra *"Glow-Over-Shadow"* com destaque em Azul UnB Glow (`#008bff`), evitando gradientes lineares.

- **Paleta principal da aplicação (`/eventos`, `/plano-de-ensino`, `/sugestoes`, `/admin`, `/configuracoes`):**
  - **Tema escuro:** fundo `#080c16`, cards `#1a2235`, campos `#101a2c`, texto `#ffffff`, texto secundário `#94a3b8`, borda `rgba(255, 255, 255, 0.15)`.
  - **Tema claro:** fundo `#f0f4f8`, cards `#ffffff`, campos `#f8fafc`, texto `#1a1a2e`, texto secundário `#526278`, borda `rgba(0, 0, 0, 0.15)`.
- **Variantes de canvas e painéis de planos:** a página inicial (`/`) e o detalhe do evento (`/evento/:id`) usam fundo `#050508` no tema escuro e `#f5f6fa` no tema claro; o painel de planos usa superfícies translúcidas dedicadas em `semester-plans.css`.
- **Sombras e brilhos:** cards mantêm restrição de opacidade de sombra até 20%, com exceções intencionais para backdrops de modais (`rgba(2, 6, 16, 0.88)` / `rgba(0, 0, 0, 0.8)`) e brilhos neon azuis (`rgba(0, 139, 255, 0.25–0.45)`).
- **Tipografia, ícones e logotipo:** **Orbitron** para títulos, **Inter** para texto corrido, **Material Symbols** para iconografia e ampulheta minimalista como logotipo.

## 2. Interface e rotas da aplicação

A interface utiliza React 19, Vite 6 e React Router 7. As operações de eventos, agenda, catálogo de turmas, planos de ensino, lembretes, conta/privacidade e Google Agenda consomem a API FastAPI (`/api/v1`), enquanto autenticação, leitura de perfil, notificações de moderação e RPCs administrativas utilizam o SDK do Supabase. Consulte a [visão arquitetural](/arquitetura/visao-geral).

| Rota | Finalidade e acesso |
| --- | --- |
| `/` | Apresentação institucional, seleção de tema e autenticação (e-mail/senha, Google OAuth e acesso como visitante) |
| `/auth/retorno` | Retorno PKCE para confirmação de e-mail, redefinição de senha e login Google |
| `/eventos` | Catálogo público de eventos e **Meus Eventos**, com lista de cards, calendário mensal/semanal, filtros, sugestões, lembretes e exportação Google Agenda / `.ics` (`/segunda-pagina` redireciona preservando query e `#plano-de-ensino`) |
| `/evento/:id` | Detalhes do evento público aprovado ou compromisso privado, procedência institucional e ação **Conferir evento** |
| `/plano-de-ensino` | Fluxo autenticado de seleção de turmas, envio de planos (PDF/texto), extração sanitizada, revisão em lote e biblioteca compartilhada da turma |
| `/configuracoes` | Aceite de Termos de Uso e Política de Privacidade, gestão de consentimentos opcionais, exportação de dados em JSON e exclusão de conta |
| `/sugestoes` | Fila e histórico de sugestões estudantis e revisões de coleta institucional (`professor` e `admin`) |
| `/admin` | Busca e filtros de usuários, alteração de papéis e gestão de categorias (`admin`) |
| `/privacidade.html`, `/termos.html` | Páginas públicas estáticas com os documentos legais vigentes |

### 2.1. Apresentação e autenticação (`/`)

A página inicial apresenta os recursos do Agenda UnB e disponibiliza autenticação por e-mail e senha, Google OAuth e acesso como visitante ao catálogo público. Cadastro e autopromoção ao papel `professor` exigem e-mail `@unb.br` confirmado; a atribuição administrativa de papéis segue a [ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas). O alternador global entre temas claro e escuro persiste a preferência do usuário em toda a aplicação.

### 2.2. Catálogo público e agenda pessoal (`/eventos` e `/evento/:id`)

Em `/eventos`, o usuário alterna entre o catálogo público da comunidade acadêmica e **Meus Eventos** (combinando compromissos privados com eventos públicos salvos), em visualização por lista de cards ou calendário mensal/semanal com botão **Hoje** e rolagem horizontal em telas pequenas.

Cards exibem rótulos em pílula por campus (`Darcy Ribeiro (Plano Piloto)`, `FCTE (Gama)`, `FCTS (Ceilândia)`, `FUP (Planaltina)`, `FAL`) e categoria, além de selo de procedência para eventos coletados da Agenda UnB Notícias. Estudantes autenticados podem sugerir eventos públicos pelo botão **Sugerir evento** no formulário de criação; professores e administradores publicam e editam eventos públicos diretamente.

Em **Meus Eventos**, o usuário pode conectar sua conta Google (escopo `calendar.app.created`) para exportar lotes de até 20 eventos para a agenda secundária **"Agenda UnB"** com prévia de alterações, ou baixar um arquivo `.ics` compatível com Apple Calendar e Outlook.

### 2.3. Central de notificações (`NotificationBell`)

O componente `NotificationBell` é exibido na barra de navegação para todas as contas autenticadas:

- **Lembretes:** disponível para qualquer papel autenticado (`student`, `professor`, `admin`), listando os avisos de proximidade (24 horas antes do evento) disparados pelo banco via `GET /api/v1/me/reminders` e permitindo marcar leitura (`PUT /api/v1/me/reminders/{id}/read`).
- **Sugestões:** aba adicional exibida para contas `student`, consultando `notificacoes` (envio, aprovação e recusa com justificativa) ao submeter proposta, ao retornar o foco à janela e periodicamente a cada 30 segundos.

### 2.4. Organizador acadêmico e planos de ensino (`/plano-de-ensino`) {#painel-do-semestre}

A página `/plano-de-ensino` exige conta autenticada (visitantes recebem orientação de acesso) e organiza a jornada em **duas etapas principais** no topo do painel (`#semester-step-classes` e `#semester-step-dates`):

1. **Etapa 1 — Selecionar turmas:** exibe **Suas turmas** e a busca no **Catálogo de turmas** (agrupada por unidade e disciplina/período, com seleções persistidas em memória entre buscas e paginações). Contas sem turmas seguidas iniciam diretamente nesta etapa. O vínculo com a turma é autodeclarado.
2. **Etapa 2 — Organizar datas:** contas com turmas ou planos já registrados abrem nesta etapa. No painel de envio (**Seus planos**), o usuário escolhe uma turma seguida e alterna entre **Arquivo PDF** (até 10 MiB e 10 páginas) e **Colar texto** (até 40.000 bytes UTF-8). Os envios autorizam a extração do texto sanitizado após preparação determinística local (até dois envios preparados em paralelo) e o worker processa a fila em segundo plano mesmo que o usuário mude de página.

Na área principal da Etapa 2, abas separam:
- **Minhas avaliações:** exibe o andamento da extração, o total de identificadores pessoais removidos (`redactedCount`), a lista pré-selecionada de candidatos completos, o filtro **Precisam de atenção** (com trecho de origem e sugestão automática de horário baseada na grade SIGAA da oferta para provas sem horário) e a confirmação em lote com `Idempotency-Key` via **Adicionar à agenda**.
- **Planos compartilhados da turma:** biblioteca colaborativa das versões compartilhadas da oferta selecionada. A versão inicial (`v1`) de um plano vinculado a uma oferta e concluído com candidatos é compartilhada automaticamente ao ser consultada ou confirmada pelo autor (e não volta a ser compartilhada automaticamente se for retirada). Reprocessamentos e revisões iniciam privados até publicação explícita (`PUT .../sharing` ou `share: true`). Seguidores da turma visualizam autoria, papel do autor, procedência institucional validada, votos (ordenados por confirmações e data mais recente), sinalização de divergência (sem alteração automática de datas) e podem importar candidatos para suas próprias agendas ou criar revisões mantendo as cópias já importadas por terceiros intactas.

Consulte os contratos em [Dados de planos](/arquitetura/dados-de-planos) e as decisões [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos), [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos) e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia).

#### Roteiro de homologação da jornada de oito planos

Para avaliar fluidez e latência fim a fim em ambiente de homologação com catálogo publicado, oito ofertas no mesmo semestre, worker habilitado e provedor Gemini ativo:

1. Convide participantes com contas autenticadas sem as oito ofertas seguidas e forneça oito PDFs digitais sintéticos totalizando 60 datas conhecidas (incluindo provas com horário e entregas de dia inteiro).
2. Cronometre a partir da abertura autenticada de `/plano-de-ensino` até as 60 avaliações constarem em **Meus Eventos**, registrando separadamente tempo total, tempo ativo de interação, tempo de espera de rede/extração e latência por plano.
3. Confira títulos, datas, horários, marcação de dia inteiro e ausência de duplicatas em **Meus Eventos** (meta: pelo menos quatro em cinco conclusões corretas abaixo de 300 segundos sem auxílio).

### 2.5. Responsividade e acessibilidade

A interface adapta layouts de calendário, modais, catálogo de turmas e tabelas de moderação/administração para desktop, tablet e celular (validados nas larguras de 360 px, 768 px e 1365 px nos temas claro e escuro), preservando áreas de toque adequadas, navegação por teclado e atributos ARIA em diálogos, notificações e abas.
