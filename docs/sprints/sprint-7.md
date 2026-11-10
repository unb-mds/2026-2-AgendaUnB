---
title: "Sprint 07 - Release 2"
sidebarTitle: "Sprint 7"
---

# Sprint 7

Planejamento aprovado para 07–15/11/2026. Entrega final em 25/11/2026. As tarefas abaixo representam trabalho planejado e dependem das evidências de aceite para conclusão.

## Decisões da entrega

- Seleção manual de turmas pelo catálogo público Followw, com vínculo autodeclarado.
- Planos privados por padrão e compartilhamento voluntário de versões revisadas.
- IA limitada a provas e trabalhos, com revisão do texto antes do envio e confirmação antes da criação de eventos.
- Coleta inicial pela Agenda UnB Notícias e participação registrada localmente.
- Professores e administradores moderam eventos. Administradores gerenciam papéis e categorias.
- Lembretes persistidos na plataforma e exportação direta ao Google Agenda via Calendar API com consentimento adicional, usando agenda secundária criada pelo aplicativo. ICS permanece como opção complementar para Apple Calendar/Outlook.
- Primeira URL Vercel até 12/11 e ambiente integrado até 15/11. Congelamento funcional em 20/11, homologação até 23/11, ensaio em 24/11 e aceite em 25/11.

## Organização

F identifica frontend, B backend e D dados. A numeração é independente por área e sprint. Para atividades transversais, a área corresponde à frente coordenadora. Prioridades foram atribuídas considerando dependências e marcos da entrega. Cada issue tem até dois responsáveis formais, com apoios adicionais registrados no conteúdo.

[Milestone da Sprint 7](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)

## Issues planejadas

### S7-B01 - Concluir extração assíncrona de provas e trabalhos com IA

[Issue #51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51)

#### Objetivo

Concluir a extração da antiga S6-B01. Transformar texto de planos em candidatos privados a provas e trabalhos, sujeitos à confirmação do aluno.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 09–13/11/2026
- **Responsável principal** @heitormontt
- **Corresponsável** @pontesluis
- **Dependências** S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)), S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)) e S7-D01 ([#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)). Reaproveitar [#40](https://github.com/unb-mds/2026-2-AgendaUnB/issues/40), [#53](https://github.com/unb-mds/2026-2-AgendaUnB/issues/53) e [#54](https://github.com/unb-mds/2026-2-AgendaUnB/issues/54). Integração da interface em S7-F03 ([#73](https://github.com/unb-mds/2026-2-AgendaUnB/issues/73)).
- **Requisitos** RF05, RF06, RNF02, RNF06 e RNF10.

#### Tasks

- [x] Reaproveitar as validações de PDF digital de até 10 MB e 10 páginas, extrair texto no servidor com referência de página quando disponível e aceitar texto bruto com limite documentado.
- [x] Extrair localmente e descartar o PDF original/temporários ao fim da preparação, inclusive em falha. Minimizar identificadores, mostrar o texto exato e exigir autorização antes de enviar somente o trecho aprovado ao Gemini.
- [x] Documentar provedor/modelo, configuração por ambiente, limite de custo por arquivo, timeout e tentativas limitadas. Manter credenciais no servidor e processar em job persistido e recuperável.
- [x] Validar saída estruturada com título, tipo prova/trabalho, data/horário quando disponíveis, ambiguidade e trecho/página de origem. Tratar o texto como dado, sem execução de instruções, navegação ou ferramentas acionadas pelo documento.
- [x] Persistir candidatos privados sem criar eventos definitivos. Tratar falha, 429, timeout, resultado vazio e reprocessamento, sem registrar PDF ou texto integral em logs.
- [ ] Oferecer organização manual para PDF escaneado ou conteúdo ainda pessoal/confidencial. Habilitar o provedor em produção após validação de termos e elegibilidade em S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)).

#### Critérios de aceite

- [x] Com amostras anonimizadas e resultado esperado, demonstrar que só provas e trabalhos viram candidatos. Registrar acertos, omissões e datas inventadas. Aulas e referências bibliográficas ficam fora, e datas incompletas exigem correção sem inferência de ano ou horário.
- [x] Demonstrar retomada e retry sem duplicar candidatos ativos, além de estados recuperáveis para erros e ausência de avaliações.
- [x] Medir RNF06 com corpus de até 10 páginas. Incluir fila e provedor, separar tempo humano de revisão e documentar o tempo inicial de preparação. Verificar a meta de menos de 20 s e registrar desvios.

#### Observações

A minimização por regex tem alcance limitado. Enviar conteúdo ao serviço gratuito somente se o texto aprovado atender às regras aplicáveis de dados pessoais e confidenciais.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


**Evidência local em 10/11/2026:** [contrato e métricas](../processamento-planos-s7.md),
[revisão técnica e pendências](../s7-b01-validacao.md). O caminho manual e o bloqueio
operacional estão implementados; produção continua pendente de S7-B02, implantação
validada e revisão humana. Os checks acima representam implementação/validação
local, sem aprovação automática de dados reais ou fechamento das dependências.

### S7-F01 - Consolidar requisitos, decisões e contratos da entrega

[Issue #67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)

#### Objetivo

Fixar as decisões da Release 2 e publicar contratos que permitam frontend, backend e dados trabalharem em paralelo.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 07–08/11/2026
- **Responsável principal** @Thomas4ugust0
- **Apoio adicional** Toda a equipe valida os contratos e critérios das suas frentes.
- **Dependências** Nenhuma.
- **Requisitos** RF05–RF07, RF11, RF12, RF18, RF21, RNF02, RNF04 e RNF13. A matriz cobre RF01–RF21 e RNF01–RNF13.

#### Tasks

- [ ] Definir RF21 como exportação direta, acionada pelo usuário, para uma agenda secundária “Agenda UnB” via Google Calendar API. Registrar consentimento adicional, contratos de conexão/desconexão, mapeamento de IDs e reexportação idempotente. Manter ICS como compatibilidade com Apple Calendar/Outlook. A sincronização automática bidirecional fica fora do recorte.
- [ ] Atualizar a visão e os requisitos canônicos, incluindo as funcionalidades antecipadas para esta entrega.
- [ ] Revisar RF05/RF06 para substituir atestado de matrícula por seleção manual de oferta do catálogo público do Followw. Registrar vínculo autodeclarado e separar o catálogo de matrícula, notas, avisos privados e login Followw/SIGAA.
- [ ] Revisar RF07/RNF02 para definir planos privados por padrão e compartilhamento voluntário após revisão. Distinguir contribuição de estudante, envio por perfil professor e origem institucional comprovada.
- [ ] Revisar RF11/RNF04 para delimitar moderação por professor/admin e gestão de papéis e categorias por admin. Revisar RF12/RF18 para distinguir interesse/participação local, inscrição externa e comprovação de presença.
- [ ] Atualizar RF21 para exportação direta pela Google Calendar API com autorização adicional. Registrar o escopo de lembretes na plataforma, coleta inicial pela Agenda UnB Notícias e extração de provas/trabalhos com confirmação humana.
- [ ] Definir contratos de turma, plano/versão, candidato, evento com intervalo/dia inteiro, participação e lembrete. Harmonizar estados de processamento entre backend e frontend e planejar migração quando necessária.

#### Critérios de aceite

- [ ] Publicar matriz RF01–RF21 e RNF01–RNF13 com issue, responsável, critério verificável e estado.
- [ ] Documentar exemplos de payload e erros, identidade canônica de turma, fuso `America/Sao_Paulo`, datas ambíguas e permissões.
- [ ] Registrar exceções existentes de nomenclatura do banco e manter renomeações gerais fora do escopo.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-B02 - Validar infraestrutura gratuita, integrações e CI

[Issue #68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)

#### Objetivo

Demonstrar a viabilidade de Followw público, SMTP, Gemini e jobs persistidos dentro do orçamento zero, com CI reproduzível.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** Provas até 08/11/2026. Conclusão até 10/11/2026.
- **Responsável principal** @pontesluis
- **Corresponsável** @heitormontt
- **Apoio adicional** Thomas apoia a integração de autenticação e o alinhamento dos contratos.
- **Dependências** Pode começar em paralelo a S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)).
- **Requisitos** RF16, RNF03, RNF11 e RNF13.

#### Tasks

- [ ] Validar Google Calendar API habilitada, escopo `https://www.googleapis.com/auth/calendar.app.created`, consentimento OAuth, usuários de teste, condições de publicação/verificação, cotas e renovação do token Google. Criar agenda secundária e evento sintético, demonstrar revogação e registrar requisitos de liberação pública e bloqueios antes da integração em [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82).
- [ ] Executar chamadas reais aos endpoints públicos Followw e registrar paginação, limites e cobertura observada.
- [ ] Demonstrar envio de confirmação e recuperação via SMTP para endereço fora da equipe Supabase.
- [ ] Chamar o modelo Gemini escolhido com texto sintético. Conferir cotas, termos de conteúdo e condições de elegibilidade, inclusive idade do público universitário.
- [ ] Executar uma tarefa persistida na hospedagem candidata e demonstrar retomada após reinício. Definir onde rodam FastAPI, worker, coletor e scheduler e registrar limites e custo efetivo.
- [ ] Configurar fila/tabela persistida e processamento recuperável, limites de cota, tratamento de 429/timeout, segredos de servidor e logs sem conteúdo acadêmico.
- [ ] Configurar checks essenciais de frontend, backend e migrations no CI com os comandos existentes.

#### Critérios de aceite

- [ ] Anexar evidência das cinco provas com configuração reproduzível. Credenciais permanecem fora do frontend e do repositório.
- [ ] Comprovar retomada após reinício, tratamento de limite/timeout e migrations tanto em base limpa quanto na atualização da base existente.
- [ ] Demonstrar SMTP, elegibilidade do Gemini e hospedagem sem custo, ou registrar imediatamente o requisito bloqueado e a alternativa escolhida.

#### Observações

Validar SMTP próprio para destinatários externos. Consultar a documentação de [SMTP do Supabase](https://supabase.com/docs/guides/auth/auth-smtp), os [termos do Gemini](https://ai.google.dev/gemini-api/terms) e a [arquitetura do Followw](https://docs.followw.app/arquitetura) durante as provas. O consentimento do usuário não dispensa as condições do provedor.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-D01 - Modelar turmas, vínculos, versões e isolamento dos planos

[Issue #69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)

#### Objetivo

Evoluir o esquema de planos existentes para associar ofertas de turma, versões e vínculos preservando o isolamento de dados.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 08–10/11/2026
- **Responsável principal** @felipecduque7
- **Corresponsável** @marrathomaz
- **Apoio adicional** Luis apoia migrations e validação da infraestrutura de dados.
- **Dependências** Contrato de S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)). Reaproveitar [#43](https://github.com/unb-mds/2026-2-AgendaUnB/issues/43), [#53](https://github.com/unb-mds/2026-2-AgendaUnB/issues/53) e [#54](https://github.com/unb-mds/2026-2-AgendaUnB/issues/54).
- **Requisitos** RF05, RF07, RNF02 e RNF04.

#### Tasks

- [ ] Modelar a oferta canônica com período, origem pública e data de atualização. Preferir identificador de disciplina da origem e, na falta dele, combinar código, número da turma, período e unidade/nível quando necessário.
- [ ] Criar vínculo único entre usuário e oferta. Associar plano e versão à oferta com autoria, visibilidade privada/compartilhada e candidatos com evidência.
- [ ] Preparar chaves e índices de importação por usuário/candidato/versão. Alinhar ORM, migrations, constraints, RLS e autorização no Storage.

#### Critérios de aceite

- [ ] Executar migrations em dados existentes e demonstrar compatibilidade com o ORM.
- [ ] Seguir uma turma repetidamente mantém um vínculo, e ofertas de semestres diferentes permanecem distintas.
- [ ] Usuário B não acessa PDF, texto ou candidatos privados de A por API, banco ou Storage. Arquivos são privados por padrão e as verificações valem para requisições diretas.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-B03 - Integrar o catálogo público do Followw no backend

[Issue #70](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70)

#### Objetivo

Expor o catálogo público de turmas do Followw para seleção manual, com cache resiliente.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 08–11/11/2026
- **Responsável principal** @heitormontt
- **Corresponsável** @felipecduque7
- **Dependências** Contratos de S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)), endpoints validados em S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)) e persistência de S7-D01 ([#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)) para a integração final.
- **Requisitos** RF05 e RNF11.

#### Tasks

- [ ] Implementar adaptador de servidor com lista permitida de endpoints públicos, timeout e tentativas limitadas. Usar `/public/classrooms/units`, `/public/classrooms` e consultas filtradas a `/public/subjects` conforme a prova.
- [ ] Consultar por unidade, período e código respeitando paginação e limites reais. Evitar busca vazia de disciplinas que acione recomendação autenticada. Restringir a sincronização ao servidor e a chamadas públicas sem token de usuário.
- [ ] Persistir cache e data de atualização. Devolver à interface a indicação de catálogo desatualizado quando a fonte estiver indisponível.

#### Critérios de aceite

- [ ] Demonstrar busca real por disciplina, unidade e período, com identidade estável em sincronizações repetidas.
- [ ] Simular indisponibilidade e confirmar preservação das turmas seguidas e do último catálogo válido.
- [ ] Verificar que só endpoints públicos foram chamados e documentar a cobertura efetivamente observada.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-F02 - Implementar catálogo e “Minhas turmas” na interface

[Issue #71](https://github.com/unb-mds/2026-2-AgendaUnB/issues/71)

#### Objetivo

Permitir ao usuário escolher manualmente a oferta correta e usar suas turmas na jornada de planos de ensino.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 09–12/11/2026
- **Responsável principal** @Thomas4ugust0
- **Corresponsável** @Bielziin07
- **Dependências** S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)). Integração real com S7-D01 ([#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)) e S7-B03 ([#70](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70)).
- **Requisitos** RF05, RNF07, RNF08 e RNF09.

#### Tasks

- [ ] Criar busca por disciplina e seleção de oferta com número, semestre, unidade e horários disponíveis.
- [ ] Integrar seguir/deixar de seguir com persistência após login e incluir seleção da turma no envio de plano. Explicar que o vínculo é autodeclarado.
- [ ] Mostrar planos disponíveis ou convite para envio. Preservar eventos particulares já importados ao deixar de seguir uma turma.

#### Critérios de aceite

- [ ] Buscar, seguir e reencontrar uma turma após recarregar, distinguindo disciplinas homônimas e ofertas de períodos diferentes. Navegar para os planos da oferta correta.
- [ ] Verificar orientações de vazio, erro e catálogo desatualizado, navegação por teclado e uso a partir de 360 px.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-B04 - Validar a integração da consulta e confirmação de planos

[Issue #72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)

#### Objetivo

Validar o fluxo de confirmação já entregue na sprint 6 com a extração real e preparar a importação por usuário na sprint 8.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 10–13/11/2026
- **Responsável principal** @marrathomaz
- **Corresponsável** @felipecduque7
- **Dependências** S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)) e S7-D01 ([#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)). Integrar resultados de S7-B01 ([#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51)) e reaproveitar a consulta/confirmação concluída na [#52](https://github.com/unb-mds/2026-2-AgendaUnB/issues/52) e a transação da [#54](https://github.com/unb-mds/2026-2-AgendaUnB/issues/54).
- **Requisitos** RF07 e RF09.

#### Tasks

- [ ] Reutilizar `GET /api/v1/syllabus/{id}` e `POST /api/v1/syllabus/{id}/confirm`, conferindo estados, schemas, constraints, permissões e migrations aplicadas.
- [ ] Verificar seleção parcial, edição de data/título/tipo e descarte, preservando a procedência no evento particular.
- [ ] Preparar importação de candidatos compartilhados com decisão isolada por usuário. Definir reimportação explícita após exclusão e bloquear restauração involuntária por retry antigo.

#### Critérios de aceite

- [ ] Demonstrar que apenas itens selecionados e válidos viram eventos do usuário. Recusar candidato de outro plano e exigir correção de data ambígua.
- [ ] Testar em PostgreSQL permissões, unicidade por usuário, confirmações repetidas e concorrentes, além de rollback sem gravação parcial.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-F03 - Integrar envio, revisão do texto, candidatos e agenda

[Issue #73](https://github.com/unb-mds/2026-2-AgendaUnB/issues/73)

#### Objetivo

Completar em homologação a jornada de plano particular até a agenda com dados e processamento reais.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 10–15/11/2026
- **Responsável principal** @Bielziin07
- **Corresponsável** @Thomas4ugust0
- **Dependências** S7-F02 ([#71](https://github.com/unb-mds/2026-2-AgendaUnB/issues/71)), S7-B01 ([#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51)) e S7-B04 ([#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)). Pode começar pelos contratos. Reaproveitar [#49](https://github.com/unb-mds/2026-2-AgendaUnB/issues/49) e [#50](https://github.com/unb-mds/2026-2-AgendaUnB/issues/50).
- **Requisitos** RF05–RF09, RNF06–RNF10.

#### Tasks

- [ ] Integrar PDF/texto, escolha da turma, histórico de envios e acompanhamento do processamento. Trocar o editor vazio/desabilitado em `SyllabusReviewPanel.jsx` pelos dados reais.
- [ ] Exibir antes do processamento o texto minimizado editável, o destino e a autorização separada para enviar ao provedor.
- [ ] Mostrar candidatos com origem e alertas, seleção individual/em lote e correção. Chamar o endpoint real de confirmação e atualizar a agenda.
- [ ] Tratar recarga, envio duplicado, falhas recuperáveis e PDF inválido/escaneado com alternativa por texto ou organização manual. Fornecer feedback acessível.

#### Critérios de aceite

- [ ] Demonstrar em homologação, sem mocks: seguir turma → enviar → revisar texto → autorizar → acompanhar → corrigir avaliações → importar → abrir na agenda.
- [ ] Verificar que o envio ao provedor começa após autorização, que o evento só é criado após confirmação e que o progresso persiste após recarga.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-F04 - Completar autenticação, confirmação de e-mail e recuperação

[Issue #74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74)

#### Objetivo

Completar cadastro e recuperação via Supabase, homologar Google OAuth e reforçar a autorização no servidor.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 09–15/11/2026
- **Responsável principal** @Thomas4ugust0
- **Corresponsável** @marrathomaz
- **Dependências** SMTP homologado em S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)). Reaproveitar a base de autenticação da [#16](https://github.com/unb-mds/2026-2-AgendaUnB/issues/16).
- **Requisitos** RF01–RF04, RNF01, RNF04, RNF07 e RNF09.

#### Tasks

- [ ] Implementar autorização incremental para Calendar ao conectar a integração. Vincular a conta Google à sessão Agenda UnB autenticada, inclusive para quem entrou com e-mail/senha, validando state/PKCE conforme o fluxo adotado. Tratar recusa sem bloquear login. Obter tokens do provedor e implementar renovação no servidor, armazenamento protegido e desconexão com revogação e remoção dos tokens. Testar expiração, `invalid_grant`, conta divergente e nova autorização. Integrar com [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82).
- [ ] Tratar cadastro sem sessão, tela de confirmação, retorno do link, reenvio com intervalo e links expirados ou reutilizados. Integrar recuperação e troca de senha pelo Supabase.
- [ ] Adicionar mostrar/ocultar senha, confirmação, validação e autocomplete apropriados. Tratar retorno e erros do Google OAuth sem confirmação local redundante.
- [ ] Verificar e-mail confirmado e autorização no servidor. Impedir escalada via domínio informado ou metadata do cliente. Restringir alterações de papel de terceiros a admin.

#### Critérios de aceite

- [ ] Com SMTP homologado, demonstrar cadastro e confirmação com endereço externo à equipe, reenvio, links expirados/reutilizados conforme política e recuperação real. Bloquear operações protegidas de conta não confirmada.
- [ ] Testar login/logout por e-mail e Google, retorno OAuth e tentativa de autopromoção por requisição direta. Verificar ausência de senhas e tokens nos logs.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-B05 - Coletar eventos da Agenda UnB com atualização e deduplicação

[Issue #75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75)

#### Objetivo

Alimentar a agenda pela fonte institucional Agenda UnB Notícias, com origem verificável e execução recorrente.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** 10–15/11/2026
- **Responsável principal** @pontesluis
- **Corresponsável** @marrathomaz
- **Apoio adicional** Felipe apoia as migrations de eventos.
- **Dependências** S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)) e S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)).
- **Requisitos** RF14–RF16 e RNF11.

#### Tasks

- [ ] Implementar coletor periódico da [lista paginada e dos detalhes da Agenda UnB Notícias](https://noticias.unb.br/component/agenda/agendas), observando restrições de acesso e frequência moderada.
- [ ] Persistir fonte, identificador/URL canônica, hash e última coleta. Fazer upsert por chave única da origem. Conciliar URL idêntica já cadastrada manualmente e enviar similaridade de título/data para revisão.
- [ ] Normalizar início/fim, dia inteiro, campus, local e link externo. Tratar `00:00` de preenchimento sem inventar horário e distinguir informes de eventos.
- [ ] Enviar casos ambíguos ou incompletos para moderação. Validar com a equipe a publicação automática proposta para itens válidos da fonte institucional permitida. Exibir a procedência.

#### Critérios de aceite

- [ ] Demonstrar execução agendada em homologação, duas execuções sucessivas e concorrentes sem duplicatas e atualização de data no mesmo registro.
- [ ] Verificar que indisponibilidade da fonte preserva registros, que decisões de moderação e campos editados localmente são respeitados e que a cobertura multicampus reflete os dados disponíveis.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S7-B06 - Publicar o Agenda UnB na Vercel com serviços integrados

[Issue #76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)

#### Objetivo

Disponibilizar o frontend React/Vite em uma URL Vercel HTTPS estável e demonstrar sua operação junto de FastAPI, Supabase Auth, banco e jobs.

- **Sprint** [Sprint 07](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/7)
- **Janela** Configuração de 09 a 10/11/2026. Primeira URL até 12/11. Aceite integrado até 15/11.
- **Responsável principal** @pontesluis
- **Corresponsável** @Thomas4ugust0
- **Apoio adicional** Heitor apoia a conexão da API e a execução de jobs. Thomas apoia Vercel e rotas SPA.
- **Dependências** S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)). Validar S7-F04 ([#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74)) no domínio publicado e testar as jornadas de S7-F02 ([#71](https://github.com/unb-mds/2026-2-AgendaUnB/issues/71)), S7-F03 ([#73](https://github.com/unb-mds/2026-2-AgendaUnB/issues/73)) e S7-B05 ([#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75)).
- **Requisitos** RNF03, RNF09, RNF11 e RNF13. O ambiente habilita a homologação dos RF.

#### Tasks

- [ ] Configurar callbacks OAuth da integração Calendar no domínio HTTPS de produção e ambiente de teste. Guardar client secret e material de criptografia no servidor. Validar conexão, retorno e renovação no domínio publicado em conjunto com [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74), preparando o aceite da [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82).
- [ ] Configurar diretório raiz `frontend`, build `npm run build`, saída `dist` e fallback SPA que preserve rotas de API. Domínio próprio é opcional.
- [ ] Separar preview e produção, incluindo variáveis e dados. Manter chaves de serviço Supabase e Gemini fora do bundle `VITE_*`. Impedir que previews escrevam em produção ou disparem coleta/lembretes reais.
- [ ] Aplicar a arquitetura escolhida em S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)) para API, worker, coletor e scheduler. Validar execução, limites, custo zero, persistência e uploads antes de usar Vercel para esses componentes. Usar hospedagem separada compatível quando necessário.
- [ ] Testar o caminho autorizado de upload para 10 MB. Se o caminho ultrapassar limites da hospedagem, definir transporte compatível com validação e privacidade.
- [ ] Configurar API pública HTTPS, CORS com origens explícitas e URLs de retorno do Supabase. Aplicar migrations de forma controlada e ligar deploy à branch e aos checks definidos.
- [ ] Documentar arquitetura, limites, variáveis sem valores secretos, observabilidade e rollback de frontend/API compatível com o schema.

#### Critérios de aceite

- [ ] Abrir a URL Vercel em outra máquina ou rede. Confirmar HTTPS, rotas profundas após refresh, build reproduzível e tratamento de falha da API na interface.
- [ ] Demonstrar cadastro, confirmação, recuperação, Google OAuth, consultas da API, upload/revisão/importação e agenda no ambiente publicado. Jobs e coleta executam na hospedagem sem navegador ou computador da equipe.
- [ ] Ensaiar rollback e verificar que logs são úteis e livres de dados sensíveis.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


