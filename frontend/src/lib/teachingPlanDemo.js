import { validateReviewItem } from './syllabusReview.js';
import { catalogPeriods, demoOffering } from './classCatalogDemo.js';

export const demoMonths = period => {
  const [year, semester] = period.split('.');
  return semester === '1' ? [`${year}-05`, `${year}-06`] : [`${year}-11`, `${year}-12`];
};

function sampleCandidates(period) {
  const [first, last] = demoMonths(period);
  return [
    { id: 'first', title: 'Prova 1', type: 'Prova', date: `${first}-12`, time: '14:00', utcOffset: '', decision: 'pending', page: 4, excerpt: `12/${first.slice(-2)} — Primeira avaliação, às 14h, em sala.` },
    { id: 'final', title: 'Entrega do projeto final', type: 'Trabalho', date: `${last}-03`, time: '', utcOffset: '', decision: 'pending', page: 5, excerpt: `Entrega do projeto final: 03/${last.slice(-2)}.` },
  ];
}

export function initialDemoState({ periods = catalogPeriods(), ids = [] } = {}) {
  const [month] = demoMonths(periods[0]);
  return { periods, step: 1, followedCourses: ids, activeCourse: ids[0] || null, plans: {
    [`cal:${periods[0]}`]: { status: 'ready', fileName: 'plano_calculo_exemplo.pdf', candidates: [
      { id: 'cal-1', title: 'Prova 2', type: 'Prova', date: `${month}-18`, time: '10:00', utcOffset: '-03:00', decision: 'selected' },
      { id: 'cal-2', title: 'Prova final', type: 'Prova', date: `${month}-30`, time: '10:00', utcOffset: '-03:00', decision: 'selected' },
    ] },
  }, events: [], selectedCourses: [], acknowledged: false };
}

export function canOpenDemoStep(state, step) {
  switch (step) {
    case 1: return true;
    case 2: return !!state.activeCourse;
    case 3: return !!state.plans[state.activeCourse]?.candidates;
    case 4: return !!(state.followedCourses.length || state.events.length);
    default: return false;
  }
}

export function canConfirm(plan, acknowledged) {
  const selected = plan?.candidates?.filter(item => item.decision === 'selected') || [];
  return plan?.status === 'review' && acknowledged && selected.length > 0
    && selected.every(item => Object.keys(validateReviewItem(item)).length === 0);
}

export function demoReducer(state, action) {
  switch (action.type) {
    case 'RESET': return initialDemoState({ periods: state.periods });
    case 'FOLLOW': {
      const offer = demoOffering(action.id);
      if (!action.available || !offer || !state.periods.includes(offer.period) || state.followedCourses.includes(action.id)) return state;
      return { ...state, followedCourses: [...state.followedCourses, action.id], activeCourse: state.activeCourse || action.id };
    }
    case 'UNFOLLOW': {
      if (!state.followedCourses.includes(action.id)) return state;
      const followedCourses = state.followedCourses.filter(id => id !== action.id);
      const removedActive = state.activeCourse === action.id;
      return { ...state, followedCourses, selectedCourses: state.selectedCourses.filter(id => id !== action.id),
        activeCourse: removedActive ? followedCourses[0] || null : state.activeCourse,
        step: removedActive && (state.step === 2 || state.step === 3) ? 1 : state.step,
        acknowledged: removedActive ? false : state.acknowledged };
    }
    case 'STEP': {
      if (!canOpenDemoStep(state, action.step)) return state;
      return { ...state, step: action.step };
    }
    case 'OPEN': {
      if (!state.followedCourses.includes(action.id)) return state;
      return { ...state, activeCourse: action.id, acknowledged: false,
        step: state.plans[action.id]?.candidates ? 3 : 2 };
    }
    case 'PROCESS': {
      if (!action.available || !state.followedCourses.includes(state.activeCourse) || state.plans[state.activeCourse]) return state;
      return { ...state, plans: { ...state.plans, [state.activeCourse]: { status: 'processing', fileName: action.name } } };
    }
    case 'PROCESSED': {
      const plan = state.plans[action.id];
      if (plan?.status !== 'processing') return state;
      return { ...state, plans: { ...state.plans, [action.id]: { ...plan, status: 'review', candidates: sampleCandidates(demoOffering(action.id).period) } },
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
      if (state.plans[action.id]?.status !== 'ready' || !state.followedCourses.includes(action.id)) return state;
      return { ...state, selectedCourses: action.selected
        ? [...new Set([...state.selectedCourses, action.id])]
        : state.selectedCourses.filter(id => id !== action.id) };
    }
    case 'IMPORT': {
      if (!state.selectedCourses.length) return state;
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
