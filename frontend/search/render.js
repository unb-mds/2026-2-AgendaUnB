import { activityCalendar, calendarDates, officialCalendar, searchPages, sigaaUrl, siteUrl, summerCalendar } from '../src/lib/searchPages.js';

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

function siteNav() {
  return `<nav aria-label="Navegação principal">
    <a href="/">Agenda UnB</a>
    <a href="/eventos">Eventos da UnB</a>
    <a href="/calendario-academico">Calendário acadêmico</a>
    <a href="/horarios-de-aula">Horários de aulas</a>
    <a href="/plano-de-ensino">Planos de ensino</a>
  </nav>`;
}

function shell({ heading, intro }, body) {
  return `<main class="public-search-page">
    ${siteNav()}
    <h1>${escapeHtml(heading)}</h1>
    ${intro ? `<p>${escapeHtml(intro)}</p>` : ''}
    ${body}
  </main>`;
}

export function renderSearchPage(path) {
  const page = searchPages[path];
  const content = {
    '/': '<p>Encontre atividades acadêmicas, culturais e de extensão, acompanhe prazos da graduação e organize provas e trabalhos na sua agenda pessoal.</p>',
    '/eventos': '<p>Use a agenda pública para consultar atividades por campus, área ou turno. Para acompanhar os prazos de matrícula e o período de aulas, veja o calendário acadêmico.</p>',
    '/calendario-academico': `
      <h2>Períodos de aulas da graduação</h2>
      <table><thead><tr><th scope="col">Semestre</th><th scope="col">Período de aulas</th></tr></thead>
      <tbody>${calendarDates.map(([semester, dates]) => `<tr><th scope="row">${semester}</th><td>${dates}</td></tr>`).join('')}</tbody></table>
      <h2>Fim do semestre 2026.2</h2>
      <p>As aulas terminam em <time datetime="2026-12-14">14 de dezembro de 2026</time>. O prazo para registro e consolidação das menções no SIGAA vai até <time datetime="2026-12-19">19 de dezembro</time>. A solicitação de matrícula ou retirada de componentes do tipo atividade (TCC e estágio) vai até 14 de dezembro e deve ser tratada com a coordenação do curso.</p>
      <h2>Calendários oficiais</h2>
      <ul>
        <li><a href="${activityCalendar}">Calendário por atividades de 2026.2 (PDF)</a></li>
        <li><a href="${summerCalendar}">Calendário de verão de 2027 (PDF)</a></li>
        <li><a href="${officialCalendar}">Calendário acadêmico atualizado da SAA</a></li>
      </ul>`,
    '/horarios-de-aula': `
      <h2>Onde consultar a oferta de turmas</h2>
      <ol>
        <li>Abra o <a href="${sigaaUrl}">portal público do SIGAA da UnB</a> e procure a consulta de turmas na área de graduação.</li>
        <li>Escolha o ano e o semestre. Use o código ou o nome da disciplina para identificar a oferta que você procura.</li>
        <li>Compare o número da turma, o docente, os dias e o local indicados na oferta. Consulte novamente antes da matrícula, pois a oferta pode ser atualizada.</li>
      </ol>
      <h2>Como ler um código de horário</h2>
      <p>Em <strong>24M23</strong>, os dígitos antes da letra indicam os dias da semana (segunda e quarta). A letra indica o turno (M para manhã, T para tarde e N para noite). Os dígitos depois da letra indicam as faixas de aula daquele turno. Confira os horários e o local da sua turma no SIGAA.</p>
      <p>Consulte o <a href="/calendario-academico">calendário acadêmico da UnB</a> para conferir quando começam as aulas do semestre.</p>`,
  };
  return {
    ...page,
    path,
    body: shell(page, content[path]),
    jsonLd: path === '/' ? { '@context': 'https://schema.org', '@type': 'WebSite', name: 'Agenda UnB', url: siteUrl } : undefined,
  };
}

export function renderEventContent(event) {
  const date = new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'long', timeStyle: 'short', timeZone: 'America/Sao_Paulo',
  }).format(new Date(event.data_evento));
  const place = [event.localizacao, event.campus?.nome].filter(Boolean).map(escapeHtml).join(' · ');
  return shell({ heading: event.titulo }, `
    <p><time datetime="${escapeHtml(event.data_evento)}">${escapeHtml(date)}</time></p>
    ${place ? `<p>${place}</p>` : ''}
    ${event.descricao ? `<p class="public-event-description">${escapeHtml(event.descricao)}</p>` : ''}
  `);
}
