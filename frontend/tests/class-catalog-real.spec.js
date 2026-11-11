import { test, expect } from '@playwright/test';
const plan = { id: 'plan-synthetic', disciplina: 'Computação' };
async function setup(page, { guest = false, items = [], total = items.length, detail = plan, listStatus = 200 } = {}) {
  // Substitute only the external auth/data provider, never the page or API client.
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({ contentType: 'application/javascript', body: `
    const user = ${guest ? 'null' : "{ id: 'student-test', email: 'student@example.test', user_metadata: { nome_completo: 'Estudante' } }"};
    let session = user ? { user, access_token: 'test-token' } : null;
    export const supabase = {
      auth: {
        onAuthStateChange(callback) { queueMicrotask(() => callback('INITIAL_SESSION', session));
          const logout = () => { session = null; callback('SIGNED_OUT', null); };
          window.addEventListener('test-signout', logout);
          return { data: { subscription: { unsubscribe() { window.removeEventListener('test-signout', logout); } } } };
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
  await page.route('**/api/v1/class-offerings/70000000-0000-4000-8000-000000000071', route => route.fulfill({ json: { id: '70000000-0000-4000-8000-000000000071', subject_name: plan.disciplina, subject_code: 'FGA0138', class_number: '01', year: 2026, semester: 2, unit: '673', available: true } }));
  await page.route('**/api/v1/class-offerings/*/shared-plans?*', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.route('**/api/v1/syllabus?*', route => route.fulfill({ status: listStatus, json: listStatus === 200 ? { items, total } : { detail: 'Not Found' } }));
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => route.fulfill({ json: detail }));
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/**', route => route.fulfill({ json: [] }));
}


const offer = { id: '70000000-0000-4000-8000-000000000071', subject_name: 'Computação', subject_code: 'FGA0108', class_number: '01', year: 2026, semester: 2, unit: '673', teacher: 'Docente', schedule: '24T12', available: true };
async function catalogSetup(page, { guest = false, failed = false } = {}) {
  await setup(page, { guest });
  let following = false;
  await page.route('**/api/v1/class-offerings/filters', route => route.fulfill({ status: failed ? 503 : 200, json: { units: [{ id: 673, code: 'FCTE', name: 'Gama' }], periods: ['2026.2', '2027.1'], stale: true, source_updated_at: '2026-11-09T12:00:00Z' } }));
  await page.route('**/api/v1/class-offerings?*', route => {
    expect(route.request().headers().authorization).toBe('Bearer test-token');
    const url = new URL(route.request().url());
    const empty = url.searchParams.get('q') === 'inexistente';
    return route.fulfill({ json: { items: empty ? [] : [offer], total: empty ? 0 : 21, offset: Number(url.searchParams.get('offset')), limit: 20, stale: true, source_updated_at: '2026-11-09T12:00:00Z' } });
  });
  await page.route('**/api/v1/me/class-offerings', route => route.fulfill({ json: { items: following ? [offer] : [] } }));
  await page.route(`**/api/v1/me/class-offerings/${offer.id}`, route => {
    following = route.request().method() === 'PUT';
    return route.fulfill({ status: 204 });
  });
  return () => following;
}

for (const width of [360, 1365]) {
  test(`busca, vínculo persistente, oferta correta e teclado ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await catalogSetup(page);
    await page.goto('/plano-de-ensino');
    await expect(page.getByRole('navigation', { name: 'Etapas do plano de ensino' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Catálogo e planos reais' })).toHaveCount(0);
    await page.getByLabel('Ano/Período').selectOption('2026.2');
    await page.getByLabel('Unidade', { exact: true }).selectOption('673');
    await page.getByLabel('Disciplina, código, professor ou turma').fill('FGA0108');
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: 'Buscar turmas', exact: true })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.getByText('21 turmas encontradas.')).toBeVisible();
    await expect(page.getByText('Catálogo desatualizado', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Seguir turma', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Ver planos' })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('button', { name: 'Ver planos' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath('catalog.png'), fullPage: true });
    await page.getByRole('button', { name: 'Ver planos' }).click();
    await expect(page).toHaveURL(new RegExp(`oferta=${offer.id}`));
    await expect(page.getByRole('heading', { name: 'Enviar plano de ensino' })).toBeVisible();
    await expect(page.getByText('Ainda não há plano compartilhado nesta oferta.', { exact: false })).toBeVisible();
    await page.getByRole('link', { name: 'Voltar ao catálogo de turmas' }).click();
    await page.getByRole('button', { name: 'Deixar de seguir', exact: true }).click();
    await expect(page.getByText('Você ainda não segue turmas.', { exact: false })).toBeVisible();
  });
}

test('503 recuperável, vazio e paginação local', async ({ page }) => {
  await catalogSetup(page, { failed: true });
  await page.goto('/plano-de-ensino');
    await expect(page.getByRole('navigation', { name: 'Etapas do plano de ensino' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Catálogo e planos reais' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Cadastrar um compromisso manualmente' })).toBeVisible();
  await catalogSetup(page);
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await page.getByLabel('Ano/Período').selectOption('2026.2');
  await page.getByRole('button', { name: 'Buscar turmas', exact: true }).click();
  const next = page.waitForRequest(r => r.url().includes('offset=20'));
  await page.getByRole('button', { name: 'Próxima' }).click(); await next;
  await page.getByLabel('Disciplina, código, professor ou turma').fill('inexistente');
  await page.getByRole('button', { name: 'Buscar turmas', exact: true }).click();
  await expect(page.getByText('Nenhuma turma encontrada.', { exact: false })).toBeVisible();
});

test('visitante mantém demonstração interativa sem chamar origem', async ({ page }) => {
  await catalogSetup(page, { guest: true });
  const calls = [];
  page.on('request', r => { if (/class-offerings|api.followw.app/.test(r.url())) calls.push(r.url()); });
  await page.goto('/plano-de-ensino');
    await expect(page.getByRole('navigation', { name: 'Etapas do plano de ensino' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Catálogo e planos reais' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '1 Selecionar turmas' })).toBeVisible();
  await expect(page.getByText('Catálogo de demonstração', { exact: true })).toBeVisible();
  expect(calls).toEqual([]);
});

test('primeira carga indisponível é consultada novamente automaticamente', async ({ page }) => {
  await catalogSetup(page, { failed: true });
  await page.clock.install();
  await page.goto('/plano-de-ensino');
  await expect(page.getByText('A primeira carga precisa concluir', { exact: false })).toBeVisible();
  await page.route('**/api/v1/class-offerings/filters', route => route.fulfill({ json: {
    units: [{ id: 673, code: 'FCTE', name: 'Gama' }], periods: ['2026.2'], stale: false, source_updated_at: '2026-11-10T12:00:00Z'
  } }));
  await page.clock.fastForward(15000);
  await expect(page.getByLabel('Ano/Período').locator('option', { hasText: '2026.2' })).toHaveCount(1);
  await expect(page.getByText('A primeira carga precisa concluir', { exact: false })).toHaveCount(0);
});
