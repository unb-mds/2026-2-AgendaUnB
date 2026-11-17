import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mergeReview, needsAttention } from './semesterReview.js';

const candidate = (id, overrides = {}) => ({
  id, title: `Avaliação ${id}`, status: 'pendente', type: 'trabalho',
  suggestedDate: '2026-11-23', suggestedTime: null, versionId: 'v1',
  ambiguous: false, ambiguousFields: [], ...overrides,
});
const plan = (...candidates) => ({ id: 'plano', offeringId: 'turma', candidates });

test('pré-seleciona datas completas e mantém pendências, descartes e confirmadas fora do lote', () => {
  const rows = mergeReview(plan(
    candidate('A'),
    candidate('B', { type: 'prova' }),
    candidate('C', { ambiguous: true, ambiguousFields: ['data'] }),
    candidate('D', { status: 'confirmado' }),
    candidate('E', { status: 'descartado' }),
  ), null, {});
  assert.deepEqual(rows.filter(row => row.selected).map(row => row.id), ['A']);
  assert.deepEqual(rows.filter(needsAttention).map(row => row.id), ['B', 'C']);
});

test('atualização mantém correção e exclusão manual na versão revisada', () => {
  const source = candidate('A');
  const [first] = mergeReview(plan(source), null, {});
  const drafts = { [first.key]: { ...first, selected: false, edits: { date: '2026-12-03' } } };
  const [updated] = mergeReview(plan({ ...source, sourceExcerpt: 'Origem atualizada' }), null, drafts);
  assert.equal(updated.date, '2026-12-03');
  assert.equal(updated.selected, false);
  const [nextVersion] = mergeReview(plan({ ...source, versionId: 'v2' }), null, drafts);
  assert.equal(nextVersion.date, source.suggestedDate);
  assert.equal(nextVersion.selected, true);
});

test('alterar a evidência invalida a decisão sobre uma ambiguidade', () => {
  const source = candidate('A', { ambiguous: true, ambiguousFields: ['data'], sourceExcerpt: 'Data a conferir' });
  const [first] = mergeReview(plan(source), null, {});
  const drafts = { [first.key]: { ...first, selected: true, checked: true } };
  assert.equal(mergeReview(plan(source), null, drafts)[0].selected, true);
  const [updated] = mergeReview(plan({ ...source, sourceExcerpt: 'Novo trecho' }), null, drafts);
  assert.equal(updated.checked, false);
  assert.equal(updated.selected, false);
  assert.equal(needsAttention(updated), true);
});
