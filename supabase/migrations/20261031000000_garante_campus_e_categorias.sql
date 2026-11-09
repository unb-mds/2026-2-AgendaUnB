-- Cadastros obrigatórios para as opções do formulário de eventos.
-- Também devem existir em bancos que recebem migrações sem executar seed.sql.
-- Preserva registros e IDs existentes, inclusive vínculos com eventos.
INSERT INTO public.campus (nome) VALUES
  ('Darcy Ribeiro (Plano Piloto)'),
  ('Faculdade do Gama (FCTE)'),
  ('Faculdade de Ceilândia (FCTS)'),
  ('Faculdade de Planaltina (FUP)'),
  ('Fazenda Água Limpa (FAL)')
ON CONFLICT (nome) DO NOTHING;

INSERT INTO public.categories (nome) VALUES
  ('Acadêmico'),
  ('Cultura'),
  ('Esporte'),
  ('Extensão'),
  ('Lazer'),
  ('Comunicado'),
  ('Reunião')
ON CONFLICT (nome) DO NOTHING;
