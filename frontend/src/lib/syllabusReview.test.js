import test from 'node:test';
import assert from 'node:assert/strict';
import { buildReviewConfirmation, createCandidateReviewDraft, selectReviewItems, createReviewDraft, updateCandidateReviewItem, validReviewDate, validUtcOffset, validateReviewItem } from './syllabusReview.js';

test('o catálogo só preenche provas pendentes sem hora explícita e com data confiável', () => {
  const exam = { id: 'a', type: 'prova', status: 'pendente', suggestedDate: '2026-11-10' };
  const drafts = createCandidateReviewDraft([
    exam,
    { ...exam, id: 'b', suggestedTime: '16:30' },
    { ...exam, id: 'c', type: 'trabalho' },
    { ...exam, id: 'd', ambiguousFields: ['data'] },
    { ...exam, id: 'e', status: 'confirmado' },
  ], '3T23');
  assert.deepEqual(drafts.map(({ time }) => time), ['14:00', '16:30', '', '', '']);
  assert.deepEqual(drafts.map(({ timeSource }) => timeSource), ['catalog', 'plan', null, null, null]);
  assert.ok(drafts.every(({ decision }) => decision === 'pending'));
});

test('mudar a data atualiza a sugestão da turma e preserva o horário digitado', () => {
  const schedule = '3T23 5M12';
  const [exam] = createCandidateReviewDraft([
    { id: 'a', type: 'prova', status: 'pendente', suggestedDate: '2026-11-10' },
  ], schedule);
  const thursday = updateCandidateReviewItem(exam, { date: '2026-11-12' }, schedule);
  assert.equal(thursday.time, '08:00');
  assert.equal(updateCandidateReviewItem(thursday, { date: '2026-11-11' }, schedule).time, '');
  for (const time of ['09:30', '']) {
    const manual = updateCandidateReviewItem(thursday, { time }, schedule);
    assert.equal(updateCandidateReviewItem(manual, { date: '2026-11-10' }, schedule).time, time);
    assert.equal(manual.timeSource, 'manual');
  }
});

test('candidatos usam sugestões civis e convertem startsAt explícito para Brasília', () => {
  const candidates = [
    { id: 'a', status: 'pendente', suggestedDate: '2026-12-01', suggestedTime: '14:30:45' },
    { id: 'b', status: 'confirmado', startsAt: '2026-12-01T14:30:00Z' },
    { id: 'c', status: 'desconhecido', startsAt: '2026-12-01T14:30:00' },
  ];
  const [a, b, c] = createCandidateReviewDraft(candidates);
  assert.equal(a.date, '2026-12-01'); assert.equal(a.time, '14:30:45');
  assert.equal(b.date, '2026-12-01'); assert.equal(b.time, '11:30:00'); assert.equal(b.editable, false);
  assert.equal(c.date, ''); assert.equal(c.editable, false);
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

test('rascunho não seleciona itens nem infere horário', () => {
  const source = [{ id: 'a', title: 'Prova', date: '2026-11-10' }];
  const [draft] = createReviewDraft(source);
  assert.equal(draft.decision, 'pending');
  assert.equal(draft.time, '');
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
  assert.deepEqual(Object.keys(validateReviewItem({ ...draft, decision: 'selected' })), ['title', 'date', 'time']);
  const valid = { ...draft, decision: 'selected', title: 'Prova', date: '2026-11-10', time: '00:00' };
  assert.deepEqual(validateReviewItem(valid), {});
  for (const time of ['24:00', '12:60', '9:00']) assert.ok(validateReviewItem({ ...valid, time }).time);
});
test('buildReviewConfirmation inclui tipo revisado, título, data em Brasília (-03:00) e procedência', () => {
  const candidates = [{ id: 'a', status: 'pendente', sourceExcerpt: 'Prova escrita.' }];
  const draft = [{
    id: 'a', decision: 'selected', title: '  Prova 1  ', type: 'Prova',
    date: '2026-12-01', time: '14:00',
  }];
  const [payload] = buildReviewConfirmation(draft, candidates);
  assert.deepEqual(payload, {
    candidateId: 'a',
    title: 'Prova 1',
    type: 'prova',
    startsAt: '2026-12-01T14:00-03:00',
    category: 'Acadêmico',
    description: 'Tipo de avaliação: Prova\n\nProva escrita.',
  });
});
