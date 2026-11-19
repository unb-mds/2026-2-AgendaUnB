import { expect, test } from '@playwright/test';

const reminders = [
  { id: 'private-reminder', title: 'Revisão para a prova', event_kind: 'personal', starts_at: '2030-04-21T03:00:00Z', read_at: null },
  { id: 'public-reminder', title: 'Palestra de extensão', event_kind: 'saved_public', starts_at: '2030-04-21T17:00:00Z', read_at: null },
];

async function mockAccounts(page) {
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({
    contentType: 'text/javascript',
    body: `
      let notify;
      let account = sessionStorage.getItem('reminderAccount') ?? 'ana';
      const session = () => account ? { user: { id: account }, access_token: account } : null;
      function changeAccount(next) {
        account = next;
        sessionStorage.setItem('reminderAccount', account);
        notify(account ? 'SIGNED_IN' : 'SIGNED_OUT', session());
      }
      window.changeReminderAccount = changeAccount;
      export const supabase = {
        auth: {
          onAuthStateChange(callback) {
            notify = callback;
            queueMicrotask(() => callback('INITIAL_SESSION', session()));
            return { data: { subscription: { unsubscribe() {} } } };
          },
          async getSession() { return { data: { session: session() } }; },
          async signOut() { changeAccount(''); },
        },
        from(table) {
          return {
            select() { return this; }, eq() { return this; }, order() { return this; },
            async single() { return { data: { papel: account === 'ana' ? 'professor' : 'student' } }; },
            async range() {
              return { data: [{ id: 'moderation-1', tipo: 'submissao', titulo_evento: 'Sugestão de Bruno',
                criado_em: '2030-04-20T17:00:00Z' }], count: 1 };
            },
            async is() { return { count: 1 }; },
          };
        },
      };
      export const createRecoveryClient = () => supabase;
    `,
  }));
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
}

test('a leitura persiste no retorno e a troca de conta limpa a central', async ({ page }) => {
  await mockAccounts(page);
  const items = reminders.map(item => ({ ...item }));
  await page.route('**/api/v1/me/reminders?*', route => route.fulfill({
    json: route.request().headers().authorization === 'Bearer ana' ? items : [],
  }));
  await page.route('**/api/v1/me/reminders/private-reminder/read', route => {
    expect(route.request().method()).toBe('PUT');
    expect(route.request().headers().authorization).toBe('Bearer ana');
    items[0].read_at = '2030-04-20T15:00:00Z';
    return route.fulfill({ json: { id: items[0].id, read_at: items[0].read_at } });
  });

  await page.goto('/');
  const bell = page.getByRole('button', { name: /^Notificações/ });
  const panel = page.getByRole('dialog', { name: 'Notificações' });
  await bell.click();
  const privateRow = panel.getByRole('listitem').filter({ hasText: 'Revisão para a prova' });
  await expect(privateRow.getByText('Não lido', { exact: true })).toBeVisible();
  await expect(privateRow.locator('time')).toContainText('00:00');
  await expect(panel.getByText('Palestra de extensão')).toBeVisible();
  await privateRow.getByRole('button', { name: 'Marcar como lido' }).click();
  await expect(privateRow.getByText('Lido', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await expect(bell).toHaveCount(0);
  await page.evaluate(() => window.changeReminderAccount('ana'));
  await bell.click();
  await expect(privateRow.getByText('Lido', { exact: true })).toBeVisible();

  await page.evaluate(() => window.changeReminderAccount('bruno'));
  await expect(panel).toHaveCount(0);
  await bell.click();
  await expect(panel.getByText('Nenhum lembrete nesta página.')).toBeVisible();
  await expect(privateRow).toHaveCount(0);
  await panel.getByRole('button', { name: /^Sugestões/ }).click();
  await expect(panel.getByText('Sugestão de Bruno')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(panel).toHaveCount(0);
  await expect(bell).toBeFocused();
});

test('a central pagina lembretes e oferece recuperação de erro em tela pequena', async ({ page }) => {
  await mockAccounts(page);
  await page.setViewportSize({ width: 360, height: 760 });
  const items = Array.from({ length: 21 }, (_, index) => ({
    ...reminders[0],
    id: `reminder-${index + 1}`,
    title: `Compromisso ${index + 1}`,
  }));
  let firstRequest = true;
  await page.route('**/api/v1/me/reminders?*', async route => {
    if (firstRequest) {
      firstRequest = false;
      return route.fulfill({ status: 503, json: { detail: 'Falha temporária' } });
    }
    const query = new URL(route.request().url()).searchParams;
    const offset = Number(query.get('offset'));
    return route.fulfill({ json: items.slice(offset, offset + Number(query.get('limit'))) });
  });

  await page.goto('/');
  await page.getByRole('button', { name: /^Notificações/ }).click();
  const panel = page.getByRole('dialog', { name: 'Notificações' });
  await expect(panel.getByRole('alert')).toContainText('Falha temporária');
  await panel.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(panel.getByRole('listitem')).toHaveCount(20);
  const bounds = await panel.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(360);
  await panel.getByRole('button', { name: 'Próxima' }).click();
  await expect(panel.getByRole('listitem')).toHaveCount(1);
  await expect(panel.getByText('Compromisso 21')).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Próxima' })).toBeDisabled();
});
