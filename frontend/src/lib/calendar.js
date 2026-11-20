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
