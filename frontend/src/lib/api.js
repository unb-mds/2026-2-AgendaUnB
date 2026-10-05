import { supabase } from './supabase';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1')
  .replace(/\/$/, '');

async function request(path, { auth = false, ...options } = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set('Content-Type', 'application/json');

  if (auth) {
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error || !session?.access_token) {
      throw new Error('Entre na sua conta para realizar esta ação.');
    }
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 204) return null;

  const result = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = result?.detail;
    throw new Error(typeof detail === 'string' ? detail : 'Não foi possível concluir a solicitação.');
  }
  return result;
}

export const eventsApi = {
  listPublic: (filters = {}) => {
    const query = new URLSearchParams();
    if (filters.campus) query.set('campus', filters.campus);
    if (filters.category) query.set('category', filters.category);
    if (filters.search) query.set('q', filters.search);
    const encodedQuery = query.toString();
    const suffix = encodedQuery ? `?${encodedQuery}` : '';
    return request(`/events${suffix}`);
  },
  getPublic: (id) => request(`/events/${encodeURIComponent(id)}`),
  listPersonal: () => request('/me/events', { auth: true }),
  getPersonal: (id) => request(`/me/events/${encodeURIComponent(id)}`, { auth: true }),
  createPublic: (event) => request('/events', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(event),
  }),
  deletePublic: (id) => request(`/events/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    auth: true,
  }),
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

export function toUiEvent(event, isPersonal = false) {
  const startsAt = new Date(event.starts_at);
  const pad = (value) => String(value).padStart(2, '0');
  return {
    id: event.id,
    titulo: event.title,
    data: `${startsAt.getFullYear()}-${pad(startsAt.getMonth() + 1)}-${pad(startsAt.getDate())}`,
    horario: `${pad(startsAt.getHours())}:${pad(startsAt.getMinutes())}`,
    campus: event.campus || '',
    local: event.location || '',
    area: event.category || 'Acadêmico',
    descricao: event.description || '',
    linkExterno: event.external_url || '',
    organizadorNome: event.organizer_name || '',
    organizadorFoto: event.organizer_avatar || null,
    visibilidade: isPersonal ? 'Privado' : 'Público',
    criadoPorMim: isPersonal,
  };
}

export function toApiEvent({ titulo, data, horario, campus, local, area, descricao, linkExterno }) {
  const startsAt = new Date(`${data}T${horario}:00`);
  if (Number.isNaN(startsAt.getTime())) {
    throw new Error('Informe uma data e um horário válidos.');
  }
  return {
    title: titulo.trim(),
    description: descricao.trim() || null,
    starts_at: startsAt.toISOString(),
    campus: campus || null,
    category: area || null,
    location: local.trim() || null,
    ...(linkExterno.trim() ? { external_url: linkExterno.trim() } : {}),
  };
}
