CREATE TABLE eventos_pessoais (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  titulo TEXT NOT NULL,
  descricao TEXT,
  data_hora TIMESTAMP WITH TIME ZONE NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) DEFAULT auth.uid(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE eventos_pessoais ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Usuários podem ver seus próprios eventos"
ON eventos_pessoais FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Usuários podem criar eventos"
ON eventos_pessoais FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Usuários podem atualizar seus próprios eventos"
ON eventos_pessoais FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Usuários podem deletar seus próprios eventos"
ON eventos_pessoais FOR DELETE
USING (auth.uid() = user_id);