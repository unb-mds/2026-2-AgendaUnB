# 1. Objetivo

As personas básicas do AgendaUnB representam os principais perfis de usuários da plataforma. Elas auxiliam na compreensão das necessidades, dos objetivos e das dificuldades dos usuários, orientando as decisões de design, usabilidade e desenvolvimento do sistema.

Foram definidos três perfis principais: o estudante, que consulta eventos públicos e pode criar eventos privados, e o professor/organizador de eventos, responsável pela publicação e pelo gerenciamento de eventos destinados à comunidade universitária, e o administrador, que garante que todas as funcionalidades estejam dentro dos padrões e segurança dos usuários.

# 2. Persona 01 — Estudante

## Nome fictício: Pedro Martins
## Perfil: Estudante universitário
## Principal objetivo: Descobrir e acompanhar eventos de seu interesse na universidade.

### Descrição:

Pedro é um estudante universitário interessado em participar de palestras, workshops, atividades acadêmicas e eventos de integração. 
Ele tem receio de perder oportunidades por não ficar sabendo dos eventos a tempo e, por isso, procura uma plataforma centralizada, intuitiva e atualizada. 
No AgendaUnB, Pedro pode visualizar os eventos públicos publicados por organizadores e administradores, consultar informações como datas, horários, locais e descrições, além de criar eventos privados para uso pessoal, acessíveis somente a ele. Ele valoriza uma interface responsiva, informações claras e uma navegação simples que facilite a descoberta de novas atividades.

### Necessidades principais:
- Consultar os eventos públicos disponíveis.
- Visualizar os detalhes de cada evento.
- Encontrar oportunidades acadêmicas e de integração.
- Criar e consultar seus próprios eventos privados.
- Salvar eventos públicos na agenda e consultar lista ou calendário.
- Sugerir atividades e acompanhar a decisão pelo sino de notificações.

# 3. Persona 02 — Professora / Organizadora de Eventos

## Nome fictício: Mariana Costa
## Perfil: Professora universitária e organizadora de eventos acadêmicos
## Principal objetivo: Divulgar e gerenciar eventos acadêmicos de maneira simples e organizada.

### Descrição:

Marina é uma professora da Universidade de Brasília (UnB) que, além de ministrar aulas, participa da organização de palestras, workshops, seminários e outras atividades acadêmicas. 
Ela precisa divulgar essas oportunidades para os estudantes de maneira rápida e eficiente, garantindo que todos tenham acesso às informações necessárias.
No AgendaUnB, Marina utiliza a plataforma para cadastrar e publicar eventos públicos, informando datas, horários, locais e descrições. Além disso, pode atualizar as informações dos eventos sob sua responsabilidade, facilitando a comunicação entre professores e estudantes.
Marina valoriza uma interface intuitiva, formulários simples e ferramentas que permitam organizar suas publicações sem precisar recorrer a diferentes canais de comunicação.

### Necessidades principais:
- Cadastrar e divulgar eventos acadêmicos.
- Informar datas, horários, locais e descrições dos eventos.
- Editar e atualizar eventos sob sua responsabilidade.
- Facilitar a comunicação de atividades acadêmicas aos estudantes.

# 4. Persona 03 — Administrador da Plataforma

## Nome fictício: Rafael Oliveira
## Perfil: Administrador do sistema AgendaUnB
## Principal objetivo: Garantir a organização, a confiabilidade e o gerenciamento adequado da plataforma.

### Descrição:

Rafael é um profissional responsável pela administração e pelo gerenciamento do AgendaUnB, garantindo que a plataforma seja utilizada de maneira organizada e segura pela comunidade universitária.
No AgendaUnB, Rafael acompanha os eventos públicos cadastrados pelos professores e organizadores, verificando se as informações estão adequadas às regras estabelecidas para a plataforma. Seu papel envolve gerenciar publicações, acompanhar solicitações de divulgação e, conforme as permissões previstas no sistema, aprovar, rejeitar ou moderar eventos.
Seu principal objetivo é manter a plataforma confiável e organizada, permitindo que os estudantes encontrem informações relevantes e que os professores possam divulgar suas atividades acadêmicas de maneira adequada.
Rafael valoriza uma interface administrativa clara, com ferramentas que facilitem o acompanhamento das publicações, a identificação de problemas e o gerenciamento das informações.

### Necessidades principais:
- Gerenciar e acompanhar eventos públicos cadastrados.
- Verificar se as publicações seguem as regras da plataforma.
- Aprovar, rejeitar ou moderar eventos, conforme as permissões definidas.
- Manter as informações organizadas e atualizadas.
- Garantir uma experiência confiável para estudantes e professores.

# 5. Relação das personas com o sistema

As três personas representam necessidades complementares do AgendaUnB. O estudante utiliza a plataforma principalmente para descobrir e consultar eventos públicos, 
mas também pode criar eventos privados, cujo acesso é restrito ao próprio usuário. Já o professor/organizador possui as permissões necessárias para publicar e gerenciar eventos 
destinados à comunidade universitária. E o administrador é responsável por garantir que todas as funcionalidades estejam funcionando da melhor forma e garantir a segurança dos dados 
dos usuários da plataforma.

# 6. Observações

Os nomes e os perfis descritos são fictícios e devem ser tratados como hipóteses de persona. As características devem ser revisadas conforme a evolução dos requisitos 
e das funcionalidades do AgendaUnB. Todos esses detalhes estão organizados de uma forma visual em nosso Figma na seção "Persona Básica 1", "Persona Básica 2" e "Persona Básica 3".


# 7. Permissões na navegação atual

Estudantes gerenciam compromissos privados, salvam públicos aprovados e enviam sugestões. Professores e administradores publicam diretamente e moderam sugestões em `/sugestoes`. Apenas administradores acessam `/admin` para consultar usuários e alterar cargos. A persona organizadora reúne necessidades que, na implementação, são distribuídas entre esses dois papéis. Consulte [Painel administrativo](painel-administrativo.md).
