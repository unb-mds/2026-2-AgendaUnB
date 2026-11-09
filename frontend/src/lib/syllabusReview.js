// Local editor model, not an API payload. Map the approved S6-B02 contract here later.
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

export function validateReviewItem(item) {
  if (item.decision !== 'selected') return {};
  const errors = {};
  if (!item.title.trim()) errors.title = 'Informe o título da avaliação.';
  if (!validReviewDate(item.date)) errors.date = 'Informe uma data válida.';
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(item.time)) errors.time = 'Informe o horário entre 00:00 e 23:59.';
  if (!validUtcOffset(item.utcOffset)) errors.utcOffset = 'Informe o fuso como -03:00 ou +00:00 (até ±14:00).';
  return errors;
}
