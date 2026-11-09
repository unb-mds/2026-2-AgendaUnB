# R2 — Issues propostas para as sprints 7 e 8

Planejamento aprovado em 07/11/2026 e publicado nas issues das sprints 7 e 8. Os códigos identificam sprint, área coordenadora (F frontend, B backend, D dados) e sequência por área. As páginas de [Sprint 7](sprints/sprint-7.md) e [Sprint 8](sprints/sprint-8.md) registram os responsáveis e os links atuais.

## Objetivo e calendário

Entregar até **25/11/2026** o escopo funcional e não funcional acordado, com aplicação integrada e evidências de validação. A sprint 7 termina em **15/11**; a sprint 8 vai de **16 a 23/11**. Os dias **24 e 25/11** ficam para aceite final, correções impeditivas e preparação da entrega, sem funcionalidades novas planejadas.

| Marco | Resultado esperado |
| --- | --- |
| 07–08/11 | Contratos, decisões de produto e provas de viabilidade de Followw público, SMTP, Gemini e execução de tarefas em segundo plano |
| 09–12/11 | Primeiro deploy Vercel acessível por HTTPS; banco e catálogo integrados; primeira jornada real PDF/texto → revisão → agenda; autenticação em homologação |
| 13–15/11 | Deploy Vercel integrado à API e Supabase, fluxos particulares concluídos, coleta automática operante e permissões verificadas |
| 16–19/11 | Planos compartilhados, votação, participação/histórico, lembretes e exportação direta Google integrados |
| 20/11 | Congelamento funcional proposto: todas as funcionalidades devem estar disponíveis em homologação |
| 21–23/11 | Correção de defeitos, acessibilidade, desempenho, segurança, navegadores e documentação final |
| 24/11 | Ensaio completo da entrega, restauração/rollback e verificação do ambiente final |
| 25/11 | Aceite e entrega com matriz de requisitos e limitações conhecidas |

O calendário é uma proposta de execução, não uma estimativa comprovada de capacidade: a disponibilidade diária das seis pessoas não foi informada. Dependências externas devem ser resolvidas até 08/11. Se alguma falhar, registrar o requisito afetado e decidir a alternativa imediatamente; não deixar a descoberta para o fim da sprint 8.

## Escopo fechado para este planejamento

- Followw somente por endpoints públicos sem autenticação. Não haverá botão “Continuar com Followw”, login SIGAA, coleta de senha institucional, consulta de matrícula privada, notas ou avisos de turmas autenticadas.
- O aluno escolhe manualmente as turmas do catálogo público. “Seguir turma” não comprova matrícula nem concede identidade institucional verificada.
- Atestado de matrícula deixa de ser o mecanismo desta entrega. RF05/RF06 e visão precisam registrar essa substituição expressamente.
- Coleta automática pela **Agenda UnB Notícias** como primeira fonte. Followw fornece catálogo acadêmico; não presumir que forneça notícias, provas ou planos pelos endpoints públicos.
- PDF/texto particular por padrão. Compartilhamento com a turma exige ação explícita após revisão; qualquer usuário autenticado que siga a turma pode consultar e votar.
- Manter autoria e procedência distintas: envio por estudante, envio por perfil professor e origem institucional comprovada não são equivalentes.
- IA extrai somente **provas e trabalhos**; nenhum resultado vira evento sem revisão e confirmação do aluno.
- Inscrição significa registro local de interesse/participação no Agenda UnB; não substitui eventual inscrição exigida pelo organizador externo. Histórico não certifica presença.
- Professores e administradores moderam eventos; somente administradores alteram papéis e gerenciam categorias.
- Lembretes persistidos dentro da plataforma. E-mail transacional atende autenticação, não uma campanha de notificações acadêmicas.
- Deploy na **Vercel prioritariamente na sprint 7**, com primeira URL até 12/11 e aplicação integrada até 15/11. Publicar somente o frontend não conclui a entrega: API, Auth, banco e jobs precisam estar acessíveis e funcionar juntos.
- RF21 passa a prever exportação direta pela Google Calendar API na S8-F03 (#82), com consentimento OAuth adicional e agenda secundária “Agenda UnB”. A atualização ocorre por reexportação explícita. ICS atende Apple Calendar/Outlook como alternativa complementar.
- Sem orçamento previsto. Validar cota, termos e execução dos serviços gratuitos antes de depender deles.
- PDF digital até 10 MB e 10 páginas, conforme sprint 6; PDF escaneado sem texto recebe orientação e alternativa manual. OCR não integra este recorte.

## O que já existe e deve ser reaproveitado

O backend já possui código para upload, listagem, detalhe com candidatos e `POST /syllabus/{id}/confirm`. Ano e semestre já são recebidos no upload. **A consulta e confirmação da antiga S6-B02 foram concluídas e renomeadas para S6-B01. A issue #51 é a extração com IA, originalmente S6-B01 e agora S7-B01, e permanece inconclusa.** Rotas existentes são implementação parcial; reaproveitar o código e concluir os critérios na sprint 7.

A tela `frontend/src/components/SyllabusReviewPanel.jsx` ainda entrega `value={[]}` e `disabled` ao editor. O serviço de upload ainda grava estado `pendente`; a existência do endpoint de confirmação não demonstra processamento real por IA. O trabalho é concluir o processamento, harmonizar estados e integrar a jornada.

As políticas/migrations existentes precisam ser verificadas junto ao modelo atual antes de ampliar compartilhamento. Uma confirmação particular existente não garante importação compartilhada correta para múltiplos usuários.

Há documentação navegada por `docs.json`/Mintlify e workflow de publicação com MkDocs em `.github/workflows/docs.yml`. Também coexistem documentos antigos e novos. A entrega precisa definir uma fonte canônica e validar sua publicação; não manter duas versões divergentes de requisitos.

## Responsabilidade e organização

Os responsáveis foram atribuídos no GitHub, com até dois assignees por issue. Apoios adicionais estão registrados nas descrições. Cada issue tem um responsável principal e apoio necessário; a outra pessoa da área revisa. Luis e Felipe apoiam serviços e automação ligados a dados, além das migrations. Se isso não couber na disponibilidade da dupla, redistribuir explicitamente no início, pois concentrar tudo nos dois integrantes de backend inviabiliza esta divisão.

| Pessoa | Frentes principais |
| --- | --- |
| Thomas Araujo — @Thomas4ugust0 | Contratos/documentação, catálogo de turmas, autenticação, biblioteca compartilhada |
| Gabriel Escramin — @Bielziin07 | Revisão de planos, agenda/eventos, Calendar API e experiência/acessibilidade |
| Heitor Monteiro — @heitormontt | Adaptador Followw, processamento com IA e lembretes |
| Thomaz Marra — @marrathomaz | Confirmação/importação, colaboração, participação e autorização |
| Felipe Couto — @felipecduque7 | Modelo relacional, restrições/RLS, privacidade e ciclo de vida dos dados |
| Luis Davi — @pontesluis | Infraestrutura/CI, coleta institucional, validação de segurança e entrega operacional |

Labels aplicadas no GitHub, conforme a natureza de cada issue: `sprint-7`/`sprint-8`, `release-2`, área e `feature`/`integration`/`quality`/`documentation`. Todos os itens abaixo compõem o escopo de entrega; a ordem indica dependência, não autorização para descartar os últimos.

## Sprint 7 — até 15/11

### S7-F01 — Consolidar requisitos, decisões e contratos da entrega

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


### S7-B02 — Validar infraestrutura gratuita, integrações e CI

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


### S7-D01 — Modelar turmas, vínculos, versões e isolamento dos planos

**Responsável:** Felipe; apoio Luis e Thomaz. **Janela:** 08–10/11. **Dependências:** contrato de S7-F01.

**Como fazer:** evoluir as tabelas existentes com identidade canônica da oferta, período, origem pública e atualização; vínculo único usuário/turma; plano e versão associados a uma turma; autoria, visibilidade privada/compartilhada e candidatos com evidência. Usar identificador da disciplina na origem quando disponível; caso contrário, combinação validada de código, número da turma, período e unidade/nível quando necessários. Não confundir a disciplina abstrata com sua oferta em determinado semestre. Preparar referências de importação por usuário/candidato/versão e índices necessários.

**Aceite:** migrations preservam dados atuais; seguir turma repetidamente não duplica vínculos; turmas de semestres diferentes não se misturam; usuário B não consulta PDF, texto ou candidatos privados de A pela API, banco ou Storage; arquivo continua privado por padrão. Autorizações não dependem de controles escondidos na interface. Compatibilidade entre modelos ORM e migrations comprovada.

### S7-B03 — Integrar o catálogo público do Followw no backend

**Responsável:** Heitor; apoio Felipe. **Janela:** 08–11/11. **Dependências:** contratos S7-F01; persistência S7-D01 para integração final.

**Como fazer:** adaptador de servidor com lista permitida de endpoints públicos, timeout, tentativas limitadas, cache persistido e data da última atualização. Trabalhar com `/public/classrooms/units`, `/public/classrooms` e consultas filtradas a `/public/subjects`, conforme contrato confirmado em S7-B02. Consultar por unidade/período/código, respeitando paginação e limites reais; não pressupor endpoint público que enumera tudo. Evitar consulta vazia a subjects que acione recomendação autenticada. Sincronização restrita no servidor; nenhum token de usuário Followw.

**Aceite:** busca real por disciplina, unidade e período; identidade estável em sincronizações repetidas; indisponibilidade externa preserva turmas seguidas e último catálogo válido; interface recebe informação de desatualização; nenhum endpoint privado é chamado. Registrar cobertura efetiva do catálogo, sem anunciar abrangência que não foi verificada.

### S7-F02 — Implementar catálogo e “Minhas turmas” na interface

**Responsável:** Thomas; apoio Gabriel. **Janela:** 09–12/11. **Dependências:** S7-F01; S7-D01, S7-B03 para integração real.

**Como fazer:** buscar disciplina e escolher oferta com número, semestre, unidade e horários disponíveis; seguir/deixar de seguir; manter preferências após login; selecionar turma no envio de plano. Mostrar planos existentes ou chamada para enviar quando não houver nenhum. Informar que o vínculo é autodeclarado. Desvincular turma não apaga silenciosamente eventos particulares já importados.

**Aceite:** usuário encontra e segue turma, recarrega e mantém o vínculo; não confunde homônimas/períodos; navega para planos daquela oferta; estados vazio, erro e catálogo desatualizado têm orientação; tela utilizável em 360 px e por teclado.

### S7-B01 (#51) — Concluir extração assíncrona de provas e trabalhos com IA

**Responsável:** Heitor; apoio Luis. **Situação:** #51, antiga S6-B01, realocada e inconclusa. **Janela:** 09–13/11. **Dependências:** S7-F01, S7-B02, S7-D01; interface em S7-F03.

**Como fazer:** reaproveitar validações do upload e adicionar texto bruto com limite documentado. Extrair texto no servidor, minimizar/remover identificadores, permitir revisão do conteúdo exato a enviar e exigir autorização antes da chamada externa. Não enviar PDF original ao Gemini. Processar somente trecho aprovado em job persistido; validar resposta estruturada com título, tipo prova/trabalho, data, ambiguidades e referência ao trecho/página disponível. Texto do documento é dado, nunca instrução executável. Sem navegação ou ferramentas acionadas pelo documento. Guardar candidatos, não eventos definitivos.

**Aceite:** PDFs/textos representativos retornam somente avaliações; data incompleta fica pendente de correção, sem inventar ano/horário; aulas e referências bibliográficas não viram eventos; erro/429/timeout, resultado vazio e reprocessamento têm estados recuperáveis; retry não duplica candidatos ativos. Medir RNF06 com corpus até 10 páginas, incluindo fila e provedor, sem contar o tempo humano de revisão; documentar também o tempo da preparação inicial. Manter a meta de menos de 20 s e registrar qualquer descumprimento, sem mudar o requisito silenciosamente.

**Limite:** sanitização por regex não garante anonimização. Conteúdo ainda pessoal/confidencial não pode seguir ao serviço gratuito; oferecer organização manual. Validar termos/elegibilidade em S7-B02 antes de habilitar o provedor em produção.

### S7-B04 — Validar integração da consulta e confirmação já concluídas na S6-B01

**Responsável:** Thomaz; apoio Felipe. **Situação:** validação de integração da S6-B01 concluída; não é a issue #51. **Janela:** 10–13/11. **Dependências:** S7-F01, S7-D01; integrar resultados de S7-B01.

**Como fazer:** reaproveitar `GET /syllabus/{id}` e `POST /syllabus/{id}/confirm`; conferir estados, schemas, constraints e comportamento real das migrations. Permitir seleção parcial, edição de data/título/tipo e descarte. Manter procedência no evento particular. Preparar a operação para importar candidatos compartilhados na sprint 8 sem modificar o candidato global em função da decisão individual. Definir reimportação explícita após exclusão, para que retry antigo não ressuscite evento removido.

**Aceite:** só itens selecionados viram eventos do usuário; repetir ou executar duas confirmações concorrentes não duplica; candidato de outro plano é recusado; data ambígua precisa ser corrigida; falha transacional não deixa importação parcial inesperada. Testes em PostgreSQL verificam concorrência e unicidade por usuário, além das permissões.

### S7-F03 — Integrar envio, revisão do texto, candidatos e agenda

**Responsável:** Gabriel; apoio Thomas. **Janela:** 10–15/11. **Dependências:** S7-F02, S7-B01 (#51) e S7-B04; pode começar pelos contratos.

**Como fazer:** substituir editor vazio/desabilitado pela resposta real; aceitar PDF/texto, escolher turma e exibir estado do processamento. Antes da IA, mostrar texto sanitizado editável, destino e autorização separada. Depois, exibir candidatos com origem, alertas, seleção individual/em lote e correção. Acionar endpoint real de confirmação; atualizar agenda e permitir consultar envios anteriores.

**Aceite:** jornada completa em homologação, sem mocks: seguir turma → enviar → revisar texto → autorizar → acompanhar → corrigir avaliações → importar → abrir na agenda. Nada é enviado ao provedor antes da autorização e nada é criado na agenda antes da confirmação. Recarregar mantém progresso; PDF inválido/escaneado oferece alternativa por texto/manual; operações possuem feedback acessível e impedem submissão duplicada.

### S7-F04 — Completar autenticação, confirmação de e-mail e recuperação

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


### S7-B05 — Coletar eventos da Agenda UnB com atualização e deduplicação

**Responsável:** Luis; apoio Thomaz. **Janela:** 10–15/11. **Dependências:** S7-F01, S7-B02; migrations de eventos com Felipe.

**Como fazer:** coletor periódico da lista paginada e detalhes de `https://noticias.unb.br/component/agenda/agendas`; respeitar restrições de acesso e frequência moderada. Persistir origem, identificador/URL canônica, hash, última coleta e campos normalizados. Upsert com chave única da origem; reexecução atualiza o mesmo registro. Normalizar início/fim, dia inteiro, campus, local e link externo. Não inventar horário para “00:00” usado como preenchimento nem classificar todo informe como evento. Item sem dados suficientes fica para revisão. Proposta: publicar automaticamente itens válidos da fonte institucional permitida; casos ambíguos entram na moderação.

**Aceite:** duas execuções e duas execuções concorrentes não duplicam; alteração de data atualiza registro; URL já cadastrada manualmente é tratada sem criar segunda cópia; semelhança apenas de título/data gera revisão, não fusão automática. Fonte indisponível não apaga agenda nem registros antigos. Preservar decisões de moderação e campos editados localmente; exibir origem. Job agendado realmente executa em homologação. Cobertura multi-campus existe no produto, mas não se inventam eventos ausentes na fonte.

### S7-B06 — Publicar o Agenda UnB na Vercel com serviços integrados

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


## Sprint 8 — 16 a 23/11

### S8-B01 — Implementar compartilhamento, versões e votação dos planos

**Responsável:** Thomaz; apoio Felipe. **Janela:** 16–18/11. **Dependências:** S7-D01, S7-B04 e S7-F03.

**Como fazer:** publicar voluntariamente uma versão revisada na turma; autor/professor/admin conforme regra registrada, sem tornar todo plano particular público. Leitura por usuários autenticados que seguem a turma. Uma avaliação ativa por conta/candidato/versão, permitindo corrigir o próprio voto sem multiplicá-lo. Exibir contagem e divergência; votação não altera automaticamente datas nem prova veracidade. Nova revisão cria versão e não sobrescreve calendários pessoais. Importação compartilhada usa deduplicação por usuário/candidato/versão.

**Aceite:** dois usuários da turma leem a mesma versão e importam para agendas privadas independentes; voto repetido não aumenta contagem; usuário não vinculado/visitante é recusado; vincular-se é explicitamente autodeclarado. Compartilhar esclarece se inclui o PDF original; por padrão, compartilhar apenas conteúdo revisado, com PDF exigindo autorização específica. Retirada do compartilhamento impede novos acessos/importações, preservando eventos particulares já copiados conforme política documentada. Downloads privados usam autorização efetiva, não URL pública permanente.

### S8-F01 — Entregar biblioteca de planos e validação colaborativa na interface

**Responsável:** Thomas; apoio Gabriel. **Janela:** 16–19/11. **Dependências:** S7-F02, S7-F03 e S8-B01.

**Como fazer:** por turma, listar versões, autor/tipo de autoria, origem e data; abrir plano disponível, revisar avaliações e importar selecionadas. Mostrar votos, divergências e quais itens já foram importados. Permitir publicar/retirar compartilhamento e consultar versões. Quando não há plano, manter upload vinculado à turma. Não rotular contribuição de colega como “oficial” automaticamente.

**Aceite:** usuário novo segue turma e aproveita avaliações existentes sem reenviar arquivo; colega publica e retira compartilhamento com confirmação clara; divergências têm tratamento visível; versão nova não altera evento pessoal silenciosamente; ações e limites de acesso ficam claros em desktop e celular.

### S8-B02 — Implementar participação local, cancelamento e histórico

**Responsável:** Thomaz; apoio Felipe e Gabriel. **Janela:** 16–19/11. **Dependências:** S7-F01; modelo público de eventos consolidado em S7-B05.

**Como fazer:** persistir vínculo único usuário/evento com estado e timestamps; inscrição/cancelamento idempotentes e autorizados. Ligar participação aos eventos públicos exibidos na agenda. Histórico separa eventos públicos inscritos e compromissos privados passados, com status de cancelamento, sem alegar presença comprovada. Proposta: novas inscrições só em eventos publicados não encerrados; cancelamento disponível conforme RF13.

**Aceite:** um clique registra, repetição não duplica, cancelamento persiste e remove lembretes futuros; evento rejeitado/inexistente não aceita inscrição; usuário não muda inscrição de outro. Mensagem avisa quando inscrição externa também é necessária, com link oficial. Histórico e agenda refletem estados sem duplicar o mesmo evento.

### S8-F02 — Fechar eventos, moderação, agenda e melhorias de uso

**Responsável:** Gabriel; apoio Thomas e Thomaz. **Janela:** 16–20/11. **Dependências:** S7-B05 e S8-B02 para integração final.

**Como fazer:** verificar e corrigir RF08–RF11/RF14/RF15/RF19/RF20 nos fluxos existentes: mês/semana/lista, CRUD particular, submissão estudantil pendente, criação direta por professor/admin, aprovação/rejeição com motivo, gestão de papéis/categorias restrita a admin. Completar detalhes e filtros combináveis por categoria, campus/instituto e intervalo; representar cinco campi sem inferência incorreta da fonte. Persistir tema e filtros úteis; dar estados vazios, limpeza de filtros, feedback de erro e confirmação de ações destrutivas.

**Aceite:** matriz de permissões exercitada por visitante/aluno/professor/admin; aluno não publica diretamente; professor modera mas não altera papéis/categorias. Data, horário ou dia inteiro, intervalo, local e URL preservados do formulário à tela. Filtros combinam corretamente; calendário lida com fuso e eventos de vários dias; tema claro/escuro não perde legibilidade; participação e eventos particulares permanecem distinguíveis. Não redesenhar toda a plataforma nesta issue.

### S8-B03 — Entregar lembretes persistentes dentro da plataforma

**Responsável:** Heitor; apoio Luis e Gabriel. **Janela:** 16–19/11. **Dependências:** S7-B02, S7-B04 e S8-B02.

**Como fazer:** preferência de antecedência com padrão explícito; scheduler cria notificações para provas/trabalhos particulares e eventos inscritos. Chave idempotente por usuário/evento/antecedência/versão relevante; estados lida/não lida e central simples. Alteração de horário reprograma pendências; exclusão/cancelamento cancela envios futuros. Para evento de dia inteiro, documentar horário de referência local. Proposta inicial: 24 h antes; escolha editável na interface.

**Aceite:** job reiniciado/duplicado não envia lembrete duplicado; usuário offline recebe aviso persistido ao retornar; cancelamento e mudanças são respeitados; nenhuma notificação privada chega a outro usuário. Caso criado já dentro da antecedência tem regra explícita e teste; interface não promete push/e-mail.

### S8-F03 — Exportar diretamente para o Google Agenda via Calendar API

#### Objetivo

Exportar eventos selecionados diretamente para uma agenda secundária “Agenda UnB” na conta Google autorizada, mediante ação do usuário. Manter exportação ICS para compatibilidade com Apple Calendar e Outlook.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 17–19/11/2026
- **Responsável principal** @Bielziin07
- **Corresponsável** @marrathomaz
- **Dependências** Contrato de datas de S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)), integração de S7-B04 ([#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)), S7-F03 ([#73](https://github.com/unb-mds/2026-2-AgendaUnB/issues/73)) e S8-B02 ([#79](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79)), eventos públicos e URL de S7-B06 ([#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)).
- **Integrações necessárias** [#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68), [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74), [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83) e [#84](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84).
- **Requisitos** RF21 e RNF02.

#### Tasks

- [ ] Implementar “Conectar Google Agenda” e consentimento adicional com o escopo `calendar.app.created`. Disponibilizar a conexão tanto para login Google quanto para e-mail/senha, aproveitando a autorização implementada em [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74).
- [ ] Criar uma agenda secundária “Agenda UnB” após autorização e persistir seu calendarId associado ao usuário e à conta Google. Reutilizar essa agenda nas próximas exportações.
- [ ] Permitir selecionar período/eventos e confirmar o envio. Exportar provas, trabalhos e eventos públicos inscritos com título, descrição selecionada, local, início/fim, dia inteiro e fuso America/Sao_Paulo. Excluir PDFs, texto integral dos planos, caminhos de Storage, tokens e dados de terceiros.
- [ ] Persistir mapeamento usuário/evento local/calendarId/eventId e versão exportada. Usar identificador de criação estável aceito pela API para reconciliar timeout após envio, retries e concorrência. Registrar resultado individual e retomar somente itens pendentes ou falhos.
- [ ] Na reexportação explícita, atualizar o evento previamente exportado mediante confirmação de sobrescrita dos campos geridos pelo Agenda UnB. Exibir quais itens serão criados/atualizados. Exclusões locais não removem automaticamente cópias no Google. Tratar destino apagado e conta desconectada com orientação e confirmação para recriação.
- [ ] Usar tokens Google pelo servidor e renovação da [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74). Tratar permissão recusada/revogada, expiração, 401/403, 429 com espera limitada e falhas parciais. Apresentar estado por item, sucesso e opção de tentar novamente.
- [ ] Manter a opção de arquivo ICS para Apple Calendar/Outlook com UID estável, UTF-8, escape e datas corretas. Explicar que atualização do Google ocorre quando o usuário solicita nova exportação. Sincronização automática bidirecional exige planejamento próprio.

#### Critérios de aceite

- [ ] Na URL Vercel, demonstrar autorização → seleção → exportação direta → eventos visíveis na agenda Google, com contas sintéticas. Conferir provas, trabalhos, evento inscrito, acentos, fuso, intervalos e dia inteiro, em desktop e celular.
- [ ] Demonstrar ausência de duplicatas em exportações repetidas/concorrentes e recuperação após timeout ou falha parcial. Confirmar atualização de um evento alterado em reexportação explícita.
- [ ] Testar recusa, revogação, expiração e renovação, isolamento entre usuários, desconexão e destino removido. Confirmar funcionamento para conta Agenda UnB de e-mail/senha e conta com login Google.
- [ ] Importar o ICS complementar em Apple Calendar e Outlook, registrando clientes usados e verificando UID, acentos e datas.

#### Referências

- [Escopos Google Calendar](https://developers.google.com/workspace/calendar/api/auth)
- [Criação de eventos](https://developers.google.com/workspace/calendar/api/guides/create-events)
- [Tokens de provedores no Supabase](https://supabase.com/docs/guides/auth/social-login#provider-tokens)

#### Evidências para fechamento

- [ ] Anexar PR, versão implantada, resultados dos cenários e revisão de outra pessoa.


### S8-D01 — Concluir privacidade, termos e ciclo de vida dos dados

#### Objetivo

Alinhar tratamento e documentação aos fluxos reais e demonstrar o exercício dos direitos sobre dados do usuário.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 16–20/11/2026. Inventário iniciado na Sprint 07.
- **Responsável principal** @felipecduque7
- **Corresponsável** @Thomas4ugust0
- **Apoio adicional** Thomaz apoia a autorização e o ciclo de vida da conta.
- **Dependências** Inventário em S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67))/S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)), modelo de S7-D01 ([#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)), extração S7-B01 ([#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51)) e decisões de S8-B01 ([#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77)).
- **Requisitos** RF07, RNF02 e RNF04.

#### Tasks

- [ ] Incluir Google Calendar no inventário de provedores e na política, descrevendo dados enviados, escopo autorizado, retenção e proteção dos tokens. Implementar desconexão/revogação e apagar tokens na exclusão da conta. Informar que eventos já exportados permanecem no Google Agenda e definir a exclusão explícita dessas cópias pelo usuário.
- [ ] Inventariar dados, finalidade, base legal aplicável, operadores/provedores, transferências, retenção e exclusão. Definir com a equipe identificação e canal do responsável.
- [ ] Publicar política e termos no cadastro/configurações, registrar versão e manifestação pertinente e distinguir aceite de termos de consentimento. Descrever Gemini, Followw e coleta pública com os limites efetivos da minimização.
- [ ] Implementar acesso/exportação de dados do titular, solicitação/exclusão de conta e revogação de compartilhamento conforme política. Abranger Auth, banco, Storage, jobs e logs, incluindo autoria, derivações compartilhadas e retenções justificadas.
- [ ] Documentar atendimento ao titular e procedimento de incidente. Usar o [guia de segurança da ANPD](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-vf.pdf) como referência de controles.

#### Critérios de aceite

- [ ] Demonstrar acesso e exclusão ponta a ponta, incluindo PDFs e tarefas pendentes. Explicar retenções e cópias independentes já importadas.
- [ ] Verificar que conteúdo acadêmico e tokens não aparecem em logs. Anexar evidência da revisão técnica e documental e registrar seu escopo.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-D02 — Verificar segurança e corrigir falhas de autorização

#### Objetivo

Verificar controles de acesso, infraestrutura e superfícies de abuso antes do aceite da Release 2.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 16–21/11/2026. Testes preventivos desde a Sprint 07.
- **Responsável principal** @pontesluis
- **Corresponsável** @felipecduque7
- **Apoio adicional** Thomaz apoia os testes de autorização e a correção dos fluxos do backend.
- **Dependências** Fluxos integrados progressivamente em S7-F04 ([#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74)), S7-B06 ([#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)), S8-B01 ([#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77)), S8-B02 ([#79](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79)), S8-F02 ([#80](https://github.com/unb-mds/2026-2-AgendaUnB/issues/80)), S8-B03 ([#81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81)) e S8-D01 ([#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83)).
- **Requisitos** RF04, RF09–RF11, RNF01–RNF04.

#### Tasks

- [ ] Testar isolamento cross-user da conexão Calendar e dos mapeamentos de eventos, callbacks OAuth, revogação, expiração e renovação concorrente. Verificar criptografia dos tokens em repouso, acesso restrito ao servidor e ausência de tokens em URLs da aplicação, logs e respostas de negócio. Exercitar recusa de consentimento e `invalid_grant`.
- [ ] Montar matriz cross-user para planos/candidatos/Storage, agenda, participação, votos, notificações e funções admin. Testar chamadas diretas à API e ao banco exposto.
- [ ] Conferir JWT, e-mail confirmado, RLS, privilégios de service role, URLs assinadas, secrets, TLS frontend–API–banco e CORS/origens.
- [ ] Verificar validação de uploads, sanitização de HTML coletado, consultas parametrizadas e proteções contra abuso de upload, IA, login/reenvio e sincronização.
- [ ] Executar análise de dependências e segredos, revisar resultados e verificar a configuração de credenciais sob Supabase Auth.

#### Critérios de aceite

- [ ] Corrigir vulnerabilidades críticas/altas conhecidas no escopo avaliado e registrar tratamento e responsável para achados menores.
- [ ] Anexar evidências com cenários, ambiente e limites da avaliação. Verificar que o app usa Supabase Auth para armazenar e gerenciar credenciais.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-F04 — Homologar requisitos não funcionais e jornadas completas

#### Objetivo

Homologar a Release 2 com testes integrados, medições reproduzíveis e evidências por requisito.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** Medições desde a Sprint 07. Fechamento de 20 a 23/11/2026.
- **Responsável principal** @Bielziin07
- **Apoio adicional** Toda a equipe testa e registra evidências da sua frente.
- **Dependências** Funcionalidades em homologação até 20/11, no ambiente de S7-B06 ([#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)).
- **Requisitos** RNF01–RNF13 e jornadas funcionais da Release 2.

#### Tasks

- [ ] Executar na URL Vercel a jornada conectar Google → autorizar Calendar → selecionar eventos → exportar → abrir a agenda Google. Testar usuário com login Google e com e-mail/senha, reexportação repetida/concorrente, timeout após criação, falha parcial, 429, token expirado, consentimento recusado e revogado. Anexar evidências com contas sintéticas para [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82).
- [ ] Executar testes unitários e de integração das regras de cada issue. Testar E2E cadastro → turma → plano → importação, publicação → voto → importação por colega e evento coletado → inscrição → lembrete → histórico → exportação direta para o Google Agenda.
- [ ] Definir a carga de uso normal antes de medir. Registrar dataset, concorrência, infraestrutura, cache e metodologia. Medir `GET /events` em p95 ≤ 300 ms e parser < 20 s conforme S7-B01 ([#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51)). Ajustar índices, paginação ou consultas conforme resultados.
- [ ] Verificar WCAG 2.1 AA, contraste nos dois temas, teclado, foco, labels, largura de 360 px e demais resoluções principais.
- [ ] Homologar versões atuais de Chrome, Firefox, Edge e Safari real e registrar navegador/versão.
- [ ] Exercitar PDFs ilegíveis, protegidos e escaneados, indisponibilidade de Followw/UnB/Gemini, sessão expirada, duplicação de requisições e interrupção de job.

#### Critérios de aceite

- [ ] Publicar relatório reproduzível por RNF e jornada com evidências reais, correções e riscos. Manter pendentes metas não medidas ou não atingidas.
- [ ] Confirmar ausência de vazamento ou perda indevida nos cenários de falha e registrar os resultados em homologação.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-F05 — Fechar documentação, operação e pacote de entrega

#### Objetivo

Consolidar a documentação canônica e preparar a operação, demonstração e aceite da entrega de 25/11.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** Atualização contínua. Consolidação de 21 a 23/11/2026. Ensaio em 24/11 e aceite em 25/11.
- **Responsável principal** @Thomas4ugust0
- **Corresponsável** @pontesluis
- **Apoio adicional** Autores das demais issues fornecem documentação e evidências das suas entregas.
- **Dependências** Evidências das demais issues, incluindo S7-B06 ([#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)) e S8-F04 ([#85](https://github.com/unb-mds/2026-2-AgendaUnB/issues/85)).
- **Requisitos** RNF13 e rastreabilidade de RF01–RF21/RNF01–RNF13.

#### Tasks

- [ ] Documentar habilitação da Calendar API, escopo OAuth, callbacks, modo de teste/publicação, proteção e renovação de tokens, desconexão e regras de reexportação. Incluir a exportação direta no roteiro da entrega, com falhas recuperáveis e limites de sincronização explícitos.
- [ ] Reconciliar docs canônicas e antigas. Alinhar `docs.json`/Mintlify com a estratégia de publicação e resolver a divergência do workflow MkDocs.
- [ ] Atualizar arquitetura, modelo de dados, API, variáveis sem segredos, instalação, execução de worker/coletor, falhas e cotas, sprints e release notes.
- [ ] Preparar checklist de implantação/migrations, backup, restauração e rollback, incluindo mudanças de schema. Planejar ensaio em 24/11 com verificação do ambiente final.
- [ ] Preparar roteiro demonstrável e matriz RF/RNF com links de implementação/testes, status, pendências e limitações conhecidas para o aceite de 25/11.

#### Critérios de aceite

- [ ] Outra pessoa da equipe reproduz setup e demonstração com a documentação. Links e build passam, e o ambiente final corresponde à versão revisada.
- [ ] Cada requisito tem evidência ou pendência explícita. Roteiro de 24–25/11 fica pronto, com critérios de aceite, restauração/rollback e espaço para correções impeditivas.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


## Dependências que determinam a entrega

1. **Turmas/planos:** S7-F01 → S7-D01, S7-B03 → S7-F02 → S7-B01, S7-B04 e S7-F03 → S8-B01, S8-F01.
2. **Automação:** S7-B02 → S7-B01/10 e S8-B03; sem execução real dos jobs, essas funcionalidades não estão entregues.
3. **Eventos:** S7-F01, S7-B05 → S8-B02, S8-F02 → S8-B03, S8-F03.
4. **Autenticação:** S7-B02 → S7-F04 → verificação de acessos em todas as jornadas.
5. **Qualidade:** S8-D01, S8-D02, S8-F04, S8-F05 começam de forma incremental, não somente quando todas as features terminarem.
6. **Deploy:** S7-B02 → S7-B06; validar S7-F04 e demais fluxos na URL Vercel até 15/11. A homologação S8-F04 e a exportação Google S8-F03 usam esse ambiente publicado.

Frontend pode avançar com contratos simulados, mas a issue só fecha após integração real. Contratos e schema precisam estar estáveis até 10/11. Não reservar a integração entre as três duplas para 23/11.

## Matriz de cobertura

| Requisito | Issues de implementação/integração | Evidência principal de aceite |
| --- | --- | --- |
| RF01 — login local | S7-F04 | Login, sessão, erros e logout reais |
| RF02 — cadastro | S7-F04 | Cadastro, confirmação de senha/e-mail e recuperação |
| RF03 — Google OAuth | S7-F04 | Jornada completa de retorno/autenticação |
| RF04 — papéis | S7-F04, S8-F02, S8-D02 | Usuário não se promove; admin controla alterações |
| RF05 — envio e vínculo, com revisão aprovada do requisito | S7-F01, S7-D01, S7-F02, S7-B01, S7-F03, S8-B01, S8-F01 | PDF/texto particular e vínculo manual à turma |
| RF06 — extração, com revisão aprovada do requisito | S7-F01, S7-B01, S7-F03 | Provas/trabalhos com evidência, revisão e ambiguidades |
| RF07 — revisão/colaboração | S7-B04, S7-F03, S8-B01, S8-F01 | Confirmação individual e voto único por versão |
| RF08 — calendário | S7-F03, S8-F02 | Mês, semana e lista com dados reais |
| RF09 — CRUD privado | S7-B04, S7-F03, S8-F02, S8-D02 | CRUD isolado por usuário e origem preservada |
| RF10 — submissão pública | S8-F02, S8-D02 | Aluno pendente; professor/admin publicação direta |
| RF11 — moderação | S7-F01, S8-F02, S8-D02 | Matriz de ações por papel |
| RF12 — inscrição local | S7-F01, S8-B02, S8-F02 | Registro idempotente e aviso sobre organizador |
| RF13 — cancelamento | S8-B02, S8-B03 | Estado persistido e lembretes futuros cancelados |
| RF14 — detalhes | S7-B05, S8-F02 | Data/intervalo/local/URL íntegros |
| RF15 — multi-campus | S7-B05, S8-F02 | Cinco campi suportados e filtráveis |
| RF16 — coleta | S7-B02, S7-B05 | Job real, origem e deduplicação |
| RF17 — lembretes | S8-B03 | Aviso persistente, antecedência e isolamento |
| RF18 — histórico | S7-F01, S8-B02, S8-F02 | Públicos/privados separados, sem alegar presença |
| RF19 — filtros | S8-F02 | Categoria, campus/instituto e intervalo combinados |
| RF20 — tema | S8-F02, S8-F04 | Persistência e contraste nos dois temas |
| RF21 — exportação direta Google Calendar | S7-F01, S7-B02, S7-F04, S8-F03 | Autorização adicional, exportação na Vercel, eventos no Google, retry sem duplicatas e renovação de tokens; ICS complementar |
| RNF01 — credenciais | S7-F04, S8-D02 | Configuração Auth verificada e ausência de senha em logs |
| RNF02 — privacidade | S7-D01, S7-B01, S8-B01, S8-D01, S8-D02 | Isolamento, compartilhamento explícito e ciclo de vida |
| RNF03 — TLS | S7-B02, S7-B06, S8-D02 | Vercel, API e conexão de banco verificadas |
| RNF04 — RBAC revisado | S7-F01, S7-F04, S8-F02, S8-D02 | Professor/admin moderam; admin gere papéis/categorias |
| RNF05 — API ≤300 ms em 95% | S8-F04 | Relatório de carga com metodologia |
| RNF06 — parser inferior a 20 s | S7-B01, S7-F03, S8-F04 | Medição com corpus até 10 páginas e progresso real |
| RNF07 — 360 px | S7-F02, S7-F03, S7-F04, S8-F01, S8-F02, S8-F04 | Verificação dos fluxos críticos responsivos |
| RNF08 — WCAG 2.1 AA | S8-F04 e telas de cada issue | Contraste e acessibilidade avaliados |
| RNF09 — feedback | Todas as issues com UI; S8-F04 | Sucesso, erro, vazio, progresso e recuperação |
| RNF10 — PDF inválido | S7-B01, S7-F03, S8-F04 | Casos corrompido/protegido/sem texto |
| RNF11 — falha externa isolada | S7-B02, S7-B03, S7-B05, S8-F04 | Indisponibilidade não impede agenda existente |
| RNF12 — navegadores | S8-F04 | Registro por navegador/versão, incluindo Safari real |
| RNF13 — padrões/testes | S7-F01, S7-B02, S7-B06 e cada issue; S8-F04, S8-F05 | CI, deploy reproduzível, testes essenciais e docs coerentes |

## Definition of Done para cada issue

- Fluxo integrado entre interface, API e banco no ambiente de homologação quando aplicável.
- Critérios de aceite demonstrados; testes relevantes de regra de negócio, falha e permissão incluídos.
- Migrations, índices e RLS avaliados em conjunto; dados existentes preservados.
- Estado vazio/erro/carregamento e acessibilidade básica tratados nas telas tocadas.
- Contrato e documentação atualizados junto da implementação, sem segredos ou dados reais sensíveis nos exemplos.
- Revisão por outra pessoa; evidências anexáveis à futura issue/PR.
- Nenhuma conclusão baseada apenas em mock, endpoint existente ou documento que descreve intenção futura.

## Revisão crítica dos documentos — grill-with-docs

### DOCUMENT OVERVIEW — Visão geral

A visão e os requisitos descrevem uma agenda acadêmica com 21 RF e 13 RNF. O plano acima transforma esse escopo e as decisões desta conversa em trabalho para duas sprints. Documentos orientam o produto; descrições de funcionalidades neles não provam que elas estejam implementadas.

### KEY CLAIMS — Afirmações principais

- “Há confirmação de candidatos no backend”: sustentado pelo router atual; não prova jornada completa.
- “Planos particulares devem ser confidenciais”: explícito no RNF02; exige revisão delimitada para permitir compartilhamento voluntário.
- “Parser inferior a 20 s” e “GET /events p95 ≤300 ms”: metas explícitas em RNF06/RNF05; cumprimento ainda depende de medição.
- “Todos os requisitos estarão prontos em 25/11”: objetivo do usuário; não é fato comprovado nem cronograma garantido sem conhecer capacidade e dependências.

### GRILL QUESTIONS — Perguntas para verificação

Estas perguntas são critérios de trabalho das issues, não pedidos para interromper o planejamento:

- RF05/RF06: como demonstrar o novo vínculo manual sem a documentação ainda prometer atestado? S7-F01, S7-F02.
- RNF02/RF07: exatamente quem pode ler uma versão e o PDF após compartilhamento/retirada? S7-D01 e S8-B01, S8-D01, S8-D02.
- RNF06: o tempo medido inclui espera na fila e chamada ao provedor? S7-B01 e S8-F04.
- RF16: qual chave impede que o mesmo evento se duplique entre coleta e cadastro manual? S7-B05.
- RF12/RF18: a interface diferencia participação local, inscrição externa e presença efetiva? S8-B02, S8-F02.

### WEAKNESSES AND GAPS — Lacunas

O RNF05 não define a carga de “uso normal”; sem metodologia, uma medição rápida isolada não demonstra conformidade. A configuração real de SMTP, limites do Gemini e execução gratuita de jobs precisa de prova. O frontend de revisão ainda não consome os candidatos. Essas lacunas tornam S7-B02, S7-B01, S7-F03 e S8-F04 decisivas para o prazo.

### CONTRADICTIONS — Contradições

- RF11 e visão permitem moderação por professores; RNF04 restringe moderação a admin. Resolver conforme decisão do usuário, distinguindo moderação de gestão de papéis/categorias.
- RF05/RF06 e visão ainda exigem atestado, mas a decisão atual substitui por catálogo público e seleção manual.
- RNF02 descreve confidencialidade estrita, enquanto colaboração requer acesso entre usuários. Delimitar compartilhamento explícito, sem expor os particulares.
- `docs.json` aponta navegação Mintlify; workflow `docs.yml` publica MkDocs. Verificar qual site deve refletir a entrega e alinhar as configurações.

### EVIDENCE CHECK — Evidências

Evidências locais: `docs/produto/requisitos.md`, `docs/produto/visao.md`, `docs/sprints/sprint-6.md`, `backend/src/modules/syllabus/router.py`, `backend/src/modules/syllabus/services.py`, `frontend/src/components/SyllabusReviewPanel.jsx`, `docs.json` e `.github/workflows/docs.yml`. O catálogo público Followw foi analisado no repositório local de referência; disponibilidade e contrato em produção ainda exigem prova S7-B02. A documentação hospedada em `https://docs.followw.app/arquitetura` não pôde ser validada nesta consulta.

Não foram executados testes da aplicação nem benchmark como parte desta organização. Nenhum RNF foi declarado atendido por essa inspeção.

### ASSUMPTIONS — Premissas

Equipe de seis pessoas mantém as áreas registradas na sprint 6. Início operacional considerado em 07/11, data desta análise. Antecedência inicial de lembrete em 24 h, congelamento em 20/11 e publicação automática de itens institucionais válidos são propostas deste plano, a registrar nos contratos. Acesso público Followw não garante disponibilidade permanente ou catálogo completo. Cotas gratuitas não garantem a meta de tempo do parser.

### STRONG POINTS — Pontos fortes

Os requisitos já possuem IDs estáveis, metas quantitativas para API/parser e regras de erro/privacidade. A sprint 6 explicita revisão humana, procedência e deduplicação; o endpoint de confirmação existente permite evoluir a solução sem reconstruir esse fluxo.

### QUESTIONS THE AUTHOR MUST BE READY TO ANSWER — Perguntas da banca/equipe

1. Quais RF foram alterados por decisão de produto e onde está registrada a justificativa?
2. Como se impede acesso cruzado a um PDF privado e duplicação por confirmação concorrente?
3. Qual evidência mostra coleta, parser e lembretes executando fora de uma demonstração manual?
4. Em qual carga, ambiente e corpus os RNF05/RNF06 foram medidos?
5. Quais serviços recebem dados, sob quais condições, e como o titular exerce seus direitos?

### FINAL ASSESSMENT — Avaliação

O escopo é identificável, mas a documentação ainda precisa refletir decisões e permissões atuais. Há base implementada reaproveitável, especialmente na confirmação de planos, e lacunas claras de integração. O planejamento cobre todos os RF/RNF; a conformidade da implementação permanece **parcial e não homologada** até a produção das evidências nas issues. Viabilidade de prazo depende especialmente de S7-B02 e de concluir a primeira jornada de planos ainda na sprint 7.

## Fontes externas e limites de integração

- [Vercel — Vite](https://vercel.com/docs/frameworks/frontend/vite): referência para publicação do frontend e configuração de rotas SPA; infraestrutura de API/jobs e limites do plano devem ser validados separadamente.
- [Google Calendar API — escopos](https://developers.google.com/workspace/calendar/api/auth) e [criação de eventos](https://developers.google.com/workspace/calendar/api/guides/create-events) fundamentam a integração direta.
- [Agenda UnB Notícias](https://noticias.unb.br/component/agenda/agendas): fonte pública escolhida para coleta de eventos; a existência de informes e períodos exige classificação e normalização.
- [Documentação de arquitetura Followw](https://docs.followw.app/arquitetura): referência fornecida pelo usuário; consulta hospedada indisponível nesta análise. Confirmar contrato público e ambiente em S7-B02, sem presumir acesso autenticado.
- [Supabase — SMTP](https://supabase.com/docs/guides/auth/auth-smtp): o envio padrão restringe destinatários e destina-se a testes; validar SMTP apropriado antes de fechar autenticação.
- [Gemini API — termos](https://ai.google.dev/gemini-api/terms): o serviço gratuito restringe envio de dados pessoais/confidenciais e informa uso de conteúdo para melhoria; conferir condições aplicáveis, inclusive elegibilidade, antes da implantação.
- [ANPD — guia de segurança para agentes de pequeno porte](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-vf.pdf): referência para controles e processo de segurança; não substitui definir o tratamento real de dados e suas responsabilidades.

## Rastreabilidade da publicação

As 21 issues foram publicadas e revisadas. A implementação continua pendente de validação pelos critérios de aceite. Consulte as páginas das sprints para títulos, responsáveis, dependências e checklists atualizados.

− S7-F01 — [#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)
− S7-B02 — [#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)
− S7-D01 — [#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)
− S7-B03 — [#70](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70)
− S7-F02 — [#71](https://github.com/unb-mds/2026-2-AgendaUnB/issues/71)
− S7-B01 — [#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51)
− S7-B04 — [#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)
− S7-F03 — [#73](https://github.com/unb-mds/2026-2-AgendaUnB/issues/73)
− S7-F04 — [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74)
− S7-B05 — [#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75)
− S7-B06 — [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)
− S8-B01 — [#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77)
− S8-F01 — [#78](https://github.com/unb-mds/2026-2-AgendaUnB/issues/78)
− S8-B02 — [#79](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79)
− S8-F02 — [#80](https://github.com/unb-mds/2026-2-AgendaUnB/issues/80)
− S8-B03 — [#81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81)
− S8-F03 — [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82)
− S8-D01 — [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83)
− S8-D02 — [#84](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84)
− S8-F04 — [#85](https://github.com/unb-mds/2026-2-AgendaUnB/issues/85)
− S8-F05 — [#86](https://github.com/unb-mds/2026-2-AgendaUnB/issues/86)

## Alteração aprovada — exportação direta Google

O sistema deve permitir selecionar período e eventos e exportá-los diretamente para uma agenda secundária Agenda UnB na conta Google autorizada, via Google Calendar API e consentimento OAuth adicional. Deve controlar duplicações e falhas parciais, permitir reexportação explícita para atualização e desconexão. A exportação ICS complementa a compatibilidade com Apple Calendar e Outlook. Sincronização automática bidirecional exige escopo próprio.

Preparação da API e consentimento em S7-B02 (#68), conexão e tokens em S7-F04 (#74), callbacks em S7-B06 (#76), exportação em S8-F03 (#82), privacidade em S8-D01 (#83), segurança em S8-D02 (#84) e homologação em S8-F04 (#85). Utilizar calendar.app.created e tokens do provedor Google, com renovação própria no servidor. Validar exigências de publicação OAuth e cotas na prova de infraestrutura. A implementação deve registrar IDs por conta, usuário e evento para recuperação de falhas parciais e reexportação idempotente.
