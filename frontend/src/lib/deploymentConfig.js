const PUBLIC_KEYS = new Set([
  'VITE_API_URL', 'VITE_SUPABASE_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY',
  'VITE_SUPABASE_ANON_KEY', 'VITE_DEPLOYMENT_ENV',
]);

function publicHttpsUrl(value, name) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${name} deve ser uma URL HTTPS pública.`);
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
    throw new Error(`${name} deve ser uma URL HTTPS pública.`);
  }
  return url;
}

// Build-time policy: errors never include configuration values.
export function validateDeploymentConfig(env, platform = {}) {
  for (const name of Object.keys(env)) {
    if (name.startsWith('VITE_') && !PUBLIC_KEYS.has(name) && !name.startsWith('VITE_VERCEL_')) {
      throw new Error(`${name}: variável pública não autorizada. Segredos pertencem ao servidor.`);
    }
  }
  if (!platform.VERCEL_ENV) return;
  const api = publicHttpsUrl(env.VITE_API_URL, 'VITE_API_URL');
  const auth = publicHttpsUrl(env.VITE_SUPABASE_URL, 'VITE_SUPABASE_URL');
  if (!['/api/v1', '/api/v1/'].includes(api.pathname) || auth.pathname !== '/') {
    throw new Error('Use a origem do Supabase e a URL da API terminando em /api/v1.');
  }
  if (platform.VERCEL_ENV === 'preview') {
    if (env.VITE_DEPLOYMENT_ENV !== 'preview' || !platform.PRODUCTION_SUPABASE_URL || !platform.PRODUCTION_API_ORIGIN) {
      throw new Error('Preview bloqueado: configure dados separados e as referências de produção.');
    }
    const productionAuth = publicHttpsUrl(platform.PRODUCTION_SUPABASE_URL, 'PRODUCTION_SUPABASE_URL');
    const productionApi = publicHttpsUrl(platform.PRODUCTION_API_ORIGIN, 'PRODUCTION_API_ORIGIN');
    if (auth.origin === productionAuth.origin || api.origin === productionApi.origin) {
      throw new Error('Preview não pode usar Auth, banco ou API de produção.');
    }
  }
}
