BEGIN;

DROP POLICY IF EXISTS "avaliacoes sao publicas" ON public.avaliacoes;

DROP POLICY IF EXISTS "Dono gerencia seus planos" ON public.planos_ensino;
CREATE POLICY "Dono gerencia seus planos" ON public.planos_ensino
  FOR ALL USING (proprietario_id = auth.uid()) WITH CHECK (proprietario_id = auth.uid());

DROP POLICY IF EXISTS "Dono gerencia candidatos de seus planos" ON public.candidatos_eventos;
CREATE POLICY "Dono gerencia candidatos de seus planos" ON public.candidatos_eventos
  FOR ALL USING (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE proprietario_id = auth.uid())
  ) WITH CHECK (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE proprietario_id = auth.uid())
  );

DROP POLICY IF EXISTS "Dono gerencia suas avaliacoes" ON public.avaliacoes;
CREATE POLICY "Dono gerencia suas avaliacoes" ON public.avaliacoes
  FOR ALL USING (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE proprietario_id = auth.uid())
  ) WITH CHECK (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE proprietario_id = auth.uid())
  );

COMMIT;