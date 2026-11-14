export const siteUrl = 'https://agendaunb.com.br';

export const searchPages = {
  '/': {
    title: 'Agenda UnB | Eventos e organização acadêmica da UnB',
    description: 'Encontre eventos nos campi da Universidade de Brasília e organize datas de provas, trabalhos e outros compromissos da sua rotina acadêmica.',
  },
  '/eventos': {
    title: 'Eventos da UnB por campus | Agenda UnB',
    description: 'Consulte a agenda pública de eventos da UnB e filtre por campus, área ou turno. Confira datas, locais e links para as atividades publicadas.',
  },
};

export function eventTitle(title) {
  return `${title} | Eventos da UnB`;
}

export function eventDescription({ description, title, location, campus }) {
  const text = description?.replace(/\*+/g, '').replace(/\s+/g, ' ').trim();
  if (text) {
    return text.length > 157 ? `${(text.slice(0, 157).replace(/\s+\S*$/, '') || text.slice(0, 157))}…` : text;
  }
  return `Confira a data e os detalhes de ${title}${location || campus ? ` em ${location || campus}` : ''} na agenda da UnB.`;
}
