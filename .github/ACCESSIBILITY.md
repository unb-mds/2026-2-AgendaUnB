# Acessibilidade

A acessibilidade é uma prioridade central no **Agenda UnB**. Queremos que todas as pessoas da comunidade acadêmica da Universidade de Brasília — incluindo pessoas com deficiência e pessoas que utilizam tecnologias assistivas — consigam consultar eventos do campus, organizar sua rotina acadêmica, revisar planos de ensino e contribuir com o projeto.

Este documento explica nosso compromisso com a acessibilidade, o que esperamos de quem contribui com código ou documentação e como relatar barreiras de acessibilidade encontradas na plataforma.

## Prioridades

- **Meta de acessibilidade:** trabalhamos continuamente para atender às diretrizes [WCAG 2.1 Nível AA](https://www.w3.org/TR/WCAG21/) (conforme especificado no `RNF08` do projeto). Essa referência orienta o design, o desenvolvimento e as revisões do sistema, sem representar uma declaração formal de certificação externa.
- **Navegação por teclado:** todos os elementos interativos (filtros, calendário mensal e semanal, seleção de turmas, envio e revisão de planos de ensino, modais de autenticação e configurações) devem ser alcançáveis e operáveis exclusivamente por teclado, com indicador de foco visível e ordem lógica de tabulação.
- **Suporte a leitores de tela:** a interface utiliza HTML semântico, hierarquia lógica de títulos, rótulos programáticos (`aria-label`, `aria-labelledby`, `htmlFor`) e regiões de anúncio dinâmico (`aria-live`, `role="status"`, `role="alert"`) para navegação com NVDA, VoiceOver, JAWS e TalkBack.
- **Conteúdo legível e contraste:** priorizamos linguagem clara em português, links descritivos, contraste suficiente nos temas escuro (*Dark Mode*) e claro (*Light Mode*) e adaptação fluida a partir de `360px` de largura (`RNF07`) e com ampliação de tela.
- **Idioma declarado:** as páginas declaram explicitamente o idioma `pt-BR` no código para que leitores de tela utilizem a pronúncia e as regras de leitura corretas.

## Expectativas para contribuidores

Se você está contribuindo com código, interface ou documentação, siga estas diretrizes para evitar regressões de acessibilidade:

- **Testes de interface (`frontend/`)**
  - Verifique alterações visuais com uma ferramenta automatizada de acessibilidade (como [axe DevTools](https://www.deque.com/axe/devtools/) ou Lighthouse) e execute a suíte E2E (`npx playwright test`).
  - Faça ao menos uma passagem completa usando **apenas o teclado** em qualquer fluxo interativo alterado:
    - A ordem do `Tab` / `Shift+Tab` segue a leitura visual sem saltos inesperados.
    - O indicador de foco (`:focus-visible`) está sempre visível e possui contraste adequado nos temas claro e escuro.
    - Todas as ações funcionam por teclado (`Enter`, `Espaço`, `Escape` para fechar modais/menus e setas quando aplicável).
    - Não há armadilhas de teclado (*keyboard traps*): é possível entrar e sair de modais (`AuthDialog`, diálogos de confirmação, seletores customizados) com segurança.
  - Confira o comportamento para leitores de tela em novos componentes ou mudanças relevantes:
    - É possível navegar por cabeçalhos e regiões principais (`main`, `nav`, `dialog`).
    - Botões, campos e controles customizados (`CustomSelect`, abas, sino de lembretes) possuem nome acessível claro e expõem seu estado (`aria-expanded`, `aria-selected`, `aria-checked`, `disabled`).
    - Atualizações assíncronas (processamento de plano de ensino, mensagens de erro, confirmações e *toasts*) são anunciadas adequadamente.
- **Documentação e conteúdo (`docs/`)**
  - Utilize hierarquia lógica de títulos (sem pular níveis) e listas semânticas reais.
  - Escreva textos de link descritivos (evite *"clique aqui"* ou *"saiba mais"* isolados).
  - Forneça texto alternativo significativo para imagens informativas e `alt=""` para ícones puramente decorativos (consulte a [Árvore de Decisão de `alt` da W3C](https://www.w3.org/WAI/tutorials/images/decision-tree/)).
  - Não utilize apenas a cor para transmitir status ou significado (combine cor com texto, ícone ou rótulo explícito, como nos tipos de avaliação e status de processamento).
  - Garanta que o conteúdo se ajuste sem perda de informação ou estouro horizontal em telas estreitas (`360px`) e com zoom de até 200%.
- **CI/CD**
  - Pull Requests passam pela validação automatizada de acessibilidade e contraste da documentação (`npx mint a11y` no workflow [`.github/workflows/docs.yml`](workflows/docs.yml)) e pelos testes de interface ([`.github/workflows/app-ci.yml`](workflows/app-ci.yml)).
  - Corrija violações apontadas antes do merge ou documente a limitação técnica na descrição do PR.

## Como relatar barreiras de acessibilidade

Se você encontrar qualquer barreira de acessibilidade no Agenda UnB ou na sua documentação, avise nossa equipe — tratamos relatos de acessibilidade como contribuições técnicas valiosas.

1. **Abra uma issue** usando o [template de acessibilidade](https://github.com/unb-mds/2026-2-AgendaUnB/issues/new?template=acessibilidade.md) (ou envie um e-mail para `unbagenda@gmail.com` se preferir não usar o GitHub).
2. Inclua, quando possível:
   - O que você estava tentando fazer e qual barreira encontrou.
   - A rota ou URL da página (ex.: `/eventos`, `/plano-de-ensino`, `/configuracoes`).
   - Os passos para reproduzir o problema.
   - Seu sistema operacional, navegador e tecnologia assistiva utilizada (com versões, se souber).
   - Uma captura ou gravação de tela, apenas se você se sentir confortável em compartilhar.
   - A severidade estimada, conforme a [classificação abaixo](#severidade).

### Severidade

- **Crítica:** impede completamente a realização de uma tarefa principal (por exemplo, não conseguir autenticar, consultar a agenda ou confirmar candidatos de um plano de ensino via teclado ou leitor de tela).
- **Alta:** impõe dificuldade significativa para concluir a tarefa, embora exista uma alternativa ou caminho de contorno.
- **Moderada:** gera atrito, inconsistência de foco/anúncio ou contraste abaixo do esperado sem bloquear o fluxo.
- **Baixa:** ajuste pontual de semântica ou leitura com baixo impacto prático na usabilidade.

### Como respondemos

- Reconheceremos o relato de forma respeitosa e construtiva.
- **Nunca exigiremos** que a pessoa relatora informe diagnóstico médico ou dados pessoais sensíveis.
- Explicaremos os próximos passos, eventuais dependências técnicas e caminhos alternativos disponíveis enquanto a correção estiver em andamento.
- Atualizaremos a issue vinculada conforme o progresso da correção e convidaremos a pessoa relatora, se desejar, a validar se a solução eliminou a barreira antes do fechamento.

### Expectativas de resolução

Após a triagem, atribuímos severidade, responsável e meta de resolução para cada relato:

- **Crítica:** até 15 dias.
- **Alta:** até 30 dias.
- **Moderada:** até 60 dias.
- **Baixa:** até 90 dias.

Esses prazos contam a partir da abertura da issue. Caso haja impedimento técnico para cumprir a meta, registraremos o motivo na própria issue junto com a alternativa disponível e a nova previsão.

## Responsabilidade e manutenção

A acessibilidade do projeto é mantida coletivamente pela **[Equipe G8 — Mantenedores do Agenda UnB](../README.md#criadores)**, com canal direto em `unbagenda@gmail.com`.

### Responsabilidades da equipe mantenedora

- Fazer a triagem dos relatos de acessibilidade recebidos por issue ou e-mail.
- Acompanhar a correção de barreiras conhecidas e revisar o impacto de novas funcionalidades no frontend e na documentação.
- Manter os tokens de contraste dos temas claro e escuro, a navegação por teclado e este documento atualizados.

## Ambientes suportados

A aplicação web (`https://agendaunb.com.br`) e a documentação são projetadas para funcionar em:

- **Web (desktop):** versões atuais do Google Chrome, Microsoft Edge, Mozilla Firefox e Safari (`RNF12`).
- **Web (mobile):** versões atuais do Chrome no Android e Mobile Safari no iOS (a partir de `360px` de largura, `RNF07`).
- **Tecnologias assistivas de referência:** NVDA (Windows), VoiceOver (macOS / iOS) e TalkBack (Android), além de navegação exclusiva por teclado e zoom do navegador.

## Limitações conhecidas e alternativas

- **PDFs de planos de ensino escaneados (sem camada de texto):** arquivos PDF gerados apenas como imagem não possuem texto selecionável para extração automática nem leitura direta. Nesses casos, a plataforma orienta o usuário e oferece entrada por texto bruto ou cadastro manual das avaliações na agenda (`RNF10`).
- **Conteúdos e links externos de eventos:** cartazes ou páginas externas vinculadas pelo botão *Conferir evento* são hospedados pelos respectivos organizadores ou portais institucionais e podem não seguir integralmente as mesmas garantias de legenda ou descrição textual da plataforma.

**Nota:** caso encontre qualquer outra barreira, abra uma [issue de acessibilidade](https://github.com/unb-mds/2026-2-AgendaUnB/issues/new?template=acessibilidade.md).

## Feedback

A acessibilidade é uma prática contínua. Se você tiver sugestões para aprimorar esta política, nossos componentes ou nossos fluxos de verificação, abra uma issue ou envie um Pull Request.
