import CustomSelect from '../components/CustomSelect';
import GoogleCalendarConnection from '../components/GoogleCalendarConnection';
import { useState, useMemo, useRef, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { eventsApi, toApiEvent, toUiEvent } from '../lib/api';
import { formatEventSchedule } from '../lib/calendar';
import {
  clearStoredEventFilters,
  getStoredEventFilters,
  getStoredTheme,
  setStoredEventFilters,
  setStoredTheme,
} from '../lib/preferences';
import NavBar from '../components/NavBar';
import EventCalendar from '../components/EventCalendar';
import EventsLoading from '../components/EventsLoading';
import { Feedback, Modal } from '../components/ManagementUI';

const DEFAULT_CATEGORIES = ['Acadêmico', 'Cultura', 'Esporte', 'Extensão', 'Lazer', 'Comunicado', 'Reunião'];

const UNB_CAMPUSES = [
  { label: 'Darcy Ribeiro', value: 'Darcy Ribeiro (Plano Piloto)' },
  { label: 'FCTE - Gama', value: 'Faculdade do Gama (FCTE)' },
  { label: 'FCTS - Ceilândia', value: 'Faculdade de Ceilândia (FCTS)' },
  { label: 'FUP - Planaltina', value: 'Faculdade de Planaltina (FUP)' },
  { label: 'FAL', value: 'Fazenda Água Limpa (FAL)' },
];

function EventError({ message, compact = false, onRetry = null }) {
  const needsAccount = message.includes('Entre na sua conta');
  return <div role="alert" className={`event-error${needsAccount ? ' event-error-auth' : ''}${compact ? ' event-error-compact' : ''}`}>
    <p>{message}</p>
    <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginLeft: 'auto', flexWrap: 'wrap' }}>
      {onRetry && (
        <button type="button" className="manage-button" onClick={onRetry}>
          Tentar novamente
        </button>
      )}
      {needsAccount && <Link className="event-error-signup" to="/?auth=signup">Criar conta</Link>}
    </div>
  </div>;
}

const CustomDatePicker = ({ value, onChange, placeholder, dropUp = false, className, wrapperWidth = '100%', ariaLabel }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const [viewDate, setViewDate] = useState(() => value ? new Date(`${value}T12:00:00`) : new Date());

  useEffect(() => {
    if (value) {
      const next = new Date(`${value}T12:00:00`);
      if (!Number.isNaN(next.getTime())) setViewDate(next);
    }
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const daysInMonth = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 0).getDate();
  const startDay = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1).getDay();

  const days = Array(startDay).fill(null).concat(Array.from({ length: daysInMonth }, (_, i) => i + 1));
  const weekDays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

  const handleSelectDate = (d) => {
    if (!d) return;
    const yyyy = viewDate.getFullYear();
    const mm = String(viewDate.getMonth() + 1).padStart(2, '0');
    const dd = String(d).padStart(2, '0');
    onChange(`${yyyy}-${mm}-${dd}`);
    setIsOpen(false);
  };

  const changeMonth = (e, offset) => {
    e.stopPropagation();
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + offset, 1));
  };

  const displayValue = value ? value.split('-').reverse().join('/') : '';

  return (
    <div ref={containerRef} onKeyDownCapture={e => {
      if (isOpen && e.key === 'Escape') {
        e.preventDefault(); e.stopPropagation(); setIsOpen(false);
        containerRef.current?.querySelector('.custom-input, .filter-pill')?.focus();
      }
    }} style={{ position: 'relative', width: wrapperWidth, zIndex: isOpen ? 1000 : 1 }}>
      <div
        className={className || 'custom-input'}
        role="button" tabIndex={0} aria-expanded={isOpen} aria-label={ariaLabel || placeholder}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsOpen(v => !v); } }}
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px',
          cursor: 'pointer', userSelect: 'none'
        }}
      >
        <span style={{ color: value ? 'inherit' : 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {displayValue || placeholder}
        </span>
        <span className="material-symbols-outlined" style={{ fontSize: '1.1rem', color: 'var(--text-muted)', flexShrink: 0 }}>calendar_today</span>
      </div>

      {isOpen && (
        <div className="custom-picker-popup" style={{
          top: dropUp ? 'auto' : 'calc(100% + 8px)', bottom: dropUp ? 'calc(100% + 8px)' : 'auto',
          width: '280px', padding: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <button type="button" aria-label="Mês anterior" onClick={(e) => changeMonth(e, -1)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: '4px', display: 'flex' }}>
              <span className="material-symbols-outlined">chevron_left</span>
            </button>
            <span style={{ fontWeight: 'bold', textTransform: 'capitalize' }}>
              {viewDate.toLocaleString('pt-BR', { month: 'long', year: 'numeric' })}
            </span>
            <button type="button" aria-label="Próximo mês" onClick={(e) => changeMonth(e, 1)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: '4px', display: 'flex' }}>
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', textAlign: 'center', marginBottom: '8px' }}>
            {weekDays.map(wd => <span key={wd} style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>{wd}</span>)}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
            {days.map((d, i) => {
              const isSelected = value && d && value === `${viewDate.getFullYear()}-${String(viewDate.getMonth() + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
              const isToday = !value && d === new Date().getDate() && viewDate.getMonth() === new Date().getMonth() && viewDate.getFullYear() === new Date().getFullYear();

              let classes = 'custom-picker-option';
              if (isSelected) classes += ' active';

              return (
                <div
                  key={i}
                  className={classes}
                  role={d ? 'button' : undefined} tabIndex={d ? 0 : undefined}
                  aria-label={d ? `${d}/${viewDate.getMonth() + 1}/${viewDate.getFullYear()}` : undefined}
                  onKeyDown={e => { if (d && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); handleSelectDate(d); } }}
                  onClick={() => handleSelectDate(d)}
                  style={{
                    height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    borderRadius: '8px', cursor: d ? 'pointer' : 'default', padding: 0,
                    border: isToday && !isSelected ? '1px solid var(--accent-color)' : '1px solid transparent',
                    color: !d ? 'transparent' : ''
                  }}
                >
                  {d}
                </div>
              );
            })}
          </div>
          {value && (
            <button
              type="button"
              onClick={() => { onChange(''); setIsOpen(false); }}
              style={{
                marginTop: '10px', width: '100%', padding: '6px', borderRadius: '8px',
                border: '1px solid var(--border-color)', background: 'transparent',
                color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600
              }}
            >
              Limpar data
            </button>
          )}
        </div>
      )}
    </div>
  );
};

const CustomTimePicker = ({ value, onChange, placeholder, dropUp = false, className }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const hourRef = useRef(null);
  const minRef = useRef(null);

  const [tempHour, setTempHour] = useState('12');
  const [tempMin, setTempMin] = useState('00');

  useEffect(() => {
    if (value) {
      const [h, m] = value.split(':');
      if (h) setTempHour(h);
      if (m) setTempMin(m);
    }
  }, [value, isOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        hourRef.current?.scrollIntoView({ block: 'center' });
        minRef.current?.scrollIntoView({ block: 'center' });
      }, 10);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
  const minutes = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));

  const handleHourClick = (h) => {
    setTempHour(h);
    onChange(`${h}:${tempMin}`);
  };

  const handleMinClick = (m) => {
    setTempMin(m);
    onChange(`${tempHour}:${m}`);
  };

  const hideScrollbarStyle = {
    msOverflowStyle: 'none',
    scrollbarWidth: 'none',
  };

  return (
    <div ref={containerRef} onKeyDownCapture={e => {
      if (isOpen && e.key === 'Escape') {
        e.preventDefault(); e.stopPropagation(); setIsOpen(false);
        containerRef.current?.querySelector('.custom-input')?.focus();
      }
    }} style={{ position: 'relative', width: '100%', zIndex: isOpen ? 1000 : 1 }}>
      <div
        className={className || 'custom-input'}
        role="button" tabIndex={0} aria-expanded={isOpen}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsOpen(v => !v); } }}
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          cursor: 'pointer', userSelect: 'none'
        }}
      >
        <span style={{ color: value ? 'inherit' : 'var(--text-muted)' }}>{value || placeholder}</span>
        <span className="material-symbols-outlined" style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>schedule</span>
      </div>

      {isOpen && (
        <div className="custom-picker-popup" style={{
          top: dropUp ? 'auto' : 'calc(100% + 8px)', bottom: dropUp ? 'calc(100% + 8px)' : 'auto',
          width: '240px', padding: '0', overflow: 'hidden'
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            padding: '14px 16px', borderBottom: '1px solid var(--border-color)',
            background: 'rgba(0, 139, 255, 0.08)'
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: '1.1rem', color: 'var(--text-color)' }}>schedule</span>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-color)' }}>
              Selecione o horário
            </span>
          </div>

          <div style={{
            display: 'flex', justifyContent: 'space-around', padding: '10px 16px 6px',
            fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)'
          }}>
            <span>Hora</span>
            <span>Minuto</span>
          </div>

          <div style={{ display: 'flex', gap: '0', height: '220px', padding: '4px 12px 12px' }}>
            <div className="time-picker-col" style={{
              flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '3px',
              paddingRight: '6px', ...hideScrollbarStyle
            }}>
              {hours.map(h => (
                <div
                  key={h} ref={tempHour === h ? hourRef : null}
                  role="button" tabIndex={0} aria-label={`Hora ${h}`}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleHourClick(h); } }}
                  onClick={() => handleHourClick(h)}
                  className="time-picker-item"
                  style={{
                    padding: '8px 0', textAlign: 'center', borderRadius: '10px', cursor: 'pointer',
                    fontSize: '0.95rem', fontWeight: tempHour === h ? 700 : 400,
                    transition: 'all 0.2s',
                    background: tempHour === h ? '#005fd2' : 'transparent',
                    color: tempHour === h ? '#ffffff' : 'var(--text-color)',
                    border: tempHour === h ? '1px solid rgba(0, 139, 255, 0.5)' : '1px solid transparent',
                  }}
                >
                  {h}
                </div>
              ))}
            </div>

            <div style={{
              width: '1px', margin: '8px 0',
              background: 'var(--border-color)',
              borderRadius: '2px'
            }}></div>

            <div className="time-picker-col" style={{
              flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '3px',
              paddingLeft: '6px', ...hideScrollbarStyle
            }}>
              {minutes.map(m => (
                <div
                  key={m} ref={tempMin === m ? minRef : null}
                  role="button" tabIndex={0} aria-label={`Minuto ${m}`}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleMinClick(m); } }}
                  onClick={() => handleMinClick(m)}
                  className="time-picker-item"
                  style={{
                    padding: '8px 0', textAlign: 'center', borderRadius: '10px', cursor: 'pointer',
                    fontSize: '0.95rem', fontWeight: tempMin === m ? 700 : 400,
                    transition: 'all 0.2s',
                    background: tempMin === m ? '#005fd2' : 'transparent',
                    color: tempMin === m ? '#ffffff' : 'var(--text-color)',
                    border: tempMin === m ? '1px solid rgba(0, 139, 255, 0.5)' : '1px solid transparent',
                  }}
                >
                  {m}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function getAreaIcon(areaName) {
  switch (areaName) {
    case 'Acadêmico': return 'school';
    case 'Cultura': return 'palette';
    case 'Esporte': return 'sports_soccer';
    case 'Extensão': return 'groups';
    case 'Lazer': return 'celebration';
    case 'Comunicado': return 'campaign';
    case 'Reunião': return 'forum';
    default: return 'event';
  }
}

function EventCardItem({
  evento,
  visaoEventos,
  canManagePublic,
  textColor,
  onOpen,
  onEdit,
  onRemove,
}) {
  const canEdit = visaoEventos === 'MEUS'
    ? Boolean(evento.criadoPorMim)
    : canManagePublic;
  const canRemove = visaoEventos === 'MEUS'
    ? (evento.criadoPorMim || evento.salvoNaAgenda)
    : canManagePublic;

  return (
    <div
      className="event-card"
      role="button"
      tabIndex={0}
      aria-label={`Abrir detalhes de ${evento.titulo}`}
      onClick={() => onOpen(evento)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpen(evento);
        }
      }}
      style={{ cursor: 'pointer' }}
    >
      <div className="event-card-icon">
        <span className="material-symbols-outlined" style={{ color: textColor }}>
          {getAreaIcon(evento.area)}
        </span>
      </div>

      <div className="event-card-body">
        <h3 className="event-card-title">{evento.titulo}</h3>
        <div className="event-card-date">
          {formatEventSchedule(evento) || `${evento.data} · ${evento.horario}`}
        </div>
        {evento.descricao && (
          <p className="event-card-desc">{evento.descricao}</p>
        )}
        <div className="event-card-footer">
          {visaoEventos === 'MEUS' && evento.criadoPorMim && (
            <span className="event-tag event-tag--personal">Compromisso privado</span>
          )}
          {evento.salvoNaAgenda && (
            <span className="event-tag event-tag--saved">Público salvo</span>
          )}
          {evento.fonteUrl && (
            <span className="event-tag" title="Fonte: Agenda UnB Notícias">
              <span className="material-symbols-outlined" style={{ fontSize: '0.9rem', flexShrink: 0 }}>newspaper</span>
              <span className="event-tag-text">UnB Notícias</span>
            </span>
          )}
          {evento.campus && (
            <span className="event-tag">
              <span className="material-symbols-outlined" style={{ fontSize: '0.9rem', flexShrink: 0 }}>location_on</span>
              <span className="event-tag-text">{evento.campus}</span>
            </span>
          )}
          {evento.local && (
            <span className="event-tag">
              <span className="material-symbols-outlined" style={{ fontSize: '0.9rem', flexShrink: 0 }}>meeting_room</span>
              <span className="event-tag-text">{evento.local}</span>
            </span>
          )}
        </div>
      </div>

      {(canEdit || canRemove) && (
        <div
          onClick={(event) => event.stopPropagation()}
          style={{ position: 'absolute', top: '12px', right: '12px', display: 'flex', gap: '6px' }}
        >
          {canEdit && (
            <button
              type="button"
              onClick={() => onEdit(evento)}
              title="Editar evento"
              aria-label={`Editar ${evento.titulo}`}
              className="event-card-delete"
              style={{ position: 'static' }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '1.1rem' }}>edit</span>
            </button>
          )}
          {canRemove && (
            <button
              type="button"
              onClick={() => onRemove(evento)}
              title={evento.salvoNaAgenda ? 'Remover dos meus eventos' : 'Excluir evento'}
              aria-label={evento.salvoNaAgenda ? `Remover ${evento.titulo} dos meus eventos` : `Excluir ${evento.titulo}`}
              className="event-card-delete"
              style={{ position: 'static' }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '1.1rem' }}>{evento.salvoNaAgenda ? 'bookmark_remove' : 'delete'}</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function SegundaPagina() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, profile, isProfessor, isAdmin } = useAuth();
  const professorId = isProfessor && !isAdmin ? user?.id : null;
  const [publishedEvents, setPublishedEvents] = useState(null);
  const [publishedEventsRevision, setPublishedEventsRevision] = useState(0);
  const canManagePublic = (event) => isAdmin || Boolean(
    professorId && publishedEvents?.userId === professorId && publishedEvents.ids.has(event.id),
  );

  // --- GERENCIAMENTO DE TEMA PERSISTENTE ---
  const [theme, setTheme] = useState(() => getStoredTheme());

  useEffect(() => {
    setStoredTheme(theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');
  const isDark = theme === 'dark';

  // --- ESTADOS DA APLICAÇÃO (COM PERSISTÊNCIA DE FILTROS) ---
  const savedFilters = useMemo(() => getStoredEventFilters(), []);
  const urlAba = searchParams.get('aba');
  const initialVisao = urlAba === 'meus' ? 'MEUS' : (urlAba === 'publicos' ? 'Públicos' : savedFilters.visaoEventos);
  const initialCachedPublic = initialVisao === 'Públicos' ? eventsApi.getCachedPublic() : null;
  const [eventos, setEventos] = useState(() => initialCachedPublic ? initialCachedPublic.map(event => toUiEvent(event)) : []);
  const [carregandoEventos, setCarregandoEventos] = useState(() => !initialCachedPublic);
  const [erroEventos, setErroEventos] = useState('');
  const [reloadRevision, setReloadRevision] = useState(0);

  const [visaoEventos, setVisaoEventos] = useState(initialVisao);
  const [modoVisualizacao, setModoVisualizacao] = useState(savedFilters.modoVisualizacao);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [savingEvent, setSavingEvent] = useState(false);
  const savingEventRef = useRef(false);
  const [suggestionSuccess, setSuggestionSuccess] = useState('');
  const [eventoEmEdicao, setEventoEmEdicao] = useState(null);
  const [eventoParaRemover, setEventoParaRemover] = useState(null);
  const [removendoEvento, setRemovendoEvento] = useState(false);
  const [categoriesList, setCategoriesList] = useState(DEFAULT_CATEGORIES);

  // Estados do Modal
  const [titulo, setTitulo] = useState('');
  const [data, setData] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [horario, setHorario] = useState('');
  const [horarioFim, setHorarioFim] = useState('');
  const [diaInteiro, setDiaInteiro] = useState(false);
  const [campus, setCampus] = useState('');
  const [local, setLocal] = useState('');
  const [area, setArea] = useState('');
  const [descricao, setDescricao] = useState('');
  const [visibilidade, setVisibilidade] = useState('');
  const [linkExterno, setLinkExterno] = useState('');

  // Estados dos Filtros
  const [searchQuery, setSearchQuery] = useState(savedFilters.searchQuery);
  const [filtroArea, setFiltroArea] = useState(savedFilters.filtroArea);
  const [filtroCampus, setFiltroCampus] = useState(savedFilters.filtroCampus);
  const [filtroTurno, setFiltroTurno] = useState(savedFilters.filtroTurno);
  const [filtroDataInicio, setFiltroDataInicio] = useState(savedFilters.filtroDataInicio);
  const [filtroDataFim, setFiltroDataFim] = useState(savedFilters.filtroDataFim);

  useEffect(() => {
    setStoredEventFilters({
      visaoEventos,
      modoVisualizacao,
      searchQuery,
      filtroArea,
      filtroCampus,
      filtroTurno,
      filtroDataInicio,
      filtroDataFim,
    });
  }, [visaoEventos, modoVisualizacao, searchQuery, filtroArea, filtroCampus, filtroTurno, filtroDataInicio, filtroDataFim]);

  useEffect(() => {
    let active = true;
    eventsApi.listCategories()
      .then(items => {
        if (!active || !Array.isArray(items) || !items.length) return;
        const names = items.map(c => c.name).filter(Boolean);
        if (names.length) setCategoriesList(names);
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  // --- DADOS BASE PARA OS DROPDOWNS ---
  const areasOptions = useMemo(
    () => categoriesList.map(a => ({ label: a, value: a })),
    [categoriesList],
  );
  const campiOptions = UNB_CAMPUSES;
  const turnoOptions = [
    { label: 'Matutino (06h - 12h)', value: 'Matutino' },
    { label: 'Vespertino (12h - 18h)', value: 'Vespertino' },
    { label: 'Noturno (18h - 06h)', value: 'Noturno' },
    { label: 'Dia inteiro', value: 'Dia inteiro' },
  ];
  const editingPublic = Boolean(
    eventoEmEdicao && eventoEmEdicao.visibilidade === 'Público' && !eventoEmEdicao.criadoPorMim,
  );
  const visibilidadeOptions = eventoEmEdicao
    ? [editingPublic ? { label: 'Público', value: 'Público' } : { label: 'Apenas para mim', value: 'Privado' }]
    : [
      ...((isProfessor || isAdmin) ? [{ label: 'Público', value: 'Público' }] : []),
      ...(profile?.papel === 'student' ? [{ label: 'Sugerir evento', value: 'Sugestão' }] : []),
      { label: 'Apenas para mim', value: 'Privado' },
    ];

  useEffect(() => {
    if (!professorId || visaoEventos !== 'Públicos') {
      setPublishedEvents(null);
      return undefined;
    }
    setPublishedEvents(current => current?.userId === professorId ? { ...current, failed: false } : null);
    let active = true;
    eventsApi.listOwnPublishedIds()
      .then((ids) => {
        if (active) setPublishedEvents(current => ({
          userId: professorId,
          ids: new Set([...ids, ...(current?.userId === professorId ? current.ids : [])]),
          failed: false,
        }));
      })
      .catch(() => {
        if (active) setPublishedEvents(current => ({
          userId: professorId,
          ids: current?.userId === professorId ? current.ids : new Set(),
          failed: true,
        }));
      });
    return () => { active = false; };
  }, [professorId, visaoEventos, publishedEventsRevision]);

  useEffect(() => {
    let active = true;
    const loadEvents = async () => {
      setErroEventos('');
      if (visaoEventos === 'MEUS') {
        if (!user) {
          setEventos([]);
          setCarregandoEventos(false);
          setErroEventos('Entre na sua conta para acessar seus eventos e compromissos.');
          return;
        }
        setCarregandoEventos(true);
        try {
          const [personal, saved] = await Promise.all([eventsApi.listPersonal(), eventsApi.listSaved()]);
          const mappedEvents = [
            ...personal.map(event => toUiEvent(event, true)),
            ...saved.map(event => ({ ...toUiEvent(event), salvoNaAgenda: true })),
          ].sort((a, b) => `${a.data}T${a.horario}`.localeCompare(`${b.data}T${b.horario}`));
          if (active) setEventos(mappedEvents);
        } catch (error) {
          if (active) setErroEventos(error.message || 'Não foi possível carregar os eventos.');
        } finally {
          if (active) setCarregandoEventos(false);
        }
        return;
      }

      const cached = eventsApi.getCachedPublic();
      if (cached) {
        setEventos(cached.map(event => toUiEvent(event)));
        setCarregandoEventos(false);
      } else {
        setCarregandoEventos(true);
      }

      try {
        const result = await eventsApi.listPublic();
        if (active) {
          setEventos(result.map(event => toUiEvent(event)));
        }
      } catch (error) {
        if (active && !cached) {
          setErroEventos(error.message || 'Não foi possível carregar os eventos.');
        }
      } finally {
        if (active) setCarregandoEventos(false);
      }
    };
    loadEvents();
    return () => { active = false; };
  }, [visaoEventos, visaoEventos === 'MEUS' ? user?.id : null, reloadRevision]);

  // --- FUNÇÕES AUXILIARES ---
  const getTurnoByEvento = (evento) => {
    if (evento.diaInteiro || evento.horario === 'Dia inteiro') return 'Dia inteiro';
    if (!evento.horario) return null;
    const [hora] = evento.horario.split(':').map(Number);
    if (Number.isNaN(hora)) return null;
    if (hora >= 6 && hora < 12) return 'Matutino';
    if (hora >= 12 && hora < 18) return 'Vespertino';
    return 'Noturno';
  };

  // --- HANDLERS ---
  const resetModal = () => {
    setTitulo('');
    setData('');
    setDataFim('');
    setHorario('');
    setHorarioFim('');
    setDiaInteiro(false);
    setCampus('');
    setLocal('');
    setArea('');
    setDescricao('');
    setVisibilidade('');
    setLinkExterno('');
    setEventoEmEdicao(null);
    setErroEventos('');
  };

  const handleAdicionarEvento = async (e) => {
    e.preventDefault();
    if (savingEventRef.current) return;
    const tituloLimpo = titulo.trim();
    if (!tituloLimpo) {
      setErroEventos('Informe o título do evento.');
      return;
    }
    if (tituloLimpo.length < 3) {
      setErroEventos('O título do evento deve ter pelo menos 3 caracteres.');
      return;
    }
    if (!data) {
      setErroEventos('Selecione uma data de início para o evento.');
      return;
    }
    if (dataFim && dataFim < data) {
      setErroEventos('A data de término não pode ser anterior à data de início.');
      return;
    }
    if (!diaInteiro && !horario) {
      setErroEventos('Selecione um horário de início ou marque como dia inteiro.');
      return;
    }
    if (!visibilidade) {
      setErroEventos('Selecione a visibilidade do evento.');
      return;
    }

    savingEventRef.current = true;
    setSavingEvent(true);
    try {
      setErroEventos('');
      const payload = toApiEvent({
        titulo,
        data,
        dataFim,
        horario,
        horarioFim,
        diaInteiro,
        campus,
        local,
        area,
        descricao,
        linkExterno,
      });
      let savedEvent;
      if (visibilidade === 'Sugestão' && !eventoEmEdicao) {
        await eventsApi.suggest(payload);
        window.dispatchEvent(new Event('suggestion-submitted'));
        setSuggestionSuccess('Sugestão enviada! Acompanhe a análise pelo sino de notificações.');
        resetModal();
        setIsModalOpen(false);
        return;
      }
      if (editingPublic) {
        if (!canManagePublic(eventoEmEdicao)) {
          throw new Error('Apenas o autor ou um administrador pode editar este evento.');
        }
        savedEvent = await eventsApi.updatePublic(eventoEmEdicao.id, payload);
      } else if (eventoEmEdicao) {
        savedEvent = await eventsApi.updatePersonal(eventoEmEdicao.id, payload);
      } else if (visibilidade === 'Público') {
        savedEvent = await eventsApi.createPublic(payload);
        if (professorId) setPublishedEvents(current => ({
          userId: professorId,
          ids: new Set([savedEvent.id, ...(current?.userId === professorId ? current.ids : [])]),
          failed: current?.userId === professorId && current.failed,
        }));
      } else {
        savedEvent = await eventsApi.createPersonal(payload);
      }

      const isPersonalResult = editingPublic ? false : (eventoEmEdicao ? true : visibilidade !== 'Público');
      const mappedEvent = toUiEvent(savedEvent, isPersonalResult);
      if (!isPersonalResult && visaoEventos !== 'Públicos') {
        setVisaoEventos('Públicos');
        setEventos([mappedEvent]);
      } else if (isPersonalResult && visaoEventos !== 'MEUS') {
        setVisaoEventos('MEUS');
        setEventos([mappedEvent]);
      } else {
        setEventos((current) => eventoEmEdicao
          ? current.map((event) => (
            event.id === mappedEvent.id && event.visibilidade === mappedEvent.visibilidade
              ? mappedEvent
              : event
          ))
          : [mappedEvent, ...current]);
      }
      resetModal();
      setIsModalOpen(false);
      setSuggestionSuccess(
        editingPublic
          ? 'Alterações no evento público salvas com sucesso.'
          : eventoEmEdicao
            ? 'Alterações no evento salvas com sucesso.'
            : visibilidade === 'Público'
              ? 'Evento público publicado na agenda.'
              : 'Compromisso privado adicionado à sua agenda.',
      );
    } catch (error) {
      setErroEventos(error.message || 'Não foi possível salvar o evento.');
    } finally {
      savingEventRef.current = false;
      setSavingEvent(false);
    }
  };

  const handleEditarEvento = (evento) => {
    const isPublicEdit = evento.visibilidade === 'Público' && !evento.criadoPorMim;
    if (isPublicEdit && !canManagePublic(evento)) return;
    setErroEventos('');
    setEventoEmEdicao(evento);
    setTitulo(evento.titulo);
    setData(evento.data);
    setDiaInteiro(Boolean(evento.diaInteiro));
    setDataFim(evento.dataFim && evento.dataFim !== evento.data ? evento.dataFim : '');
    setHorario(evento.diaInteiro ? '' : (evento.horario || ''));
    setHorarioFim(evento.diaInteiro ? '' : (evento.horarioFim || ''));
    setCampus(evento.campus);
    setLocal(evento.local);
    setArea(evento.area);
    setDescricao(evento.descricao);
    setVisibilidade(isPublicEdit ? 'Público' : 'Privado');
    setLinkExterno(isPublicEdit ? (evento.linkExterno || '') : '');
    setIsModalOpen(true);
  };

  const handleSolicitarRemocao = (evento) => {
    setErroEventos('');
    setEventoParaRemover(evento);
  };

  const handleConfirmarRemocao = async () => {
    if (!eventoParaRemover || removendoEvento) return;
    const evento = eventoParaRemover;
    const idParaRemover = evento.id;
    setRemovendoEvento(true);
    try {
      setErroEventos('');
      if (visaoEventos === 'MEUS' && evento.salvoNaAgenda) {
        await eventsApi.removeSaved(idParaRemover);
        setSuggestionSuccess(`"${evento.titulo}" foi removido dos seus eventos salvos.`);
      } else if (visaoEventos === 'MEUS') {
        await eventsApi.deletePersonal(idParaRemover);
        setSuggestionSuccess(`Compromisso "${evento.titulo}" excluído da sua agenda.`);
      } else {
        await eventsApi.deletePublic(idParaRemover);
        setSuggestionSuccess(`Evento público "${evento.titulo}" excluído do catálogo.`);
      }
      setEventos((current) => current.filter((event) => !(event.id === idParaRemover && event.visibilidade === evento.visibilidade)));
      setEventoParaRemover(null);
    } catch (error) {
      setErroEventos(error.message || 'Não foi possível excluir o evento.');
      setEventoParaRemover(null);
    } finally {
      setRemovendoEvento(false);
    }
  };

  const clearAllFilters = () => {
    setSearchQuery('');
    setFiltroArea([]);
    setFiltroCampus([]);
    setFiltroTurno([]);
    setFiltroDataInicio('');
    setFiltroDataFim('');
    clearStoredEventFilters();
  };

  const hasActiveFilters = Boolean(
    searchQuery
    || filtroArea.length
    || filtroCampus.length
    || filtroTurno.length
    || filtroDataInicio
    || filtroDataFim,
  );

  // --- LÓGICA DE FILTRAGEM ---
  const eventosFiltrados = useMemo(() => {
    const queryLower = searchQuery.trim().toLowerCase();
    return eventos.filter(evento => {
      const matchVisao = visaoEventos === 'Públicos' ? evento.visibilidade === 'Público' : evento.criadoPorMim || evento.salvoNaAgenda;
      const matchBusca = !queryLower || `${evento.titulo} ${evento.descricao || ''} ${evento.local || ''}`.toLowerCase().includes(queryLower);
      const matchArea = filtroArea.length ? filtroArea.includes(evento.area) : true;
      const matchCampus = filtroCampus.length ? filtroCampus.includes(evento.campus) : true;
      const matchTurno = filtroTurno.length ? filtroTurno.includes(getTurnoByEvento(evento)) : true;
      const evInicio = evento.data || '';
      const evFim = evento.dataFim || evInicio;
      const matchDataInicio = filtroDataInicio ? (evFim ? evFim >= filtroDataInicio : false) : true;
      const matchDataFim = filtroDataFim ? (evInicio ? evInicio <= filtroDataFim : false) : true;

      return matchVisao && matchBusca && matchArea && matchCampus && matchTurno && matchDataInicio && matchDataFim;
    });
  }, [eventos, visaoEventos, searchQuery, filtroArea, filtroCampus, filtroTurno, filtroDataInicio, filtroDataFim]);

  // --- ESTILIZAÇÃO DINÂMICA ---
  const bgColor = isDark ? '#080c16' : '#f0f4f8';
  const cardBg = isDark ? '#1a2235' : '#ffffff';
  const textColor = isDark ? '#ffffff' : '#1a1a2e';
  const textMuted = isDark ? '#94a3b8' : '#64748b';
  const accentColor = '#008bff';
  const borderColor = isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.15)';

  return (
    <div style={{ minHeight: '100vh', backgroundColor: bgColor, color: textColor, paddingBottom: '4rem', transition: 'background-color 0.3s' }}>

      <NavBar pageType="second" isDark={isDark} toggleTheme={toggleTheme} />

      <main className="events-page" style={{ maxWidth: '1200px', margin: '0 auto', padding: '8rem 1.5rem 2rem' }}>

        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '2.5rem' }}>
          <div className="btn-toggle-group">
            <button
              type="button"
              onClick={() => setVisaoEventos('Públicos')}
              className={`btn-toggle-item ${visaoEventos === 'Públicos' ? 'active' : ''}`}
            >
              Eventos Públicos
            </button>
            <button
              type="button"
              onClick={() => setVisaoEventos('MEUS')}
              className={`btn-toggle-item ${visaoEventos === 'MEUS' ? 'active' : ''}`}
            >
              Meus Eventos
            </button>
          </div>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 280px', minWidth: 0, position: 'relative' }}>
              <span className="material-symbols-outlined" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: textMuted }}>search</span>
              <input
                type="text" aria-label="Buscar eventos e comunicados" placeholder="Busque eventos, locais ou comunicados..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%', padding: '16px 20px 16px 48px', borderRadius: '24px',
                  border: `1px solid ${borderColor}`, background: cardBg, color: textColor, fontSize: '1.05rem',
                  boxShadow: isDark ? '0 4px 20px rgba(0,0,0,0.2)' : '0 4px 15px rgba(0,0,0,0.05)', outline: 'none'
                }}
              />
            </div>
            {user && (
              <button
                type="button"
                onClick={() => {
                  resetModal();
                  setVisibilidade(isProfessor || isAdmin ? 'Público' : 'Privado');
                  setIsModalOpen(true);
                }}
                style={{
                  padding: '0 24px', borderRadius: '26px', background: accentColor,
                  color: '#fff', border: 'none', fontWeight: 600, fontSize: '1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                  boxShadow: '0 4px 15px rgba(0, 140, 255, 0.19)', height: '56px'
                }}
              >
                <span className="material-symbols-outlined">add</span>
                Criar Evento
              </button>
            )}
          </div>

          <div className="events-filters-bar" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center', zIndex: 11, position: 'relative' }}>
            <span className="events-filters-label" style={{ color: textMuted, fontSize: '0.9rem', fontWeight: 600, marginRight: '4px' }}>Filtros:</span>

            <CustomSelect
              options={areasOptions} value={filtroArea} onChange={setFiltroArea} placeholder="Todas as áreas"
              className="filter-pill" wrapperWidth="fit-content" ariaLabel="Filtrar por área" multiple
            />
            <CustomSelect
              options={campiOptions} value={filtroCampus} onChange={setFiltroCampus} placeholder="Qualquer campus"
              className="filter-pill" wrapperWidth="fit-content" ariaLabel="Filtrar por campus" multiple
            />
            <CustomSelect
              options={turnoOptions} value={filtroTurno} onChange={setFiltroTurno} placeholder="Qualquer turno"
              className="filter-pill" wrapperWidth="fit-content" ariaLabel="Filtrar por turno" multiple
            />
            <CustomDatePicker
              value={filtroDataInicio}
              onChange={setFiltroDataInicio}
              placeholder="De (início)"
              className="filter-pill"
              wrapperWidth="165px"
              ariaLabel="Filtrar a partir da data"
            />
            <CustomDatePicker
              value={filtroDataFim}
              onChange={setFiltroDataFim}
              placeholder="Até (término)"
              className="filter-pill"
              wrapperWidth="165px"
              ariaLabel="Filtrar até a data"
            />

            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearAllFilters}
                style={{ background: 'transparent', border: 'none', color: accentColor, cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, padding: '8px', marginLeft: 'auto' }}
              >
                Limpar Filtros
              </button>
            )}
          </div>
        </div>

        <Feedback success={suggestionSuccess} />
        <div className="events-section-header">
          <h2 className="events-section-title">
            {visaoEventos === 'MEUS' ? 'MEUS EVENTOS' : 'EVENTOS PÚBLICOS'}
            <span className="material-symbols-outlined" aria-hidden="true" style={{ color: accentColor, fontSize: '1.4rem' }}>event</span>
          </h2>
          <div className="events-section-actions">
            {user && visaoEventos === 'MEUS' && (
              <GoogleCalendarConnection key={user.id} callbackResult={searchParams.get('google_calendar')} events={carregandoEventos || erroEventos ? [] : eventosFiltrados} />
            )}
            <div className="btn-toggle-group events-view-toggle" role="group" aria-label="Visualização dos eventos">
              <button
                type="button"
                className={`btn-toggle-item ${modoVisualizacao === 'lista' ? 'active' : ''}`}
                aria-pressed={modoVisualizacao === 'lista'}
                onClick={() => setModoVisualizacao('lista')}
              >
                Lista
              </button>
              <button
                type="button"
                className={`btn-toggle-item ${modoVisualizacao === 'calendario' ? 'active' : ''}`}
                aria-pressed={modoVisualizacao === 'calendario'}
                onClick={() => setModoVisualizacao('calendario')}
              >
                Calendário
              </button>
            </div>
          </div>
        </div>

        {erroEventos && (
          <EventError message={erroEventos} onRetry={() => setReloadRevision(v => v + 1)} />
        )}
        {visaoEventos === 'Públicos' && professorId && publishedEvents?.userId === professorId && publishedEvents.failed && (
          <EventError
            message="Não foi possível consultar quais eventos públicos você pode gerenciar."
            onRetry={() => setPublishedEventsRevision(value => value + 1)}
          />
        )}

        {modoVisualizacao === 'calendario' ? (
          <EventCalendar
            events={eventosFiltrados}
            loading={carregandoEventos}
            error={Boolean(erroEventos)}
            hasActiveFilters={hasActiveFilters}
            onClearFilters={clearAllFilters}
          />
        ) : carregandoEventos ? (
          <EventsLoading />
        ) : erroEventos ? null : eventosFiltrados.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 2rem', background: cardBg, borderRadius: '24px', border: `1px dashed ${borderColor}` }}>
            <span className="material-symbols-outlined" style={{ fontSize: '3rem', color: textMuted, marginBottom: '1rem' }}>event_busy</span>
            <h3 style={{ color: textColor, marginBottom: '0.5rem' }}>Nenhum evento encontrado</h3>
            <p style={{ color: textMuted, marginBottom: '1rem', fontSize: '0.95rem' }}>
              {hasActiveFilters
                ? 'Nenhum evento corresponde à combinação atual de filtros.'
                : visaoEventos === 'MEUS'
                  ? 'Você ainda não possui compromissos pessoais ou eventos salvos na sua agenda.'
                  : 'Nenhum evento público cadastrado no momento.'}
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearAllFilters}
                  style={{
                    padding: '10px 20px', borderRadius: '12px',
                    background: accentColor, color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600,
                  }}
                >
                  Limpar filtros
                </button>
              )}
              {user && !hasActiveFilters && (
                <button
                  type="button"
                  onClick={() => {
                    resetModal();
                    setVisibilidade(visaoEventos === 'MEUS' ? 'Privado' : (isProfessor || isAdmin ? 'Público' : 'Privado'));
                    setIsModalOpen(true);
                  }}
                  style={{
                    padding: '10px 20px', borderRadius: '12px',
                    background: accentColor, color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600,
                  }}
                >
                  Criar evento
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="events-grid">
            {eventosFiltrados.map((evento) => (
              <EventCardItem
                key={`${evento.visibilidade}-${evento.id}`}
                evento={evento}
                visaoEventos={visaoEventos}
                canManagePublic={canManagePublic(evento)}
                textColor={textColor}
                onOpen={ev => navigate(`/evento/${ev.id}`, { state: { evento: ev } })}
                onEdit={handleEditarEvento}
                onRemove={handleSolicitarRemocao}
              />
            ))}
          </div>
        )}
      </main>

      {isModalOpen && (
        <Modal
          className="event-create-dialog"
          title={eventoEmEdicao ? (editingPublic ? 'Editar Evento Público' : 'Editar Evento Pessoal') : 'Novo Evento'}
          busy={savingEvent}
          onClose={() => { setIsModalOpen(false); resetModal(); }}
        >
            <form onSubmit={handleAdicionarEvento} className="modal-form">
              {erroEventos && (
                <EventError message={erroEventos} compact />
              )}

              <div>
                <label htmlFor="event-title" className="modal-label">TÍTULO DO EVENTO *</label>
                <input id="event-title" type="text" required minLength={3} maxLength={200} value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Dê um título breve para o seu evento..." className="custom-input" />
              </div>
              <div>
                <label htmlFor="event-description" className="modal-label">DESCRIÇÃO</label>
                <textarea id="event-description" maxLength={10000} value={descricao} onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Forneça mais detalhes..." className="custom-input event-description-input" />
              </div>

              <label htmlFor="event-all-day" style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 600, fontSize: '0.92rem' }}>
                <input
                  id="event-all-day"
                  type="checkbox"
                  checked={diaInteiro}
                  onChange={e => {
                    const checked = e.target.checked;
                    setDiaInteiro(checked);
                    if (checked) {
                      setHorario('');
                      setHorarioFim('');
                    }
                  }}
                  style={{ width: '18px', height: '18px', accentColor }}
                />
                Evento de dia inteiro
              </label>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="modal-label">DATA DE INÍCIO *</label>
                  <CustomDatePicker value={data} onChange={setData} placeholder="dd/mm/aaaa" className="custom-input" />
                </div>
                {!diaInteiro && (
                  <div>
                    <label className="modal-label">HORÁRIO DE INÍCIO *</label>
                    <CustomTimePicker value={horario} onChange={setHorario} placeholder="-- : --" className="custom-input" />
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="modal-label">DATA DE TÉRMINO (OPCIONAL)</label>
                  <CustomDatePicker value={dataFim} onChange={setDataFim} placeholder="Mesmo dia ou término" className="custom-input" />
                </div>
                {!diaInteiro && (
                  <div>
                    <label className="modal-label">HORÁRIO DE TÉRMINO (OPCIONAL)</label>
                    <CustomTimePicker value={horarioFim} onChange={setHorarioFim} placeholder="-- : --" className="custom-input" />
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="modal-label">CAMPUS</label>
                  <CustomSelect options={campiOptions} value={campus} onChange={setCampus} placeholder="Selecione..." ariaLabel="Campus" dropUp />
                </div>
                <div>
                  <label className="modal-label">ÁREA</label>
                  <CustomSelect options={areasOptions} value={area} onChange={setArea} placeholder="Selecione..." ariaLabel="Área" dropUp />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label htmlFor="event-location" className="modal-label">LOCAL EXATO</label>
                  <input id="event-location" type="text" maxLength={250} value={local} onChange={(e) => setLocal(e.target.value)} placeholder="Ex: Auditório, S9, MOCAP..." className="custom-input" />
                </div>
                <div>
                  <span className="modal-label">VISIBILIDADE *</span>
                  <CustomSelect
                    options={visibilidadeOptions}
                    value={visibilidade}
                    onChange={setVisibilidade}
                    placeholder="Selecione..."
                    ariaLabel="Visibilidade"
                    allowClear={!eventoEmEdicao}
                    disabled={Boolean(eventoEmEdicao)}
                    dropUp
                  />
                </div>
              </div>
              {visibilidade === 'Sugestão' && <p id="suggestion-help" className="management-muted">Seu evento será analisado por professores e administradores antes da publicação. Você receberá a confirmação e o resultado pelo sino de notificações.</p>}
              <div>
                <label htmlFor="event-url" className="modal-label">LINK EXTERNO</label>
                <input id="event-url" type="url" maxLength={2000} value={linkExterno} onChange={(e) => setLinkExterno(e.target.value)} placeholder="Ex: https://sigaa.unb.br/..." className="custom-input" />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '1rem' }}>
                <button type="button" disabled={savingEvent} onClick={() => { setIsModalOpen(false); resetModal(); }} style={{ padding: '12px 20px', borderRadius: '16px', background: 'transparent', color: textMuted, border: `1px solid ${borderColor}`, cursor: 'pointer', fontWeight: 600 }}>
                  Cancelar
                </button>
                <button type="submit" disabled={savingEvent} style={{ padding: '12px 24px', borderRadius: '16px', background: 'rgba(0, 95, 210, 1)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600, boxShadow: '0 4px 15px rgba(0, 139, 255, 0.3)' }}>
                  {savingEvent ? 'Enviando…' : eventoEmEdicao ? 'Salvar alterações' : visibilidade === 'Sugestão' ? 'Enviar sugestão' : 'Salvar Evento'}
                </button>
              </div>
            </form>
        </Modal>
      )}
      {eventoParaRemover && (
        <Modal
          title={eventoParaRemover.salvoNaAgenda ? 'Remover dos meus eventos' : 'Confirmar exclusão'}
          busy={removendoEvento}
          onClose={() => { if (!removendoEvento) setEventoParaRemover(null); }}
        >
          <p className="dialog-event-title">{eventoParaRemover.titulo}</p>
          <p className="management-muted" style={{ marginBottom: '16px' }}>
            {visaoEventos === 'MEUS' && eventoParaRemover.salvoNaAgenda
              ? 'Este evento público deixará de aparecer na sua agenda pessoal, mas continuará disponível no catálogo público.'
              : visaoEventos === 'MEUS'
                ? 'Este compromisso particular será excluído permanentemente da sua agenda.'
                : 'Este evento público será excluído permanentemente do catálogo para toda a comunidade.'}
          </p>
          <footer className="dialog-actions">
            <button
              type="button"
              className="manage-button"
              disabled={removendoEvento}
              onClick={() => setEventoParaRemover(null)}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="manage-button primary"
              disabled={removendoEvento}
              onClick={handleConfirmarRemocao}
            >
              {removendoEvento
                ? 'Processando…'
                : eventoParaRemover.salvoNaAgenda
                  ? 'Remover da agenda'
                  : 'Confirmar exclusão'}
            </button>
          </footer>
        </Modal>
      )}
    </div>
  );
}
