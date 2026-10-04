# 1.Design
## 1.1 Referências visuais e inspiração
Durante o processo de desenvolvimento da identidade visual do AgendaUnB, a equipe
utilizou o site Awwwards como referência para pesquisar tendências, estilos e
conceitos de design aplicados ao desenvolvimento de interfaces web.
A plataforma serviu como fonte de inspiração para a construção de uma interface
moderna, visualmente organizada e alinhada às tendências atuais de desenvolvimento
web.
A partir dessas referências, a equipe buscou desenvolver uma identidade própria para
o AgendaUnB, adaptando elementos visuais que contribuíssem para transmitir
organização, modernidade e simplicidade.
## 1.2. Estilo visual Halftone
Outro elemento utilizado na construção da identidade visual do AgendaUnB foi o estilo
Halftone, também conhecido como retícula de pontos.
Essa técnica visual utiliza pequenos pontos organizados em padrões para criar
texturas, contrastes e efeitos gráficos. No projeto, essa abordagem foi incorporada
como elemento estético, contribuindo para tornar a interface visualmente diferenciada
sem comprometer sua proposta minimalista.
A utilização do Halftone busca estabelecer uma identidade visual mais característica
para o sistema, combinando elementos gráficos modernos com uma interface limpa e
organizada.
## 1.3. Identidade visual consolidada
A identidade visual do AgendaUnB combina diferentes elementos para estabelecer
uma apresentação consistente:
- Referência estética: inspiração em projetos e tendências de design encontrados
na plataforma Awwwards.
- Paleta de cores: predominância de tons de azul.
- Estilo gráfico: utilização de elementos Halftone, baseados em padrões de
pequenos pontos.
- Logotipo: ampulheta minimalista, representando a gestão e organização do
tempo.
- Estilo geral: visual clean, minimalista e moderno.
- Personalização: disponibilização dos temas claro e escuro.
# 2. UI — User Interface (Interface do Usuário)
A interface do AgendaUnB foi desenvolvida utilizando a biblioteca React, buscando
proporcionar uma navegação simples, organizada e intuitiva entre as funcionalidades
disponíveis.
A aplicação está estruturada em duas páginas principais, cada uma com uma
finalidade específica dentro do sistema. Essa divisão permite separar as informações
institucionais e de autenticação das funcionalidades relacionadas ao gerenciamento
de eventos acadêmicos.
## 2.1. Primeira página — Apresentação e autenticação
A primeira página tem como finalidade apresentar o AgendaUnB aos visitantes,
disponibilizando informações sobre a proposta do projeto, seus objetivos e os
desenvolvedores responsáveis.
Além da apresentação institucional, essa página disponibiliza os mecanismos de
autenticação necessários para que o usuário possa acessar as funcionalidades
internas da aplicação.
Os métodos de autenticação disponibilizados são:
- E-mail e senha: permite que o usuário realize seu acesso utilizando suas
credenciais cadastradas.
- Google: possibilita a autenticação por meio de uma conta Google.
- Convidado: possibilita o usuário acessar de forma anônima, mas sem acesso a
funcionalidade de criação de eventos privados.

A página também disponibiliza o controle de alternância entre os temas claro e escuro,
permitindo modificar a aparência visual de toda a aplicação.
## 2.2. Segunda página — Gerenciamento de eventos
A segunda página concentra as principais funcionalidades do AgendaUnB,
relacionadas à visualização e ao gerenciamento de eventos acadêmicos.
Nessa página, os usuários podem visualizar eventos públicos divulgados por
professores e administradores, além de criar seus próprios eventos privados.
Os eventos são apresentados por meio de cards (cartões), permitindo organizar
visualmente as informações de cada atividade e facilitar sua identificação.
Os principais recursos disponíveis nessa página são:
- Eventos públicos: eventos divulgados por professores e administradores,
disponíveis para visualização pelos usuários.
- Eventos privados: eventos criados individualmente pelo usuário, cujo acesso é
restrito ao próprio criador.
- Apresentação em cards: organização visual dos eventos em cartões, facilitando
a leitura e identificação das informações.
- Gerenciamento de eventos: disponibilização das funcionalidades relacionadas
à criação e organização dos compromissos pessoais.
## 2.3. Navegação entre páginas
Para implementar a navegação entre as diferentes páginas da aplicação, a equipe de
frontend utilizou a biblioteca React Router DOM.
Essa biblioteca permite gerenciar as rotas da aplicação React, possibilitando a
navegação entre diferentes páginas sem a necessidade de recarregar completamente
o site a cada mudança de rota.
A utilização dessa tecnologia contribui para uma estrutura de navegação mais
organizada, permitindo separar as funcionalidades da aplicação e facilitar futuras
expansões do sistema.
## 2.4. Alternância entre temas claro e escuro
O sistema disponibiliza um mecanismo de alternância entre os temas claro e escuro,
permitindo que o usuário escolha a aparência visual de sua preferência.
Essa funcionalidade possui abrangência global, ou seja, a alteração realizada pelo
usuário é aplicada à interface de toda a aplicação, mantendo a consistência visual
durante a navegação entre as páginas.
A implementação busca proporcionar maior conforto visual e flexibilidade de
utilização.
## 2.5. Responsividade
O AgendaUnB foi desenvolvido com uma interface responsiva, permitindo que os
elementos visuais se adaptem a diferentes resoluções e tamanhos de tela.
A estrutura da interface modifica o posicionamento e as dimensões de seus
componentes conforme o dispositivo utilizado, buscando preservar a organização e a
funcionalidade do sistema.
Dessa forma, a aplicação pode ser utilizada em computadores, tablets e smartphones,
proporcionando uma experiência consistente em diferentes dispositivos.
# 3. UX — User Experience (Experiência do Usuário)
A experiência do usuário no AgendaUnB tem como principal objetivo facilitar a
organização e o acompanhamento de eventos acadêmicos, proporcionando um
ambiente acessível, intuitivo e eficiente para estudantes universitários.
A estrutura da aplicação foi planejada para separar a apresentação institucional das
funcionalidades de gerenciamento de eventos, permitindo que o usuário compreenda
inicialmente a proposta do sistema e, posteriormente, acesse os recursos disponíveis.
As decisões relacionadas à experiência do usuário consideram os seguintes aspectos:
## 3.1. Facilidade de navegação
A divisão da aplicação em duas páginas principais permite organizar as
funcionalidades de acordo com suas finalidades, facilitando a localização dos
recursos disponíveis.
A utilização do React Router DOM contribui para uma navegação fluida entre as
diferentes áreas do sistema.
## 3.2. Personalização da interface
A disponibilização dos temas claro e escuro permite que o usuário personalize a
aparência visual da aplicação de acordo com suas preferências.
Como a alteração é aplicada globalmente, o usuário mantém sua experiência visual
consistente durante a utilização do sistema.
## 3.3. Organização dos eventos
A separação entre eventos públicos e privados permite distinguir os compromissos
divulgados pela administração daqueles criados individualmente pelos usuários.
Além disso, a apresentação dos eventos em cards facilita a identificação e a leitura das
informações relacionadas a cada atividade.
## 3.4. Facilidade de autenticação
A disponibilização de diferentes métodos de autenticação, por meio de e-mail e senha
ou conta Google ou como convidado, oferece alternativas para o acesso ao sistema.
Essa abordagem busca tornar o processo de entrada mais flexível e conveniente para
os usuários.
## 3.5. Acessibilidade em diferentes dispositivos
A responsividade da aplicação permite que os usuários acessem o AgendaUnB por
meio de diferentes dispositivos, adaptando a interface às características de cada tela.
Essa característica amplia as possibilidades de utilização do sistema, permitindo que
os estudantes consultem seus eventos e compromissos independentemente de
estarem utilizando um computador ou dispositivo móvel.
## 3.6. Simplicidade e intuitividade
A organização dos elementos visuais, a divisão das funcionalidades e a utilização de
componentes padronizados buscam reduzir a complexidade de utilização do sistema.
O objetivo é permitir que os estudantes realizem suas atividades de maneira simples,
sem precisar percorrer caminhos desnecessários para encontrar os recursos
desejados.
