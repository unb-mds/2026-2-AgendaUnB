BEGIN;

-- Avaliações legadas e planos só podem ser consultados por seu dono.
-- O backend/worker realiza alterações de processamento com sua conexão privilegiada.
DROP POLICY IF EXISTS "avaliacoes sao publicas" ON public.avaliacoes;
DROP POLICY IF EXISTS "planos particulares: usuario le apenas os proprios planos" ON public.planos_ensino;
DROP POLICY IF EXISTS "planos particulares: usuario cria os proprios planos" ON public.planos_ensino;
DROP POLICY IF EXISTS "Dono gerencia seus planos" ON public.planos_ensino;
DROP POLICY IF EXISTS "Dono gerencia candidatos de seus planos" ON public.candidatos_avaliacao;
DROP POLICY IF EXISTS "Dono gerencia suas avaliacoes" ON public.avaliacoes;

CREATE POLICY "Dono consulta seus planos" ON public.planos_ensino
  FOR SELECT TO authenticated USING (user_id = (SELECT auth.uid()));

-- Candidatos só são alterados pela função de confirmação, depois de validar
-- propriedade, execução e os dados necessários para criar o evento.
CREATE POLICY "Dono consulta candidatos de seus planos" ON public.candidatos_avaliacao
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.planos_ensino p
            WHERE p.id = plano_id AND p.user_id = (SELECT auth.uid()))
  );

CREATE POLICY "Dono consulta suas avaliacoes" ON public.avaliacoes
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.planos_ensino p
            WHERE p.id = plano_id AND p.user_id = (SELECT auth.uid()))
  );

COMMIT;
