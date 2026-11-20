---
title: "Requisitos"
description: "Especificação de Requisitos de Software do projeto Agenda UnB, incluindo requisitos funcionais e não funcionais."
---

Este documento reúne os **Requisitos Funcionais (RF)** e **Requisitos Não Funcionais (RNF)** do projeto **Agenda UnB**, desenvolvido na disciplina de Métodos de Desenvolvimento de Software (MDS) da Universidade de Brasília (UnB) - 2026/2.

---

## 1. Requisitos Funcionais (RF)

| ID | Nome | Descrição |
| :-- | :-- | :-- |
| **RF01** | **Autenticação Local** | O sistema deve permitir que os usuários façam login e se autentiquem com e-mail (institucional ou pessoal) e senha criptografada. |
| **RF02** | **Cadastro de Usuários** | O sistema deve permitir o cadastro de novos usuários informando nome completo, e-mail e senha, com confirmação de senha. |
| **RF03** | **Autenticação Google (OAuth)** | O sistema deve permitir cadastro e login ágil com um clique utilizando contas Google. |
| **RF04** | **Categorização por Papel (Role)** | O sistema deve categorizar e conceder permissões ao usuário conforme seu perfil: Estudante (`student`), Professor (`professor`) ou Administrador (`admin`). Administradores possuem permissão exclusiva para alterar os papéis de outros usuários. |
| **RF05** | **Seleção de turma e envio de plano** | O usuário autenticado deve selecionar manualmente uma oferta do catálogo público do Followw e registrar vínculo autodeclarado. Na indisponibilidade da fonte, o sistema usa o último catálogo válido. Sem a oferta no catálogo disponível, bloqueia o envio do plano. Aceita PDF digital com texto selecionável ou texto bruto para processamento. |
| **RF06** | **Extração assistida de avaliações** | Extrair candidatos a provas e trabalhos com evidência de origem e indicação de datas incertas. O envio autoriza a análise do texto sanitizado automaticamente no servidor, que descarta o PDF após a leitura local. Avaliações entram na agenda após confirmação explícita, com seleção múltipla, confirmação em lote e correção de campos ambíguos. |
| **RF07** | **Revisão e colaboração por turma** | Planos começam privados. A primeira versão com candidatos de uma oferta é compartilhada quando o autor consulta ou confirma o resultado. Seguidores autenticados podem votar, importar para a própria agenda e publicar revisões de conteúdo compartilhado. Novas extrações ficam privadas até publicação. Autor ou admin podem retirar o compartilhamento ou avaliações individuais. Revisões e cópias já importadas preservam a própria visibilidade e titularidade. A interface distingue autoria de estudante, professor ou admin e procedência institucional comprovada. |
| **RF08** | **Visualização em Agenda / Calendário** | O sistema deve exibir todos os compromissos em uma interface visual de calendário (visões mensal, semanal ou lista). |
| **RF09** | **Gestão de Eventos Privados (CRUD)** | O sistema deve permitir ao usuário criar, editar e excluir eventos e prazos acadêmicos particulares em sua agenda pessoal. |
| **RF10** | **Submissão de eventos públicos** | Estudantes podem sugerir eventos públicos para moderação. Professor e admin podem publicar eventos diretamente. |
| **RF11** | **Moderação e administração** | Professores e administradores podem consultar, aprovar ou rejeitar sugestões de eventos. A rejeição exige justificativa. A gestão de papéis e categorias cabe exclusivamente a administradores. |
| **RF12** | **Evento público na agenda e acesso à fonte** | O sistema deve oferecer duas ações independentes. Adicionar aos meus eventos salva um vínculo na agenda pessoal do usuário. Conferir evento abre o link original, quando disponível, e conta o redirecionamento em uma métrica agregada. A inscrição, quando exigida, ocorre no canal do organizador. |
| **RF13** | **Remoção de evento público da agenda** | O usuário deve poder remover seu próprio vínculo com um evento público. A remoção é idempotente e cancela lembretes futuros associados ao vínculo. |
| **RF14** | **Resumo e Detalhes do Evento** | O sistema deve fornecer uma página/modal com a descrição completa do evento, data, horário, local e link externo oficial da organização. |
| **RF15** | **Divulgação Multi-campus** | O sistema deve organizar e divulgar eventos que ocorram em todos os campi da UnB (Darcy Ribeiro, FGA/FCTE, FCE/FCTS, FUP e FAL). |
| **RF16** | **Coleta de eventos institucionais** | A primeira fonte é a Agenda UnB Notícias. O sistema deve coletar periodicamente, deduplicar e publicar automaticamente eventos completos da fonte. Itens ambíguos, incompletos ou possivelmente duplicados seguem para revisão. |
| **RF17** | **Lembretes na plataforma** | O sistema deve persistir um lembrete 24 horas antes do início para cada evento da agenda do próprio usuário, incluindo compromissos privados e eventos públicos adicionados. O usuário pode consultar o aviso ao voltar à plataforma. |
| **RF18** | **Histórico da agenda pessoal** | Retirado do escopo da R2. Meus Eventos usa a lista e o calendário da agenda, com filtro por período. |
| **RF19** | **Filtros e Busca de Eventos** | O sistema deve permitir filtrar e classificar eventos por categoria (prova, trabalho, palestra, cultural), campus/instituto e intervalo de datas. |
| **RF20** | **Alternância de Tema (Dark / Light)** | O sistema deve disponibilizar alternância de tema visual entre modo escuro (_Dark Mode_) e modo claro (_Light Mode_). |
| **RF21** | **Exportação de calendário** | O usuário deve poder selecionar período e eventos da própria agenda e exportá-los diretamente para uma agenda secundária Agenda UnB pela Google Calendar API. A exportação direta exige consentimento adicional do Calendar e conta Google com e-mail verificado correspondente ao e-mail confirmado da Agenda UnB. A conexão também está disponível para quem entrou com e-mail e senha. |

---

## 2. Requisitos Não Funcionais (RNF)

Os requisitos não funcionais estão divididos de acordo com a norma **ISO/IEC 25010** e modelo **FURPS+**, definindo métricas testáveis e critérios de qualidade:

### 2.1 Segurança (Security)

- **RNF01 — Criptografia de Credenciais:** Todas as senhas de usuários devem ser armazenadas utilizando algoritmos de derivação de chave e hash unidirecional seguro (ex: `bcrypt` com _cost factor_ ≥ 10 ou `Argon2`).
- **RNF02 — Privacidade dos dados acadêmicos.** Descartar o PDF original após a extração local, inclusive em falha. Aplicar minimização automática e autorização específica antes do envio do texto ao provedor. Restringir a agenda e os planos ao acesso autorizado. Versões compartilhadas ficam disponíveis aos seguidores autenticados conforme RF07.
- **RNF03 — Comunicação Criptografada:** Todo o tráfego de dados entre a aplicação web, a API de backend e o banco de dados deve utilizar criptografia TLS/HTTPS.
- **RNF04 —** Controle de acesso (RBAC). Professor e admin moderam eventos. Somente admin gerencia papéis e categorias. API e políticas de dados devem verificar papel, propriedade e visibilidade em cada operação protegida.

### 2.2 Desempenho e Eficiência (Performance)

- **RNF05 — Tempo de Resposta da API:** Pelo menos 95% das requisições de consulta de eventos (`GET /events`) devem ser respondidas pelo servidor em até **300 milissegundos** sob condições normais de uso.
- **RNF06 — Desempenho da extração.** A meta é inferior a **20 segundos** do início do envio à disponibilização de candidatos de um plano de até 10 páginas. Medir transferência, validação, preparação local, fila e processamento externo. Exibir o andamento sem impedir outras ações.

### 2.3 Usabilidade e Acessibilidade (Usability)

- **RNF07 — Design Responsivo:** A interface gráfica deve ser fluida e adaptável a telas de smartphones (largura mínima de 360px), tablets e desktops convencionais.
- **RNF08 — Contraste e Acessibilidade:** As cores utilizadas nos temas claro e escuro devem cumprir os critérios de taxa de contraste mínimo estipulados pelas diretrizes WCAG 2.1 (nível AA).
- **RNF09 — Feedback Visual de Operações:** O sistema deve fornecer mensagens claras e informativas (_toasts_ / notificações de tela) sobre o resultado de qualquer ação realizada pelo usuário (sucesso no envio, erros de validação, etc.).

### 2.4 Confiabilidade e Tolerância a Falhas (Reliability)

- **RNF10 — Resiliência no Upload de Arquivos:** Se um arquivo enviado estiver ilegível, protegido por senha ou corrompido, o sistema não deve entrar em estado de exceção, devendo apresentar instruções claras de correção ao usuário.
- **RNF11 —** Isolamento de falhas do Followw. A indisponibilidade do catálogo Followw não deve impedir a navegação nem o uso da agenda existente. Este requisito não garante funcionamento sem Auth, banco ou backend, nem estabelece garantia geral para outros provedores.

### 2.5 Compatibilidade e Manutenibilidade (Compatibility & Maintainability)

- **RNF12 — Compatibilidade entre Navegadores:** A aplicação deve ser homologada e funcional nas versões atuais dos principais navegadores web do mercado (Google Chrome, Mozilla Firefox, Microsoft Edge e Safari).
- **RNF13 — Qualidade de Código e Padrões:** O desenvolvimento deve seguir rigorosamente as regras estipuladas em [padrões](/produto/padroes) e manter cobertura de testes automatizados unitários e de integração nas funcionalidades de negócio essenciais.
