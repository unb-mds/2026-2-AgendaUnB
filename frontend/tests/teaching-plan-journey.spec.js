import { test, expect } from '@playwright/test';

async function open(page) {
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({ contentType: 'application/javascript', body: `
    export const supabase = { auth: {
      async getSession() { return { data: { session: null } }; },
      onAuthStateChange(cb) { queueMicrotask(() => cb('INITIAL_SESSION', null)); return { data: { subscription: { unsubscribe() {} } } }; }
    } };
  ` }));
  await page.goto('/plano-de-ensino');
  await expect(page.getByRole('heading', { name: 'Sua matrícula é o ponto de partida.' })).toBeVisible();
}

async function enroll(page) {
  await page.getByRole('button', { name: 'Usar PDF de exemplo' }).click();
  await page.getByRole('button', { name: 'Vincular turmas de exemplo' }).click();
  await expect(page.getByRole('heading', { name: 'Minhas turmas', exact: true })).toBeVisible();
}

test('jornada completa: matrícula, revisão parcial, edição, confirmação e agenda sem API', async ({ page }) => {
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
  await page.getByRole('button', { name: '2 Conectar planos' }).click();
  await page.getByRole('article').filter({ hasText: 'Métodos de Desenvolvimento' }).getByRole('button', { name: 'Ver avaliações' }).click();
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
  expect(requests).toEqual([]);
});

test('arquivo inválido, filtros, reset cancelável e recarga', async ({ page }) => {
  await open(page);
  await page.getByLabel('Comprovante de matrícula', { exact: true }).setInputFiles({ name: 'invalido.png', mimeType: 'image/png', buffer: Buffer.from('invalid') });
  await expect(page.getByRole('alert')).toContainText('formato PDF');
  await expect(page.getByRole('button', { name: 'Vincular turmas de exemplo' })).toBeDisabled();
  await page.getByLabel('Disciplina ou sigla').fill('calculo');
  await expect(page.locator('.tp-catalog-row')).toHaveCount(1);
  await page.getByLabel('Campus', { exact: true }).selectOption('Faculdade do Gama');
  await expect(page.getByText('Nenhuma turma corresponde aos filtros.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Limpar filtros' }).click();
  await expect(page.locator('.tp-catalog-row')).toHaveCount(5);
  await enroll(page);
  await page.getByRole('button', { name: 'Reiniciar demonstração' }).click();
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Minhas turmas', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Reiniciar demonstração' }).click();
  await page.getByRole('button', { name: 'Reiniciar', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Vincular turmas de exemplo' })).toBeDisabled();
  await enroll(page);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Sua matrícula é o ponto de partida.' })).toBeVisible();
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
