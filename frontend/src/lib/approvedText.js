export const MAX_APPROVED_TEXT_BYTES = 40000;

export async function approvedTextHash(pages) {
  const snapshot = pages.map(({ pagina, texto }) => ({ pagina: pagina ?? null, texto }));
  const bytes = new TextEncoder().encode(JSON.stringify(snapshot));
  const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

export function approvedTextSize(pages) {
  return pages.reduce((sum, page) => sum + new TextEncoder().encode(page.texto).length, 0);
}
