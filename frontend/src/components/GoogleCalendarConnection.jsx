import { useEffect, useMemo, useRef, useState } from 'react';
import { request } from '../lib/api';
import { downloadIcsCalendar } from '../lib/ics';
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

const previewActionLabels = {
  create: 'Será criado',
  update: 'Será atualizado',
  unchanged: 'Já exportado',
};

const resultStatusLabels = {
  pending: 'Pendente…',
  exported: 'Criado no Google Agenda',
  updated: 'Atualizado no Google Agenda',
  already_exported: 'Já exportado (inalterado)',
  failed: 'Falha ao exportar',
};

function formatCivilDateBr(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const parts = dateStr.split('-');
  return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : dateStr;
}

function formatEventTimingLabel(event) {
  if (event.diaInteiro) {
    const start = formatCivilDateBr(event.startDate || event.data);
    const end = event.dataFim && event.dataFim > (event.startDate || event.data)
      ? formatCivilDateBr(event.dataFim)
      : '';
    return end ? `${start} a ${end} · Dia inteiro` : `${start} · Dia inteiro`;
  }
  const startLabel = saoPauloTime.format(new Date(event.startsAt));
  if (event.endsAt) {
    const endDate = new Date(event.endsAt);
    if (!Number.isNaN(endDate.getTime()) && endDate.getTime() > new Date(event.startsAt).getTime()) {
      return `${startLabel} – ${saoPauloTime.format(endDate)}`;
    }
  }
  return startLabel;
}

function classifyEventBadge(event) {
  if (event.salvoNaAgenda || !event.criadoPorMim) return 'Público salvo';
  const desc = event.descricao || '';
  const title = event.titulo || '';
  if (desc.startsWith('Tipo de avaliação: Prova') || /\bprova\b/i.test(title)) return 'Prova';
  if (desc.startsWith('Tipo de avaliação: Trabalho') || /\b(trabalho|entrega|semin[aá]rio)\b/i.test(title)) return 'Trabalho';
  return 'Pessoal';
}

function createIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `export-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export default function GoogleCalendarConnection({ events, callbackResult }) {
  const [connection, setConnection] = useState(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [disconnectedGuide, setDisconnectedGuide] = useState(false);
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
    setDisconnectedGuide(false);
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
      setDisconnectedGuide(true);
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
    event?.preventDefault?.();
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
      const latest = await request(`${ROOT}/connection`, { auth: true });
      setConnection(latest);
      return latest;
    } catch {
      return null;
    }
  }

  function handleQuickIcsDownload() {
    if (!events.length) return;
    setError('');
    try {
      downloadIcsCalendar(events, { includeDescription: true });
      setNotice('Arquivo ICS gerado para Apple Calendar e Outlook.');
    } catch (err) {
      setError(err.message || 'Não foi possível gerar o arquivo ICS.');
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
        <>
          {events.length > 0 && (
            <button type="button" className="manage-button google-calendar-secondary" disabled={busy} onClick={handleQuickIcsDownload}>
              Exportar arquivo ICS
            </button>
          )}
          <button type="button" className="manage-button google-calendar-action" disabled={busy} onClick={() => changeConnection('POST')}>
            <img src="/google-calendar-2026.svg" alt="" width="24" height="24" />
            <span>Conectar ao Google Agenda</span>
          </button>
        </>
      )}
      {!recoveryOpen && <Feedback error={error || (!notice && callbackMessages.get(callbackResult))} />}
      <Feedback success={notice || (callbackResult === 'connected' && connection?.connected ? 'Google Agenda conectado.' : '')} />
      {disconnectedGuide && (
        <div className="google-calendar-disconnect-guide">
          <p className="management-muted">
            Eventos já exportados permanecem na agenda secundária “Agenda UnB” do seu Google Agenda.
          </p>
          <GoogleCalendarDeletionInstructions />
        </div>
      )}
      {open && (
        <ExportDialog
          events={events}
          onClose={() => setOpen(false)}
          onFailure={refreshConnection}
          onOpenRecovery={() => {
            setOpen(false);
            setRecoveryOpen(true);
          }}
          onReconnect={() => {
            setOpen(false);
            changeConnection('POST');
          }}
        />
      )}
      {recoveryOpen && (
        <Modal title="Recuperar agenda do Google" onClose={() => setRecoveryOpen(false)} busy={busy}>
          <form onSubmit={recover}>
            <p>
              A agenda secundária <strong>Agenda UnB</strong> não foi encontrada ou teve a resposta de criação interrompida.
              Exclusões locais não removem automaticamente cópias no Google.
              Para reutilizar uma agenda existente, abra as configurações da agenda no Google e copie o ID em “Integrar agenda”,
              ou confirme abaixo para recriar uma nova agenda <strong>Agenda UnB</strong>.
            </p>
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

function ExportDialog({ events, onClose, onFailure, onOpenRecovery, onReconnect }) {
  const [selection, setSelection] = useState([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [includeDescription, setIncludeDescription] = useState(false);
  const [preview, setPreview] = useState(null);
  const [confirmingOverwrite, setConfirmingOverwrite] = useState(false);
  const [itemStatuses, setItemStatuses] = useState({});
  const [recoveryNeeded, setRecoveryNeeded] = useState(false);
  const [reconnectNeeded, setReconnectNeeded] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const busy = useRef(false);
  const retryKeyRef = useRef(null);
  const approvedOverwriteRef = useRef(false);

  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      const evStart = event.startDate || event.data || '';
      const evEnd = event.dataFim || evStart;
      if (startDate && evEnd && evEnd < startDate) return false;
      if (endDate && evStart && evStart > endDate) return false;
      return true;
    });
  }, [events, startDate, endDate]);

  const chosen = useMemo(
    () => filteredEvents.filter(event => selection.includes(keyOf(event))),
    [filteredEvents, selection],
  );
  const selectedKeys = useMemo(() => new Set(chosen.map(keyOf)), [chosen]);

  useEffect(() => {
    setConfirmingOverwrite(false);
    if (!chosen.length || chosen.length > MAX_EVENTS) {
      setPreview(null);
      return undefined;
    }
    const controller = new AbortController();
    const payload = {
      events: chosen.map(item => ({ id: item.id, kind: item.criadoPorMim ? 'personal' : 'saved' })),
      ...(includeDescription ? { include_description: true } : {}),
      ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}),
    };
    request(`${ROOT}/exports/preview`, {
      method: 'POST',
      auth: true,
      signal: controller.signal,
      body: JSON.stringify(payload),
    })
      .then(result => {
        if (!controller.signal.aborted && result && Array.isArray(result.items)) {
          setPreview(result);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setPreview(null);
      });
    return () => controller.abort();
  }, [chosen, includeDescription, startDate, endDate]);

  const previewByKey = useMemo(() => {
    const map = new Map();
    if (preview?.items) {
      for (const item of preview.items) {
        map.set(`${item.kind}:${item.id}`, item.action);
      }
    }
    return map;
  }, [preview]);

  const previewSummary = useMemo(() => {
    if (!preview?.items?.length) return null;
    let createCount = 0;
    let updateCount = 0;
    let unchangedCount = 0;
    for (const item of preview.items) {
      if (item.action === 'create') createCount += 1;
      else if (item.action === 'update') updateCount += 1;
      else if (item.action === 'unchanged') unchangedCount += 1;
    }
    return { createCount, updateCount, unchangedCount };
  }, [preview]);

  function resetBatchState() {
    setItemStatuses({});
    setConfirmingOverwrite(false);
    retryKeyRef.current = null;
    approvedOverwriteRef.current = false;
  }

  function toggle(key) {
    resetBatchState();
    setSelection(current => current.includes(key)
      ? current.filter(value => value !== key) : [...current, key]);
  }

  function selectAllFiltered() {
    resetBatchState();
    setSelection(filteredEvents.slice(0, MAX_EVENTS).map(keyOf));
  }

  function clearSelection() {
    resetBatchState();
    setSelection([]);
  }

  function handleDownloadIcs() {
    const targetEvents = chosen.length ? chosen : filteredEvents;
    if (!targetEvents.length) return;
    setError('');
    try {
      downloadIcsCalendar(targetEvents, { includeDescription: true });
      setSuccess(targetEvents.length === 1
        ? '1 evento exportado em arquivo ICS para Apple Calendar e Outlook.'
        : `${targetEvents.length} eventos exportados em arquivo ICS para Apple Calendar e Outlook.`);
    } catch (err) {
      setError(err.message || 'Não foi possível gerar o arquivo ICS.');
    }
  }

  async function executeExport(allowOverwrite = false, isRetry = false) {
    if (busy.current || !chosen.length || chosen.length > MAX_EVENTS) return;
    busy.current = true;
    setPending(true);
    setSuccess('');
    setError('');
    setRecoveryNeeded(false);
    setReconnectNeeded(false);

    const pendingMap = {};
    for (const item of chosen) {
      pendingMap[keyOf(item)] = 'pending';
    }
    setItemStatuses(current => ({ ...current, ...pendingMap }));

    const idempotencyKey = isRetry && retryKeyRef.current
      ? retryKeyRef.current
      : createIdempotencyKey();
    retryKeyRef.current = idempotencyKey;
    approvedOverwriteRef.current = Boolean(allowOverwrite);

    const payload = {
      events: chosen.map(item => ({ id: item.id, kind: item.criadoPorMim ? 'personal' : 'saved' })),
      ...(allowOverwrite ? { allow_managed_field_updates: true } : {}),
      ...(includeDescription ? { include_description: true } : {}),
      ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}),
    };

    try {
      const results = await request(`${ROOT}/exports`, {
        method: 'POST',
        auth: true,
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(payload),
      });
      if (!Array.isArray(results) || results.length !== chosen.length) throw new Error();
      const expected = new Set(chosen.map(keyOf));
      if (results.some(item => !expected.delete(`${item?.kind}:${item?.id}`)
          || !['failed', 'exported', 'updated', 'already_exported'].includes(item.status))) throw new Error();

      const nextStatuses = {};
      for (const item of results) {
        nextStatuses[`${item.kind}:${item.id}`] = item.status;
      }
      setItemStatuses(current => ({ ...current, ...nextStatuses }));
      setConfirmingOverwrite(false);

      const failed = results.filter(item => item.status === 'failed');
      const exported = results.length - failed.length;
      const updatedCount = results.filter(item => item.status === 'updated').length;
      setSelection(failed.map(item => `${item.kind}:${item.id}`));

      if (exported) {
        const baseMsg = exported === 1
          ? '1 evento disponível no Google Agenda.'
          : `${exported} eventos disponíveis no Google Agenda.`;
        setSuccess(updatedCount > 0
          ? `${baseMsg} (${updatedCount === 1 ? '1 atualizado' : `${updatedCount} atualizados`})`
          : baseMsg);
      }
      if (failed.length) {
        retryKeyRef.current = idempotencyKey;
        setError('Alguns eventos não foram exportados. Tente novamente com os itens selecionados.');
      } else {
        retryKeyRef.current = null;
        approvedOverwriteRef.current = false;
      }
    } catch (err) {
      setError(err.status ? err.message : 'Não foi possível exportar. Verifique sua conexão e tente novamente.');
      let requiresAction = false;
      if (err.status === 409 || err.status === 503) {
        const latest = await onFailure();
        if (latest?.recovery_required) {
          setRecoveryNeeded(true);
          requiresAction = true;
        } else if (latest && !latest.connected) {
          setReconnectNeeded(true);
          requiresAction = true;
        }
      }
      if (requiresAction) {
        retryKeyRef.current = null;
        setItemStatuses(current => {
          const next = { ...current };
          for (const item of chosen) {
            if (next[keyOf(item)] === 'pending') delete next[keyOf(item)];
          }
          return next;
        });
      } else {
        const failedMap = {};
        for (const item of chosen) {
          failedMap[keyOf(item)] = 'failed';
        }
        setItemStatuses(current => ({ ...current, ...failedMap }));
      }
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (busy.current || !chosen.length || chosen.length > MAX_EVENTS) return;
    if (preview?.requires_overwrite_confirmation && !confirmingOverwrite) {
      setConfirmingOverwrite(true);
      return;
    }
    await executeExport(Boolean(preview?.requires_overwrite_confirmation && confirmingOverwrite), false);
  }

  const hasFailedSelection = chosen.length > 0 && chosen.every(item => itemStatuses[keyOf(item)] === 'failed');

  return (
    <Modal title={EXPORT_LABEL} onClose={onClose} busy={pending}>
      <form onSubmit={submit}>
        <p className="management-muted">
          Escolha até {MAX_EVENTS} eventos da sua agenda para enviar à agenda secundária <strong>Agenda UnB</strong> no Google,
          com datas e horários em <code>America/Sao_Paulo</code>. A atualização no Google ocorre quando você solicita nova exportação
          (sem sincronização automática bidirecional). Exclusões locais não removem cópias já exportadas.
        </p>
        <p className="management-muted google-calendar-copy-notice">
          As cópias enviadas permanecem na agenda “Agenda UnB” do Google Agenda mesmo se você desconectar ou excluir sua conta.
        </p>
        <GoogleCalendarDeletionInstructions />

        <div className="google-calendar-period-filter" role="group" aria-label="Filtrar período para exportação">
          <label className="google-calendar-period-field">
            <span>De</span>
            <input
              type="date"
              className="modal-input"
              value={startDate}
              disabled={pending}
              onChange={e => { resetBatchState(); setStartDate(e.target.value); }}
            />
          </label>
          <label className="google-calendar-period-field">
            <span>Até</span>
            <input
              type="date"
              className="modal-input"
              value={endDate}
              min={startDate || undefined}
              disabled={pending}
              onChange={e => { resetBatchState(); setEndDate(e.target.value); }}
            />
          </label>
          <div className="google-calendar-period-actions">
            <button
              type="button"
              className="management-text-button"
              disabled={pending || !filteredEvents.length}
              onClick={selectAllFiltered}
            >
              Selecionar período
            </button>
            {chosen.length > 0 && (
              <button
                type="button"
                className="management-text-button"
                disabled={pending}
                onClick={clearSelection}
              >
                Limpar seleção
              </button>
            )}
          </div>
        </div>

        <label className="google-calendar-option-toggle">
          <input
            type="checkbox"
            checked={includeDescription}
            disabled={pending}
            onChange={e => { resetBatchState(); setIncludeDescription(e.target.checked); }}
          />
          <span>Incluir descrição selecionada nos eventos enviados ao Google Agenda</span>
        </label>

        {previewSummary && chosen.length > 0 && (
          <p className="google-calendar-preview-summary" aria-live="polite">
            Prévia: <strong>{previewSummary.createCount}</strong> {previewSummary.createCount === 1 ? 'será criado' : 'serão criados'}
            {' · '}
            <strong>{previewSummary.updateCount}</strong> {previewSummary.updateCount === 1 ? 'será atualizado' : 'serão atualizados'}
            {previewSummary.unchangedCount > 0 && (
              <> · <strong>{previewSummary.unchangedCount}</strong> {previewSummary.unchangedCount === 1 ? 'inalterado' : 'inalterados'}</>
            )}
          </p>
        )}

        <fieldset className="google-calendar-event-list" disabled={pending}>
          <legend className="sr-only">Eventos para exportar</legend>
          {filteredEvents.length === 0 ? (
            <p className="management-muted" style={{ padding: '0.75rem' }}>
              Nenhum evento encontrado no período selecionado.
            </p>
          ) : (
            filteredEvents.map(event => {
              const key = keyOf(event);
              const checked = selectedKeys.has(key);
              const status = itemStatuses[key];
              const previewAction = checked ? previewByKey.get(key) : null;
              const locationText = event.local || event.campus || '';
              return (
                <label key={key}>
                  <input type="checkbox" checked={checked}
                    disabled={!checked && chosen.length >= MAX_EVENTS} onChange={() => toggle(key)} />
                  <span className="google-calendar-event-info">
                    <span className="google-calendar-event-header">
                      <strong>{event.titulo}</strong>
                      <span className="management-tag">{classifyEventBadge(event)}</span>
                      {status && (
                        <span className={`management-tag google-calendar-status google-calendar-status--${status}`}>
                          {resultStatusLabels[status]}
                        </span>
                      )}
                      {!status && previewAction && (
                        <span className={`management-tag google-calendar-preview google-calendar-preview--${previewAction}`}>
                          {previewActionLabels[previewAction]}
                        </span>
                      )}
                    </span>
                    <small>
                      {formatEventTimingLabel(event)}
                      {locationText ? ` · ${locationText}` : ''}
                    </small>
                  </span>
                </label>
              );
            })
          )}
        </fieldset>

        {confirmingOverwrite && (
          <div className="google-calendar-overwrite-confirm" role="region" aria-label="Confirmação de atualização">
            <p>
              <strong>Confirmar atualização de eventos já exportados?</strong> Os campos geridos pelo Agenda UnB
              (título, datas, local e descrição selecionada) serão atualizados na agenda <strong>Agenda UnB</strong>.
              Exclusões feitas localmente não apagam cópias no Google Agenda.
            </p>
            <div className="dialog-actions">
              <button
                type="button"
                className="manage-button"
                disabled={pending}
                onClick={() => setConfirmingOverwrite(false)}
              >
                Voltar
              </button>
              <button
                type="button"
                className="manage-button primary"
                disabled={pending}
                onClick={() => executeExport(true, false)}
              >
                Confirmar atualização e exportar
              </button>
            </div>
          </div>
        )}

        <Feedback error={error} />
        {hasFailedSelection && !pending && (
          <div className="dialog-actions" style={{ marginTop: '0.5rem' }}>
            <button
              type="button"
              className="manage-button"
              onClick={() => executeExport(approvedOverwriteRef.current, true)}
            >
              Tentar novamente
            </button>
          </div>
        )}
        {recoveryNeeded && onOpenRecovery && (
          <div className="dialog-actions" style={{ marginTop: '0.5rem' }}>
            <button type="button" className="manage-button" onClick={onOpenRecovery}>
              Recuperar ou recriar agenda Agenda UnB
            </button>
          </div>
        )}
        {reconnectNeeded && onReconnect && (
          <div className="dialog-actions" style={{ marginTop: '0.5rem' }}>
            <button type="button" className="manage-button" onClick={onReconnect}>
              Reconectar ao Google Agenda
            </button>
          </div>
        )}
        <Feedback success={success} />

        <div className="dialog-actions">
          <button
            type="button"
            className="manage-button"
            disabled={pending || (!chosen.length && !filteredEvents.length)}
            onClick={handleDownloadIcs}
          >
            Baixar arquivo ICS (.ics)
          </button>
          <button type="submit" className="manage-button primary" disabled={pending || !chosen.length}>
            {pending ? 'Exportando…' : 'Exportar eventos selecionados'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function GoogleCalendarDeletionInstructions() {
  return (
    <details className="google-calendar-help">
      <summary>Como excluir eventos exportados no Google Agenda</summary>
      <ol>
        <li>Acesse calendar.google.com com a sua Conta Google.</li>
        <li>Em Minhas agendas, abra o menu da agenda “Agenda UnB” → Configurações e compartilhamento → Excluir agenda para remover todas as cópias.</li>
        <li>Se preferir manter a agenda, clique em um evento específico e escolha Excluir.</li>
      </ol>
    </details>
  );
}
