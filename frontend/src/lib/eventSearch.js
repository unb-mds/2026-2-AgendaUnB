const CONNECTORS = new Set([
  'a', 'as', 'o', 'os', 'da', 'das', 'de', 'do', 'dos', 'e', 'em', 'na', 'nas', 'no', 'nos', 'para',
]);

export function normalizeEventSearch(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim();
}

export function buildEventSearchIndex(events) {
  return events.map(event => {
    const title = normalizeEventSearch(event.titulo);
    const details = normalizeEventSearch([event.local, event.campus, event.area, event.organizadorNome].join(' '));
    const description = normalizeEventSearch(event.descricao);
    return {
      event,
      title,
      fields: [
        { words: title.split(' '), weight: 6 },
        { words: details.split(' '), weight: 4 },
        { words: description.split(' '), weight: 2 },
      ],
    };
  });
}

function scoreTerm(term, fields) {
  for (const { words, weight } of fields) {
    if (words.includes(term)) return weight;
    if (term.length >= 2 && words.some(word => word.startsWith(term))) return weight - 1;
  }
  return 0;
}

export function searchIndexedEvents(index, query) {
  const queryTerms = [...new Set(query.split(' '))];
  const keywords = queryTerms.filter(term => !CONNECTORS.has(term));
  const terms = keywords.length ? keywords : queryTerms;
  const matches = [];

  for (const { event, title, fields } of index) {
    const scores = terms.map(term => scoreTerm(term, fields));
    if (scores.includes(0)) continue;
    let score = scores.reduce((total, termScore) => total + termScore, 0);
    if (title === query) score += 2;
    else if (` ${title} `.includes(` ${query} `)) score += 1;
    matches.push({ event, score });
  }

  return matches.sort((a, b) => b.score - a.score).map(match => match.event);
}
