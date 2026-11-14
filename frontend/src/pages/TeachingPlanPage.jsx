import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Feedback, Icon, ManagementShell } from '../components/ManagementUI';
import { useAuth } from '../contexts/AuthContext';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import { syllabusApi } from '../lib/syllabusApi';
import SyllabusReviewPanel from '../components/SyllabusReviewPanel';
import SyllabusTextReview, { SyllabusTextInput } from '../components/SyllabusTextReview';
import JourneyPlanReview from '../components/JourneyPlanReview';
import SharedClassPlans from '../components/SharedClassPlans';
import { OfferingDetails } from '../components/RealClassCatalog';
import TeachingPlanJourney from '../components/TeachingPlanJourney';
import { formatFileSize, formatPlanDate, isProcessing, PLAN_STATES, syllabusError, SYLLABUS_PAGE_SIZE, validatePdf } from '../lib/syllabus';
import '../styles/teaching-plan.css';

const pollList = data => data.items.some(isProcessing);
const manualPath = '/eventos?aba=meus';

function PlanBadge({ status }) {
  const state = PLAN_STATES[status] || { label: 'Estado indisponível', icon: 'help' };
  return <span className={`plan-badge plan-badge-${status}`}><Icon>{state.icon}</Icon>{state.label}</span>;
}

function PlanHelp() {
  return <aside className="plan-help" aria-labelledby="plan-help-title">
    <h2 id="plan-help-title">Do PDF ao seu planejamento</h2>
    <ol className="plan-steps">
      <li><span aria-hidden="true">1</span><div><h3>Envie o plano</h3><p>Selecione a oferta correta no catálogo de turmas.</p></div></li>
      <li><span aria-hidden="true">2</span><div><h3>Revise e autorize o texto</h3><p>Remova informações pessoais antes de decidir pelo envio ao Gemini.</p></div></li>
      <li><Icon>event_available</Icon><div><h3>Você decide o que entra na agenda</h3><p>O envio não cria compromissos. As avaliações precisam de revisão e confirmação.</p></div></li>
    </ol>
    <details className="plan-file-help"><summary>Como saber se meu PDF tem texto?</summary><p>Abra o arquivo e tente selecionar e copiar uma frase. Se não conseguir, peça uma versão com texto selecionável. Fotos e digitalizações sem texto não podem ser analisadas.</p></details>
    <div className="plan-manual"><Icon>edit_calendar</Icon><div><h3>Prefere organizar por conta própria?</h3><p>Em Meus Eventos, use “Criar evento” para cadastrar uma prova, entrega ou outro prazo.</p><Link to={manualPath}>Ir para Meus Eventos<Icon>arrow_forward</Icon></Link></div></div>
  </aside>;
}

function PlanUpload({ onUploaded, offer }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [fileError, setFileError] = useState('');
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const uploadRef = useRef(null);
  const errorRef = useRef(null);
  useEffect(() => () => uploadRef.current?.abort(), []);
  const choose = files => {
    if (uploadRef.current || !files?.length) return;
    const nextError = files.length !== 1 ? 'Selecione apenas um PDF por envio.' : validatePdf(files[0]);
    setFileError(nextError);
    setError('');
    setFile(nextError ? null : files[0]);
    if (inputRef.current) inputRef.current.value = '';
  };
  const submit = async event => {
    event.preventDefault();
    if (uploadRef.current) return;
    const validation = validatePdf(file);
    if (validation) { setFileError(validation); inputRef.current?.focus(); return; }
    const controller = new AbortController();
    uploadRef.current = controller;
    setBusy(true); setError('');
    try {
      const result = await syllabusApi.upload({ file, offeringId: offer.id }, controller.signal);
      if (controller.signal.aborted) return;
      setFile(null);
      onUploaded(result);
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(syllabusError(err, 'envio'));
        requestAnimationFrame(() => errorRef.current?.focus());
      }
    } finally {
      if (!controller.signal.aborted) { uploadRef.current = null; setBusy(false); }
    }
  };
  return <section className="plan-upload" aria-labelledby="plan-upload-title">
    <header className="plan-section-heading"><div><h2 id="plan-upload-title">Enviar plano de ensino</h2><p>Comece pelo PDF fornecido para sua disciplina.</p></div><Icon>upload_file</Icon></header>
    <form onSubmit={submit} aria-busy={busy}>
      <fieldset disabled={busy}>
        <legend className="sr-only">Arquivo e período de referência</legend>
        <OfferingDetails offer={offer} />
        <div className={`plan-dropzone${dragging ? ' dragging' : ''}${file ? ' has-file' : ''}`}
          onDragOver={event => { event.preventDefault(); if (!busy) setDragging(true); }}
          onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
          onDrop={event => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files); }}>
          <Icon>{file ? 'task' : 'upload_file'}</Icon>
          <strong>{file ? file.name : 'Arraste seu plano para cá'}</strong>
          <p>{file ? `${formatFileSize(file.size)} · PDF selecionado` : 'ou selecione o arquivo no seu dispositivo'}</p>
          <label className="manage-button plan-file-picker">{file ? 'Trocar PDF' : 'Selecionar PDF'}<input ref={inputRef} type="file" accept=".pdf,application/pdf" aria-label={file ? 'Trocar PDF' : 'Selecionar PDF'} aria-describedby="plan-file-rules plan-file-validation" aria-invalid={!!fileError} onChange={event => choose(event.target.files)} /></label>
          <small id="plan-file-rules">PDF de até 10 MB e 10 páginas, com texto selecionável.</small>
        </div>
        <p id="plan-file-validation" className="plan-validation" role={fileError ? 'alert' : undefined}>{fileError}</p>
        {file && <button type="button" className="management-text-button" onClick={() => { setFile(null); inputRef.current?.focus(); }}>Remover arquivo</button>}
      </fieldset>
      {error && <div ref={errorRef} tabIndex={-1}><Feedback error={error} /><Link className="management-text-button" to={manualPath}>Cadastrar prazos manualmente</Link></div>}
      <div className="plan-submit"><span><Icon>lock</Icon>Plano particular da sua conta</span><button className="manage-button primary" disabled={busy} type="submit"><Icon>{busy ? 'hourglass_top' : 'upload'}</Icon>{busy ? 'Enviando PDF…' : 'Preparar PDF para revisão'}</button></div>
      <p className="plan-submit-note" role="status">{busy ? 'Aguarde a confirmação do envio antes de sair da página.' : 'O texto será extraído localmente e o PDF descartado. O envio ao Gemini exige sua autorização posterior.'}</p>
    </form>
  </section>;
}

function PlanTracking({ id, onClose, offeringId, onConfirmed, onChanged }) {
  const load = useCallback(async signal => {
    const plan = await syllabusApi.get(id, signal);
    if (offeringId && plan.offeringId !== offeringId) throw new Error('Este plano pertence a outra oferta. Abra um plano pelo histórico desta turma.');
    return plan;
  }, [id, offeringId]);
  const { data: plan, loading, error, retry } = useSyllabusResource(id, load, isProcessing);
  const headingRef = useRef(null);
  useEffect(() => { headingRef.current?.focus(); }, [id]);
  const state = PLAN_STATES[plan?.status];
  const empty = plan?.status === 'concluido' && plan.extractedEventsCount === 0;
  return <section className="plan-tracking" aria-labelledby="plan-tracking-title">
    <header className="plan-section-heading"><h2 id="plan-tracking-title" tabIndex={-1} ref={headingRef}>Acompanhamento</h2><button className="manage-icon-button" onClick={onClose} aria-label="Fechar acompanhamento"><Icon>close</Icon></button></header>
    {loading && <p role="status" className="management-muted">Consultando seu plano…</p>}
    <Feedback error={error && syllabusError(error)} onRetry={retry} />
    {error && !plan && <Link className="management-text-button" to={manualPath}>Cadastrar prazos manualmente</Link>}
    {plan && <>
      <h3 className="plan-tracking-subject">{plan.disciplina || plan.fileName}</h3>
      <p className="plan-tracking-file">{plan.fileName} · {formatPlanDate(plan.createdAt)}</p>
      <div className="plan-result" role="status" aria-live="polite" aria-atomic="true">
        <PlanBadge status={plan.status} />
        <h3>{plan.authorizationRequired ? 'Aguardando sua revisão do texto' : empty ? 'Nenhuma avaliação encontrada' : state?.title || 'Estado de processamento indisponível'}</h3>
        <p>{plan.authorizationRequired ? 'Na última consulta, o envio ao Gemini ainda aguardava sua autorização. Revise o trecho abaixo e decida se deseja autorizar.' : empty ? 'A análise terminou, mas não identificou avaliações neste PDF. Isso não é uma falha de processamento. Você pode cadastrar seus prazos manualmente.' : state?.description || 'Tente consultar novamente para verificar o andamento.'}</p>
        {plan.status === 'concluido' && plan.extractedEventsCount > 0 && <p><strong>{plan.extractedEventsCount} {plan.extractedEventsCount === 1 ? 'avaliação encontrada' : 'avaliações encontradas'}.</strong> Consulte a disponibilidade na área de revisão abaixo.</p>}
        {plan.status === 'falha' && plan.errorMessage && <p className="plan-error-detail">{plan.errorMessage}</p>}
      </div>
      {isProcessing(plan) && <p className="management-muted">{error ? 'A atualização automática foi pausada. Tente novamente para retomar.' : 'Atualização automática enquanto esta página estiver visível.'}</p>}
      {!state && <button className="manage-button" onClick={retry} disabled={loading}>Consultar novamente</button>}
      {(empty || plan.status === 'falha') && <div className="plan-recovery"><Link className="manage-button" to={`/plano-de-ensino?${new URLSearchParams({ ...(plan.offeringId ? { oferta: plan.offeringId } : {}), etapa: '2' })}`}>Enviar outro PDF ou texto</Link><Link className="management-text-button" to={manualPath}>Cadastrar prazos manualmente</Link></div>}
    </>}
    {!loading && !error && plan?.preparedTextAvailable && <SyllabusTextReview key={plan.id} plan={plan} onAuthorized={() => { retry(); onChanged(); }} />}
    {!plan?.authorizationRequired && (!loading && !error && offeringId && plan?.status === "concluido" && plan.candidates?.length ? <JourneyPlanReview key={plan.id} plan={plan} onConfirmed={onConfirmed} /> : <SyllabusReviewPanel selected plan={plan} loading={loading} error={error} />)}
  </section>;
}

function PlanWorkspace({ userId, offer, step, onStep }) {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get('plano');
  const requestedPage = Number(params.get('pagina') || 1);
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 && requestedPage <= 100000 ? requestedPage - 1 : 0;
  const loadList = useCallback(signal => syllabusApi.list(page, signal, offer?.id), [page, offer?.id]);
  const history = useSyllabusResource(`${userId}:${offer?.id}:${page}`, loadList, pollList, 15000);
  const setSelection = id => setParams(previous => {
    const next = new URLSearchParams(previous);
    if (id) { next.set('plano', id); next.set('etapa', '3'); } else next.delete('plano');
    return next;
  });
  const changePage = nextPage => setParams(previous => {
    const next = new URLSearchParams(previous);
    next.set('pagina', String(nextPage + 1));
    return next;
  });
  const onUploaded = plan => {
    setParams(previous => { const next = new URLSearchParams(previous); next.set('plano', plan.id); next.set('etapa', '3'); next.delete('pagina'); return next; });
    history.retry();

  };
  return <>
    <Link className="management-text-button" to="/plano-de-ensino">Voltar ao catálogo de turmas</Link>{offer && <OfferingDetails offer={offer} />}
    <div className="plan-layout"><div>{step === 2 && offer?.available && offer?.following ? <><PlanUpload key={offer.id} offer={offer} onUploaded={onUploaded} /><SyllabusTextInput key={`text-${offer.id}`} offeringId={offer.id} onPrepared={onUploaded} /></> : step === 2 ? <p>Selecione uma oferta disponível que sua conta segue no catálogo para enviar um plano. Seus envios anteriores continuam no histórico.</p> : null}</div><div className="plan-sidebar">{selectedId ? <PlanTracking key={selectedId} id={selectedId} onChanged={history.retry} offeringId={offer?.id} onConfirmed={() => onStep(4)} onClose={() => { setSelection(null); document.getElementById('plan-subject')?.focus(); }} /> : <PlanHelp />}</div></div>
    {offer?.following && <SharedClassPlans key={offer.id} offeringId={offer.id} />}
    {!selectedId && <SyllabusReviewPanel />}
    <section className="plan-history" aria-labelledby="plan-history-title" aria-busy={history.loading}>
      <header className="plan-section-heading"><div><h2 id="plan-history-title">Seus planos enviados</h2><p>Retome um acompanhamento a qualquer momento.</p></div><button className="manage-button" onClick={history.retry} disabled={history.loading}><Icon>refresh</Icon>Atualizar</button></header>
      <Feedback error={history.error && syllabusError(history.error, 'historico')} onRetry={history.retry} />
      {history.loading && <p className="plan-history-loading" role="status">Carregando seus planos…</p>}
      {!history.loading && !history.error && history.data?.items.length === 0 && <div className="plan-history-empty"><Icon>description</Icon><div><h3>{page ? 'Nenhum plano nesta página' : 'Seu próximo semestre começa aqui'}</h3><p>{page ? 'Volte à primeira página para consultar os envios disponíveis.' : 'Envie seu primeiro PDF acima. A disciplina, o arquivo e o andamento da análise aparecerão aqui.'}</p>{page > 0 && <button className="manage-button" onClick={() => changePage(0)}>Voltar à primeira página</button>}</div></div>}
      {!!history.data?.items.length && <ul className="plan-history-list">{history.data.items.map(plan => <li key={plan.id}>
        <Icon>description</Icon><div className="plan-history-info"><h3>{plan.disciplina || plan.fileName}</h3><p>{plan.ano && plan.semestre ? `${plan.ano}.${plan.semestre} · ` : ''}{plan.fileName}</p><time dateTime={plan.createdAt || undefined}>Enviado em {formatPlanDate(plan.createdAt)}</time></div>
        <PlanBadge status={plan.status} /><button className="manage-button" aria-label={`Acompanhar ${plan.disciplina || plan.fileName}`} aria-pressed={selectedId === plan.id} onClick={() => setSelection(plan.id)}>Acompanhar<Icon>arrow_forward</Icon></button>
      </li>)}</ul>}
      {history.data && history.data.total > 0 && <nav className="plan-pagination" aria-label="Páginas dos planos de ensino"><span>{history.data.total} {history.data.total === 1 ? 'plano' : 'planos'} · Página {page + 1} de {Math.max(1, Math.ceil(history.data.total / SYLLABUS_PAGE_SIZE))}</span><div><button className="manage-button" disabled={history.loading || page === 0} onClick={() => changePage(page - 1)}><Icon>chevron_left</Icon>Anterior</button><button className="manage-button" disabled={history.loading || (page + 1) * SYLLABUS_PAGE_SIZE >= history.data.total} onClick={() => changePage(page + 1)}>Próxima<Icon>chevron_right</Icon></button></div></nav>}
    </section>
  </>;
}

export default function TeachingPlanPage() {
  const { user } = useAuth();
  return <ManagementShell title="Planos de ensino" description="Da escolha da turma às datas na sua agenda, confira cada etapa no seu ritmo.">
    <TeachingPlanJourney key={user?.id || 'guest'} userId={user?.id}
      renderWorkspace={(offer, step, onStep) => <PlanWorkspace userId={user.id} offer={offer} step={step} onStep={onStep} />} />
  </ManagementShell>;
}
