// Grade do SIGAA/UnB: https://design.unb.br/codigos-aulas-sigaa/
const periods = {
  M: [['08:00', '08:55'], ['08:55', '09:50'], ['10:00', '10:55'], ['10:55', '11:50'], ['12:00', '12:55']],
  T: [['12:55', '13:50'], ['14:00', '14:55'], ['14:55', '15:50'], ['16:00', '16:55'], ['16:55', '17:50'], ['18:00', '18:55']],
  N: [['19:00', '19:50'], ['19:50', '20:40'], ['20:50', '21:40'], ['21:40', '22:30']],
};

function minutes(time) {
  const [hours, mins] = time.split(':').map(Number);
  return hours * 60 + mins;
}

function blockStart(classes) {
  const slots = [...classes.entries()].sort(([a], [b]) => a.localeCompare(b));
  if (!slots.length) return '';
  // A grade da UnB tem intervalos de até 10 min entre períodos consecutivos.
  for (let index = 1; index < slots.length; index++) {
    if (minutes(slots[index][0]) - minutes(slots[index - 1][1]) > 10) return '';
  }
  return slots[0][0];
}

export function classStartOnDate(schedule, date) {
  if (typeof schedule !== 'string' || !schedule.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return '';
  const day = new Date(`${date}T00:00:00Z`);
  if (Number.isNaN(day.getTime()) || day.toISOString().slice(0, 10) !== date || date.startsWith('0000')) return '';
  const weekday = String(day.getUTCDay() + 1);
  const classes = new Map();

  for (const code of schedule.trim().toUpperCase().split(/[\s,;]+/)) {
    const match = /^([2-7]+)([MTN])([1-6]+)$/.exec(code);
    if (!match) return '';
    const [, days, shift, hours] = match;
    for (const hour of hours) {
      const period = periods[shift][Number(hour) - 1];
      if (!period) return '';
      if (days.includes(weekday)) classes.set(period[0], period[1]);
    }
  }

  return blockStart(classes);
}

export function defaultClassStart(schedule) {
  if (typeof schedule !== 'string' || !schedule.trim()) return '';
  const byDay = new Map();

  for (const code of schedule.trim().toUpperCase().split(/[\s,;]+/)) {
    const match = /^([2-7]+)([MTN])([1-6]+)$/.exec(code);
    if (!match) return '';
    const [, days, shift, hours] = match;
    for (const day of days) {
      let classes = byDay.get(day);
      if (!classes) {
        classes = new Map();
        byDay.set(day, classes);
      }
      for (const hour of hours) {
        const period = periods[shift][Number(hour) - 1];
        if (!period) return '';
        classes.set(period[0], period[1]);
      }
    }
  }

  if (!byDay.size) return '';
  const starts = new Set();
  for (const classes of byDay.values()) {
    const start = blockStart(classes);
    if (!start) return '';
    starts.add(start);
  }
  return starts.size === 1 ? [...starts][0] : '';
}
