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
