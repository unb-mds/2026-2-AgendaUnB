BEGIN;

-- 1. Criação da Tabela de Origens de Coleta (Para evitar duplicidade e saber de onde veio)
CREATE TABLE public.eventos_coletados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Dados brutos originais para auditoria e revisão
    url_origem TEXT NOT NULL UNIQUE, -- Chave única exigida na issue (Upsert/Deduplicação)
    hash_conteudo TEXT NOT NULL,     -- Para saber se o evento mudou desde a última coleta
    fonte TEXT NOT NULL DEFAULT 'Agenda UnB Notícias',
    
    -- Dados normalizados (Task 3 da Issue)
    titulo TEXT NOT NULL,
    descricao TEXT,
    data_inicio TIMESTAMPTZ,
    data_fim TIMESTAMPTZ,
    dia_inteiro BOOLEAN DEFAULT false,
    local TEXT, -- Equivalente a campus, mas em texto livre por vir de raspagem
    link_externo TEXT,
    
    -- Controle de Publicação Automática ou Revisão (Task 4 da Issue)
    status_revisao TEXT NOT NULL DEFAULT 'revisao_pendente'
        CHECK (status_revisao IN ('publicado_automaticamente', 'revisao_pendente', 'rejeitado')),
    
    -- Identificação de ambiguidades para o backend preencher
    motivo_revisao TEXT,
    
    -- Se foi publicado, guarda o link para a tabela oficial de eventos públicos
    evento_publico_id UUID REFERENCES public.eventos(id) ON DELETE SET NULL,
    
    ultima_coleta_em TIMESTAMPTZ DEFAULT NOW(),
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Índices de Performance e Buscas do Coletor
CREATE INDEX idx_eventos_coletados_url ON public.eventos_coletados(url_origem);
CREATE INDEX idx_eventos_coletados_status ON public.eventos_coletados(status_revisao);

-- 3. Segurança (RLS)
ALTER TABLE public.eventos_coletados ENABLE ROW LEVEL SECURITY;

-- Apenas a role de serviço do backend (Service Role) pode Inserir/Atualizar eventos da raspagem
-- Usuários comuns não interagem diretamente com essa tabela transitória.
CREATE POLICY "Acesso total para a Service Role"
    ON public.eventos_coletados FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- (Opcional) Permite leitura pública se a moderação quiser mostrar a procedência
CREATE POLICY "Leitura pública de eventos coletados"
    ON public.eventos_coletados FOR SELECT
    USING (true);

COMMIT;