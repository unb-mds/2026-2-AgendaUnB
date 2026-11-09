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
| **RF06** | **Extração assistida de avaliações** | O sistema deve extrair apenas candidatos a provas e trabalhos, com evidência de origem e indicação de datas incertas. Antes de enviar texto minimizado ao provedor, exige revisão e autorização específica. O PDF é temporário e deve ser descartado após a extração local do texto. A agenda recebe avaliações efetivas apenas após confirmação humana dos candidatos. Permitir seleção múltipla e confirmação em lote, com correção focada nos campos ambíguos. |
| **RF07** | **Revisão e colaboração por turma** | Planos começam privados. O autor pode compartilhar voluntariamente uma versão revisada na turma. Autor, professor e admin podem editar conforme as regras de visibilidade. Professor e admin podem publicar diretamente revisões de conteúdo já compartilhado, sem aprovação adicional do autor original; isso não autoriza publicar conteúdo privado alheio. Seguidores autenticados podem consultar a versão compartilhada, votar uma vez por candidato e versão e importar avaliações confirmadas para a própria agenda. Retirar a versão original não retira revisões compartilhadas nem avaliações já importadas. Revisões por professor/admin herdam a procedência institucional previamente validada, com rastreabilidade da origem e da revisão. Distinguir contribuição estudantil, envio por perfil professor e origem institucional comprovada. |
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
| **RF18** | **Histórico da agenda pessoal** | O sistema deve exibir separadamente eventos públicos passados ainda adicionados à agenda e compromissos privados passados do próprio usuário. Redirecionamentos à fonte são uma métrica agregada e ficam fora do histórico pessoal. Inscrição externa e presença dependem do organizador. |
| **RF19** | **Filtros e Busca de Eventos** | O sistema deve permitir filtrar e classificar eventos por categoria (prova, trabalho, palestra, cultural), campus/instituto e intervalo de datas. |
| **RF20** | **Alternância de Tema (Dark / Light)** | O sistema deve disponibilizar alternância de tema visual entre modo escuro (_Dark Mode_) e modo claro (_Light Mode_). |
| **RF21** | **Exportação de calendário** | O usuário deve poder selecionar período e eventos da própria agenda e exportá-los diretamente para uma agenda secundária Agenda UnB pela Google Calendar API. A autorização OAuth é adicional e o e-mail Google verificado deve corresponder ao e-mail verificado da conta Agenda UnB. O sistema deve permitir reexportação explícita e idempotente, recuperação por item após falha parcial e desconexão. ICS complementa a compatibilidade com Apple Calendar e Outlook. Sincronização automática fica fora da Release 2. |

---

## 2. Requisitos Não Funcionais (RNF)

Os requisitos não funcionais estão divididos de acordo com a norma **ISO/IEC 25010** e modelo **FURPS+**, definindo métricas testáveis e critérios de qualidade:

### 2.1 Segurança (Security)

- **RNF01 — Criptografia de Credenciais:** Todas as senhas de usuários devem ser armazenadas utilizando algoritmos de derivação de chave e hash unidirecional seguro (ex: `bcrypt` com _cost factor_ ≥ 10 ou `Argon2`).
- **RNF02 —** Privacidade dos dados acadêmicos. O PDF original deve ser descartado após a extração local, inclusive em caso de falha. Texto, candidatos e agenda pessoal ficam sob acesso autorizado. Apenas conteúdo revisado é compartilhado voluntariamente com seguidores autenticados da oferta. O texto enviado ao provedor depende de autorização específica e minimização.
- **RNF03 — Comunicação Criptografada:** Todo o tráfego de dados entre a aplicação web, a API de backend e o banco de dados deve utilizar criptografia TLS/HTTPS.
- **RNF04 —** Controle de acesso (RBAC). Professor e admin moderam eventos. Somente admin gerencia papéis e categorias. API e políticas de dados devem verificar papel, propriedade e visibilidade em cada operação protegida.

### 2.2 Desempenho e Eficiência (Performance)

- **RNF05 — Tempo de Resposta da API:** Pelo menos 95% das requisições de consulta de eventos (`GET /events`) devem ser respondidas pelo servidor em até **300 milissegundos** sob condições normais de uso.
- **RNF06 — Processamento Assíncrono do Parser:** O tempo do upload até os candidatos prontos para revisão, para um plano de até 10 páginas, deve ser inferior a **20 segundos**, descontando somente a espera pelas ações humanas de revisão e autorização. Transferência, validação, extração local, fila e processamento externo integram a medição. Exibir progresso na interface sem bloquear o usuário.

### 2.3 Usabilidade e Acessibilidade (Usability)

- **RNF07 — Design Responsivo:** A interface gráfica deve ser fluida e adaptável a telas de smartphones (largura mínima de 360px), tablets e desktops convencionais.
- **RNF08 — Contraste e Acessibilidade:** As cores utilizadas nos temas claro e escuro devem cumprir os critérios de taxa de contraste mínimo estipulados pelas diretrizes WCAG 2.1 (nível AA).
- **RNF09 — Feedback Visual de Operações:** O sistema deve fornecer mensagens claras e informativas (_toasts_ / notificações de tela) sobre o resultado de qualquer ação realizada pelo usuário (sucesso no envio, erros de validação, etc.).

### 2.4 Confiabilidade e Tolerância a Falhas (Reliability)

- **RNF10 — Resiliência no Upload de Arquivos:** Se um arquivo enviado estiver ilegível, protegido por senha ou corrompido, o sistema não deve entrar em estado de exceção, devendo apresentar instruções claras de correção ao usuário.
- **RNF11 —** Isolamento de falhas do Followw. A indisponibilidade do catálogo Followw não deve impedir a navegação nem o uso da agenda existente. Este requisito não garante funcionamento sem Auth, banco ou backend, nem estabelece garantia geral para outros provedores.

### 2.5 Compatibilidade e Manutenibilidade (Compatibility & Maintainability)

- **RNF12 — Compatibilidade entre Navegadores:** A aplicação deve ser homologada e funcional nas versões atuais dos principais navegadores web do mercado (Google Chrome, Mozilla Firefox, Microsoft Edge e Safari).
- **RNF13 — Qualidade de Código e Padrões:** O desenvolvimento deve seguir rigorosamente as regras estipuladas em [padrões](padroes.md) e manter cobertura de testes automatizados unitários e de integração nas funcionalidades de negócio essenciais.
