-- =============================================================
-- Issue #43 — Bucket e RLS para planos de ensino (RNF02)
--
-- Os PDFs de plano de ensino ficam num bucket privado. Cada
-- usuário só enxerga os próprios arquivos; o back-end lê todos
-- para processar.
--
-- Convenção de caminho (obrigatória, as políticas dependem dela):
--   syllabus_files/<user_id>/<nome-do-arquivo>.pdf
--
-- Uso no front:
--   const caminho = `${user.id}/${arquivo.name}`;
--   await supabase.storage.from('syllabus_files').upload(caminho, arquivo);
--   await supabase.storage.from('syllabus_files').createSignedUrl(caminho, 60);
-- =============================================================


-- -------------------------------------------------------------
-- 1. Bucket privado
--
-- public = false: não existe URL pública. Todo acesso passa pela
-- API do Storage, que aplica as políticas abaixo.
-- Só aceita PDF, até 10 MB.
-- -------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'syllabus_files',
  'syllabus_files',
  false,
  10485760,                       -- 10 MB
  array['application/pdf']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;


-- -------------------------------------------------------------
-- 2. Sem acesso anônimo
--
-- Nenhuma política abaixo é para o papel anon. Como o RLS de
-- storage.objects nega tudo que não tem política, visitante não
-- logado não lista, não baixa e não envia nada.
-- -------------------------------------------------------------


-- -------------------------------------------------------------
-- 3. Upload: só usuário logado, e só na própria pasta
--
-- (storage.foldername(name))[1] é a primeira pasta do caminho.
-- Obrigar que seja o próprio id impede alguém de gravar na pasta
-- de outra pessoa e garante que a regra de leitura funcione.
-- -------------------------------------------------------------
create policy "planos: usuario envia para a propria pasta"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'syllabus_files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );


-- -------------------------------------------------------------
-- 4. Download: só os próprios PDFs
-- -------------------------------------------------------------
create policy "planos: usuario le apenas os proprios arquivos"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'syllabus_files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );


-- -------------------------------------------------------------
-- 5. Leitura pelo back-end (workers de processamento)
--
-- O back-end acessa o Storage com a chave service_role, que no
-- Supabase já ignora RLS. Esta política deixa a permissão
-- explícita e documentada, caso isso mude.
--
-- A chave service_role nunca pode ir para o front, para variável
-- VITE_ ou para o repositório: quem a tiver lê todos os arquivos.
-- -------------------------------------------------------------
create policy "planos: back-end le todos os arquivos"
  on storage.objects for select
  to service_role
  using (bucket_id = 'syllabus_files');
