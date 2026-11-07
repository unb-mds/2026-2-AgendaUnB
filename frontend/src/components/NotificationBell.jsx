import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Feedback, Icon, Pagination } from './ManagementUI';
import { formatDate, moderationApi } from '../lib/moderation';

const TYPES = {
  submissao: { title: 'Sugestão enviada', icon: 'schedule', description: 'Seu evento está em análise por professores e administradores.' },
  aprovacao: { title: 'Sugestão aprovada', icon: 'check_circle', description: 'Seu evento foi publicado na agenda da comunidade.' },
  recusa: { title: 'Sugestão recusada', icon: 'chat', description: 'Confira o feedback para entender a decisão.' },
};
export default function NotificationBell({ userId }) {
  const panelId = useId();
  const containerRef = useRef(null);
  const buttonRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [result, setResult] = useState({ items: [], total: 0, unread: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const sequence = useRef(0);
  useEffect(() => {
    if (!open) return;
    const dismiss = event => {
      if (event.type === 'keydown' && event.key === 'Escape') {
        event.preventDefault();
        setOpen(false);
        buttonRef.current?.focus();
      } else if (event.type === 'pointerdown' && !containerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('keydown', dismiss);
    document.addEventListener('pointerdown', dismiss);
    return () => {
      document.removeEventListener('keydown', dismiss);
      document.removeEventListener('pointerdown', dismiss);
    };
  }, [open]);
  useEffect(() => {
    let active = true;
    const load = async (quiet = false) => {
      const version = ++sequence.current;
      if (!quiet) setLoading(true);
      try {
        const data = await moderationApi.notifications(userId, page);
        if (active && version === sequence.current) { setResult(data); setError(''); }
      } catch (err) { if (active && version === sequence.current) setError(err.message); }
      finally { if (active && version === sequence.current) setLoading(false); }
    };
    load();
    const refresh = () => { if (!document.hidden) load(true); };
    const timer = setInterval(refresh, 30000);
    window.addEventListener('suggestion-submitted', refresh); window.addEventListener('focus', refresh);
    return () => { active = false; clearInterval(timer); window.removeEventListener('suggestion-submitted', refresh); window.removeEventListener('focus', refresh); };
  }, [userId, page, open, revision]);
  const markRead = async ids => {
    if (busy) return;
    setBusy(true);
    try { await moderationApi.markRead(userId, ids); setRevision(v => v + 1); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return <div className="notification-anchor" ref={containerRef}>
    <button ref={buttonRef} className="manage-icon-button notification-bell" aria-label={`Notificações${result.unread ? `: ${result.unread} não lidas` : ''}`}
      aria-haspopup="dialog" aria-controls={panelId} aria-expanded={open} onClick={() => setOpen(value => !value)} title="Notificações">
      <Icon>notifications</Icon>{result.unread > 0 && <span className="notification-count" aria-hidden="true">{result.unread > 99 ? '99+' : result.unread}</span>}
    </button>
    {open && <section id={panelId} className="notification-popover" role="dialog" aria-label="Notificações">
      <header className="notification-popover-header"><h2>Notificações</h2></header>
      <div className="notification-popover-body">
      <Feedback error={error} onRetry={() => setRevision(v => v + 1)} />
      {loading ? <div className="notification-empty" role="status">Carregando notificações…</div> : <>
        {!!result.items.some(item => !item.lida_em) && <button className="manage-button notification-mark" disabled={busy}
          onClick={() => markRead(result.items.filter(item => !item.lida_em).map(item => item.id))}>Marcar esta página como lida</button>}
        {!result.items.length && !error && <p className="notification-empty">Nenhuma notificação por enquanto.</p>}
        <ul className="notification-list">{result.items.map(item => <li key={item.id} className={item.lida_em ? '' : 'unread'}>
          <Icon>{TYPES[item.tipo].icon}</Icon><div>
            <div className="notification-title"><strong>{TYPES[item.tipo].title}</strong>{!item.lida_em && <span className="management-tag">Nova</span>}</div>
            <p className="notification-event">{item.titulo_evento}</p><p className="management-muted">{TYPES[item.tipo].description}</p>
            {item.justificativa && <blockquote>{item.justificativa}</blockquote>}
            <time dateTime={item.criado_em}>{formatDate(item.criado_em)}</time>
            <div className="notification-actions">{item.tipo === 'aprovacao' && item.evento_id && <Link className="management-link" to={`/evento/${item.evento_id}`} onClick={() => setOpen(false)}>Ver evento<Icon>arrow_forward</Icon></Link>}
              {!item.lida_em && <button className="management-text-button" disabled={busy} onClick={() => markRead([item.id])}>Marcar como lida</button>}</div>
          </div>
        </li>)}</ul>
        <Pagination page={page} total={result.total} onPage={setPage} busy={loading} />
      </>}
      </div>
    </section>}
  </div>;
}
