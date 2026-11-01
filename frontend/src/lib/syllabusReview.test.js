import test from 'node:test';
import assert from 'node:assert/strict';
import { createReviewDraft, validReviewDate, validUtcOffset, validateReviewItem } from './syllabusReview.js';

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
