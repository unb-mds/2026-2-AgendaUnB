# Sprint 06 - Planos de ensino com IA e revisão assistida

**Período proposto:** 19/10/2026 - 01/11/2026

**Objetivo:** Implementar a primeira jornada completa de planos de ensino particulares: envio de PDF, extração de avaliações com IA, revisão pelo estudante e inclusão dos itens confirmados na agenda pessoal. Concluir também o backend pendente do painel administrativo (#38) e do upload de planos (#40), reaproveitando telas, RPCs e Storage já entregues.

## Principais atividades planejadas:

- Concluir os endpoints administrativos e de upload realocados da Sprint 05, exclusivamente no backend.
- Evoluir o esquema de planos para aceitar autoria estudantil, estados de processamento e candidatos com evidências de origem.
- Processar PDFs com texto selecionável, estruturando resultados de IA com validação e tratamento de ambiguidades.
- Criar envio, histórico e acompanhamento na página Plano de Ensino.
- Implementar revisão assistida e confirmação explícita antes da inclusão na agenda.
- Garantir privacidade, confirmação transacional e prevenção de duplicatas.
- Integrar frontend, backend e banco com testes de contratos, jornada e permissões reais.

## Escopo desta sprint

A entrega cobre **planos particulares**, PDF de até **10 MB e 10 páginas**, com texto selecionável. O limite de tamanho acompanha o bucket existente; a referência de 5 MB no texto original da #40 era um exemplo. PDF corrompido, protegido ou escaneado sem texto deve gerar erro recuperável e orientação para organização manual.

O Modelo Dual permanece como visão do produto. Planos oficiais por turma, upload de atestados do SIGAA, alocação automática, validação colaborativa, OCR e entrada por texto bruto ficam para uma etapa seguinte. O esquema deve permitir evolução sem prometer esses fluxos na Sprint 06. O provedor/modelo de IA será escolhido e registrado na S6-B01, sem pressupor uma integração já existente.

## Distribuição da equipe

Há **oito issues: seis novas e duas realocadas**, com pelo menos duas por área. As atribuições abaixo são propostas de responsabilidade principal; a outra pessoa da área participa de alinhamento e revisão.

| Área | Integrante | Issues principais |
| --- | --- | --- |
| Front-end | Thomas Araujo (@Thomas4ugust0) | S6-F01 — Envio e acompanhamento |
| Front-end | Gabriel Escramin (@Bielziin07) | S6-F02 — Revisão e agenda |
| Back-end | Heitor Monteiro (@heitormontt) | #40 — Upload; S6-B01 — Extração com IA |
| Back-end | Thomaz Marra (@marrathomaz) | #38 — Painel; S6-B02 — Consulta e confirmação |
| Banco de dados | Felipe Couto (@felipecduque7) | S6-D01 — Modelagem e candidatos |
| Banco de dados | Luis Davi (@pontesluis) | S6-D02 — Privacidade e confirmação |

O backend recebe quatro issues porque absorve #38 e #40. Ambas já tinham os dois integrantes como responsáveis no GitHub; a divisão principal acima não altera os assignees remotamente. Se a capacidade ficar apertada, priorizar o fluxo de planos e tornar explícito o impacto da #38 no fechamento; não declarar entrega sem concluir os critérios.

## Ordem de execução e dependências

1. Alinhar exemplos de payloads/estados e os contratos de #40 e S6-B02 com as duas issues de dados. O frontend começa com respostas simuladas desses contratos.
2. Executar S6-D01 e S6-D02 para liberar esquema, isolamento e operação de confirmação. #38 avança com as RPCs existentes, sem trabalho novo de frontend/banco administrativo.
3. Concluir #40 e S6-B01; conectar acompanhamento e revisão. A S6-B02 pode implementar listagem/detalhe antes de integrar a confirmação final.
4. Integrar confirmação na agenda e executar os cenários de privacidade, repetição e falhas. Cada issue inclui seus testes e documentação; não há issue genérica reservando a validação apenas para o final.

## Entregas/resultados esperados

- PDF particular enviado com segurança e consultável pelo próprio usuário.
- Avaliações extraídas como candidatos com trecho/página de origem e campos ambíguos identificados.
- Revisão manual antes da gravação; somente itens confirmados chegam à agenda.
- Lista e calendário exibindo os eventos importados, sem duplicação por repetição da confirmação.
- Políticas de banco/Storage testadas e contratos de API documentados.
- Endpoints REST da #38 concluídos respeitando as permissões atuais, sem reconstruir as telas já entregues.

## Definition of Done

A Sprint 06 será considerada concluída quando um estudante autenticado conseguir enviar um PDF válido, acompanhar o processamento real por IA, revisar os candidatos e salvar somente os selecionados na agenda privada, com procedência preservada. Recarregar ou repetir a confirmação não pode duplicar eventos. Outro usuário, visitante ou professor não pode ler esse plano particular ou seus resultados.

Deve haver verificação dos limites de arquivo, PDF inválido/sem texto, falha de IA, resultado vazio, revisão parcial e concorrência, com contratos atualizados. O tempo total para PDFs de até 10 páginas deve ser medido contra a meta de menos de 20 segundos do RNF06; desvio deve ser registrado e tratado como pendência. As rotas e os testes de #38 e #40 precisam estar concluídos. Todas as tarefas abaixo permanecem planejadas até implementação e validação.

## Issues da sprint

Os códigos S6-F/B/D são **identificadores locais de planejamento**, não números atribuídos pelo GitHub. #38 e #40 são issues existentes, abertas e sem milestone na consulta de 19/10/2026. O planejamento as aloca nesta sprint; as demais issues permanecem nas sprints originais, incluindo #39 e #45 ainda abertas na Sprint 05. Nenhuma milestone, issue, label ou atribuição foi alterada no GitHub por esta documentação.

Os textos de #38 e #40 abaixo são propostas de atualização das mesmas issues, não duplicatas. Ajustam o escopo ao código atual: moderação também por professores, RPCs existentes e limite de upload alinhado ao bucket.

| Identificador | Título | Área | Responsável principal | Situação |
| --- | --- | --- | --- | --- |
| #38 | Endpoints do Painel Administrativo | Back-end | Thomaz Marra | Realocada, aberta no GitHub |
| #40 | Endpoint Base de Upload de Plano de Ensino | Back-end | Heitor Monteiro | Realocada, aberta no GitHub |
| S6-F01 | Envio e Acompanhamento de Planos de Ensino | Front-end | Thomas Araujo | Proposta, ainda sem número no GitHub |
| S6-F02 | Revisão Assistida por IA e Importação na Agenda | Front-end | Gabriel Escramin | Proposta, ainda sem número no GitHub |
| S6-B01 | Extração Assíncrona de Avaliações com IA | Back-end | Heitor Monteiro | Proposta, ainda sem número no GitHub |
| S6-B02 | Consulta, Revisão e Confirmação de Planos na API | Back-end | Thomaz Marra | Proposta, ainda sem número no GitHub |
| S6-D01 | Modelagem de Planos Particulares e Resultados da IA | Banco de dados | Felipe Couto | Proposta, ainda sem número no GitHub |
| S6-D02 | Privacidade e Confirmação Transacional dos Planos | Banco de dados | Luis Davi | Proposta, ainda sem número no GitHub |

## Texto de cada issue

### #38 — Endpoints do Painel Administrativo

**Responsável principal:** Thomaz Marra (@marrathomaz).

**Labels propostas:** Back-end; 02. MÉDIA PRIORIDADE.

**Dependências:** RPCs e políticas administrativas já existentes (#42).

**Concluir as rotas REST do painel administrativo, reaproveitando as RPCs e regras de moderação já entregues. A realocação da Sprint 05 envolve somente backend; não exige refazer telas ou migrações administrativas.**

Tasks:

- [ ] Implementar `GET /api/v1/admin/events/pending` e `PATCH /api/v1/admin/events/{id}/review`, permitindo moderação por professores e administradores.
- [ ] Implementar `GET /api/v1/admin/users` e `PATCH /api/v1/admin/users/{id}/role`, exclusivos de administradores.
- [ ] Reaproveitar as regras das RPCs: justificativa obrigatória na recusa, bloqueio de decisões concorrentes e impedimento de remover o próprio cargo de admin.
- [ ] Preservar a exceção de atribuição de professor por admin a outro domínio, sem permitir autopromoção indevida.
- [ ] Permitir PATCH no CORS para as origens configuradas e documentar payloads e respostas na OpenAPI.
- [ ] Testar 401/403, perfis permitidos, concorrência e preservação das notificações transacionais, sem refazer o frontend.

### #40 — Endpoint Base de Upload de Plano de Ensino

**Responsável principal:** Heitor Monteiro (@heitormontt).

**Labels propostas:** Back-end; 03. ALTA PRIORIDADE.

**Dependências:** S6-D01 e S6-D02; bucket e RLS de Storage já existentes (#43).

**Concluir o upload autenticado de planos particulares de estudantes, usando o bucket privado já criado. A realocação da Sprint 05 envolve somente backend; o esquema de rastreamento será tratado pelas novas issues de dados.**

Tasks:

- [ ] Implementar `POST /api/v1/syllabus/upload` com sessão validada e autoria obtida do token.
- [ ] Validar extensão, MIME, assinatura e leitura do PDF, com limite de 10 MB alinhado ao bucket e até 10 páginas para o recorte da sprint.
- [ ] Rejeitar arquivos protegidos, corrompidos ou sem texto selecionável com instrução de correção e alternativa de cadastro manual.
- [ ] Gravar em `syllabus_files/<user_id>/<identificador>.pdf`, sem expor chave de serviço ou URL pública.
- [ ] Criar o rastreamento como `pendente` e retornar 202 com o ID; compensar upload ou registro parcial em caso de falha.
- [ ] Testar autenticação, limites, arquivos inválidos e falhas do Storage e documentar o contrato para integração.

### S6-F01 — Envio e Acompanhamento de Planos de Ensino

**Responsável principal:** Thomas Araujo (@Thomas4ugust0).

**Labels propostas:** Front-end; 03. ALTA PRIORIDADE.

**Dependências:** Contratos de #40 e S6-B02; o frontend pode começar com respostas simuladas.

**Implementar o envio autenticado de planos particulares e o histórico de processamento em `/plano-de-ensino`, substituindo o aviso atual por um fluxo utilizável e responsivo (RF05, RF06, RNF07 e RNF09).**

Tasks:

- [ ] Criar formulário de envio de PDF com disciplina e semestre/ano de referência, informando limites de 10 MB e 10 páginas e a exigência de texto selecionável.
- [ ] Integrar `POST /api/v1/syllabus/upload`, impedir cliques duplicados e abrir acompanhamento pelo ID retornado.
- [ ] Criar histórico paginado com os próprios planos e integrar `GET /api/v1/syllabus` e `GET /api/v1/syllabus/{id}`.
- [ ] Exibir `pendente`, `processando`, `concluido` e `falha`, distinguindo falha de resultado sem avaliações e sem percentual de progresso fictício.
- [ ] Consultar em intervalos controlados, interromper consultas ao sair da tela ou alcançar estado final e permitir retomar a revisão após recarregar.
- [ ] Apresentar erros recuperáveis e alternativa de cadastro manual; validar teclado, telas a partir de 360px e temas claro/escuro.

### S6-F02 — Revisão Assistida por IA e Importação na Agenda

**Responsável principal:** Gabriel Escramin (@Bielziin07).

**Labels propostas:** Front-end; 03. ALTA PRIORIDADE.

**Dependências:** S6-F01 e contrato de confirmação de S6-B02.

**Permitir ao estudante revisar, corrigir e selecionar as avaliações extraídas pela IA e confirmar sua inclusão em Meus Eventos, em lista e calendário (RF07, RF08 e RF09).**

Tasks:

- [ ] Exibir título, tipo, data sugerida, página e trecho de origem de cada candidato, destacando dados ausentes ou ambíguos.
- [ ] Permitir corrigir os campos, selecionar ou descartar itens e exigir data, horário e fuso explícitos para os selecionados, sem inferência silenciosa.
- [ ] Integrar `POST /api/v1/syllabus/{id}/confirm`, impedir envio duplicado e preservar as edições se a operação falhar.
- [ ] Apresentar quantidade confirmada, atualizar Meus Eventos e mostrar os compromissos em lista e calendário mensal/semanal.
- [ ] Exibir a procedência do plano retornada pela API e preservar a edição/exclusão de privados e o comportamento dos públicos salvos.
- [ ] Verificar a jornada PDF → acompanhamento → revisão → agenda, inclusive revisão parcial, recarga, erros e confirmação repetida, nos dois temas e com teclado.

### S6-B01 — Extração Assíncrona de Avaliações com IA

**Responsável principal:** Heitor Monteiro (@heitormontt).

**Labels propostas:** Back-end; 03. ALTA PRIORIDADE.

**Dependências:** #40 e S6-D01; políticas de S6-D02 antes da integração com dados reais.

**Processar PDFs com texto selecionável e transformar o cronograma em candidatos estruturados a avaliações, sem criar compromissos antes da revisão do estudante (RF06 e RNF06).**

Tasks:

- [ ] Extrair texto com referência de página e implementar processamento fora do ciclo da requisição, com estado persistido e recuperação de tarefas interrompidas.
- [ ] Definir e documentar provedor/modelo de IA, configuração por ambiente, limite de custo por arquivo, timeout e tentativas limitadas; manter credenciais somente no servidor.
- [ ] Validar saída estruturada contendo título, tipo, data/horário quando presentes e evidência de origem; marcar ambiguidades sem inventar informações ausentes.
- [ ] Tratar o conteúdo do PDF como dados e validar a resposta da IA antes de persistir candidatos privados; não gravar PDFs ou texto integral em logs.
- [ ] Tratar falhas do provedor e documentos sem cronograma, registrando `falha` ou resultado vazio conforme o caso.
- [ ] Criar amostras anonimizadas com referência esperada e medir extrações corretas, omissões, datas inventadas e tempo total; verificar a meta de menos de 20s para PDFs de até 10 páginas e registrar desvios.

### S6-B02 — Consulta, Revisão e Confirmação de Planos na API

**Responsável principal:** Thomaz Marra (@marrathomaz).

**Labels propostas:** Back-end; 03. ALTA PRIORIDADE.

**Dependências:** #40, S6-B01, S6-D02.

**Disponibilizar o resultado do processamento somente ao dono e confirmar avaliações revisadas na agenda pessoal, com transação e proteção contra duplicação (RF07 e RF09).**

Tasks:

- [ ] Publicar primeiro os contratos de `GET /api/v1/syllabus`, `GET /api/v1/syllabus/{id}` e `POST /api/v1/syllabus/{id}/confirm`, permitindo avanço paralelo do frontend.
- [ ] Implementar listagem paginada, estado, falhas e candidatos com procedência; conferir propriedade em todas as operações.
- [ ] Validar itens selecionados, campos corrigidos, IDs de origem e fuso explícito, sem aceitar candidatos pertencentes a outro plano/usuário.
- [ ] Usar a persistência transacional e idempotente de S6-D02 para criar somente compromissos particulares confirmados; devolver IDs dos eventos e origem nas consultas pessoais.
- [ ] Restringir a confirmação a processamento concluído e retornar erro recuperável para dados inválidos sem gravação parcial.
- [ ] Testar acesso cruzado, falha do processamento, revisão parcial, repetição/concorrência e a jornada integrada com banco e Storage locais.

### S6-D01 — Modelagem de Planos Particulares e Resultados da IA

**Responsável principal:** Felipe Couto (@felipecduque7).

**Labels propostas:** Banco de dados; 03. ALTA PRIORIDADE.

**Dependências:** Contrato alinhado com #40 e S6-B01; reaproveita #43.

**Evoluir o esquema de planos e avaliações para uploads particulares de estudantes e candidatos extraídos com procedência, preservando dados existentes e separando sugestões da IA dos compromissos confirmados (RF05–RF07).**

Tasks:

- [ ] Migrar a estrutura atual para identificar proprietário e tipo de plano, sem exigir professor/turma em uploads particulares nem reutilizar `professor_id` com significado incorreto.
- [ ] Adicionar metadados de arquivo, caminho privado, disciplina, semestre/ano, datas, erro sanitizado e estados `pendente`, `processando`, `concluido` e `falha`.
- [ ] Modelar candidatos com título, tipo, data/horário opcionais, ambiguidade, página e trecho de origem, versão de processamento e provedor/modelo.
- [ ] Distinguir candidato pendente, descartado e confirmado, sem criar eventos pessoais automaticamente; evitar duplicação na repetição da mesma execução.
- [ ] Definir vínculo entre candidato e evento pessoal confirmado, com unicidade e comportamento documentado para posterior edição/exclusão do evento.
- [ ] Criar constraints e índices, preparar referência opcional a planos oficiais futuros e testar a migração com dados existentes, sem implementar turmas/matrículas nesta sprint.
- [ ] Atualizar DER e dicionário de dados, alinhando contratos com #40, S6-B01 e S6-B02.

### S6-D02 — Privacidade e Confirmação Transacional dos Planos

**Responsável principal:** Luis Davi (@pontesluis).

**Labels propostas:** Banco de dados; 03. ALTA PRIORIDADE.

**Dependências:** S6-D01, contrato de confirmação de S6-B02 e bucket/RLS existentes da #43.

**Proteger planos particulares e resultados extraídos e disponibilizar a confirmação atômica na agenda privada, sem duplicação. Corrigir a leitura pública de avaliações e reaproveitar o bucket já entregue (RF07, RF09, RNF02 e RNF04).**

Tasks:

- [ ] Substituir `avaliacoes sao publicas` por acesso vinculado ao proprietário e criar RLS de planos, candidatos e vínculos de confirmação.
- [ ] Impedir leitura/escrita entre usuários, alteração indevida de autoria e acesso de professores a planos particulares de terceiros.
- [ ] Revalidar as políticas do bucket existente com pastas por usuário e acesso anônimo negado; não recriar o bucket da #43.
- [ ] Criar a operação transacional de confirmação: validar dono e seleção, gravar somente os eventos aprovados pelo estudante e evitar gravação parcial.
- [ ] Garantir idempotência e unicidade por candidato em confirmações repetidas ou concorrentes; descartar candidato não pode criar compromisso.
- [ ] Limitar execução das operações privilegiadas e documentar validações obrigatórias quando o backend usa conexão que ignora RLS.
- [ ] Testar em PostgreSQL com papéis `anon` e `authenticated`: dono, outro usuário, Storage, rollback e concorrência; atualizar documentação das políticas.

## Base documental

- [Requisitos](../requisitos.md): RF05–RF09, RNF02, RNF04, RNF06, RNF07, RNF09 e RNF10.
- [Documento de visão](../documento-de-visao.md): Modelo Dual e prioridade da extração assistida.
- [Arquitetura](../Architecture.md): FastAPI, Supabase Auth/Storage e estado atual do processamento.
- [Especificação de banco](../especificacao-banco-de-dados.md) e [modelo de dados](../modelo-de-dados.md): estruturas existentes, que precisam evoluir para propriedade estudantil e estados.
- [Painel administrativo](../painel-administrativo.md): permissões, RPCs e notificações já entregues.
- Migrações `20260923172640` e `20261014120200`: planos atuais com `professor_id` obrigatório, leitura pública de avaliações e bucket PDF privado de até 10 MB. Essas limitações fundamentam as issues de dados.
