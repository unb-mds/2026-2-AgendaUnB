import { createHash } from 'node:crypto';
import { test, expect } from '@playwright/test';
import { makeOffer, makePlan, setupSemester } from './fixtures/semester.js';

const plan = makePlan(1, { status: 'pendente', authorizationRequired: true, preparedTextAvailable: true });
const provider = 'Google Gemini API';
const path = '/plano-de-ensino?plano=plan-1&etapa=3';
const pages = [{ pagina: 1, texto: 'Prova em 23/11/2026 às 14:00.' }];
const authorize = page => page.getByRole('button', { name: 'Iniciar extração', exact: true });

for (const { width, redactedCount, notice } of [
  { width: 360, redactedCount: 1, notice: 'A preparação automática mascarou 1 ocorrência de dados pessoais.' },
  { width: 1365, redactedCount: 2, notice: 'A preparação automática mascarou 2 ocorrências de dados pessoais.' },
  { width: 1365, redactedCount: 0 },
  { width: 360 },
]) {
  test(`aviso da preparação automática com contagem ${redactedCount ?? 'desconhecida'} em ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await setupSemester(page, { plans: [plan] });
    await page.route('**/api/v1/syllabus/plan-1/text', route => route.fulfill({
      json: { pages, provider, providerAvailable: true, redactedCount },
    }));
    await page.goto(path, { waitUntil: 'domcontentloaded' });
    await expect(authorize(page)).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('textbox', { name: 'Texto da página 1' })).toHaveCount(0);
    const status = page.getByRole('status').filter({ hasText: /preparação automática mascarou/ });
    if (notice) {
      await expect(status).toHaveText(notice);
    } else {
      await expect(status).toHaveCount(0);
    }
    await expect(authorize(page)).toBeEnabled();
  });
}

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
  await page.getByRole('tab', { name: 'Colar texto' }).click();
  const input = page.getByLabel('Texto do plano', { exact: true });
  const submit = page.getByRole('button', { name: 'Enviar texto e extrair', exact: true });
  await input.fill('é'.repeat(20001));
  await expect(submit).toBeDisabled();
  await expect(page.getByRole('progressbar', { name: 'Capacidade do texto usada' })).toHaveAttribute('aria-valuetext', '101% — limite excedido');
  await expect(page.getByText('Limite excedido. Reduza o texto.')).toBeVisible();
  const text = 'é'.repeat(20000);
  await input.fill(text);
  await submit.evaluate(button => { button.click(); button.click(); });
  await expect(page.getByText(/Confira seus planos antes de tentar de novo/)).toBeVisible();
  expect(posts).toEqual([{ text, offering_id: 'class-2' }]);

  await select.click();
  await page.getByRole('button', { name: /FGA0101 · Turma 01/ }).click();
  await expect(page).toHaveURL(/oferta=class-1/);
  const history = page.waitForRequest(request => {
    const url = new URL(request.url());
    return url.pathname.endsWith('/api/v1/syllabus') && url.searchParams.get('offering_id') === 'class-2';
  });
  await page.getByRole('button', { name: 'Consultar planos' }).click();
  await history;
  await expect(page).toHaveURL(/oferta=class-2/);
  await expect(page.getByRole('button', { name: 'Não encontrei o plano. Reenviar' })).toBeVisible();
});

test('prévia inválida permite tentar novamente; provedor indisponível bloqueia autorização', async ({ page }) => {
  await setupSemester(page, { plans: [plan] });
  await page.route('**/api/v1/syllabus/plan-1/text', route => route.fulfill({ json: { pages: [null] } }));
  await page.goto(path);
  await expect(page.getByRole('alert')).toContainText('O serviço retornou um texto inválido', { timeout: 15000 });
  await expect(authorize(page)).toHaveCount(0);
  await page.route('**/api/v1/syllabus/plan-1/text', route => route.fulfill({ json: { pages, provider, providerAvailable: false } }));
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(authorize(page)).toBeDisabled();
  await expect(page.getByText('A extração está indisponível no momento.')).toBeVisible();
});

test('retomar a extração autoriza o texto sanitizado e bloqueia envio duplo', async ({ page }) => {
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
  await expect(page.getByText(/Ao iniciar, você autoriza o envio do texto sanitizado/)).toBeVisible();
  expect(writes).toEqual([]);
  await authorize(page).evaluate(button => { button.click(); button.click(); });
  await expect(page.getByText('Analisando seu plano', { exact: true })).toBeVisible();
  expect(writes).toEqual([{
    pages, textHash: createHash('sha256').update(JSON.stringify(pages)).digest('hex'),
    authorize: true, reprocess: false,
  }]);
});

test('texto colado autoriza o snapshot sanitizado no próprio envio', async ({ page }) => {
  const { data } = await setupSemester(page);
  const preparedPages = [{ pagina: null, texto: 'Prova 1 em 23/11/2026.' }];
  const writes = [];
  const prepared = { ...plan, redactedCount: 1 };
  await page.route('**/api/v1/syllabus/text', route => {
    data.set(plan.id, prepared);
    return route.fulfill({ status: 202, json: prepared });
  });
  await page.route('**/api/v1/syllabus/plan-1/text', route =>
    route.fulfill({ json: { pages: preparedPages, provider, providerAvailable: true } }));
  await page.route('**/api/v1/syllabus/plan-1/extractions', route => {
    writes.push(route.request().postDataJSON());
    const next = { ...prepared, authorizationRequired: false, status: 'processando' };
    data.set(plan.id, next);
    return route.fulfill({ status: 202, json: next });
  });
  await page.goto('/plano-de-ensino?oferta=class-1');
  await page.getByRole('tab', { name: 'Colar texto' }).click();
  await page.getByLabel('Texto do plano', { exact: true }).fill(preparedPages[0].texto + ' | E-mail: pessoa@example.test');
  expect(writes).toEqual([]);
  await page.getByRole('button', { name: 'Enviar texto e extrair', exact: true }).click();
  await expect(page.getByText('Analisando seu plano', { exact: true })).toBeVisible();
  await expect(authorize(page)).toHaveCount(0);
  const notice = page.getByRole('status').filter({ hasText: 'Dados pessoais detectados foram removidos antes da análise.' });
  await expect(notice).toBeVisible();
  expect(writes).toEqual([{
    pages: preparedPages, textHash: createHash('sha256').update(JSON.stringify(preparedPages)).digest('hex'),
    authorize: true, reprocess: false,
  }]);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(notice).toBeVisible({ timeout: 15000 });
});

test('envio preserva o plano para nova tentativa quando o provedor está indisponível', async ({ page }) => {
  const { data } = await setupSemester(page);
  await page.route('**/api/v1/syllabus/text', route => {
    data.set(plan.id, plan);
    return route.fulfill({ status: 202, json: plan });
  });
  await page.route('**/api/v1/syllabus/plan-1/text', route =>
    route.fulfill({ json: { pages, provider, providerAvailable: false } }));
  const requests = [];
  await page.route('**/api/v1/syllabus/plan-1/extractions', route => {
    requests.push(route.request());
    return route.abort();
  });
  await page.goto('/plano-de-ensino?oferta=class-1');
  await page.getByRole('tab', { name: 'Colar texto' }).click();
  await page.getByLabel('Texto do plano', { exact: true }).fill(pages[0].texto);
  await page.getByRole('button', { name: 'Enviar texto e extrair', exact: true }).click();
  await expect(page.getByText('A extração está indisponível no momento.')).toBeVisible();
  await expect(authorize(page)).toBeDisabled();
  expect(requests).toEqual([]);
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
    await page.getByRole('button', { name: 'Consultar andamento' }).click();
    await expect(page.getByRole('button', { name: 'Solicitar nova análise' })).toHaveCount(status === 'concluido' ? 1 : 0);
    await expect(authorize(page)).toHaveCount(0);
    expect(posts).toBe(1);
  });
}
