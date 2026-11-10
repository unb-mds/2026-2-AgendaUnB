import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { approvedTextHash, approvedTextSize } from './approvedText.js';
import { isProcessing, normalizePlan } from './syllabus.js';

test('hash vincula o texto UTF-8 exato, páginas e espaços aprovados', async () => {
  const pages = [{ pagina: null, texto: 'Prova de cálculo — 10/11/2026.  ' }];
  assert.equal(await approvedTextHash(pages), createHash('sha256').update(JSON.stringify(pages)).digest('hex'));
  assert.notEqual(await approvedTextHash(pages), await approvedTextHash([{ ...pages[0], texto: pages[0].texto.trim() }]));
  assert.equal(approvedTextSize([{ pagina: null, texto: 'é' }]), 2);
});

test('plano aguardando autorização não dispara polling de processamento', () => {
  const plan = normalizePlan({ id: '1', status: 'pendente', authorizationRequired: true, preparedTextAvailable: true });
  assert.equal(isProcessing(plan), false);
  assert.equal(plan.preparedTextAvailable, true);
  assert.equal(isProcessing({ ...plan, authorizationRequired: false }), true);
});
