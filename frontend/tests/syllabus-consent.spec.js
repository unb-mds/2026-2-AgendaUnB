import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
const plan = { id: 'd79eeb53-aed8-4369-936b-156e01cc455c', disciplina: 'Disciplina sintética', fileName: 'sintetico.pdf', status: 'pendente', authorizationRequired: true, preparedTextAvailable: true };
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
  await page.route('**/api/v1/syllabus?*', route => route.fulfill({ status: listStatus, json: listStatus === 200 ? { items, total } : { detail: 'Not Found' } }));
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => route.fulfill({ json: detail }));
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/**', route => route.fulfill({ json: [] }));
}


test('revisão explícita preserva texto exato, revoga consentimento ao editar e envia uma vez', async ({ page }) => {
  await setup(page, { detail: plan });
  const pages = [{ pagina: 1, texto: 'Prova 1 - 10/11/2026 - 14:00.' }];
  let authorized = 0;
  let payload;
  let current = { ...plan };
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => route.fulfill({ json: current }));
  await page.route(`**/api/v1/syllabus/${plan.id}/text`, route => route.fulfill({ json: { pages, provider: 'Google Gemini API', providerAvailable: true } }));
  await page.route(`**/api/v1/syllabus/${plan.id}/extractions`, async route => {
    authorized++;
    payload = route.request().postDataJSON();
    current = { ...plan, authorizationRequired: false, status: 'concluido', extractedEventsCount: 1 };
    await new Promise(resolve => setTimeout(resolve, 100));
    await route.fulfill({ status: 202, json: current });
  });
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  await expect(page.getByText('Nenhum texto foi enviado ao Gemini.', { exact: false })).toBeVisible();
  const submit = page.getByRole('button', { name: 'Autorizar envio ao Gemini' });
  await expect(submit).toBeDisabled();
  const eligible = page.getByRole('checkbox', { name: 'Revisei e removi conteúdo pessoal, sensível e confidencial.' });
  const consent = page.getByRole('checkbox', { name: 'Autorizo o envio somente do texto acima ao Google Gemini.' });
  await eligible.check(); await consent.check();
  const edited = pages[0].texto + '  ';
  await page.getByLabel('Texto da página 1').fill(edited);
  await expect(eligible).not.toBeChecked(); await expect(consent).not.toBeChecked();
  expect(authorized).toBe(0);
  await eligible.check(); await consent.check();
  await submit.evaluate(button => { button.click(); button.click(); });
  await expect(page.getByRole('heading', { name: 'Análise concluída' })).toBeVisible();
  expect(authorized).toBe(1);
  expect(payload.pages).toEqual([{ pagina: 1, texto: edited }]);
  expect(payload.textHash).toBe(createHash('sha256').update(JSON.stringify(payload.pages)).digest('hex'));
  expect(payload.authorize && payload.contentEligible).toBe(true);
});

test('texto colado passa por preparação e provedor indisponível oferece caminho manual', async ({ page }) => {
  await setup(page, { detail: plan });
  let prepared = 0;
  await page.route('**/api/v1/syllabus/text', route => {
    prepared++;
    expect(route.request().postDataJSON()).toEqual({ text: 'Trabalho final - data a definir.' });
    return route.fulfill({ status: 202, json: plan });
  });
  await page.route(`**/api/v1/syllabus/${plan.id}/text`, route => route.fulfill({ json: {
    pages: [{ pagina: null, texto: 'Trabalho final - data a definir.' }], provider: 'Google Gemini API', providerAvailable: false,
  } }));
  await page.goto('/plano-de-ensino?modo=envios');
  await page.getByLabel('Texto do plano', { exact: true }).fill('Trabalho final - data a definir.');
  await page.getByRole('button', { name: 'Preparar texto para revisão' }).click();
  await expect(page.getByLabel('Texto sem referência de página')).toHaveValue('Trabalho final - data a definir.');
  await expect(page.getByRole('button', { name: 'Autorizar envio ao Gemini' })).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Organizar prazos manualmente' })).toHaveAttribute('href', '/eventos?aba=meus');
  expect(prepared).toBe(1);
});

test('revisão de texto funciona em desktop escuro e celular claro sem overflow', async ({ page }) => {
  await setup(page, { detail: plan });
  await page.route(`**/api/v1/syllabus/${plan.id}/text`, route => route.fulfill({ json: {
    pages: [{ pagina: 1, texto: 'Prova de integração - 10/11/2026.\n'.repeat(4) }], provider: 'Google Gemini API', providerAvailable: true,
  } }));
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  await expect(page.getByLabel('Texto da página 1')).toBeVisible();
  await page.screenshot({ path: 'test-results/s7-consent-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => document.body.classList.add('light'));
  await expect(page.getByRole('button', { name: 'Autorizar envio ao Gemini' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/s7-consent-mobile.png', fullPage: true });
});
