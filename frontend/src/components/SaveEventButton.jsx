import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { eventsApi } from '../lib/api';

export default function SaveEventButton({ eventId, user }) {
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(Boolean(user));
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!user) return;
    let active = true;
    setLoading(true);
    setLoadError('');
    eventsApi.savedStatus(eventId)
      .then(result => { if (active) setSaved(result.saved); })
      .catch(() => { if (active) setLoadError('Não foi possível consultar sua agenda.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [eventId, user?.id, attempt]);

  const toggleSaved = async () => {
    if (saving) return;
    setSaving(true);
    setError('');
    setMessage('');
    try {
      if (saved) await eventsApi.removeSaved(eventId);
      else await eventsApi.savePublic(eventId);
      setSaved(!saved);
      setMessage(saved ? 'Evento removido da sua agenda.' : 'Evento adicionado à sua agenda.');
    } catch (err) {
      setError(err.message || 'Não foi possível atualizar sua agenda. Tente novamente.');
    } finally {
      setSaving(false);
    }
  };

  if (!user) {
    return <p className="save-event-feedback"><Link to="/">Entre na sua conta</Link> para adicionar este evento aos seus eventos.</p>;
  }

  return (
    <div className="save-event-controls">
      {loadError ? (
        <>
          <p className="save-event-feedback" role="alert">{loadError}</p>
          <button type="button" className="ds-btn-secondary" onClick={() => setAttempt(value => value + 1)}>Tentar novamente</button>
        </>
      ) : (
        <button type="button" className={saved ? 'ds-btn-secondary' : 'ds-btn-primary'} disabled={loading || saving} onClick={toggleSaved}>
          <span className="material-symbols-outlined" aria-hidden="true">{saved ? 'bookmark_remove' : 'bookmark_add'}</span>
          {loading ? 'Consultando sua agenda…' : saving ? 'Atualizando agenda…' : saved ? 'Remover dos meus eventos' : 'Adicionar aos meus eventos'}
        </button>
      )}
      {error && <p className="save-event-feedback" role="alert">{error}</p>}
      {message && <p className="save-event-feedback" role="status">{message} <Link to="/segunda-pagina?aba=meus">Ver meus eventos</Link></p>}
    </div>
  );
}
