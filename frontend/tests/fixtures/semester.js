export async function mockAuth(page, guest) {
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({ contentType: 'application/javascript', body: `
    const user = ${guest ? 'null' : "{ id: 'student-test', email: 'student@example.test', user_metadata: { nome_completo: 'Estudante' } }"};
    let session = user ? { user, access_token: 'test-token' } : null;
    export const supabase = {
      auth: {
        onAuthStateChange(callback) { queueMicrotask(() => callback('INITIAL_SESSION', session));
          const logout = () => { session = null; callback('SIGNED_OUT', null); };
          const swap = e => { session = { access_token: 'test-token', user: { id: e.detail, email: 'other@example.test' } }; callback('SIGNED_IN', session); };
          window.addEventListener('test-switch-account', swap);
          window.addEventListener('test-signout', logout);
          return { data: { subscription: { unsubscribe() { window.removeEventListener('test-signout', logout); window.removeEventListener('test-switch-account', swap); } } } };
        },
        async getSession() { return { data: { session } }; },
        async signOut() { window.dispatchEvent(new Event('test-signout')); }
      },
      from(table) {
        const result = { data: table === 'profiles' ? { papel: 'student', nome_completo: 'Estudante' } : [], count: 0, error: null };
        const chain = { then(resolve) { return Promise.resolve(result).then(resolve); } };
        for (const name of ['select','eq','order','range','is','single']) chain[name] = () => chain;
        return chain;
      }
    };
  ` }));
}

export const makeOffer = index => ({
  id: `class-${index}`, subject_name: `Disciplina ${index}`, subject_code: `FGA010${index}`,
  class_number: '01', year: 2026, semester: 2, teacher: 'Docente', unit_name: 'Gama',
  schedule: '24T12', available: true,
});
export const makePlan = (index, properties = {}) => ({
  id: `plan-${index}`, userId: 'student-test', offeringId: `class-${index}`, fileName: `plano-${index}.pdf`,
  disciplina: `Disciplina ${index}`, ano: 2026, semestre: 2, status: 'concluido',
  extractedEventsCount: 1, createdAt: '2026-11-15T18:00:00Z',
  ...properties,
});
export const makeCandidate = (index, properties = {}) => ({
  id: `event-${index}`, title: `Avaliação ${index}`, type: 'trabalho', status: 'pendente',
  ambiguous: false, ambiguousFields: [], suggestedDate: '2026-11-23', suggestedTime: null,
  sourcePage: 2, sourceExcerpt: 'Prova e entrega em novembro.', versionId: 'v1',
  ...properties,
});
export const makePdf = index => ({
  name: `plano-${index}.pdf`, mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 conteúdo sintético'),
});
export const summary = ({ candidates, ...plan }) => plan;

export async function setupSemester(page, { guest = false, offers = [makeOffer(1)], followed = offers, plans = [] } = {}) {
  await mockAuth(page, guest);
  const data = new Map(plans.map(plan => [plan.id, plan]));
  const memberships = new Map(followed.map(offer => [offer.id, offer]));
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/**', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/class-offerings/filters', route => route.fulfill({ json: {
    periods: ['2026.2'], units: [{ id: 'gama', code: 'FCTE', name: 'Gama' }],
  } }));
  await page.route('**/api/v1/class-offerings?*', route => {
    const q = new URL(route.request().url()).searchParams.get('q');
    const items = q ? offers.filter(offer => offer.subject_code.includes(q)) : offers;
    return route.fulfill({ json: { items, total: items.length } });
  });
  await page.route('**/api/v1/me/class-offerings', route => route.fulfill({ json: { items: [...memberships.values()] } }));
  await page.route('**/api/v1/me/class-offerings/*', route => {
    const id = route.request().url().split('/').at(-1);
    const offer = offers.find(item => item.id === id);
    if (!offer?.available) return route.fulfill({ status: 404, json: { detail: 'Turma indisponível.' } });
    if (route.request().method() === 'PUT') memberships.set(id, offer);
    else memberships.delete(id);
    return route.fulfill({ status: 204 });
  });
  await page.route(/\/api\/v1\/class-offerings\/class-[^/?]+$/, route => {
    const id = route.request().url().split('/').at(-1);
    const offer = offers.find(item => item.id === id);
    return offer ? route.fulfill({ json: offer }) : route.fulfill({ status: 404, json: { detail: 'Turma indisponível.' } });
  });
  await page.route('**/api/v1/class-offerings/*/shared-plans?*', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.route('**/api/v1/syllabus?*', route => {
    const params = new URL(route.request().url()).searchParams;
    const items = [...data.values()].filter(plan => !params.has('offering_id') || plan.offeringId === params.get('offering_id'));
    const offset = Number(params.get('offset'));
    const limit = Number(params.get('limit'));
    return route.fulfill({ json: { items: items.slice(offset, offset + limit).map(summary), total: items.length } });
  });
  await page.route('**/api/v1/syllabus/*', route => {
    const id = route.request().url().split('/').at(-1);
    const plan = data.get(id);
    return plan ? route.fulfill({ json: plan }) : route.fulfill({ status: 404, json: { detail: 'Plano indisponível.' } });
  });
  return { data, memberships };
}

export function confirmation(plan, requested) {
  const items = requested.map((item, index) => ({
    candidateId: item.candidateId, eventId: `${plan.id}-saved-${index}`, removed: false,
  }));
  return {
    syllabusId: plan.id, items, events: items.map(item => ({
      id: item.eventId, origin: { syllabusId: plan.id, candidateId: item.candidateId },
    })),
  };
}
