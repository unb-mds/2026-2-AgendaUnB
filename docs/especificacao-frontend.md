# 1.Design

## 1.1 Referências visuais e inspiração
Durante o processo de desenvolvimento da identidade visual do AgendaUnB, a equipe utilizou o site Awwwards como referência para pesquisar tendências, estilos e conceitos de design aplicados ao desenvolvimento de interfaces web.
A plataforma serviu como fonte de inspiração para a construção de uma interface moderna, visualmente organizada e alinhada às tendências atuais de desenvolvimento web.
A partir dessas referências, a equipe buscou desenvolver uma identidade própria para o AgendaUnB, adaptando elementos visuais que contribuíssem para transmitir organização, modernidade e simplicidade.

Especificamente, a equipe inspirou-se no site "Son Daven" (https://www.awwwards.com/sites/son-daven) e em técnicas e estilos demonstradas neste vídeo (https://youtu.be/BBKGPxw-6iY?si=7rVYIGBMF3PrFjo6) para a construção de um site com personalidade e interações avançadas. No âmbito acadêmico, o projeto também se inspirou em outras iniciativas que também foram desenvolvidas na disciplina de Métodos de Desenvolvimento de Software, como o **SuaGradeUnB** e o **NoFluxoUnB**, que, além de servirem como referências de como resolver problemas de organização universitária de forma eficiente, também representaram bons exemplos de UI e UX que almejamos alcançar em nosso projeto, o que fez com que mantivéssemos algumas estruturas que já estavam consolidadas e validadas naqueles projetos, tais como a NavBar, experiência de autenticação, entre outros.

Como parte dessa identidade única que buscávamos, a produção dos vídeos principais da aplicação em estilo halftone (versões *dark* e *light*) não foi feita por edição/geração convencional, mas originou-se de uma implementação focada em computação gráfica web. Utilizando as bibliotecas **Three.js** e **React Three Fiber**, um vídeo limpo original (gerado e tratado utilizando o Google AI STudio) foi capturado via `VideoTexture` e sofreu pós-processamento via **WebGL**. O núcleo dessa estética foi a construção de um *fragment shader* (GLSL) customizado, injetado através de um `ShaderPass`. Esse *shader* processou o conteúdo aplicando algoritmos de *dithering* (pontilhamento), pixelização e *halftone* (retículas), além de manipular contraste para gerar a aparência digital texturizada característica da plataforma. Assim, a equipe do frontend estabeleceu parâmetros matemáticos (*uniforms* como densidade da grade, força do efeito e contraste de cor) e, com essa parte do frontend concluída, houve a renderização dos dois shaders resultantes em vídeos .webm (um feito para o modo claro e outro para o escuro) para que a demanda de desempenho computacional (principalmente uso da GPU) fosse reduzida consideravelmente, tornando o site mais otimizado e responsivo e mantendo o diferencial estético.

## 1.2. Estilo visual Halftone e o "Neon Campus"
Como citado acima, um dos elementos utilizados na construção da identidade visual do AgendaUnB foi o estilo Halftone, também conhecido como retícula de pontos.
Essa técnica visual utiliza pequenos pontos organizados em padrões para criar texturas, contrastes e efeitos gráficos. No projeto, essa abordagem foi incorporada como elemento estético, contribuindo para tornar a interface visualmente diferenciada sem comprometer sua proposta minimalista.
A utilização do Halftone busca estabelecer uma identidade visual mais característica para o sistema, combinando elementos gráficos modernos com uma interface limpa e organizada.

Aliado ao Halftone, a bússola criativa do projeto segue o conceito e identidade visual **"The Neon Campus"**. A interface adota uma atmosfera predominantemente *clean* (fundos quase pretos ou brancos absolutos, como `#080c16`), utilizando amplamente o **Glassmorphism** (fundos translúcidos com `backdrop-filter`). Para transmitir profundidade sem pesar a interface, aplicamos a regra do *"Glow-Over-Shadow"*: em vez de sombras pretas duras (sendo proibidas no projeto opacidades maiores que 20%), a elevação dos componentes é destacada por meio de brilhos (glows) na cor Azul UnB Glow (`#008bff`), simulando luzes neon. Estilos com bordas coloridas em fundos claros e o uso de *linear gradients* também são estritamente evitados para manter a pureza e identidade visual. O design inclui o uso exclusivo da tipografia **Orbitron** para cabeçalhos (trazendo um ar tecnológico) e **Inter** para textos gerais, além do uso padronizado da iconografia via **Material Symbols**.

## 1.3. Identidade visual consolidada
A identidade visual do AgendaUnB combina diferentes elementos para estabelecer uma apresentação consistente:
- Referência estética: inspiração em projetos e tendências de design encontrados na plataforma Awwwards (com destaque para o "Son Daven") e nos projetos locais SuaGradeUnB e NoFluxoUnB.
- Paleta de cores: predominância de tons de azul (com destaque para o Azul UnB Glow `#008bff`).
- Estilo gráfico: utilização de elementos Halftone, baseados em padrões de pequenos pontos, combinados ao Glassmorphism e à regra do Glow-Over-Shadow.
- Logotipo: ampulheta minimalista, representando a gestão e organização do tempo.
- Estilo geral: visual clean, minimalista e moderno, isento de degradês ou sombras poluentes.
- Tipografia e Ícones: casamento das fontes Orbitron e Inter, com iconografia padronizada em Material Symbols.
- Personalização: disponibilização dos temas claro e escuro.

# 2. UI — User Interface (Interface do Usuário)
A interface do AgendaUnB foi desenvolvida utilizando a biblioteca React, buscando proporcionar uma navegação simples, organizada e intuitiva entre as funcionalidades disponíveis. Na arquitetura de desenvolvimento, a SPA (Single Page Application) foi construída junto à ferramenta **Vite** para otimização de build, operando de forma desacoplada do backend e utilizando o **Supabase JS** para realizar a comunicação direta com serviços de banco e armazenamento.

A aplicação está estruturada em duas páginas principais, cada uma com uma finalidade específica dentro do sistema. Essa divisão permite separar as informações institucionais e de autenticação das funcionalidades relacionadas ao gerenciamento de eventos acadêmicos.

## 2.1. Primeira página — Apresentação e autenticação
A primeira página tem como finalidade apresentar o AgendaUnB aos visitantes, disponibilizando informações sobre a proposta do projeto, seus objetivos e os desenvolvedores responsáveis.
Além da apresentação institucional, essa página disponibiliza os mecanismos de autenticação necessários para que o usuário possa acessar as funcionalidades internas da aplicação.
Os métodos de autenticação disponibilizados são:
- E-mail e senha: permite que o usuário realize seu acesso utilizando suas credenciais cadastradas.
- Google: possibilita a autenticação por meio de uma conta Google (ideal para o fluxo de estudantes).
- Convidado: possibilita o usuário acessar de forma anônima, mas sem acesso a funcionalidade de criação de eventos privados.
Além destes perfis, foi estipulada uma verificação rigorosa para Professores e Administração, exigindo validação por e-mail com o domínio oficial `@unb.br` para atestar a veracidade de eventos oficiais.

A página também disponibiliza o controle de alternância entre os temas claro e escuro, permitindo modificar a aparência visual de toda a aplicação.

## 2.2. Segunda página — Gerenciamento de eventos
A segunda página concentra as principais funcionalidades do AgendaUnB, relacionadas à visualização e ao gerenciamento de eventos acadêmicos.
Nessa página, os usuários podem visualizar eventos públicos divulgados por professores e administradores, além de criar seus próprios eventos privados.
Os eventos são apresentados por meio de cards (cartões), permitindo organizar visualmente as informações de cada atividade e facilitar sua identificação.
Os principais recursos disponíveis nessa página são:
- Eventos públicos: eventos divulgados por professores e administradores, disponíveis para visualização pelos usuários.
- Eventos privados: eventos criados individualmente pelo usuário, cujo acesso é restrito ao próprio criador.
- Apresentação em cards: organização visual dos eventos em cartões translúcidos (com bordas suaves de 14 a 20px e brilhos interativos de hover), facilitando a leitura e identificação das informações. Categorizações rígidas informam rapidamente a qual campus ou tipo de atividade o evento pertence através de rótulos (badges em formato de pílula).
- Gerenciamento de eventos: disponibilização das funcionalidades relacionadas à criação e organização dos compromissos pessoais.

## 2.3. Extração de Planos de Ensino (Core Feature pós-R1)
Para automatizar o preenchimento da agenda, a interface dispõe de um fluxo completo voltado ao envio de Planos de Ensino em PDF. O usuário realiza o upload do arquivo e acompanha o seu status de processamento através de *feedback* visual (estados como *pending* e *processing*). Após o sistema extrair as avaliações, a interface fornece uma tela de revisão ("Human-in-the-loop") para que o aluno possa corrigir nomes, descartar sugestões inconsistentes e aceitar as datas finais de provas e trabalhos antes de adicioná-las efetivamente à sua agenda privada.

## 2.4. Navegação entre páginas
Para implementar a navegação entre as diferentes páginas da aplicação, a equipe de frontend utilizou a biblioteca React Router DOM.
Essa biblioteca permite gerenciar as rotas da aplicação React, possibilitando a navegação entre diferentes páginas sem a necessidade de recarregar completamente o site a cada mudança de rota.
A utilização dessa tecnologia contribui para uma estrutura de navegação mais organizada, permitindo separar as funcionalidades da aplicação e facilitar futuras expansões do sistema, enquanto assegura comunicação fluida com a API (FastAPI) em segundo plano.

## 2.5. Alternância entre temas claro e escuro
O sistema disponibiliza um mecanismo de alternância entre os temas claro e escuro, permitindo que o usuário escolha a aparência visual de sua preferência.
Essa funcionalidade possui abrangência global, ou seja, a alteração realizada pelo usuário é aplicada à interface de toda a aplicação, mantendo a consistência visual durante a navegação entre as páginas.
A implementação busca proporcionar maior conforto visual e flexibilidade de utilização. As variáveis de luz e os vidros translúcidos se adaptam, assegurando a *bivalência* para que ambos os temas apresentem uma experiência de excelência, clareza e imersão.

## 2.6. Responsividade
O AgendaUnB foi desenvolvido com uma interface responsiva, permitindo que os elementos visuais se adaptem a diferentes resoluções e tamanhos de tela.
A estrutura da interface modifica o posicionamento e as dimensões de seus componentes conforme o dispositivo utilizado, buscando preservar a organização e a funcionalidade do sistema (redimensionando, por exemplo, exibições amplas de calendário em formatos de lista mobile e ajustando áreas de toque para as pontas dos dedos).
Dessa forma, a aplicação pode ser utilizada em computadores, tablets e smartphones, proporcionando uma experiência consistente em diferentes dispositivos sem depender de um aplicativo nativo.

# 3. UX — User Experience (Experiência do Usuário)
A experiência do usuário no AgendaUnB tem como principal objetivo facilitar a organização e o acompanhamento de eventos acadêmicos, proporcionando um ambiente acessível, intuitivo e eficiente para estudantes universitários e atuando como o hub definitivo para conter a dispersão de informações.
A estrutura da aplicação foi planejada para separar a apresentação institucional das funcionalidades de gerenciamento de eventos, permitindo que o usuário compreenda inicialmente a proposta do sistema e, posteriormente, acesse os recursos disponíveis.
As decisões relacionadas à experiência do usuário consideram os seguintes aspectos:

## 3.1. Facilidade de navegação e redução da carga cognitiva
A divisão da aplicação em duas páginas principais permite organizar as funcionalidades de acordo com suas finalidades, facilitando a localização dos recursos disponíveis num só ambiente e limitando distrações.
A utilização do React Router DOM contribui para uma navegação fluida entre as diferentes áreas do sistema.

## 3.2. Personalização da interface
A disponibilização dos temas claro e escuro permite que o usuário personalize a aparência visual da aplicação de acordo com suas preferências.
Como a alteração é aplicada globalmente, o usuário mantém sua experiência visual consistente durante a utilização do sistema, adaptando-se confortavelmente aos longos períodos noturnos ou diurnos de estudo.

## 3.3. Organização e hierarquia visual dos eventos
A separação entre eventos públicos e privados permite distinguir os compromissos divulgados pela administração daqueles criados individualmente pelos usuários.
Além disso, a apresentação dos eventos em cards facilita a identificação e a leitura das informações relacionadas a cada atividade, estabelecendo uma *hierarquia acadêmica* em que o discente pode bater o olho na tela e distinguir uma simples atração cultural de uma prova perigosa de fim de semestre.

## 3.4. Facilidade de autenticação
A disponibilização de diferentes métodos de autenticação, por meio de e-mail e senha ou conta Google ou como convidado, oferece alternativas para o acesso ao sistema.
Essa abordagem busca tornar o processo de entrada mais flexível e conveniente para os usuários, acompanhando o ritmo ágil dos alunos e as demandas burocráticas de docentes.

## 3.5. Acessibilidade em diferentes dispositivos
A responsividade da aplicação permite que os usuários acessem o AgendaUnB por meio de diferentes dispositivos, adaptando a interface às características de cada tela.
Essa característica amplia as possibilidades de utilização do sistema, permitindo que os estudantes consultem seus eventos e compromissos independentemente de estarem utilizando um computador ou dispositivo móvel na cantina do campus.

## 3.6. Simplicidade, transparência e intuitividade
A organização dos elementos visuais, a divisão das funcionalidades e a utilização de componentes padronizados buscam reduzir a complexidade de utilização do sistema.
O objetivo é permitir que os estudantes realizem suas atividades de maneira simples, sem precisar percorrer caminhos desnecessários para encontrar os recursos desejados. A adoção de indicadores de carregamento e áreas de moderação humana em processos densos (como a leitura dos PDFs) garantem que a pessoa mantenha controle total sem se perder na intuição da plataforma.
