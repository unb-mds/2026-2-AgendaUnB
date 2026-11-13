import test from 'node:test';
import assert from 'node:assert/strict';
import { catalogPeriods, loadDemoCatalog, searchOfferings } from './classCatalogDemo.js';

test('os dois períodos avançam na virada do semestre e do ano em Brasília', () => {
  assert.deepEqual(catalogPeriods(new Date('2026-07-01T02:59:59Z')), ['2026.1', '2026.2']);
  assert.deepEqual(catalogPeriods(new Date('2026-07-01T03:00:00Z')), ['2026.2', '2027.1']);
  assert.deepEqual(catalogPeriods(new Date('2027-01-01T03:00:00Z')), ['2027.1', '2027.2']);
});

test('busca sem acentos e com espaços identifica professor, código e número de turma no período', async () => {
  const { items } = await loadDemoCatalog(['2026.2', '2027.1']);
  const find = (period, query) => searchOfferings(items, period, query).map(offer => offer.id);
  assert.deepEqual(find('2026.2', ' calculo  03 '), ['cal:2026.2', 'cal-fga:2026.2']);
  assert.deepEqual(find('2026.2', 'LUCIA NUNES'), ['cal:2026.2']);
  assert.deepEqual(find('2027.1', 'MAT0025'), ['cal:2027.1']);
  assert.deepEqual(find('2025.1', 'calculo'), []);
});
