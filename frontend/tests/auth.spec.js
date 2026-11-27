import { expect, test } from '@playwright/test';

async function authClient(page, implementation, initialSession = null, profile = null) {
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
        from() { return { select() { return this }, eq() { return this }, async single() { return { data: ${JSON.stringify(profile)} } } } },
      };
      export const createRecoveryClient = () => ({ auth: { ...auth,
        async signOut() { window.recoveryEnded = true; }
      } });
    `,
  }));
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
}

test('Conferir evento reutiliza o identificador em cliques e tentativas da mesma visualização', async ({ page }) => {
  await authClient(page, '');
  await page.addInitScript(() => { window.open = () => null; });
  const clicks = [];
  await page.route('**/api/v1/events/*', (route) => route.fulfill({ json: {
    id: new URL(route.request().url()).pathname.split('/').at(-1),
    title: 'Evento público', starts_at: '2026-11-22T17:00:00Z', external_url: 'https://example.org/oficial',
  } }));
  await page.route('**/api/v1/events/*/outbound-clicks', (route) => {
    const { click_id } = route.request().postDataJSON();
    clicks.push(click_id);
    return clicks.length === 1
      ? route.fulfill({ status: 503, json: { detail: 'Tente novamente.' } })
      : route.fulfill({ json: { outbound_clicks_count: 1, incremented: !clicks.slice(0, -1).includes(click_id) } });
  });

  await page.goto('/evento/primeiro');
  const officialLink = page.getByRole('button', { name: 'Conferir evento' });
  await officialLink.click();
  await expect(page.getByRole('alert')).toContainText('Tente novamente.');
  await officialLink.click();
  await officialLink.click();
  await expect.poll(() => clicks.length).toBe(3);
  expect(new Set(clicks).size).toBe(1);

  await page.goto('/evento/segundo');
  await officialLink.click();
  await expect.poll(() => clicks.length).toBe(4);
  expect(clicks[3]).not.toBe(clicks[0]);
});

test('professor vê ações de gestão apenas nos próprios eventos públicos', async ({ page }) => {
  const session = { access_token: 'token', user: { id: 'professor-unb', email: 'pessoa@unb.br' } };
  await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`,
    session, { id: session.user.id, papel: 'professor' });
  let ownershipRequests = 0;
  await page.route('**/api/v1/me/published-event-ids', (route) => {
    ownershipRequests += 1;
    return ownershipRequests === 1
      ? route.fulfill({ status: 503, json: { detail: 'Tente novamente.' } })
      : route.fulfill({ json: ['evento-proprio'] });
  });
  await page.route('**/api/v1/events?*', (route) => route.fulfill({ json: [
    { id: 'evento-proprio', title: 'Evento do professor', starts_at: '2026-11-22T17:00:00Z' },
    { id: 'evento-alheio', title: 'Evento de outro autor', starts_at: '2026-11-22T18:00:00Z' },
  ] }));
  await page.goto('/eventos?aba=publicos');

  const own = page.locator('.event-card').filter({ hasText: 'Evento do professor' });
  const other = page.locator('.event-card').filter({ hasText: 'Evento de outro autor' });
  const accessError = page.getByRole('alert').filter({ hasText: 'Não foi possível consultar quais eventos públicos você pode gerenciar.' });
  await expect(own).toBeVisible();
  await expect(own.getByTitle('Editar evento')).toHaveCount(0);
  await accessError.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(accessError).toHaveCount(0);
  await expect(own.getByTitle('Editar evento')).toBeVisible();
  await expect(other).toBeVisible();
  await expect(other.getByTitle('Editar evento')).toHaveCount(0);

  await page.route('**/api/v1/events', (route) => route.fulfill({ status: 201, json: {
    id: 'evento-publicado', title: 'Evento recém-publicado', starts_at: '2026-11-22T17:00:00Z',
  } }));
  await page.getByRole('button', { name: 'Criar Evento' }).click();
  const form = page.getByRole('dialog', { name: 'Novo Evento' });
  await form.getByLabel('Título do evento', { exact: false }).fill('Evento recém-publicado');
  await form.getByRole('checkbox', { name: 'Evento de dia inteiro' }).check();
  await form.getByRole('button', { name: 'dd/mm/aaaa' }).click();
  await form.getByRole('button', { name: /^1\/\d+\/\d+$/ }).click();
  await form.getByRole('button', { name: 'Salvar Evento' }).click();
  const published = page.locator('.event-card').filter({ hasText: 'Evento recém-publicado' });
  await expect(published.getByTitle('Editar evento')).toBeVisible();
  await expect(own.getByTitle('Editar evento')).toBeVisible();
  expect(ownershipRequests).toBe(2);
});

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
  await password.fill('Somenteletras');
  const confirmation = dialog.getByLabel('Confirmar senha', { exact: true });
  await confirmation.fill('Somenteletras');
  await dialog.getByRole('button', { name: 'Criar conta' }).click();
  await expect(dialog.getByRole('alert')).toHaveText('Use pelo menos 8 caracteres, com letras e números.');
  await password.fill('Exemplo local 124!');
  await dialog.getByRole('button', { name: 'Mostrar senha', exact: true }).click();
  await expect(password).toHaveAttribute('type', 'text');
  await confirmation.fill('Exemplo local 125!');
  await dialog.getByRole('button', { name: 'Criar conta' }).click();
  await expect(dialog.getByRole('alert')).toHaveText('As senhas não coincidem.');
  await confirmation.fill('Exemplo local 124!');
  await dialog.getByRole('button', { name: 'Criar conta' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Aceite os Termos de Uso');
  expect(await page.evaluate(() => window.signupEmail)).toBeUndefined();
  await dialog.getByRole('checkbox', { name: /Termos de Uso/i }).check();
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
    if (mode === 'login') {
      await expect(page.getByRole('dialog').getByRole('checkbox')).toHaveCount(0);
    } else {
      await expect(page.getByRole('dialog').getByRole('checkbox', { name: /Google Agenda|Calendar/i })).toHaveCount(0);
      await expect(page.getByRole('dialog').getByRole('checkbox')).toHaveCount(1);
    }
    await page.getByRole('button', { name: 'Continuar com Google' }).click();
    await expect(page).toHaveURL(/\/eventos$/);
    const profileButton = page.getByRole('button', { name: /Menu do perfil/i });
    await profileButton.click();
    await page.getByRole('button', { name: 'Sair da conta' }).click();
    await expect(profileButton).toHaveCount(0);
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

test('filtros acompanham a largura da busca e recolhem no celular', async ({ page }) => {
  const session = calendarSession('email');
  await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`, session);
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/google-calendar/connection', route => route.fulfill({ json: { connected: false } }));
  await page.goto('/eventos');
  const search = page.getByRole('searchbox', { name: 'Buscar eventos e comunicados' });
  const filters = page.getByRole('group', { name: 'Filtros de eventos' });
  const [input, bar] = await Promise.all([search.boundingBox(), filters.boundingBox()]);
  expect({ left: bar.x, width: bar.width }).toEqual({ left: input.x, width: input.width });

  for (const [tab, emptyMessage] of [
    ['Eventos Públicos', 'Nenhum evento público cadastrado no momento.'],
    ['Meus Eventos', 'Você ainda não possui compromissos pessoais ou eventos salvos na sua agenda.'],
  ]) {
    await page.getByRole('button', { name: tab, exact: true }).click();
    await expect(page.getByText(emptyMessage)).toBeVisible();
    await expect(page.getByRole('button', { name: /^criar evento$/i })).toHaveCount(1);
  }

  await page.setViewportSize({ width: 360, height: 820 });
  const toggle = page.getByRole('button', { name: /^Filtros/ });
  const exportButton = page.getByRole('button', { name: 'Exportar agenda', exact: true });
  const createButton = page.getByRole('button', { name: 'Criar Evento', exact: true });
  const [filterBox, exportBox, createBox] = await Promise.all([toggle, exportButton, createButton].map(button => button.boundingBox()));
  const mobileActions = [toggle, createButton];
  const personalFontSizes = await Promise.all(mobileActions.map(button => button.evaluate(el => getComputedStyle(el).fontSize)));
  await expect(exportButton).toHaveCSS('font-size', personalFontSizes[0]);
  await page.getByRole('button', { name: 'Eventos Públicos', exact: true }).click();
  await expect(exportButton).toBeHidden();
  expect(await Promise.all(mobileActions.map(button => button.boundingBox()))).toEqual([filterBox, createBox]);
  for (const [index, button] of mobileActions.entries()) {
    await expect(button).toHaveCSS('font-size', personalFontSizes[index]);
  }
  await page.getByRole('button', { name: 'Meus Eventos', exact: true }).click();

  expect(exportBox.y).toBe(filterBox.y);
  expect(createBox.y).toBe(filterBox.y);
  expect(exportBox.x).toBeGreaterThanOrEqual(filterBox.x + filterBox.width);
  expect(createBox.x).toBeGreaterThanOrEqual(exportBox.x + exportBox.width);
  expect(createBox.x + createBox.width).toBeLessThanOrEqual(360);
  expect(filterBox.width).toBeGreaterThan(85);
  expect(exportBox.width).toBeLessThanOrEqual(createBox.width * 1.1);

  await exportButton.click();
  await expect(page.getByRole('dialog', { name: 'Exportar agenda' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(exportButton).toBeFocused();
  await expect(filters).toBeHidden();
  await toggle.click();
  await filters.getByRole('button', { name: 'Filtrar por campus' }).click();
  await filters.getByRole('checkbox', { name: 'Darcy Ribeiro' }).click();
  await expect(filters.getByRole('checkbox', { name: 'Darcy Ribeiro' })).toBeChecked();
  await toggle.click();
  await expect(filters).toBeHidden();
  await expect(toggle).toContainText('1');

  await toggle.click();
  const clear = filters.getByRole('button', { name: 'Limpar Filtros', exact: true });
  const [startBox, endBox, clearBox] = await Promise.all([
    filters.getByRole('button', { name: 'Filtrar a partir da data' }).boundingBox(),
    filters.getByRole('button', { name: 'Filtrar até a data' }).boundingBox(),
    clear.boundingBox(),
  ]);
  expect(clearBox.y).toBe(endBox.y);
  expect(clearBox.x).toBeGreaterThanOrEqual(startBox.x);
  expect(clearBox.x + clearBox.width).toBeLessThanOrEqual(startBox.x + startBox.width);
  await clear.click();
  await expect(toggle.locator('.events-filter-count')).toHaveCount(0);
});

test('busca de eventos combina campos, prioriza títulos e usa o destaque dos filtros', async ({ page }) => {
  const session = calendarSession('email');
  await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`, session);
  const gama = 'Faculdade do Gama (FCTE)';
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [
    { id: 'roda', title: 'Roda de conversa', description: 'Inteligência artificial na UnB.', campus: gama, category: 'Cultura', starts_at: '2026-11-21T17:00:00Z' },
    { id: 'ia', title: 'Inteligência Artificial', campus: gama, category: 'Extensão', starts_at: '2026-11-22T17:00:00Z' },
    { id: 'inclusao', title: 'Inteligência Artificial e inclusão', campus: 'Faculdade de Ceilândia (FCTS)', starts_at: '2026-11-23T17:00:00Z' },
  ] }));
  await page.route('**/api/v1/me/events', route => route.fulfill({ json: [
    { id: 'calculo', title: 'Prova de Cálculo', location: 'Anfiteatro 12', starts_at: '2026-11-22T17:00:00Z' },
  ] }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/google-calendar/connection', route => route.fulfill({ json: { connected: false } }));
  await page.goto('/eventos?aba=publicos');

  const search = page.getByRole('searchbox', { name: 'Buscar eventos e comunicados' });
  const area = page.getByRole('button', { name: 'Filtrar por área' });
  const personalTab = page.getByRole('button', { name: 'Meus Eventos' });
  const titles = page.locator('.event-card-title');
  const neutralBorder = await search.evaluate(input => getComputedStyle(input).borderColor);
  await expect(titles).toHaveText(['Roda de conversa', 'Inteligência Artificial', 'Inteligência Artificial e inclusão']);
  await area.hover();
  const selectedBorder = await area.evaluate(async button => {
    await Promise.all(button.getAnimations().map(animation => animation.finished));
    return getComputedStyle(button).borderColor;
  });
  expect(selectedBorder).not.toBe(neutralBorder);
  await search.hover();
  await expect(search).toHaveCSS('border-color', selectedBorder);
  await area.hover();
  await personalTab.focus();
  await page.keyboard.press('Tab');
  await expect(search).toBeFocused();
  await expect(search).toHaveCSS('outline-color', selectedBorder);
  await expect(search).toHaveCSS('border-color', selectedBorder);

  await search.fill('inteligencia artificial');
  await expect(titles).toHaveText(['Inteligência Artificial', 'Inteligência Artificial e inclusão', 'Roda de conversa']);
  await search.fill('GAMA, de intelig artificial');
  await expect(titles).toHaveText(['Inteligência Artificial', 'Roda de conversa']);
  await area.click();
  await page.getByRole('checkbox', { name: 'Cultura', exact: true }).click();
  await expect(area).toHaveCSS('border-color', selectedBorder);
  await expect(search).toHaveCSS('border-color', selectedBorder);
  await expect(titles).toHaveText(['Roda de conversa']);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Limpar Filtros' }).click();
  await expect(search).toHaveCSS('border-color', neutralBorder);

  await personalTab.click();
  await search.fill('anfiteatro calc');
  await expect(titles).toHaveText(['Prova de Cálculo']);
});

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
  await page.route('**/api/v1/me/google-calendar/exports/preview', route => route.fulfill({
    json: { requires_overwrite_confirmation: false, items: [{ id: 'exam', kind: 'personal', action: 'create' }] },
  }));
  await page.route('**/api/v1/me/google-calendar/exports', route => {
    expect(route.request().postDataJSON()).toEqual({ events: [{ id: 'exam', kind: 'personal' }] });
    return route.fulfill({ json: [{ id: 'exam', kind: 'personal', status: 'exported' }] });
  });

  await page.goto('/eventos?aba=meus');
  const exportButton = page.getByRole('button', { name: 'Exportar agenda' });
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
  await expect(exportButton.locator('.material-symbols-outlined')).toHaveText('calendar_today');
  await expect(page.getByRole('button', { name: 'Desconectar Google Agenda' })).toHaveCount(0);
  await exportButton.focus();
  await page.keyboard.press('Tab');
  await expect(viewSelector.getByRole('button', { name: 'Lista' })).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog', { name: 'Exportar agenda' });
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
    await page.route('**/api/v1/me/google-calendar/connection', route => route.fulfill({ json: { connected } }));
    await page.goto('/eventos?aba=meus');
    const exportButton = page.getByRole('button', { name: 'Exportar agenda' });
    await exportButton.click();
    const dialog = page.getByRole('dialog', { name: 'Exportar agenda' });
    const connect = dialog.getByRole('button', { name: 'Conectar ao Google Agenda', exact: true });
    await connect.click();
    await expect(page).toHaveURL(new RegExp(`google_calendar=${outcome}`));
    if (connected) {
      await expect(dialog.getByRole('button', { name: 'Exportar eventos selecionados' })).toBeDisabled();
      await expect(connect).toHaveCount(0);
    } else {
      await expect(dialog.getByRole('alert')).toContainText(outcome === 'denied' ? /não foi concedido/ : /mesmo e-mail verificado/);
    }
    await page.keyboard.press('Escape');
    await expect(page).toHaveURL(/\?aba=meus$/);
    const profileButton = page.getByRole('button', { name: /Menu do perfil/i });
    await expect(profileButton).toBeVisible();
    await profileButton.click();
    await expect(page.getByRole('button', { name: 'Sair da conta' })).toBeVisible();
  });
}

test('Google Agenda exibe prévia, pede confirmação de sobrescrita, trata falha parcial com retry e exporta ICS', async ({ page }) => {
  const session = calendarSession('password');
  await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`, session);
  await page.route('**/api/v1/me/events', route => route.fulfill({
    json: [
      {
        id: '11111111-1111-4111-8111-111111111111',
        title: 'Prova 2 de Cálculo',
        description: 'Tipo de avaliação: Prova\n\nIntegrais triplas',
        starts_at: '2026-11-20T17:00:00Z',
        ends_at: '2026-11-20T18:50:00Z',
        all_day: false,
        location: 'PAT AT-011',
      },
      {
        id: '22222222-2222-4222-8222-222222222222',
        title: 'Entrega do Trabalho Final',
        description: 'Tipo de avaliação: Trabalho\n\nRelatório em PDF',
        starts_at: '2026-11-25T03:00:00Z',
        all_day: true,
        start_date: '2026-11-25',
        end_date: '2026-11-26',
      },
    ],
  }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({
    json: [
      {
        id: '33333333-3333-4333-8333-333333333333',
        title: 'Semana Universitária 2026',
        description: 'Mostra de extensão da UnB',
        starts_at: '2026-11-18T03:00:00Z',
        all_day: true,
        start_date: '2026-11-18',
        end_date: '2026-11-21',
        campus: 'Darcy Ribeiro (Plano Piloto)',
      },
    ],
  }));
  await page.route('**/api/v1/me/google-calendar/connection', route => route.fulfill({
    json: { connected: true, recovery_required: false },
  }));
  await page.route('**/api/v1/me/google-calendar/exports/preview', route => {
    const body = route.request().postDataJSON();
    return route.fulfill({
      json: {
        requires_overwrite_confirmation: body.events.some(ev => ev.id === '11111111-1111-4111-8111-111111111111'),
        items: body.events.map(ev => ({
          id: ev.id,
          kind: ev.kind,
          action: ev.id === '11111111-1111-4111-8111-111111111111' ? 'update' : 'create',
        })),
      },
    });
  });

  const exportCalls = [];
  await page.route('**/api/v1/me/google-calendar/exports', route => {
    const body = route.request().postDataJSON();
    const idempotencyKey = route.request().headers()['idempotency-key'];
    exportCalls.push({ body, idempotencyKey });
    if (exportCalls.length === 1) {
      return route.fulfill({
        json: [
          { id: '11111111-1111-4111-8111-111111111111', kind: 'personal', status: 'updated' },
          { id: '22222222-2222-4222-8222-222222222222', kind: 'personal', status: 'failed' },
          { id: '33333333-3333-4333-8333-333333333333', kind: 'saved', status: 'exported' },
        ],
      });
    }
    return route.fulfill({
      json: [
        { id: '22222222-2222-4222-8222-222222222222', kind: 'personal', status: 'exported' },
      ],
    });
  });

  await page.goto('/eventos?aba=meus');
  await page.getByRole('button', { name: 'Exportar agenda' }).click();
  const dialog = page.getByRole('dialog', { name: 'Exportar agenda' });

  await dialog.getByRole('button', { name: 'Selecionar período' }).click();
  await dialog.getByLabel('Incluir a descrição dos eventos no Google Agenda').check();
  await expect(dialog.locator('.google-calendar-preview-summary')).toContainText('2 serão criados');
  await expect(dialog.locator('.google-calendar-preview-summary')).toContainText('1 será atualizado');

  // Primeiro clique exige confirmação explícita de sobrescrita dos campos geridos
  await dialog.getByRole('button', { name: 'Exportar eventos selecionados' }).click();
  await expect(dialog.getByText('Confirmar atualização de eventos já exportados?')).toBeVisible();
  expect(exportCalls).toHaveLength(0);

  await dialog.getByRole('button', { name: 'Confirmar atualização e exportar' }).click();
  expect(exportCalls).toHaveLength(1);
  expect(exportCalls[0].body.allow_managed_field_updates).toBe(true);
  expect(exportCalls[0].body.include_description).toBe(true);
  expect(exportCalls[0].idempotencyKey).toBeTruthy();

  await expect(dialog.getByRole('status')).toContainText('2 eventos disponíveis no Google Agenda. (1 atualizado)');
  await expect(dialog.getByRole('alert')).toContainText('Alguns eventos não foram exportados.');
  await expect(dialog.getByText('Atualizado no Google Agenda')).toBeVisible();
  await expect(dialog.getByText('Falha ao exportar')).toBeVisible();

  // Somente o item falho permanece selecionado para nova tentativa
  await expect(dialog.getByRole('checkbox', { name: /Prova 2 de Cálculo/ })).not.toBeChecked();
  await expect(dialog.getByRole('checkbox', { name: /Entrega do Trabalho Final/ })).toBeChecked();

  await dialog.getByRole('button', { name: 'Tentar novamente' }).click();
  expect(exportCalls).toHaveLength(2);
  expect(exportCalls[1].idempotencyKey).toBe(exportCalls[0].idempotencyKey);
  expect(exportCalls[1].body.allow_managed_field_updates).toBe(true);
  expect(exportCalls[1].body.events).toEqual([{ id: '22222222-2222-4222-8222-222222222222', kind: 'personal' }]);
  await expect(dialog.getByRole('status')).toContainText('1 evento disponível no Google Agenda.');

  // Testa download de arquivo ICS complementar
  const downloadPromise = page.waitForEvent('download');
  await dialog.getByRole('button', { name: 'Baixar arquivo ICS (.ics)' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('agenda-unb.ics');
});

test('destino Agenda UnB removido no Google permite confirmar recriação', async ({ page }) => {
  const session = calendarSession('oauth');
  let recoveryRequired = false;
  let destinationPayload = undefined;
  await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`, session);
  await page.route('**/api/v1/me/events', route => route.fulfill({
    json: [{ id: '11111111-1111-4111-8111-111111111111', title: 'Prova de Cálculo', starts_at: '2026-11-20T17:00:00Z' }],
  }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/google-calendar/connection', route => route.fulfill({
    json: { connected: true, recovery_required: recoveryRequired },
  }));
  await page.route('**/api/v1/me/google-calendar/exports/preview', route => route.fulfill({
    json: { requires_overwrite_confirmation: false, items: [{ id: '11111111-1111-4111-8111-111111111111', kind: 'personal', action: 'create' }] },
  }));
  await page.route('**/api/v1/me/google-calendar/exports', route => {
    recoveryRequired = true;
    return route.fulfill({
      status: 409,
      json: { detail: 'Confirme o ID da agenda Agenda UnB antes de tentar exportar novamente.' },
    });
  });
  await page.route('**/api/v1/me/google-calendar/destination', route => {
    destinationPayload = route.request().postDataJSON();
    recoveryRequired = false;
    return route.fulfill({ status: 204 });
  });

  await page.goto('/eventos?aba=meus');
  await page.getByRole('button', { name: 'Exportar agenda' }).click();
  const dialog = page.getByRole('dialog', { name: 'Exportar agenda' });
  await dialog.getByRole('checkbox', { name: /Prova de Cálculo/ }).check();
  await dialog.getByRole('button', { name: 'Exportar eventos selecionados' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Confirme o ID da agenda Agenda UnB');
  await dialog.getByRole('button', { name: 'Recuperar agenda do Google' }).click();

  const recoveryDialog = page.getByRole('dialog', { name: 'Recuperar agenda do Google' });
  await expect(recoveryDialog).toBeVisible();
  await recoveryDialog.getByRole('button', { name: 'Confirmei que a agenda não existe' }).click();
  expect(destinationPayload).toEqual({ calendar_id: null });
  await expect(page.getByText('A próxima exportação criará a agenda Agenda UnB.')).toBeVisible();
});

test('cards de eventos mantêm altura padronizada mesmo com títulos, descrições e tags diferentes', async ({ page }) => {
  const session = calendarSession('email');
  await authClient(page, `async getSession() { return { data: { session: ${JSON.stringify(session)} } }; },`, session);
  await page.route('**/api/v1/me/events', route => route.fulfill({
    json: [
      { id: '11111111-1111-4111-8111-111111111111', title: 'Prova 1', starts_at: '2026-11-20T15:00:00Z' },
      { id: '22222222-2222-4222-8222-222222222222', title: 'Prova 2 com título bem mais longo para ocupar duas linhas no card', description: 'Descrição completa ocupando duas linhas para testar altura.', starts_at: '2026-11-21T15:00:00Z', location: 'Auditório Central' },
      { id: '33333333-3333-4333-8333-333333333333', title: 'Prova 3', starts_at: '2026-11-22T15:00:00Z' },
      { id: '44444444-4444-4444-8444-444444444444', title: 'Prova 4', starts_at: '2026-11-23T15:00:00Z' },
    ],
  }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({
    json: [
      {
        id: '55555555-5555-4555-8555-555555555555',
        title: 'Lançamento - Agenda UnB',
        description: 'No dia 25 de novembro acontece o lançamento exclusivo com transmissão.',
        starts_at: '2026-11-25T17:00:00Z',
        campus_id: 'fga',
        location: 'MOCAP',
        external_url: 'https://noticias.unb.br/evento',
      },
    ],
  }));
  await page.route('**/api/v1/me/google-calendar/connection', route => route.fulfill({
    json: { connected: false, recovery_required: false },
  }));

  await page.goto('/eventos?aba=meus');
  const cards = page.locator('.events-grid .event-card');
  await expect(cards).toHaveCount(5);
  const boxes = await cards.evaluateAll(elements => elements.map(el => {
    const rect = el.getBoundingClientRect();
    return { width: Math.round(rect.width), height: Math.round(rect.height) };
  }));
  expect(new Set(boxes.map(box => box.height)).size).toBe(1);
  expect(boxes[0].width).toBeGreaterThan(boxes[0].height * 1.35);
});
