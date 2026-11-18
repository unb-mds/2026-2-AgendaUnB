import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clearPublicCache,
  getCachedPublic,
  isCachedPublicFresh,
  PUBLIC_EVENTS_CACHE_KEY,
  PUBLIC_EVENTS_FRESH_TTL_MS,
  PUBLIC_EVENTS_MAX_STALE_TTL_MS,
  setCachedPublic,
  toApiEvent,
  toUiEvent,
} from './publicEventsCache.js';

function createMemoryStorage() {
  const store = new Map();
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => { store.set(key, String(value)); },
    removeItem: (key) => { store.delete(key); },
  };
}

test('armazena e recupera eventos públicos em cache respeitando TTL fresco e expirado', () => {
  const storage = createMemoryStorage();
  const baseTime = 1_700_000_000_000;
  const sample = [{ id: 'ev-1', title: 'Semana Universitária', starts_at: '2026-11-15T14:00:00Z' }];

  setCachedPublic(sample, baseTime, storage);
  assert.deepEqual(getCachedPublic(baseTime + 1000, storage), sample);
  assert.equal(isCachedPublicFresh(baseTime + PUBLIC_EVENTS_FRESH_TTL_MS, storage), true);
  assert.equal(isCachedPublicFresh(baseTime + PUBLIC_EVENTS_FRESH_TTL_MS + 1, storage), false);

  // Ainda utilizável em modo stale-while-revalidate antes de 24h
  assert.deepEqual(getCachedPublic(baseTime + PUBLIC_EVENTS_MAX_STALE_TTL_MS, storage), sample);

  // Expirado após 24h e removido do storage
  assert.equal(getCachedPublic(baseTime + PUBLIC_EVENTS_MAX_STALE_TTL_MS + 1, storage), null);
  assert.equal(storage.getItem(PUBLIC_EVENTS_CACHE_KEY), null);
});

test('clearPublicCache invalida a leitura em memória e no storage', () => {
  const storage = createMemoryStorage();
  const now = 1_700_000_000_000;
  setCachedPublic([{ id: 'ev-2', title: 'Palestra', starts_at: '2026-11-16T10:00:00Z' }], now, storage);
  assert.ok(getCachedPublic(now, storage));

  clearPublicCache(storage);
  assert.equal(getCachedPublic(now, storage), null);
  assert.equal(isCachedPublicFresh(now, storage), false);
});

test('ignora JSON corrompido ou payload inesperado no storage sem lançar erro', () => {
  const storage = createMemoryStorage();
  storage.setItem(PUBLIC_EVENTS_CACHE_KEY, '{invalido');
  assert.equal(getCachedPublic(Date.now(), storage), null);

  storage.setItem(PUBLIC_EVENTS_CACHE_KEY, JSON.stringify({ events: 'nao-array', timestamp: Date.now() }));
  assert.equal(getCachedPublic(Date.now(), storage), null);
});

test('toUiEvent e toApiEvent convertem eventos públicos e privados mantendo o contrato', () => {
  const ui = toUiEvent({
    id: '11111111-1111-4111-8111-111111111111',
    title: 'Oficina de Robótica',
    description: 'Aberta ao público',
    starts_at: '2026-11-20T17:30:00Z',
    campus: 'Faculdade do Gama (FCTE)',
    category: 'Extensão',
    location: 'MOCAP',
    external_url: 'https://agendaunb.com.br',
    organizer_name: 'Docente UnB',
    organizer_avatar: null,
    source: 'agenda_unb_noticias',
    source_url: 'https://noticias.unb.br/component/agenda/agenda/42',
    all_day: false,
  });

  assert.equal(ui.titulo, 'Oficina de Robótica');
  assert.equal(ui.visibilidade, 'Público');
  assert.equal(ui.criadoPorMim, false);
  assert.equal(ui.campus, 'Faculdade do Gama (FCTE)');
  assert.equal(ui.area, 'Extensão');
  assert.equal(ui.fonte, 'agenda_unb_noticias');
  assert.equal(ui.fonteUrl, 'https://noticias.unb.br/component/agenda/agenda/42');
  assert.equal(ui.diaInteiro, false);

  const allDayUi = toUiEvent({
    id: '22222222-2222-4222-8222-222222222222',
    title: 'Semana Universitária 2026',
    starts_at: '2026-11-18T03:00:00Z',
    start_date: '2026-11-18',
    end_date: '2026-11-21',
    all_day: true,
    source: 'agenda_unb_noticias',
    source_url: 'https://noticias.unb.br/component/agenda/agenda/100',
  });

  assert.equal(allDayUi.diaInteiro, true);
  assert.equal(allDayUi.data, '2026-11-18');
  assert.equal(allDayUi.horario, 'Dia inteiro');
  assert.equal(allDayUi.fonte, 'agenda_unb_noticias');
  assert.equal(allDayUi.fonteUrl, 'https://noticias.unb.br/component/agenda/agenda/100');

  const apiPayload = toApiEvent({
    titulo: '  Reunião do Centro Acadêmico  ',
    data: '2026-11-21',
    horario: '14:00',
    campus: 'Darcy Ribeiro (Plano Piloto)',
    local: 'ICC Sul',
    area: 'Acadêmico',
    descricao: '  Pauta semestral  ',
    linkExterno: '',
  });

  assert.equal(apiPayload.title, 'Reunião do Centro Acadêmico');
  assert.equal(apiPayload.description, 'Pauta semestral');
  assert.equal(apiPayload.location, 'ICC Sul');
  assert.equal('external_url' in apiPayload, false);
  assert.ok(apiPayload.starts_at.endsWith('Z'));
});

test('toUiEvent usa fuso America/Sao_Paulo e toApiEvent trata dia inteiro e intervalos', () => {
  // 2026-11-19T01:30:00Z corresponde a 18/11 às 22:30 em Brasília (-03:00)
  const lateNightUi = toUiEvent({
    id: '33333333-3333-4333-8333-333333333333',
    title: 'Observação Astronômica',
    starts_at: '2026-11-19T01:30:00Z',
    ends_at: '2026-11-19T02:30:00Z',
    outbound_clicks_count: 7,
  });

  assert.equal(lateNightUi.data, '2026-11-18');
  assert.equal(lateNightUi.horario, '22:30');
  assert.equal(lateNightUi.horarioFim, '23:30');
  assert.equal(lateNightUi.interessadosCount, 7);

  const allDayPayload = toApiEvent({
    titulo: 'Semana Universitária',
    data: '2026-11-18',
    dataFim: '2026-11-20',
    diaInteiro: true,
  });
  assert.equal(allDayPayload.all_day, true);
  assert.equal(allDayPayload.start_date, '2026-11-18');
  assert.equal(allDayPayload.end_date, '2026-11-21');

  const timedRange = toApiEvent({
    titulo: 'Oficina',
    data: '2026-11-20',
    horario: '14:00',
    horarioFim: '16:00',
  });
  assert.equal(timedRange.all_day, false);
  assert.ok(timedRange.ends_at.endsWith('Z'));

  assert.throws(() => toApiEvent({
    titulo: 'Inválido',
    data: '2026-11-20',
    horario: '14:00',
    horarioFim: '13:00',
  }));
});
