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
const callbackMessages = new Map([
  ['denied', 'O acesso ao Google Agenda não foi concedido.'],
  ['email_mismatch', 'Use uma conta Google com o mesmo e-mail verificado da Agenda UnB.'],
  ['invalid_state', 'A solicitação expirou ou já foi usada. Inicie a conexão novamente.'],
  ['different_google_account', 'Desconecte a conta Google anterior antes de tentar outra.'],
  ['offline_access_unavailable', 'O Google não concedeu acesso para renovar a conexão. Tente conectar novamente.'],
  ['failed', 'Não foi possível conectar ao Google Agenda. Tente novamente.'],
]);

export default function GoogleCalendarConnection({ events, callbackResult }) {
  const [connection, setConnection] = useState(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [recoveryOpen, setRecoveryOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    request(`${ROOT}/connection`, { auth: true, signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setConnection(result); })
      .catch(() => {
        if (!controller.signal.aborted) setError('Não foi possível consultar a conexão com o Google Agenda.');
      });
    return () => controller.abort();
  }, [callbackResult]);

  async function changeConnection(method) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      if (method === 'POST') {
        const result = await request(`${ROOT}/authorization`, { auth: true, method });
        const url = new URL(result.authorization_url);
        if (url.origin !== 'https://accounts.google.com') throw new Error();
        window.location.assign(url);
        return;
      }
      const result = await request(`${ROOT}/connection`, { auth: true, method });
      setConnection({ connected: false });
      setNotice(result.revocation === 'not_confirmed_remove_access_in_google'
        ? 'Desconectado. Remova o acesso também nas conexões da sua Conta Google.'
        : 'Google Agenda desconectado.');
    } catch (err) {
      setError(err.status ? err.message : 'Não foi possível atualizar a conexão com o Google Agenda.');
    } finally {
      setBusy(false);
    }
  }

  async function recover(event, createNew = false) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const calendarId = createNew ? null : new FormData(event.currentTarget).get('calendar_id').trim();
    try {
      await request(`${ROOT}/destination`, {
        auth: true, method: 'PUT', body: JSON.stringify({ calendar_id: calendarId }),
      });
      setConnection(current => ({ ...current, recovery_required: false }));
      setRecoveryOpen(false);
      setNotice(createNew ? 'A próxima exportação criará a agenda Agenda UnB.' : 'Agenda UnB recuperada.');
    } catch (err) {
      setError(err.status ? err.message : 'Não foi possível recuperar a agenda.');
    } finally {
      setBusy(false);
    }
  }

  async function refreshConnection() {
    try {
      setConnection(await request(`${ROOT}/connection`, { auth: true }));
    } catch {
      // The export dialog already displays the operation error.
    }
  }

  return (
    <>
      {connection?.connected ? (
        <>
          <button type="button" className="manage-button google-calendar-secondary" disabled={busy} onClick={() => changeConnection('DELETE')}>
            Desconectar Google Agenda
          </button>
          {connection.recovery_required ? (
            <button type="button" className="manage-button google-calendar-action" aria-haspopup="dialog" onClick={() => setRecoveryOpen(true)}>
              <img src="/google-calendar-2026.svg" alt="" width="24" height="24" />
              <span>Recuperar agenda do Google</span>
            </button>
          ) : (
            <button type="button" className="manage-button google-calendar-action"
              aria-haspopup="dialog" disabled={!events.length} onClick={() => setOpen(true)}>
              <img src="/google-calendar-2026.svg" alt="" width="24" height="24" />
              <span>{EXPORT_LABEL}</span>
            </button>
          )}
        </>
      ) : (
        <button type="button" className="manage-button google-calendar-action" disabled={busy} onClick={() => changeConnection('POST')}>
          <img src="/google-calendar-2026.svg" alt="" width="24" height="24" />
          <span>Conectar ao Google Agenda</span>
        </button>
      )}
      {!recoveryOpen && <Feedback error={error || (!notice && callbackMessages.get(callbackResult))} />}
      <Feedback success={notice || (callbackResult === 'connected' && connection?.connected ? 'Google Agenda conectado.' : '')} />
      {open && <ExportDialog events={events} onClose={() => setOpen(false)} onFailure={refreshConnection} />}
      {recoveryOpen && (
        <Modal title="Recuperar agenda do Google" onClose={() => setRecoveryOpen(false)} busy={busy}>
          <form onSubmit={recover}>
            <p>Abra as configurações da agenda Agenda UnB no Google e copie o ID em “Integrar agenda”.</p>
            <label htmlFor="google-calendar-id">ID da agenda</label>
            <input className="modal-input" id="google-calendar-id" name="calendar_id" required maxLength={512} />
            <Feedback error={error} />
            <div className="dialog-actions">
              <button type="button" className="manage-button" disabled={busy} onClick={event => recover(event, true)}>
                Confirmei que a agenda não existe
              </button>
              <button type="submit" className="manage-button primary" disabled={busy}>Recuperar agenda</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function ExportDialog({ events, onClose, onFailure }) {
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
      if (err.status === 409 || err.status === 503) await onFailure();
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
