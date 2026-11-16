import { classStartOnDate } from './classSchedule.js';

// Local editor model, not an API payload.
export const BRASILIA_UTC_OFFSET = '-03:00';

function formatInBrasilia(isoInstant) {
  if (!isoInstant) return null;
  const parsed = new Date(isoInstant);
  if (Number.isNaN(parsed.getTime())) return null;
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/Sao_Paulo',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).formatToParts(parsed).map(part => [part.type, part.value])
  );
  const hour = parts.hour === '24' ? '00' : parts.hour;
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    time: `${hour}:${parts.minute}:${parts.second}`,
  };
}

export function createReviewDraft(items) {
  if (!Array.isArray(items)) throw new Error('Lista de avaliações inválida.');
  const ids = new Set();
  return items.map(item => {
    if (!item || typeof item.id !== 'string' || !item.id.trim() || ids.has(item.id)) {
      throw new Error('Cada avaliação precisa de um identificador único.');
    }
    ids.add(item.id);
    const string = key => typeof item[key] === 'string' ? item[key] : '';
    return { id: item.id, title: string('title'), type: string('type'), date: string('date'),
      time: string('time'), decision: 'pending' };
  });
}

export function createCandidateReviewDraft(candidates, classSchedule) {
  return createReviewDraft(candidates).map((draft, index) => {
    const candidate = candidates[index];
    const hasExplicitZone = /(?:Z|[+-]\d{2}:\d{2})$/.test(candidate.startsAt || '');
    const brasilia = hasExplicitZone ? formatInBrasilia(candidate.startsAt) : null;
    const time = candidate.suggestedTime ?? brasilia?.time ?? '';
    return withClassTime({ ...draft, type: draft.type.toLowerCase(),
      date: candidate.suggestedDate ?? brasilia?.date ?? '',
      time,
      timeSource: time ? 'plan' : null,
      dateNeedsReview: candidate.ambiguousFields?.some(field => ['data', 'date'].includes(field)),
      status: candidate.status, versionId: candidate.versionId,
      editable: candidate.status === 'pendente' }, classSchedule);
  });
}

function withClassTime(item, classSchedule) {
  if (item.timeSource === 'plan' || item.timeSource === 'manual') return item;
  const canSuggest = item.editable === true && item.type === 'prova' && !item.dateNeedsReview;
  const time = canSuggest ? classStartOnDate(classSchedule, item.date) : '';
  return { ...item, time, timeSource: time ? 'catalog' : null };
}

export function updateCandidateReviewItem(item, patch, classSchedule) {
  const updated = { ...item, ...patch };
  if (!('timeSource' in item)) return updated;
  if ('time' in patch) return { ...updated, timeSource: 'manual' };
  if (updated.date !== item.date) updated.dateNeedsReview = false;
  if (updated.date !== item.date || updated.type !== item.type) return withClassTime(updated, classSchedule);
  return updated;
}

export function selectReviewItems(items, selected) {
  return items.map(item => item.editable === false || (selected && item.decision === 'discarded')
    ? item : { ...item, decision: selected ? 'selected' : item.decision === 'selected' ? 'pending' : item.decision });
}

export function buildReviewConfirmation(draft, candidates) {
  const pending = new Map(candidates.filter(item => item.status === 'pendente').map(item => [item.id, item]));
  const selected = draft.filter(item => item.decision === 'selected');
  if (!selected.length || selected.length > 100 || new Set(selected.map(item => item.id)).size !== selected.length
    || selected.some(item => !pending.has(item.id) || Object.keys(validateReviewItem(item, true)).length)) {
    throw new Error('Revise as avaliações selecionadas antes de confirmar.');
  }
  return selected.map(item => {
    const type = item.type.toLowerCase() === 'prova' ? 'Prova' : 'Trabalho';
    const excerpt = pending.get(item.id).sourceExcerpt;
    const description = excerpt ? `Tipo de avaliação: ${type}\n\n${excerpt}` : `Tipo de avaliação: ${type}`;
    return {
      candidateId: item.id,
      title: item.title.trim(),
      type: item.type.toLowerCase(),
      startsAt: `${item.date}T${item.time}${BRASILIA_UTC_OFFSET}`,
      category: 'Acadêmico',
      description: Array.from(description).slice(0, 10000).join(''),
    };
  });
}

export function validReviewDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000')) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function validUtcOffset(value) {
  if (!/^[+-]\d{2}:\d{2}$/.test(value)) return false;
  const hours = Number(value.slice(1, 3));
  const minutes = Number(value.slice(4));
  return hours <= 14 && minutes < 60 && (hours !== 14 || minutes === 0) && value !== '-00:00';
}

export function validateReviewItem(item, strict = false) {
  if (item.decision !== 'selected') return {};
  const errors = {};
  if (!item.title.trim()) errors.title = 'Informe o título da avaliação.';
  if (strict && (Array.from(item.title.trim()).length < 3 || Array.from(item.title.trim()).length > 200)) errors.title = 'Informe um título entre 3 e 200 caracteres.';
  if (strict && !['prova', 'trabalho'].includes(item.type.toLowerCase())) errors.type = 'Selecione Prova ou Trabalho.';
  if (!validReviewDate(item.date)) errors.date = 'Informe uma data válida.';
  if (!/^([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d{1,6})?)?$/.test(item.time)) errors.time = 'Informe um horário válido entre 00:00 e 23:59:59.';
  return errors;
}
