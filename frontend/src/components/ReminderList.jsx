import { useEffect, useRef, useState } from 'react';
import { remindersApi } from '../lib/remindersApi';
import { formatDate } from '../lib/moderation';
import { Feedback, Icon } from './ManagementUI';

const PAGE_SIZE = 20;

export default function ReminderList() {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const sequence = useRef(0);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const version = ++sequence.current;
      try {
        const reminders = await remindersApi.list(PAGE_SIZE + 1, page * PAGE_SIZE);
        if (active && version === sequence.current) {
          setItems(reminders);
          setError('');
        }
      } catch (err) {
        if (active && version === sequence.current) setError(err.message);
      } finally {
        if (active && version === sequence.current) setLoading(false);
      }
    };
    load();
    const refresh = () => { if (!document.hidden) load(); };
    const timer = setInterval(refresh, 30000);
    window.addEventListener('focus', refresh);
    return () => {
      active = false;
      clearInterval(timer);
      window.removeEventListener('focus', refresh);
    };
  }, [page, revision]);

  const showPage = nextPage => {
    setLoading(true);
    setItems([]);
    setPage(nextPage);
  };

  const markRead = async (id, button) => {
    setBusy(true);
    const row = button.closest('li');
    try {
      const { read_at } = await remindersApi.markRead(id);
      ++sequence.current;
      setItems(current => current.map(item => item.id === id ? { ...item, read_at } : item));
      setError('');
      if (document.activeElement === button || document.activeElement === document.body) {
        row.focus({ preventScroll: true });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return <>
    <Feedback error={error} onRetry={() => setRevision(value => value + 1)} />
    {loading && <p className="notification-empty" role="status">Carregando lembretes…</p>}
    {!loading && !items.length && !error && <p className="notification-empty">Nenhum lembrete nesta página.</p>}
    {!loading && !!items.length && <ul className="notification-list" aria-label="Lembretes da agenda">
      {items.slice(0, PAGE_SIZE).map(item => <li key={item.id} tabIndex={-1} className={item.read_at ? '' : 'unread'}>
        <Icon>event</Icon>
        <div>
          <div className="notification-title">
            <strong>{item.title || (item.event_kind === 'personal' ? 'Compromisso da agenda' : 'Evento público salvo')}</strong>
            <span className={item.read_at ? 'management-muted' : 'management-tag'}>
              {item.read_at ? 'Lido' : 'Não lido'}
            </span>
          </div>
          <time dateTime={item.starts_at}>Início em {formatDate(item.starts_at)}</time>
          {!item.read_at && <button type="button" className="management-text-button" disabled={busy}
            onClick={event => markRead(item.id, event.currentTarget)}>Marcar como lido</button>}
        </div>
      </li>)}
    </ul>}
    {(page > 0 || items.length > PAGE_SIZE) && <nav className="management-pagination notification-pagination" aria-label="Paginação dos lembretes">
      <button type="button" className="manage-button" disabled={loading || busy || page === 0}
        onClick={() => showPage(page - 1)}>Anterior</button>
      <span>Página {page + 1}</span>
      <button type="button" className="manage-button" disabled={loading || busy || items.length <= PAGE_SIZE}
        onClick={() => showPage(page + 1)}>Próxima</button>
    </nav>}
  </>;
}
