import test from 'node:test';
import assert from 'node:assert/strict';
import { canConfirm, demoReducer, initialDemoState } from './teachingPlanDemo.js';

test('etapas dependentes ficam bloqueadas antes da matrícula', () => {
  const state = initialDemoState();
  for (const action of [{ type: 'STEP', step: 4 }, { type: 'PROCESS', name: 'plano.pdf' }, { type: 'OPEN', id: 'mds' }, { type: 'SELECT_COURSE', id: 'cal', selected: true }, { type: 'IMPORT' }]) {
    assert.deepEqual(demoReducer(state, action), state);
  }
});
test('revisão parcial exige conferência, data, horário e fuso; editar revoga conferência', () => {
  let state = demoReducer(initialDemoState(), { type: 'ENROLL', name: 'exemplo.pdf' });
  state = demoReducer(state, { type: 'PROCESS', name: 'plano.pdf' });
  assert.equal(state.plans.mds.status, 'processing');
  assert.equal(demoReducer(state, { type: 'PROCESS', name: 'duplicado.pdf' }), state);
  state = demoReducer(state, { type: 'PROCESSED', id: 'mds' });
  assert.equal(state.step, 3);
  state = demoReducer(state, { type: 'EDIT', id: 'first', field: 'decision', value: 'selected' });
  state = demoReducer(state, { type: 'ACK', value: true });
  assert.equal(canConfirm(state.plans.mds, state.acknowledged), false);
  state = demoReducer(state, { type: 'EDIT', id: 'first', field: 'utcOffset', value: '-03:00' });
  assert.equal(state.acknowledged, false);
  state = demoReducer(state, { type: 'ACK', value: true });
  state = demoReducer(state, { type: 'CONFIRM' });
  assert.equal(state.plans.mds.status, 'ready');
  assert.equal(state.step, 4);
  state = demoReducer(state, { type: 'SELECT_COURSE', id: 'mds', selected: true });
  state = demoReducer(state, { type: 'IMPORT' });
  assert.equal(state.events.length, 1);
  const repeated = demoReducer(demoReducer(state, { type: 'SELECT_COURSE', id: 'mds', selected: true }), { type: 'IMPORT' });
  assert.deepEqual(repeated.events, state.events);
  assert.deepEqual(demoReducer(state, { type: 'RESET' }), initialDemoState());
});
test('voltar etapas preserva edições e não vincula outra turma', () => {
  let state = demoReducer(initialDemoState(), { type: 'ENROLL', name: 'exemplo.pdf' });
  state = demoReducer(state, { type: 'PROCESS', name: 'mds.pdf' });
  state = demoReducer(state, { type: 'PROCESSED', id: 'mds' });
  state = demoReducer(state, { type: 'EDIT', id: 'first', field: 'title', value: 'Prova editada' });
  state = demoReducer(state, { type: 'OPEN', id: 'fac' });
  assert.equal(state.plans.fac, undefined);
  state = demoReducer(state, { type: 'OPEN', id: 'mds' });
  assert.equal(state.plans.mds.candidates[0].title, 'Prova editada');
  assert.equal(state.plans.mds.status, 'review');
});
