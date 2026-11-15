import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { getSupabaseConfig } from './src/lib/supabaseConfig.js'
import { validateDeploymentConfig } from './src/lib/deploymentConfig.js'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', 'VITE_');
  getSupabaseConfig(env);
  validateDeploymentConfig(env, process.env);
  return {
    envDir: '..',
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: `http://127.0.0.1:${process.env.AGENDA_BACKEND_PORT || 8000}`,
          changeOrigin: true,
        },
      },
    },
  };
})

