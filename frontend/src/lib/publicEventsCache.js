export const PUBLIC_EVENTS_CACHE_KEY = 'agenda_unb_public_events_v1';
export const PUBLIC_EVENTS_FRESH_TTL_MS = 60_000;
export const PUBLIC_EVENTS_MAX_STALE_TTL_MS = 24 * 60 * 60 * 1000;

let memoryPublicCache = null;

function defaultStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

function isValidEntry(entry, now) {
  return Boolean(
    entry
      && Array.isArray(entry.events)
      && typeof entry.timestamp === 'number'
      && Number.isFinite(entry.timestamp)
      && now - entry.timestamp <= PUBLIC_EVENTS_MAX_STALE_TTL_MS,
  );
}

function readCacheEntry(now = Date.now(), storage = defaultStorage()) {
  const defaultStore = defaultStorage();
  if (storage === defaultStore && memoryPublicCache) {
    if (isValidEntry(memoryPublicCache, now)) {
      return memoryPublicCache;
    }
    memoryPublicCache = null;
  }

  if (!storage || typeof storage.getItem !== 'function') {
    return null;
  }

  try {
    const raw = storage.getItem(PUBLIC_EVENTS_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!isValidEntry(parsed, now)) {
      storage.removeItem?.(PUBLIC_EVENTS_CACHE_KEY);
      return null;
    }
    if (storage === defaultStore) {
      memoryPublicCache = parsed;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function getCachedPublic(now = Date.now(), storage = defaultStorage()) {
  return readCacheEntry(now, storage)?.events ?? null;
}

export function isCachedPublicFresh(now = Date.now(), storage = defaultStorage()) {
  const entry = readCacheEntry(now, storage);
  return Boolean(entry && now - entry.timestamp <= PUBLIC_EVENTS_FRESH_TTL_MS);
}

export function setCachedPublic(events, now = Date.now(), storage = defaultStorage()) {
  if (!Array.isArray(events)) return events;
  const entry = { events, timestamp: now };
  if (storage === defaultStorage()) {
    memoryPublicCache = entry;
  }
  try {
    storage?.setItem?.(PUBLIC_EVENTS_CACHE_KEY, JSON.stringify(entry));
  } catch {
    // Ignore storage quota or private browsing errors; in-memory cache remains active.
  }
  return events;
}

export function clearPublicCache(storage = defaultStorage()) {
  if (storage === defaultStorage()) {
    memoryPublicCache = null;
  }
  try {
    storage?.removeItem?.(PUBLIC_EVENTS_CACHE_KEY);
  } catch {
    // Ignore storage errors.
  }
}

export function toUiEvent(event, isPersonal = false) {
  const startsAt = new Date(event.starts_at);
  const pad = (value) => String(value).padStart(2, '0');
  return {
    id: event.id,
    titulo: event.title,
    startsAt: event.starts_at,
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
    description: descricao?.trim() || null,
    starts_at: startsAt.toISOString(),
    campus: campus?.trim() || null,
    category: area?.trim() || null,
    location: local?.trim() || null,
    ...(linkExterno?.trim() ? { external_url: linkExterno.trim() } : {}),
  };
}
