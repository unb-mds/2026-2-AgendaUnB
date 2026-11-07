import { validateReviewItem } from './syllabusReview.js';

// Explicit demonstration data, never an API response or extracted PDF content.
export const DEMO_COURSES = [
  { id: 'mds', initials: 'MDS', title: 'Métodos de Desenvolvimento de Software', group: 'A', campus: 'Faculdade do Gama', enrolled: true },
  { id: 'fac', initials: 'FAC', title: 'Fundamentos de Arquitetura de Computadores', group: 'B', campus: 'Darcy Ribeiro', enrolled: true },
  { id: 'cal', initials: 'C1', title: 'Cálculo 1', group: 'C', campus: 'Darcy Ribeiro', enrolled: true },
  { id: 'icc', initials: 'ICC', title: 'Introdução à Ciência da Computação', group: 'A', campus: 'Darcy Ribeiro', enrolled: false },
  { id: 'ea', initials: 'EA', title: 'Engenharia e Ambiente', group: 'B', campus: 'Faculdade do Gama', enrolled: false },
];

export function sampleCandidates() {
  return [
    { id: 'first', title: 'Prova 1', type: 'Prova', date: '2026-11-12', time: '14:00', utcOffset: '', decision: 'pending', page: 4, excerpt: '12/11 — Primeira avaliação, às 14h, em sala.' },
    { id: 'final', title: 'Entrega do projeto final', type: 'Trabalho', date: '2026-12-03', time: '', utcOffset: '', decision: 'pending', page: 5, excerpt: 'Entrega do projeto final: 03 de dezembro.' },
  ];
}

export function initialDemoState() {
  return { step: 1, enrollment: '', activeCourse: 'mds', plans: {
    cal: { status: 'ready', fileName: 'plano_calculo_exemplo.pdf', candidates: [
      { id: 'cal-1', title: 'Prova 2', type: 'Prova', date: '2026-11-18', time: '10:00', utcOffset: '-03:00', decision: 'selected' },
      { id: 'cal-2', title: 'Prova final', type: 'Prova', date: '2026-11-30', time: '10:00', utcOffset: '-03:00', decision: 'selected' },
    ] },
  }, events: [], selectedCourses: [], acknowledged: false };
}

export function canConfirm(plan, acknowledged) {
  const selected = plan?.candidates?.filter(item => item.decision === 'selected') || [];
  return plan?.status === 'review' && acknowledged && selected.length > 0
    && selected.every(item => Object.keys(validateReviewItem(item)).length === 0);
}

export function demoReducer(state, action) {
  switch (action.type) {
    case 'RESET': return initialDemoState();
    case 'ENROLL': return state.enrollment ? state : { ...state, enrollment: action.name, step: 2 };
    case 'STEP': {
      if (![1, 2, 3, 4].includes(action.step) || (action.step > 1 && !state.enrollment)) return state;
      if (action.step === 3 && !state.plans[state.activeCourse]?.candidates) return state;
      return { ...state, step: action.step };
    }
    case 'OPEN': {
      if (!state.enrollment || !DEMO_COURSES.some(c => c.id === action.id && c.enrolled)) return state;
      return { ...state, activeCourse: action.id, acknowledged: false,
        step: state.plans[action.id]?.candidates ? 3 : 2 };
    }
    case 'PROCESS': {
      if (!state.enrollment || state.plans[state.activeCourse]) return state;
      return { ...state, plans: { ...state.plans, [state.activeCourse]: { status: 'processing', fileName: action.name } } };
    }
    case 'PROCESSED': {
      const plan = state.plans[action.id];
      if (plan?.status !== 'processing') return state;
      return { ...state, plans: { ...state.plans, [action.id]: { ...plan, status: 'review', candidates: sampleCandidates() } },
        step: state.activeCourse === action.id && state.step === 2 ? 3 : state.step };
    }
    case 'EDIT': {
      const plan = state.plans[state.activeCourse];
      if (plan?.status !== 'review' || !['title', 'type', 'date', 'time', 'utcOffset', 'decision'].includes(action.field)) return state;
      return { ...state, acknowledged: false, plans: { ...state.plans, [state.activeCourse]: { ...plan,
        candidates: plan.candidates.map(item => item.id === action.id ? { ...item, [action.field]: action.value } : item) } } };
    }
    case 'ACK': return { ...state, acknowledged: action.value };
    case 'CONFIRM': {
      const plan = state.plans[state.activeCourse];
      if (!canConfirm(plan, state.acknowledged)) return state;
      return { ...state, step: 4, plans: { ...state.plans, [state.activeCourse]: { ...plan, status: 'ready' } } };
    }
    case 'SELECT_COURSE': {
      if (state.plans[action.id]?.status !== 'ready' || !state.enrollment) return state;
      return { ...state, selectedCourses: action.selected
        ? [...new Set([...state.selectedCourses, action.id])]
        : state.selectedCourses.filter(id => id !== action.id) };
    }
    case 'IMPORT': {
      if (!state.enrollment) return state;
      const events = new Map(state.events.map(event => [event.id, event]));
      for (const id of state.selectedCourses) {
        const plan = state.plans[id];
        if (plan?.status !== 'ready') continue;
        for (const item of plan.candidates.filter(item => item.decision === 'selected')) {
          const key = `${id}:${item.id}`;
          if (!events.has(key)) events.set(key, { ...item, id: key, courseId: id });
        }
      }
      return { ...state, events: [...events.values()], selectedCourses: [] };
    }
    default: return state;
  }
}
