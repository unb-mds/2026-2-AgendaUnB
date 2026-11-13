export const MAX_APPROVED_TEXT_BYTES = 40000;

export function normalizeTextPreview(data) {
  const pages = data?.pages;
  if (!Array.isArray(pages) || !pages.length || pages.length > 10
    || typeof data.provider !== 'string' || !data.provider.trim() || typeof data.providerAvailable !== 'boolean'
    || pages.some(page => !page || typeof page.texto !== 'string'
      || (page.pagina !== null && (!Number.isInteger(page.pagina) || page.pagina < 1 || page.pagina > 10)))
    || new Set(pages.map(page => page.pagina)).size !== pages.length
    || (pages.length > 1 && pages.some(page => page.pagina === null))
    || approvedTextSize(pages) > MAX_APPROVED_TEXT_BYTES) {
    throw new Error('O serviço retornou um texto inválido. Tente carregar novamente.');
  }
  return { ...data, pages: pages.map(({ pagina, texto }) => ({ pagina, texto })) };
}

export async function approvedTextHash(pages) {
  const snapshot = pages.map(({ pagina, texto }) => ({ pagina: pagina ?? null, texto }));
  const bytes = new TextEncoder().encode(JSON.stringify(snapshot));
  const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

export function approvedTextSize(pages) {
  return pages.reduce((sum, page) => sum + new TextEncoder().encode(page.texto).length, 0);
}
