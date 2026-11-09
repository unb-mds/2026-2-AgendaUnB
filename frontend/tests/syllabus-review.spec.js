import { test, expect } from '@playwright/test';

// Harness exists only in intercepted test responses, never in the application routes.
async function openEditor(page, { light = false, empty = false } = {}) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/__review_test', route => route.fulfill({ contentType: 'text/html', body: `
    <html lang="pt-BR"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body class="${light ? 'light' : ''}"><main id="root" class="management-shell" style="padding:24px"></main>
    <script type="module">
      import RefreshRuntime from '/@react-refresh';
      RefreshRuntime.injectIntoGlobalHook(window);
      window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => type => type;
      window.__vite_plugin_react_preamble_installed__ = true;
      const { default: React } = await import('/node_modules/.vite/deps/react.js');
      const { default: ReactDOM } = await import('/node_modules/.vite/deps/react-dom_client.js');
      const { default: Editor } = await import('/src/components/SyllabusReviewEditor.jsx');
      const { createReviewDraft } = await import('/src/lib/syllabusReview.js');
      await import('/src/styles/global.css'); await import('/src/styles/management.css');
      function Harness() {
        const [value, onChange] = React.useState(() => createReviewDraft(${empty ? '[]' : "[{ id: 'a', title: 'Avaliação de Métodos de Desenvolvimento de Software', type: 'Trabalho' }]"}));
        return React.createElement(Editor, { value, onChange });
      }
      ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(Harness));
    </script></body></html>` }));
  await page.goto('/__review_test');
  await expect(page.getByRole('heading', { name: 'Revisar avaliações' })).toBeVisible();
  expect(errors).toEqual([]);
}

test('seleção, validação, teclado e descarte preservam edições sem chamar API', async ({ page }) => {
  const apiCalls = [];
  page.on('request', request => { if (request.url().includes('/api/')) apiCalls.push(request.url()); });
  await openEditor(page);
  await expect(page.getByRole('button', { name: 'Conferir selecionados' })).toBeDisabled();
  await page.getByLabel('Decisão').selectOption('selected');
  await page.getByRole('button', { name: 'Conferir selecionados' }).click();
  await expect(page.getByLabel('Data', { exact: false })).toBeFocused();
  await page.getByLabel('Título').fill('Prova revisada');
  await page.getByLabel('Data', { exact: false }).fill('2026-11-10');
  await page.getByLabel('Horário').fill('13:00');
  await page.getByLabel('Fuso UTC').fill('-03:00');
  await page.getByLabel('Decisão').selectOption('discarded');
  await expect(page.getByLabel('Título')).toBeDisabled();
  await page.getByLabel('Decisão').selectOption('selected');
  await expect(page.getByLabel('Título')).toHaveValue('Prova revisada');
  await expect(page.getByLabel('Fuso UTC')).toHaveValue('-03:00');
  await page.getByRole('button', { name: 'Conferir selecionados' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Campos conferidos. Nenhum evento foi salvo na agenda.')).toBeVisible();
  expect(apiCalls).toEqual([]);
});

for (const light of [false, true]) for (const width of [360, 768, 1365]) {
  test(`layout ${width}px tema ${light ? 'claro' : 'escuro'}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await openEditor(page, { light });
    await page.getByLabel('Título').fill('Avaliação '.repeat(30));
    await page.getByLabel('Decisão').selectOption('selected');
    await page.getByRole('button', { name: 'Conferir selecionados' }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath('review.png'), fullPage: true });
  });
}
test('lista vazia não oferece conferência', async ({ page }) => {
  await openEditor(page, { empty: true });
  await expect(page.getByText('Nenhuma avaliação disponível para revisão.')).toBeVisible();
  await expect(page.getByRole('button')).toHaveCount(0);
});
