import test from 'node:test';
import assert from 'node:assert/strict';
import { validatePdf, MAX_PDF_BYTES, normalizePlan, normalizePlanList, syllabusError, isProcessing } from './syllabus.js';

test('PDF: limites, MIME ausente, arquivo vazio e extensão', () => {
  const file = { name: 'plano.PDF', type: 'application/pdf', size: MAX_PDF_BYTES };
  assert.equal(validatePdf(file), '');
  assert.equal(validatePdf({ ...file, type: '' }), '');
  assert.match(validatePdf({ ...file, size: MAX_PDF_BYTES + 1 }), /10 MB/);
  assert.match(validatePdf({ ...file, size: 0 }), /vazio/);
  assert.match(validatePdf({ ...file, name: 'plano.pdf.exe' }), /formato PDF/);
  assert.match(validatePdf({ ...file, type: 'image/png' }), /formato PDF/);
  assert.match(validatePdf(null), /Selecione/);
});

test('resultado ausente não significa análise sem avaliações', () => {
  assert.equal(normalizePlan({ id: '1', status: 'concluido' }).extractedEventsCount, null);
  assert.equal(normalizePlan({ id: '1', extractedEventsCount: 0 }).extractedEventsCount, 0);
  assert.equal(normalizePlan({ id: '1', extractedEventsCount: -1 }).extractedEventsCount, null);
  assert.throws(() => normalizePlanList({ items: [], total: '0' }));
  assert.throws(() => normalizePlan({}));
});

test('somente estados ativos permitem polling; erros são recuperáveis', () => {
  for (const status of ['pendente', 'processando']) assert.equal(isProcessing({ status }), true);
  for (const status of ['concluido', 'falha', 'desconhecido']) assert.equal(isProcessing({ status }), false);
  assert.match(syllabusError({ status: 401 }), /sessão expirou/);
  assert.match(syllabusError({ status: 429 }), /Aguarde/);
  assert.match(syllabusError({ status: 404 }, 'historico'), /histórico ainda não/);
  assert.match(syllabusError(new TypeError('Failed to fetch'), 'envio'), /Confira o histórico/);
});
