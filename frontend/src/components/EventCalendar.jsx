import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { calendarDays, dateKey, movePeriod } from '../lib/calendar';

const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const fullDate = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' });
const shortDate = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' });

export default function EventCalendar({ events, loading = false, error = false }) {
  const [mode, setMode] = useState('month');
  const [reference, setReference] = useState(() => new Date());
  const days = calendarDays(reference, mode);
  const today = dateKey(new Date());
  const byDate = useMemo(() => {
    const groups = new Map();
    for (const event of events) {
      if (!groups.has(event.data)) groups.set(event.data, []);
      groups.get(event.data).push(event);
    }
    for (const group of groups.values()) {
      group.sort((a, b) => (a.horario || '').localeCompare(b.horario || '') || a.titulo.localeCompare(b.titulo, 'pt-BR'));
    }
    return groups;
  }, [events]);
  const title = mode === 'month'
    ? reference.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    : `${shortDate.format(days[0])} – ${shortDate.format(days[6])}`;
  const hasEvents = days.some(day => (mode === 'week' || day.getMonth() === reference.getMonth()) && byDate.has(dateKey(day)));

  return (
    <section className={`event-calendar event-calendar--${mode}`} aria-label="Calendário de eventos" aria-busy={loading}>
      <div className="calendar-toolbar">
        <div className="calendar-navigation">
          <button type="button" className="calendar-nav-button" aria-label={mode === 'month' ? 'Mês anterior' : 'Semana anterior'} onClick={() => setReference(date => movePeriod(date, mode, -1))}>
            <span className="material-symbols-outlined" aria-hidden="true">chevron_left</span>
          </button>
          <button type="button" className="calendar-nav-button" onClick={() => setReference(new Date())}>Hoje</button>
          <button type="button" className="calendar-nav-button" aria-label={mode === 'month' ? 'Próximo mês' : 'Próxima semana'} onClick={() => setReference(date => movePeriod(date, mode, 1))}>
            <span className="material-symbols-outlined" aria-hidden="true">chevron_right</span>
          </button>
        </div>
        <h3 className="calendar-period" aria-live="polite" aria-atomic="true">{title}</h3>
        <div className="btn-toggle-group events-view-toggle calendar-mode" role="group" aria-label="Período do calendário">
          <button type="button" className={`btn-toggle-item ${mode === 'month' ? 'active' : ''}`} aria-pressed={mode === 'month'} onClick={() => setMode('month')}>Mês</button>
          <button type="button" className={`btn-toggle-item ${mode === 'week' ? 'active' : ''}`} aria-pressed={mode === 'week'} onClick={() => setMode('week')}>Semana</button>
        </div>
      </div>
      {loading && <p className="calendar-empty" role="status">Carregando eventos…</p>}
      {!loading && !error && !hasEvents && <p className="calendar-empty" role="status">Nenhum evento encontrado neste {mode === 'month' ? 'mês' : 'período'} com os filtros atuais.</p>}
      <p className="calendar-scroll-hint">Deslize para os lados para ver todos os dias.</p>
      <div className="calendar-scroll" hidden={loading || error} tabIndex={0} role="region" aria-label="Dias e eventos. Em telas pequenas, role horizontalmente para ver todos os dias.">
        <div className="calendar-grid">
          {weekdays.map(day => <div className="calendar-weekday" key={day} aria-hidden="true">{day}</div>)}
          {days.map(day => {
            const key = dateKey(day);
            const dayEvents = byDate.get(key) || [];
            const outside = mode === 'month' && day.getMonth() !== reference.getMonth();
            return (
              <section className={`calendar-day${outside ? ' calendar-day--outside' : ''}`} key={key} aria-label={fullDate.format(day)}>
                <h4 className="calendar-day-heading">
                  <time dateTime={key} aria-current={key === today ? 'date' : undefined} className={key === today ? 'calendar-today' : ''}>{day.getDate()}</time>
                  {dayEvents.length > 0 && <span className="calendar-count" aria-label={`${dayEvents.length} eventos`}>{dayEvents.length}</span>}
                </h4>
                <ul className="calendar-events">
                  {dayEvents.map(event => (
                    <li key={`${event.visibilidade}-${event.id}`}>
                      <Link className="calendar-event" to={`/evento/${event.id}`} state={{ evento: event }}>
                        {event.horario && <span className="calendar-event-time">{event.horario}</span>}
                        <span>{event.titulo}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      </div>
    </section>
  );
}
