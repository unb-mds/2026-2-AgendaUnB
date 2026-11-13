import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFile } from 'node:fs/promises'
import { guidePaths } from './src/lib/searchPages.js'
import { renderAppDocument, renderSearchPage } from './search/render.js'

const searchGuides = {
  name: 'search-guides',
  configureServer(server) {
    server.middlewares.use(async (request, response, next) => {
      const path = request.url?.split('?')[0];
      if (!guidePaths.includes(path)) return next();

      try {
        const source = await readFile(new URL('./index.html', import.meta.url), 'utf8');
        const template = source.replace('<script type="module" src="/src/main.jsx"></script>',
          '<link rel="stylesheet" href="/src/styles/global.css">');
        const html = await server.transformIndexHtml(path, renderAppDocument(template, renderSearchPage(path)));
        response.setHeader('Content-Type', 'text/html; charset=utf-8');
        response.end(html);
      } catch (error) {
        next(error);
      }
    });
  },
};

export default defineConfig({
  envDir: '..',
  plugins: [react(), searchGuides],
  server: {
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${process.env.AGENDA_BACKEND_PORT || 8000}`,
        changeOrigin: true,
      },
    },
  },
})

