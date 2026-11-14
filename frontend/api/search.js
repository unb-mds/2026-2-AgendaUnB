import { eventDescription, eventTitle, searchPages, siteUrl } from '../src/lib/searchPages.js';
import { escapeHtml, renderEventDocument, renderEventContent } from '../search/render.js';

const uuid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
const cache = 'public, s-maxage=300';

async function approvedEvents(filters, signal) {
  const url = process.env.VITE_SUPABASE_URL?.trim();
  const key = (process.env.VITE_SUPABASE_PUBLISHABLE_KEY || process.env.VITE_SUPABASE_ANON_KEY)?.trim();
  if (!url || !key) throw new Error('Configuração pública do Supabase ausente.');
  const headers = { apikey: key };
  if (!key.startsWith('sb_publishable_')) {
    const payload = JSON.parse(Buffer.from(key.split('.')[1], 'base64url').toString());
    if (payload.role !== 'anon') throw new Error('A busca requer uma chave pública do Supabase.');
    headers.Authorization = `Bearer ${key}`;
  }
  const endpoint = new URL('/rest/v1/eventos', url);
  endpoint.search = new URLSearchParams({ status: 'eq.aprovado', ...filters });
  const result = await fetch(endpoint, { headers, signal });
  if (!result.ok) throw new Error(`Supabase respondeu com status ${result.status}`);
  return result.json();
}

async function eventPaths(signal) {
  const paths = [];
  const pageSize = 1000;
  const maxEvents = 50000 - Object.keys(searchPages).length;
  // Use the immutable UUID as a cursor so additions and removals do not shift pages.
  while (paths.length < maxEvents) {
    const last = paths.at(-1)?.split('/').at(-1);
    const page = await approvedEvents({
      select: 'id',
      order: 'id.asc',
      limit: String(Math.min(pageSize, maxEvents - paths.length)),
      ...(last && { id: `gt.${last}` }),
    }, signal);
    if (!page.length) break;
    for (const { id } of page) paths.push(`/evento/${id}`);
  }
  return paths;
}

function eventMetadata(event, path) {
  return {
    path,
    title: eventTitle(event.titulo),
    description: eventDescription({
      description: event.descricao,
      title: event.titulo,
      location: event.localizacao,
      campus: event.campus?.nome,
    }),
    body: renderEventContent(event),
  };
}

export default async function handler(request, response) {
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.setHeader('Cache-Control', 'no-store');
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.setHeader('Allow', 'GET, HEAD');
    return response.status(405).end();
  }

  const signal = AbortSignal.timeout(4500);
  try {
    const { kind, id } = request.query;
    if (kind === 'sitemap') {
      const paths = [...Object.keys(searchPages), ...await eventPaths(signal)];
      const xml = paths.map(path => `<url><loc>${escapeHtml(siteUrl + path)}</loc></url>`).join('\n');
      response.setHeader('Content-Type', 'application/xml; charset=utf-8');
      response.setHeader('Cache-Control', cache);
      return response.status(200).send(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${xml}\n</urlset>\n`);
    }

    const validId = typeof id === 'string' && uuid.test(id);
    if (kind !== 'event' || !validId) {
      response.setHeader('X-Robots-Tag', 'noindex');
      return response.status(404).end();
    }

    const [event] = await approvedEvents({
      id: `eq.${id.toLowerCase()}`,
      select: 'id,titulo,descricao,data_evento,localizacao,campus(nome)',
    }, signal);
    const path = `/evento/${id.toLowerCase()}`;
    if (event && id !== id.toLowerCase()) {
      response.setHeader('Location', path);
      return response.status(308).end();
    }

    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    if (!event) {
      // The app can still load the event via authenticated personal routes.
      response.setHeader('X-Robots-Tag', 'noindex');
      const body = '<main class="public-search-page"><h1>Evento indisponível na agenda pública</h1><p><a href="/eventos">Consultar eventos da UnB</a></p></main>';
      return response.status(404).send(renderEventDocument({ title: 'Evento | Agenda UnB', body }));
    }

    const html = renderEventDocument(eventMetadata(event, path));
    response.setHeader('Cache-Control', cache);
    return response.status(200).send(html);
  } catch (error) {
    console.error('Falha ao servir conteúdo de busca:', error.message);
    response.setHeader('Retry-After', '60');
    return response.status(503).send('Conteúdo temporariamente indisponível.');
  }
}
