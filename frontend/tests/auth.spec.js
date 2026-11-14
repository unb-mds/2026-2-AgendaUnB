import { expect, test } from '@playwright/test';

async function authClient(page, implementation, initialSession = null) {
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({
    contentType: 'text/javascript',
    body: `
      let notify;
      const auth = {
        onAuthStateChange(callback) {
          notify = callback;
          queueMicrotask(() => callback('INITIAL_SESSION', ${JSON.stringify(initialSession)}));
          return { data: { subscription: { unsubscribe() {} } } };
        },
        async signOut() { notify('SIGNED_OUT', null); },
        ${implementation}
      };
      export const supabase = {
        auth,
        from() { return { select() { return this }, eq() { return this }, async single() { return { data: null } } } },
      };
      export const createRecoveryClient = () => ({ auth: { ...auth,
        async signOut() { window.recoveryEnded = true; }
      } });
    `,
  }));
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
}

test('cadastro sem sessão confirma e controla intervalo de reenvio', async ({ page }) => {
  await page.clock.install();
  await authClient(page, `
    async signUp({ email, options }) {
      window.signupEmail = email;
      window.signupReturn = new URL(options.emailRedirectTo).pathname;
      return { data: { user: {}, session: null } };
    },
    async resend({ type }) {
      window.resendType = type;
      return {};
    },
  `);
  await page.goto('/?auth=signup');
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Nome completo').fill('Pessoa de teste');
  await dialog.getByLabel('E-mail').fill('PESSOA@example.com');
  const password = dialog.getByLabel('Senha', { exact: true });
  await expect(password).toHaveAttribute('autocomplete', 'new-password');
  await password.fill('Exemplo local 124!');
  await dialog.getByRole('button', { name: 'Mostrar senha', exact: true }).click();
  await expect(password).toHaveAttribute('type', 'text');
  const confirmation = dialog.getByLabel('Confirmar senha', { exact: true });
  await confirmation.fill('Exemplo local 125!');
  await dialog.getByRole('button', { name: 'Criar conta' }).click();
  await expect(dialog.getByRole('alert')).toHaveText('As senhas não coincidem.');
  await confirmation.fill('Exemplo local 124!');
  await dialog.getByRole('button', { name: 'Criar conta' }).click();
  await expect(dialog.getByRole('heading')).toHaveText('Confirme seu e-mail');
  await expect(dialog.getByLabel('E-mail')).toHaveValue('PESSOA@example.com');
  expect(await page.evaluate(() => [window.signupEmail, window.signupReturn])).toEqual(['pessoa@example.com', '/auth/retorno']);
  const resend = dialog.getByRole('button', { name: 'Reenviar confirmação' });
  await expect(resend).toBeDisabled();
  await page.clock.fastForward(61_000);
  await resend.click();
  await expect(dialog.getByRole('status')).toContainText('enviamos outro link');
  await expect(resend).toBeDisabled();
  expect(await page.evaluate(() => window.resendType)).toBe('signup');
});

test('link expirado e link reutilizado orientam a solicitar outro', async ({ page }) => {
  await authClient(page, `
    async verifyOtp() { return { error: { code: 'otp_expired', status: 403 } }; },
  `);
  await page.goto('/auth/retorno#type=email&token_hash=expired');
  await page.getByRole('button', { name: 'Confirmar e-mail' }).click();
  await expect(page.getByText('Este link de confirmação expirou', { exact: false })).toBeVisible();
  await page.getByRole('link', { name: 'Solicitar confirmação' }).click();
  await expect(page.getByRole('dialog').getByRole('heading')).toHaveText('Confirme seu e-mail');

  await page.goto('/auth/retorno#type=recovery&token_hash=already-used');
  await page.getByRole('button', { name: 'Validar link' }).click();
  await expect(page.getByRole('link', { name: 'Solicitar recuperação' })).toBeVisible();
  await expect(page.getByLabel('Nova senha', { exact: true })).toHaveCount(0);
});

test('recuperação envia link e usa sessão temporária para redefinir senha', async ({ page }) => {
  await authClient(page, `
    async resetPasswordForEmail(email, { redirectTo }) {
      window.recoveryRequest = [email, new URL(redirectTo).pathname];
      return {};
    },
    async verifyOtp({ type }) {
      window.recoveryType = type;
      return { data: { session: {} } };
    },
    async updateUser() { window.passwordUpdated = true; return {}; },
  `);
  await page.goto('/?auth=login');
  await page.getByRole('button', { name: 'Esqueci minha senha' }).click();
  await page.getByLabel('E-mail').fill('pessoa@example.com');
  await page.getByRole('button', { name: 'Enviar link' }).click();
  await expect(page.getByRole('status')).toContainText('Se houver uma conta');
  expect(await page.evaluate(() => window.recoveryRequest)).toEqual(['pessoa@example.com', '/auth/retorno']);

  await page.goto('/auth/retorno#type=recovery&token_hash=fresh');
  await expect(page).toHaveURL(/\/auth\/retorno$/);
  await page.getByRole('button', { name: 'Validar link' }).click();
  await page.getByLabel('Nova senha', { exact: true }).fill('Exemplo local 234!');
  await page.getByLabel('Confirmar nova senha', { exact: true }).fill('Exemplo local 234!');
  await page.getByRole('button', { name: 'Salvar senha' }).click();
  await expect(page.getByRole('heading', { name: 'Senha redefinida' })).toBeVisible();
  expect(await page.evaluate(() => [window.recoveryType, window.passwordUpdated, window.recoveryEnded]))
    .toEqual(['recovery', true, true]);
});

for (const mode of ['login', 'signup']) {
  test(`Google autentica sem solicitar o Calendar no fluxo ${mode}`, async ({ page }) => {
    await authClient(page, `
      async signInWithOAuth({ options }) {
        if (options.scopes || options.queryParams) throw new Error('Unexpected Calendar consent');
        return { data: { url: options.redirectTo + '?code=test-code' } };
      },
      async exchangeCodeForSession(code) {
        if (code !== 'test-code') return { error: { code: 'bad_code' } };
        const session = {
          user: { id: 'google-user', email: 'pessoa@example.com' },
          access_token: 'fake-supabase-token',
        };
        notify('SIGNED_IN', session);
        return { data: { session } };
      },
    `);
    await page.goto(`/?auth=${mode}`);
    await expect(page.getByRole('dialog').getByRole('checkbox')).toHaveCount(0);
    await page.getByRole('button', { name: 'Continuar com Google' }).click();
    await expect(page).toHaveURL(/\/eventos$/);
    await page.getByRole('button', { name: 'Sair da conta' }).click();
    await expect(page.getByRole('button', { name: 'Sair da conta' })).toHaveCount(0);
  });
}

test('recusa do Google oferece retorno para o login', async ({ page }) => {
  await authClient(page, '');
  await page.goto('/auth/retorno#error=access_denied');
  await expect(page.getByRole('heading', { name: 'Não foi possível entrar com Google' })).toBeVisible();
  await page.getByRole('link', { name: 'Voltar para entrar' }).click();
  await expect(page.getByRole('button', { name: 'Continuar com Google' })).toBeVisible();
});

function calendarSession(method) {
  const claims = Buffer.from(JSON.stringify({ amr: [{ method }] })).toString('base64url');
  return {
    access_token: `header.${claims}.signature`,
    user: { id: 'google-user', email: 'pessoa@example.com', identities: [{ provider: 'google' }] },
  };
}

test('Google com permissão exporta apenas os eventos selecionados', async ({ page }) => {
  const session = calendarSession('oauth');
  await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`, session);
  await page.route('**/api/v1/me/events', route => route.fulfill({
    json: [{ id: 'exam', title: 'Prova de MDS', starts_at: '2026-11-13T17:00:00Z' }],
  }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({
    json: [{ id: 'talk', title: 'Palestra', starts_at: '2026-11-13T18:00:00Z' }],
  }));
  await page.route('**/api/v1/me/google-calendar/connection', route => route.fulfill({ json: { connected: true } }));
  await page.route('**/api/v1/me/google-calendar/exports', route => {
    expect(route.request().postDataJSON()).toEqual({ events: [{ id: 'exam', kind: 'personal' }] });
    return route.fulfill({ json: [{ id: 'exam', kind: 'personal', status: 'exported' }] });
  });

  await page.goto('/eventos?aba=meus');
  const exportButton = page.getByRole('button', { name: 'Exportar para o Google Agenda' });
  const viewSelector = page.getByRole('group', { name: 'Visualização dos eventos' });
  await expect(exportButton).toBeVisible();
  const [action, selector] = await Promise.all([exportButton.boundingBox(), viewSelector.boundingBox()]);
  expect(action.x + action.width).toBeLessThan(selector.x);
  const eventsSelector = page.locator('.btn-toggle-group').filter({
    has: page.getByRole('button', { name: 'Eventos Públicos', exact: true }),
  });
  const { height: referenceHeight } = await eventsSelector.boundingBox();
  expect(action.height).toBe(referenceHeight);
  expect(selector.height).toBe(referenceHeight);
  await expect(exportButton.locator('img')).toHaveAttribute('src', '/google-calendar-2026.svg');
  await expect.poll(() => exportButton.locator('img').evaluate(icon => icon.naturalWidth)).toBeGreaterThan(0);
  await exportButton.focus();
  await page.keyboard.press('Tab');
  await expect(viewSelector.getByRole('button', { name: 'Lista' })).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog', { name: 'Exportar para o Google Agenda' });
  await dialog.getByRole('checkbox', { name: /Prova de MDS/ }).check();
  await dialog.getByRole('button', { name: 'Exportar eventos selecionados' }).click();
  await expect(dialog.getByRole('status')).toContainText('1 evento disponível no Google Agenda.');
  await page.keyboard.press('Escape');
  await expect(exportButton).toBeFocused();
  await viewSelector.getByRole('button', { name: 'Calendário' }).click();
  const periodSelector = page.getByRole('group', { name: 'Período do calendário' });
  await expect(periodSelector).toBeVisible();
  expect((await periodSelector.boundingBox()).height).toBe(referenceHeight);
});

for (const outcome of ['denied', 'email_mismatch', 'connected']) {
  test(`Calendar mantém sessão por senha após retorno ${outcome}`, async ({ page }) => {
    const session = calendarSession('password');
    let connected = false;
    await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`, session);
    await page.route('**/api/v1/me/events', route => route.fulfill({ json: [] }));
    await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));
    await page.route('https://accounts.google.com/o/oauth2/v2/auth**', route => {
      connected = outcome === 'connected';
      return route.fulfill({
        status: 302, headers: { location: new URL(`/eventos?aba=meus&google_calendar=${outcome}`, page.url()).href },
      });
    });
    await page.route('**/api/v1/me/google-calendar/authorization', route => {
      expect(route.request().method()).toBe('POST');
      return route.fulfill({ json: { authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=simulado' } });
    });
    await page.route('**/api/v1/me/google-calendar/connection', route => {
      if (route.request().method() === 'DELETE') {
        connected = false;
        return route.fulfill({ json: { disconnected: true, revocation: 'confirmed' } });
      }
      return route.fulfill({ json: { connected } });
    });
    await page.goto('/eventos?aba=meus');
    const connect = page.getByRole('button', { name: 'Conectar Google Agenda', exact: true });
    await connect.click();
    await expect(page).toHaveURL(new RegExp(`google_calendar=${outcome}`));
    if (connected) {
      await expect(page.getByText('Google Agenda conectado.')).toBeVisible();
      await page.getByRole('button', { name: 'Desconectar Google Agenda', exact: true }).click();
      await expect(page.getByText('Google Agenda desconectado.')).toBeVisible();
      await expect(connect).toBeVisible();
    } else {
      await expect(page.getByText(outcome === 'denied' ? /não foi concedido/ : /mesmo e-mail verificado/)).toBeVisible();
    }
    await expect(page.getByRole('button', { name: 'Sair da conta' })).toBeVisible();
  });
}
