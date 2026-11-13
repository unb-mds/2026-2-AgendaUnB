import test from 'node:test';
import assert from 'node:assert/strict';
import { createCandidateReviewDraft, selectReviewItems, createReviewDraft, validReviewDate, validUtcOffset, validateReviewItem } from './syllabusReview.js';

test('candidatos usam sugestões civis e só preservam fuso explícito da origem', () => {
  const candidates = [
    { id: 'a', status: 'pendente', suggestedDate: '2026-12-01', suggestedTime: '14:30:45' },
    { id: 'b', status: 'confirmado', startsAt: '2026-12-01T14:30:00-03:00' },
    { id: 'c', status: 'desconhecido', startsAt: '2026-12-01T14:30:00' },
  ];
  const [a, b, c] = createCandidateReviewDraft(candidates);
  assert.equal(a.date, '2026-12-01'); assert.equal(a.time, '14:30:45'); assert.equal(a.utcOffset, '');
  assert.equal(b.utcOffset, '-03:00'); assert.equal(b.editable, false);
  assert.equal(c.date, ''); assert.equal(c.utcOffset, ''); assert.equal(c.editable, false);
  assert.ok([a, b, c].every(item => item.decision === 'pending'));
});

test('lote preserva exclusões locais, correções e estados persistidos', () => {
  const items = [
    { id: 'a', decision: 'pending', editable: true, title: 'Corrigido' },
    { id: 'b', decision: 'discarded', editable: true },
    { id: 'c', decision: 'pending', editable: false },
  ];
  const selected = selectReviewItems(items, true);
  assert.deepEqual(selected.map(item => item.decision), ['selected', 'discarded', 'pending']);
  assert.equal(selected[0].title, 'Corrigido');
  assert.equal(items[0].decision, 'pending');
  assert.deepEqual(selectReviewItems(selected, false).map(item => item.decision), ['pending', 'discarded', 'pending']);
});

test('validação da revisão real respeita limites de título e tipos de avaliação', () => {
  const item = { decision: 'selected', title: 'Prova', type: 'prova', date: '2026-12-01', time: '14:30:45', utcOffset: '-03:00' };
  assert.deepEqual(validateReviewItem(item, true), {});
  for (const title of ['ab', ' '.repeat(3), 'a'.repeat(201)]) assert.ok(validateReviewItem({ ...item, title }, true).title);
  assert.deepEqual(validateReviewItem({ ...item, title: 'a'.repeat(200) }, true), {});
  assert.ok(validateReviewItem({ ...item, type: 'aula' }, true).type);
  assert.ok(validateReviewItem({ ...item, time: '14:30:60' }, true).time);
});

test('rascunho não seleciona itens nem infere horário ou fuso', () => {
  const source = [{ id: 'a', title: 'Prova', date: '2026-11-10' }];
  const [draft] = createReviewDraft(source);
  assert.equal(draft.decision, 'pending');
  assert.equal(draft.time, '');
  assert.equal(draft.utcOffset, '');
  draft.title = 'Alterada';
  assert.equal(source[0].title, 'Prova');
});
test('rejeita lista inválida e identificadores ausentes ou duplicados', () => {
  for (const value of [null, {}, [null], [{}], [{ id: 'a' }, { id: 'a' }]]) {
    assert.throws(() => createReviewDraft(value));
  }
  assert.deepEqual(createReviewDraft([]), []);
});
test('datas reais, incluindo anos bissextos, sem normalização silenciosa', () => {
  for (const date of ['2024-02-29', '2026-12-31']) assert.equal(validReviewDate(date), true);
  for (const date of ['', '2026-02-29', '2026-04-31', '0000-01-01', '2026-13-01']) assert.equal(validReviewDate(date), false);
});
test('fuso explícito e limites de deslocamento UTC', () => {
  for (const zone of ['-03:00', '+00:00', '+05:45', '-12:00', '+14:00']) assert.equal(validUtcOffset(zone), true);
  for (const zone of ['', 'Brasília', '-3:00', '+14:01', '+15:00', '-00:00', '+03:60']) assert.equal(validUtcOffset(zone), false);
});
test('somente selecionados exigem campos; revisão parcial é permitida', () => {
  const [draft] = createReviewDraft([{ id: 'a' }]);
  assert.deepEqual(validateReviewItem(draft), {});
  assert.deepEqual(validateReviewItem({ ...draft, decision: 'discarded' }), {});
  assert.deepEqual(Object.keys(validateReviewItem({ ...draft, decision: 'selected' })), ['title', 'date', 'time', 'utcOffset']);
  const valid = { ...draft, decision: 'selected', title: 'Prova', date: '2026-11-10', time: '00:00', utcOffset: '-03:00' };
  assert.deepEqual(validateReviewItem(valid), {});
  for (const time of ['24:00', '12:60', '9:00']) assert.ok(validateReviewItem({ ...valid, time }).time);
});
