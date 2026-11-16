import test from 'node:test';
import assert from 'node:assert/strict';
import { classStartOnDate } from './classSchedule.js';

test('usa o início do bloco da turma no dia civil da prova', () => {
  const schedule = '3M34 5T23 7N34';
  assert.equal(classStartOnDate(schedule, '2026-11-10'), '10:00');
  assert.equal(classStartOnDate(schedule, '2026-11-12'), '14:00');
  assert.equal(classStartOnDate(schedule, '2026-11-14'), '20:50');
  assert.equal(classStartOnDate(schedule, '2026-11-11'), '');
});

test('períodos consecutivos indicam um bloco e códigos repetidos não tornam o horário ambíguo', () => {
  assert.equal(classStartOnDate('24T23', '2026-11-11'), '14:00');
  assert.equal(classStartOnDate('35M5 35T1', '2026-11-10'), '12:00');
  assert.equal(classStartOnDate('3M2, 3M1; 3M2', '2026-11-10'), '08:00');
});

test('agenda com mais de um bloco ou sem dados confiáveis deixa o horário em branco', () => {
  for (const schedule of ['3T24', '3M12 3T23', '3N5', '3M12 (01/08/2026 - 20/12/2026)', '3M12 a definir', '', null]) {
    assert.equal(classStartOnDate(schedule, '2026-11-10'), '', String(schedule));
  }
  for (const date of ['2026-02-30', '2026-11', '2026-11-15', '']) {
    assert.equal(classStartOnDate('3M12', date), '', date);
  }
});
