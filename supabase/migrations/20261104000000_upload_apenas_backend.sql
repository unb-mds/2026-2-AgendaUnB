-- O upload passa pelo backend, que valida PDF e aplica a cota por usuário.
-- Manter INSERT pelo SDK permitiria contornar a cota e enviar PDFs diretamente.
DROP POLICY IF EXISTS "planos: usuario envia para a propria pasta" ON storage.objects;
