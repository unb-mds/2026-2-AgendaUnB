// Fixtures for the frontend demonstration. Followw is only queried by the future server adapter.
const SUBJECTS = [
  ['mds', 'FGA0108', 'Métodos de Desenvolvimento de Software', '01', 'Faculdade do Gama', 'Ana Ribeiro'],
  ['fac', 'CIC0092', 'Fundamentos de Arquitetura de Computadores', '02', 'Darcy Ribeiro', 'Marcos Lima'],
  ['cal', 'MAT0025', 'Cálculo 1', '03', 'Darcy Ribeiro', 'Lúcia Nunes'],
  ['icc', 'CIC0004', 'Introdução à Ciência da Computação', '01', 'Darcy Ribeiro', 'João Martins'],
  ['ea', 'FGA0168', 'Engenharia e Ambiente', '02', 'Faculdade do Gama', 'Helena Souza'],
  ['cal-fga', 'FGA0001', 'Cálculo 1', '03', 'Faculdade do Gama', 'Rafael Costa'],
];

const localDate = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Sao_Paulo', year: 'numeric', month: 'numeric',
});

// Civil semesters are a preview convention until an academic-period source is integrated.
export function catalogPeriods(date = new Date()) {
  const parts = localDate.formatToParts(date);
  const year = Number(parts.find(part => part.type === 'year').value);
  const semester = Number(parts.find(part => part.type === 'month').value) <= 6 ? 1 : 2;
  return [`${year}.${semester}`, semester === 1 ? `${year}.2` : `${year + 1}.1`];
}

export function demoOffering(id) {
  const [key, period, ...rest] = id.split(':');
  const subject = SUBJECTS.find(([subjectKey]) => subjectKey === key);
  if (!subject || !/^20\d{2}\.[12]$/.test(period || '') || rest.length) return null;
  const [, code, title, group, campus, professor] = subject;
  return { id, code, title, group, campus, professor, period };
}

export async function loadDemoCatalog(periods) {
  return {
    items: periods.flatMap(period => SUBJECTS.map(([key]) => demoOffering(`${key}:${period}`))),
    stale: false,
    sourceUpdatedAt: null,
  };
}

const normalize = text => text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();

export function searchOfferings(items, period, query) {
  const terms = normalize(query).trim().split(/\s+/).filter(Boolean);
  return items.filter(course => {
    if (course.period !== period) return false;
    const searchable = normalize(`${course.title} ${course.professor} ${course.code} turma ${course.group}`);
    return terms.every(term => searchable.includes(term));
  });
}

export const offeringLabel = course => `${course.code} · Turma ${course.group} · ${course.campus} · ${course.period}`;

const storageKey = userId => `agendaunb:demo-class-follows:v1:${userId}`;

export function loadDemoFollows(userId) {
  if (!userId) return { ids: [] };
  try {
    const ids = JSON.parse(localStorage.getItem(storageKey(userId)) || '[]');
    if (!Array.isArray(ids)) return { ids: [] };
    return { ids: [...new Set(ids.filter(id => typeof id === 'string' && demoOffering(id)))] };
  } catch {
    return { ids: [], error: true };
  }
}

export function saveDemoFollows(userId, ids) {
  if (userId) localStorage.setItem(storageKey(userId), JSON.stringify(ids));
}
