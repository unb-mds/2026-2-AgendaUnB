import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { getSupabaseConfig } from './src/lib/supabaseConfig.js'

export default defineConfig(({ mode }) => {
  getSupabaseConfig(loadEnv(mode, '..', 'VITE_'));
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

