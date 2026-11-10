// Local editor model, not an API payload.
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
      time: string('time'), utcOffset: '', decision: 'pending' };
  });
}

export function createCandidateReviewDraft(candidates) {
  return createReviewDraft(candidates).map((draft, index) => {
    const candidate = candidates[index];
    // Preserve civil suggestions, never derive a date or timezone from the browser.
    const instant = candidate.startsAt?.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)(Z|[+-]\d{2}:\d{2})$/);
    return { ...draft, type: draft.type.toLowerCase(),
      date: candidate.suggestedDate ?? instant?.[1] ?? '',
      time: candidate.suggestedTime ?? instant?.[2] ?? '',
      utcOffset: instant ? (instant[3] === 'Z' ? '+00:00' : instant[3]) : '',
      status: candidate.status, versionId: candidate.versionId,
      editable: candidate.status === 'pendente' };
  });
}

export function selectReviewItems(items, selected) {
  return items.map(item => item.editable === false || (selected && item.decision === 'discarded')
    ? item : { ...item, decision: selected ? 'selected' : item.decision === 'selected' ? 'pending' : item.decision });
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
  if (!validUtcOffset(item.utcOffset)) errors.utcOffset = 'Informe o fuso como -03:00 ou +00:00 (até ±14:00).';
  return errors;
}
