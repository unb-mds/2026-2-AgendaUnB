export function authErrorMessage(error) {
  const message = error?.message || '';
  if (/invalid login credentials/i.test(message)) return 'E-mail ou senha incorretos.';
  if (/email not confirmed/i.test(message)) return 'Confirme seu e-mail pelo link enviado antes de entrar.';
  if (/provider.*not enabled|unsupported provider/i.test(message)) return 'O login com Google ainda não está disponível. Use e-mail e senha.';
  if (/secret API key|invalid API key/i.test(message)) return 'O serviço de login está configurado incorretamente. Contate a equipe do Agenda UnB.';
  if (/rate limit|too many requests|security purposes/i.test(message)) return 'Muitas tentativas. Aguarde alguns minutos e tente novamente.';
  return 'Não foi possível autenticar. Verifique sua conexão e tente novamente.';
}

export async function attemptAuth(action) {
  try { return await action(); }
  catch (error) { return { erro: authErrorMessage(error) }; }
}
