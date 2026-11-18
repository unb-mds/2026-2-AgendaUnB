import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  authorRoleLabel,
  buildRevisionCandidatesPayload,
  buildSharedDrafts,
  sortSharedVersions,
} from './sharedPlans.js';

test('sortSharedVersions prioriza maior número de votos positivos e desempata pela mais recente', () => {
  const v1 = { id: 'v1', number: 1, confirm_count: 1, updated_at: '2026-11-16T10:00:00Z' };
  const v2 = { id: 'v2', number: 2, confirm_count: 3, updated_at: '2026-11-16T09:00:00Z' };
  const v3 = { id: 'v3', number: 3, confirm_count: 3, updated_at: '2026-11-16T12:00:00Z' };
  assert.deepEqual(sortSharedVersions([v1, v2, v3]).map(v => v.id), ['v3', 'v2', 'v1']);
});

test('authorRoleLabel diferencia estudante, professor e admin', () => {
  assert.equal(authorRoleLabel('student'), 'Contribuição de estudante');
  assert.equal(authorRoleLabel('professor'), 'Perfil professor');
  assert.equal(authorRoleLabel('admin'), 'Perfil administrador');
});

test('buildSharedDrafts preserva itens já importados fora da seleção inicial e pré-seleciona atualizados', () => {
  const plan = {
    id: 'ver-2',
    candidates: [
      { id: 'c1', title: 'Prova 1', type: 'prova', suggested_date: '2026-11-20', suggested_time: '14:00:00', ambiguous: false, imported: true, modified_since_import: false },
      { id: 'c2', title: 'Prova 2', type: 'prova', suggested_date: '2026-12-01', suggested_time: '14:00:00', ambiguous: false, imported: false, modified_since_import: true },
    ],
  };
  const drafts = buildSharedDrafts(plan, null, {});
  assert.equal(drafts[0].selected, false);
  assert.equal(drafts[0].imported, true);
  assert.equal(drafts[1].selected, true);
  assert.equal(drafts[1].modifiedSinceImport, true);
});

test('buildRevisionCandidatesPayload valida campos obrigatórios e formata fuso de Brasília', () => {
  const payload = buildRevisionCandidatesPayload([
    { id: 'c1', title: 'Prova 1 atualizada', type: 'prova', date: '2026-12-05', time: '14:00', candidate: { sourcePage: 2, sourceExcerpt: 'P1' } },
    { id: 'c2', title: 'Trabalho final', type: 'trabalho', date: '2026-12-10', time: '', candidate: { sourcePage: 3, sourceExcerpt: 'TF' } },
  ]);
  assert.equal(payload[0].startsAt, '2026-12-05T14:00:00-03:00');
  assert.equal(payload[1].startsAt, null);
  assert.equal(payload[1].suggestedDate, '2026-12-10');
});
