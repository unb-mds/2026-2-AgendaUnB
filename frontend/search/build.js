import { readFile, writeFile } from 'node:fs/promises';
import { searchPages } from '../src/lib/searchPages.js';
import { renderAppDocument, renderSearchPage } from './render.js';

const dist = new URL('../dist/', import.meta.url);
const index = new URL('index.html', dist);
const template = await readFile(index, 'utf8');
const verification = /<meta name="google-site-verification"[^>]*>\n?/.exec(template)?.[0];
const appTemplate = verification ? template.replace(verification, '') : template;
const app = renderAppDocument(appTemplate, { title: 'Agenda UnB' });
await writeFile(new URL('app.html', dist), app);
await writeFile(new URL('404.html', dist), renderAppDocument(appTemplate, {
  title: 'Página não encontrada | Agenda UnB',
  body: '<main class="public-search-page"><h1>Página não encontrada</h1><p><a href="/">Voltar ao Agenda UnB</a></p></main>',
}).replace(/<script type="module"[^>]*><\/script>/, ''));

for (const path of Object.keys(searchPages)) {
  const document = renderAppDocument(path === '/' ? template : appTemplate, renderSearchPage(path));
  await writeFile(path === '/' ? index : new URL(`.${path}.html`, dist), document);
}

const entry = /<script type="module"[^>]*src="([^"]+)"/.exec(template)?.[1];
const stylesheet = /<link rel="stylesheet"[^>]*href="(\/assets\/[^"]+\.css)"/.exec(template)?.[1];
if (!entry || !stylesheet) throw new Error('Assets do Vite ausentes no HTML compilado.');
await writeFile(new URL('event-app.js', dist), `import ${JSON.stringify(entry)};\n`);
await writeFile(new URL('event-app.css', dist), `@import url(${JSON.stringify(stylesheet)});\n`);
