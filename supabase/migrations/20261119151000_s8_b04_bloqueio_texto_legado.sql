alter table public.planos_ensino
  drop constraint planos_erro_codigo_valido,
  add constraint planos_erro_codigo_valido check (erro_codigo is null or erro_codigo in (
    'pdf_invalido', 'pdf_protegido', 'pdf_sem_texto', 'limite_paginas',
    'falha_ia', 'tempo_esgotado', 'erro_interno', 'texto_com_dados_pessoais'
  ));
