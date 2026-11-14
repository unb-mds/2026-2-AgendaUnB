import test from 'node:test';
import assert from 'node:assert/strict';
import { validateDeploymentConfig } from './deploymentConfig.js';
const env = { VITE_API_URL: 'https://api-preview.example.test/api/v1', VITE_SUPABASE_URL: 'https://preview.supabase.co', VITE_DEPLOYMENT_ENV: 'preview' };
const platform = { VERCEL_ENV: 'preview', PRODUCTION_API_ORIGIN: 'https://api.example.test', PRODUCTION_SUPABASE_URL: 'https://production.supabase.co' };
test('refuses provider or database secrets exposed with VITE_', () => {
  for (const name of ['VITE_GEMINI_API_KEY', 'VITE_DATABASE_URL', 'VITE_GOOGLE_CLIENT_SECRET', 'VITE_SUPABASE_SERVICE_ROLE_KEY']) {
    assert.throws(() => validateDeploymentConfig({ ...env, [name]: 'private-value' }), error => !error.message.includes('private-value'));
  }
});
test('preview fails closed and rejects production resources', () => {
  assert.throws(() => validateDeploymentConfig(env, { VERCEL_ENV: 'preview' }));
  assert.throws(() => validateDeploymentConfig({ ...env, VITE_SUPABASE_URL: platform.PRODUCTION_SUPABASE_URL }, platform));
  assert.throws(() => validateDeploymentConfig({ ...env, VITE_API_URL: `${platform.PRODUCTION_API_ORIGIN}/api/v1` }, platform));
  assert.doesNotThrow(() => validateDeploymentConfig(env, platform));
});
test('hosted builds require HTTPS and the API version prefix', () => {
  for (const url of ['http://api.example.test/api/v1', 'https://api.example.test', '/api/v1',
    'https://user:private-value@api.example.test/api/v1', 'https://api.example.test/api/v1?token=private-value',
    'private-value']) {
    assert.throws(() => validateDeploymentConfig({ ...env, VITE_API_URL: url }, { VERCEL_ENV: 'production' }),
      error => !error.message.includes('private-value') && error.cause === undefined);
  }
  assert.doesNotThrow(() => validateDeploymentConfig(env, { VERCEL_ENV: 'production' }));
});
test('allows Vercel system VITE_VERCEL_ variables', () => {
  assert.doesNotThrow(() => validateDeploymentConfig({
    ...env,
    VITE_VERCEL_ENV: 'production',
    VITE_VERCEL_GIT_REPO_ID: '123456',
    VITE_VERCEL_URL: 'agendaunb.com.br',
  }, { VERCEL_ENV: 'production' }));
});
