BEGIN;

DROP POLICY IF EXISTS "Restricao de pasta por usuario no storage" ON storage.objects;
CREATE POLICY "Restricao de pasta por usuario no storage" 
  ON storage.objects FOR ALL 
  USING (
    bucket_id = 'planos' 
    AND auth.role() = 'authenticated' 
    AND (storage.foldername(name))[1] = auth.uid()::text
  )
  WITH CHECK (
    bucket_id = 'planos' 
    AND auth.role() = 'authenticated' 
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

COMMIT;