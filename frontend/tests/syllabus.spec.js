import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { confirmation, makeCandidate, makeOffer, makePdf, makePlan, setupSemester } from './fixtures/semester.js';

const ready = (index, candidates) => makePlan(index, { candidates, extractedEventsCount: candidates.length });
const pendingText = index => makePlan(index, { status: 'pendente', authorizationRequired: true, preparedTextAvailable: true });
const textPayload = { pages: [{ pagina: 1, texto: 'Avaliações em 23 de novembro.' }], provider: 'Google Gemini API', providerAvailable: true };
const confirmButton = page => page.getByRole('button', { name: /Adicionar \d+ avaliaç.* à agenda/ });
const candidate = (page, title) => page.locator('.semester-candidate').filter({ has: page.getByText(title, { exact: true }) });
const files = page => page.locator('input[type=file]');
const queue = page => page.getByRole('complementary', { name: 'Seus planos' });
async function chooseUploadClass(page, index) {
  const picker = queue(page).getByRole('button', { name: 'Turma dos planos' });
  await picker.click();
  await queue(page).getByRole('button', { name: `Disciplina ${index}`, exact: true }).click();
  await expect(picker).toContainText(`Disciplina ${index}`);
  await expect(page).toHaveURL(new RegExp(`oferta=class-${index}(?:&|$)`));
}

test('oito planos e 60 avaliações: vínculo, upload concorrente, autorização específica e confirmação por plano', async ({ page }) => {
  test.setTimeout(60000);
  const offers = Array.from({ length: 8 }, (_, i) => makeOffer(i + 1));
  const { data, memberships } = await setupSemester(page, { offers, followed: [] });
  const confirmations = [];
  const running = new Set();
  let maxUploads = 0;
  let duringProcessing = false;
  let authorized = 0;
  let thirdUploadStarted;
  const overlappingUpload = new Promise(resolve => { thirdUploadStarted = resolve; });
  const started = performance.now();
  const hash = createHash('sha256').update(JSON.stringify(textPayload.pages)).digest('hex');
  await page.route('**/api/v1/syllabus/upload', async route => {
    const body = route.request().postData();
    expect(route.request().headers().authorization).toBe('Bearer test-token');
    const index = Number(body.match(/filename="plano-(\d+)\.pdf"/)[1]);
    expect(body).toContain(`class-${index}`);
    expect(memberships.has(`class-${index}`)).toBe(true);
    duringProcessing ||= [...data.values()].some(plan => plan.status === 'processando');
    running.add(index);
    maxUploads = Math.max(maxUploads, running.size);
    // Mantenha o segundo envio aberto até o terceiro chegar, mesmo em CI lento.
    if (index === 2) await overlappingUpload;
    if (index === 3) thirdUploadStarted();
    await new Promise(resolve => setTimeout(resolve, 650));
    const plan = pendingText(index);
    data.set(plan.id, plan);
    running.delete(index);
    return route.fulfill({ status: 202, json: plan });
  });
  await page.route('**/api/v1/syllabus/*/text', route => route.fulfill({ json: textPayload }));
  await page.route('**/api/v1/syllabus/*/extractions', route => {
    const id = route.request().url().split('/').at(-2);
    const body = route.request().postDataJSON();
    expect(body).toMatchObject({ pages: textPayload.pages, textHash: hash, authorize: true });
    authorized++;
    const plan = { ...data.get(id), authorizationRequired: false, status: 'processando' };
    data.set(id, plan);
    return route.fulfill({ status: 202, json: plan });
  });
  await page.route('**/api/v1/syllabus/*/confirm', route => {
    const id = route.request().url().split('/').at(-2);
    const { candidates } = route.request().postDataJSON();
    const plan = data.get(id);
    expect(candidates.every(item => plan.candidates.some(saved => saved.id === item.candidateId))).toBe(true);
    expect(candidates.every(item => item.all_day && item.start_date === '2026-11-23')).toBe(true);
    confirmations.push({ key: route.request().headers()['idempotency-key'], count: candidates.length });
    return route.fulfill({ json: confirmation(plan, candidates) });
  });

  await page.goto('/plano-de-ensino');
  const catalog = page.getByRole('region', { name: 'Catálogo de turmas' });
  await catalog.getByRole('button', { name: 'Buscar turmas', exact: true }).click();
  for (const offer of offers) {
    await catalog.locator('summary').filter({ hasText: offer.subject_name }).click();
    await catalog.getByRole('checkbox', { name: `Selecionar turma 01 de ${offer.subject_name}`, exact: true }).check();
  }
  await catalog.getByRole('button', { name: /Seguir 8/ }).click();
  await expect(catalog.getByText('8 turmas adicionadas à sua lista.')).toBeVisible();
  await page.getByRole('button', { name: 'Avançar para organizar datas' }).first().click();

  await chooseUploadClass(page, 1);
  await files(page).setInputFiles(makePdf(1));
  await expect(queue(page).getByRole('button', { name: 'Processando: plano-1.pdf', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Iniciar extração', exact: true })).toHaveCount(0);

  for (let index = 2; index <= 8; index++) {
    await chooseUploadClass(page, index);
    await files(page).setInputFiles(makePdf(index));
  }
  await expect.poll(() => maxUploads).toBe(2);
  await page.getByRole('button', { name: 'Ver todos os planos' }).click();
  for (let index = 2; index <= 8; index++) {
    await expect(queue(page).getByRole('button', { name: `Processando: plano-${index}.pdf`, exact: true })).toBeVisible();
  }
  expect(authorized).toBe(8);
  expect(duringProcessing).toBe(true);
  expect(maxUploads).toBe(2);

  for (let index = 1; index <= 8; index++) data.set(`plan-${index}`, ready(index, Array.from({ length: index <= 4 ? 8 : 7 }, (_, i) => makeCandidate(`${index}-${i}`))));
  await expect(confirmButton(page)).toHaveText(/Adicionar 60 avaliações/, { timeout: 10000 });
  await confirmButton(page).evaluate(button => { button.click(); button.click(); });
  await expect(page.getByText('60 adicionadas')).toBeVisible();
  expect(confirmations).toHaveLength(8);
  expect(new Set(confirmations.map(operation => operation.key)).size).toBe(8);
  expect(confirmations.reduce((sum, operation) => sum + operation.count, 0)).toBe(60);
  await test.info().attach('tempo da jornada simulada', { body: String(Math.round(performance.now() - started)), contentType: 'text/plain' });
});

test('corrige ambiguidade e aplica ou desfaz horário em lote, preservando escolhas fora do filtro', async ({ page }) => {
  await setupSemester(page, { offers: [makeOffer(1), makeOffer(2)], plans: [
    ready(1, [makeCandidate('A', { type: 'prova' }), makeCandidate('B'), makeCandidate('C', {
      ambiguous: true, ambiguousFields: ['data'], suggestedDate: null,
    })]),
    ready(2, [makeCandidate('D')]),
  ] });
  await page.goto('/plano-de-ensino');
  await expect(confirmButton(page)).toHaveText(/Adicionar 3 avaliações/);
  await expect(candidate(page, 'Avaliação A')).toContainText('horário da turma');
  await expect(candidate(page, 'Avaliação C').getByRole('checkbox')).toBeDisabled();
  await page.getByRole('button', { name: /Precisam de atenção/ }).click();
  await expect(page.getByText(/3 fora do filtro/)).toBeVisible();
  const row = candidate(page, 'Avaliação C');
  await row.getByRole('button', { name: 'Ver detalhes de Avaliação C' }).press('Enter');
  await expect(row).toContainText('Página 2');
  await expect(row.getByRole('button', { name: 'Usar estes dados' })).toBeDisabled();
  await row.getByLabel('Data', { exact: true }).fill('2026-12-01');
  await row.getByRole('button', { name: 'Usar estes dados' }).click();
  await expect(confirmButton(page)).toHaveText(/Adicionar 4 avaliações/);
  await page.getByRole('button', { name: 'Todas', exact: true }).click();
  await candidate(page, 'Avaliação D').getByRole('checkbox').uncheck();
  await page.getByText('Editar em lote', { exact: true }).click();
  await page.getByRole('combobox', { name: 'Campo', exact: true }).selectOption('time');
  await page.getByLabel('Novo valor').fill('17:30');
  await page.getByRole('button', { name: 'Aplicar a 3 avaliações' }).click();
  await expect(candidate(page, 'Avaliação A')).toContainText('17:30');
  await page.getByRole('button', { name: 'Desfazer edição em lote' }).click();
  await expect(candidate(page, 'Avaliação A')).toContainText('horário da turma');
  await page.getByLabel('Filtrar avaliações por turma').selectOption('class-2');
  await expect(page.getByText(/3 fora do filtro/)).toBeVisible();
});

for (const committed of [true, false]) {
  test(`resultado parcial e reconciliação de resposta perdida (gravado: ${committed})`, async ({ page }) => {
    const a = ready(1, [makeCandidate('A')]);
    const b = ready(2, [makeCandidate('B')]);
    const { data } = await setupSemester(page, { plans: [a, b], offers: [makeOffer(1), makeOffer(2)] });
    const calls = [];
    await page.route('**/api/v1/syllabus/*/confirm', route => {
      const id = route.request().url().split('/').at(-2);
      const key = route.request().headers()['idempotency-key'];
      const { candidates } = route.request().postDataJSON();
      calls.push({ id, key, candidates });
      if (id === a.id && calls.filter(item => item.id === id).length === 1) {
        if (committed) data.set(id, { ...a, candidates: [{ ...a.candidates[0], status: 'confirmado' }] });
        return route.abort();
      }
      return route.fulfill({ json: confirmation(data.get(id), candidates) });
    });
    await page.goto('/plano-de-ensino');
    await confirmButton(page).click();
    await expect(page.getByText('1 na agenda')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Verificar confirmação' })).toBeVisible();
    await page.getByRole('button', { name: 'Verificar confirmação' }).click();
    await expect(page.getByText('2 adicionadas')).toBeVisible();
    if (committed) expect(calls).toHaveLength(2);
    else expect(calls[2]).toEqual(calls[0]);
  });
}

test('arquivo inválido não bloqueia outro e oferta retirada não pode ser associada', async ({ page }) => {
  const offers = [makeOffer(1), { ...makeOffer(2), available: false }];
  await setupSemester(page, { offers });
  let calls = 0;
  await page.route('**/api/v1/syllabus/upload', route => {
    calls++;
    return route.fulfill({ status: 400, json: { detail: 'O PDF não contém texto extraível.' } });
  });
  await page.goto('/plano-de-ensino');
  const addPlans = queue(page).getByRole('button', { name: 'Enviar PDF e extrair' });
  await expect(addPlans).toBeDisabled();
  await expect(queue(page).getByText('Selecione uma turma antes de enviar um plano.')).toBeVisible();
  await files(page).setInputFiles(makePdf(2));
  await expect(queue(page).getByText('plano-2.pdf', { exact: true })).toHaveCount(0);
  await chooseUploadClass(page, 2);
  await expect(addPlans).toBeDisabled();
  await chooseUploadClass(page, 1);
  await files(page).setInputFiles([{ name: 'invalido.txt', mimeType: 'text/plain', buffer: Buffer.from('a') }, makePdf(1)]);
  await expect(queue(page).getByRole('alert').first()).toContainText('Escolha um arquivo no formato PDF');
  await expect(queue(page).getByText('O PDF não contém texto extraível.')).toBeVisible();
  await expect(queue(page).getByText('plano-1.pdf', { exact: true })).toBeVisible();
  await queue(page).getByRole('tab', { name: 'Colar texto' }).click();
  await expect(queue(page).getByRole('textbox', { name: 'Texto do plano' })).toBeVisible();
  expect(calls).toBe(1);
});

test('seletor de Seus planos troca o histórico e o destino do PDF entre semestres', async ({ page }) => {
  const offers = [makeOffer(1), { ...makeOffer(2), semester: 1 }];
  await setupSemester(page, { offers, plans: [makePlan(1), makePlan(2, { semestre: 1 })] });
  await page.route('**/api/v1/syllabus/upload', route => route.fulfill({ status: 400, json: { detail: 'PDF de teste' } }));
  await page.goto('/plano-de-ensino');
  await page.getByRole('button', { name: 'Semestre', exact: true }).click();
  await page.getByRole('button', { name: '2026.2', exact: true }).click();
  await expect(page).toHaveURL(/periodo=2026.2/);
  const picker = queue(page).getByRole('button', { name: 'Turma dos planos' });
  await picker.click();
  await queue(page).getByRole('button', { name: 'Disciplina 2', exact: true }).click();
  await expect(picker).toHaveText(/^Disciplina 2/);
  await expect(page).toHaveURL(/oferta=class-2/);
  await expect(queue(page).getByText('plano-2.pdf', { exact: true })).toBeVisible();
  await expect(queue(page).getByText('plano-1.pdf', { exact: true })).toHaveCount(0);
  const request = page.waitForRequest('**/api/v1/syllabus/upload');
  await files(page).setInputFiles({ ...makePdf(3), name: 'teste.pdf' });
  expect((await request).postData()).toContain('class-2');
});

test('rascunho atravessa navegação, mas é limpo ao trocar de conta; recarga recupera histórico', async ({ page }) => {
  const plan = ready(1, [makeCandidate('privada')]);
  await setupSemester(page, { plans: [plan] });
  await page.goto('/plano-de-ensino');
  await candidate(page, 'Avaliação privada').getByRole('button', { name: 'Ver detalhes de Avaliação privada' }).click();
  await page.getByLabel('Título', { exact: true }).fill('Rascunho particular');
  await page.locator('.semester-review').getByRole('link', { name: 'Meus Eventos' }).click();
  await page.goBack();
  await expect(candidate(page, 'Rascunho particular')).toBeVisible();
  await page.reload();
  await expect(candidate(page, 'Avaliação privada')).toBeVisible();
  await page.route('**/api/v1/syllabus?*', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('test-switch-account', { detail: 'outro-aluno' })));
  await expect(page.getByText('Avaliação privada', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'As datas aparecem aqui' })).toBeVisible();
});

test('polling suspenso em segundo plano e retomado sem recriar edições', async ({ page }) => {
  const plan = makePlan(1, { status: 'processando' });
  const { data } = await setupSemester(page, { plans: [plan] });
  let reads = 0;
  await page.route('**/api/v1/syllabus/plan-1', route => {
    reads++;
    return route.fulfill({ json: data.get(plan.id) });
  });
  await page.clock.install();
  await page.goto('/plano-de-ensino');
  await expect.poll(() => reads).toBe(1);
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await page.clock.fastForward(10000);
  expect(reads).toBe(1);
  data.set(plan.id, ready(1, [makeCandidate('final')]));
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { value: false }); document.dispatchEvent(new Event('visibilitychange')); });
  await expect(confirmButton(page)).toBeEnabled();
  await page.clock.fastForward(10000);
  expect(reads).toBe(2);
});

test('links antigos de oferta, plano e página abrem o contexto correto', async ({ page }) => {
  const plan = ready(1, [makeCandidate('A')]);
  await setupSemester(page, { plans: [plan], offers: [makeOffer(1), makeOffer(2)] });
  await page.goto('/plano-de-ensino?oferta=class-1&plano=plan-1&etapa=3&pagina=2');
  await expect(page.getByRole('heading', { name: 'Disciplina 1' })).toBeVisible();
  await expect(page.getByText('Página 2', { exact: true })).toBeVisible();
  await expect(confirmButton(page)).toBeEnabled();
  await page.goto('/plano-de-ensino?oferta=class-2&plano=plan-1&etapa=3');
  await expect(page.getByText('Este plano pertence a outra oferta.', { exact: false })).toBeVisible();
  await expect(confirmButton(page)).toHaveCount(0);
});

for (const width of [360, 768, 1365]) for (const theme of ['light', 'dark']) {
  test(`painel ${width}px tema ${theme}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    await setupSemester(page, { plans: [
      ready(1, [makeCandidate('A', { title: 'Apresentação do projeto de Métodos de Desenvolvimento de Software' }),
        makeCandidate('B', { ambiguous: true, suggestedDate: null })]),
      pendingText(2),
      makePlan(3, { status: 'processando' }),
    ] });
    await page.goto('/plano-de-ensino');
    if (theme === 'light') await page.getByRole('button', { name: /tema/i }).click();
    await expect(confirmButton(page)).toBeEnabled();
    expect(await page.evaluate(() => {
      if (document.documentElement.scrollWidth <= innerWidth) return [];
      return Array.from(document.querySelectorAll('body *')).filter(el => el.getBoundingClientRect().right > innerWidth + 1)
        .slice(0, 15).map(el => `${el.tagName}.${el.className} em ${el.parentElement?.className}`);
    })).toEqual([]);
    if (width < 820) {
      await page.getByRole('button', { name: 'Recolher fila de planos' }).press('Enter');
      await expect(page.getByRole('button', { name: 'Extrair avaliações: plano-2.pdf' })).toBeHidden();
      await expect(page.getByRole('button', { name: 'Enviar PDF e extrair' })).toBeVisible();
      await page.getByRole('button', { name: 'Expandir fila de planos' }).press('Enter');
    }
    await page.screenshot({ path: info.outputPath('semester.png'), fullPage: true });
  });
}

test('resultado vazio, falha e resposta malformada são distinguíveis e recuperáveis', async ({ page }) => {
  const failed = makePlan(1, { status: 'falha', errorMessage: 'Provedor temporariamente indisponível.' });
  const empty = ready(2, []);
  const invalid = ready(3, [null]);
  const { data } = await setupSemester(page, { plans: [failed, empty, invalid] });
  await page.goto('/plano-de-ensino');
  await queue(page).getByRole('button', { name: 'Falha: plano-1.pdf' }).click();
  await expect(page.getByText(failed.errorMessage)).toBeVisible();
  await queue(page).getByRole('button', { name: 'Sem avaliações: plano-2.pdf' }).click();
  await expect(page.getByText('A análise terminou sem encontrar avaliações.')).toBeVisible();
  await expect(queue(page).getByText('Resposta das avaliações inválida.', { exact: false })).toBeVisible();
  data.set(invalid.id, ready(3, [makeCandidate('recuperada')]));
  await queue(page).getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(candidate(page, 'Avaliação recuperada')).toBeVisible();
});
