# 1. Objetivo

As personas básicas do AgendaUnB representam os principais perfis de usuários da plataforma. Elas auxiliam na compreensão das necessidades, dos objetivos e das dificuldades dos usuários, orientando as decisões de design, usabilidade e desenvolvimento do sistema.

Foram definidos dois perfis principais: o estudante, que consulta eventos públicos e pode criar eventos privados, e o organizador de eventos/administrador, responsável pela publicação e pelo gerenciamento de eventos destinados à comunidade universitária.

# 2. Persona 01 — Estudante

## Nome fictício: Pedro Martins
## Perfil: Estudante universitário
## Principal objetivo: Descobrir e acompanhar eventos de seu interesse na universidade.

### Descrição:

Pedro é um estudante universitário interessado em participar de palestras, workshops, atividades acadêmicas e eventos de integração. 
Ele tem receio de perder oportunidades por não ficar sabendo dos eventos a tempo e, por isso, procura uma plataforma centralizada, intuitiva e atualizada. 
No AgendaUnB, Pedro pode visualizar os eventos públicos publicados por organizadores e administradores, consultar informações como datas, horários, locais e descrições, além de criar eventos
privados para uso pessoal, acessíveis somente a ele. Ele valoriza uma interface responsiva, informações claras e uma navegação simples que facilite a descoberta de novas atividades.

### Necessidades principais:
- Consultar os eventos públicos disponíveis.
- Visualizar os detalhes de cada evento.
- Encontrar oportunidades acadêmicas e de integração.
- Criar e consultar seus próprios eventos privados.
- Salvar eventos públicos na agenda e consultar lista ou calendário.
- Sugerir atividades e acompanhar a decisão pelo sino de notificações.

# 3. Persona 02 — Organizador de Eventos / Administrador

## Nome fictício: Mariana Costa
## Perfil: Organizadora de eventos e administradora da plataforma
## Principal objetivo: Divulgar e gerenciar eventos de maneira simples e organizada.

### Descrição:

Mariana é responsável pela organização e divulgação de atividades acadêmicas, como palestras, workshops e encontros universitários. 
Ela precisa disponibilizar informações confiáveis e atualizadas para que os estudantes conheçam os eventos oferecidos pela universidade. 
No AgendaUnB, Mariana utiliza as funcionalidades administrativas para cadastrar, publicar, editar e gerenciar eventos destinados à comunidade universitária, 
conforme as permissões do sistema. Ela busca uma plataforma intuitiva, com formulários objetivos e processos simples, que facilite a divulgação das atividades e 
reduza o esforço necessário para manter as informações organizadas.

### Necessidades principais:
- Cadastrar e publicar eventos públicos.
- Informar os detalhes necessários de cada evento.
- Editar informações e manter as publicações atualizadas.
- Gerenciar os eventos de acordo com suas permissões.

# 4. Relação das personas com o sistema

As duas personas representam necessidades complementares do AgendaUnB. O estudante utiliza a plataforma principalmente para descobrir e consultar eventos públicos, 
mas também pode criar eventos privados, cujo acesso é restrito ao próprio usuário. Já o organizador/administrador possui as permissões necessárias para publicar e gerenciar eventos 
destinados à comunidade universitária.

# 5. Observações

Os nomes e os perfis descritos são fictícios e devem ser tratados como hipóteses de persona. As características devem ser revisadas conforme a evolução dos requisitos 
e das funcionalidades do AgendaUnB. Todos esses detalhes estão organizados de uma forma visual em nosso Figma na seção "Persona Básica 1" e "Persona Básica 2".


# 6. Permissões na navegação atual

Estudantes gerenciam compromissos privados, salvam públicos aprovados e enviam sugestões. Professores e administradores publicam diretamente e moderam sugestões em `/sugestoes`. Apenas administradores acessam `/admin` para consultar usuários e alterar cargos. A persona organizadora reúne necessidades que, na implementação, são distribuídas entre esses dois papéis. Consulte [Painel administrativo](painel-administrativo.md).
