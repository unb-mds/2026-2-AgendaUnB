---
title: "Atualizações pós-Release 1"
---

**Atualização: Registro histórico da Sprint 7 e 8 em 08/11/2026, para os contratos da R2.**

## Agenda e calendário

- `/eventos` substitui `/segunda-pagina` como rota principal. A rota antiga redireciona preservando parâmetros e fragmento; `#plano-de-ensino` abre a página independente de planos.
- Catálogo e Meus Eventos oferecem lista e calendário mensal/semanal, mantendo busca e filtros por campus, área e turno.
- O calendário permite avançar/voltar períodos e retornar a Hoje; a grade tem rolagem horizontal em telas pequenas e usa datas locais do navegador.
- **Adicionar aos meus eventos** salva um vínculo com o evento público aprovado, mantendo seus dados atualizados a partir do original. Remover o vínculo não exclui o evento. Salvar não equivale a inscrição ou confirmação de participação.

## Sugestões, notificações e administração

- Estudantes sugerem eventos no mesmo formulário Criar Evento, selecionando a visibilidade apropriada. A API e o banco mantêm essas propostas pendentes até análise.
- `/sugestoes` permite a professores e administradores consultar pendências e histórico, buscar, paginar e aprovar/recusar propostas. Recusas exigem justificativa de até 2.000 caracteres.
- Notificações persistidas confirmam envio e comunicam aprovação/recusa ao estudante. O sino mostra contagem de não lidas e permite marcá-las como lidas; atualiza ao enviar, ao retornar à janela e a cada 30 segundos.
- `/admin`, exclusivo de admins, permite busca por nome/e-mail, filtros de papel e confirmação de e-mail, consulta ao último acesso e alteração de cargos com confirmação.
- RPCs verificam permissões no banco, detectam alterações concorrentes e impedem o admin de remover o próprio acesso. Cadastro e autopromoção para professor exigem `@unb.br`; atribuição por admin admite outro domínio.

## API e persistência

A FastAPI ganhou `POST /api/v1/suggestions` e GET/PUT/DELETE de `/api/v1/me/saved-events`, conforme [Padrões](produto/padroes.md). Moderação e gestão de usuários usam RPCs do Supabase, não as rotas `/admin` propostas anteriormente.

Após as cinco migrações da base R1, o repositório inclui:

| Migração | Mudança |
| --- | --- |
| `20261014120000` | Sugestões pendentes, justificativa de recusa e contador de interessados |
| `20261014120100` | Regras de acesso e RPCs administrativas |
| `20261014120200` | Bucket privado `syllabus_files`, PDF até 10 MB e isolamento por pasta do usuário |
| `20261016000000` | Vínculos de eventos públicos salvos com RLS por proprietário |
| `20261018000000` | Moderação por professores/admins, RPCs paginadas, origem estudantil e notificações transacionais |
| `20261018000100` | Atribuição de professor por admin sem restrição de domínio; cadastro/autopromoção continuam institucionais |

Aplique as migrações pendentes em ordem antes de disponibilizar o código atualizado. No ambiente local já iniciado: `npx supabase migration up --local`. Os detalhes estão nos guias de [eventos salvos](eventos-salvos.md) e [painel administrativo](painel-administrativo.md).

## Ainda em preparação

`/plano-de-ensino` continua informativo e oferece organização manual da agenda.
No backend, #40/S6-B01 disponibilizam upload autenticado e worker separado para
candidatos privados com procedência, recuperação e limite de custo. O worker fica
desativado por padrão. As políticas e a revisão transacional S6-D02 foram validadas
em PostgreSQL isolado; dados reais exigem aplicá-las/homologá-las no destino. Tela e
endpoints de revisão/confirmacão ainda pertencem à S6-B02.
Ver [operação](processamento-planos.md) e [privacidade](privacidade-planos.md).
Upload de atestados e validação colaborativa continuam planejados, assim como
inscrições, histórico de participação, lembretes de proximidade, exportação `.ics`
e coleta externa.

## Verificação disponível

O projeto contém testes pytest da API (eventos, sugestões e vínculos salvos), testes Node de calendário e testes PostgreSQL de RLS/RPC/triggers. Estes últimos exigem `TEST_SUPABASE_DB_URL` local e são ignorados se ela não estiver configurada. Consulte [Contribuição](processo/contribuindo.md). A existência das suítes não afirma execução ou aprovação em um ambiente de produção.

# Contratos da Release 2

Contrato de implementação da [S7-F01 (#67)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67). Os exemplos descrevem a interface alvo e usam dados fictícios. A [API atual](api-specs.md) documenta as rotas em funcionamento. A [matriz de aceite](matriz-release-2.md) registra responsáveis, cenários e evidências.

## Catálogo e vínculo com a turma

O backend consulta exclusivamente o catálogo público do Followw. Cada oferta tem um UUID local imutável. Preferir uma chave da origem que identifique inequivocamente a **oferta**. Se a origem só fornecer o ID da disciplina, combinar origem, ID da disciplina, número da turma, ano, semestre, unidade e nível. Se faltar o ID da disciplina, usar o código normalizado no lugar dele. Preservar o número da turma como texto, inclusive zeros à esquerda. Professor e horário são atributos atualizáveis. Chave incompleta ou colisão que não possa ser resolvida pela origem exige revisão antes de disponibilizar a oferta.

`GET /api/v1/class-offerings?year=2026&semester=2&unit=FGA&subject_code=FGA0001&limit=20&offset=0` retorna o catálogo paginado para conta autenticada. `PUT /api/v1/me/class-offerings/{id}` registra o vínculo autodeclarado e `DELETE` na mesma rota remove o vínculo. A identidade vem da sessão. A chave `(user_id, class_offering_id)` impede duplicatas e mantém ofertas de semestres diferentes separadas.

```json
{
  "items": [{
    "id": "11111111-1111-4111-8111-111111111111",
    "source": "followw",
    "subject_code": "FGA0001",
    "section": "01",
    "year": 2026,
    "semester": 2,
    "unit": "FGA",
    "education_level": "undergraduate"
  }],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "source_updated_at": "2026-11-07T18:00:00Z",
  "stale": true
}
```

Em falha da origem, retornar o último catálogo válido com `stale: true` e preservar os vínculos existentes. Sem cache, devolver 503 à consulta do catálogo. O envio ou vínculo com oferta fora do catálogo disponível é bloqueado. A interface oferece nova busca e o cadastro manual de compromissos na agenda. O vínculo autoriza acesso ao conteúdo compartilhado da oferta e representa uma declaração do usuário. Matrícula, notas, avisos privados e login Followw/SIGAA ficam fora dessa integração. A [#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68) ainda precisa comprovar endpoints públicos, cobertura e paginação. A [#70](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70) implementa o adaptador e a [#69](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69) valida as chaves.

## Plano, versão e candidatos

A decisão sobre retenção de PDFs e autorização do texto está no [ADR-003](arquitetura/adrs/adr-003-minimizar-dados-de-planos.md).

- **Envio.** `POST /api/v1/syllabus/upload` mantém `multipart/form-data` e devolve 202. Para novos planos, exige `class_offering_id` de uma turma disponível que o usuário segue e exatamente um de `file` (PDF digital até 10 MB e 10 páginas) ou `text` (texto bruto, com limite de entrada a confirmar na [#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51)). As leituras existentes em `GET /syllabus` e `GET /syllabus/{id}` continuam disponíveis ao dono, inclusive para registros antigos sem oferta.
- **PDF e revisão.** O arquivo passa apenas pela extração local. Descartar bytes, arquivos temporários e caminhos acessíveis assim que essa etapa terminar, inclusive em erro ou interrupção. Persistir somente texto necessário, metadados e candidatos autorizados. A versão começa privada. A interface exibe o texto minimizado exato e o destino antes de enviar `POST /api/v1/syllabus/{id}/versions/{version_id}/processing-jobs`. O detalhe privado do plano devolve `version_id`, `phase` e `review_text` ao autor na etapa de autorização. O POST recebe `{"approved_text":"Trecho revisado e minimizado"}`. O servidor registra a autorização daquela versão e do texto aprovado. Mudança de texto exige nova revisão e autorização. Ao Gemini vai apenas o texto autorizado. Repetir a mesma operação retoma o job e preserva a unicidade dos candidatos.
- **Edição e visibilidade.** O autor edita suas versões privadas e compartilhadas. Professor e admin podem editar o conteúdo de uma versão já compartilhada, criando uma revisão separada. O papel por si só não dá acesso a PDF, texto original, candidatos privados ou agenda alheia. `POST /api/v1/syllabus/{id}/versions` cria uma revisão e mantém a versão anterior e as cópias na agenda. `PUT /api/v1/syllabus/{id}/versions/{version_id}/sharing` publica conteúdo revisado mediante decisão do autor. Professor e admin também podem publicar diretamente as revisões que criam a partir de conteúdo já compartilhado, sem aprovação adicional do autor original. Essa permissão não permite tornar público material privado alheio. `DELETE` no mesmo recurso retira o compartilhamento pelo autor ou admin, bloqueando novos acessos, votos e importações. Retirar o compartilhamento da versão original não retira nem exclui suas revisões: elas mantêm sua própria visibilidade e continuam disponíveis quando compartilhadas. Cópias já importadas na agenda também permanecem. Essa regra trata da retirada de compartilhamento, não define a política de exclusão de conta. O PDF original fica fora do compartilhamento e da retenção.
- **Procedência.** Registrar `author_role` com o papel da conta no momento do envio e `institutional_source_url` separadamente. A atribuição inicial de origem institucional exige evidência pública oficial vinculada à versão, validada por admin. Uma revisão feita por professor ou admin mantém a procedência institucional já validada da versão de origem. Registrar a versão de origem, a evidência institucional herdada, o autor da revisão e seu papel no momento da alteração. A interface distingue documento institucional de origem e alterações posteriores da comunidade. Papel professor/admin não cria procedência institucional quando a origem não a possuía; revisões estudantis não recebem essa herança automaticamente. Voto, vínculo autodeclarado e papel `professor` não constituem essa evidência.
- **Colaboração.** Seguidores autenticados da turma leem versões compartilhadas e votam por `PUT /api/v1/syllabus/{id}/versions/{version_id}/candidates/{candidate_id}/vote`, com `{"value":"confirm"}` ou `{"value":"contest"}`. Um voto ativo por usuário, candidato e versão. Repetir ou alterar voto não multiplica o total. A votação não altera datas automaticamente.
- **Confirmação.** Preservar `POST /api/v1/syllabus/{id}/confirm` para o fluxo particular e acrescentar `version_id` para selecionar explicitamente a versão compartilhada. O servidor verifica acesso, versão, seleção e datas antes de gravar o lote em transação. A decisão na versão compartilhada é por usuário. Deduplicar por `(user_id, version_id, candidate_id)` e manter a procedência do evento pessoal. Requisição antiga não restaura evento apagado. Uma nova importação exige ação explícita do usuário.

Exemplo de versão com um candidato a revisar. Campos legados de candidato como `type`, `startsAt`, `sourcePage` e `sourceExcerpt` permanecem nas rotas existentes durante a transição.

```json
{
  "id": "22222222-2222-4222-8222-222222222222",
  "syllabus_id": "33333333-3333-4333-8333-333333333333",
  "class_offering_id": "11111111-1111-4111-8111-111111111111",
  "number": 1,
  "visibility": "private",
  "author_role": "student",
  "institutional_source_url": null,
  "status": "concluido",
  "phase": "review_candidates",
  "candidates": [{
    "id": "44444444-4444-4444-8444-444444444444",
    "title": "Prova 1",
    "type": "exam",
    "startsAt": null,
    "ambiguous": true,
    "sourcePage": 3,
    "sourceExcerpt": "Prova 1 na primeira semana de novembro",
    "status": "pendente"
  }]
}
```

| Estado de processamento na API e no banco | Fase na interface | Regra |
| --- | --- | --- |
| `pendente` | `prepare_text`, `awaiting_authorization` ou `queued` | Só entra na fila externa depois da autorização. |
| `processando` | `extracting_candidates` | O job autorizado está em execução. Recarregar preserva o progresso. |
| `concluido` | `review_candidates` | A extração terminou. Zero candidatos é um resultado válido. A confirmação de cada candidato ocorre à parte. |
| `falha` | `failed` | Mostrar ação de recuperação aplicável, como reenviar texto, tentar novamente ou usar a agenda manual. |

Manter os quatro valores de `status` já consumidos pelo frontend. `phase` é aditivo e vem do backend, a partir do estado da preparação e do job. Candidato particular mantém `pendente`, `confirmado` ou `descartado`. Na versão compartilhada, a decisão de importar pertence à conta que importa. O estado de publicação pertence à versão.

### Medição do processamento (RNF06)

Medir do início do upload até a disponibilização dos candidatos para revisão. Descontar somente os intervalos de espera por revisão e autorização humanas; incluir transferência, validação, extração local, espera em fila e processamento externo. Registrar duração total, intervalos humanos descontados e duração resultante. A meta para planos de até 10 páginas é inferior a 20 segundos; a autorização específica continua obrigatória.

### Confirmação rápida e reimportação

Toda data extraída começa como candidata. Somente a confirmação explícita do usuário a transforma em avaliação efetiva na sua agenda; em versões compartilhadas, essa decisão pertence a cada conta. A revisão deve ser breve: mostrar candidatos em uma lista, permitir selecionar vários e confirmar o lote em uma única ação, destacar apenas campos ambíguos que exigem correção e preservar as escolhas durante ajustes. Não exigir uma sequência de confirmações por item nem importar automaticamente. Avaliar a fluidez na homologação com o tempo e as dificuldades observadas, sem inventar um limite numérico ainda não acordado.

Na R2, exigir `Idempotency-Key` por ação de confirmação, vinculada à conta, à operação e ao conteúdo do lote. Repetições da mesma ação usam a mesma chave; payload diferente com a mesma chave retorna 409. Persistir a operação e seus itens na mesma transação da confirmação e serializar requisições concorrentes. A exclusão do evento preserva o registro da importação e da operação: repetir a chave antiga não recria o evento nem reativa o vínculo. Reimportar exige o comando explícito “Adicionar novamente”, uma nova chave e nova verificação de acesso, versão e datas. Manter no máximo um evento ativo por `(user_id, version_id, candidate_id)`, mesmo com chaves diferentes; novas ações após exclusão não apagam o histórico das anteriores. O resultado de retry informa quando o evento anteriormente criado já foi removido. A transição dos clientes legados deve ser documentada antes de tornar a chave obrigatória; não inventar uma chave nova a cada retry.

## Datas e eventos

O calendário interpreta datas locais em `America/Sao_Paulo`. Campos de instante usam ISO 8601/RFC 3339 com deslocamento explícito. Persistir instantes como `timestamptz` e dias inteiros como datas civis. O fim de um intervalo é exclusivo. Se a fonte informar último dia inclusivo, converter para o dia civil seguinte. A janela de consulta inclui eventos que a intersectam. Para um evento com apenas início, usar esse instante para inclusão.

```json
{
  "title": "Apresentação de projetos",
  "all_day": false,
  "starts_at": "2026-11-18T14:00:00-03:00",
  "ends_at": "2026-11-18T16:00:00-03:00",
  "location": "Auditório"
}
```

```json
{
  "title": "Mostra de extensão",
  "all_day": true,
  "start_date": "2026-11-18",
  "end_date": "2026-11-21"
}
```

O segundo exemplo cobre 18, 19 e 20/11. Aceitar apenas a combinação de campos correspondente a `all_day`. Em intervalo informado, fim deve ser maior que início. Registros antigos apenas com início mantêm seu instante e fim ausente. Datas como “primeira semana de novembro”, datas sem ano, hora incerta e `00:00` usada como preenchimento exigem revisão. Uma avaliação com dia conhecido e sem hora vira dia inteiro apenas por confirmação explícita. Na confirmação, cada entrada mantém `candidateId` e aceita `startsAt` para instante ou `all_day: true` com `start_date` e `end_date` para dia inteiro. Recusar com 422 uma confirmação com data ainda ambígua.

A [Agenda UnB Notícias](https://noticias.unb.br/component/agenda/agendas) é a fonte inicial. Persistir URL/ID canônico, hash, data da última coleta e procedência visível. Publicar automaticamente eventos completos e inequívocos dessa fonte. Mandar ambíguos, incompletos e possíveis duplicatas à revisão por professor/admin. Conciliar URL idêntica, preservar decisões de moderação e edições locais em novas coletas, e manter registros existentes em falha da fonte. Tratar informes como tal antes de publicar como evento.

## Agenda, redirecionamento e lembretes

| Ação | Contrato | Efeito |
| --- | --- | --- |
| Adicionar aos meus eventos | `PUT /api/v1/me/saved-events/{event_id}` → 200 `{"saved":true}` | Salva vínculo único do usuário com evento público aprovado. A agenda pessoal lê os dados do original. |
| Remover dos meus eventos | `DELETE /api/v1/me/saved-events/{event_id}` → 204 | Remove o próprio vínculo e invalida lembretes futuros associados. Repetição é segura. |
| Conferir evento | `POST /api/v1/events/{event_id}/outbound-clicks` com `{"click_id":"55555555-5555-4555-8555-555555555555"}` → 200 `{"external_url":"https://example.org/evento"}` | Disponível inclusive a visitantes quando o evento é aprovado e possui URL válida. O cliente abre a URL devolvida pelo servidor. O mesmo `click_id` reenviado para o evento não incrementa o contador novamente. |

`click_id` é criado por acionamento, sem identificar a pessoa. Contar redirecionamentos acionados, sem inferir visitantes únicos, inscrição externa ou presença. O link vem do evento armazenado e passa pela validação HTTP/HTTPS. A ação não adiciona o evento à agenda. O histórico combina compromissos privados passados com eventos públicos passados ainda salvos, em listas separadas. Eventos públicos salvos continuam editáveis apenas na origem. O organizador recebe inscrições externas pelo seu próprio canal.

Reaproveitar `eventos.interessados_count` como contador de redirecionamentos, com deduplicação e incremento atômicos. Hoje o botão altera apenas o estado da tela. A R2 deve migrar para o contador persistido, atualizar o rótulo da interface e impedir que o caminho legado `registrar_interesse(uuid)` contorne a validação de URL e a deduplicação depois da transição.

A [#81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81) prevê um aviso persistido na plataforma exatamente 24 horas antes do início de cada evento que está na agenda da conta. Para dia inteiro, usar o início do primeiro dia civil à meia-noite em Brasília. Um item que entra na agenda após o instante de disparo segue sem alerta retroativo. Se o scheduler atrasar uma tarefa que já estava agendada, pode retomá-la antes do início, uma única vez. Exclusão, retirada do vínculo e retirada do evento do catálogo cancelam pendências. Mudança de início invalida a tarefa antiga e recalcula o disparo. A chave inclui conta, tipo e ID do evento e instante de referência. Verificar a elegibilidade novamente no disparo.

```json
{
  "id": "66666666-6666-4666-8666-666666666666",
  "event_kind": "saved_public",
  "event_id": "77777777-7777-4777-8777-777777777777",
  "scheduled_at": "2026-11-17T17:00:00Z",
  "read_at": null
}
```

`GET /api/v1/me/reminders?limit=20&offset=0` lista avisos disparados para a conta. `PUT /api/v1/me/reminders/{id}/read` marca o próprio aviso como lido e mantém o primeiro `read_at` em retries. E-mail transacional permanece no fluxo de autenticação.

## Google Agenda e ICS

1. **Autorizar.** Todo login com Google solicita o escopo [`calendar.app.created`](https://developers.google.com/workspace/calendar/api/auth) durante o OAuth. O backend valida a sessão OAuth, a identidade Google e o e-mail verificado antes de guardar as credenciais criptografadas. A exportação fica disponível em **Meus Eventos** após consentimento.
2. **Exportar.** O fluxo atual permite selecionar até 20 eventos pessoais ou públicos salvos. A cópia usa título, horário de Brasília e duração de uma hora, com ID estável por evento. A primeira exportação cria uma agenda secundária **Agenda UnB**. Falhas são apresentadas por item e a seleção mantém os itens que precisam de nova tentativa.
3. **Revogar.** A autorização é gerenciada nas conexões da Conta Google. Após revogar, um novo login com Google e o consentimento de calendário permitem recuperar a exportação.

Os contratos abaixo descrevem a ampliação prevista na S8-F03 (#82), incluindo seleção por período, lotes assíncronos, confirmação de sobrescrita, reconciliação do destino e exportação ICS.

```json
{
  "start_date": "2026-11-18",
  "end_date": "2026-11-22",
  "items": [{"event_kind": "saved_public", "event_id": "77777777-7777-4777-8777-777777777777"}],
  "allow_managed_field_updates": false
}
```

O detalhe do lote retorna `pending`, `running`, `completed`, `partial_failure` ou `failed`. A tentativa de cada item tem resultado próprio, incluindo `created`, `updated`, `unchanged` ou `failed`. Usar `Idempotency-Key` por confirmação do lote e verificar se a conexão e os itens continuam autorizados antes da escrita externa. Um retry do mesmo lote não autoriza atualizar campos que o usuário não aprovou.

```json
{
  "id": "88888888-8888-4888-8888-888888888888",
  "status": "partial_failure",
  "items": [
    {"event_id": "77777777-7777-4777-8777-777777777777", "status": "created"},
    {"event_id": "99999999-9999-4999-8999-999999999999", "status": "failed",
     "code": "END_REQUIRED", "retryable": false}
  ]
}
```

## Permissões e erros

| Operação | Autorização |
| --- | --- |
| Ler catálogo público de eventos e conferir link original | Visitante ou conta autenticada. Apenas eventos aprovados. |
| Usar catálogo de turmas, agenda, lembretes e exportação | Conta autenticada. Dados pessoais restritos à conta da sessão. |
| Ler material privado de plano | Autor. |
| Ler, votar e importar versão compartilhada | Seguidor autenticado da oferta. Autor mantém acesso aos próprios dados. |
| Editar plano | Autor em plano próprio. Professor e admin em versão compartilhada, com acesso limitado ao conteúdo já compartilhado. |
| Publicar ou retirar versão | Autor publica seu conteúdo. Professor/admin publicam diretamente suas revisões de conteúdo já compartilhado, sem aprovação adicional do autor original. Autor ou admin retira uma versão compartilhada. |
| Moderar sugestões de eventos | Professor ou admin. |
| Gerenciar papéis, categorias e prova de procedência institucional | Admin. |

Manter o [envelope FastAPI existente](api-specs.md#erros-fastapi). Usar 401 para sessão ausente ou inválida, 403 para papel insuficiente, 404 para recurso inexistente ou invisível à conta, 409 para plano fora da etapa esperada ou conexão Google que exige nova autorização, 422 para oferta inválida, candidato ambíguo ou data incompatível, 429 para cota e 503 para catálogo indisponível sem cache. Respostas com falhas parciais da exportação informam o erro por item. Tokens, PDF, texto integral e dados de outra conta ficam fora dos detalhes.

Exemplo HTTP 422 ao tentar confirmar candidato sem corrigir data ambígua:

```json
{"detail":"Informe uma data completa e confirme o horário ou marque como dia inteiro."}
```

Exemplo HTTP 403 ao concluir autorização Google com e-mail diferente:

```json
{"detail":"Selecione a conta Google com o mesmo e-mail verificado do Agenda UnB."}
```

## Compatibilidade e migração

- Fazer mudanças aditivas primeiro. Planos antigos mantêm IDs, candidatos, metadados e acesso do dono. Associar automaticamente uma oferta apenas se a correspondência for inequívoca. Pedir seleção do usuário nos demais casos antes de publicar uma versão. Manter os aliases atuais de `syllabus` e adaptar o frontend ao campo `phase` antes de exigir novos campos.
- A implementação atual guarda `caminho_arquivo` e pode retornar `filePath` ao dono. A migração deve interromper novas gravações permanentes de PDF, inventariar e remover os originais legados e suas referências com verificação de Storage. Preservar candidatos e agenda. Se um plano antigo dependia exclusivamente do PDF para processamento, orientar novo envio temporário ou entrada de texto.
- Migrar importação de candidatos para unicidade por usuário, candidato e versão antes de liberar versões compartilhadas. O índice legado de `origem_avaliacao_id` sozinho não cobre o novo uso. Alinhar migrations, ORM, RLS e autorização da API. Preservar `eventos_salvos` como vínculo existente.
- Acrescentar fim e campos civis aos eventos sem reclassificar automaticamente datas legadas de meia-noite. Verificar leitores antigos, dados migrados e rollback compatível antes de exigir os campos no frontend.
- Preservar exceções do esquema como `profiles`, `categories`, `user_id`, `professor_id`, `category_id` e `event_id`. Preservar também os mapeamentos diferentes de início em `eventos.data_evento` e `eventos_pessoais.data_hora` e os estados em português. Campos novos seguem os [padrões do projeto](produto/padroes.md). Renomeações gerais de tabelas, colunas e aliases ficam fora da Release 2.
