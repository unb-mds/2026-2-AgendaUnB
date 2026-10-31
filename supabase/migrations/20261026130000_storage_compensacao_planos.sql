-- Compensação do upload (#40): o backend usa a sessão validada do dono.
-- Mantém o bucket privado e não permite remover arquivos de outros usuários.
drop policy if exists "planos: usuario remove da propria pasta" on storage.objects;
create policy "planos: usuario remove da propria pasta"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'syllabus_files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
