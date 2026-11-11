import { defineConfig } from '@playwright/test';

const port = Number(process.env.E2E_PORT || 5173);

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  use: { channel: process.env.E2E_BROWSER_CHANNEL || undefined, baseURL: `http://127.0.0.1:${port}`, viewport: { width: 1365, height: 1000 } },
  webServer: { command: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`, url: `http://127.0.0.1:${port}`, reuseExistingServer: !process.env.CI },
});
