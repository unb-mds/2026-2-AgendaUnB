import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calendarDays,
  dateKey,
  eventDateKeys,
  formatEventSchedule,
  isPastUiEvent,
  movePeriod,
  splitMyEventsByHistory,
} from './calendar.js';

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

test('eventDateKeys projeta todos os dias civis respeitando fim exclusivo e intervalos', () => {
  assert.deepEqual(
    eventDateKeys({ data: '2026-11-18', diaInteiro: true, endDate: '2026-11-21' }),
    ['2026-11-18', '2026-11-19', '2026-11-20'],
  );
  assert.deepEqual(
    eventDateKeys({ data: '2026-11-10', dataFim: '2026-11-12', diaInteiro: false }),
    ['2026-11-10', '2026-11-11', '2026-11-12'],
  );
  assert.deepEqual(
    eventDateKeys({ data: '2026-11-10', diaInteiro: false }),
    ['2026-11-10'],
  );
});

test('formatEventSchedule formata corretamente dia inteiro, intervalo e horário único', () => {
  const singleAllDay = formatEventSchedule({ data: '2026-11-18', diaInteiro: true });
  assert.ok(singleAllDay.includes('Dia inteiro'));

  const multiAllDay = formatEventSchedule({ data: '2026-11-18', dataFim: '2026-11-20', diaInteiro: true });
  assert.ok(multiAllDay.includes('18') && multiAllDay.includes('20') && multiAllDay.includes('Dia inteiro'));

  const timed = formatEventSchedule({ data: '2026-11-18', horario: '14:00', horarioFim: '16:30', diaInteiro: false });
  assert.ok(timed.includes('14:00 – 16:30'));
});

test('splitMyEventsByHistory separa eventos ativos de históricos separados de públicos salvos e privados passados', () => {
  const referenceNow = new Date('2026-11-18T12:00:00-03:00');
  const items = [
    {
      id: 'pub-past',
      titulo: 'Palestra Passada Salva',
      startsAt: '2026-11-10T14:00:00-03:00',
      data: '2026-11-10',
      horario: '14:00',
      visibilidade: 'Público',
      salvoNaAgenda: true,
      criadoPorMim: false,
    },
    {
      id: 'priv-past',
      titulo: 'Prova 1 Passada',
      startsAt: '2026-11-12T10:00:00-03:00',
      data: '2026-11-12',
      horario: '10:00',
      visibilidade: 'Privado',
      salvoNaAgenda: false,
      criadoPorMim: true,
    },
    {
      id: 'pub-future',
      titulo: 'Mostra Futura Salva',
      startsAt: '2026-11-25T15:00:00-03:00',
      data: '2026-11-25',
      horario: '15:00',
      visibilidade: 'Público',
      salvoNaAgenda: true,
      criadoPorMim: false,
    },
    {
      id: 'priv-future',
      titulo: 'Trabalho Final Futuro',
      startsAt: '2026-11-28T18:00:00-03:00',
      data: '2026-11-28',
      horario: '18:00',
      visibilidade: 'Privado',
      salvoNaAgenda: false,
      criadoPorMim: true,
    },
  ];

  assert.equal(isPastUiEvent(items[0], referenceNow), true);
  assert.equal(isPastUiEvent(items[2], referenceNow), false);

  const grouped = splitMyEventsByHistory(items, referenceNow);
  assert.deepEqual(grouped.upcomingEvents.map(e => e.id), ['pub-future', 'priv-future']);
  assert.deepEqual(grouped.pastSavedPublicEvents.map(e => e.id), ['pub-past']);
  assert.deepEqual(grouped.pastPersonalEvents.map(e => e.id), ['priv-past']);
});
