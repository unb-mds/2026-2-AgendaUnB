BEGIN;

-- Avaliações legadas e planos só podem ser consultados por seu dono.
-- O backend/worker realiza alterações de processamento com sua conexão privilegiada.
DROP POLICY IF EXISTS "avaliacoes sao publicas" ON public.avaliacoes;
DROP POLICY IF EXISTS "planos particulares: usuario le apenas os proprios planos" ON public.planos_ensino;
DROP POLICY IF EXISTS "planos particulares: usuario cria os proprios planos" ON public.planos_ensino;
DROP POLICY IF EXISTS "Dono gerencia seus planos" ON public.planos_ensino;
CREATE POLICY "Dono gerencia seus planos" ON public.planos_ensino
  FOR ALL USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()));

DROP POLICY IF EXISTS "Dono gerencia candidatos de seus planos" ON public.candidatos_avaliacao;
CREATE POLICY "Dono gerencia candidatos de seus planos" ON public.candidatos_avaliacao
  FOR ALL USING (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE user_id = (select auth.uid()))
  ) WITH CHECK (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE user_id = (select auth.uid()))
  );

DROP POLICY IF EXISTS "Dono gerencia suas avaliacoes" ON public.avaliacoes;
CREATE POLICY "Dono gerencia suas avaliacoes" ON public.avaliacoes
  FOR ALL USING (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE user_id = (select auth.uid()))
  ) WITH CHECK (
    plano_id IN (SELECT id FROM public.planos_ensino WHERE user_id = (select auth.uid()))
  );

COMMIT;
