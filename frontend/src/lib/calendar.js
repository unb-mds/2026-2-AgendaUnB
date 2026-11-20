import { addCivilDays } from './publicEventsCache.js';

const MAX_SPAN_DAYS = 60;

// Datas civis locais: mantém a mesma convenção de fuso usada por toUiEvent.
export function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function calendarDays(reference, mode) {
  const start = new Date(reference.getFullYear(), reference.getMonth(), mode === 'month' ? 1 : reference.getDate(), 12);
  const monthEnd = new Date(start.getFullYear(), start.getMonth() + 1, 0, 12);
  const count = mode === 'month' ? Math.ceil((start.getDay() + monthEnd.getDate()) / 7) * 7 : 7;
  start.setDate(start.getDate() - start.getDay());
  return Array.from({ length: count }, (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index, 12));
}

export function movePeriod(reference, mode, direction) {
  return mode === 'month'
    ? new Date(reference.getFullYear(), reference.getMonth() + direction, 1, 12)
    : new Date(reference.getFullYear(), reference.getMonth(), reference.getDate() + direction * 7, 12);
}

/**
 * Retorna todas as datas civis (YYYY-MM-DD) ocupadas por um evento,
 * respeitando fim exclusivo em eventos de dia inteiro (ADR-011) e
 * intervalos de vários dias em eventos com horário.
 */
export function eventDateKeys(event) {
  if (!event?.data) return [];
  const start = event.data;
  let inclusiveEnd = event.dataFim || start;

  if (event.diaInteiro && event.endDate) {
    const fromExclusive = addCivilDays(event.endDate, -1);
    if (fromExclusive >= start) {
      inclusiveEnd = fromExclusive;
    }
  }

  if (!inclusiveEnd || inclusiveEnd <= start) {
    return [start];
  }

  const keys = [];
  let cursor = start;
  for (let step = 0; step < MAX_SPAN_DAYS && cursor <= inclusiveEnd; step += 1) {
    keys.push(cursor);
    if (cursor === inclusiveEnd) break;
    cursor = addCivilDays(cursor, 1);
  }
  return keys;
}

export function formatShortCivilDate(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  const dateObj = new Date(`${dateStr}T12:00:00`);
  if (Number.isNaN(dateObj.getTime())) return dateStr;
  const month = dateObj.toLocaleString('pt-BR', { month: 'short' }).replace('.', '');
  const monthCap = month.charAt(0).toUpperCase() + month.slice(1);
  return `${parts[2]} ${monthCap}`;
}

export function formatEventSchedule(event) {
  if (!event?.data) return '';
  const startLabel = formatShortCivilDate(event.data);
  const endDate = event.dataFim && event.dataFim > event.data ? event.dataFim : '';
  const endLabel = endDate ? formatShortCivilDate(endDate) : '';

  if (event.diaInteiro) {
    return endLabel
      ? `${startLabel} a ${endLabel} · Dia inteiro`
      : `${startLabel} · Dia inteiro`;
  }

  const startTime = event.horario || '';
  const endTime = event.horarioFim || '';

  if (endLabel) {
    return `${startLabel}${startTime ? ` (${startTime})` : ''} até ${endLabel}${endTime ? ` (${endTime})` : ''}`;
  }
  if (startTime && endTime && endTime !== startTime) {
    return `${startLabel} · ${startTime} – ${endTime}`;
  }
  return startTime ? `${startLabel} · ${startTime}` : startLabel;
}

/**
 * Determina se um evento (toUiEvent) já é considerado passado em relação ao instante atual
 * (ou a um instante de referência), respeitando endsAt/startsAt e dias civis em America/Sao_Paulo.
 */
export function isPastUiEvent(event, now = new Date()) {
  if (!event) return false;
  const nowDate = now instanceof Date ? now : new Date(now);
  const nowMs = nowDate.getTime();
  if (Number.isNaN(nowMs)) return false;

  if (event.endsAt) {
    const endMs = new Date(event.endsAt).getTime();
    if (!Number.isNaN(endMs)) {
      return endMs < nowMs;
    }
  }

  if (event.diaInteiro && event.endDate) {
    const exclusiveEndMs = new Date(`${event.endDate}T00:00:00-03:00`).getTime();
    if (!Number.isNaN(exclusiveEndMs)) {
      return exclusiveEndMs < nowMs;
    }
  }

  if (event.startsAt) {
    const startMs = new Date(event.startsAt).getTime();
    if (!Number.isNaN(startMs)) {
      return startMs < nowMs;
    }
  }

  if (event.data) {
    const targetDate = event.dataFim || event.data;
    const targetTime = !event.diaInteiro && (event.horarioFim || event.horario)
      ? `${event.horarioFim || event.horario}:00`
      : '23:59:59';
    const fallbackMs = new Date(`${targetDate}T${targetTime}-03:00`).getTime();
    if (!Number.isNaN(fallbackMs)) {
      return fallbackMs < nowMs;
    }
  }

  return false;
}

/**
 * Separa os eventos de "Meus Eventos" em:
 * - upcomingEvents: compromissos privados e eventos públicos salvos ativos/futuros
 * - pastSavedPublicEvents: histórico separado de eventos públicos salvos já encerrados
 * - pastPersonalEvents: histórico separado de compromissos privados já encerrados
 */
export function splitMyEventsByHistory(events, now = new Date()) {
  const upcomingEvents = [];
  const pastSavedPublicEvents = [];
  const pastPersonalEvents = [];

  for (const event of Array.isArray(events) ? events : []) {
    if (!isPastUiEvent(event, now)) {
      upcomingEvents.push(event);
      continue;
    }
    if (event.salvoNaAgenda) {
      pastSavedPublicEvents.push(event);
    } else if (event.criadoPorMim || event.visibilidade === 'Privado') {
      pastPersonalEvents.push(event);
    }
  }

  const descComparator = (a, b) => `${b.data || ''}T${b.horario || ''}`.localeCompare(`${a.data || ''}T${a.horario || ''}`);
  pastSavedPublicEvents.sort(descComparator);
  pastPersonalEvents.sort(descComparator);

  return {
    upcomingEvents,
    pastSavedPublicEvents,
    pastPersonalEvents,
  };
}
