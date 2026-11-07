-- Políticas permissivas se somam. O FOR ALL de S6-D02 ainda permitia
-- uploads diretos mesmo após a remoção da política específica de INSERT.
drop policy if exists "Restricao de pasta por usuario no storage" on storage.objects;
drop policy if exists "planos: usuario remove da propria pasta" on storage.objects;

-- Planos e avaliações podem ser consultados pelo dono. A API, o worker e
-- a RPC de confirmação são responsáveis pelas alterações de estado.
drop policy if exists "planos particulares: usuario cria os proprios planos" on public.planos_ensino;
drop policy if exists "planos particulares: usuario le apenas os proprios planos" on public.planos_ensino;
drop policy if exists "Dono gerencia seus planos" on public.planos_ensino;
drop policy if exists "Dono consulta seus planos" on public.planos_ensino;
create policy "Dono consulta seus planos" on public.planos_ensino
  for select to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "Dono gerencia candidatos de seus planos" on public.candidatos_avaliacao;
drop policy if exists "Dono consulta candidatos de seus planos" on public.candidatos_avaliacao;
create policy "Dono consulta candidatos de seus planos" on public.candidatos_avaliacao
  for select to authenticated
  using (
    exists (
      select 1 from public.planos_ensino plano
      where plano.id = candidatos_avaliacao.plano_id
        and plano.user_id = (select auth.uid())
    )
  );

-- A migração 20261029160000 já mantém a leitura das avaliações do dono.
drop policy if exists "Dono gerencia suas avaliacoes" on public.avaliacoes;
drop policy if exists "Dono consulta suas avaliacoes" on public.avaliacoes;
