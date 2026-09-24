CREATE TABLE campus (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  nome TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


CREATE TABLE categories (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  nome TEXT NOT NULL UNIQUE,
  cor TEXT, -- Opcional: para o frontend colorir a badge do evento
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE eventos_pessoais 
ADD COLUMN campus_id UUID REFERENCES campus(id),
ADD COLUMN category_id UUID REFERENCES categories(id);

ALTER TABLE campus ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir leitura pública de campus" ON campus FOR SELECT USING (true);
CREATE POLICY "Permitir leitura pública de categorias" ON categories FOR SELECT USING (true);