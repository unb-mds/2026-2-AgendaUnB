import { createHash } from 'node:crypto';
import { test, expect } from '@playwright/test';
import { makeOffer, makePlan, setupSemester } from './fixtures/semester.js';

const plan = makePlan(1, { status: 'pendente', authorizationRequired: true, preparedTextAvailable: true });
const provider = 'Google Gemini API';
const path = '/plano-de-ensino?plano=plan-1&etapa=3';
const pages = [{ pagina: 1, texto: 'Prova em 23/11/2026 às 14:00.' }];
const authorize = page => page.getByRole('button', { name: 'Autorizar envio', exact: true });

test('texto bruto mede capacidade em UTF-8 e fica disponível para recuperar o envio', async ({ page }) => {
  const secondClass = { ...makeOffer(1), id: 'class-2', class_number: '02' };
  await setupSemester(page, { offers: [makeOffer(1), secondClass] });
  const posts = [];
  await page.route('**/api/v1/syllabus/text', route => {
    posts.push(route.request().postDataJSON());
    return route.abort();
  });
  await page.goto('/plano-de-ensino');
  const select = page.getByRole('button', { name: 'Turma dos planos' });
  await expect(select).toBeEnabled();
  await select.press('Enter');
  await page.getByRole('button', { name: /FGA0101 · Turma 02/ }).press('Enter');
  const input = page.getByLabel('Texto do plano', { exact: true });
  const submit = page.getByRole('button', { name: 'Preparar texto para revisão' });
  await input.fill('é'.repeat(20001));
  await expect(submit).toBeDisabled();
  await expect(page.getByRole('progressbar', { name: 'Capacidade do texto usada' })).toHaveAttribute('aria-valuetext', '101% — limite excedido');
  await expect(page.getByText('Limite excedido. Reduza o texto.')).toBeVisible();
  const text = 'é'.repeat(20000);
  await input.fill(text);
  await submit.evaluate(button => { button.click(); button.click(); });
  await expect(page.getByText(/Confira o histórico antes de tentar de novo/)).toBeVisible();
  expect(posts).toEqual([{ text, offering_id: 'class-2' }]);

  await select.click();
  await page.getByRole('button', { name: /FGA0101 · Turma 01/ }).click();
  await expect(page).toHaveURL(/oferta=class-1/);
  const history = page.waitForRequest(request => {
    const url = new URL(request.url());
    return url.pathname.endsWith('/api/v1/syllabus') && url.searchParams.get('offering_id') === 'class-2';
  });
  await page.getByRole('button', { name: 'Consultar histórico' }).click();
  await history;
  await expect(page).toHaveURL(/oferta=class-2/);
  await expect(page.getByRole('button', { name: 'Não encontrei no histórico. Reenviar' })).toBeVisible();
});

test('prévia inválida permite tentar novamente; provedor indisponível bloqueia autorização', async ({ page }) => {
  await setupSemester(page, { plans: [plan] });
  await page.route('**/api/v1/syllabus/plan-1/text', route => route.fulfill({ json: { pages: [null] } }));
  await page.goto(path);
  await expect(page.getByRole('alert')).toContainText('O serviço retornou um texto inválido');
  await expect(authorize(page)).toHaveCount(0);
  await page.route('**/api/v1/syllabus/plan-1/text', route => route.fulfill({ json: { pages, provider, providerAvailable: false } }));
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(page.getByLabel('Texto da página 1')).toHaveValue(pages[0].texto);
  await expect(authorize(page)).toBeDisabled();
  await expect(page.getByText('A extração está indisponível no momento.')).toBeVisible();
});

test('clique explícito consente com a versão editada e bloqueia envio duplo', async ({ page }) => {
  const { data } = await setupSemester(page, { plans: [plan] });
  await page.route('**/api/v1/syllabus/plan-1/text', route => route.fulfill({ json: { pages, provider, providerAvailable: true } }));
  const writes = [];
  await page.route('**/api/v1/syllabus/plan-1/extractions', route => {
    writes.push(route.request().postDataJSON());
    const next = { ...plan, authorizationRequired: false, status: 'processando' };
    data.set(plan.id, next);
    return route.fulfill({ status: 202, json: next });
  });
  await page.goto(path);
  const edited = [{ pagina: 1, texto: pages[0].texto + '  ' }];
  await page.getByLabel('Texto da página 1').fill(edited[0].texto);
  await expect(page.getByText(/Ao autorizar, você declara que revisou/)).toBeVisible();
  expect(writes).toEqual([]);
  await authorize(page).evaluate(button => { button.click(); button.click(); });
  await expect(page.getByText('Analisando seu plano', { exact: true })).toBeVisible();
  expect(writes).toEqual([{
    pages: edited, textHash: createHash('sha256').update(JSON.stringify(edited)).digest('hex'),
    authorize: true, contentEligible: true, reprocess: false,
  }]);
});

for (const status of ['processando', 'concluido']) {
  test(`autorização com resposta perdida consulta estado persistido ${status}`, async ({ page }) => {
    const { data } = await setupSemester(page, { plans: [plan] });
    await page.route('**/api/v1/syllabus/plan-1/text', route => route.fulfill({ json: { pages, provider, providerAvailable: true } }));
    let posts = 0;
    await page.route('**/api/v1/syllabus/plan-1/extractions', route => {
      posts++;
      data.set(plan.id, { ...plan, authorizationRequired: false, status });
      return route.abort();
    });
    await page.goto(path);
    await authorize(page).click();
    await expect(authorize(page)).toBeDisabled();
    await page.getByRole('button', { name: 'Consultar autorização' }).click();
    await expect(page.getByRole('button', { name: 'Rever texto do plano' })).toHaveCount(status === 'concluido' ? 1 : 0);
    await expect(authorize(page)).toHaveCount(0);
    expect(posts).toBe(1);
  });
}
