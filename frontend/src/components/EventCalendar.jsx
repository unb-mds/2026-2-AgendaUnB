import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { calendarDays, dateKey, eventDateKeys, movePeriod } from '../lib/calendar';
import EventsLoading from './EventsLoading';

const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const fullDate = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' });
const shortDate = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' });

function getEventKindBadge(event) {
  if (event.criadoPorMim) {
    return { label: 'Privado', className: 'calendar-event--personal' };
  }
  if (event.salvoNaAgenda) {
    return { label: 'Salvo', className: 'calendar-event--saved' };
  }
  return { label: null, className: 'calendar-event--public' };
}

function getCalendarTimeLabel(event, dayIndex, totalDays) {
  if (event.diaInteiro) {
    return totalDays > 1 ? `Dia inteiro (${dayIndex + 1}/${totalDays})` : 'Dia inteiro';
  }
  if (totalDays > 1) {
    if (dayIndex === 0) return `${event.horario || ''} · Início`.trim();
    if (dayIndex === totalDays - 1 && event.horarioFim) return `Até ${event.horarioFim}`;
    return `Dia ${dayIndex + 1}/${totalDays}`;
  }
  if (event.horario && event.horarioFim && event.horarioFim !== event.horario) {
    return `${event.horario} – ${event.horarioFim}`;
  }
  return event.horario || '';
}

export default function EventCalendar({
  events,
  loading = false,
  error = false,
  hasActiveFilters = false,
  onClearFilters = null,
}) {
  const [mode, setMode] = useState('month');
  const [reference, setReference] = useState(() => new Date());
  const days = calendarDays(reference, mode);
  const today = dateKey(new Date());
  const byDate = useMemo(() => {
    const groups = new Map();
    for (const event of events) {
      const keys = eventDateKeys(event);
      keys.forEach((key, index) => {
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push({
          event,
          dayIndex: index,
          totalDays: keys.length,
        });
      });
    }
    for (const group of groups.values()) {
      group.sort((a, b) => {
        if (a.event.diaInteiro !== b.event.diaInteiro) {
          return a.event.diaInteiro ? -1 : 1;
        }
        return (a.event.horario || '').localeCompare(b.event.horario || '')
          || a.event.titulo.localeCompare(b.event.titulo, 'pt-BR');
      });
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
      {loading && <EventsLoading />}
      {!loading && !error && !hasEvents && (
        <div className="calendar-empty" role="status">
          <p>Nenhum evento encontrado neste {mode === 'month' ? 'mês' : 'período'} com os filtros atuais.</p>
          {hasActiveFilters && onClearFilters && (
            <button type="button" className="manage-button" onClick={onClearFilters} style={{ marginTop: '8px' }}>
              Limpar filtros
            </button>
          )}
        </div>
      )}
      <p className="calendar-scroll-hint">Deslize para os lados para ver todos os dias.</p>
      <div className="calendar-scroll" hidden={loading || error} tabIndex={0} role="region" aria-label="Dias e eventos. Em telas pequenas, role horizontalmente para ver todos os dias.">
        <div className="calendar-grid">
          {weekdays.map(day => <div className="calendar-weekday" key={day} aria-hidden="true">{day}</div>)}
          {days.map(day => {
            const key = dateKey(day);
            const dayEntries = byDate.get(key) || [];
            const outside = mode === 'month' && day.getMonth() !== reference.getMonth();
            return (
              <section className={`calendar-day${outside ? ' calendar-day--outside' : ''}`} key={key} aria-label={fullDate.format(day)}>
                <h4 className="calendar-day-heading">
                  <time dateTime={key} aria-current={key === today ? 'date' : undefined} className={key === today ? 'calendar-today' : ''}>{day.getDate()}</time>
                  {dayEntries.length > 0 && <span className="calendar-count" aria-label={`${dayEntries.length} ${dayEntries.length === 1 ? 'evento' : 'eventos'}`}>{dayEntries.length}</span>}
                </h4>
                <ul className="calendar-events">
                  {dayEntries.map(({ event, dayIndex, totalDays }) => {
                    const kind = getEventKindBadge(event);
                    const timeLabel = getCalendarTimeLabel(event, dayIndex, totalDays);
                    return (
                      <li key={`${event.visibilidade}-${event.id}-${key}`}>
                        <Link className={`calendar-event ${kind.className}`} to={`/evento/${event.id}`} state={{ evento: event }}>
                          <div className="calendar-event-meta">
                            {timeLabel && <span className="calendar-event-time">{timeLabel}</span>}
                            {kind.label && <span className="calendar-event-badge">{kind.label}</span>}
                          </div>
                          <span className="calendar-event-title">{event.titulo}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      </div>
    </section>
  );
}
