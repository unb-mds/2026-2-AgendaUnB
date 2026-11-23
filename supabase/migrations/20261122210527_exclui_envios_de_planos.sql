-- Keep a minimal record for the upload quota and any third-party revisions.
alter table public.planos_ensino add column envio_excluido_em timestamptz;

create policy "envios excluidos nao aparecem no historico"
  on public.planos_ensino as restrictive for select to authenticated
  using (envio_excluido_em is null);
