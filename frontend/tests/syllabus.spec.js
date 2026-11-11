import { test, expect } from '@playwright/test';

const plan = { offeringId: '70000000-0000-4000-8000-000000000071', id: 'd79eeb53-aed8-4369-936b-156e01cc455c', disciplina: 'Métodos de Desenvolvimento de Software', fileName: 'plano-mds.pdf', semestre: 2, ano: 2026, fileSize: 12345, createdAt: '2026-10-30T15:00:00Z', status: 'pendente' };
const pdf = { name: 'plano-mds.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\nTeste de transporte multipart') };
const candidate = { id: 'candidate-a', title: 'Prova de integração', type: 'prova', status: 'pendente', ambiguous: true, ambiguousFields: ['data'], suggestedDate: null, suggestedTime: null, sourcePage: 2, sourceExcerpt: 'Prova: data a definir.', versionId: 'version-a' };

test('PDF sem texto mantém arquivo e oferece texto e organização manual', async ({ page }) => {
  await setup(page);
  await page.route('**/api/v1/syllabus/upload', route => route.fulfill({ status: 400,
    json: { detail: 'O PDF não contém texto extraível. Use uma versão digital ou envie o cronograma por texto.' } }));
  await page.goto(`/plano-de-ensino?oferta=${plan.offeringId}&etapa=2`);
  await fillUpload(page);
  await page.getByRole('button', { name: 'Preparar PDF para revisão' }).click();
  await expect(page.getByRole('alert')).toContainText('O PDF não contém texto extraível.');
  await expect(page.getByRole('link', { name: 'Cadastrar prazos manualmente' })).toBeVisible();
  await expect(page.getByLabel('Texto do plano', { exact: true })).toBeVisible();
  await expect(page.getByText(pdf.name, { exact: true })).toBeVisible();
});

for (const state of ['sem vínculo', 'vínculo de outra oferta', 'oferta retirada', 'resposta inválida', 'falha de rede']) {
  test(`envio bloqueado por URL direta: ${state}`, async ({ page }, testInfo) => {
    await setup(page, { items: [plan], total: 1 });
    await page.setViewportSize({ width: 360, height: 1000 });
    const writes = [];
    page.on('request', request => { if (request.method() === 'POST') writes.push(request.url()); });
    await page.route('**/api/v1/me/class-offerings', route => {
      if (state === 'falha de rede') return route.abort();
      const items = state === 'vínculo de outra oferta' ? [{ id: 'other' }] : [];
      return route.fulfill({ json: state === 'resposta inválida' ? [] : { items } });
    });
    if (state === 'oferta retirada') {
      await page.route(`**/api/v1/class-offerings/${plan.offeringId}`, route => route.fulfill({ json: { id: plan.offeringId, available: false } }));
    }
    await page.goto(`/plano-de-ensino?oferta=${plan.offeringId}&etapa=2`);
    if (['resposta inválida', 'falha de rede'].includes(state)) {
      await expect(page.getByText('Não foi possível verificar a oferta e suas turmas seguidas.')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Tentar novamente', exact: true })).toBeVisible();
    } else {
      await expect(page.getByText(/Selecione uma oferta disponível que sua conta segue/)).toBeVisible();
      await expect(page.getByRole('button', { name: `Acompanhar ${plan.disciplina}` })).toBeVisible();
    }
    await expect(page.locator('input[type=file]')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Preparar texto para revisão' })).toHaveCount(0);
    expect(writes).toEqual([]);
    if (state === 'sem vínculo') await page.screenshot({ path: testInfo.outputPath('offering-blocked.png'), fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test('recarga verifica vínculo removido e bloqueia novo envio mantendo histórico', async ({ page }) => {
  await setup(page, { items: [plan] });
  await page.goto(`/plano-de-ensino?oferta=${plan.offeringId}&etapa=2`);
  await expect(page.getByRole('button', { name: 'Preparar texto para revisão' })).toBeVisible();
  await page.route('**/api/v1/me/class-offerings', route => route.fulfill({ json: { items: [] } }));
  await page.reload();
  await expect(page.getByText(/Selecione uma oferta disponível que sua conta segue/)).toBeVisible();
  await expect(page.getByRole('button', { name: `Acompanhar ${plan.disciplina}` })).toBeVisible();
  await expect(page.locator('input[type=file]')).toHaveCount(0);
});

async function openCheckedReview(page, path = `/plano-de-ensino?plano=${plan.id}`) {
  const first = page.getByRole('group', { name: 'Avaliação 1', exact: true });
  await page.goto(path);
  await first.getByLabel('Decisão').selectOption('selected');
  await first.getByLabel('Título').fill('Trabalho corrigido');
  await first.getByLabel('Tipo').selectOption('trabalho');
  await first.getByLabel('Data', { exact: false }).fill('2026-12-01');
  await first.getByLabel('Horário').fill('14:30');
  await first.getByLabel('Fuso UTC').fill('-03:00');
  const confirm = page.getByRole('button', { name: 'Confirmar e importar' });
  await expect(confirm).toBeDisabled();
  await page.getByRole('button', { name: 'Conferir selecionados' }).click();
  if (!path.includes('oferta=')) await expect(confirm).toBeEnabled();
  return { first, confirm };
}

test('jornada recebida da main confirma pela revisão integrada e atualiza o calendário', async ({ page }) => {
  await setup(page, { detail: { ...plan, status: 'concluido', candidates: [candidate] } });
  let confirmed = false;
  let agendaReads = 0;
  const event = { id: 'event-merged', title: 'Trabalho corrigido', starts_at: '2026-12-01T14:30:00-03:00',
    category: 'Acadêmico', origin: { syllabusId: plan.id, candidateId: candidate.id } };
  await page.route(`**/api/v1/syllabus/${plan.id}/confirm`, route => {
    expect(route.request().postDataJSON().candidates[0].candidateId).toBe(candidate.id);
    confirmed = true;
    return route.fulfill({ json: { syllabusId: plan.id, events: [event] } });
  });
  await page.route('**/api/v1/me/events', route => {
    agendaReads++;
    return route.fulfill({ json: confirmed ? [event] : [] });
  });
  const { first, confirm } = await openCheckedReview(page, `/plano-de-ensino?oferta=${plan.offeringId}&plano=${plan.id}&etapa=3`);
  const acknowledgement = page.getByRole('checkbox', { name: 'Conferi as avaliações e a turma de destino.' });
  await expect(confirm).toBeDisabled();
  await acknowledgement.check();
  await expect(confirm).toBeEnabled();
  await first.getByLabel('Título').fill('Trabalho corrigido novamente');
  await expect(acknowledgement).not.toBeChecked();
  await page.getByRole('button', { name: 'Conferir selecionados' }).click();
  await acknowledgement.check();
  await confirm.click();
  await expect(page).toHaveURL(/etapa=4/);
  await expect(page.getByRole('heading', { name: 'Leve as datas para o seu calendário.' })).toBeVisible();
  await expect.poll(() => agendaReads).toBe(1);
  await expect(page.getByRole('link', { name: 'Abrir Meus Eventos' })).toBeVisible();
});

for (const [width, theme] of [[360, 'light'], [1365, 'dark']]) {
  test(`confirmação envia somente selecionados e bloqueia clique duplicado em ${width}px ${theme}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await setup(page, { detail: { ...plan, status: 'concluido', candidates: [candidate, { ...candidate, id: 'other' }] } });
    const posts = [];
    await page.route(`**/api/v1/syllabus/${plan.id}/confirm`, async route => {
      expect(route.request().headers().authorization).toBe('Bearer test-token');
      posts.push(route.request().postDataJSON());
      await route.fulfill({ json: { syllabusId: plan.id, events: [{ id: 'event-a', origin: { syllabusId: plan.id, candidateId: candidate.id } }] } });
    });
    const { first, confirm } = await openCheckedReview(page);
    if (theme === 'light') await page.getByRole('button', { name: /tema/i }).click();
    const agenda = page.getByRole('link', { name: 'Abrir Meus Eventos' });
    await expect(agenda).toHaveCount(0);
    expect(posts).toHaveLength(0);
    await confirm.evaluate(button => { button.click(); button.click(); });
    const feedback = page.getByText('1 avaliação confirmada na agenda.');
    await expect(feedback).toBeVisible();
    await expect(agenda).toBeVisible();
    await expect(first.getByLabel('Decisão')).toBeDisabled();
    await expect(page.getByRole('group', { name: 'Avaliação 2', exact: true }).getByLabel('Decisão')).toBeEnabled();
    expect(posts).toEqual([{ candidates: [{ candidateId: candidate.id, title: 'Trabalho corrigido',
      startsAt: '2026-12-01T14:30-03:00', category: 'Acadêmico', description: `Tipo de avaliação: Trabalho\n\n${candidate.sourceExcerpt}` }] }]);
    await feedback.evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath('confirmation.png') });
  });
}

test('abrir Meus Eventos consulta a agenda e exibe a avaliação persistida uma vez', async ({ page }) => {
  await setup(page, { detail: { ...plan, status: 'concluido', candidates: [candidate] } });
  let storedEvent = null;
  let agendaReads = 0;
  let confirmations = 0;
  await page.route('**/api/v1/me/events', route => {
    expect(route.request().headers().authorization).toBe('Bearer test-token');
    agendaReads++;
    return route.fulfill({ json: storedEvent ? [storedEvent] : [] });
  });
  await page.route(`**/api/v1/syllabus/${plan.id}/confirm`, route => {
    confirmations++;
    const [item] = route.request().postDataJSON().candidates;
    storedEvent = {
      id: 'event-a', title: item.title, starts_at: item.startsAt, category: item.category, description: item.description,
      origin: { syllabusId: plan.id, candidateId: item.candidateId },
    };
    return route.fulfill({ json: { syllabusId: plan.id, events: [storedEvent] } });
  });

  await page.goto('/eventos?aba=meus');
  await expect(page.getByRole('heading', { name: 'Nenhum evento encontrado' })).toBeVisible();
  expect(agendaReads).toBe(1);

  const { confirm } = await openCheckedReview(page);
  await confirm.click();
  const agenda = page.getByRole('link', { name: 'Abrir Meus Eventos' });
  await agenda.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/eventos\?aba=meus$/);
  await expect(page.getByRole('heading', { name: 'Trabalho corrigido', exact: true })).toHaveCount(1);
  expect(agendaReads).toBe(2);

  await page.reload();
  await expect(page.getByRole('heading', { name: 'Trabalho corrigido', exact: true })).toHaveCount(1);
  expect(agendaReads).toBe(3);
  expect(confirmations).toBe(1);
});

for (const mode of ['resposta perdida', 'conflito']) {
  test(`${mode} exige consultar o estado salvo antes de tentar confirmar de novo`, async ({ page }) => {
    await setup(page, { detail: { ...plan, status: 'concluido', candidates: [candidate] } });
    const posts = [];
    await page.route(`**/api/v1/syllabus/${plan.id}/confirm`, route => {
      posts.push(route.request().postDataJSON());
      if (posts.length > 1) return route.fulfill({ json: { syllabusId: plan.id, events: [] } });
      return mode === 'conflito' ? route.fulfill({ status: 409, json: { detail: 'Confirmação concorrente.' } }) : route.abort();
    });
    const { first, confirm } = await openCheckedReview(page);
    await confirm.click();
    const refresh = page.getByRole('button', { name: 'Atualizar avaliações' });
    await expect(refresh).toBeEnabled();
    await expect(confirm).toBeDisabled();
    expect(posts).toHaveLength(1);
    const status = mode === 'conflito' ? 'pendente' : 'confirmado';
    await page.route(`**/api/v1/syllabus/${plan.id}`, route => route.fulfill({ json: { ...plan, status: 'concluido', candidates: [{ ...candidate, status }] } }));
    await refresh.click();
    if (status === 'confirmado') {
      await expect(page.getByText(/1 de 1 itens do último envio constam como confirmados/)).toBeVisible();
      await expect(page.getByRole('link', { name: 'Abrir Meus Eventos' })).toBeVisible();
      await expect(first.getByLabel('Decisão')).toBeDisabled();
      expect(posts).toHaveLength(1);
    } else {
      await expect(first.getByLabel('Título')).toHaveValue('Trabalho corrigido');
      await expect(confirm).toBeDisabled();
      await page.getByRole('button', { name: 'Conferir selecionados' }).click();
      await confirm.click();
      await expect(page.getByText(/0 de 1 eventos disponíveis na agenda/)).toBeVisible();
      expect(posts).toEqual([posts[0], posts[0]]);
    }
  });
}

test('revisão real permite corrigir e selecionar em lote sem gravar eventos', async ({ page }) => {
  await setup(page, { detail: { ...plan, status: 'concluido', candidates: [candidate,
    { ...candidate, id: 'b', title: 'Trabalho', type: 'trabalho' },
    { ...candidate, id: 'c', status: 'confirmado' }, { ...candidate, id: 'd', status: 'descartado' },
    { ...candidate, id: 'e', status: 'desconhecido' }] } });
  const writes = [];
  page.on('request', request => { if (request.method() !== 'GET' && request.url().includes('/api/')) writes.push(request.url()); });
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  const first = page.getByRole('group', { name: 'Avaliação 1', exact: true });
  const second = page.getByRole('group', { name: 'Avaliação 2', exact: true });
  await expect(first.getByLabel('Fuso UTC')).toHaveValue('');
  await second.getByLabel('Decisão').selectOption('discarded');
  await page.getByRole('button', { name: 'Selecionar pendentes' }).click();
  await expect(first.getByLabel('Decisão')).toHaveValue('selected');
  await expect(second.getByLabel('Decisão')).toHaveValue('discarded');
  for (const index of [3, 4, 5]) await expect(page.getByRole('group', { name: `Avaliação ${index}`, exact: true }).getByLabel('Decisão')).toBeDisabled();
  await page.getByRole('button', { name: 'Conferir selecionados' }).click();
  await expect(first.getByLabel('Data', { exact: false })).toBeFocused();
  await first.getByLabel('Título').fill('Trabalho corrigido');
  await first.getByLabel('Tipo', { exact: false }).selectOption('trabalho');
  await first.getByLabel('Data', { exact: false }).fill('2026-12-01');
  await first.getByLabel('Horário').fill('14:30');
  await first.getByLabel('Fuso UTC').fill('-03:00');
  await page.getByRole('button', { name: 'Conferir selecionados' }).click();
  await expect(page.getByText('Campos conferidos. Nenhum evento foi salvo na agenda.')).toBeVisible();
  await first.getByLabel('Título').fill('ab');
  await expect(page.getByText('Campos conferidos. Nenhum evento foi salvo na agenda.')).toHaveCount(0);
  await page.getByRole('button', { name: 'Conferir selecionados' }).click();
  await expect(first.getByLabel('Título')).toBeFocused();
  await page.getByRole('button', { name: 'Limpar seleção' }).click();
  await expect(first.getByLabel('Título')).toHaveValue('ab');
  await expect(first.getByLabel('Decisão')).toHaveValue('pending');
  await page.reload();
  await expect(first.getByLabel('Título')).toHaveValue(candidate.title);
  await expect(first.getByLabel('Decisão')).toHaveValue('pending');
  expect(writes).toEqual([]);
});

test('candidatos da API: origem, estados, recarga, troca de plano e saída da conta', async ({ page }) => {
  await setup(page, { detail: { ...plan, status: 'concluido', candidates: [candidate, { ...candidate, id: 'b', title: 'Trabalho confirmado', status: 'confirmado', sourcePage: null }] } });
  const writes = [];
  page.on('request', request => { if (request.method() !== 'GET' && request.url().includes('/api/')) writes.push(request.url()); });
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  const review = page.getByRole('region', { name: 'Revisar avaliações' });
  await expect(review).toContainText(candidate.title);
  await expect(review).toContainText('Página 2');
  await expect(review).toContainText(candidate.sourceExcerpt);
  await expect(review).toContainText('Requer conferência: data');
  await expect(review).toContainText('Sem referência de página');
  await expect(review).toContainText('Confirmado');
  await page.reload();
  await expect(review).toContainText(candidate.title);
  await page.route('**/api/v1/syllabus/other-plan', route => route.fulfill({ json: { ...plan, id: 'other-plan', status: 'concluido', candidates: [] } }));
  await page.goto('/plano-de-ensino?plano=other-plan');
  await expect(review).toContainText('terminou sem avaliações');
  await expect(page.getByText(candidate.title, { exact: true })).toHaveCount(0);
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  await expect(review).toContainText(candidate.title);
  await page.evaluate(() => window.dispatchEvent(new Event('test-signout')));
  await expect(page.getByText(candidate.title, { exact: true })).toHaveCount(0);
  expect(writes).toEqual([]);
});

test('resposta inválida de candidatos permite recuperação sem exibir lista vazia', async ({ page }) => {
  await setup(page, { detail: { ...plan, status: 'concluido', candidates: [null] } });
  await page.goto(`/plano-de-ensino?plano=${plan.id}`);
  await expect(page.getByText('Resposta das avaliações inválida. Tente consultar novamente.')).toBeVisible();
  await page.route(`**/api/v1/syllabus/${plan.id}`, route => route.fulfill({ json: { ...plan, status: 'concluido', candidates: [candidate] } }));
  await page.getByRole('button', { name: 'Tentar novamente', exact: true }).click();
  await expect(page.getByRole('heading', { name: candidate.title })).toBeVisible();
});

for (const width of [360, 1365]) for (const theme of ['dark', 'light']) {
  test(`candidatos legíveis ${width}px ${theme}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await setup(page, { detail: { ...plan, status: 'concluido', candidates: [{ ...candidate, sourceExcerpt: '<script>alert(1)</script> ' + 'TextoSemEspacos'.repeat(30) }] } });
    await page.goto(`/plano-de-ensino?plano=${plan.id}`);
    if (theme === 'light') await page.getByRole('button', { name: /tema/i }).click();
    const review = page.getByRole('region', { name: 'Revisar avaliações' });
    await expect(review).toContainText('<script>alert(1)</script>');
    await review.evaluate(element => element.scrollIntoView({ block: 'start' }));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath('candidates.png') });
  });
}

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
  await page.route('**/api/v1/me/class-offerings', route => route.fulfill({ json: { items: [{ id: plan.offeringId }] } }));
}

async function fillUpload(page) {
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
  await page.goto('/plano-de-ensino?modo=envios&oferta=70000000-0000-4000-8000-000000000071');
  await fillUpload(page);
  await page.getByRole('button', { name: 'Preparar PDF para revisão' }).evaluate(button => { button.click(); button.click(); });
  await expect(page.getByRole('heading', { name: 'Análise concluída' })).toBeVisible();
  expect(uploads).toBe(1);
  expect(uploadedBody).toContain('name="offering_id"');
  expect(uploadedBody).toContain('70000000-0000-4000-8000-000000000071');
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
  await page.goto('/plano-de-ensino?modo=envios&oferta=70000000-0000-4000-8000-000000000071');
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
  await page.goto('/plano-de-ensino?modo=envios&oferta=70000000-0000-4000-8000-000000000071');
  await expect(page.getByText('O histórico ainda não está disponível.', { exact: false })).toBeVisible();
  await page.getByLabel('Selecionar PDF', { exact: true }).setInputFiles({ name: 'imagem.png', mimeType: 'image/png', buffer: Buffer.from('image') });
  await expect(page.getByText('Escolha um arquivo no formato PDF (.pdf).')).toBeVisible();
  await fillUpload(page);
  await page.getByRole('button', { name: 'Preparar PDF para revisão' }).click();
  await expect(page.getByText('O PDF deve possuir no máximo 10 páginas.')).toBeVisible();
  await expect(page.getByRole('heading', { name: plan.disciplina }).first()).toBeVisible();
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
  await expect(page.getByText('Catálogo de demonstração', { exact: true })).toBeVisible();
  await expect(page.getByText(plan.disciplina)).toHaveCount(0);
});

for (const width of [360, 768, 1365]) {
  for (const theme of ['dark', 'light']) {
    test(`layout e teclado ${width}px ${theme}`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 1000 });
      await setup(page, { items: [{ ...plan, disciplina: 'Disciplina de nome extenso '.repeat(6), status: 'concluido' }] });
      await page.goto('/plano-de-ensino?modo=envios&oferta=70000000-0000-4000-8000-000000000071');
      if (theme === 'light') await page.getByRole('button', { name: /tema/i }).click();
      await expect(page.getByRole('heading', { name: 'Enviar plano de ensino' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Revisar avaliações' })).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      await page.getByLabel('Selecionar PDF', { exact: true }).focus();
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
  await expect(page.getByText('Catálogo de demonstração', { exact: true })).toBeVisible();
  expect(calls).toBe(0);
});

test('revisão aparece na rota real, explica limites e acompanha abertura e fechamento', async ({ page }) => {
  await setup(page, { items: [plan], detail: { ...plan, status: 'concluido', extractedEventsCount: 3 } });
  let confirmations = 0;
  page.on('request', request => { if (request.url().includes('/confirm')) confirmations++; });
  await page.goto('/plano-de-ensino?modo=envios&oferta=70000000-0000-4000-8000-000000000071');
  const review = page.getByRole('region', { name: 'Revisar avaliações' });
  await expect(review).toContainText('Abra um plano');
  await page.getByText('O que poderei revisar?', { exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText(/Somente as avaliações selecionadas entram na agenda/)).toBeVisible();
  await page.getByRole('button', { name: `Acompanhar ${plan.disciplina}` }).click();
  await expect(review).toContainText('os detalhes das avaliações ainda não estão disponíveis');
  await expect(page.getByRole('button', { name: 'Conferir selecionados' })).toHaveCount(0);
  await page.reload();
  await expect(review).toContainText('os detalhes das avaliações ainda não estão disponíveis');
  await page.getByRole('button', { name: 'Fechar acompanhamento' }).click();
  await expect(review).toContainText('Abra um plano');
  expect(confirmations).toBe(0);
});

for (const [status, count, text] of [
  ['pendente', null, 'aguarda processamento'],
  ['processando', null, 'análise está em andamento'],
  ['falha', null, 'análise deste plano falhou'],
  ['concluido', 0, 'terminou sem avaliações'],
  ['concluido', null, 'detalhes das avaliações ainda não estão disponíveis'],
  ['desconhecido', null, 'identificar o estado da análise'],
]) {
  test(`disponibilidade da revisão: ${status}, contagem ${count}`, async ({ page }) => {
    await setup(page, { detail: { ...plan, status, extractedEventsCount: count } });
    await page.goto(`/plano-de-ensino?plano=${plan.id}`);
    await expect(page.getByRole('region', { name: 'Revisar avaliações' })).toContainText(text);
  });
}
