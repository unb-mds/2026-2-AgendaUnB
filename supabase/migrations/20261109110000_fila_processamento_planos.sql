-- S6-B01: lease com fencing e orçamento conservador persistido por arquivo.
-- Depende da S6-D01. Não substitui as políticas de privacidade da S6-D02.
alter table public.planos_ensino
  add column token_processamento uuid,
  add column proxima_tentativa_em timestamptz,
  add column custo_reservado_usd numeric(12,6) not null default 0
    check (custo_reservado_usd >= 0),
  add column duracao_processamento_ms integer
    check (duracao_processamento_ms is null or duracao_processamento_ms >= 0);

comment on column public.planos_ensino.token_processamento is
  'Fencing token: somente o worker com o lease atual pode finalizar a execução.';
comment on column public.planos_ensino.custo_reservado_usd is
  'Reserva acumulada de custo máximo. Não é cobrança medida. Não devolver reserva após falha ou interrupção: a chamada pode ter sido cobrada.';
comment on column public.planos_ensino.duracao_processamento_ms is
  'Duração da última tentativa, da leitura do Storage à persistência. Espera na fila é medida por criado_em/processado_em.';

-- Não habilitar o worker para dados reais até a S6-D02 impedir escrita direta
-- de clientes sobre estado, leases, orçamento e candidatos, além da leitura cruzada.
