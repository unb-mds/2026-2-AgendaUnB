import { request } from './api';
import { approvedTextHash, normalizeTextPreview } from './approvedText';
import { normalizePlan, normalizePlanList, SYLLABUS_PAGE_SIZE } from './syllabus';

async function syllabusRequest(path, { signal, timeout = 30000, ...options } = {}) {
  const controller = new AbortController();
  const cancel = () => controller.abort(signal.reason);
  if (signal?.aborted) cancel();
  else signal?.addEventListener('abort', cancel, { once: true });
  const timer = setTimeout(() => controller.abort(new DOMException('Tempo de espera excedido.', 'TimeoutError')), timeout);
  try {
    return await request(`/syllabus${path}`, { ...options, auth: true, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted && !signal?.aborted) throw controller.signal.reason;
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}

export const syllabusApi = {
  async prepareText(text, signal, offeringId) {
    return normalizePlan(await syllabusRequest('/text', { method: 'POST', body: JSON.stringify({ text, offering_id: offeringId }), signal }));
  },
  async text(id, signal) {
    return normalizeTextPreview(await syllabusRequest(`/${encodeURIComponent(id)}/text`, { signal }));
  },
  async authorize(id, pages, reprocess, signal) {
    const textHash = await approvedTextHash(pages);
    return normalizePlan(await syllabusRequest(`/${encodeURIComponent(id)}/extractions`, {
      method: 'POST', signal,
      body: JSON.stringify({ pages, textHash, authorize: true, contentEligible: true, reprocess }),
    }));
  },
  async upload({ file, offeringId }, signal) {
    const body = new FormData();
    body.append('file', file);
    body.append('offering_id', offeringId);
    return normalizePlan(await syllabusRequest('/upload', { method: 'POST', body, signal, timeout: 90000 }));
  },
  async list(page, signal, offeringId) {
    const query = new URLSearchParams({ limit: String(SYLLABUS_PAGE_SIZE), offset: String(page * SYLLABUS_PAGE_SIZE) });
    if (offeringId) query.set('offering_id', offeringId);
    return normalizePlanList(await syllabusRequest(`?${query}`, { signal }));
  },
  async get(id, signal) {
    return normalizePlan(await syllabusRequest(`/${encodeURIComponent(id)}`, { signal }));
  },
  async confirm(id, candidates, options) {
    const {
      idempotencyKey = crypto.randomUUID(),
      signal,
    } = typeof options === 'string'
      ? { idempotencyKey: options }
      : options && typeof options === 'object' && 'aborted' in options
        ? { signal: options }
        : (options || {});
    const result = await syllabusRequest(`/${encodeURIComponent(id)}/confirm`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({ candidates }),
      signal,
    });
    const requested = new Set(candidates.map(item => item.candidateId));
    const removed = new Set((result?.items || []).filter(item => item?.removed).map(item => item.candidateId));
    const returned = new Set();
    const validEvents = Array.isArray(result?.events) && result.events.every(event => {
      const candidateId = event?.origin?.candidateId;
      if (typeof event?.id !== 'string' || event.origin?.syllabusId !== id || !requested.has(candidateId) || returned.has(candidateId)) {
        return false;
      }
      returned.add(candidateId);
      return true;
    });
    const allAccountedFor = [...requested].every(candidateId => returned.has(candidateId) || removed.has(candidateId));
    if (result?.syllabusId !== id || !validEvents || !allAccountedFor) {
      throw new Error('A resposta da confirmação não pôde ser verificada.');
    }
    return result.events;
  },
};
