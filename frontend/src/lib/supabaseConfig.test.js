import test from 'node:test';
import assert from 'node:assert/strict';
import { getSupabaseConfig } from './supabaseConfig.js';
const jwt = role => `header.${Buffer.from(JSON.stringify({ role })).toString('base64url')}.signature`;
const env = { VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_test' };

test('accepts publishable and legacy anon keys', () => {
  assert.equal(getSupabaseConfig(env).key, 'sb_publishable_test');
  assert.equal(getSupabaseConfig({ VITE_SUPABASE_URL: env.VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY: jwt('anon') }).key, jwt('anon'));
});
test('rejects secrets even in shadowed or unrelated public variables without leaking them', () => {
  for (const secret of ['sb_secret_do_not_print', jwt('service_role')]) {
    for (const name of ['VITE_SUPABASE_ANON_KEY', 'VITE_OTHER']) {
      assert.throws(() => getSupabaseConfig({ ...env, [name]: secret }), error => /chave secreta/.test(error.message) && !error.message.includes(secret));
    }
  }
});
test('rejects missing, malformed and non-public configuration', () => {
  for (const invalid of [{}, { ...env, VITE_SUPABASE_URL: 'invalid' }, { ...env, VITE_SUPABASE_PUBLISHABLE_KEY: jwt('authenticated') }]) {
    assert.throws(() => getSupabaseConfig(invalid));
  }
});
