import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Feedback, Icon, ManagementShell } from '../components/ManagementUI';
import CustomSelect from '../components/CustomSelect';
import SemesterCatalog from '../components/SemesterCatalog';
import SemesterReview from '../components/SemesterReview';
import SemesterTextReview, { TextCapacity } from '../components/SemesterTextReview';
import SharedClassPlans from '../components/SharedClassPlans';
import { useAuth } from '../contexts/AuthContext';
import { useSemesterPlans } from '../contexts/SemesterPlansContext';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import { MAX_APPROVED_TEXT_BYTES } from '../lib/approvedText';
import { catalogApi } from '../lib/classCatalogApi';
import { isProcessing, PLAN_STATES, syllabusError, SYLLABUS_PAGE_SIZE } from '../lib/syllabus';
import { syllabusApi } from '../lib/syllabusApi';
import { mergeReview } from '../lib/semesterReview';
import '../styles/semester-plans.css';

const periodOf = value => {
  const year = value?.year ?? value?.ano;
  const semester = value?.semester ?? value?.semestre;
  return year && semester ? `${year}.${semester}` : '';
};
const offerLabel = offer => `${offer.subject_name} · ${offer.subject_code} · Turma ${offer.class_number} · ${periodOf(offer)}`;
const empty = [];
async function loadFollowed(signal) {
  const result = await catalogApi.followed(signal);
  if (!Array.isArray(result?.items)) throw new Error('Resposta das turmas inválida.');
  return result;
}
const uploadLabels = {
  queued: 'Na fila de envio', sending: 'Preparando texto…',
  invalid: 'Arquivo inválido', failed: 'Falha no envio', uncertain: 'Envio a verificar',
};

function TextEntry({ offer }) {
  const workspace = useSemesterPlans();
  const { text } = workspace.rawText;
  const submitted = useRef(false);
  const setText = value => workspace.setRawText(current => ({ ...current, text: value }));
  const size = new TextEncoder().encode(text).length;
  return <form className="semester-raw" onSubmit={event => {
    event.preventDefault();
    if (submitted.current || !offer || !text.trim() || size > MAX_APPROVED_TEXT_BYTES) return;
    submitted.current = true;
    workspace.addText(text, offer);
    setText('');
  }}>
    <label className="semester-field">Texto do plano<textarea aria-label="Texto do plano" rows={5} value={text} onChange={event => { submitted.current = false; setText(event.target.value); }} /></label>
    <TextCapacity size={size} />
    <button className="manage-button" disabled={!offer || !text.trim() || size > MAX_APPROVED_TEXT_BYTES}>Preparar texto para revisão</button>
  </form>;
}

function PlanQueue({ options, followed, initialOffer, onOffer, plans, selectedId, onSelect, onUploaded, history, page, changePage, onCatalog }) {
  const workspace = useSemesterPlans();
  const fileRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [open, setOpen] = useState(true);
  const [message, setMessage] = useState('');
  const selectedOffer = options.find(offer => offer.id === initialOffer);
  const append = files => {
    if (!files?.length || !selectedOffer) return;
    workspace.addFiles(files, selectedOffer);
    setOpen(true);
    setMessage(`${files.length} arquivo(s) na fila para ${offerLabel(selectedOffer)}.`);
  };
  const chooseFiles = () => fileRef.current?.click();

  return <aside className="semester-section semester-queue" aria-labelledby="semester-queue-title">
    <div className="semester-section-heading">
      <h2 id="semester-queue-title">Seus planos</h2>
      <button className="manage-icon-button semester-queue-toggle" type="button" aria-expanded={open} aria-controls="semester-queue-body"
        aria-label={open ? 'Recolher fila de planos' : 'Expandir fila de planos'} onClick={() => setOpen(!open)}><Icon>{open ? 'expand_less' : 'expand_more'}</Icon></button>
    </div>
    <div className="semester-plan-offer">
      <CustomSelect value={initialOffer || ''} onChange={onOffer} ariaLabel="Turma dos planos"
        disabled={!followed.length} placeholder={followed.length ? 'Selecione uma turma' : 'Nenhuma turma seguida'}
        options={followed.map(offer => ({
          value: offer.id,
          label: offer.subject_name,
          detail: followed.some(other => other.id !== offer.id && other.subject_name === offer.subject_name) ? offerLabel(offer) : undefined,
        }))} />
      {!followed.length ? <button className="management-text-button" type="button" onClick={onCatalog}>Adicione uma turma para enviar</button>
        : !initialOffer && <small>Selecione uma turma antes de enviar um plano.</small>}
    </div>
    <input ref={fileRef} type="file" hidden accept=".pdf,application/pdf" multiple onChange={event => { append(event.target.files); event.target.value = ''; }} />
    <div className={`semester-drop${dragging ? ' is-dragging' : ''}`}
        onDragOver={event => { event.preventDefault(); if (selectedOffer) setDragging(true); }}
        onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget instanceof Node ? event.relatedTarget : null)) setDragging(false); }}
        onDrop={event => { event.preventDefault(); setDragging(false); append(event.dataTransfer.files); }}>
        <button id="semester-add-pdfs" className="manage-button primary" type="button" onClick={chooseFiles} disabled={!selectedOffer}><Icon>upload_file</Icon>Adicionar planos</button>
        <small>Arraste ou selecione PDFs com texto · até 10 MB e 10 páginas por arquivo</small>
      </div>
      <TextEntry offer={selectedOffer} />
      <p className="sr-only" role="status">{message}</p>
    <div id="semester-queue-body" className={open ? '' : 'semester-queue-collapsed'}>
      {!!workspace.uploads.length && <ul className="semester-queue-list">
        {workspace.uploads.map(item => <li key={item.id}>
          <div className="semester-queue-line">
            <Icon>description</Icon><div><strong>{item.name}</strong><small>{item.offer ? offerLabel(item.offer) : ''}</small></div>
            {item.status !== 'sending' && <button className="manage-icon-button" aria-label={`Retirar ${item.name} da fila`} onClick={() => workspace.remove(item.id)}><Icon>close</Icon></button>}
          </div>
          <small role={item.status === 'sending' ? 'status' : undefined}>{uploadLabels[item.status]}</small>
          <Feedback error={item.error} />
          {item.status === 'failed' && <button className="manage-button" onClick={() => workspace.retryUpload(item.id)}>Tentar novamente</button>}
          {item.text && item.status === 'failed' && !workspace.rawText.text && <button className="management-text-button" onClick={() => {
            workspace.setRawText({ text: item.text });
            onOffer(item.offer.id);
            workspace.remove(item.id);
          }}>Editar texto</button>}
          {item.status === 'uncertain' && <>
            <button className="manage-button" onClick={() => {
              if (initialOffer === item.offer.id) onUploaded();
              else onOffer(item.offer.id);
              workspace.acknowledgeUpload(item.id);
            }}>Consultar histórico</button>
            {workspace.uploadNotice[item.id] && initialOffer === item.offer.id && page === 0 && !history.loading && !history.error && history.data &&
              <button className="management-text-button" onClick={() => workspace.retryUncertainUpload(item.id)}>Não encontrei no histórico. Reenviar</button>}
          </>}
        </li>)}
      </ul>}
      <ul className="semester-queue-list">
        {plans.map(plan => {
          const pendingText = plan.authorizationRequired && plan.preparedTextAvailable;
          const state = pendingText ? 'Autorizar texto' : plan.status === 'concluido' && plan.extractedEventsCount === 0 ? 'Sem avaliações' : PLAN_STATES[plan.status]?.label || 'Consultar estado';
          return <li key={plan.id} className={selectedId === plan.id ? 'is-current' : ''}>
            <div className="semester-queue-line"><Icon>{pendingText ? 'article' : PLAN_STATES[plan.status]?.icon || 'description'}</Icon>
              <div><strong>{plan.disciplina || plan.fileName}</strong>{plan.disciplina && <small>{plan.fileName}</small>}</div>
            </div>
            <button className={`manage-button${pendingText ? ' semester-text-action' : ''}`} aria-current={selectedId === plan.id ? 'true' : undefined}
              aria-label={`${state}: ${plan.fileName}`} onClick={() => onSelect(plan.id)}>{state}<Icon>arrow_forward</Icon></button>
            <Feedback error={workspace.planErrors[plan.id]} onRetry={() => workspace.loadPlan(plan.id, true)} />
          </li>;
        })}
      </ul>
      {history.loading && <p role="status">Carregando planos…</p>}
      <Feedback error={history.error && syllabusError(history.error, 'historico')} onRetry={history.retry} />
      {history.data && (history.data.total > SYLLABUS_PAGE_SIZE || page > 0) && <nav aria-label="Histórico de planos" className="semester-pagination">
        <button className="manage-button" disabled={page === 0 || history.loading} onClick={() => changePage(page - 1)}>Anterior</button>
        <span>Página {page + 1}</span>
        <button className="manage-button" disabled={history.loading || (page + 1) * SYLLABUS_PAGE_SIZE >= history.data.total} onClick={() => changePage(page + 1)}>Próxima</button>
      </nav>}
    </div>
  </aside>;
}

function PlanDetails({ plan, onClose, onOpenText }) {
  const workspace = useSemesterPlans();
  return <section className="semester-section" aria-labelledby="semester-plan-title">
    <header className="semester-section-heading"><h2 id="semester-plan-title" tabIndex={-1}>{plan.disciplina || plan.fileName}</h2>
      <button className="manage-button" onClick={onClose}>Voltar às avaliações</button>
    </header>
    <p role="status">{plan.status === 'concluido' && plan.extractedEventsCount === 0 ? 'A análise terminou sem encontrar avaliações.' :
      plan.authorizationRequired ? 'O texto aguarda sua autorização.' : PLAN_STATES[plan.status]?.title || 'Estado indisponível'}</p>
    <Feedback error={plan.errorMessage || workspace.planErrors[plan.id]} onRetry={workspace.planErrors[plan.id] ? () => workspace.loadPlan(plan.id, true) : undefined} />
    {plan.preparedTextAvailable && !isProcessing(plan) && <button className="manage-button" onClick={onOpenText}>Rever texto do plano</button>}
    {isProcessing(plan) && <p>Você já pode adicionar outros planos ou revisar as avaliações disponíveis.</p>}
    {plan.status === 'falha' && <p>Adicione outro PDF com texto ou cole o cronograma para tentar novamente.</p>}
  </section>;
}

function SemesterPanel({ userId }) {
  const workspace = useSemesterPlans();
  const [params, setParams] = useSearchParams();
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [textId, setTextId] = useState(null);
  const [followChanges, setFollowChanges] = useState({});
  const [offerCache, setOfferCache] = useState({});
  const [waitingFor, setWaitingFor] = useState(null);
  const legacyFocus = useRef(false);
  const contentRef = useRef(null);
  const selectedId = params.get('plano');
  const initialOffer = params.get('oferta');
  const requestedPage = Number(params.get('pagina') || 1);
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 && requestedPage <= 100000 ? requestedPage - 1 : 0;
  const followed = useSyllabusResource(userId, loadFollowed);
  useEffect(() => {
    if (!followed.data) return;
    const ids = new Set(followed.data.items.map(offer => offer.id));
    setFollowChanges(current => {
      const pending = Object.entries(current).filter(([id, offer]) => ids.has(id) !== Boolean(offer));
      return pending.length === Object.keys(current).length ? current : Object.fromEntries(pending);
    });
  }, [followed.data]);
  const changed = Object.entries(followChanges);
  const followedOffers = [...(followed.data?.items || empty).filter(offer => !Object.hasOwn(followChanges, offer.id)),
    ...changed.flatMap(([, offer]) => offer ? [offer] : [])];
  const loadHistory = useCallback(signal => syllabusApi.list(page, signal, initialOffer), [page, initialOffer]);
  const history = useSyllabusResource(`${userId}:${initialOffer}:${page}`, loadHistory);
  const historyItems = history.data?.items || empty;
  const { observe, loadPlan } = workspace;
  const selectedPlan = workspace.plans[selectedId];
  const openOfferId = initialOffer || selectedPlan?.offeringId;
  const loadOffer = useCallback(signal => catalogApi.get(openOfferId, signal), [openOfferId]);
  const openOffer = useSyllabusResource(openOfferId, loadOffer);
  useEffect(() => {
    if (openOfferId && openOffer.data?.id === openOfferId && typeof openOffer.data.available === 'boolean') setOfferCache(current => ({ ...current, [openOfferId]: openOffer.data }));
  }, [openOffer.data, openOfferId]);

  const offers = { ...offerCache, ...Object.fromEntries(followedOffers.map(offer => [offer.id, offer])) };
  if (openOffer.data && openOffer.data.id === openOfferId && typeof openOffer.data.available === 'boolean') offers[openOfferId] = openOffer.data;
  const allPlans = [...new Map([...historyItems, ...workspace.recent, ...Object.values(workspace.plans)]
    .filter(plan => !initialOffer || plan.offeringId === initialOffer)
    .map(plan => [plan.id, plan])).values()];
  const periods = [...new Set([...followedOffers, ...allPlans, ...Object.values(offerCache)].map(periodOf).filter(Boolean))].sort().reverse();
  const period = params.get('periodo') ?? (periodOf(offers[initialOffer] || selectedPlan) || '');
  const planPeriod = plan => periodOf(offers[plan.offeringId] || plan);
  const scoped = allPlans.filter(plan => !period || !planPeriod(plan) || period === planPeriod(plan) || plan.id === selectedId)
    .sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
  const allowedPlans = scoped.filter(plan => !workspace.authorizations[plan.id]?.busy && !workspace.authorizations[plan.id]?.uncertain && !plan.authorizationRequired && plan.status === 'concluido' && !!plan.candidates?.length);
  const rows = allowedPlans.flatMap(plan => mergeReview(plan, offers[plan.offeringId]?.schedule, workspace.drafts));
  const available = followedOffers.map(offer => offers[offer.id]).filter(offer => offer.available === true);
  const pageIds = new Set([...historyItems, ...workspace.recent].map(plan => plan.id));
  const queuePlans = scoped.filter(plan => pageIds.has(plan.id) || isProcessing(plan) || plan.id === selectedId || plan.authorizationRequired);
  const offerIds = [...new Set(allowedPlans.filter(plan => plan.offeringId && !offers[plan.offeringId] &&
    plan.candidates.some(candidate => candidate.type === 'prova' && !candidate.suggestedTime && !candidate.startsAt))
    .map(plan => plan.offeringId))].sort().join(',');
  useEffect(() => {
    if (!offerIds) return;
    const controller = new AbortController();
    Promise.allSettled(offerIds.split(',').map(async id => [id, await catalogApi.get(id, controller.signal)]))
      .then(results => {
        if (controller.signal.aborted) return;
        const loaded = Object.fromEntries(results.flatMap(result => result.status === 'fulfilled' && result.value[1]?.id === result.value[0] &&
          result.value[1].available ? [result.value] : []));
        if (Object.keys(loaded).length) setOfferCache(current => ({ ...current, ...loaded }));
      });
    return () => controller.abort();
  }, [offerIds]);
  const textPlan = selectedPlan?.preparedTextAvailable && (selectedPlan.authorizationRequired || textId === selectedId) ? selectedPlan : null;
  const wrongOffer = selectedPlan && initialOffer && selectedPlan.offeringId !== initialOffer;
  const pendingAuth = scoped.find(plan => plan.authorizationRequired && plan.preparedTextAvailable && plan.id !== selectedId);

  useEffect(() => { observe(historyItems); }, [historyItems, observe]);
  useEffect(() => { if (selectedId) loadPlan(selectedId); }, [selectedId, loadPlan]);
  useEffect(() => {
    if (legacyFocus.current || selectedId || !['3', '4'].includes(params.get('etapa'))) return;
    legacyFocus.current = true;
    document.getElementById('semester-review-title')?.focus();
  }, [selectedId, params]);
  useEffect(() => {
    if (!waitingFor || selectedId !== waitingFor || !selectedPlan) return;
    contentRef.current?.querySelector('h2')?.focus();
    setWaitingFor(null);
  }, [waitingFor, selectedId, selectedPlan]);

  const updateParams = update => setParams(previous => {
    const next = new URLSearchParams(previous);
    update(next);
    return next;
  });
  const closePlan = () => {
    updateParams(next => { next.delete('plano'); next.delete('etapa'); });
    setTextId(null);
    requestAnimationFrame(() => document.getElementById('semester-review-title')?.focus());
  };
  const selectPlan = id => {
    setTextId(null);
    setWaitingFor(id);
    updateParams(next => { next.set('plano', id); next.delete('etapa'); });
  };
  const selectOffer = id => {
    setTextId(null);
    updateParams(next => {
      if (id) {
        next.set('oferta', id);
        next.delete('periodo');
      } else next.delete('oferta');
      for (const key of ['plano', 'pagina', 'etapa']) next.delete(key);
    });
  };
  const showCatalog = () => {
    setCatalogOpen(true);
    requestAnimationFrame(() => {
      const title = document.getElementById('semester-catalog-title');
      title?.focus({ preventScroll: true });
      title?.scrollIntoView({ block: 'nearest' });
    });
  };
  const onFollowed = (offer, value) => {
    if (value && periodOf(offer) && !initialOffer && period !== periodOf(offer)) {
      updateParams(next => { next.set('periodo', periodOf(offer)); next.delete('oferta'); next.delete('plano'); next.delete('pagina'); next.delete('etapa'); });
    }
    setFollowChanges(current => ({ ...current, [offer.id]: value ? offer : null }));
    setOfferCache(current => ({ ...current, [offer.id]: offer }));
    followed.retry();
  };

  const libraryOffers = followedOffers.filter(offer => !period || periodOf(offer) === period);
  const libraryPool = libraryOffers.length ? libraryOffers : followedOffers;
  const libraryOfferId = (openOfferId && followedOffers.some(offer => offer.id === openOfferId))
    ? openOfferId
    : (libraryPool[0]?.id || null);

  return <div className="semester-panel">
    <div className="semester-toolbar">
      <button className={`manage-button${catalogOpen ? '' : ' primary'}`} aria-expanded={catalogOpen} aria-controls="semester-catalog"
        onClick={() => catalogOpen ? setCatalogOpen(false) : showCatalog()}>
        <Icon>{catalogOpen ? 'close' : 'search'}</Icon>{catalogOpen ? 'Fechar catálogo' : 'Buscar turmas'}
      </button>
      <CustomSelect className="custom-input semester-toolbar-period" wrapperWidth="fit-content" ariaLabel="Semestre"
        placeholder="Selecione um semestre" value={period}
        options={(period && !periods.includes(period) ? [period, ...periods] : periods).map(value => ({ value, label: value }))}
        onChange={value => updateParams(next => {
          next.set('periodo', value); next.delete('oferta'); next.delete('plano'); next.delete('pagina'); next.delete('etapa');
        })} />
    </div>
    <Feedback error={followed.error && 'Não foi possível carregar suas turmas.'} onRetry={followed.retry} />
    <div id="semester-catalog" hidden={!catalogOpen}>
      <SemesterCatalog userId={userId} period={period} periods={periods} followed={followedOffers} onFollowed={onFollowed} />
    </div>
    <ul className="semester-metrics" aria-label="Resumo do semestre" aria-live="polite">
      <li><Icon>autorenew</Icon><strong>{scoped.filter(isProcessing).length}</strong> em análise</li>
      <li><Icon>article</Icon><strong>{scoped.filter(plan => plan.authorizationRequired && plan.preparedTextAvailable).length}</strong> a autorizar</li>
      <li><Icon>edit_calendar</Icon><strong>{rows.filter(row => row.attention).length}</strong> a revisar</li>
      <li><Icon>event_available</Icon><strong>{rows.filter(row => row.status === 'confirmado' && !row.candidate.removed).length}</strong> adicionadas</li>
    </ul>
    {initialOffer && <div className="semester-offer-context">
      <strong>{offers[initialOffer] ? offerLabel(offers[initialOffer]) : 'Planos da turma'}</strong>
      <button className="management-text-button" onClick={() => selectOffer('')}>Ver todos os planos</button>
      {offers[initialOffer]?.available === false && <span>Oferta indisponível para novos envios.</span>}
      <Feedback error={openOffer.error?.message} onRetry={openOffer.retry} />
    </div>}
    <div className="semester-layout">
      <PlanQueue options={available} followed={followedOffers} initialOffer={initialOffer} onOffer={selectOffer} plans={queuePlans} selectedId={!wrongOffer && selectedId} onSelect={selectPlan}
        history={history} page={page} onCatalog={showCatalog}
        onUploaded={() => { updateParams(next => next.delete('pagina')); history.retry(); }}
        changePage={index => updateParams(next => next.set('pagina', String(index + 1)))} />
      <div className="semester-content" ref={contentRef}>
        {wrongOffer ? <Feedback error="Este plano pertence a outra oferta. Abra-o pelo histórico correto." /> :
          textPlan ? <SemesterTextReview key={textPlan.id} plan={textPlan} onClose={closePlan} /> :
          selectedPlan ? <PlanDetails plan={selectedPlan} onClose={closePlan} onOpenText={() => setTextId(selectedId)} /> :
          selectedId ? <div className="semester-section">{workspace.planErrors[selectedId] ?
            <Feedback error={workspace.planErrors[selectedId]} onRetry={() => loadPlan(selectedId, true)} /> : <p role="status">Consultando plano…</p>}</div> : null}
        {selectedPlan && !selectedPlan.authorizationRequired && pendingAuth && <button className="manage-button" onClick={() => selectPlan(pendingAuth.id)}>Revisar próximo texto <Icon>arrow_forward</Icon></button>}
        <SemesterReview plans={allowedPlans} allPlans={scoped} rows={rows} offers={offers} onPlan={selectPlan} onOpenCatalog={showCatalog} />
        {libraryOfferId && !wrongOffer && (
          <SharedClassPlans
            key={libraryOfferId}
            offeringId={libraryOfferId}
            offer={offers[libraryOfferId]}
            offers={libraryPool}
            onSelectOffer={selectOffer}
            onImported={() => { if (selectedId) loadPlan(selectedId, true); }}
          />
        )}
      </div>
    </div>
  </div>;
}

function GuestTeachingPlanNotice() {
  return <div className="semester-panel">
    <section className="semester-section semester-guest" aria-labelledby="semester-guest-title">
      <Icon>lock</Icon>
      <h2 id="semester-guest-title">Entre na sua conta para acessar planos de ensino</h2>
      <p>
        Faça login para seguir turmas do catálogo, consultar versões compartilhadas, enviar planos de ensino
        e importar avaliações para sua agenda pessoal.
      </p>
      <div className="semester-guest-actions">
        <Link className="manage-button primary" to="/?auth=login">Entrar na conta<Icon>arrow_forward</Icon></Link>
        <Link className="manage-button" to="/?auth=signup">Criar conta</Link>
      </div>
    </section>
  </div>;
}

export default function TeachingPlanPage() {
  const { user } = useAuth();
  return <ManagementShell title="Planos de ensino" description="Organize as datas das suas disciplinas.">
    {user ? <SemesterPanel key={user.id} userId={user.id} /> : <GuestTeachingPlanNotice />}
  </ManagementShell>;
}
