export const DELETE_CONFIRMATION_PHRASE = 'EXCLUIR MINHA CONTA';
export const ACCOUNT_EXPORT_FILENAME = 'agenda-unb-dados.json';
export const LEGAL_DOCUMENTS_UPDATED_EVENT = 'legal-documents-updated';
const PENDING_LEGAL_PREFIX = 'agenda-unb.pending-legal:';
const LEGAL_DOCUMENT_KEYS = ['terms', 'privacy'];
const REVOCABLE_CONSENTS = new Set(['google_agenda']);

function getApiBaseUrl() {
  const configured = typeof import.meta !== 'undefined' && import.meta.env
    ? import.meta.env.VITE_API_URL
    : '';
  return (configured || '/api/v1').replace(/\/$/, '');
}

async function defaultRequest(path, options) {
  const { request } = await import('./api.js');
  return request(path, options);
}

async function defaultGetAccessToken() {
  const { supabase } = await import('./supabase.js');
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error || !session?.access_token) {
    const authError = new Error('Entre na sua conta para realizar esta ação.');
    authError.status = 401;
    throw authError;
  }
  return session.access_token;
}

function getDefaultStorage() {
  if (typeof globalThis === 'undefined' || !('localStorage' in globalThis)) return null;
  try {
    return globalThis.localStorage;
  } catch {
    return null;
  }
}

function parseSingleLegalDocument(entry) {
  if (!entry || typeof entry !== 'object' || Array.isArray(entry)) return null;
  if (typeof entry.currentVersion !== 'string' || !entry.currentVersion.trim()) return null;
  if (typeof entry.pending !== 'boolean') return null;
  if (entry.acceptedVersion !== null && entry.acceptedVersion !== undefined && typeof entry.acceptedVersion !== 'string') {
    return null;
  }
  if (entry.acceptedAt !== null && entry.acceptedAt !== undefined && typeof entry.acceptedAt !== 'string') {
    return null;
  }
  return {
    currentVersion: entry.currentVersion,
    acceptedVersion: entry.acceptedVersion ?? null,
    acceptedAt: entry.acceptedAt ?? null,
    pending: entry.pending,
  };
}

export function parseLegalDocumentsResponse(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const terms = parseSingleLegalDocument(payload.terms);
  const privacy = parseSingleLegalDocument(payload.privacy);
  if (!terms || !privacy) return null;
  return { terms, privacy };
}

export function getPendingLegalDocumentKeys(docs) {
  if (!docs) return [];
  return LEGAL_DOCUMENT_KEYS.filter(key => docs[key]?.pending === true);
}

export function hasPendingLegalDocuments(docs) {
  return getPendingLegalDocumentKeys(docs).length > 0;
}

export function parseConsentsResponse(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload) || !Array.isArray(payload.items)) {
    return { items: [] };
  }
  const items = [];
  for (const item of payload.items) {
    if (!item || typeof item !== 'object') continue;
    if (typeof item.id !== 'string' || !item.id || typeof item.purpose !== 'string' || !item.purpose) continue;
    if (typeof item.active !== 'boolean') continue;
    items.push({
      id: item.id,
      purpose: item.purpose,
      active: item.active,
      grantedAt: typeof item.grantedAt === 'string' ? item.grantedAt : null,
      revokedAt: typeof item.revokedAt === 'string' ? item.revokedAt : null,
      referenceId: typeof item.referenceId === 'string' ? item.referenceId : null,
    });
  }
  return { items };
}

export function isValidDeleteConfirmation(value) {
  return typeof value === 'string' && value === DELETE_CONFIRMATION_PHRASE;
}

export function formatAccountError(error, action = 'generic') {
  const status = error?.status;
  if (status === 401) {
    return 'Sua sessão expirou. Entre novamente na conta para continuar.';
  }
  if (status === 409) {
    if (action === 'legal') {
      return 'Uma nova versão dos documentos foi publicada enquanto você revisava. Atualizamos a página para mostrar o texto vigente.';
    }
    if (action === 'delete') {
      return error?.message || 'O último administrador não pode excluir a própria conta.';
    }
  }
  if (status === 422 && action === 'delete') {
    return `Digite exatamente '${DELETE_CONFIRMATION_PHRASE}' para confirmar a exclusão.`;
  }
  if (status && error?.message) {
    return error.message;
  }
  if (action === 'export') {
    return 'Não foi possível baixar seus dados agora. Verifique sua conexão e tente novamente.';
  }
  if (action === 'delete') {
    return 'Não foi possível concluir a exclusão da conta agora. Tente novamente em instantes.';
  }
  return 'Não foi possível concluir a solicitação. Verifique sua conexão e tente novamente.';
}

export async function hashPendingEmail(email) {
  const normalized = String(email || '').trim().toLowerCase();
  if (!normalized || !globalThis.crypto?.subtle) return '';
  const bytes = new TextEncoder().encode(normalized);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

export async function markPendingSignupLegal(email, storage = getDefaultStorage()) {
  if (!storage) return false;
  const hashed = await hashPendingEmail(email);
  if (!hashed) return false;
  try {
    storage.setItem(`${PENDING_LEGAL_PREFIX}${hashed}`, '1');
    return true;
  } catch {
    return false;
  }
}

export async function clearPendingSignupLegal(email, storage = getDefaultStorage()) {
  if (!storage) return;
  const hashed = await hashPendingEmail(email);
  if (!hashed) return;
  try {
    storage.removeItem(`${PENDING_LEGAL_PREFIX}${hashed}`);
  } catch {
    // Ignore storage removal errors.
  }
}

export async function flushPendingSignupLegal(email, { accountApi = defaultAccountApi, storage = getDefaultStorage(), signal } = {}) {
  if (!storage || !email) return false;
  const hashed = await hashPendingEmail(email);
  if (!hashed) return false;
  const key = `${PENDING_LEGAL_PREFIX}${hashed}`;
  let pendingFlag = null;
  try {
    pendingFlag = storage.getItem(key);
  } catch {
    return false;
  }
  if (!pendingFlag) return false;

  const docs = await accountApi.getLegalDocuments(signal);
  if (!docs) return false;

  const firstSignupKeys = LEGAL_DOCUMENT_KEYS.filter(
    docKey => docs[docKey]?.pending === true && docs[docKey]?.acceptedVersion === null,
  );
  for (const docKey of firstSignupKeys) {
    await accountApi.acceptLegalDocument(docKey, docs[docKey].currentVersion, signal);
  }
  try {
    storage.removeItem(key);
  } catch {
    // Ignore storage removal errors.
  }
  return firstSignupKeys.length > 0;
}

export function notifyLegalDocumentsUpdated() {
  if (typeof window === 'undefined' || typeof CustomEvent !== 'function') return;
  window.dispatchEvent(new CustomEvent(LEGAL_DOCUMENTS_UPDATED_EVENT));
}

export function clearUserLocalData(userId, storage = getDefaultStorage()) {
  if (!storage || !userId) return;
  try {
    storage.removeItem(`agenda-unb.class-catalog-demo:${userId}`);
  } catch {
    // Ignore storage errors.
  }
}

export function createAccountApi({
  requestFn = defaultRequest,
  getAccessToken = defaultGetAccessToken,
  fetchFn = (...args) => globalThis.fetch(...args),
} = {}) {
  const api = {
    async getLegalDocuments(signal) {
      const data = await requestFn('/me/legal-documents', { auth: true, signal });
      return parseLegalDocumentsResponse(data);
    },

    async acceptLegalDocument(document, version, signal) {
      if (!LEGAL_DOCUMENT_KEYS.includes(document)) {
        throw new Error('Documento legal inválido.');
      }
      if (typeof version !== 'string' || !version.trim()) {
        throw new Error('Versão do documento inválida.');
      }
      return requestFn(`/me/legal-acceptances/${document}`, {
        method: 'PUT',
        auth: true,
        signal,
        body: JSON.stringify({ version }),
      });
    },

    async acceptPendingLegalDocuments(docs, signal) {
      const keys = getPendingLegalDocumentKeys(docs);
      for (const docKey of keys) {
        await api.acceptLegalDocument(docKey, docs[docKey].currentVersion, signal);
      }
      return keys;
    },

    async getConsents(signal) {
      const data = await requestFn('/me/consents', { auth: true, signal });
      return parseConsentsResponse(data);
    },

    async revokeConsent(purpose, signal) {
      if (!REVOCABLE_CONSENTS.has(purpose)) {
        throw new Error('Finalidade de consentimento não revogável por este endpoint.');
      }
      return requestFn(`/me/consents/${purpose}`, {
        method: 'DELETE',
        auth: true,
        signal,
      });
    },

    async fetchDataExportBlob(signal) {
      const token = await getAccessToken();
      let response;
      try {
        response = await fetchFn(`${getApiBaseUrl()}/me/data-export`, {
          method: 'GET',
          signal,
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        throw new Error('A API está indisponível. Verifique sua conexão e tente novamente.');
      }

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const detail = typeof errorBody?.detail === 'string'
          ? errorBody.detail
          : 'Não foi possível exportar os dados da conta.';
        const err = new Error(detail);
        err.status = response.status;
        throw err;
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        throw new Error('A API retornou um formato inesperado na exportação de dados.');
      }

      const blob = await response.blob();
      return { blob, filename: ACCOUNT_EXPORT_FILENAME };
    },

    async downloadDataExport(signal) {
      const { blob, filename } = await api.fetchDataExportBlob(signal);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      return filename;
    },

    async deleteAccount(confirmation, signal) {
      if (!isValidDeleteConfirmation(confirmation)) {
        const err = new Error(`Digite exatamente '${DELETE_CONFIRMATION_PHRASE}' para confirmar a exclusão.`);
        err.status = 422;
        throw err;
      }
      return requestFn('/me', {
        method: 'DELETE',
        auth: true,
        signal,
        body: JSON.stringify({ confirmation }),
      });
    },
  };
  return api;
}

const defaultAccountApi = createAccountApi();
export const accountApi = defaultAccountApi;
