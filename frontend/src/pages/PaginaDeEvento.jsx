import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { eventsApi, toUiEvent } from '../lib/api';
import { formatEventSchedule } from '../lib/calendar';
import { safeEventUrl } from '../lib/moderation';
import { getStoredTheme, setStoredTheme } from '../lib/preferences';
import NavBar from '../components/NavBar';
import SaveEventButton from '../components/SaveEventButton';
import SearchMetadata from '../components/SearchMetadata.jsx';
import { eventDescription, eventTitle } from '../lib/searchPages.js';
import '../styles/global.css';

function createClickId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, char => {
    const rand = Math.floor(Math.random() * 16);
    const val = char === 'x' ? rand : (rand & 0x3) | 0x8;
    return val.toString(16);
  });
}

export default function PaginaDeEvento() {
  const { id } = useParams();
  const { user, profile } = useAuth();
  const location = useLocation();
  const eventoState = location.state?.evento;
  const [eventoCarregado, setEventoCarregado] = useState(eventoState || null);
  const [carregandoEvento, setCarregandoEvento] = useState(!eventoState);
  const [erroEvento, setErroEvento] = useState('');

  const [interessados, setInteressados] = useState(() => eventoState?.interessadosCount ?? 0);
  const [salvoNaAgenda, setSalvoNaAgenda] = useState(() => Boolean(eventoState?.salvoNaAgenda));
  const [outboundError, setOutboundError] = useState('');
  const [registeringClick, setRegisteringClick] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const [theme, setTheme] = useState(() => getStoredTheme());

  useEffect(() => {
    setStoredTheme(theme);
  }, [theme]);

  useEffect(() => {
    setOutboundError('');
  }, [id]);

  useEffect(() => {
    if (eventoCarregado) {
      setInteressados(eventoCarregado.interessadosCount ?? 0);
      if (typeof eventoCarregado.salvoNaAgenda === 'boolean') {
        setSalvoNaAgenda(eventoCarregado.salvoNaAgenda);
      }
    }
  }, [eventoCarregado]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');
  const isDark = theme === 'dark';

  useEffect(() => {
    if (eventoState) {
      setEventoCarregado(eventoState);
      setCarregandoEvento(false);
      return undefined;
    }

    let active = true;
    const loadEvent = async () => {
      setCarregandoEvento(true);
      setErroEvento('');
      try {
        let result;
        let isPersonal = false;
        try {
          result = await eventsApi.getPublic(id);
        } catch (publicError) {
          if (!user) throw publicError;
          result = await eventsApi.getPersonal(id);
          isPersonal = true;
        }
        if (active) setEventoCarregado(toUiEvent(result, isPersonal));
      } catch (error) {
        if (active) setErroEvento(error.message || 'Não foi possível carregar o evento.');
      } finally {
        if (active) setCarregandoEvento(false);
      }
    };
    loadEvent();
    return () => { active = false; };
  }, [id, user?.id, eventoState]);

  const getOrganizadorInfo = () => {
    if (eventoCarregado?.organizadorNome) {
      return {
        nome: eventoCarregado.organizadorNome,
        foto: eventoCarregado.organizadorFoto,
        iniciais: eventoCarregado.organizadorNome.charAt(0).toUpperCase()
      };
    }
    if (eventoCarregado?.fonte === 'agenda_unb_noticias' || eventoCarregado?.fonteUrl) {
      return {
        nome: 'Agenda UnB Notícias',
        foto: '/Logo-AgendaUnB1.png',
        iniciais: 'U',
        isFonteInstitucional: true,
      };
    }
    if (eventoCarregado?.criadoPorMim && user) {
      const nome = profile?.nome_completo || user.user_metadata?.nome_completo || user.user_metadata?.full_name || user.user_metadata?.name || user.email || 'Organizador';
      return {
        nome,
        foto: profile?.avatar_url || user.user_metadata?.avatar_url || user.user_metadata?.picture || null,
        iniciais: nome.charAt(0).toUpperCase()
      };
    }
    return {
      nome: 'Comunidade UnB',
      foto: null,
      iniciais: 'U'
    };
  };

  const organizador = getOrganizadorInfo() || { nome: 'Organizador', foto: null, iniciais: 'O' };

  const dataEvento = eventoCarregado || {};
  const scheduleLabel = formatEventSchedule(dataEvento) || (dataEvento.data ? `${dataEvento.data}${dataEvento.horario ? ` · ${dataEvento.horario}` : ''}` : 'Data não informada');
  const safeExternalLink = safeEventUrl(dataEvento.linkExterno);
  const isPersonalEvent = Boolean(dataEvento.criadoPorMim || dataEvento.visibilidade === 'Privado');
  const kindBadgeLabel = isPersonalEvent
    ? 'Compromisso privado'
    : salvoNaAgenda
      ? 'Público salvo na agenda'
      : 'Evento público';

  const evento = {
    titulo: dataEvento.titulo || 'Evento',
    data: scheduleLabel,
    campus: dataEvento.campus || '',
    local: dataEvento.local || '',
    categoria: dataEvento.area || 'Evento',
    organizador,
    descricao: dataEvento.descricao || 'Sem descrição disponível.',
    linkOriginal: safeExternalLink,
  };

  const handleConferir = async () => {
    if (!evento.linkOriginal || registeringClick) return;
    setOutboundError('');
    window.open(evento.linkOriginal, '_blank', 'noopener,noreferrer');

    if (isPersonalEvent) return;
    setRegisteringClick(true);
    try {
      const result = await eventsApi.registerOutboundClick(id, createClickId());
      if (typeof result?.outbound_clicks_count === 'number') {
        setInteressados(result.outbound_clicks_count);
      }
    } catch (error) {
      setOutboundError(error.message || 'Não foi possível registrar o acesso ao link oficial.');
    } finally {
      setRegisteringClick(false);
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const renderDescricao = () => {
    return evento.descricao.split('\n\n').map((para, idx) => {
      if (para.startsWith('**')) {
        return <h2 key={idx} style={{
          marginTop: '1.75rem',
          marginBottom: '0.75rem',
          fontWeight: 700,
          fontSize: '1.2rem',
          color: isDark ? '#fff' : '#1a1a2e',
          paddingBottom: '0.4rem',
          borderBottom: '1px solid var(--border-color)'
        }}>{para.replace(/\*\*/g, '')}</h2>;
      }
      if (para.startsWith('-')) {
        return (
          <ul key={idx} className="event-list" style={{ color: isDark ? '#e2e8f0' : '#1e293b' }}>
            {para.split('\n').map((item, i) => (
              <li key={i} style={{ paddingLeft: '0.5rem', marginBottom: '0.75rem' }}>{item.replace('-', '').trim()}</li>
            ))}
          </ul>
        );
      }
      return <p key={idx} style={{ color: isDark ? '#e2e8f0' : '#1e293b', fontSize: '1.05rem', lineHeight: '1.8' }}>{para}</p>;
    });
  };

  if (carregandoEvento) {
    return <main role="status" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>Carregando evento…</main>;
  }

  if (erroEvento) {
    return (
      <main role="alert" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '2rem', textAlign: 'center' }}>
        <div>
          <SearchMetadata />
          <p>{erroEvento}</p>
          <Link to="/eventos">Voltar aos eventos</Link>
        </div>
      </main>
    );
  }

  return (
    <div className="event-page-wrapper" style={{ position: 'relative', overflow: 'hidden' }}>
      <SearchMetadata event={eventoCarregado?.visibilidade === 'Público' ? {
        title: eventTitle(evento.titulo),
        description: eventDescription({
          title: evento.titulo,
          description: eventoCarregado.descricao,
          location: eventoCarregado.local,
          campus: eventoCarregado.campus,
        }),
      } : undefined} />

      <NavBar pageType="evento" isDark={isDark} toggleTheme={toggleTheme} />

      <main className="event-page-content" style={{ position: 'relative', zIndex: 1 }}>
        <div className="event-main-col">
          <div className="event-header">
            <div className="event-badges">
              <span className="ds-section-label" style={{
                background: 'rgba(0, 139, 255, 1)',
                color: '#fff',
                borderColor: 'transparent',
                boxShadow: '0 4px 15px rgba(0, 139, 255, 0.35)'
              }}>{evento.categoria}</span>
              <span className="ds-section-label campus-badge">{kindBadgeLabel}</span>
              {evento.campus && (
                <span className="ds-section-label campus-badge" style={{
                  color: isDark ? 'rgba(255,255,255,0.8)' : 'rgba(26,26,46,0.8)',
                  borderColor: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)',
                  background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
                }}>{evento.campus}</span>
              )}
              {dataEvento.diaInteiro && (
                <span className="ds-section-label campus-badge">Dia inteiro</span>
              )}
            </div>
            <h1 className="event-title" style={{
              color: isDark ? '#fff' : '#1a1a2e',
              textShadow: isDark ? '0 0 30px rgba(0,139,255,0.25)' : 'none',
              fontSize: 'clamp(2.5rem, 5vw, 4rem)',
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              marginBottom: '2.5rem'
            }}>{evento.titulo}</h1>

            <div className="event-organizer-box" style={{ borderColor: isDark ? 'rgba(0, 139, 255, 0.15)' : 'rgba(0, 139, 255, 0.2)' }}>
              <div className="organizer-avatar">
                {evento.organizador.foto ? (
                  <img
                    src={evento.organizador.foto}
                    alt={evento.organizador.nome}
                    style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }}
                  />
                ) : (
                  evento.organizador.iniciais
                )}
              </div>
              <div className="organizer-info">
                <span className="org-label" style={{ color: isDark ? '#b0bfd0' : '#475569' }}>
                  {evento.organizador.isFonteInstitucional ? 'Fonte Oficial' : 'Organizado por'}
                </span>
                <span className="org-name" style={{ color: isDark ? '#fff' : '#1a1a2e', fontSize: '1.1rem' }}>{evento.organizador.nome}</span>
              </div>
            </div>

            {dataEvento.origem && (
              <div
                className="event-provenance-box"
                style={{
                  marginTop: '1rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '12px',
                  background: isDark ? 'rgba(0, 139, 255, 0.08)' : 'rgba(0, 139, 255, 0.06)',
                  border: `1px solid ${isDark ? 'rgba(0, 139, 255, 0.2)' : 'rgba(0, 139, 255, 0.18)'}`,
                  fontSize: '0.95rem',
                }}
              >
                <span className="material-symbols-outlined icon-blue" style={{ fontSize: '1.2rem' }}>description</span>
                <span style={{ color: isDark ? 'rgba(255, 255, 255, 0.75)' : 'rgba(26, 26, 46, 0.75)' }}>
                  Importado de plano de ensino
                  {dataEvento.origem.page ? ` · Página ${dataEvento.origem.page}` : ''}
                  {dataEvento.origem.excerpt ? `: “${dataEvento.origem.excerpt}”` : ''}
                </span>
              </div>
            )}

            {eventoCarregado?.fonteUrl && (
              <div
                className="event-provenance-box"
                style={{
                  marginTop: '1rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '12px',
                  background: isDark ? 'rgba(0, 139, 255, 0.08)' : 'rgba(0, 139, 255, 0.06)',
                  border: `1px solid ${isDark ? 'rgba(0, 139, 255, 0.2)' : 'rgba(0, 139, 255, 0.18)'}`,
                  fontSize: '0.95rem',
                }}
              >
                <span className="material-symbols-outlined icon-blue" style={{ fontSize: '1.2rem' }}>verified</span>
                <span style={{ color: isDark ? 'rgba(255, 255, 255, 0.75)' : 'rgba(26, 26, 46, 0.75)' }}>
                  Origem institucional:{' '}
                  <a
                    href={eventoCarregado.fonteUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#008bff', fontWeight: 600, textDecoration: 'underline' }}
                  >
                    Agenda UnB Notícias
                  </a>
                </span>
              </div>
            )}
          </div>

          <div className="event-body">
            {renderDescricao()}
          </div>
        </div>

        <aside className="event-side-col">
          <div className="event-action-card" style={{
            background: isDark ? 'rgba(8, 12, 22, 0.78)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(0, 139, 255, 0.15)' : 'rgba(0, 139, 255, 0.25)',
            boxShadow: isDark ? '0 16px 32px rgba(0, 0, 0, 0.2), 0 0 28px rgba(0, 139, 255, 0.12)' : '0 10px 24px rgba(0, 0, 0, 0.08)'
          }}>
            <div className="event-info-line" style={{ color: isDark ? '#fff' : '#1a1a2e' }}>
              <span className="material-symbols-outlined icon-blue" style={{ fontSize: '1.6rem' }}>calendar_month</span>
              <span style={{ fontWeight: 600 }}>{evento.data}</span>
            </div>
            <div className="event-info-line" style={{ color: isDark ? '#fff' : '#1a1a2e' }}>
              <span className="material-symbols-outlined icon-blue" style={{ fontSize: '1.6rem' }}>location_on</span>
              <span style={{ fontWeight: 600 }}>{evento.campus || 'Campus não informado'}</span>
            </div>
            {evento.local && (
              <div className="event-info-line" style={{ color: isDark ? '#fff' : '#1a1a2e' }}>
                <span className="material-symbols-outlined icon-blue" style={{ fontSize: '1.6rem' }}>meeting_room</span>
                <span style={{ fontWeight: 600 }}>{evento.local}</span>
              </div>
            )}

            <div className="event-actions">
              {!isPersonalEvent && (
                <SaveEventButton
                  key={`${user?.id || 'guest'}-${id}`}
                  eventId={id}
                  user={user}
                  onSavedChange={setSalvoNaAgenda}
                />
              )}
              {evento.linkOriginal && (
                <button
                  type="button"
                  className="ds-btn-primary"
                  onClick={handleConferir}
                  disabled={registeringClick}
                  style={{
                    background: 'rgba(0, 95, 210, 1)',
                    height: '56px',
                    fontSize: '1rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}
                >
                  <span className="material-symbols-outlined" aria-hidden="true">open_in_new</span>
                  CONFERIR EVENTO
                </button>
              )}
              {outboundError && (
                <p className="save-event-feedback" role="alert">{outboundError}</p>
              )}

              {!isPersonalEvent && (
                <div className="social-counter" style={{
                  background: isDark ? 'rgba(0, 139, 255, 0.05)' : 'rgba(0, 139, 255, 0.08)',
                  color: isDark ? 'rgba(255,255,255,0.65)' : 'rgba(26,26,46,0.65)',
                  padding: '12px'
                }}>
                  <span className="material-symbols-outlined icon-hot" aria-hidden="true">open_in_new</span>
                  <strong style={{ color: isDark ? '#fff' : '#1a1a2e', fontSize: '1rem' }}>{interessados}</strong>
                  <span>{interessados === 1 ? 'acesso ao link oficial' : 'acessos ao link oficial'}</span>
                </div>
              )}

              <button type="button" className="ds-btn-secondary" onClick={handleShare} style={{
                color: isDark ? 'rgba(255, 255, 255, 0.7)' : 'rgba(26, 26, 46, 0.7)',
                borderColor: isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.15)',
                height: '50px'
              }}>
                <span className="material-symbols-outlined" aria-hidden="true">{isCopied ? 'check' : 'share'}</span>
                {isCopied ? 'Link Copiado!' : 'Compartilhar evento'}
              </button>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
