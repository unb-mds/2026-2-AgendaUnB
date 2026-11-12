import { test, expect } from '@playwright/test';

async function setup(page, { confirm = true, googleError = false, loginError = null } = {}) {
  await page.route('**/src/lib/supabase.js*', route => route.fulfill({ contentType: 'application/javascript', body: `
    window.authCalls = [];
    export const supabase = { auth: {
      onAuthStateChange(cb) { setTimeout(() => cb('INITIAL_SESSION', null), 0); return { data: { subscription: { unsubscribe() {} } } }; },
      async signUp(payload) { window.authCalls.push(payload); return { data: { user: { id: 'test' }, session: ${confirm ? 'null' : '{}'} }, error: null }; },
      async signInWithPassword(payload) { window.authCalls.push(payload); return { error: ${JSON.stringify(loginError)} }; },
      async signInWithOAuth(payload) { window.authCalls.push(payload); return { error: ${googleError ? "{ message: 'Unsupported provider: provider is not enabled' }" : 'null'} }; }
    } };
  ` }));
}

for (const role of ['Estudante', 'Professor']) {
  test(`cadastro ${role} preserva papel e aguarda confirmação`, async ({ page }) => {
    await setup(page);
    await page.goto('/?auth=signup');
    await page.getByRole('button', { name: role, exact: true }).click();
    const inputs = page.locator('.modal-box input');
    await inputs.nth(0).fill('Pessoa Teste');
    await inputs.nth(1).fill(role === 'Professor' ? 'docente@unb.br' : 'aluno@example.com');
    await inputs.nth(2).fill('SenhaDeTeste123!');
    await inputs.nth(3).fill('SenhaDeTeste123!');
    await page.getByRole('button', { name: 'Criar Conta', exact: true }).click();
    await expect(page.getByRole('status')).toContainText('link de confirmação');
    expect(await page.evaluate(() => window.authCalls[0].options.data.papel)).toBe(role === 'Professor' ? 'professor' : 'student');
    await expect(page.getByRole('heading', { name: 'Entrar', exact: true })).toBeVisible();
  });
}
test('Google desativado mostra alternativa de e-mail e senha', async ({ page }) => {
  await setup(page, { googleError: true });
  await page.goto('/?auth=login');
  await page.getByRole('button', { name: 'Continuar com Google' }).click();
  await expect(page.getByText('O login com Google ainda não está disponível. Use e-mail e senha.')).toBeVisible();
});
test('login informa confirmação pendente', async ({ page }) => {
  await setup(page, { loginError: { message: 'Email not confirmed' } });
  await page.goto('/?auth=login');
  await page.locator('.modal-box input').nth(0).fill('docente@unb.br');
  await page.locator('.modal-box input').nth(1).fill('SenhaDeTeste123!');
  await page.locator('.modal-box').getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page.getByText('Confirme seu e-mail pelo link enviado antes de entrar.')).toBeVisible();
});

for (const email of ['aluno@example.com', 'docente@unb.br']) {
  test(`login com senha encaminha ${email} para eventos`, async ({ page }) => {
    await setup(page);
    await page.goto('/?auth=login');
    await page.locator('.modal-box input').nth(0).fill(email);
    await page.locator('.modal-box input').nth(1).fill('SenhaDeTeste123!');
    await page.locator('.modal-box').getByRole('button', { name: 'Entrar', exact: true }).click();
    await expect(page).toHaveURL(/\/eventos$/);
    expect(await page.evaluate(() => window.authCalls[0].email)).toBe(email);
  });
}

test('cadastro professor recusa domínio estudantil antes de enviar', async ({ page }) => {
  await setup(page);
  await page.goto('/?auth=signup');
  await page.getByRole('button', { name: 'Professor', exact: true }).click();
  const inputs = page.locator('.modal-box input');
  await inputs.nth(0).fill('Pessoa Teste');
  await inputs.nth(1).fill('aluno@aluno.unb.br');
  await inputs.nth(2).fill('SenhaDeTeste123!');
  await inputs.nth(3).fill('SenhaDeTeste123!');
  await page.getByRole('button', { name: 'Criar Conta', exact: true }).click();
  await expect(page.getByText(/Cadastro como professor exige/)).toBeVisible();
  expect(await page.evaluate(() => window.authCalls.length)).toBe(0);
});
