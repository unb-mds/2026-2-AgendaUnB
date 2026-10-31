import { test, expect } from '@playwright/test';

const plan = { id: 'd79eeb53-aed8-4369-936b-156e01cc455c', disciplina: 'Métodos de Desenvolvimento de Software', fileName: 'plano-mds.pdf', semestre: 2, ano: 2026, fileSize: 12345, createdAt: '2026-10-30T15:00:00Z', status: 'pendente' };
const pdf = { name: 'plano-mds.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\nTeste de transporte multipart') };

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

async function fillUpload(page) {
  await page.getByLabel('Disciplina', { exact: true }).fill(plan.disciplina);
  await page.getByLabel('Semestre', { exact: true }).selectOption('2');
  await page.getByLabel('Ano de referência').fill('2026');
  await page.getByLabel('Selecionar PDF', { exact: true }).setInputFiles(pdf);
}

test('envio multipart autenticado, clique duplicado, recarga e estado final sem polling', async ({ page }) => {
  await setup(page);
  let uploads = 0;
  let details = 0;
  let uploadedBody;
  await page.route('**/api/v1/syllabus/upload', async route => {
    uploads++;
    expect(route.request().headers().authorization).toBe('Bearer test-token');
    expect(route.request().headers()['content-type']).toContain('multipart/form-data; boundary=');
    uploadedBody = route.request().postData();
    await new Promise(resolve => setTimeout(resolve, 300));
    await route.fulfill({ status: 202, json: plan });
  });
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => { details++; return route.fulfill({ json: { ...plan, status: 'concluido', extractedEventsCount: 3 } }); });
  await page.goto('/plano-de-ensino');
  await fillUpload(page);
  await page.getByRole('button', { name: 'Enviar para análise' }).evaluate(button => { button.click(); button.click(); });
  await expect(page.getByRole('heading', { name: 'Análise concluída' })).toBeVisible();
  expect(uploads).toBe(1);
  expect(uploadedBody).toContain('name="disciplina"');
  expect(uploadedBody).toContain('name="semestre"\r\n\r\n2');
  expect(uploadedBody).toContain('name="ano"\r\n\r\n2026');
  await expect(page).toHaveURL(new RegExp(`plano=${plan.id}`));
  await page.clock.install();
  const completed = details;
  await page.clock.fastForward(60000);
  expect(details).toBe(completed);
  await page.reload();
  await expect(page.getByText('3 avaliações encontradas.')).toBeVisible();
  expect(details).toBe(completed + 1);
});

test('paginação, erro recuperável e resultado vazio distintos de falha', async ({ page }) => {
  await setup(page, { items: [plan], total: 11, detail: { ...plan, status: 'falha', errorMessage: 'PDF protegido. Envie uma versão sem senha.' } });
  await page.goto('/plano-de-ensino');
  await page.getByRole('button', { name: `Acompanhar ${plan.disciplina}` }).click();
  await expect(page.getByRole('heading', { name: 'Não foi possível analisar o plano' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Cadastrar prazos manualmente' })).toHaveAttribute('href', '/eventos?aba=meus');
  const request = page.waitForRequest(request => request.url().includes('offset=10'));
  await page.getByRole('button', { name: 'Próxima' }).click();
  await request;
  await expect(page.getByText('Página 2 de 2', { exact: false })).toBeVisible();
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => route.fulfill({ json: { ...plan, status: 'concluido', extractedEventsCount: 0 } }));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Nenhuma avaliação encontrada' })).toBeVisible();
  await expect(page.getByText('Isso não é uma falha', { exact: false })).toBeVisible();
});

test('validação de arquivo, erro de envio preserva campos e recuperação do histórico', async ({ page }) => {
  await setup(page, { listStatus: 404 });
  await page.route('**/api/v1/syllabus/upload', route => route.fulfill({ status: 422, json: { detail: 'O PDF deve possuir no máximo 10 páginas.' } }));
  await page.goto('/plano-de-ensino');
  await expect(page.getByText('O histórico ainda não está disponível.', { exact: false })).toBeVisible();
  await page.getByLabel('Selecionar PDF', { exact: true }).setInputFiles({ name: 'imagem.png', mimeType: 'image/png', buffer: Buffer.from('image') });
  await expect(page.getByText('Escolha um arquivo no formato PDF (.pdf).')).toBeVisible();
  await fillUpload(page);
  await page.getByRole('button', { name: 'Enviar para análise' }).click();
  await expect(page.getByText('O PDF deve possuir no máximo 10 páginas.')).toBeVisible();
  await expect(page.getByLabel('Disciplina', { exact: true })).toHaveValue(plan.disciplina);
  await expect(page.getByText('plano-mds.pdf', { exact: true })).toBeVisible();
  await page.route('**/api/v1/syllabus?*', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.getByRole('button', { name: 'Atualizar', exact: true }).click();
  await expect(page.getByText('Seu próximo semestre começa aqui')).toBeVisible();
});

test('polling controlado, suspenso em segundo plano, retomado e cancelado ao sair', async ({ page }) => {
  await setup(page);
  let calls = 0;
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => { calls++; return route.fulfill({ json: { ...plan, status: 'processando' } }); });
  await page.clock.install();
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  await expect(page.getByRole('heading', { name: 'Analisando seu plano' })).toBeVisible();
  expect(calls).toBe(1);
  await page.clock.fastForward(5000);
  await expect.poll(() => calls).toBe(2);
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await page.clock.fastForward(30000);
  expect(calls).toBe(2);
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: false }); document.dispatchEvent(new Event('visibilitychange')); });
  await expect.poll(() => calls).toBe(3);
  await page.getByRole('button', { name: 'Fechar acompanhamento' }).click();
  await page.clock.fastForward(60000);
  expect(calls).toBe(3);
});

test('erro de consulta pausa polling; retry funciona; logout remove planos privados', async ({ page }) => {
  await setup(page, { items: [{ ...plan, status: 'concluido' }] });
  let calls = 0;
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => { calls++; return route.fulfill({ status: 503, json: {} }); });
  await page.clock.install();
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  await expect(page.getByText('Não foi possível atualizar os dados.', { exact: false })).toBeVisible();
  await page.clock.fastForward(60000);
  expect(calls).toBe(1);
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => route.fulfill({ json: { ...plan, status: 'concluido' } }));
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(page.getByRole('heading', { name: 'Análise concluída' })).toBeVisible();
  await expect(page.getByText('Nenhuma avaliação encontrada')).toHaveCount(0);
  await page.evaluate(() => window.dispatchEvent(new Event('test-signout')));
  await expect(page.getByRole('link', { name: 'Entrar para enviar um plano' })).toBeVisible();
  await expect(page.getByText(plan.disciplina)).toHaveCount(0);
});

for (const width of [360, 768, 1365]) {
  for (const theme of ['dark', 'light']) {
    test(`layout e teclado ${width}px ${theme}`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 1000 });
      await setup(page, { items: [{ ...plan, disciplina: 'Disciplina de nome extenso '.repeat(6), status: 'concluido' }] });
      await page.goto('/plano-de-ensino');
      if (theme === 'light') await page.getByRole('button', { name: /tema/i }).click();
      await expect(page.getByRole('heading', { name: 'Enviar plano de ensino' })).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      await page.getByLabel('Disciplina', { exact: true }).focus();
      await page.keyboard.press('Tab');
      await expect(page.getByLabel('Semestre', { exact: true })).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByLabel('Ano de referência')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByLabel('Selecionar PDF', { exact: true })).toBeFocused();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath('page.png'), fullPage: true });
    });
  }
}

test('visitante não consulta endpoints privados', async ({ page }) => {
  await setup(page, { guest: true });
  let calls = 0;
  page.on('request', request => { if (request.url().includes('/api/v1/syllabus')) calls++; });
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  await expect(page.getByRole('link', { name: 'Entrar para enviar um plano' })).toBeVisible();
  expect(calls).toBe(0);
});
