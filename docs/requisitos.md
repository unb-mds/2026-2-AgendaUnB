# 📋 Especificação de Requisitos de Software — Agenda UnB

Este documento reúne os **Requisitos Funcionais (RF)** e **Requisitos Não Funcionais (RNF)** do projeto **Agenda UnB**, desenvolvido na disciplina de Métodos de Desenvolvimento de Software (MDS) da Universidade de Brasília (UnB) - 2026/2.

---

## 1. Requisitos Funcionais (RF)

| ID | Nome | Descrição |
| :--- | :--- | :--- |
| **RF01** | **Autenticação Local** | O sistema deve permitir que os usuários façam login e se autentiquem com e-mail (institucional ou pessoal) e senha criptografada. |
| **RF02** | **Cadastro de Usuários** | O sistema deve permitir o cadastro de novos usuários informando nome completo, e-mail e senha, com confirmação de senha. |
| **RF03** | **Autenticação Google (OAuth)** | O sistema deve permitir cadastro e login ágil com um clique utilizando contas Google. |
| **RF04** | **Categorização por Papel (Role)** | O sistema deve categorizar e conceder permissões ao usuário conforme seu perfil: Estudante (`student`), Professor (`professor`) ou Administrador (`admin`). |
| **RF05** | **Upload de Planos de Ensino** | O sistema deve permitir que os usuários enviem arquivos de planos de ensino em formatos suportados (PDF ou texto bruto). |
| **RF06** | **Extração Automática de Datas** | O sistema deve processar os planos de ensino enviados e extrair automaticamente datas de provas, entregas de trabalhos e seminários acadêmicos. |
| **RF07** | **Revisão de Dados Extraídos** | O sistema deve apresentar uma prévia das datas acadêmicas identificadas para que o estudante possa conferir antes de salvá-las na agenda. |
| **RF08** | **Visualização em Agenda / Calendário** | O sistema deve exibir todos os compromissos em uma interface visual de calendário (visões mensal, semanal ou lista). |
| **RF09** | **Gestão de Eventos Privados (CRUD)** | O sistema deve permitir ao usuário criar, editar e excluir eventos e prazos acadêmicos particulares em sua agenda pessoal. |
| **RF10** | **Submissão de Eventos Públicos** | O sistema deve permitir que usuários submetam propostas de eventos públicos e acadêmicos para divulgação na plataforma. |
| **RF11** | **Moderação de Eventos (Painel Admin)** | O sistema deve disponibilizar aos Administradores uma área para aprovar, rejeitar ou editar eventos públicos submetidos antes de sua publicação geral. |
| **RF12** | **Inscrição Direta em Eventos** | O sistema deve permitir que os usuários se inscrevam diretamente em eventos públicos do campus com apenas um clique. |
| **RF13** | **Cancelamento de Inscrição** | O sistema deve permitir que o usuário cancele a qualquer momento sua inscrição prévia em um evento. |
| **RF14** | **Resumo e Detalhes do Evento** | O sistema deve fornecer uma página/modal com a descrição completa do evento, data, horário, local e link externo oficial da organização. |
| **RF15** | **Divulgação Multi-campus** | O sistema deve organizar e divulgar eventos que ocorram em todos os campi da UnB (Darcy Ribeiro, FGA, FCE e FUP). |
| **RF16** | **Coleta Automática Externa (Web Scraping)** | O sistema deve possuir rotinas para coletar e importar automaticamente eventos divulgados pela UnB através do SIGAA, portais de notícias e redes sociais. |
| **RF17** | **Notificações de Proximidade** | O sistema deve notificar o usuário com antecedência programada quando a data de uma prova, trabalho ou evento inscrito estiver se aproximando. |
| **RF18** | **Histórico de Participação** | O sistema deve disponibilizar um histórico dos eventos dos quais o usuário participou, separando eventos públicos e privados. |
| **RF19** | **Filtros e Busca de Eventos** | O sistema deve permitir filtrar e classificar eventos por categoria (prova, trabalho, palestra, cultural), campus/instituto e intervalo de datas. |
| **RF20** | **Alternância de Tema (Dark / Light)** | O sistema deve disponibilizar alternância de tema visual entre modo escuro (*Dark Mode*) e modo claro (*Light Mode*). |
| **RF21** | **Exportação de Calendário** | O sistema deve permitir a exportação dos eventos da agenda para arquivo `.ics`, permitindo sincronização com Google Calendar, Apple Calendar e Outlook. |

---

## 2. Requisitos Não Funcionais (RNF)

Os requisitos não funcionais estão divididos de acordo com a norma **ISO/IEC 25010** e modelo **FURPS+**, definindo métricas testáveis e critérios de qualidade:

### 🔒 2.1 Segurança (Security)
* **RNF01 — Criptografia de Credenciais:** Todas as senhas de usuários devem ser armazenadas utilizando algoritmos de derivação de chave e hash unidirecional seguro (ex: `bcrypt` com *cost factor* $\ge 10$ ou `Argon2`).
* **RNF02 — Privacidade dos Dados Acadêmicos (LGPD):** Planos de ensino, notas e eventos privados dos estudantes são estritamente confidenciais e não podem ser acessíveis por terceiros ou expostos sem autenticação.
* **RNF03 — Comunicação Criptografada:** Todo o tráfego de dados entre a aplicação web, a API de backend e o banco de dados deve utilizar criptografia TLS/HTTPS.
* **RNF04 — Controle de Acesso (RBAC):** O acesso a rotas administrativas (moderação de eventos, gestão de categorias) deve ser restrito exclusivamente a usuários com a atribuição de Administrador (`admin`).

### ⚡ 2.2 Desempenho e Eficiência (Performance)
* **RNF05 — Tempo de Resposta da API:** Pelo menos 95% das requisições de consulta de eventos (`GET /events`) devem ser respondidas pelo servidor em até **300 milissegundos** sob condições normais de uso.
* **RNF06 — Processamento Assíncrono do Parser:** O processamento de um plano de ensino de até 10 páginas deve ser concluído em menos de **20 segundos**, exibindo um indicador visual de progresso na interface para não bloquear o usuário.

### 📱 2.3 Usabilidade e Acessibilidade (Usability)
* **RNF07 — Design Responsivo:** A interface gráfica deve ser fluida e adaptável a telas de smartphones (largura mínima de 360px), tablets e desktops convencionais.
* **RNF08 — Contraste e Acessibilidade:** As cores utilizadas nos temas claro e escuro devem cumprir os critérios de taxa de contraste mínimo estipulados pelas diretrizes WCAG 2.1 (nível AA).
* **RNF09 — Feedback Visual de Operações:** O sistema deve fornecer mensagens claras e informativas (*toasts* / notificações de tela) sobre o resultado de qualquer ação realizada pelo usuário (sucesso no envio, erros de validação, etc.).

### 🛡️ 2.4 Confiabilidade e Tolerância a Falhas (Reliability)
* **RNF10 — Resiliência no Upload de Arquivos:** Se um arquivo enviado estiver ilegível, protegido por senha ou corrompido, o sistema não deve entrar em estado de exceção, devendo apresentar instruções claras de correção ao usuário.
* **RNF11 — Isolamento do Web Scraping:** Uma falha ou indisponibilidade temporária na coleta de dados de fontes externas (SIGAA ou Instagram) não pode afetar a navegação ou o funcionamento da agenda existente.

### 🧩 2.5 Compatibilidade e Manutenibilidade (Compatibility & Maintainability)
* **RNF12 — Compatibilidade entre Navegadores:** A aplicação deve ser homologada e funcional nas versões atuais dos principais navegadores web do mercado (Google Chrome, Mozilla Firefox, Microsoft Edge e Safari).
* **RNF13 — Qualidade de Código e Padrões:** O desenvolvimento deve seguir rigorosamente as regras estipuladas no [`padrao.md`](file:///c:/Users/Thomaz/Documents/APC/MDS/G8-2026-2/padrao.md) e manter cobertura de testes automatizados unitários e de integração nas funcionalidades de negócio essenciais.
