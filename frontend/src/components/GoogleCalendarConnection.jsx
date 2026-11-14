import { useEffect, useRef, useState } from 'react';
import { request } from '../lib/api';
import { Feedback, Modal } from './ManagementUI';

const ROOT = '/me/google-calendar';
const MAX_EVENTS = 20;
const EXPORT_LABEL = 'Exportar para o Google Agenda';
const saoPauloTime = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo',
});
const keyOf = event => `${event.criadoPorMim ? 'personal' : 'saved'}:${event.id}`;

export default function GoogleCalendarConnection({ events }) {
  const [available, setAvailable] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    request(`${ROOT}/connection`, { auth: true, signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setAvailable(result?.connected === true); })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  if (!available) return null;

  return (
    <>
      <button type="button" className="manage-button google-calendar-action"
        aria-haspopup="dialog" disabled={!events.length} onClick={() => setOpen(true)}>
        <img src="/google-calendar-2026.svg" alt="" width="24" height="24" />
        <span>{EXPORT_LABEL}</span>
      </button>
      {open && <ExportDialog events={events} onClose={() => setOpen(false)} />}
    </>
  );
}

function ExportDialog({ events, onClose }) {
  const [selection, setSelection] = useState([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const busy = useRef(false);
  const chosen = events.filter(event => selection.includes(keyOf(event)));
  const selectedKeys = new Set(chosen.map(keyOf));

  function toggle(key) {
    setSelection(current => current.includes(key)
      ? current.filter(value => value !== key) : [...current, key]);
  }

  async function submit(event) {
    event.preventDefault();
    if (busy.current || !chosen.length || chosen.length > MAX_EVENTS) return;
    busy.current = true;
    setPending(true);
    setSuccess('');
    setError('');
    try {
      const results = await request(`${ROOT}/exports`, {
        method: 'POST',
        auth: true,
        body: JSON.stringify({
          events: chosen.map(item => ({ id: item.id, kind: item.criadoPorMim ? 'personal' : 'saved' })),
        }),
      });
      if (!Array.isArray(results) || results.length !== chosen.length) throw new Error();
      const expected = new Set(chosen.map(keyOf));
      if (results.some(item => !expected.delete(`${item?.kind}:${item?.id}`)
          || !['failed', 'exported', 'already_exported'].includes(item.status))) throw new Error();
      const failed = results.filter(item => item.status === 'failed');
      const exported = results.length - failed.length;
      setSelection(failed.map(item => `${item.kind}:${item.id}`));
      if (exported) setSuccess(exported === 1
        ? '1 evento disponível no Google Agenda.' : `${exported} eventos disponíveis no Google Agenda.`);
      if (failed.length) setError('Alguns eventos não foram exportados. Tente novamente com os itens selecionados.');
    } catch (err) {
      setError(err.status ? err.message : 'Não foi possível exportar. Verifique sua conexão e tente novamente.');
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  return (
    <Modal title={EXPORT_LABEL} onClose={onClose} busy={pending}>
      <form onSubmit={submit}>
        <p className="management-muted">
          Escolha até {MAX_EVENTS} eventos para enviar à agenda Agenda UnB no Google.
          Cada evento será exportado com seu título, horário de Brasília e duração de uma hora.
        </p>
        <fieldset className="google-calendar-event-list" disabled={pending}>
          <legend className="sr-only">Eventos para exportar</legend>
          {events.map(event => {
            const key = keyOf(event);
            const checked = selectedKeys.has(key);
            return (
              <label key={key}>
                <input type="checkbox" checked={checked}
                  disabled={!checked && chosen.length >= MAX_EVENTS} onChange={() => toggle(key)} />
                <span>
                  {event.titulo}
                  <small>{saoPauloTime.format(new Date(event.startsAt))}</small>
                </span>
              </label>
            );
          })}
        </fieldset>
        <Feedback error={error} />
        <Feedback success={success} />
        <div className="dialog-actions">
          <button type="submit" className="manage-button primary" disabled={pending || !chosen.length}>
            {pending ? 'Exportando…' : 'Exportar eventos selecionados'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
