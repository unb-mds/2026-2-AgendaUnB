begin;

-- A coleta antiga descartava as tags. Recupera limites identificáveis no
-- texto salvo, inclusive quando a página já saiu da listagem institucional.
-- Uma quebra ocupa o espaço que substitui, mesmo no limite de 10.000 caracteres.
select set_config('agenda.coleta', '1', true);

with formatadas as (
  select id, regexp_replace(
    regexp_replace(descricao,
      ' (?=(?:[0-9]{2}/[0-9]{2}/[0-9]{4} *[|]|Horário:|Local:|Unidade/organização:|Responsável/contato:|Público-alvo:|Inscrições:))',
      E'\n', 'g'),
    '([[:alpha:]]{4,}[.!?]) (?=[[:upper:]])', E'\\1\n', 'g'
  ) as descricao
  from public.eventos
  where fonte = 'agenda_unb_noticias'
    and not ('descricao' = any(campos_editados))
    and strpos(descricao, E'\n') = 0
)
update public.eventos e
   set descricao = f.descricao
  from formatadas f
 where e.id = f.id and e.descricao is distinct from f.descricao;

commit;
