export const PUBLIC_EVENTS_CACHE_KEY = 'agenda_unb_public_events_v1';
export const PUBLIC_EVENTS_FRESH_TTL_MS = 60_000;
export const PUBLIC_EVENTS_MAX_STALE_TTL_MS = 24 * 60 * 60 * 1000;
export const BRASILIA_TIME_ZONE = 'America/Sao_Paulo';

let memoryPublicCache = null;

const brasiliaFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: BRASILIA_TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

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

export function addCivilDays(dateStr, deltaDays) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const parts = dateStr.split('-').map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return dateStr;
  const utc = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2] + deltaDays, 12, 0, 0));
  const yyyy = utc.getUTCFullYear();
  const mm = String(utc.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(utc.getUTCDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export function extractBrasiliaDateTime(isoValue) {
  if (!isoValue) return null;
  const parsed = new Date(isoValue);
  if (Number.isNaN(parsed.getTime())) return null;
  const map = {};
  for (const part of brasiliaFormatter.formatToParts(parsed)) {
    if (part.type !== 'literal') {
      map[part.type] = part.value;
    }
  }
  const hour = map.hour === '24' ? '00' : map.hour;
  return {
    date: `${map.year}-${map.month}-${map.day}`,
    time: `${hour}:${map.minute}`,
  };
}

export function toUiEvent(event, isPersonal = false) {
  const isAllDay = Boolean(event.all_day);
  const startParts = extractBrasiliaDateTime(event.starts_at);
  const endParts = extractBrasiliaDateTime(event.ends_at);
  const dataInicio = isAllDay
    ? (event.start_date || startParts?.date || '')
    : (startParts?.date || event.start_date || '');

  let dataFim = dataInicio;
  if (isAllDay && event.end_date) {
    const inclusiveEnd = addCivilDays(event.end_date, -1);
    dataFim = inclusiveEnd >= dataInicio ? inclusiveEnd : dataInicio;
  } else if (!isAllDay && endParts?.date) {
    dataFim = endParts.date >= dataInicio ? endParts.date : dataInicio;
  }

  const horarioInicio = isAllDay ? 'Dia inteiro' : (startParts?.time || '');
  const horarioFim = !isAllDay && endParts?.time ? endParts.time : '';

  return {
    id: event.id,
    titulo: event.title,
    startsAt: event.starts_at,
    endsAt: event.ends_at || null,
    diaInteiro: isAllDay,
    startDate: event.start_date || (isAllDay ? dataInicio : null),
    endDate: event.end_date || (isAllDay && dataFim ? addCivilDays(dataFim, 1) : null),
    data: dataInicio,
    dataFim,
    horario: horarioInicio,
    horarioFim,
    campus: event.campus || '',
    local: event.location || '',
    area: event.category || 'Acadêmico',
    descricao: event.description || '',
    linkExterno: event.external_url || '',
    organizadorNome: event.organizer_name || '',
    organizadorFoto: event.organizer_avatar || null,
    fonte: event.source || '',
    fonteUrl: event.source_url || '',
    origem: event.origin || null,
    visibilidade: isPersonal ? 'Privado' : 'Público',
    criadoPorMim: isPersonal,
  };
}

export function toApiEvent({
  titulo,
  data,
  dataFim,
  horario,
  horarioFim,
  diaInteiro = false,
  campus,
  local,
  area,
  descricao,
  linkExterno,
}) {
  const cleanTitle = titulo?.trim() || '';
  if (!data) {
    throw new Error('Informe uma data e um horário válidos.');
  }

  const basePayload = {
    title: cleanTitle,
    description: descricao?.trim() || null,
    campus: campus?.trim() || null,
    category: area?.trim() || null,
    location: local?.trim() || null,
    ...(linkExterno?.trim() ? { external_url: linkExterno.trim() } : {}),
  };

  if (diaInteiro) {
    const inclusiveEnd = (dataFim && dataFim.trim()) ? dataFim.trim() : data.trim();
    if (inclusiveEnd < data.trim()) {
      throw new Error('A data de término não pode ser anterior à data de início.');
    }
    return {
      ...basePayload,
      all_day: true,
      start_date: data.trim(),
      end_date: addCivilDays(inclusiveEnd, 1),
    };
  }

  if (!horario || horario === 'Dia inteiro') {
    throw new Error('Informe uma data e um horário válidos.');
  }

  const startsAt = new Date(`${data.trim()}T${horario.trim()}:00-03:00`);
  if (Number.isNaN(startsAt.getTime())) {
    throw new Error('Informe uma data e um horário válidos.');
  }

  const targetEndDate = (dataFim && dataFim.trim()) ? dataFim.trim() : data.trim();
  const hasExplicitEnd = Boolean((horarioFim && horarioFim.trim()) || (dataFim && dataFim.trim() && dataFim.trim() !== data.trim()));
  let endsAtIso = null;

  if (hasExplicitEnd) {
    const effectiveEndTime = (horarioFim && horarioFim.trim()) ? horarioFim.trim() : horario.trim();
    const endsAt = new Date(`${targetEndDate}T${effectiveEndTime}:00-03:00`);
    if (Number.isNaN(endsAt.getTime()) || endsAt.getTime() <= startsAt.getTime()) {
      throw new Error('O horário de término deve ser posterior ao início.');
    }
    endsAtIso = endsAt.toISOString();
  }

  return {
    ...basePayload,
    starts_at: startsAt.toISOString(),
    ...(endsAtIso ? { ends_at: endsAtIso } : {}),
  };
}
