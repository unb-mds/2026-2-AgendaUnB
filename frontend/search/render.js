import { searchPages, siteUrl } from '../src/lib/searchPages.js';

export function escapeHtml(value) {
  const replacements = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(value).replace(/[&<>"']/g, character => replacements[character]);
}

function jsonLdScript(value) {
  return `<script type="application/ld+json" data-agenda-search>${JSON.stringify(value).replace(/</g, '\\u003c')}</script>`;
}

export function renderAppDocument(template, { title, description, path, body = '', jsonLd }) {
  const metadata = [
    `<title>${escapeHtml(title)}</title>`,
    description && `<meta name="description" content="${escapeHtml(description)}">`,
    path && `<link rel="canonical" href="${siteUrl}${path}">`,
    path && '<meta property="og:type" content="website">',
    path && '<meta property="og:locale" content="pt_BR">',
    path && '<meta property="og:site_name" content="Agenda UnB">',
    path && `<meta property="og:title" content="${escapeHtml(title)}">`,
    path && `<meta property="og:description" content="${escapeHtml(description)}">`,
    path && `<meta property="og:url" content="${siteUrl}${path}">`,
    path && `<meta property="og:image" content="${siteUrl}/banner.png">`,
    !path && '<meta name="robots" content="noindex">',
    jsonLd && jsonLdScript(jsonLd),
  ].filter(Boolean).join('\n    ');
  return template
    .replace('<title>Agenda UnB</title>', () => metadata)
    .replace('<div id="root"></div>', () => `<div id="root">${body}</div>`);
}

// Stable entry URLs load the hashed Vite assets for the deployed build.
export function renderEventDocument(page) {
  return renderAppDocument(`<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agenda UnB</title>
    <link rel="icon" href="/Logo-AgendaUnB1.png">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@200;500&family=Orbitron:wght@400;700&display=swap">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0">
    <link rel="stylesheet" href="/event-app.css">
    <script type="module" src="/event-app.js"></script>
  </head>
  <body><div id="root"></div></body>
</html>`, page);
}

export function renderSearchPage(path) {
  return {
    ...searchPages[path],
    path,
    jsonLd: path === '/' ? { '@context': 'https://schema.org', '@type': 'WebSite', name: 'Agenda UnB', url: siteUrl } : undefined,
  };
}

export function renderEventContent(event) {
  const date = new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'long', timeStyle: 'short', timeZone: 'America/Sao_Paulo',
  }).format(new Date(event.data_evento));
  const place = [event.localizacao, event.campus?.nome].filter(Boolean).map(escapeHtml).join(' · ');
  return `<main class="public-search-page">
    <h1>${escapeHtml(event.titulo)}</h1>
    <p><time datetime="${escapeHtml(event.data_evento)}">${escapeHtml(date)}</time></p>
    ${place ? `<p>${place}</p>` : ''}
    ${event.descricao ? `<p class="public-event-description">${escapeHtml(event.descricao)}</p>` : ''}
  </main>`;
}
