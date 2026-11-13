export const siteUrl = 'https://agendaunb.com.br';
export const officialCalendar = 'https://saa.unb.br/calendario-academico-graduacao/';
export const activityCalendar = 'https://saa.unb.br/wp-content/uploads/2026/10/2026_2_Calend_Ativ_Grad_02_10_2026.pdf';
export const summerCalendar = 'https://saa.unb.br/wp-content/uploads/2026/11/2026_4_Calend_Ativ_Grad_04_11_2026.pdf';
export const sigaaUrl = 'https://www.sigaa.unb.br/sigaa/public/home.jsf';

export const searchPages = {
  '/': {
    title: 'Agenda UnB | Eventos e calendário acadêmico da UnB',
    heading: 'Agenda UnB',
    description: 'Consulte eventos dos campi da Universidade de Brasília, confira o calendário acadêmico de graduação e organize suas datas de provas e trabalhos.',
    intro: 'Eventos e calendário acadêmico da Universidade de Brasília.',
  },
  '/eventos': {
    title: 'Eventos da UnB por campus | Agenda UnB',
    heading: 'Eventos da UnB',
    description: 'Consulte a agenda pública de eventos da UnB e filtre por campus, área ou turno. Confira datas, locais e links para as atividades publicadas.',
    intro: 'Consulte eventos e comunicados da Universidade de Brasília nos campi Darcy Ribeiro, Gama, Ceilândia e Planaltina e na Fazenda Água Limpa.',
  },
  '/calendario-academico': {
    title: 'Calendário acadêmico UnB 2026.2 e 2027 | Agenda UnB',
    heading: 'Calendário acadêmico da UnB',
    description: 'Confira o fim das aulas de 2026.2, as datas do verão de 2027 e os períodos de aulas de 2027 na UnB, com links para o calendário oficial da graduação.',
    intro: 'Datas da graduação publicadas pela Secretaria de Administração Acadêmica da Universidade de Brasília.',
  },
  '/horarios-de-aula': {
    title: 'Horários de aulas e turmas da UnB no SIGAA | Agenda UnB',
    heading: 'Como consultar horários de aulas na UnB',
    description: 'Encontre a oferta de turmas da UnB no SIGAA e aprenda a interpretar códigos de horário, como 24M23, antes de montar sua grade.',
    intro: 'Use a consulta pública de turmas do SIGAA para verificar o semestre, o código da disciplina e o horário de cada oferta.',
  },
};

export const guidePaths = ['/calendario-academico', '/horarios-de-aula'];

export const calendarDates = [
  ['2026.2', '10/08 a 14/12/2026'],
  ['2026.4 (verão)', '11/01 a 17/02/2027'],
  ['2027.1', '15/03 a 16/07/2027'],
  ['2027.2', '09/08 a 16/12/2027'],
];

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
