import { addCivilDays, BRASILIA_TIME_ZONE } from './publicEventsCache.js';

const MAX_LINE_OCTETS = 75;
const DEFAULT_DURATION_MS = 60 * 60 * 1000;
const encoder = new TextEncoder();

const brasiliaDateTimeParts = new Intl.DateTimeFormat('en-CA', {
  timeZone: BRASILIA_TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23',
});

export function escapeIcsText(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/\\/g, '\\\\')
    .replace(/\r\n|\r|\n/g, '\\n')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,');
}

export function foldIcsLine(line) {
  const text = String(line ?? '');
  if (encoder.encode(text).length <= MAX_LINE_OCTETS) {
    return text;
  }
  const chunks = [];
  let current = '';
  let currentBytes = 0;
  let maxBytes = MAX_LINE_OCTETS;

  for (const char of text) {
    const charBytes = encoder.encode(char).length;
    if (current && currentBytes + charBytes > maxBytes) {
      chunks.push(current);
      current = ` ${char}`;
      currentBytes = 1 + charBytes;
      maxBytes = MAX_LINE_OCTETS;
    } else {
      current += char;
      currentBytes += charBytes;
    }
  }
  if (current) {
    chunks.push(current);
  }
  return chunks.join('\r\n');
}

export function formatUtcTimestamp(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error('Data inválida para DTSTAMP.');
  }
  const pad = (n) => String(n).padStart(2, '0');
  return (
    `${date.getUTCFullYear()}`
    + `${pad(date.getUTCMonth() + 1)}`
    + `${pad(date.getUTCDate())}T`
    + `${pad(date.getUTCHours())}`
    + `${pad(date.getUTCMinutes())}`
    + `${pad(date.getUTCSeconds())}Z`
  );
}

export function formatBrasiliaDateTime(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error('Instante inválido para conversão em America/Sao_Paulo.');
  }
  const map = {};
  for (const part of brasiliaDateTimeParts.formatToParts(date)) {
    if (part.type !== 'literal') {
      map[part.type] = part.value;
    }
  }
  const hour = map.hour === '24' ? '00' : map.hour;
  return `${map.year}${map.month}${map.day}T${hour}${map.minute}${map.second}`;
}

function cleanCivilDate(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const trimmed = dateStr.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return '';
  return trimmed;
}

function resolveEventKind(event) {
  if (event?.kind === 'personal' || event?.kind === 'saved') return event.kind;
  return event?.criadoPorMim ? 'personal' : 'saved';
}

export function buildIcsEventUid(event) {
  const id = String(event?.id ?? '').trim();
  if (!id) throw new Error('Evento sem identificador para gerar UID ICS.');
  const kind = resolveEventKind(event);
  return `${kind}-${id}@agendaunb.unb.br`;
}

function resolveLocation(event) {
  const local = (event?.local ?? event?.location ?? '').trim();
  const campus = (event?.campus ?? '').trim();
  if (local && campus && !local.toLowerCase().includes(campus.toLowerCase())) {
    return `${local} - ${campus}`;
  }
  return local || campus || '';
}

function resolveEventTiming(event) {
  const isAllDay = Boolean(event?.diaInteiro || event?.all_day);
  if (isAllDay) {
    const startCivil = cleanCivilDate(event?.startDate || event?.start_date || event?.data);
    if (!startCivil) {
      throw new Error('Evento de dia inteiro sem data inicial.');
    }
    let exclusiveEnd = cleanCivilDate(event?.endDate || event?.end_date);
    if (!exclusiveEnd || exclusiveEnd <= startCivil) {
      const inclusiveEnd = cleanCivilDate(event?.dataFim);
      exclusiveEnd = inclusiveEnd && inclusiveEnd >= startCivil
        ? addCivilDays(inclusiveEnd, 1)
        : addCivilDays(startCivil, 1);
    }
    return {
      allDay: true,
      dtStartLine: `DTSTART;VALUE=DATE:${startCivil.replace(/-/g, '')}`,
      dtEndLine: `DTEND;VALUE=DATE:${exclusiveEnd.replace(/-/g, '')}`,
    };
  }

  let startInstant = event?.startsAt || event?.starts_at;
  if (!startInstant && event?.data && event?.horario && event.horario !== 'Dia inteiro') {
    startInstant = `${event.data}T${event.horario}:00-03:00`;
  }
  const startDate = new Date(startInstant);
  if (Number.isNaN(startDate.getTime())) {
    throw new Error('Evento sem horário de início válido.');
  }

  let endInstant = event?.endsAt || event?.ends_at;
  if (!endInstant && event?.horarioFim && (event?.dataFim || event?.data)) {
    endInstant = `${event.dataFim || event.data}T${event.horarioFim}:00-03:00`;
  }
  let endDate = endInstant ? new Date(endInstant) : null;
  if (!endDate || Number.isNaN(endDate.getTime()) || endDate.getTime() <= startDate.getTime()) {
    endDate = new Date(startDate.getTime() + DEFAULT_DURATION_MS);
  }

  return {
    allDay: false,
    dtStartLine: `DTSTART;TZID=${BRASILIA_TIME_ZONE}:${formatBrasiliaDateTime(startDate)}`,
    dtEndLine: `DTEND;TZID=${BRASILIA_TIME_ZONE}:${formatBrasiliaDateTime(endDate)}`,
  };
}

export function buildIcsCalendar(events, { includeDescription = true, now = new Date() } = {}) {
  if (!Array.isArray(events) || events.length === 0) {
    throw new Error('Selecione ao menos um evento para gerar o arquivo ICS.');
  }

  const dtStamp = formatUtcTimestamp(now);
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Universidade de Brasilia//Agenda UnB//PT-BR',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'X-WR-CALNAME:Agenda UnB',
    `X-WR-TIMEZONE:${BRASILIA_TIME_ZONE}`,
    'BEGIN:VTIMEZONE',
    `TZID:${BRASILIA_TIME_ZONE}`,
    `X-LIC-LOCATION:${BRASILIA_TIME_ZONE}`,
    'BEGIN:STANDARD',
    'TZOFFSETFROM:-0300',
    'TZOFFSETTO:-0300',
    'TZNAME:-03',
    'DTSTART:19700101T000000',
    'END:STANDARD',
    'END:VTIMEZONE',
  ];

  for (const event of events) {
    const title = (event?.titulo ?? event?.title ?? '').trim();
    if (!title) {
      throw new Error('Evento sem título para exportação ICS.');
    }
    const uid = buildIcsEventUid(event);
    const { dtStartLine, dtEndLine } = resolveEventTiming(event);
    const location = resolveLocation(event);
    const description = includeDescription
      ? (event?.descricao ?? event?.description ?? '').trim()
      : '';
    const category = (event?.area ?? event?.category ?? '').trim();

    lines.push('BEGIN:VEVENT');
    lines.push(`UID:${uid}`);
    lines.push(`DTSTAMP:${dtStamp}`);
    lines.push(dtStartLine);
    lines.push(dtEndLine);
    lines.push(`SUMMARY:${escapeIcsText(title)}`);
    if (description) {
      lines.push(`DESCRIPTION:${escapeIcsText(description)}`);
    }
    if (location) {
      lines.push(`LOCATION:${escapeIcsText(location)}`);
    }
    if (category) {
      lines.push(`CATEGORIES:${escapeIcsText(category)}`);
    }
    lines.push('END:VEVENT');
  }

  lines.push('END:VCALENDAR');
  return `${lines.map(foldIcsLine).join('\r\n')}\r\n`;
}

export function downloadIcsCalendar(events, { includeDescription = true, filename = 'agenda-unb.ics', now = new Date() } = {}) {
  const content = buildIcsCalendar(events, { includeDescription, now });
  const blob = new Blob([content], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  return content;
}
