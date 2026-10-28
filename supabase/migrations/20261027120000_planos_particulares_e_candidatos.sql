-- =============================================================
-- S6-D01 (#53) — Planos particulares e resultados da IA
--
-- Evolui planos_ensino para aceitar uploads particulares de
-- estudantes e cria a tabela de candidatos extraídos pela IA.
--
-- Fluxo coberto:
--   upload (#40) -> plano 'pendente'
--   worker (S6-B01) -> 'processando' -> candidatos -> 'concluido' | 'falha'
--   revisão (S6-B02) -> candidato 'confirmado' (vira evento pessoal)
--                       ou 'descartado'
--
-- Fora desta migration (S6-D02, Luis Davi):
--   - políticas de RLS de planos, candidatos e avaliações;
--   - a função transacional de confirmação.
-- As tabelas novas nascem com RLS ligado e sem política, ou seja,
-- fechadas para o navegador até a S6-D02 abrir o acesso do dono.
--
-- Dados existentes: as linhas antigas de planos_ensino foram
-- enviadas por professores, para uma turma. Elas passam a ser
-- tipo 'oficial', com status 'concluido', e nada é apagado.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Dono e tipo do plano
--
-- proprietario_id: quem enviou o arquivo (estudante ou professor).
-- professor_id continua existindo, mas só para plano oficial,
-- e significa "professor responsável pela turma".
-- -------------------------------------------------------------
alter table public.planos_ensino
  add column proprietario_id uuid references public.profiles(id) on delete cascade,
  add column tipo text not null default 'particular';

update public.planos_ensino
   set proprietario_id = professor_id,
       tipo = 'oficial';

alter table public.planos_ensino
  alter column proprietario_id set not null,
  alter column professor_id drop not null,
  alter column turma drop not null;

alter table public.planos_ensino
  add constraint planos_tipo_valido
    check (tipo in ('particular', 'oficial')),
  -- Plano oficial exige professor e turma.
  add constraint planos_oficial_exige_professor_e_turma
    check (tipo <> 'oficial' or (professor_id is not null and turma is not null)),
  -- Plano particular não usa professor_id com outro significado.
  add constraint planos_particular_sem_professor
    check (tipo <> 'particular' or professor_id is null);


-- -------------------------------------------------------------
-- 2. Arquivo, período e processamento
-- -------------------------------------------------------------
alter table public.planos_ensino
  -- Arquivo no bucket syllabus_files (#43)
  add column arquivo_caminho        text,
  add column arquivo_nome_original  text,
  add column arquivo_tamanho_bytes  integer,
  add column arquivo_mime           text,
  add column arquivo_paginas        smallint,
  -- Período de referência informado no envio
  add column ano                    smallint,
  add column semestre               smallint,
  -- Processamento
  add column status                 text not null default 'pendente',
  add column execucao_atual         smallint not null default 0,
  add column provedor_ia            text,
  add column modelo_ia              text,
  add column versao_processamento   text,
  add column erro_codigo            text,
  add column erro_mensagem          text,
  add column processamento_iniciado_em timestamptz,
  add column processado_em          timestamptz,
  add column atualizado_em          timestamptz not null default now(),
  -- Referência opcional a um plano oficial (Modelo Dual, futuro)
  add column plano_oficial_id       uuid references public.planos_ensino(id) on delete set null;

-- Linhas antigas: registros finalizados, sem processamento pendente.
update public.planos_ensino
   set status = 'concluido',
       processado_em = criado_em;

alter table public.planos_ensino
  add constraint planos_status_valido
    check (status in ('pendente', 'processando', 'concluido', 'falha')),

  -- Caminho no formato <proprietario_id>/<arquivo>.pdf, o mesmo que
  -- as políticas do bucket exigem. Obrigatório no plano particular.
  add constraint planos_particular_exige_arquivo
    check (tipo <> 'particular' or arquivo_caminho is not null),
  add constraint planos_caminho_na_pasta_do_dono
    check (
      arquivo_caminho is null
      or (arquivo_caminho ~ '^[0-9a-f-]{36}/[^/]+\.pdf$'
          and split_part(arquivo_caminho, '/', 1) = proprietario_id::text)
    ),

  -- Limites do bucket: PDF de até 10 MB
  add constraint planos_arquivo_mime_pdf
    check (arquivo_mime is null or arquivo_mime = 'application/pdf'),
  add constraint planos_arquivo_tamanho
    check (arquivo_tamanho_bytes is null or arquivo_tamanho_bytes between 1 and 10485760),
  add constraint planos_arquivo_paginas
    check (arquivo_paginas is null or arquivo_paginas >= 1),
  add constraint planos_nome_original_tamanho
    check (arquivo_nome_original is null or char_length(arquivo_nome_original) <= 255),

  -- Período: obrigatório no particular
  add constraint planos_ano_valido
    check (ano is null or ano between 2000 and 2100),
  add constraint planos_semestre_valido
    check (semestre is null or semestre in (1, 2)),
  add constraint planos_particular_exige_periodo
    check (tipo <> 'particular' or (ano is not null and semestre is not null)),

  -- Erro sanitizado: código fixo + mensagem curta para o usuário.
  -- Só existe quando o status é 'falha', e 'falha' sempre tem código.
  add constraint planos_erro_codigo_valido
    check (erro_codigo is null or erro_codigo in (
      'pdf_invalido', 'pdf_protegido', 'pdf_sem_texto', 'limite_paginas',
      'falha_ia', 'tempo_esgotado', 'erro_interno'
    )),
  add constraint planos_erro_apenas_em_falha
    check ((status = 'falha') = (erro_codigo is not null)),
  add constraint planos_erro_mensagem_tamanho
    check (erro_mensagem is null or char_length(erro_mensagem) <= 500),
  add constraint planos_erro_mensagem_exige_falha
    check (erro_mensagem is null or status = 'falha'),

  -- Datas coerentes com o status
  add constraint planos_processando_tem_inicio
    check (status <> 'processando' or processamento_iniciado_em is not null),
  add constraint planos_finalizado_tem_data
    check ((status in ('concluido', 'falha')) = (processado_em is not null)),

  add constraint planos_execucao_nao_negativa
    check (execucao_atual >= 0),

  -- Só plano particular aponta para oficial, e nunca para si mesmo
  add constraint planos_referencia_oficial
    check (plano_oficial_id is null or (tipo = 'particular' and plano_oficial_id <> id));

alter table public.planos_ensino
  add constraint planos_arquivo_caminho_unico unique (arquivo_caminho);

create trigger planos_ensino_atualiza_timestamp
  before update on public.planos_ensino
  for each row execute function public.tg_atualiza_timestamp();

comment on table  public.planos_ensino is
  'Planos de ensino enviados em PDF. particular: enviado por um usuário para a própria agenda. oficial: plano de uma turma, enviado pelo professor.';
comment on column public.planos_ensino.proprietario_id is 'Quem enviou o arquivo. É o dono do plano e dos candidatos.';
comment on column public.planos_ensino.professor_id is 'Somente em plano oficial: professor responsável pela turma.';
comment on column public.planos_ensino.arquivo_url is 'Legado (antes da S6). Use arquivo_caminho.';
comment on column public.planos_ensino.arquivo_caminho is 'Caminho no bucket syllabus_files: <proprietario_id>/<arquivo>.pdf';
comment on column public.planos_ensino.execucao_atual is 'Número da execução de processamento mais recente (0 = nunca processado). Os candidatos válidos são os desta execução.';
comment on column public.planos_ensino.erro_codigo is 'Código fixo do erro. Nunca guarda stack trace, texto do PDF ou resposta bruta da IA.';
comment on column public.planos_ensino.erro_mensagem is 'Mensagem curta e segura para exibir ao usuário.';
comment on column public.planos_ensino.plano_oficial_id is 'Reservado para o Modelo Dual: plano oficial correspondente a este plano particular.';


-- -------------------------------------------------------------
-- 3. Candidatos extraídos pela IA
--
-- Um candidato é uma SUGESTÃO. Ele só vira compromisso quando o
-- estudante confirma (S6-D02 / S6-B02). Nada aqui cria evento
-- pessoal automaticamente.
--
-- Idempotência: (plano_id, execucao, ordem) é único. Se o worker
-- repetir a mesma execução, grava com ON CONFLICT e não duplica.
-- Reprocessar o plano gera uma nova execução; as anteriores ficam
-- como histórico.
-- -------------------------------------------------------------
create table public.candidatos_avaliacao (
  id                    uuid primary key default gen_random_uuid(),
  plano_id              uuid not null references public.planos_ensino(id) on delete cascade,
  execucao              smallint not null check (execucao >= 1),
  ordem                 smallint not null check (ordem >= 0),

  -- O que a IA sugeriu
  titulo                text not null check (char_length(btrim(titulo)) between 1 and 300),
  tipo                  text not null default 'outro'
                        check (tipo in ('prova', 'trabalho', 'projeto', 'seminario',
                                        'lista', 'entrega', 'outro')),
  data_sugerida         date,
  hora_sugerida         time,
  campos_ambiguos       text[] not null default '{}'
                        check (campos_ambiguos <@ array['titulo', 'tipo', 'data', 'hora']::text[]),
  ambiguo               boolean generated always as (cardinality(campos_ambiguos) > 0) stored,

  -- De onde veio
  pagina_origem         smallint not null check (pagina_origem >= 1),
  trecho_origem         text not null check (char_length(trecho_origem) between 1 and 1000),
  provedor_ia           text not null,
  modelo_ia             text not null,
  versao_processamento  text not null,

  -- Revisão do estudante
  status                text not null default 'pendente'
                        check (status in ('pendente', 'descartado', 'confirmado')),
  revisado_em           timestamptz,
  evento_pessoal_id     uuid unique references public.eventos_pessoais(id) on delete set null,

  criado_em             timestamptz not null default now(),

  constraint candidatos_execucao_ordem_unica unique (plano_id, execucao, ordem),
  -- Hora sem data não faz sentido
  constraint candidatos_hora_exige_data check (hora_sugerida is null or data_sugerida is not null),
  -- Revisado <=> não está mais pendente
  constraint candidatos_revisao_coerente check ((status = 'pendente') = (revisado_em is null)),
  -- Só candidato confirmado aponta para um evento
  constraint candidatos_vinculo_apenas_confirmado
    check (evento_pessoal_id is null or status = 'confirmado')
);

comment on table  public.candidatos_avaliacao is
  'Avaliações sugeridas pela IA a partir de um plano. Só viram evento pessoal após confirmação do estudante.';
comment on column public.candidatos_avaliacao.execucao is 'Execução de processamento que gerou o candidato (ver planos_ensino.execucao_atual).';
comment on column public.candidatos_avaliacao.ordem is 'Posição do candidato na saída da execução. Junto com plano_id e execucao, impede duplicação em reexecuções.';
comment on column public.candidatos_avaliacao.campos_ambiguos is 'Campos que a IA marcou como incertos. A revisão deve destacá-los.';
comment on column public.candidatos_avaliacao.hora_sugerida is 'Hora local escrita no plano, sem fuso. O fuso é definido na confirmação.';
comment on column public.candidatos_avaliacao.evento_pessoal_id is
  'Evento criado na confirmação. Editar o evento não altera o candidato. Excluir o evento deixa este campo nulo e o candidato continua confirmado, sem ser recriado.';

create index candidatos_plano_status on public.candidatos_avaliacao(plano_id, execucao, status);

alter table public.candidatos_avaliacao enable row level security;


-- -------------------------------------------------------------
-- 4. Índices de consulta
-- -------------------------------------------------------------
-- Histórico paginado do usuário (GET /api/v1/syllabus)
create index planos_proprietario_criado
  on public.planos_ensino(proprietario_id, criado_em desc, id);

-- Fila do worker e recuperação de tarefas interrompidas (S6-B01)
create index planos_fila_processamento
  on public.planos_ensino(status, processamento_iniciado_em)
  where status in ('pendente', 'processando');

create index planos_plano_oficial
  on public.planos_ensino(plano_oficial_id)
  where plano_oficial_id is not null;

create index avaliacoes_plano_id
  on public.avaliacoes(plano_id);
