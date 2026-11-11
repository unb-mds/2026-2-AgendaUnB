import test from 'node:test';
import assert from 'node:assert/strict';
import { canConfirm, canOpenDemoStep, demoReducer, initialDemoState } from './teachingPlanDemo.js';

const periods = ['2026.2', '2027.1'];
const initial = () => initialDemoState({ periods });
const mds = 'mds:2026.2';
const fac = 'fac:2026.2';
const cal = 'cal:2026.2';
const follow = (state, id) => demoReducer(state, { type: 'FOLLOW', id, available: true });
const open = (state, id) => demoReducer(state, { type: 'OPEN', id });
const prepare = state => demoReducer(state, { type: 'PROCESS', name: 'plano.pdf', available: true });

test('o envio exige vínculo com a oferta específica e presença no catálogo', () => {
  const state = initial();
  assert.equal(follow(state, 'mds:2028.2'), state);
  assert.equal(follow(state, 'inexistente'), state);
  assert.equal(prepare(state), state);
  assert.equal(open(state, mds), state);
  const followed = open(follow(state, mds), mds);
  assert.equal(follow(followed, mds), followed);
  assert.equal(open(followed, 'mds:2027.1'), followed);
  assert.equal(demoReducer(followed, { type: 'PROCESS', name: 'plano.pdf', available: false }), followed);
});

test('revisão parcial exige conferência, data, horário e fuso; editar revoga conferência', () => {
  let state = prepare(open(follow(initial(), mds), mds));
  assert.equal(state.plans[mds].status, 'processing');
  assert.equal(prepare(state), state);
  state = demoReducer(state, { type: 'PROCESSED', id: mds });
  assert.equal(state.step, 3);
  state = demoReducer(state, { type: 'EDIT', id: 'first', field: 'decision', value: 'selected' });
  state = demoReducer(state, { type: 'ACK', value: true });
  assert.equal(canConfirm(state.plans[mds], state.acknowledged), false);
  state = demoReducer(state, { type: 'EDIT', id: 'first', field: 'utcOffset', value: '-03:00' });
  assert.equal(state.acknowledged, false);
  state = demoReducer(state, { type: 'ACK', value: true });
  state = demoReducer(state, { type: 'CONFIRM' });
  assert.equal(state.plans[mds].status, 'ready');
  assert.equal(state.step, 4);
});

test('trocar de oferta preserva edições e não vincula o plano à outra turma', () => {
  let state = follow(follow(initial(), mds), fac);
  state = prepare(open(state, mds));
  state = demoReducer(state, { type: 'PROCESSED', id: mds });
  state = demoReducer(state, { type: 'EDIT', id: 'first', field: 'title', value: 'Prova editada' });
  state = open(state, fac);
  assert.equal(state.plans[fac], undefined);
  state = open(state, mds);
  assert.equal(state.plans[mds].candidates[0].title, 'Prova editada');
});

test('deixar de seguir remove uma seleção pendente, preserva as cópias importadas e mantém acesso à prévia', () => {
  let state = follow(initial(), cal);
  const select = { type: 'SELECT_COURSE', id: cal, selected: true };
  state = demoReducer(demoReducer(state, select), { type: 'IMPORT' });
  assert.equal(state.events.length, 2);
  const repeated = demoReducer(demoReducer(state, select), { type: 'IMPORT' });
  assert.deepEqual(repeated.events, state.events);
  const unfollowed = demoReducer(demoReducer(state, select), { type: 'UNFOLLOW', id: cal });
  assert.deepEqual(unfollowed.selectedCourses, []);
  assert.deepEqual(unfollowed.events, state.events);
  assert.equal(canOpenDemoStep(unfollowed, 4), true);
  assert.equal(open(unfollowed, cal), unfollowed);
  assert.deepEqual(demoReducer(unfollowed, { type: 'RESET' }), initial());
});
