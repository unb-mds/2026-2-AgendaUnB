import { useEffect, useRef, useState } from 'react';
import { Feedback, Icon, ManagementShell, Modal, Pagination, useDebounced } from '../components/ManagementUI';
import { formatDate, moderationApi, safeEventUrl } from '../lib/moderation';

const STATUS = { pendente: 'Pendentes', aprovado: 'Aprovadas', rejeitado: 'Recusadas' };

export default function SuggestionsPage() {
  const [status, setStatus] = useState('pendente');
  const [search, setSearch] = useState('');
  const query = useDebounced(search);
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState({ items: [], total: 0, pending: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [decision, setDecision] = useState(null);
  const [reason, setReason] = useState('');
  const [decisionError, setDecisionError] = useState('');
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);

  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    moderationApi.suggestions(status, query, page).then(data => {
      if (!active) return;
      if (page > 0 && !data.items.length) setPage(page - 1);
      else setResult(data);
    }).catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [status, query, page, revision]);

  const openDecision = (event, nextStatus) => {
    setDecision({ event, status: nextStatus }); setReason(''); setDecisionError(''); setSuccess('');
  };
  const submit = async e => {
    e.preventDefault();
    if (submitting.current) return;
    if (decision.status === 'rejeitado' && !reason.trim()) {
      setDecisionError('Escreva uma justificativa para orientar o estudante.'); return;
    }
    submitting.current = true; setBusy(true); setDecisionError('');
    try {
      await moderationApi.decide(decision.event.id, decision.status, reason.trim());
      setSuccess(decision.status === 'aprovado'
        ? 'Sugestão aprovada e publicada. O estudante foi notificado.'
        : 'Sugestão recusada. A justificativa foi enviada ao estudante.');
      setDecision(null); setRevision(v => v + 1);
    } catch (err) { setDecisionError(err.message); }
    finally { submitting.current = false; setBusy(false); }
  };

  return <ManagementShell title="Sugestões" description="Ajude boas ideias a chegar à comunidade. Analise os eventos enviados pelos estudantes.">
    <div className="management-toolbar">
      <div className="management-tabs" role="group" aria-label="Status das sugestões">
        {Object.entries(STATUS).map(([key, label]) => <button key={key} aria-pressed={status === key}
          className={status === key ? 'active' : ''} onClick={() => { setStatus(key); setPage(0); }}>
          {label}{key === 'pendente' && <span className="management-count">{result.pending}</span>}
        </button>)}
      </div>
      <button className="manage-button" onClick={() => setRevision(v => v + 1)} disabled={loading}><Icon>refresh</Icon>Atualizar</button>
    </div>
    <div className="management-search-row">
      <label className="management-search"><Icon>search</Icon><span className="sr-only">Buscar sugestões por título ou estudante</span>
        <input value={search} maxLength={120} onChange={e => { setSearch(e.target.value); setPage(0); }} placeholder="Buscar por título ou estudante" />
      </label>
      {search && <button className="manage-button" onClick={() => { setSearch(''); setPage(0); }}>Limpar busca</button>}
      <span className="management-muted">Mais antigas primeiro</span>
    </div>
    <Feedback error={error} success={success} onRetry={() => setRevision(v => v + 1)} />
    {loading ? <div className="management-state" role="status">Carregando sugestões…</div>
      : !error && !result.items.length ? <div className="management-state"><Icon>{query ? 'search_off' : 'task_alt'}</Icon>
        <h2>{query ? 'Nenhuma sugestão encontrada' : status === 'pendente' ? 'Tudo em dia por aqui' : 'Nenhuma sugestão nesta lista'}</h2>
        <p>{query ? 'Tente outro título ou nome de estudante.' : status === 'pendente' ? 'Novas sugestões dos estudantes aparecerão aqui para análise.' : 'As decisões de moderação ficarão disponíveis aqui.'}</p>
      </div> : !error && <section className="suggestion-list" aria-label={STATUS[status]}>
        {result.items.map(event => <article className="suggestion-row" key={event.id}>
          <div className="suggestion-body">
            <div className="suggestion-title"><h2>{event.titulo}</h2><span className="management-tag">{event.categoria || 'Sem categoria'}</span></div>
            <p className="management-muted">Enviada por <strong>{event.autor_nome}</strong> · {formatDate(event.criado_em)}</p>
            <dl className="suggestion-details">
              <div><dt><Icon>event</Icon>Quando</dt><dd>{formatDate(event.data_evento)}</dd></div>
              <div><dt><Icon>location_on</Icon>Onde</dt><dd>{[event.campus, event.localizacao].filter(Boolean).join(' · ') || 'Local não informado'}</dd></div>
            </dl>
            <p className="suggestion-description">{event.descricao || 'O estudante não incluiu uma descrição.'}</p>
            {safeEventUrl(event.link_externo) && <a className="management-link" href={safeEventUrl(event.link_externo)} target="_blank" rel="noopener noreferrer">Abrir link do evento<Icon>open_in_new</Icon><span className="sr-only"> (nova aba)</span></a>}
            {event.justificativa_recusa && <div className="suggestion-reason"><strong>Justificativa enviada</strong><p>{event.justificativa_recusa}</p></div>}
          </div>
          {status === 'pendente' && <footer className="suggestion-actions">
            <span className="management-muted">{new Date(event.data_evento) < new Date() ? 'A data deste evento já passou. Confira antes de aprovar.' : 'A aprovação publica este evento para todos.'}</span>
            <div className="management-actions"><button className="manage-button" onClick={() => openDecision(event, 'rejeitado')}><Icon>close</Icon>Recusar</button>
              <button className="manage-button primary" onClick={() => openDecision(event, 'aprovado')}><Icon>check</Icon>Aprovar</button></div>
          </footer>}
        </article>)}
      </section>}
    {!error && <Pagination page={page} total={result.total} onPage={setPage} busy={loading} />}
    {decision && <Modal title={decision.status === 'rejeitado' ? 'Recusar sugestão' : 'Aprovar sugestão'} busy={busy} onClose={() => setDecision(null)}>
      <form onSubmit={submit}>
        <p className="dialog-event-title">{decision.event.titulo}</p>
        {decision.status === 'rejeitado' ? <label className="management-field">Justificativa <span className="management-muted">(obrigatória)</span>
          <textarea autoFocus required maxLength={2000} rows={5} value={reason} onChange={e => setReason(e.target.value)} aria-describedby="reason-help" placeholder="Explique o que precisa ser ajustado para orientar o estudante." />
          <small id="reason-help">O estudante receberá este texto nas notificações. {reason.length}/2000</small>
        </label> : <p>O evento será publicado na agenda e o estudante receberá uma notificação de aprovação.</p>}
        <Feedback error={decisionError} />
        <footer className="dialog-actions"><button type="button" className="manage-button" disabled={busy} onClick={() => setDecision(null)}>Cancelar</button>
          <button className="manage-button primary" disabled={busy}>{busy ? 'Enviando…' : decision.status === 'rejeitado' ? 'Recusar e notificar' : 'Aprovar e publicar'}</button></footer>
      </form>
    </Modal>}
  </ManagementShell>;
}
