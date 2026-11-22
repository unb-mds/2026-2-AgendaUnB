# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Alunos e professores da Universidade de Brasília (UnB) que precisam descobrir eventos extracurriculares, divulgar atividades e organizar suas demandas acadêmicas diárias.

## Product Purpose
O Agenda UnB reúne eventos dos campi, compromissos privados e avaliações extraídas de planos de ensino, integrando seleção de turmas, planos compartilhados entre seguidores, lembretes e exportação de calendário.

## Positioning
É o único hub digital que une a vivência extraclasse (eventos, extensão, lazer) com as obrigações acadêmicas (planos de ensino), criando uma experiência unificada e essencial para a sobrevivência e aproveitamento do estudante na Universidade.

## Operating Context
A plataforma será utilizada tanto de forma pontual (para descobrir o que está acontecendo no campus hoje) quanto para o planejamento de longo prazo do semestre (acompanhamento de calendário de provas e trabalhos dos planos de ensino).

## Capabilities and Constraints
- Autenticação via e-mail/senha e Google OAuth; autocadastro ou promoção própria ao perfil docente exige e-mail institucional `@unb.br` confirmado, com gestão de papéis exclusiva de administradores.
- Categorização atrelada aos campi da UnB (`Darcy Ribeiro (Plano Piloto)`, `FCTE (Gama)`, `FCTS (Ceilândia)`, `FUP (Planaltina)` e `FAL`) e às categorias de atividades.
- Lista e calendário mensal/semanal; agenda pessoal reúne eventos privados e públicos salvos por vínculo.
- Sugestões estudantis, moderação por professores/admins, notificações de decisão e gestão de cargos exclusiva de admins.
- Os envios de PDF ou texto autorizam a extração após a sanitização automática. O PDF é descartado após a leitura. O estudante revisa as avaliações antes de importá-las para a agenda.
- Obrigatório suporte fluido a temas (Claro e Escuro).

## Brand Commitments
- A identidade visual é ancorada na cor **Azul (`#008bff`)**, que deve estar presente de forma consistente.
- **Evitar:** Estilos com bordas coloridas e background mais claro (ex: azul claro com texto/borda azul) não devem ser usados, pois não transmitem a personalidade do produto.
- **Pureza Visual:** Gradientes lineares (*linear-gradients*) e sombreamentos pretos de cards com opacidade superior a 20% estão proibidos. A identidade requer preenchimentos sólidos (flat) ou *glassmorphism* neutro, onde o destaque é alcançado por brilhos (*glow*) e não por peso de sombras ou transições de cores. **Exceções intencionais:** backdrops de modais/overlays (`rgba(0,0,0,0.75)` a `rgba(2,6,16,0.88)`) e brilhos neon azuis (`rgba(0,139,255,0.25)` a `0.45`) em estados de destaque e interação.
- Cores base das páginas internas da aplicação (agenda, gestão e planos):
  - Fundo Dark: `#080c16` | Fundo Light: `#f0f4f8`
  - Cards Dark: `#1a2235` | Cards Light: `#ffffff`
  - Inputs Dark: `#101a2c` | Inputs Light: `#f8fafc`
  - Texto Dark: `#ffffff` (secundário `#94a3b8`) | Texto Light: `#1a1a2e` (secundário `#526278`)
  - Bordas Dark: `rgba(255, 255, 255, 0.15)` | Bordas Light: `rgba(0, 0, 0, 0.15)`
- Variantes de canvas hero / landing e detalhes de evento: Fundo Dark `#050508` com superfícies glass `rgba(8, 12, 22, 0.65)` a `0.78`; Fundo Light `#f5f6fa` com superfícies `rgba(255, 255, 255, 0.85)`.

## Product Principles
1. **Unificação e Foco:** Reduzir a carga cognitiva do aluno centralizando tudo em uma só interface clara.
2. **Bivalência de Temas:** O design deve ser igualmente premium, legível e fiel à marca tanto no modo claro quanto no modo escuro.
3. **Hierarquia Acadêmica:** Eventos, provas e trabalhos devem ter rápida distinção visual para que o usuário bata o olho e entenda o seu calendário.
