import test from 'node:test';
import assert from 'node:assert/strict';
import { calendarDays, dateKey, movePeriod } from './calendar.js';

test('fevereiro bissexto inclui o dia 29 e semanas completas', () => {
  const days = calendarDays(new Date(2024, 1, 15, 12), 'month');
  assert.equal(days.length % 7, 0);
  assert.equal(days[0].getDay(), 0);
  assert.equal(days.at(-1).getDay(), 6);
  assert.equal(days.filter(day => day.getMonth() === 1).length, 29);
  assert.ok(days.some(day => dateKey(day) === '2024-02-29'));
});

test('mês com seis semanas inclui todos os dias e avança a partir do dia 31', () => {
  const reference = new Date(2026, 7, 31, 12);
  assert.equal(calendarDays(reference, 'month').length, 42);
  assert.equal(dateKey(movePeriod(reference, 'month', 1)), '2026-09-01');
  assert.equal(dateKey(movePeriod(new Date(2026, 11, 31), 'month', 1)), '2027-01-01');
});

test('semana atravessa a virada do ano e navegação volta sete dias', () => {
  const reference = new Date(2026, 0, 1, 12);
  const days = calendarDays(reference, 'week');
  assert.equal(days.length, 7);
  assert.equal(dateKey(days[0]), '2025-12-28');
  assert.equal(dateKey(days[6]), '2026-01-03');
  assert.equal(dateKey(movePeriod(reference, 'week', -1)), '2025-12-25');
  assert.equal(dateKey(movePeriod(movePeriod(reference, 'week', 1), 'week', -1)), '2026-01-01');
});
