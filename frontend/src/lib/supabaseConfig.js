// Shared by Vite and the browser. Never include key values in errors.
export function getSupabaseConfig(env) {
  const url = env.VITE_SUPABASE_URL?.trim();
  const key = (env.VITE_SUPABASE_PUBLISHABLE_KEY || env.VITE_SUPABASE_ANON_KEY)?.trim();
  if (!url || !key) throw new Error('Configure VITE_SUPABASE_URL e VITE_SUPABASE_PUBLISHABLE_KEY.');
  let parsed;
  try { parsed = new URL(url); } catch { throw new Error('VITE_SUPABASE_URL inválida.'); }
  if (!['https:', 'http:'].includes(parsed.protocol)) throw new Error('VITE_SUPABASE_URL inválida.');
  // Validate every public variable, including a legacy key shadowed by the new one.
  for (const [name, value] of Object.entries(env)) {
    if (!name.startsWith('VITE_') || typeof value !== 'string') continue;
    let role;
    try { role = JSON.parse(atob(value.trim().split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).role; } catch { /* Not a JWT. */ }
    if (value.includes('sb_secret_') || role === 'service_role') {
      throw new Error(`${name}: chave secreta proibida no frontend. Use uma chave publishable ou anon.`);
    }
  }
  if (!key.startsWith('sb_publishable_')) {
    let role;
    try { role = JSON.parse(atob(key.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).role; } catch { /* Invalid key. */ }
    if (role !== 'anon') throw new Error('A chave pública do Supabase deve ser publishable ou anon.');
  }
  return { url, key };
}
