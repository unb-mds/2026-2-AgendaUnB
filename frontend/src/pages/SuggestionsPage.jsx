import { useEffect, useRef, useState } from 'react';
import { Feedback, Icon, ManagementShell, Modal, Pagination, useDebounced } from '../components/ManagementUI';
import { formatDate, moderationApi, safeEventUrl } from '../lib/moderation';

const STATUS = { pendente: 'Pendentes', aprovado: 'Aprovadas', rejeitado: 'Recusadas' };
const SOURCES = {
  suggestions: 'Sugestões de estudantes',
  collection: 'Revisão da coleta (UnB Notícias)',
};
const REVIEW_REASONS = {
  incompleto: 'Data ausente / incompleto',
  ambiguo: 'Data ou horário ambíguo',
  possivel_duplicata: 'Possível duplicata',
  informe: 'Informe institucional',
};

function formatSuggestionWhen(event) {
  if (!event.data_evento && !event.data_inicio_civil) {
    return 'Data não informada na fonte';
  }
  if (event.dia_inteiro && event.data_inicio_civil) {
    return `${event.data_inicio_civil.split('-').reverse().join('/')} · Dia inteiro`;
  }
  return formatDate(event.data_evento);
}

export default function SuggestionsPage() {
  const [source, setSource] = useState('suggestions');
  const [status, setStatus] = useState('pendente');
  const [search, setSearch] = useState('');
  const query = useDebounced(search);
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState({ items: [], total: 0, pending: 0 });
  const [collectionPending, setCollectionPending] = useState(0);
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
    setLoading(true);
    setError('');

    const request = source === 'collection'
      ? moderationApi.collectionReviews(status, page)
      : moderationApi.suggestions(status, query, page);

    request
      .then(data => {
        if (!active) return;
        const items = Array.isArray(data?.items) ? data.items : [];
        if (page > 0 && !items.length) {
          setPage(page - 1);
          return;
        }
        if (source === 'collection') {
          setResult(prev => ({
            items,
            total: data?.total ?? 0,
            pending: prev.pending,
          }));
          if (status === 'pendente') {
            setCollectionPending(data?.total ?? 0);
          }
        } else {
          setResult({
            items,
            total: data?.total ?? 0,
            pending: data?.pending ?? 0,
          });
        }
      })
      .catch(err => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [source, status, query, page, revision]);

  useEffect(() => {
    let active = true;
    if (source !== 'collection') {
      moderationApi.collectionReviews('pendente', 0)
        .then(data => {
          if (active) setCollectionPending(data?.total ?? 0);
        })
        .catch(() => {});
    }
    return () => { active = false; };
  }, [source, revision]);

  const openDecision = (event, nextStatus) => {
    setDecision({ event, status: nextStatus });
    setReason('');
    setDecisionError('');
    setSuccess('');
  };

  const submit = async e => {
    e.preventDefault();
    if (submitting.current) return;
    if (decision.status === 'rejeitado' && !reason.trim()) {
      setDecisionError('Escreva uma justificativa para orientar quem enviou.');
      return;
    }
    submitting.current = true;
    setBusy(true);
    setDecisionError('');
    try {
      await moderationApi.decide(decision.event.id, decision.status, reason.trim());
      if (source === 'collection') {
        setSuccess(decision.status === 'aprovado'
          ? 'Item da coleta aprovado e publicado no catálogo público.'
          : 'Item da coleta recusado e mantido fora do catálogo público.');
      } else {
        setSuccess(decision.status === 'aprovado'
          ? 'Sugestão aprovada e publicada. O estudante foi notificado.'
          : 'Sugestão recusada. A justificativa foi enviada ao estudante.');
      }
      setDecision(null);
      setRevision(v => v + 1);
    } catch (err) {
      setDecisionError(err.message);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  const isCollection = source === 'collection';
  const filteredItems = isCollection && query.trim()
    ? result.items.filter(item =>
      `${item.titulo || ''} ${item.motivo_revisao || ''} ${item.campus || ''}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()))
    : result.items;

  return (
    <ManagementShell
      title="Moderação de Eventos"
      description="Analise sugestões enviadas por estudantes e itens coletados da Agenda UnB Notícias que aguardam revisão."
    >
      <div className="management-toolbar" style={{ marginBottom: '12px' }}>
        <div className="management-tabs" role="group" aria-label="Origem da fila de moderação">
          {Object.entries(SOURCES).map(([key, label]) => (
            <button
              key={key}
              type="button"
              aria-pressed={source === key}
              className={source === key ? 'active' : ''}
              onClick={() => { setSource(key); setStatus('pendente'); setPage(0); setSuccess(''); }}
            >
              {label}
              <span className="management-count">
                {key === 'suggestions' ? result.pending : collectionPending}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="management-toolbar">
        <div className="management-tabs" role="group" aria-label="Status dos itens">
          {Object.entries(STATUS).map(([key, label]) => (
            <button
              key={key}
              type="button"
              aria-pressed={status === key}
              className={status === key ? 'active' : ''}
              onClick={() => { setStatus(key); setPage(0); }}
            >
              {label}
              {key === 'pendente' && (
                <span className="management-count">
                  {isCollection ? collectionPending : result.pending}
                </span>
              )}
            </button>
          ))}
        </div>
        <button type="button" className="manage-button" onClick={() => setRevision(v => v + 1)} disabled={loading}>
          <Icon>refresh</Icon>Atualizar
        </button>
      </div>

      <div className="management-search-row">
        <label className="management-search">
          <Icon>search</Icon>
          <span className="sr-only">
            {isCollection ? 'Filtrar itens coletados por título ou motivo' : 'Buscar sugestões por título ou estudante'}
          </span>
          <input
            value={search}
            maxLength={120}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
            placeholder={isCollection ? 'Filtrar na página por título, campus ou motivo' : 'Buscar por título ou estudante'}
          />
        </label>
        {search && (
          <button type="button" className="manage-button" onClick={() => { setSearch(''); setPage(0); }}>
            Limpar busca
          </button>
        )}
        <span className="management-muted">Mais antigos primeiro</span>
      </div>

      <Feedback error={error} success={success} onRetry={() => setRevision(v => v + 1)} />

      {loading ? (
        <div className="management-state" role="status">Carregando itens para moderação…</div>
      ) : !error && !filteredItems.length ? (
        <div className="management-state">
          <Icon>{query ? 'search_off' : 'task_alt'}</Icon>
          <h2>{query ? 'Nenhum item encontrado' : status === 'pendente' ? 'Tudo em dia por aqui' : 'Nenhum item nesta lista'}</h2>
          <p>
            {query
              ? 'Tente outro termo ou limpe a busca.'
              : isCollection
                ? 'Itens ambíguos, incompletos ou possíveis duplicatas da coleta aparecerão aqui.'
                : status === 'pendente'
                  ? 'Novas sugestões dos estudantes aparecerão aqui para análise.'
                  : 'As decisões de moderação ficarão disponíveis aqui.'}
          </p>
        </div>
      ) : !error && (
        <section className="suggestion-list" aria-label={`${SOURCES[source]} - ${STATUS[status]}`}>
          {filteredItems.map(event => {
            const missingDate = !event.data_evento && !event.data_inicio_civil;
            const pastDate = event.data_evento && new Date(event.data_evento) < new Date();
            const originUrl = safeEventUrl(event.fonte_url);
            const externalUrl = safeEventUrl(event.link_externo);
            return (
              <article className="suggestion-row" key={event.id}>
                <div className="suggestion-body">
                  <div className="suggestion-title">
                    <h2>{event.titulo}</h2>
                    <span className="management-tag">{event.categoria || 'Sem categoria'}</span>
                    {isCollection && event.motivo_revisao && (
                      <span className="management-tag">
                        {REVIEW_REASONS[event.motivo_revisao] || event.motivo_revisao}
                      </span>
                    )}
                  </div>
                  <p className="management-muted">
                    {isCollection ? (
                      <>Coletado de <strong>Agenda UnB Notícias</strong> · {formatDate(event.coletado_em)}</>
                    ) : (
                      <>Enviada por <strong>{event.autor_nome}</strong> · {formatDate(event.criado_em)}</>
                    )}
                  </p>
                  <dl className="suggestion-details">
                    <div>
                      <dt><Icon>event</Icon>Quando</dt>
                      <dd>{formatSuggestionWhen(event)}</dd>
                    </div>
                    <div>
                      <dt><Icon>location_on</Icon>Onde</dt>
                      <dd>{[event.campus, event.localizacao].filter(Boolean).join(' · ') || 'Local não informado'}</dd>
                    </div>
                  </dl>
                  <p className="suggestion-description">{event.descricao || 'Nenhuma descrição informada.'}</p>
                  <div className="management-actions" style={{ gap: '16px' }}>
                    {originUrl && (
                      <a className="management-link" href={originUrl} target="_blank" rel="noopener noreferrer">
                        Ver fonte oficial (UnB Notícias)<Icon>open_in_new</Icon><span className="sr-only"> (nova aba)</span>
                      </a>
                    )}
                    {externalUrl && externalUrl !== originUrl && (
                      <a className="management-link" href={externalUrl} target="_blank" rel="noopener noreferrer">
                        Abrir link do evento<Icon>open_in_new</Icon><span className="sr-only"> (nova aba)</span>
                      </a>
                    )}
                  </div>
                  {event.justificativa_recusa && (
                    <div className="suggestion-reason">
                      <strong>Justificativa registrada</strong>
                      <p>{event.justificativa_recusa}</p>
                    </div>
                  )}
                </div>
                {status === 'pendente' && (
                  <footer className="suggestion-actions">
                    <span className="management-muted">
                      {missingDate
                        ? 'Item sem data na fonte: só pode ser aprovado após definição de data.'
                        : pastDate
                          ? 'A data deste evento já passou. Confira antes de aprovar.'
                          : 'A aprovação publica este evento no catálogo público.'}
                    </span>
                    <div className="management-actions">
                      <button type="button" className="manage-button" onClick={() => openDecision(event, 'rejeitado')}>
                        <Icon>close</Icon>Recusar
                      </button>
                      <button
                        type="button"
                        className="manage-button primary"
                        disabled={missingDate}
                        title={missingDate ? 'Eventos sem data não podem ser publicados diretamente.' : undefined}
                        onClick={() => openDecision(event, 'aprovado')}
                      >
                        <Icon>check</Icon>Aprovar
                      </button>
                    </div>
                  </footer>
                )}
              </article>
            );
          })}
        </section>
      )}

      {!error && <Pagination page={page} total={result.total} onPage={setPage} busy={loading} />}

      {decision && (
        <Modal
          title={decision.status === 'rejeitado' ? 'Recusar item' : 'Aprovar evento'}
          busy={busy}
          onClose={() => setDecision(null)}
        >
          <form onSubmit={submit}>
            <p className="dialog-event-title">{decision.event.titulo}</p>
            {decision.status === 'rejeitado' ? (
              <label className="management-field">
                Justificativa <span className="management-muted">(obrigatória)</span>
                <textarea
                  autoFocus
                  required
                  maxLength={2000}
                  rows={5}
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                  aria-describedby="reason-help"
                  placeholder={isCollection
                    ? 'Registre o motivo da recusa deste item da coleta.'
                    : 'Explique o que precisa ser ajustado para orientar o estudante.'}
                />
                <small id="reason-help">
                  {isCollection ? 'Ficará registrado no histórico de moderação.' : 'O estudante receberá este texto nas notificações.'} {reason.length}/2000
                </small>
              </label>
            ) : (
              <p>
                {isCollection
                  ? 'O evento coletado será publicado imediatamente no catálogo público.'
                  : 'O evento será publicado na agenda e o estudante receberá uma notificação de aprovação.'}
              </p>
            )}
            <Feedback error={decisionError} />
            <footer className="dialog-actions">
              <button type="button" className="manage-button" disabled={busy} onClick={() => setDecision(null)}>
                Cancelar
              </button>
              <button type="submit" className="manage-button primary" disabled={busy}>
                {busy ? 'Enviando…' : decision.status === 'rejeitado' ? 'Confirmar recusa' : 'Aprovar e publicar'}
              </button>
            </footer>
          </form>
        </Modal>
      )}
    </ManagementShell>
  );
}
