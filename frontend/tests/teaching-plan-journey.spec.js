import { test, expect } from '@playwright/test';

async function open(page, { account = () => null } = {}) {
  await page.clock.setFixedTime(new Date('2026-11-10T18:00:00Z'));
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({ contentType: 'application/javascript', body: `
    const id = ${JSON.stringify(account())};
    const session = id ? { user: { id, email: 'demo@example.test' }, access_token: 'test-token' } : null;
    export const supabase = { auth: {
      async getSession() { return { data: { session } }; },
      onAuthStateChange(cb) { queueMicrotask(() => cb('INITIAL_SESSION', session)); return { data: { subscription: { unsubscribe() {} } } }; }
    }, from() { return { select() { return this; }, eq() { return this; }, async single() { return { data: null }; } }; } };
  ` }));
  await page.route('**/api/v1/me/**', route => route.fulfill({ json: [] }));
  await page.goto('/plano-de-ensino');
  await expect(page.getByRole('heading', { name: 'Catálogo de turmas' })).toBeVisible();
}

const mine = page => page.getByRole('region', { name: 'Minhas turmas' });
const catalog = page => page.getByRole('region', { name: 'Catálogo de turmas' });

async function search(page, query, period = '2026.2') {
  await page.getByLabel('Ano/Período').selectOption(period);
  const input = page.getByRole('searchbox', { name: 'Matéria ou professor' });
  await input.fill(query);
  await input.press('Enter');
}

async function enroll(page) {
  await search(page, 'FGA0108');
  await catalog(page).getByRole('button', { name: /Seguir turma: Métodos/ }).click();
  await mine(page).getByRole('button', { name: /Enviar plano: Métodos/ }).click();
  await expect(page.getByRole('heading', { name: /Plano de Métodos/ })).toBeVisible();
}

test('jornada completa: seleção de turmas, revisão parcial, edição, confirmação e agenda sem API', async ({ page }) => {
  const requests = [];
  page.on('request', r => { if (r.url().includes('/api/v1/')) requests.push(r.url()); });
  await open(page);
  await expect(page.getByRole('button', { name: '2 Conectar planos' })).toBeDisabled();
  await enroll(page);
  await page.getByRole('button', { name: 'Usar PDF de exemplo' }).click();
  await page.getByRole('button', { name: 'Simular extração' }).dblclick();
  await expect(page.getByRole('heading', { name: 'A IA sugere. Você confere.' })).toBeVisible();
  await page.getByRole('checkbox', { name: 'Incluir Prova 1', exact: true }).check();
  await page.getByRole('button', { name: 'Confirmar e vincular plano' }).click();
  await expect(page.getByLabel('Fuso UTC').first()).toBeFocused();
  await page.getByLabel('Fuso UTC').first().fill('-03:00');
  await page.getByLabel('Título').first().fill('Prova revisada');
  await page.getByRole('button', { name: '1 Selecionar turmas' }).click();
  await mine(page).getByRole('button', { name: /Ver plano: Métodos/ }).click();
  await expect(page.getByLabel('Título').first()).toHaveValue('Prova revisada');
  await page.getByRole('checkbox', { name: 'Conferi as avaliações e a turma de destino.' }).check();
  await page.getByRole('button', { name: 'Confirmar e vincular plano' }).click();
  await page.getByRole('checkbox', { name: /Métodos de Desenvolvimento/ }).check();
  await page.getByRole('button', { name: 'Simular envio para Meus Eventos' }).click();
  await expect(page.getByText('1 avaliação(ões) incluída(s) na prévia local. Sua agenda real não foi alterada.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Simular envio para Meus Eventos' })).toBeDisabled();
  await expect(page.locator('.tp-calendar-events li')).toHaveCount(1);
  await expect(page.locator('.tp-calendar-events')).toContainText('Prova revisada');
  await page.getByLabel('Mês da prévia').selectOption('2026-12');
  await expect(page.getByText('Nenhuma avaliação na prévia deste mês.')).toBeVisible();
  await page.getByRole('button', { name: '1 Selecionar turmas' }).click();
  await mine(page).getByRole('button', { name: /Deixar de seguir: Métodos/ }).click();
  await expect(mine(page).getByRole('heading', { name: 'Minhas turmas' })).toBeFocused();
  await page.getByRole('button', { name: '4 Enviar à agenda' }).click();
  await expect(page.locator('.tp-calendar-events')).toContainText('Prova revisada');
  expect(requests).toEqual([]);
});

test('período obrigatório, busca por teclado, homônimas e reset cancelável para visitante', async ({ page }) => {
  await open(page);
  await expect(page.locator('input[type=file]')).toHaveCount(0);
  await expect(page.getByLabel('Ano/Período').locator('option:not([disabled])')).toHaveText([
    '2026.2 — Semestre atual', '2027.1 — Próximo semestre',
  ]);
  await page.getByRole('button', { name: 'Buscar turmas' }).click();
  await expect(page.getByLabel('Ano/Período')).toBeFocused();
  await search(page, 'calculo 03');
  await expect(catalog(page).getByRole('heading', { name: 'Cálculo 1' })).toHaveCount(2);
  await search(page, 'lucia nunes');
  await expect(catalog(page).getByRole('heading', { name: 'Cálculo 1' })).toHaveCount(1);
  await search(page, 'sem resultados');
  await expect(page.getByText('Nenhuma turma encontrada em 2026.2.', { exact: false })).toBeVisible();
  await search(page, 'MAT0025');
  await catalog(page).getByRole('button', { name: /Seguir turma: Cálculo 1, MAT0025/ }).press('Enter');
  await page.getByRole('button', { name: 'Reiniciar demonstração' }).click();
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await expect(mine(page).getByRole('button', { name: /Ver plano: Cálculo 1, MAT0025/ })).toBeVisible();
  await page.getByRole('button', { name: 'Reiniciar demonstração' }).click();
  await page.getByRole('button', { name: 'Reiniciar', exact: true }).click();
  await expect(mine(page).getByText('Você ainda não segue turmas')).toBeVisible();
  await enroll(page);
  await page.reload();
  await expect(mine(page).getByText('Você ainda não segue turmas')).toBeVisible();
});

test('persistência local após login separa contas e abre o plano do período escolhido', async ({ page }) => {
  let id = 'student-a';
  await open(page, { account: () => id });
  await expect(page.getByText(/ficam salvas neste navegador para a sua conta/)).toBeVisible();
  for (const period of ['2026.2', '2027.1']) {
    await search(page, 'MAT0025', period);
    await catalog(page).getByRole('button', { name: /Seguir turma: Cálculo 1, MAT0025/ }).click();
  }
  await page.reload();
  await expect(mine(page).getByRole('button', { name: /Ver plano:.*2026.2/ })).toBeVisible();
  await mine(page).getByRole('button', { name: /Enviar plano:.*2027.1/ }).click();
  await expect(page.getByRole('region', { name: 'Plano de Cálculo 1' })).toContainText('MAT0025 · Turma 03 · Darcy Ribeiro · 2027.1');
  await expect(page.getByRole('button', { name: 'Simular extração' })).toBeDisabled();
  await page.getByRole('button', { name: '1 Selecionar turmas' }).click();
  await mine(page).getByRole('button', { name: /Deixar de seguir:.*2027.1/ }).click();
  id = 'student-b';
  await page.reload();
  await expect(mine(page).getByText('Você ainda não segue turmas')).toBeVisible();
  id = 'student-a';
  await page.reload();
  await expect(mine(page).getByRole('button', { name: /Ver plano:.*2026.2/ })).toBeVisible();
  await expect(mine(page).getByRole('button', { name: /Enviar plano:.*2027.1/ })).toHaveCount(0);
});

test('falha do catálogo permite tentar novamente; cache válido permite seguir apenas ofertas disponíveis', async ({ page }) => {
  await page.route(url => url.pathname === '/src/lib/classCatalogDemo.js' && !url.searchParams.has('fixture'),
    route => route.fulfill({ contentType: 'application/javascript', body: `
      export { catalogPeriods, demoOffering, offeringLabel, searchOfferings, loadDemoFollows, saveDemoFollows } from '/src/lib/classCatalogDemo.js?fixture';
      import { loadDemoCatalog as fixture } from '/src/lib/classCatalogDemo.js?fixture';
      let attempts = 0;
      export async function loadDemoCatalog(periods) {
        if (attempts++ === 0) throw new Error('Catalog unavailable');
        const data = await fixture(periods);
        if (attempts > 2) return { ...data, items: [] };
        return { ...data, stale: true, sourceUpdatedAt: '2026-11-07T18:00:00Z' };
      }
    ` }));
  await open(page);
  await expect(page.getByRole('alert')).toContainText('Não foi possível carregar o catálogo');
  await expect(page.getByRole('link', { name: 'Cadastrar um compromisso manualmente' })).toHaveAttribute('href', '/eventos?aba=meus');
  await catalog(page).getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(page.getByText('Catálogo desatualizado', { exact: true })).toBeVisible();
  await expect(page.getByText(/07\/11\/2026/)).toBeVisible();
  await search(page, 'FGA0108');
  await catalog(page).getByRole('button', { name: /Seguir turma: Métodos/ }).click();
  await expect(mine(page).getByRole('button', { name: /Enviar plano: Métodos/ })).toBeVisible();
  await page.getByRole('button', { name: 'Atualizar catálogo' }).click();
  await expect(mine(page).getByText('Oferta indisponível para envio')).toBeVisible();
  await expect(mine(page).getByRole('button', { name: /Enviar plano: Métodos/ })).toHaveCount(0);
  await page.getByRole('button', { name: '2 Conectar planos' }).click();
  await expect(page.getByRole('heading', { name: 'Oferta indisponível para envio' })).toBeVisible();
  await expect(page.locator('input[type=file]')).toHaveCount(0);
});

for (const width of [360, 768, 1365]) for (const light of [false, true]) {
  test(`layout ${width} ${light ? 'claro' : 'escuro'} em todas as etapas`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await open(page);
    if (light) await page.getByRole('button', { name: /tema/i }).click();
    const capture = async step => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: testInfo.outputPath(`step-${step}.png`), fullPage: true });
    };
    await search(page, 'calculo');
    await catalog(page).getByRole('button', { name: /Seguir turma: Cálculo 1, MAT0025/ }).click();
    if (width <= 820) {
      await page.getByRole('button', { name: 'Ir para Minhas turmas' }).press('Enter');
      await expect(mine(page).getByRole('heading', { name: 'Minhas turmas' })).toBeFocused();
    }
    await capture(1);
    await enroll(page);
    await capture(2);
    await page.getByRole('button', { name: 'Usar PDF de exemplo' }).click();
    await page.getByRole('button', { name: 'Simular extração' }).click();
    await expect(page.getByRole('heading', { name: 'A IA sugere. Você confere.' })).toBeVisible();
    await capture(3);
    await page.getByRole('button', { name: '4 Enviar à agenda' }).click();
    await capture(4);
  });
}
