import { supabase } from './supabase';

export const MIN_PASSWORD_LENGTH = 8;
export const EMAIL_RETRY_SECONDS = 60;
export const AUTH_RETURN_PATH = '/auth/retorno';

const EMAIL_INSTITUCIONAL = /@unb\.br$/i;
const normalizeEmail = email => email.trim().toLowerCase();
const returnUrl = () => new URL(AUTH_RETURN_PATH, window.location.origin).href;

function authFailure(error, fallback) {
  if (error?.status === 429) {
    return { error: 'Aguarde um minuto antes de solicitar outro e-mail.', rateLimited: true };
  }
  if (error?.code === 'weak_password') {
    return { error: 'Escolha uma senha mais forte, com pelo menos 8 caracteres.' };
  }
  return { error: fallback };
}

export async function signUpWithEmail({ email, password, nomeCompleto, papel }) {
  if (nomeCompleto.trim().length < 2) return { error: 'Informe seu nome completo.' };
  if (papel === 'professor' && !EMAIL_INSTITUCIONAL.test(normalizeEmail(email))) {
    return { error: 'Para se cadastrar como professor, use seu e-mail @unb.br.' };
  }
  const { data, error } = await supabase.auth.signUp({
    email: normalizeEmail(email),
    password,
    options: {
      emailRedirectTo: returnUrl(),
      data: { nome_completo: nomeCompleto.trim(), papel },
    },
  });
  if (error) return authFailure(error, 'Não foi possível criar a conta. Tente novamente.');
  return { signedIn: Boolean(data.session) };
}

export async function signInWithEmail(email, password) {
  const { error } = await supabase.auth.signInWithPassword({ email: normalizeEmail(email), password });
  if (!error) return {};
  if (error.code === 'email_not_confirmed') return { needsConfirmation: true };
  if (error.code === 'invalid_credentials') return { error: 'E-mail ou senha incorretos.' };
  return { error: 'Não foi possível entrar. Tente novamente em instantes.' };
}

export async function sendConfirmation(email) {
  const { error } = await supabase.auth.resend({
    type: 'signup', email: normalizeEmail(email), options: { emailRedirectTo: returnUrl() },
  });
  return error ? authFailure(error, 'Não foi possível reenviar a confirmação. Tente novamente.') : {};
}

export async function sendRecovery(email) {
  const { error } = await supabase.auth.resetPasswordForEmail(normalizeEmail(email), { redirectTo: returnUrl() });
  return error ? authFailure(error, 'Não foi possível enviar o link de recuperação. Tente novamente.') : {};
}

export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: returnUrl(),
      skipBrowserRedirect: true,
    },
  });
  if (error || !data?.url) return { error: 'Não foi possível iniciar o login com Google. Tente novamente.' };
  window.location.assign(data.url);
  return { redirecting: true };
}

export function validateNewPassword(password, confirmation) {
  if (password.length < MIN_PASSWORD_LENGTH) return 'Use pelo menos 8 caracteres na senha.';
  if (password !== confirmation) return 'As senhas não coincidem.';
  return '';
}

export async function changePassword(client, password) {
  const { error } = await client.auth.updateUser({ password });
  if (error?.status === 401 || error?.code === 'session_not_found') return { expired: true };
  if (error?.code === 'same_password') return { error: 'Escolha uma senha diferente da anterior.' };
  if (error) return authFailure(error, 'Não foi possível redefinir a senha. Tente novamente ou solicite outro link.');
  return {};
}
