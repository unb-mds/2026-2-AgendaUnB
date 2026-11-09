BEGIN;

-- O deslocamento em minutos é o fuso escolhido explicitamente na revisão
-- (por exemplo, -180 para UTC-03:00). A data/hora do candidato é local.
CREATE OR REPLACE FUNCTION public.confirmar_candidatos_transacional(
    p_candidato_ids UUID[], p_utc_offset_minutes INTEGER
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_uid UUID := auth.uid();
    v_candidato RECORD;
    v_evento_id UUID;
    v_processados INTEGER := 0;
BEGIN
    IF v_uid IS NULL THEN
        RAISE EXCEPTION 'Usuário não autenticado' USING ERRCODE = '42501';
    END IF;
    IF p_utc_offset_minutes IS NULL OR p_utc_offset_minutes NOT BETWEEN -840 AND 840 THEN
        RAISE EXCEPTION 'Deslocamento UTC inválido' USING ERRCODE = '22023';
    END IF;
    IF p_candidato_ids IS NULL OR cardinality(p_candidato_ids) NOT BETWEEN 1 AND 100
       OR array_position(p_candidato_ids, NULL) IS NOT NULL
       OR cardinality(p_candidato_ids) <> (SELECT count(DISTINCT id) FROM unnest(p_candidato_ids) AS ids(id)) THEN
        RAISE EXCEPTION 'Lista de candidatos inválida' USING ERRCODE = '22023';
    END IF;

    FOR v_candidato IN
        SELECT c.id, c.titulo, c.data_sugerida, c.hora_sugerida,
               c.status, c.execucao, p.execucao_atual, p.status AS plano_status,
               p.user_id
          FROM public.candidatos_avaliacao c
          JOIN public.planos_ensino p ON p.id = c.plano_id
         WHERE c.id = ANY(p_candidato_ids)
         ORDER BY c.id
         FOR UPDATE OF c
    LOOP
        IF v_candidato.user_id IS DISTINCT FROM v_uid THEN
            RAISE EXCEPTION 'Candidato não pertence ao usuário' USING ERRCODE = '42501';
        END IF;
        IF v_candidato.plano_status <> 'concluido'
           OR v_candidato.execucao <> v_candidato.execucao_atual
           OR v_candidato.status <> 'pendente' THEN
            RAISE EXCEPTION 'Candidato indisponível para confirmação' USING ERRCODE = '22023';
        END IF;
        IF v_candidato.data_sugerida IS NULL OR v_candidato.hora_sugerida IS NULL
           OR char_length(btrim(v_candidato.titulo)) < 3 THEN
            RAISE EXCEPTION 'Revise data, hora e título antes de confirmar' USING ERRCODE = '22023';
        END IF;

        INSERT INTO public.eventos_pessoais (user_id, titulo, data_hora)
        VALUES (v_uid, v_candidato.titulo,
                (v_candidato.data_sugerida + v_candidato.hora_sugerida
                 - make_interval(mins => p_utc_offset_minutes)) AT TIME ZONE 'UTC')
        RETURNING id INTO v_evento_id;

        UPDATE public.candidatos_avaliacao
           SET status = 'confirmado', revisado_em = now(), evento_pessoal_id = v_evento_id
         WHERE id = v_candidato.id;
        v_processados := v_processados + 1;
    END LOOP;

    IF v_processados <> cardinality(p_candidato_ids) THEN
        RAISE EXCEPTION 'Candidato não encontrado' USING ERRCODE = '22023';
    END IF;
END;
$$;

-- A assinatura antiga não tinha fuso e não deve permanecer executável.
DROP FUNCTION IF EXISTS public.confirmar_candidatos_transacional(UUID[]);
REVOKE ALL ON FUNCTION public.confirmar_candidatos_transacional(UUID[], INTEGER) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.confirmar_candidatos_transacional(UUID[], INTEGER) TO authenticated;

COMMIT;
