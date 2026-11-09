---
title: "Sprint 08 - Release 2"
sidebarTitle: "Sprint 8"
---

# Sprint 8

Planejamento aprovado para 16–23/11/2026. Entrega final em 25/11/2026. As tarefas abaixo representam trabalho planejado e dependem das evidências de aceite para conclusão.

## Decisões da entrega

Consulte os [contratos](../atualizacoes.md#contratos-da-release-2) e a [matriz de aceite](../matriz-release-2.md) para os critérios vigentes.

- Seleção manual de turmas pelo catálogo público Followw, com vínculo autodeclarado.
- Planos privados por padrão, com edição conforme papel e visibilidade. Compartilhamento voluntário de conteúdo revisado. O PDF original é descartado após a extração local.
- IA limitada a provas e trabalhos, com revisão do texto antes do envio e confirmação antes da criação de eventos.
- A Agenda UnB Notícias alimenta o catálogo. Eventos completos são publicados automaticamente e exceções seguem para revisão. Adicionar aos meus eventos e Conferir evento são ações independentes.
- Professores e administradores moderam eventos. Administradores gerenciam papéis e categorias.
- Lembretes na plataforma 24 horas antes de eventos da própria agenda. Exportação direta ao Google Agenda com consentimento adicional e e-mail verificado correspondente. ICS complementa Apple Calendar e Outlook.
- Primeira URL Vercel até 12/11 e ambiente integrado até 15/11. Congelamento funcional em 20/11, homologação até 23/11, ensaio em 24/11 e aceite em 25/11.

## Organização

F identifica frontend, B backend e D dados. A numeração é independente por área e sprint. Para atividades transversais, a área corresponde à frente coordenadora. Prioridades foram atribuídas considerando dependências e marcos da entrega. Cada issue tem até dois responsáveis formais, com apoios adicionais registrados no conteúdo.

[Milestone da Sprint 8](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)

## Issues planejadas

### S8-B01 - Implementar compartilhamento, versões e votação dos planos

[Issue #77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77)

#### Objetivo

Permitir que usuários autenticados que seguem uma oferta consultem, avaliem e importem versões compartilhadas voluntariamente.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 16–18/11/2026
- **Responsável principal** @marrathomaz
- **Corresponsável** @felipecduque7
- **Dependências** S7-D01 ([#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69)), S7-B04 ([#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)) e S7-F03 ([#73](https://github.com/unb-mds/2026-2-AgendaUnB/issues/73)).
- **Requisitos** RF05, RF07 e RNF02.

#### Tasks

- [ ] Autor publica voluntariamente conteúdo revisado. Autor ou admin pode retirar uma versão. Autor pode editar o próprio plano. Professor e admin podem editar versões compartilhadas conforme o contrato.
- [ ] Explicar o conteúdo compartilhado e restringir leitura a seguidores autenticados da turma. O PDF original é descartado após extração local.
- [ ] Criar voto único ativo por conta/candidato/versão, editável pelo autor do voto. Mostrar contagem e divergência, sem alterar datas automaticamente ou tratar votação como prova.
- [ ] Gerar nova versão a cada revisão sem alterar calendários pessoais. Deduplicar importações por usuário/candidato/versão e aplicar a política de retirada.

#### Critérios de aceite

- [ ] Dois seguidores da mesma turma leem a versão e importam para agendas privadas independentes. Visitante e usuário sem vínculo são recusados. O vínculo aparece como autodeclarado.
- [ ] Voto repetido mantém a contagem e permite corrigir o próprio voto. Versão nova preserva eventos importados.
- [ ] Retirar a versão impede novos acessos e importações e preserva cópias particulares já importadas conforme a política registrada.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-F01 - Entregar biblioteca de planos e validação colaborativa na interface

[Issue #78](https://github.com/unb-mds/2026-2-AgendaUnB/issues/78)

#### Objetivo

Dar acesso à biblioteca de planos por oferta de turma, incluindo versões, votação e importação de avaliações selecionadas.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 16–19/11/2026
- **Responsável principal** @Thomas4ugust0
- **Corresponsável** @Bielziin07
- **Dependências** S7-F02 ([#71](https://github.com/unb-mds/2026-2-AgendaUnB/issues/71)), S7-F03 ([#73](https://github.com/unb-mds/2026-2-AgendaUnB/issues/73)) e S8-B01 ([#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77)).
- **Requisitos** RF05, RF07, RNF07–RNF09.

#### Tasks

- [ ] Listar versões com autor/tipo de autoria, origem e data. Diferenciar contribuição de colega, perfil professor e origem institucional comprovada.
- [ ] Permitir abrir uma versão, revisar avaliações, votar e importar itens selecionados. Indicar votos, divergências e itens já importados.
- [ ] Adicionar publicação e retirada com confirmação clara, consulta a versões e ação de envio vinculada à oferta quando não houver plano.

#### Critérios de aceite

- [ ] Novo usuário segue a turma, abre um plano existente e importa avaliações sem reenviar arquivo.
- [ ] Colega publica e retira compartilhamento. Divergências, ações e limites de acesso ficam claros em desktop e celular. Nova versão preserva o evento pessoal já importado.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-B02 - Consolidar eventos salvos, redirecionamento e histórico

[Issue #79](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79)

#### Objetivo

Consolidar a distinção entre adicionar evento à agenda pessoal e conferir a fonte. Exibir históricos separados para públicos salvos e compromissos privados.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 16–19/11/2026
- **Responsável principal** @marrathomaz
- **Corresponsável** @felipecduque7
- **Apoio adicional** Gabriel apoia a integração da interface e do histórico.
- **Dependências** S7-F01 ([#67](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)) e modelo público consolidado em S7-B05 ([#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75)).
- **Requisitos** RF12, RF13, RF18 e RNF04.

#### Tasks

- [ ] Reutilizar o vínculo de evento salvo com unicidade por conta e evento. Adicionar e remover são operações idempotentes.
- [ ] Registrar métricas agregadas de redirecionamento em Conferir evento, sem alterar os vínculos. A inscrição externa, quando exigida, ocorre no canal do organizador.
- [ ] Mostrar eventos públicos salvos passados e compromissos privados passados em históricos separados. Remover o vínculo cancela lembretes futuros ([#81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81)).

#### Critérios de aceite

- [ ] Repetir adição e remoção sem duplicar vínculo. Verificar histórico, agenda e cancelamento de lembrete futuro.
- [ ] Abrir o link oficial, verificar incremento do redirecionamento e ausência de mudança na agenda. Repetir a mesma requisição sem duplicar o contador.
- [ ] Recusar adição de evento indisponível e alteração de vínculo de outra conta.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-F02 - Fechar eventos, moderação, agenda e melhorias de uso

[Issue #80](https://github.com/unb-mds/2026-2-AgendaUnB/issues/80)

#### Objetivo

Completar e homologar agenda, eventos, filtros e moderação nos fluxos existentes, mantendo o escopo focado nesses ajustes.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 16–20/11/2026
- **Responsável principal** @Bielziin07
- **Corresponsável** @marrathomaz
- **Apoio adicional** Thomas apoia a interface, os filtros e os ajustes de uso.
- **Dependências** S7-B05 ([#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75)) e integração final com S8-B02 ([#79](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79)). Reaproveitar [#14](https://github.com/unb-mds/2026-2-AgendaUnB/issues/14), [#15](https://github.com/unb-mds/2026-2-AgendaUnB/issues/15), [#36](https://github.com/unb-mds/2026-2-AgendaUnB/issues/36), [#37](https://github.com/unb-mds/2026-2-AgendaUnB/issues/37), [#38](https://github.com/unb-mds/2026-2-AgendaUnB/issues/38) e [#42](https://github.com/unb-mds/2026-2-AgendaUnB/issues/42).
- **Requisitos** RF08–RF11, RF12, RF14, RF15, RF18–RF20, RNF04 e RNF07–RNF09.

#### Tasks

- [ ] Verificar mês, semana e lista, CRUD particular, submissão estudantil pendente, publicação direta por professor/admin e aprovação/rejeição com motivo.
- [ ] Validar moderação por professor/admin e restringir gestão de papéis e categorias a admin.
- [ ] Completar detalhes e filtros combináveis por categoria, campus/instituto e intervalo. Representar os cinco campi com dados efetivamente disponíveis.
- [ ] Persistir tema e filtros úteis. Implementar vazio, limpeza de filtros, feedback de erro e confirmação de ações destrutivas.

#### Critérios de aceite

- [ ] Exercitar a matriz visitante/aluno/professor/admin. Aluno não publica diretamente e professor não altera papéis ou categorias.
- [ ] Preservar data, horário ou dia inteiro, intervalo, local e URL do formulário à tela. Verificar fuso, eventos de vários dias e combinação de filtros.
- [ ] Confirmar legibilidade nos dois temas e distinção entre participação e eventos particulares.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-B03 - Entregar lembretes persistentes dentro da plataforma

[Issue #81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81)

#### Objetivo

Notificar dentro do Agenda UnB 24 horas antes do início de eventos da própria agenda, incluindo compromissos privados e eventos públicos adicionados.

- **Sprint** [Sprint 08](https://github.com/unb-mds/2026-2-AgendaUnB/milestone/8)
- **Janela** 16–19/11/2026
- **Responsável principal** @heitormontt
- **Corresponsável** @pontesluis
- **Apoio adicional** Gabriel apoia a central de notificações.
- **Dependências** S7-B02 ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)), S7-B04 ([#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)) e S8-B02 ([#79](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79)).
- **Requisitos** RF13, RF17 e RNF02.

#### Tasks

- [ ] Agendar lembrete 24 horas antes do início. Para dia inteiro, usar meia-noite no primeiro dia local. Itens incluídos após o disparo previsto seguem sem aviso retroativo.
- [ ] Criar scheduler persistente e chave idempotente por usuário/evento/antecedência/versão relevante. Criar central simples com estados lida/não lida.
- [ ] Reprogramar pendências quando o início mudar e cancelar notificações futuras ao excluir compromisso ou remover o vínculo da agenda. Persistir os avisos na plataforma.

#### Critérios de aceite

- [ ] Reiniciar e repetir job sem duplicar lembretes. Verificar aviso persistido após retorno do usuário, isolamento entre usuários, cancelamento e reprogramação.
- [ ] Documentar e testar o comportamento de evento criado dentro da janela de antecedência.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-F03 - Exportar diretamente para o Google Agenda via Calendar API

[Issue #82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82)

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

- [ ] Implementar “Conectar Google Agenda” com consentimento adicional e escopo `calendar.app.created`. Aceitar apenas conta Google com e-mail verificado correspondente ao da conta Agenda UnB. Integrar com [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74).
- [ ] Criar uma agenda secundária “Agenda UnB” após autorização e persistir seu calendarId associado ao usuário e à conta Google. Reutilizar essa agenda nas próximas exportações.
- [ ] Permitir selecionar período e eventos da própria agenda e confirmar o envio de título, descrição selecionada, local e datas em `America/Sao_Paulo`. Incluir compromissos privados e eventos públicos adicionados. Manter PDF, texto integral, dados de terceiros e segredos fora do payload.
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


### S8-D01 - Concluir privacidade, termos e ciclo de vida dos dados

[Issue #83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83)

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

- [ ] Demonstrar acesso e exclusão ponta a ponta. Verificar descarte do PDF após extração local, eliminação de originais legados e tratamento de tarefas pendentes e cópias independentes.
- [ ] Verificar que conteúdo acadêmico e tokens não aparecem em logs. Anexar evidência da revisão técnica e documental e registrar seu escopo.

#### Evidências para fechamento

- [ ] Anexar à issue o PR, a versão implantada e o resultado de cada cenário dos critérios de aceite, identificando falhas ainda abertas.
- [ ] Registrar o nome do revisor e a revisão dos contratos, permissões e dados afetados por esta entrega.


### S8-D02 - Verificar segurança e corrigir falhas de autorização

[Issue #84](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84)

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


### S8-F04 - Homologar requisitos não funcionais e jornadas completas

[Issue #85](https://github.com/unb-mds/2026-2-AgendaUnB/issues/85)

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
- [ ] Exercitar cadastro → turma → plano → importação, compartilhamento → voto → importação por colega e evento coletado → adicionar à agenda → lembrete → histórico → exportação Google. Testar também o redirecionamento independente da agenda.
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


### S8-F05 - Fechar documentação, operação e pacote de entrega

[Issue #86](https://github.com/unb-mds/2026-2-AgendaUnB/issues/86)

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



## Esclarecimentos de contrato — 08/11/2026

O RNF11 cobre exclusivamente a indisponibilidade do Followw. Referências anteriores deste planejamento a RNF11 em coleta de notícias, exportação ou infraestrutura geral não ampliam essa garantia; permanecem os contratos específicos dessas funcionalidades.

Toda data extraída começa como candidata. Somente a confirmação explícita do usuário a transforma em avaliação efetiva na sua agenda; em versões compartilhadas, essa decisão pertence a cada conta. A revisão deve ser breve: mostrar candidatos em uma lista, permitir selecionar vários e confirmar o lote em uma única ação, destacar apenas campos ambíguos que exigem correção e preservar as escolhas durante ajustes. Não exigir uma sequência de confirmações por item nem importar automaticamente. Avaliar a fluidez na homologação com o tempo e as dificuldades observadas, sem inventar um limite numérico ainda não acordado.

Retirar o compartilhamento da versão original não retira nem exclui suas revisões: elas mantêm sua própria visibilidade e continuam disponíveis quando compartilhadas. Cópias já importadas na agenda também permanecem. Essa regra trata da retirada de compartilhamento, não define a política de exclusão de conta.

Uma revisão feita por professor ou admin mantém a procedência institucional já validada da versão de origem. Registrar a versão de origem, a evidência institucional herdada, o autor da revisão e seu papel no momento da alteração. A interface distingue documento institucional de origem e alterações posteriores da comunidade. Papel professor/admin não cria procedência institucional quando a origem não a possuía; revisões estudantis não recebem essa herança automaticamente.

A confirmação e reimportação devem seguir a chave por ação descrita nos [contratos da R2](../atualizacoes.md#confirmacao-rapida-e-reimportacao). Professor/admin publicam diretamente suas revisões de conteúdo já compartilhado.
