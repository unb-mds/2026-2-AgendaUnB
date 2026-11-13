import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn("Faltam variáveis de ambiente do Supabase.")
}

// Provider credentials are used only during the callback, never persisted with the app session.
function withoutProviderCredentials(key, value) {
  if (!value || !key.endsWith('-auth-token')) return value;
  try {
    const session = JSON.parse(value);
    if (session && typeof session === 'object') {
      delete session.provider_token;
      delete session.provider_refresh_token;
      return JSON.stringify(session);
    }
  } catch {
    // Supabase handles its own invalid session data.
  }
  return value;
}

const authStorage = {
  getItem(key) {
    const value = window.localStorage.getItem(key);
    const cleaned = withoutProviderCredentials(key, value);
    if (cleaned !== value) window.localStorage.setItem(key, cleaned);
    return cleaned;
  },
  removeItem: key => window.localStorage.removeItem(key),
  setItem: (key, value) => window.localStorage.setItem(key, withoutProviderCredentials(key, value)),
};

export const supabase = createClient(supabaseUrl || '', supabaseAnonKey || '', {
  auth: { flowType: 'pkce', detectSessionInUrl: false, storage: authStorage },
})

export function createRecoveryClient() {
  return createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      storageKey: 'agenda-password-recovery',
      persistSession: false,
      autoRefreshToken: false,
      detectSessionInUrl: false,
    },
  })
}
