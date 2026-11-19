import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ACCOUNT_EXPORT_FILENAME,
  DELETE_CONFIRMATION_PHRASE,
  createAccountApi,
  flushPendingSignupLegal,
  formatAccountError,
  getPendingLegalDocumentKeys,
  hasPendingLegalDocuments,
  hashPendingEmail,
  isValidDeleteConfirmation,
  markPendingSignupLegal,
  parseConsentsResponse,
  parseLegalDocumentsResponse,
} from './accountApi.js';

function createMemoryStorage() {
  const store = new Map();
  return {
    getItem: key => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: key => store.delete(key),
    dump: () => [...store.entries()],
  };
}

test('parseLegalDocumentsResponse accepts valid object and rejects arrays or malformed mocks', () => {
  const valid = {
    terms: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
    privacy: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-18', acceptedAt: '2026-11-18T12:00:00Z', pending: false },
  };
  assert.deepEqual(parseLegalDocumentsResponse(valid), valid);
  assert.equal(parseLegalDocumentsResponse([]), null);
  assert.equal(parseLegalDocumentsResponse(null), null);
  assert.equal(parseLegalDocumentsResponse({ terms: valid.terms }), null);
  assert.equal(parseLegalDocumentsResponse({
    terms: { ...valid.terms, pending: 'yes' },
    privacy: valid.privacy,
  }), null);
  assert.equal(parseLegalDocumentsResponse({
    terms: { ...valid.terms, currentVersion: '' },
    privacy: valid.privacy,
  }), null);
});

test('hasPendingLegalDocuments and getPendingLegalDocumentKeys identify pending documents', () => {
  assert.equal(hasPendingLegalDocuments(null), false);
  assert.deepEqual(getPendingLegalDocumentKeys(null), []);
  const docs = {
    terms: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
    privacy: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-18', acceptedAt: '2026-11-18T12:00:00Z', pending: false },
  };
  assert.equal(hasPendingLegalDocuments(docs), true);
  assert.deepEqual(getPendingLegalDocumentKeys(docs), ['terms']);
  assert.equal(hasPendingLegalDocuments({
    terms: { ...docs.terms, pending: false },
    privacy: docs.privacy,
  }), false);
});

test('parseConsentsResponse normalizes active and revoked consents safely', () => {
  const parsed = parseConsentsResponse({
    items: [
      { id: 'c1', purpose: 'google_agenda', active: true, grantedAt: '2026-11-18T10:00:00Z', revokedAt: null, referenceId: 'u1' },
      { id: 'c2', purpose: 'google_agenda', active: false, grantedAt: '2026-11-10T10:00:00Z', revokedAt: '2026-11-12T10:00:00Z', referenceId: null },
    ],
  });
  assert.equal(parsed.items.length, 2);
  assert.equal(parsed.items[0].active, true);
  assert.equal(parsed.items[1].revokedAt, '2026-11-12T10:00:00Z');
  assert.deepEqual(parseConsentsResponse(null), { items: [] });
  assert.deepEqual(parseConsentsResponse([]), { items: [] });
  assert.deepEqual(parseConsentsResponse({ items: [{ purpose: '' }] }), { items: [] });
});

test('isValidDeleteConfirmation requires exact confirmation phrase', () => {
  assert.equal(DELETE_CONFIRMATION_PHRASE, 'EXCLUIR MINHA CONTA');
  assert.equal(isValidDeleteConfirmation('EXCLUIR MINHA CONTA'), true);
  assert.equal(isValidDeleteConfirmation('excluir minha conta'), false);
  assert.equal(isValidDeleteConfirmation(' EXCLUIR MINHA CONTA '), false);
  assert.equal(isValidDeleteConfirmation('EXCLUIR'), false);
  assert.equal(isValidDeleteConfirmation(''), false);
  assert.equal(isValidDeleteConfirmation(null), false);
});

test('pending signup legal marker hashes email and only flushes unaccepted documents', async () => {
  const storage = createMemoryStorage();
  const hashA = await hashPendingEmail('Pessoa@UnB.BR ');
  const hashB = await hashPendingEmail('pessoa@unb.br');
  assert.equal(hashA, hashB);
  assert.equal(hashA.length, 64);

  const stored = await markPendingSignupLegal('Pessoa@UnB.BR', storage);
  assert.equal(stored, true);
  assert.equal(storage.dump().some(([k, v]) => k.includes('pessoa') || v.includes('pessoa')), false);

  const acceptedCalls = [];
  const api = createAccountApi({
    requestFn: async (path, options) => {
      if (path === '/me/legal-documents') {
        return {
          terms: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
          privacy: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-11', acceptedAt: '2026-11-11T10:00:00Z', pending: true },
        };
      }
      acceptedCalls.push({ path, method: options.method, body: JSON.parse(options.body) });
      return null;
    },
  });

  await flushPendingSignupLegal('pessoa@unb.br', { accountApi: api, storage });
  // Only `terms` had acceptedVersion === null; `privacy` had a prior accepted version (must be reviewed via gate).
  assert.deepEqual(acceptedCalls, [
    { path: '/me/legal-acceptances/terms', method: 'PUT', body: { version: '2026-11-18' } },
  ]);
  assert.equal(storage.dump().length, 0);
});

test('createAccountApi calls expected endpoints and formats errors accurately', async () => {
  const calls = [];
  const api = createAccountApi({
    requestFn: async (path, options) => {
      calls.push({ path, ...options });
      if (path === '/me/legal-documents') {
        return {
          terms: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
          privacy: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
        };
      }
      return null;
    },
    getAccessToken: async () => 'token-123',
    fetchFn: async (url, options) => {
      calls.push({ url, ...options });
      return new Response(JSON.stringify({ exportedAt: '2026-11-18T00:00:00Z', profile: { id: 'u1' } }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    },
  });

  const docs = await api.getLegalDocuments();
  await api.acceptPendingLegalDocuments(docs);
  await api.revokeConsent('google_agenda');
  await api.deleteAccount('EXCLUIR MINHA CONTA');
  const exportFile = await api.fetchDataExportBlob();

  assert.equal(exportFile.filename, ACCOUNT_EXPORT_FILENAME);
  assert.equal(exportFile.blob.type, 'application/json');
  assert.equal(JSON.parse(await exportFile.blob.text()).profile.id, 'u1');

  assert.deepEqual(calls.map(c => c.path || c.url), [
    '/me/legal-documents',
    '/me/legal-acceptances/terms',
    '/me/legal-acceptances/privacy',
    '/me/consents/google_agenda',
    '/me',
    '/api/v1/me/data-export',
  ]);
  assert.equal(calls[5].headers.Authorization, 'Bearer token-123');

  await assert.rejects(() => api.acceptLegalDocument('other', '2026-11-18'));
  await assert.rejects(() => api.revokeConsent('envio_texto_ia'));
  await assert.rejects(() => api.deleteAccount('errado'));

  assert.match(formatAccountError(Object.assign(new Error('stale'), { status: 409 }), 'legal'), /nova versão/i);
  assert.equal(formatAccountError(Object.assign(new Error('O último administrador não pode excluir a própria conta.'), { status: 409 }), 'delete'), 'O último administrador não pode excluir a própria conta.');
  assert.match(formatAccountError(Object.assign(new Error('bad'), { status: 422 }), 'delete'), /EXCLUIR MINHA CONTA/);
  assert.match(formatAccountError(Object.assign(new Error('unauth'), { status: 401 }), 'export'), /sessão/i);
});

test('fetchDataExportBlob surfaces server JSON error details cleanly', async () => {
  const api = createAccountApi({
    getAccessToken: async () => 'token-123',
    fetchFn: async () => new Response(JSON.stringify({ detail: 'Sessão inválida ou expirada' }), {
      status: 401,
      headers: { 'content-type': 'application/json' },
    }),
  });
  await assert.rejects(() => api.fetchDataExportBlob(), err => err.status === 401 && err.message === 'Sessão inválida ou expirada');
});
