import { test, expect } from '@playwright/test';
import { makeOffer, setupSemester } from './fixtures/semester.js';

const catalog = page => page.getByRole('region', { name: 'Catálogo de turmas' });
const followedSection = page => page.getByRole('region', { name: /Suas turmas/ });
async function openCatalog(page) {
  await page.goto('/plano-de-ensino');
  if (!(await catalog(page).isVisible())) {
    await page.getByRole('button', { name: /Selecionar turmas/ }).click();
  }
}

test('vínculo persiste na recarga, abre a biblioteca e pode ser removido', async ({ page }) => {
  await setupSemester(page, { followed: [] });
  await openCatalog(page);
  const search = catalog(page).getByRole('searchbox');
  await search.fill('FGA0101');
  await search.press('Enter');
  await catalog(page).locator('summary').filter({ hasText: 'Disciplina 1' }).click();
  await catalog(page).getByRole('checkbox', { name: 'Selecionar turma 01 de Disciplina 1' }).check();
  await catalog(page).getByRole('button', { name: 'Seguir 1 turma selecionada', exact: true }).click();
  await expect(catalog(page).getByText('Turma seguida')).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: /Selecionar turmas/ }).click();
  await expect(followedSection(page).getByRole('heading', { name: 'Suas turmas (1)' })).toBeVisible();
  await followedSection(page).getByRole('link', { name: 'Ver planos da turma' }).click();
  await expect(page).toHaveURL(/oferta=class-1/);
  await expect(page.getByRole('heading', { name: 'Planos compartilhados da turma' })).toBeVisible();
  await expect(page.getByText(/Ainda não há plano compartilhado nesta oferta/)).toBeVisible();
  await page.getByRole('button', { name: /Selecionar turmas/ }).click();
  await followedSection(page).getByRole('button', { name: 'Deixar de seguir' }).click();
  await expect(followedSection(page).getByRole('heading', { name: 'Suas turmas (0)' })).toBeVisible();
});

test('primeira carga 503 recupera automaticamente; busca vazia informa o resultado', async ({ page }) => {
  await setupSemester(page, { followed: [], offers: [makeOffer(1)] });
  await page.route('**/api/v1/class-offerings/filters', route => route.fulfill({ status: 503, json: { detail: 'Carregando primeira publicação' } }));
  await page.clock.install();
  await openCatalog(page);
  await expect(catalog(page).getByRole('alert')).toContainText('Não foi possível carregar os períodos');
  await page.route('**/api/v1/class-offerings/filters', route => route.fulfill({ json: {
    periods: ['2026.2', '2026.1'], units: [
      { id: 'gama', code: 'FCTE', name: 'Faculdade de Ciências e Tecnologias em Engenharia' },
      { id: 'direito', code: 'FD', name: 'Faculdade de Direito' },
    ],
  } }));
  await page.clock.fastForward(15000);
  const period = catalog(page).getByRole('button', { name: 'Ano/Período' });
  await expect(period).toContainText('2026.2');
  await period.press('Enter');
  await catalog(page).getByRole('button', { name: '2026.1', exact: true }).press('Enter');
  const unit = catalog(page).getByRole('button', { name: 'Unidade' });
  await unit.click();
  const unitSearch = catalog(page).getByRole('searchbox', { name: 'Pesquisar unidade' });
  await expect(unitSearch).toBeFocused();
  await unitSearch.fill('inexistente');
  await expect(catalog(page).getByText('Nenhum resultado encontrado.')).toBeVisible();
  await unitSearch.fill('ciencias');
  await expect(catalog(page).getByRole('button', { name: /FCTE/ })).toBeVisible();
  await expect(catalog(page).getByRole('button', { name: /Faculdade de Direito/ })).toHaveCount(0);
  await unitSearch.fill('fcte');
  await unitSearch.press('Enter');
  await expect(unit).toContainText('FCTE');
  await expect(unitSearch).toHaveCount(0);
  await catalog(page).getByRole('searchbox').fill('inexistente');
  const request = page.waitForRequest('**/api/v1/class-offerings?*');
  await catalog(page).getByRole('button', { name: 'Buscar turmas' }).click();
  const { searchParams } = new URL((await request).url());
  expect(searchParams.get('semester')).toBe('1');
  expect(searchParams.get('unit')).toBe('gama');
  await expect(catalog(page).getByText('0 turmas encontradas')).toBeVisible();
});

test('visitante recebe convite de login sem demonstração nem acesso a planos', async ({ page }) => {
  await setupSemester(page, { guest: true });
  const calls = [];
  page.on('request', r => { if (/api\/v1\/(class-offerings|syllabus)|api.followw.app/.test(r.url())) calls.push(r.url()); });
  await page.goto('/plano-de-ensino');
  await expect(page.getByRole('heading', { name: 'Entre na sua conta para acessar planos de ensino' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Entrar na conta' })).toHaveAttribute('href', '/?auth=login');
  await expect(page.getByRole('link', { name: 'Criar conta' })).toHaveAttribute('href', '/?auth=signup');
  await expect(page.getByText(/demonstração/i)).toHaveCount(0);
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Selecionar turmas/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Buscar turmas' })).toHaveCount(0);
  expect(calls).toEqual([]);
});

for (const width of [360, 768, 1365]) for (const theme of ['dark', 'light']) {
  test(`catálogo agrupado, seleção entre buscas e layout ${width} ${theme}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    const offers = [
      { ...makeOffer(1), subject_name: 'Estruturas de Dados 1', subject_code: 'FGA0146', unit_code: 'FCTE', unit_name: 'Faculdade de Ciências e Tecnologias em Engenharia' },
      { ...makeOffer(2), subject_name: 'Estruturas de Dados 1', subject_code: 'FGA0146', class_number: '02', unit_code: 'FCTE', unit_name: 'Faculdade de Ciências e Tecnologias em Engenharia' },
      { ...makeOffer(3), subject_name: 'Estruturas de Dados', subject_code: 'CIC0090', unit_code: 'CIC', unit_name: 'Departamento de Ciência da Computação', available: false },
    ];
    await setupSemester(page, { followed: [], offers });
    await openCatalog(page);
    await page.evaluate(theme => document.body.classList.toggle('light', theme === 'light'), theme);
    await catalog(page).getByRole('button', { name: 'Buscar turmas' }).click();
    await expect(catalog(page).locator('.semester-catalog-subject')).toHaveCount(2);
    const subject = catalog(page).locator('summary').filter({ hasText: 'FGA0146' });
    await subject.focus();
    await page.keyboard.press('Enter');
    await catalog(page).getByRole('checkbox', { name: 'Selecionar turma 02 de Estruturas de Dados 1', exact: true }).check();
    await catalog(page).locator('summary').filter({ hasText: 'CIC0090' }).click();
    await expect(catalog(page).getByRole('checkbox', { name: 'Selecionar turma 01 de Estruturas de Dados', exact: true })).toBeDisabled();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ fullPage: true, path: testInfo.outputPath(`catalog-${width}-${theme}.png`) });
    const stepper = page.getByRole('navigation', { name: 'Etapas dos planos de ensino' });
    await stepper.getByRole('button', { name: /Organizar datas/ }).click();
    await stepper.getByRole('button', { name: /Selecionar turmas/ }).click();
    await expect(catalog(page).getByRole('checkbox', { name: 'Selecionar turma 02 de Estruturas de Dados 1', exact: true })).toBeChecked();
    await catalog(page).getByRole('searchbox').fill('CIC0090');
    await catalog(page).getByRole('searchbox').press('Enter');
    await expect(catalog(page).locator('.semester-catalog-subject')).toHaveCount(1);
    await expect(catalog(page).getByRole('button', { name: 'Seguir 1 turma selecionada', exact: true })).toBeVisible();
    await catalog(page).getByRole('button', { name: /Remover turma 02/ }).click();
    await expect(catalog(page).getByRole('button', { name: 'Seguir 1 turma selecionada', exact: true })).toHaveCount(0);
  });
}
