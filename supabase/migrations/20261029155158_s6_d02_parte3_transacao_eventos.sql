BEGIN;

CREATE OR REPLACE FUNCTION public.confirmar_candidatos_transacional(
    p_candidato_ids UUID[]
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER 
AS $$
DECLARE
    v_uid UUID := auth.uid();
    v_candidato RECORD;
    v_novo_evento_id UUID;
BEGIN
    IF v_uid IS NULL THEN
        RAISE EXCEPTION 'Acesso negado: Usuário não autenticado.';
    END IF;

    FOR v_candidato IN 
        SELECT c.id, c.titulo, c.data_horario, c.status_candidato, p.proprietario_id
        FROM public.candidatos_eventos c
        JOIN public.planos_ensino p ON c.plano_id = p.id
        WHERE c.id = ANY(p_candidato_ids)
    LOOP
        IF v_candidato.proprietario_id != v_uid THEN
            RAISE EXCEPTION 'Operação não permitida: O candidato % não pertence ao seu usuário.', v_candidato.id;
        END IF;

        IF v_candidato.status_candidato != 'pendente' THEN
            CONTINUE; 
        END IF;

        INSERT INTO public.eventos_pessoais (user_id, titulo, data_hora)
        VALUES (v_uid, v_candidato.titulo, v_candidato.data_horario)
        RETURNING id INTO v_novo_evento_id;

        UPDATE public.candidatos_eventos
        SET status_candidato = 'confirmado',
            evento_pessoal_id = v_novo_evento_id
        WHERE id = v_candidato.id;
        
    END LOOP;
END;
$$;

COMMIT;