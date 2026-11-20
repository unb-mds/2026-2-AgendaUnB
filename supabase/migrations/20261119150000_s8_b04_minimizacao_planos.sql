alter table public.planos_ensino
  add column ocorrencias_mascaradas integer
  check (ocorrencias_mascaradas >= 0);

comment on column public.planos_ensino.ocorrencias_mascaradas is
  'Total de substituições da preparação inicial. Nulo para planos preparados antes da contagem.';
