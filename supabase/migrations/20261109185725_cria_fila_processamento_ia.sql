BEGIN;

-- 1. Criação da Tabela de Fila (Job Queue)
CREATE TABLE public.fila_processamento_ia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plano_id UUID NOT NULL REFERENCES public.planos_ensino(id) ON DELETE CASCADE,

    -- Controle de Estado (Atende ao requisito de timeout e 429)
    status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'processando', 'concluido', 'erro', 'rate_limit', 'timeout')),

    -- Controle de Recuperação (Atende ao "processamento recuperável")
    tentativas INT NOT NULL DEFAULT 0,
    limite_tentativas INT NOT NULL DEFAULT 3,
    proxima_tentativa TIMESTAMPTZ DEFAULT NOW(),

    -- Logs isolados (Atende ao "logs sem conteúdo acadêmico")
    -- Instrução de negócio: Salvar apenas códigos HTTP (ex: 429, 504) ou mensagens de falha de conexão.
    erro_tecnico TEXT,

    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Índices para Otimização de Busca do Worker (Essencial para filas)
CREATE INDEX idx_fila_ia_status_proxima ON public.fila_processamento_ia(status, proxima_tentativa);
CREATE INDEX idx_fila_ia_plano ON public.fila_processamento_ia(plano_id);

-- 3. Segurança (RLS)
ALTER TABLE public.fila_processamento_ia ENABLE ROW LEVEL SECURITY;

-- Permite que o usuário dono do plano acompanhe o andamento na fila, mas apenas o backend (Service Role) edita a fila.
CREATE POLICY "Usuário vê status do seu plano na fila"
    ON public.fila_processamento_ia FOR SELECT
    USING (
        plano_id IN (SELECT id FROM public.planos_ensino WHERE professor_id = auth.uid())
    );

COMMIT;
