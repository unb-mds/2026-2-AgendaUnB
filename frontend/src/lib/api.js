import { supabase } from './supabase';
import {
  clearPublicCache,
  getCachedPublic,
  isCachedPublicFresh,
  setCachedPublic,
  toApiEvent,
  toUiEvent,
} from './publicEventsCache';

const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api/v1')
  .replace(/\/$/, '');
const COLD_START_FALLBACK_DELAY_MS = 1800;

let inFlightPublicPromise = null;

function canUseSupabaseFallback() {
  const url = import.meta.env?.VITE_SUPABASE_URL;
  return Boolean(
    url
      && !url.includes('example.supabase.co')
      && !url.includes('fixture.supabase.co')
      && typeof supabase?.rpc === 'function',
  );
}

async function fetchPublicFromSupabaseFallback() {
  if (!canUseSupabaseFallback()) return null;
  try {
    const { data, error } = await supabase.rpc('listar_eventos_publicos');
    if (error || !Array.isArray(data)) return null;
    return data;
  } catch {
    return null;
  }
}

async function fetchPublicFromBackend(filters = {}) {
  const query = new URLSearchParams();
  if (filters.campus) query.set('campus', filters.campus);
  if (filters.category) query.set('category', filters.category);
  if (filters.startDate) query.set('startDate', filters.startDate);
  if (filters.endDate) query.set('endDate', filters.endDate);
  if (filters.search) query.set('q', filters.search);
  const pageSize = 100;
  const events = new Map();
  query.set('limit', String(pageSize));
  for (let offset = 0; ; offset += pageSize) {
    query.set('offset', String(offset));
    const page = await request(`/events?${query.toString()}`);
    for (const event of page) events.set(event.id, event);
    if (page.length < pageSize) return [...events.values()];
  }
}

async function loadUnfilteredPublicWithFallback() {
  const backendPromise = fetchPublicFromBackend({});
  if (!canUseSupabaseFallback()) {
    return setCachedPublic(await backendPromise);
  }

  return new Promise((resolve, reject) => {
    let settled = false;
    let fallbackTimer = null;

    const finishResolve = (events) => {
      if (settled) return;
      settled = true;
      clearTimeout(fallbackTimer);
      resolve(setCachedPublic(events));
    };

    const finishReject = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(fallbackTimer);
      reject(error);
    };

    backendPromise.then(
      (events) => finishResolve(events),
      async (backendError) => {
        if (settled) return;
        const fallbackEvents = await fetchPublicFromSupabaseFallback();
        if (fallbackEvents !== null) {
          finishResolve(fallbackEvents);
        } else {
          finishReject(backendError);
        }
      },
    );

    fallbackTimer = setTimeout(async () => {
      if (settled) return;
      const fallbackEvents = await fetchPublicFromSupabaseFallback();
      if (settled || fallbackEvents === null) return;
      backendPromise.then((fresh) => setCachedPublic(fresh)).catch(() => null);
      finishResolve(fallbackEvents);
    }, COLD_START_FALLBACK_DELAY_MS);
  });
}

async function request(path, { auth = false, ...options } = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');

  if (auth) {
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error || !session?.access_token) {
      throw new Error('Entre na sua conta para realizar esta ação.');
    }
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error('A API está indisponível. Verifique sua conexão e tente novamente.');
  }
  if (response.status === 204) return null;

  const result = await response.json().catch(() => null);
  if (response.ok && result === null) {
    throw new Error('A API retornou uma resposta inválida. Tente novamente mais tarde.');
  }
  if (!response.ok) {
    let detail = result?.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((err) => `${err.loc?.slice(-1)?.[0] || 'campo'}: ${err.msg}`).join('; ');
    } else if (typeof detail !== 'string') {
      detail = 'Não foi possível concluir a solicitação.';
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return result;
}

// Exported for feature clients that share authentication and error handling.
export { request, toApiEvent, toUiEvent };

export const eventsApi = {
  suggest: (event) => request('/suggestions', {
    method: 'POST', auth: true, body: JSON.stringify(event),
  }),
  getCachedPublic: () => getCachedPublic(),
  clearPublicCache: () => clearPublicCache(),
  prefetchPublic: () => {
    if (isCachedPublicFresh()) {
      return Promise.resolve(getCachedPublic());
    }
    return eventsApi.listPublic().catch(() => null);
  },
  listPublic: async (filters = {}) => {
    const isUnfiltered = !filters.campus && !filters.category && !filters.startDate && !filters.endDate && !filters.search;
    if (!isUnfiltered) {
      return fetchPublicFromBackend(filters);
    }
    if (!inFlightPublicPromise) {
      inFlightPublicPromise = loadUnfilteredPublicWithFallback().finally(() => {
        inFlightPublicPromise = null;
      });
    }
    return inFlightPublicPromise;
  },
  getPublic: (id) => request(`/events/${encodeURIComponent(id)}`),
  registerOutboundClick: async (eventId, clickId) => {
    const result = await request(`/events/${encodeURIComponent(eventId)}/outbound-clicks`, {
      method: 'POST',
      body: JSON.stringify({ click_id: clickId }),
    });
    if (result?.incremented) {
      clearPublicCache();
    }
    return result;
  },
  listCategories: () => request('/categories'),
  createCategory: (payload) => request('/categories', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  }),
  deleteCategory: (id) => request(`/categories/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    auth: true,
  }),
  listPersonal: () => request('/me/events', { auth: true }),
  listOwnPublishedIds: () => request('/me/published-event-ids', { auth: true }),
  listSaved: () => request('/me/saved-events', { auth: true }),
  savedStatus: (id) => request(`/me/saved-events/${encodeURIComponent(id)}`, { auth: true }),
  savePublic: (id) => request(`/me/saved-events/${encodeURIComponent(id)}`, { auth: true, method: 'PUT' }),
  removeSaved: (id) => request(`/me/saved-events/${encodeURIComponent(id)}`, { auth: true, method: 'DELETE' }),
  getPersonal: (id) => request(`/me/events/${encodeURIComponent(id)}`, { auth: true }),
  createPublic: async (event) => {
    const created = await request('/events', {
      method: 'POST',
      auth: true,
      body: JSON.stringify(event),
    });
    clearPublicCache();
    return created;
  },
  updatePublic: async (id, event) => {
    const updated = await request(`/events/${encodeURIComponent(id)}`, {
      method: 'PUT',
      auth: true,
      body: JSON.stringify(event),
    });
    clearPublicCache();
    return updated;
  },
  deletePublic: async (id) => {
    const result = await request(`/events/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      auth: true,
    });
    clearPublicCache();
    return result;
  },
  createPersonal: (event) => request('/me/events', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(event),
  }),
  updatePersonal: (id, event) => request(`/me/events/${encodeURIComponent(id)}`, {
    method: 'PUT',
    auth: true,
    body: JSON.stringify(event),
  }),
  deletePersonal: (id) => request(`/me/events/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    auth: true,
  }),
};
