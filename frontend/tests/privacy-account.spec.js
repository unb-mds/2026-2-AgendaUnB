import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

async function setupAuth(page, { session = null, profile = null, implementation = '' } = {}) {
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({
    contentType: 'text/javascript',
    body: `
      let notify;
      let currentSession = ${JSON.stringify(session)};
      const currentProfile = ${JSON.stringify(profile)};
      const auth = {
        onAuthStateChange(callback) {
          notify = callback;
          queueMicrotask(() => callback('INITIAL_SESSION', currentSession));
          return { data: { subscription: { unsubscribe() {} } } };
        },
        async getSession() { return { data: { session: currentSession } }; },
        async signOut(options) {
          window.signOutCalls = window.signOutCalls || [];
          window.signOutCalls.push(options || {});
          currentSession = null;
          notify('SIGNED_OUT', null);
        },
        ${implementation}
      };
      export const supabase = {
        auth,
        from(table) {
          return {
            select() { return this; },
            eq() { return this; },
            async single() {
              if (table === 'profiles') return { data: currentProfile };
              return { data: null };
            },
          };
        },
      };
      export const createRecoveryClient = () => ({ auth });
    `,
  }));
  await page.route('**/api/v1/events?*', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/notifications?*', route => route.fulfill({ json: { items: [], unreadCount: 0 } }));
}

function studentSession(id = 'user-1', email = 'estudante@unb.br') {
  return {
    access_token: 'test-jwt-token',
    user: { id, email, user_metadata: { nome_completo: 'Estudante Teste' } },
  };
}

const studentProfile = { id: 'user-1', nome_completo: 'Estudante Teste', papel: 'student' };

test('páginas legais publicadas e links no rodapé e autenticação', async ({ page }) => {
  await setupAuth(page);
  await page.goto('/');
  const footerNav = page.getByRole('navigation', { name: 'Informações legais' });
  await expect(footerNav.getByRole('link', { name: 'Política de Privacidade' })).toHaveAttribute('href', '/privacidade.html');
  await expect(footerNav.getByRole('link', { name: 'Termos de Uso' })).toHaveAttribute('href', '/termos.html');

  await page.goto('/?auth=login');
  const loginDialog = page.getByRole('dialog');
  await expect(loginDialog.getByRole('link', { name: 'Termos de Uso' })).toHaveAttribute('href', '/termos.html');
  await expect(loginDialog.getByRole('link', { name: 'Política de Privacidade' })).toHaveAttribute('href', '/privacidade.html');

  await page.goto('/?auth=signup');
  const signupDialog = page.getByRole('dialog');
  await expect(signupDialog.getByRole('link', { name: 'Termos de Uso' })).toHaveAttribute('href', '/termos.html');
  await expect(signupDialog.getByRole('link', { name: 'Política de Privacidade' })).toHaveAttribute('href', '/privacidade.html');

  await page.setViewportSize({ width: 360, height: 800 });
  for (const path of ['/privacidade.html', '/termos.html']) {
    const response = await page.goto(path);
    expect(response.status()).toBe(200);
    await expect(page.locator('aside.draft')).toHaveCount(0);
    await expect(page.locator('body')).toContainText('Versão 2026-11-18');
    await expect(page.locator('body')).not.toContainText('previsto para a Release 2');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(overflow).toBe(false);
  }

  await page.goto('/privacidade.html');
  const privacyText = await page.locator('main').innerText();
  expect(privacyText).toContain('calendar.app.created');
  expect(privacyText).toContain('Fernet');
  expect(privacyText).toContain('Agenda UnB');
  expect(privacyText).toContain('40.000 bytes');
  expect(privacyText).toContain('store: false');
  expect(privacyText).toContain('@vercel/analytics/react');
  expect(privacyText).toContain('Followw');
  expect(privacyText).toContain('Google Fonts');
});

test('cadastro grava aceite imediato quando há sessão ativa', async ({ page }) => {
  const acceptedImmediate = [];
  await setupAuth(page, {
    implementation: `
      async signUp({ email }) {
        const s = { user: { id: 'u-im', email }, access_token: 'tok-im' };
        currentSession = s;
        notify('SIGNED_IN', s);
        return { data: { user: s.user, session: s } };
      }
    `,
  });
  await page.route('**/api/v1/me/legal-documents', route => route.fulfill({
    json: {
      terms: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
      privacy: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
    },
  }));
  await page.route('**/api/v1/me/legal-acceptances/*', route => {
    acceptedImmediate.push({ url: route.request().url(), body: route.request().postDataJSON() });
    return route.fulfill({ status: 204 });
  });
  await page.route('**/api/v1/me/events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));

  await page.goto('/?auth=signup');
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Nome completo').fill('Pessoa Imediata');
  await dialog.getByLabel('E-mail').fill('imediata@unb.br');
  await dialog.getByLabel('Senha', { exact: true }).fill('Senha Forte 123!');
  await dialog.getByLabel('Confirmar senha', { exact: true }).fill('Senha Forte 123!');
  await dialog.getByRole('checkbox', { name: /Termos de Uso/i }).check();
  await dialog.getByRole('button', { name: 'Criar conta' }).click();

  await expect(page).toHaveURL(/\/eventos$/);
  expect(acceptedImmediate).toEqual([
    { url: expect.stringMatching(/\/api\/v1\/me\/legal-acceptances\/terms$/), body: { version: '2026-11-18' } },
    { url: expect.stringMatching(/\/api\/v1\/me\/legal-acceptances\/privacy$/), body: { version: '2026-11-18' } },
  ]);
});

test('cadastro sem sessão adia aceite sem expor e-mail e registra na confirmação', async ({ page }) => {
  const acceptedDeferred = [];
  await setupAuth(page, {
    implementation: `
      async signUp() {
        return { data: { user: { id: 'u-def' }, session: null } };
      },
      async verifyOtp() {
        const s = { user: { id: 'u-def', email: 'confirmar@unb.br' }, access_token: 'tok-def' };
        currentSession = s;
        return { data: { session: s } };
      }
    `,
  });
  await page.route('**/api/v1/me/legal-documents', route => route.fulfill({
    json: {
      terms: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
      privacy: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-11', acceptedAt: '2026-11-11T10:00:00Z', pending: true },
    },
  }));
  await page.route('**/api/v1/me/legal-acceptances/*', route => {
    acceptedDeferred.push({ url: route.request().url(), body: route.request().postDataJSON() });
    return route.fulfill({ status: 204 });
  });

  await page.goto('/?auth=signup');
  await page.getByRole('dialog').getByLabel('Nome completo').fill('Pessoa Confirmacao');
  await page.getByRole('dialog').getByLabel('E-mail').fill('confirmar@unb.br');
  await page.getByRole('dialog').getByLabel('Senha', { exact: true }).fill('Senha Forte 123!');
  await page.getByRole('dialog').getByLabel('Confirmar senha', { exact: true }).fill('Senha Forte 123!');
  await page.getByRole('dialog').getByRole('checkbox', { name: /Termos de Uso/i }).check();
  await page.getByRole('dialog').getByRole('button', { name: 'Criar conta' }).click();
  await expect(page.getByRole('dialog').getByRole('heading')).toHaveText('Confirme seu e-mail');

  const rawStorage = await page.evaluate(() => JSON.stringify(Object.entries(localStorage)));
  expect(rawStorage).not.toContain('confirmar@unb.br');
  expect(rawStorage).toContain('agenda-unb.pending-legal:');

  await page.goto('/auth/retorno#type=email&token_hash=valid');
  await page.getByRole('button', { name: 'Confirmar e-mail' }).click();
  await expect(page.getByRole('heading', { name: 'E-mail confirmado' })).toBeVisible();
  expect(acceptedDeferred).toEqual([
    { url: expect.stringMatching(/\/api\/v1\/me\/legal-acceptances\/terms$/), body: { version: '2026-11-18' } },
  ]);
});

test('gate pós-login trata atualização, conflito 409 dinâmico e adiamento sem travar teclado', async ({ page }) => {
  const session = studentSession();
  await setupAuth(page, { session, profile: studentProfile });
  await page.route('**/api/v1/me/events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));

  let docsState = {
    terms: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-11', acceptedAt: '2026-11-11T10:00:00Z', pending: true },
    privacy: { currentVersion: '2026-11-18', acceptedVersion: null, acceptedAt: null, pending: true },
  };
  let conflictOnce = true;
  const acceptedVersions = [];

  await page.route('**/api/v1/me/legal-documents', route => route.fulfill({ json: docsState }));
  await page.route('**/api/v1/me/legal-acceptances/*', route => {
    const doc = route.request().url().split('/').pop();
    const payload = route.request().postDataJSON();
    if (conflictOnce) {
      conflictOnce = false;
      docsState = {
        terms: { currentVersion: '2026-12-01', acceptedVersion: '2026-11-11', acceptedAt: '2026-11-11T10:00:00Z', pending: true },
        privacy: { currentVersion: '2026-12-01', acceptedVersion: null, acceptedAt: null, pending: true },
      };
      return route.fulfill({ status: 409, json: { detail: 'A versão informada não corresponde ao documento vigente.' } });
    }
    acceptedVersions.push({ doc, version: payload.version });
    docsState = {
      ...docsState,
      [doc]: { ...docsState[doc], acceptedVersion: payload.version, acceptedAt: '2026-12-01T12:00:00Z', pending: false },
    };
    return route.fulfill({ status: 204 });
  });

  await page.goto('/eventos');
  const gateDialog = page.getByRole('dialog', { name: /Atualização dos documentos legais/i });
  await expect(gateDialog).toBeVisible();
  await expect(gateDialog).toContainText('2026-11-18');
  await expect(gateDialog).toContainText('2026-11-11');

  // Esc closes into non-blocking banner (no keyboard trap)
  await page.keyboard.press('Escape');
  await expect(gateDialog).toBeHidden();
  const banner = page.getByRole('status', { name: 'Documentos pendentes' });
  await expect(banner).toBeVisible();
  await banner.getByRole('button', { name: 'Revisar e aceitar' }).click();
  await expect(gateDialog).toBeVisible();

  // First attempt triggers 409 and dynamically loads 2026-12-01 from API
  await gateDialog.getByRole('button', { name: 'Aceitar e continuar' }).click();
  await expect(gateDialog.getByRole('alert')).toContainText('nova versão');
  await expect(gateDialog).toContainText('2026-12-01');

  // Second attempt accepts the refreshed version dynamically
  await gateDialog.getByRole('button', { name: 'Aceitar e continuar' }).click();
  await expect(gateDialog).toBeHidden();
  expect(acceptedVersions).toEqual([
    { doc: 'terms', version: '2026-12-01' },
    { doc: 'privacy', version: '2026-12-01' },
  ]);

  await page.reload();
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('configurações exibe versões, revoga Google Agenda, exporta JSON e exclui conta com tratamento de 409 e 204', async ({ page }) => {
  await setupAuth(page);
  let unauthMeHits = 0;
  await page.route('**/api/v1/me/**', route => {
    unauthMeHits += 1;
    return route.fulfill({ status: 401, json: { detail: 'Não autenticado' } });
  });
  await page.goto('/configuracoes');
  await expect(page.getByRole('heading', { name: 'Acesso restrito' })).toBeVisible();
  expect(unauthMeHits).toBe(0);

  const session = studentSession();
  await setupAuth(page, { session, profile: studentProfile });
  await page.route('**/api/v1/me/events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/legal-documents', route => route.fulfill({
    json: {
      terms: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-18', acceptedAt: '2026-11-18T11:00:00Z', pending: false },
      privacy: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-18', acceptedAt: '2026-11-18T11:00:00Z', pending: false },
    },
  }));

  let consents = [
    { id: 'c-1', purpose: 'google_agenda', active: true, grantedAt: '2026-11-18T11:05:00Z', revokedAt: null, referenceId: 'user-1' },
  ];
  await page.route('**/api/v1/me/consents', route => route.fulfill({ json: { items: consents } }));
  await page.route('**/api/v1/me/consents/google_agenda', route => {
    expect(route.request().method()).toBe('DELETE');
    consents = [
      { id: 'c-1', purpose: 'google_agenda', active: false, grantedAt: '2026-11-18T11:05:00Z', revokedAt: '2026-11-18T12:00:00Z', referenceId: 'user-1' },
    ];
    return route.fulfill({ status: 204 });
  });

  const exportPayload = {
    exportedAt: '2026-11-18T12:00:00Z',
    profile: { id: 'user-1', email: 'estudante@unb.br', fullName: 'Estudante Teste', role: 'student' },
    personalEvents: [{ id: 'ev-1', title: 'Prova 1' }],
  };
  let failExportOnce = true;
  await page.route('**/api/v1/me/data-export', route => {
    if (failExportOnce) {
      failExportOnce = false;
      return route.fulfill({ status: 500, json: { detail: 'Erro interno inesperado.' } });
    }
    return route.fulfill({
      status: 200,
      headers: {
        'content-type': 'application/json',
        'cache-control': 'no-store',
        'content-disposition': 'attachment; filename="agenda-unb-dados.json"',
      },
      body: JSON.stringify(exportPayload),
    });
  });

  let blockAsLastAdmin = true;
  const deleteBodies = [];
  await page.route('**/api/v1/me', route => {
    expect(route.request().method()).toBe('DELETE');
    deleteBodies.push(route.request().postDataJSON());
    if (blockAsLastAdmin) {
      blockAsLastAdmin = false;
      return route.fulfill({ status: 409, json: { detail: 'O último administrador não pode excluir a própria conta.' } });
    }
    return route.fulfill({ status: 204 });
  });

  await page.goto('/eventos');
  const mainNav = page.getByRole('navigation', { name: 'Navegação principal' });
  await mainNav.getByRole('button', { name: /Menu do perfil/i }).click();
  await mainNav.getByRole('link', { name: 'Configurações' }).click();
  await expect(page).toHaveURL(/\/configuracoes$/);
  await expect(page.getByRole('heading', { name: 'Configurações e privacidade' })).toBeVisible();
  await expect(page.getByText('estudante@unb.br')).toBeVisible();
  await expect(page.getByText('Versão vigente: 2026-11-18').first()).toBeVisible();

  // Revoke Google Agenda consent
  await page.getByRole('button', { name: 'Revogar consentimento e desconectar' }).click();
  await expect(page.getByRole('status')).toContainText('Agenda UnB');

  // Share withdrawal guidance
  await expect(page.getByText(/cópias já importadas por colegas permanecem/i)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Gerenciar planos' })).toHaveAttribute('href', '/plano-de-ensino');

  // Data export error then download success
  const downloadBtn = page.getByRole('button', { name: 'Baixar meus dados' });
  await downloadBtn.click();
  await expect(page.getByRole('alert')).toContainText('Erro interno inesperado.');

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    downloadBtn.click(),
  ]);
  expect(download.suggestedFilename()).toBe('agenda-unb-dados.json');
  const downloadedJson = JSON.parse(await readFile(await download.path(), 'utf-8'));
  expect(downloadedJson).toEqual(exportPayload);

  // Account deletion: summary, validation, 409 last admin, 204 redirect + local signOut
  await expect(page.getByRole('heading', { name: 'O que é apagado' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'O que permanece' })).toBeVisible();
  await page.getByRole('button', { name: 'Excluir conta' }).click();

  const deleteDialog = page.getByRole('dialog', { name: 'Confirmar exclusão da conta' });
  const confirmInput = deleteDialog.getByLabel(/EXCLUIR MINHA CONTA/);
  await confirmInput.fill('excluir minha conta');
  await deleteDialog.getByRole('button', { name: 'Confirmar exclusão definitiva' }).click();
  await expect(deleteDialog.getByRole('alert')).toContainText('EXCLUIR MINHA CONTA');
  expect(deleteBodies).toHaveLength(0);

  await confirmInput.fill('EXCLUIR MINHA CONTA');
  await deleteDialog.getByRole('button', { name: 'Confirmar exclusão definitiva' }).click();
  await expect(deleteDialog.getByRole('alert')).toContainText('último administrador');
  expect(await page.evaluate(() => window.signOutCalls || [])).toHaveLength(0);

  await deleteDialog.getByRole('button', { name: 'Confirmar exclusão definitiva' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('status')).toContainText('Sua conta foi excluída da Agenda UnB');
  expect(deleteBodies).toEqual([
    { confirmation: 'EXCLUIR MINHA CONTA' },
    { confirmation: 'EXCLUIR MINHA CONTA' },
  ]);
  expect(await page.evaluate(() => window.signOutCalls)).toEqual([{ scope: 'local' }]);
});

test('Google Agenda exibe aviso e instruções sobre eventos na agenda Agenda UnB', async ({ page }) => {
  const session = studentSession();
  await setupAuth(page, { session, profile: studentProfile });
  await page.route('**/api/v1/me/legal-documents', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/me/events', route => route.fulfill({
    json: [{ id: 'ev-1', title: 'Seminário', starts_at: '2026-11-18T17:00:00Z' }],
  }));
  await page.route('**/api/v1/me/saved-events', route => route.fulfill({ json: [] }));

  let connected = true;
  await page.route('**/api/v1/me/google-calendar/connection', route => {
    if (route.request().method() === 'DELETE') {
      connected = false;
      return route.fulfill({ json: { disconnected: true, revocation: 'confirmed' } });
    }
    return route.fulfill({ json: { connected } });
  });

  await page.goto('/eventos?aba=meus');
  await page.getByRole('button', { name: 'Exportar para o Google Agenda' }).click();
  const exportDialog = page.getByRole('dialog', { name: 'Exportar para o Google Agenda' });
  await expect(exportDialog).toContainText('Agenda UnB');
  await exportDialog.getByText('Como excluir eventos exportados no Google Agenda').click();
  await expect(exportDialog).toContainText('calendar.google.com');
  await expect(exportDialog).toContainText('Excluir agenda');
  await page.keyboard.press('Escape');

  await page.getByRole('button', { name: 'Desconectar Google Agenda' }).click();
  await expect(page.getByText('Google Agenda desconectado.')).toBeVisible();
  await expect(page.getByText(/permanecem na agenda secundária “Agenda UnB”/i)).toBeVisible();
  await page.getByText('Como excluir eventos exportados no Google Agenda').click();
  await expect(page.getByText(/Configurações e compartilhamento/)).toBeVisible();
});

test('matriz responsiva (360px, 768px, 1365px) e temas claro/escuro sem overflow', async ({ page }) => {
  const session = studentSession();
  await setupAuth(page, { session, profile: studentProfile });
  await page.route('**/api/v1/me/legal-documents', route => route.fulfill({
    json: {
      terms: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-18', acceptedAt: '2026-11-18T11:00:00Z', pending: false },
      privacy: { currentVersion: '2026-11-18', acceptedVersion: '2026-11-18', acceptedAt: '2026-11-18T11:00:00Z', pending: false },
    },
  }));
  await page.route('**/api/v1/me/consents', route => route.fulfill({ json: { items: [] } }));

  const errors = [];
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('/configuracoes');
  await expect(page.getByRole('heading', { name: 'Configurações e privacidade' })).toBeVisible();

  for (const light of [false, true]) {
    await page.evaluate(useLight => {
      document.body.classList.toggle('light', useLight);
      document.body.classList.toggle('dark', !useLight);
    }, light);

    for (const width of [360, 768, 1365]) {
      await page.setViewportSize({ width, height: 800 });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      expect(overflow).toBe(false);
    }
  }
  expect(errors).toEqual([]);
});
