import { request } from './api';
import { approvedTextHash } from './approvedText';
import { normalizePlan, normalizePlanList, SYLLABUS_PAGE_SIZE } from './syllabus';

async function syllabusRequest(path, { signal, timeout = 30000, ...options } = {}) {
  const controller = new AbortController();
  const cancel = () => controller.abort(signal.reason);
  if (signal?.aborted) cancel();
  else signal?.addEventListener('abort', cancel, { once: true });
  const timer = setTimeout(() => controller.abort(new DOMException('Tempo de espera excedido.', 'TimeoutError')), timeout);
  try {
    return await request(`/syllabus${path}`, { ...options, auth: true, signal: controller.signal });
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}

export const syllabusApi = {
  async prepareText(text, signal) {
    return normalizePlan(await syllabusRequest('/text', { method: 'POST', body: JSON.stringify({ text }), signal }));
  },
  text(id, signal) {
    return syllabusRequest(`/${encodeURIComponent(id)}/text`, { signal });
  },
  async authorize(id, pages, reprocess, signal) {
    const textHash = await approvedTextHash(pages);
    return normalizePlan(await syllabusRequest(`/${encodeURIComponent(id)}/extractions`, {
      method: 'POST', signal,
      body: JSON.stringify({ pages, textHash, authorize: true, contentEligible: true, reprocess }),
    }));
  },
  async upload({ file, disciplina, semestre, ano }, signal) {
    const body = new FormData();
    body.append('file', file);
    body.append('disciplina', disciplina.trim());
    body.append('semestre', String(semestre));
    body.append('ano', String(ano));
    return normalizePlan(await syllabusRequest('/upload', { method: 'POST', body, signal, timeout: 90000 }));
  },
  async list(page, signal) {
    const query = new URLSearchParams({ limit: String(SYLLABUS_PAGE_SIZE), offset: String(page * SYLLABUS_PAGE_SIZE) });
    return normalizePlanList(await syllabusRequest(`?${query}`, { signal }));
  },
  async get(id, signal) {
    return normalizePlan(await syllabusRequest(`/${encodeURIComponent(id)}`, { signal }));
  },
};
