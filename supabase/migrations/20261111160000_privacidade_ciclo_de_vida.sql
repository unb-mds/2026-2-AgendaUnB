-- =============================================================
-- S8-D01 (#83) — Privacidade, termos e ciclo de vida dos dados
--
-- Requisitos: RF07, RNF02 e RNF04.
--
--   1. exclusão de conta sem resíduos nem bloqueio;
--   2. aceite de termos, separado de consentimento;
--   3. descarte do PDF original (ADR-003);
--   4. exportação dos dados do titular;
--   5. registro da exclusão sem identificar a pessoa.
--
-- Como nas demais migrações da R2, as funções recebem o ator (id da
-- conta validada pela API) e nada é gravável pelo navegador.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Excluir a conta precisa funcionar
--
-- eventos_pessoais.user_id apontava para auth.users SEM ação de
-- exclusão: uma conta com qualquer compromisso na agenda não podia
-- ser excluída (violação de chave estrangeira). Todas as outras
-- tabelas da conta já usavam ON DELETE CASCADE.
-- -------------------------------------------------------------
alter table public.eventos_pessoais
  drop constraint if exists eventos_pessoais_user_id_fkey,
  add constraint eventos_pessoais_user_id_fkey
    foreign key (user_id) references auth.users(id) on delete cascade;


-- -------------------------------------------------------------
-- 2. Aceite de termos e consentimento são registros diferentes
--
-- Aceite: a conta declara que leu uma VERSÃO dos Termos de Uso ou da
-- Política de Privacidade. Não é a base legal do tratamento.
--
-- Consentimento: autorização específica, por finalidade, que pode ser
-- revogada a qualquer momento (conectar o Google Agenda).
--
-- A autorização para enviar o texto de um plano ao provedor de IA NÃO
-- fica aqui: ela é o snapshot do próprio plano (texto_aprovado,
-- hash_texto_aprovado, autorizado_em; 20261110120000), que o worker
-- confere antes de cada chamada. Um segundo registro da mesma
-- autorização poderia divergir dele.
-- -------------------------------------------------------------
create table public.aceites_termos (
  user_id     uuid not null references public.profiles(id) on delete cascade,
  documento   text not null check (documento in ('termos_de_uso', 'politica_de_privacidade')),
  versao      text not null check (versao ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'),
  aceito_em   timestamptz not null default now(),
  primary key (user_id, documento, versao)
);

comment on table public.aceites_termos is
  'Versões dos documentos legais que a conta declarou ter lido. versao é a data de vigência do documento (AAAA-MM-DD).';

create table public.consentimentos (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.profiles(id) on delete cascade,
  finalidade     text not null check (finalidade in ('google_agenda')),
  -- O objeto autorizado, quando houver. Sem FK, para o registro
  -- sobreviver à exclusão do objeto enquanto a conta existir.
  referencia_id  uuid,
  -- Hash do que foi autorizado (ex.: escopos concedidos). Mudou, exige
  -- nova autorização.
  conteudo_hash  text check (conteudo_hash is null or char_length(conteudo_hash) between 16 and 128),
  concedido_em   timestamptz not null default now(),
  revogado_em    timestamptz,
  constraint consentimentos_revogacao_posterior check (revogado_em is null or revogado_em >= concedido_em)
);

-- Um consentimento ativo por conta, finalidade, objeto e conteúdo.
create unique index uq_consentimentos_ativos
  on public.consentimentos (user_id, finalidade,
                            coalesce(referencia_id, '00000000-0000-0000-0000-000000000000'::uuid),
                            coalesce(conteudo_hash, ''))
  where revogado_em is null;

create index idx_consentimentos_usuario on public.consentimentos (user_id, finalidade);

comment on table public.consentimentos is
  'Autorizações específicas e revogáveis. Mudou o texto autorizado, muda o hash: exige nova autorização.';

create or replace function public.registrar_aceite_termos(p_ator uuid, p_documento text, p_versao text)
returns public.aceites_termos
language plpgsql
set search_path = ''
as $$
declare
  v public.aceites_termos;
begin
  insert into public.aceites_termos (user_id, documento, versao)
  values (p_ator, p_documento, p_versao)
  on conflict do nothing;
  -- O primeiro aceite vale: repetir não altera a data.
  select * into v from public.aceites_termos
   where user_id = p_ator and documento = p_documento and versao = p_versao;
  return v;
end;
$$;

create or replace function public.registrar_consentimento(
  p_ator uuid, p_finalidade text, p_referencia_id uuid default null, p_conteudo_hash text default null
)
returns public.consentimentos
language plpgsql
set search_path = ''
as $$
declare
  v public.consentimentos;
begin
  perform pg_advisory_xact_lock(hashtextextended('consentimento:' || p_ator::text, 0));
  select * into v from public.consentimentos
   where user_id = p_ator and finalidade = p_finalidade and revogado_em is null
     and referencia_id is not distinct from p_referencia_id
     and conteudo_hash is not distinct from p_conteudo_hash;
  if found then
    return v;
  end if;
  insert into public.consentimentos (user_id, finalidade, referencia_id, conteudo_hash)
  values (p_ator, p_finalidade, p_referencia_id, p_conteudo_hash)
  returning * into v;
  return v;
end;
$$;

-- Revoga os consentimentos ativos da finalidade (e do objeto, se
-- informado). Devolve quantos foram revogados; repetir devolve 0.
create or replace function public.revogar_consentimento(
  p_ator uuid, p_finalidade text, p_referencia_id uuid default null
)
returns integer
language plpgsql
set search_path = ''
as $$
declare
  v_total integer;
begin
  update public.consentimentos
     set revogado_em = now()
   where user_id = p_ator and finalidade = p_finalidade and revogado_em is null
     and (p_referencia_id is null or referencia_id = p_referencia_id);
  get diagnostics v_total = row_count;
  return v_total;
end;
$$;

-- Há consentimento ativo para exatamente este conteúdo?
create or replace function public.tem_consentimento(
  p_ator uuid, p_finalidade text, p_referencia_id uuid default null, p_conteudo_hash text default null
)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (
    select 1 from public.consentimentos
     where user_id = p_ator and finalidade = p_finalidade and revogado_em is null
       and referencia_id is not distinct from p_referencia_id
       and conteudo_hash is not distinct from p_conteudo_hash);
$$;


-- -------------------------------------------------------------
-- 3. Descarte do PDF original (ADR-003, RNF02)
--
-- Envios novos não guardam mais o PDF (S7-B01): o texto é extraído no
-- upload e só ele é gravado. O descarte vale para os PDFs antigos.
--
-- planos_particular_exige_fonte (20261110120000) exige PDF ou texto
-- preparado em todo plano particular, o que impediria descartar o PDF
-- de um plano antigo já processado. O descarte registrado passa a ser
-- uma terceira situação válida: candidatos e agenda não dependem dele.
-- -------------------------------------------------------------
alter table public.planos_ensino
  drop constraint if exists planos_particular_exige_arquivo,
  add column arquivo_descartado_em timestamptz;

alter table public.planos_ensino
  drop constraint planos_particular_exige_fonte,
  add constraint planos_particular_exige_fonte check (
    tipo <> 'particular' or caminho_arquivo is not null
    or texto_preparado is not null or arquivo_descartado_em is not null);

comment on column public.planos_ensino.arquivo_descartado_em is
  'Quando o PDF original foi removido do Storage. O registro do plano permanece.';

-- Planos cujo arquivo já pode ser removido: processamento encerrado.
-- Planos pendentes ou em processamento ficam com a extração (#51).
create or replace function public.arquivos_a_descartar(p_limite integer default 200)
returns table (plano_id uuid, caminho_arquivo text)
language sql
stable
set search_path = ''
as $$
  select p.id, p.caminho_arquivo
    from public.planos_ensino p
   where p.caminho_arquivo is not null
     and p.status in ('concluido', 'falha')
   order by p.criado_em
   limit greatest(1, least(coalesce(p_limite, 200), 1000));
$$;

-- Chamar DEPOIS de remover o objeto do Storage. Repetir é seguro.
create or replace function public.registrar_descarte_arquivo(p_plano_id uuid)
returns boolean
language plpgsql
set search_path = ''
as $$
begin
  update public.planos_ensino
     set caminho_arquivo = null, arquivo_url = null, tamanho_bytes = null,
         arquivo_descartado_em = now()
   where id = p_plano_id and (caminho_arquivo is not null or arquivo_url is not null);
  return found;
end;
$$;


-- -------------------------------------------------------------
-- 4. Exportação dos dados do titular
--
-- Tudo o que a plataforma guarda sobre a conta, em um único JSON.
-- Não inclui dados de outras pessoas: de um evento público salvo vai
-- só a referência; de uma versão compartilhada por outra conta, só o
-- que a própria conta fez (voto, importação).
-- -------------------------------------------------------------
create or replace function public.exportar_dados_da_conta(p_ator uuid)
returns jsonb
language plpgsql
stable
set search_path = ''
as $$
declare
  v_resultado jsonb;
begin
  if not exists (select 1 from public.profiles where id = p_ator) then
    raise exception 'Conta não encontrada' using errcode = 'P0002';
  end if;

  select jsonb_build_object(
    'gerado_em', now(),
    'formato', 'agenda-unb-exportacao-v1',
    'conta', (
      select jsonb_build_object(
               'id', p.id, 'nome_completo', p.nome_completo, 'email', p.email, 'papel', p.papel,
               'avatar_url', p.avatar_url, 'criado_em', p.criado_em,
               'email_confirmado_em', u.email_confirmed_at, 'ultimo_acesso_em', u.last_sign_in_at)
        from public.profiles p join auth.users u on u.id = p.id where p.id = p_ator),
    'agenda_pessoal', coalesce((
      select jsonb_agg(to_jsonb(t) order by t.data_hora) from (
        select e.id, e.titulo, e.descricao, e.data_hora, e.data_fim, e.dia_inteiro,
               e.data_inicio_civil, e.data_fim_civil, c.nome as campus, cat.nome as categoria,
               e.origem_plano_id, e.origem_avaliacao_id, e.origem_versao_id, e.origem_pagina,
               e.origem_trecho, e.criado_em
          from public.eventos_pessoais e
          left join public.campus c on c.id = e.campus_id
          left join public.categories cat on cat.id = e.category_id
         where e.user_id = p_ator) t), '[]'::jsonb),
    'eventos_publicos_salvos', coalesce((
      select jsonb_agg(jsonb_build_object('evento_id', s.event_id, 'titulo', e.titulo, 'salvo_em', s.criado_em)
                       order by s.criado_em)
        from public.eventos_salvos s join public.eventos e on e.id = s.event_id
       where s.user_id = p_ator), '[]'::jsonb),
    'eventos_enviados', coalesce((
      select jsonb_agg(to_jsonb(t) order by t.criado_em) from (
        select e.id, e.titulo, e.descricao, e.data_evento, e.data_fim, e.dia_inteiro, e.localizacao,
               e.link_externo, e.status, e.justificativa_recusa, e.sugestao_estudante, e.criado_em
          from public.eventos e where e.autor_id = p_ator) t), '[]'::jsonb),
    'notificacoes', coalesce((
      select jsonb_agg(to_jsonb(n) - 'usuario_id' order by n.criado_em)
        from public.notificacoes n where n.usuario_id = p_ator), '[]'::jsonb),
    'lembretes', coalesce((
      select jsonb_agg(to_jsonb(l) - 'user_id' order by l.agendado_para)
        from public.lembretes l where l.user_id = p_ator), '[]'::jsonb),
    'turmas_seguidas', coalesce((
      select jsonb_agg(jsonb_build_object(
               'oferta_id', o.id, 'codigo', d.codigo, 'disciplina', d.nome, 'turma', o.turma,
               'ano', o.ano, 'semestre', o.semestre, 'origem_do_vinculo', v.origem, 'desde', v.criado_em)
               order by v.criado_em)
        from public.vinculos_turma v
        join public.ofertas_turma o on o.id = v.oferta_id
        join public.disciplinas d on d.id = o.disciplina_id
       where v.user_id = p_ator), '[]'::jsonb),
    'planos_de_ensino', coalesce((
      select jsonb_agg(to_jsonb(t) order by t.criado_em) from (
        select p.id, p.nome_arquivo, p.tamanho_bytes, p.paginas, p.status, p.erro_codigo, p.disciplina,
               p.turma, p.ano, p.semestre, p.oferta_id, p.criado_em, p.processado_em,
               p.caminho_arquivo is not null as arquivo_original_armazenado, p.arquivo_descartado_em,
               p.texto_preparado, p.texto_aprovado, p.autorizado_em as texto_autorizado_em
          from public.planos_ensino p where p.user_id = p_ator) t), '[]'::jsonb),
    'versoes_de_planos', coalesce((
      select jsonb_agg(jsonb_build_object(
               'id', v.id, 'plano_id', v.plano_id, 'numero', v.numero, 'autor_papel', v.autor_papel,
               'versao_origem_id', v.versao_origem_id, 'visibilidade', v.visibilidade,
               'compartilhada_em', v.compartilhada_em, 'retirada_em', v.retirada_em, 'criado_em', v.criado_em,
               'candidatos', coalesce((
                 select jsonb_agg(jsonb_build_object(
                          'id', a.id, 'titulo', a.titulo, 'data_avaliacao', a.data_avaliacao, 'tipo', a.tipo,
                          'ambiguo', a.ambiguo, 'status', a.status, 'pagina_origem', a.pagina_origem,
                          'trecho_origem', a.trecho_origem) order by a.ordem nulls last, a.criado_em)
                   from public.avaliacoes a where a.versao_id = v.id), '[]'::jsonb))
               order by v.criado_em)
        from public.versoes_plano v where v.autor_id = p_ator), '[]'::jsonb),
    'votos', coalesce((
      select jsonb_agg(jsonb_build_object('candidato_id', vt.avaliacao_id, 'valor', vt.valor,
                                          'criado_em', vt.criado_em, 'atualizado_em', vt.atualizado_em)
                       order by vt.criado_em)
        from public.votos_avaliacao vt where vt.user_id = p_ator), '[]'::jsonb),
    'importacoes', coalesce((
      select jsonb_agg(jsonb_build_object(
               'id', o.id, 'versao_id', o.versao_id, 'criado_em', o.criado_em,
               'itens', coalesce((
                 select jsonb_agg(jsonb_build_object('candidato_id', i.avaliacao_id,
                          'evento_id', i.evento_pessoal_id, 'resultado', i.resultado))
                   from public.itens_importacao i where i.operacao_id = o.id), '[]'::jsonb))
               order by o.criado_em)
        from public.operacoes_importacao o where o.user_id = p_ator), '[]'::jsonb),
    'aceites_de_termos', coalesce((
      select jsonb_agg(jsonb_build_object('documento', a.documento, 'versao', a.versao, 'aceito_em', a.aceito_em)
                       order by a.aceito_em)
        from public.aceites_termos a where a.user_id = p_ator), '[]'::jsonb),
    'consentimentos', coalesce((
      select jsonb_agg(jsonb_build_object('finalidade', c.finalidade, 'referencia_id', c.referencia_id,
                                          'concedido_em', c.concedido_em, 'revogado_em', c.revogado_em)
                       order by c.concedido_em)
        from public.consentimentos c where c.user_id = p_ator), '[]'::jsonb)
  ) into v_resultado;

  return v_resultado;
end;
$$;


-- -------------------------------------------------------------
-- 5. Exclusão de conta
--
-- Sequência executada pela API:
--   1. preparar_exclusao_conta(ator)  -> arquivos a remover do Storage
--   2. remover os arquivos do Storage
--   3. excluir o usuário no Supabase Auth (cascata apaga o resto)
--   4. concluir_exclusao_conta(registro)
--
-- O que a cascata apaga: perfil, agenda pessoal, eventos salvos,
-- notificações, lembretes, vínculos com turmas, votos, operações de
-- importação, aceites, consentimentos, planos da conta com todas as
-- versões e candidatos, e os eventos públicos que a conta enviou.
--
-- O que permanece: eventos que OUTRAS contas já importaram para a
-- própria agenda (cópias independentes, sem vínculo com a origem) e
-- este registro, que não identifica a pessoa.
--
-- O último administrador não pode se excluir: a plataforma ficaria
-- sem ninguém para atender titulares e moderar.
-- -------------------------------------------------------------
create table public.exclusoes_conta (
  id             uuid primary key default gen_random_uuid(),
  solicitada_em  timestamptz not null default now(),
  concluida_em   timestamptz,
  -- Só quantidades por tipo de dado. Nenhum identificador da conta.
  contagens      jsonb not null default '{}'::jsonb
);

comment on table public.exclusoes_conta is
  'Evidência de que uma exclusão foi pedida e concluída. Sem id, nome ou e-mail da conta excluída.';

create or replace function public.preparar_exclusao_conta(p_ator uuid)
returns jsonb
language plpgsql
set search_path = ''
as $$
declare
  v_papel    text;
  v_registro uuid;
  v_contagens jsonb;
begin
  select papel into v_papel from public.profiles where id = p_ator for update;
  if not found then
    raise exception 'Conta não encontrada' using errcode = 'P0002';
  end if;
  if v_papel = 'admin' and not exists (
       select 1 from public.profiles where papel = 'admin' and id <> p_ator) then
    raise exception 'Transfira a administração para outra conta antes de excluir esta' using errcode = '55000';
  end if;

  v_contagens := jsonb_build_object(
    'agenda_pessoal',  (select count(*) from public.eventos_pessoais where user_id = p_ator),
    'eventos_salvos',  (select count(*) from public.eventos_salvos where user_id = p_ator),
    'eventos_enviados', (select count(*) from public.eventos where autor_id = p_ator),
    'planos',          (select count(*) from public.planos_ensino where user_id = p_ator),
    'versoes',         (select count(*) from public.versoes_plano where autor_id = p_ator),
    'votos',           (select count(*) from public.votos_avaliacao where user_id = p_ator),
    'turmas_seguidas', (select count(*) from public.vinculos_turma where user_id = p_ator),
    'lembretes',       (select count(*) from public.lembretes where user_id = p_ator));

  insert into public.exclusoes_conta (contagens) values (v_contagens) returning id into v_registro;

  return jsonb_build_object(
    'registro_id', v_registro,
    'contagens', v_contagens,
    'arquivos', coalesce((
      select jsonb_agg(p.caminho_arquivo)
        from public.planos_ensino p
       where p.user_id = p_ator and p.caminho_arquivo is not null), '[]'::jsonb));
end;
$$;

create or replace function public.concluir_exclusao_conta(p_registro_id uuid)
returns boolean
language plpgsql
set search_path = ''
as $$
begin
  update public.exclusoes_conta set concluida_em = now()
   where id = p_registro_id and concluida_em is null;
  return found;
end;
$$;


-- -------------------------------------------------------------
-- 6. Acesso
-- -------------------------------------------------------------
alter table public.aceites_termos  enable row level security;
alter table public.consentimentos  enable row level security;
alter table public.exclusoes_conta enable row level security;

revoke all on public.aceites_termos, public.consentimentos, public.exclusoes_conta from anon, authenticated;
grant select on public.aceites_termos, public.consentimentos to authenticated;

create policy "conta le os proprios aceites"
  on public.aceites_termos for select
  to authenticated
  using (user_id = (select auth.uid()));

create policy "conta le os proprios consentimentos"
  on public.consentimentos for select
  to authenticated
  using (user_id = (select auth.uid()));

revoke execute on function
  public.registrar_aceite_termos(uuid, text, text),
  public.registrar_consentimento(uuid, text, uuid, text),
  public.revogar_consentimento(uuid, text, uuid),
  public.tem_consentimento(uuid, text, uuid, text),
  public.arquivos_a_descartar(integer),
  public.registrar_descarte_arquivo(uuid),
  public.exportar_dados_da_conta(uuid),
  public.preparar_exclusao_conta(uuid),
  public.concluir_exclusao_conta(uuid)
  from public, anon, authenticated;

grant execute on function
  public.registrar_aceite_termos(uuid, text, text),
  public.registrar_consentimento(uuid, text, uuid, text),
  public.revogar_consentimento(uuid, text, uuid),
  public.tem_consentimento(uuid, text, uuid, text),
  public.arquivos_a_descartar(integer),
  public.registrar_descarte_arquivo(uuid),
  public.exportar_dados_da_conta(uuid),
  public.preparar_exclusao_conta(uuid),
  public.concluir_exclusao_conta(uuid)
  to service_role;
