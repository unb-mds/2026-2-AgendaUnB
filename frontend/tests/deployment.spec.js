import { test, expect } from '@playwright/test';

test('API outage leaves navigation usable and displays a clear error', async ({ page }) => {
  await page.route('**/api/v1/events?*', route => route.abort('connectionfailed'));
  await page.goto('/eventos');
  await expect(page.getByRole('alert')).toContainText('A API está indisponível');
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('A API está indisponível');
  await page.getByRole('navigation', { name: 'Navegação principal' })
    .getByRole('link', { name: 'Plano de Ensino' }).click();
  await expect(page).toHaveURL(/\/plano-de-ensino$/);
});

test('an HTML fallback cannot masquerade as a successful API response', async ({ page }) => {
  await page.route('**/api/v1/events?*', route => route.fulfill({ contentType: 'text/html', body: '<html>SPA fallback</html>' }));
  await page.goto('/eventos');
  await expect(page.getByRole('alert')).toContainText('A API retornou uma resposta inválida');
});
