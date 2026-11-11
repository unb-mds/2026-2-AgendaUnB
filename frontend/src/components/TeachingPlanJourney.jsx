import { useCallback, useEffect, useId, useReducer, useRef, useState } from 'react';
import { Icon, Modal } from './ManagementUI';
import ConnectedTeachingPlanJourney from './ConnectedTeachingPlanJourney';
import ClassCatalog from './ClassCatalog';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import { catalogPeriods, demoOffering, loadDemoCatalog, loadDemoFollows, offeringLabel, saveDemoFollows } from '../lib/classCatalogDemo';
import { validatePdf } from '../lib/syllabus';
import { validateReviewItem } from '../lib/syllabusReview';
import { canConfirm, canOpenDemoStep, demoMonths, demoReducer, initialDemoState } from '../lib/teachingPlanDemo';

const steps = ['Selecionar turmas', 'Conectar planos', 'Revisar datas', 'Enviar à agenda'];
const statusLabels = { processing: 'Preparando exemplo', review: 'Revisão pendente', ready: 'Plano vinculado' };
const courseLabel = offeringLabel;
const noPolling = () => false;
const monthLabel = new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric', timeZone: 'UTC' });

function FilePicker({ label, onFile, example, name }) {
  const errorId = useId();
  const [error, setError] = useState('');
  const input = useRef(null);
  return <div className="tp-file-picker">
    <Icon>upload_file</Icon><h3>{label}</h3>
    <p>Escolha um PDF local ou use um arquivo de exemplo.</p>
    <label className="manage-button tp-file-button">Selecionar PDF
      <input ref={input} type="file" accept=".pdf,application/pdf" aria-label={label} aria-invalid={!!error} aria-describedby={error ? errorId : undefined}
        onChange={event => {
          const file = event.target.files?.[0];
          if (!file) return;
          const message = validatePdf(file);
          setError(message);
          onFile(message ? '' : file.name);
          event.target.value = '';
        }} />
    </label>
    <button type="button" className="management-text-button" onClick={() => {
      setError(''); onFile(example);
    }}>Usar PDF de exemplo</button>
    {name && <strong className="tp-file-name">{name}</strong>}
    {error && <p id={errorId} className="tp-error" role="alert">{error}</p>}
    <small>PDF até 10 MB. O arquivo não sai do seu dispositivo e seu conteúdo não é lido nesta demonstração.</small>
  </div>;
}

function CourseStatus({ plan }) {
  return <span className={`tp-badge ${plan?.status || 'missing'}`}>{statusLabels[plan?.status] || 'Plano ausente'}</span>;
}

function DemoReview({ state, dispatch }) {
  const [attempted, setAttempted] = useState(false);
  const container = useRef(null);
  const plan = state.plans[state.activeCourse];
  const course = demoOffering(state.activeCourse);
  const locked = plan.status === 'ready';
  const selected = plan.candidates.filter(item => item.decision === 'selected');
  const confirm = () => {
    setAttempted(true);
    if (canConfirm(plan, state.acknowledged)) dispatch({ type: 'CONFIRM' });
    else requestAnimationFrame(() => container.current?.querySelector('[aria-invalid="true"], [data-ack]')?.focus());
  };
  return <div ref={container}>
    <header className="tp-section-heading"><div><h2>A IA sugere. Você confere.</h2><p>{course.title} · {courseLabel(course)}</p></div><CourseStatus plan={plan} /></header>
    <div className="tp-document"><Icon>description</Icon><div><strong>{plan.fileName}</strong><p>Dados fixos de exemplo, não extraídos do PDF selecionado.</p></div></div>
    <p className="tp-help">Selecione as avaliações que deseja manter. Confira a evidência e informe o fuso explicitamente. Itens descartados não entram na agenda.</p>
    <div className="tp-review-list">{plan.candidates.map((item, index) => {
      const errors = attempted ? validateReviewItem(item) : {};
      const base = `tp-${course.id}-${item.id}`;
      return <fieldset className="tp-review-item" key={item.id} disabled={locked}>
        <legend>Avaliação {index + 1}</legend>
        <div className="tp-review-top"><label className="tp-choice"><input type="checkbox" checked={item.decision === 'selected'} onChange={e => dispatch({ type: 'EDIT', id: item.id, field: 'decision', value: e.target.checked ? 'selected' : 'discarded' })} />Incluir {item.title || `avaliação ${index + 1}`}</label>
          <span className="tp-badge">{!item.time ? 'Horário pendente' : item.decision === 'discarded' ? 'Descartada' : 'Confira os dados'}</span></div>
        <div className="tp-fields">{[['title', 'Título', 'text'], ['type', 'Tipo', 'text'], ['date', 'Data', 'date'], ['time', 'Horário', 'time'], ['utcOffset', 'Fuso UTC', 'text']].map(([field, label, type]) => <div key={field} className={field === 'title' ? 'tp-title-field' : ''}>
          <label htmlFor={`${base}-${field}`}>{label}{item.decision === 'selected' && field !== 'type' ? ' *' : ''}</label>
          <input id={`${base}-${field}`} type={type} value={item[field]} disabled={item.decision === 'discarded'}
            aria-invalid={errors[field] ? true : undefined} aria-describedby={errors[field] ? `${base}-${field}-error` : field === 'utcOffset' ? `${base}-zone` : undefined}
            placeholder={field === 'utcOffset' ? 'Ex.: -03:00' : ''}
            onChange={e => dispatch({ type: 'EDIT', id: item.id, field, value: e.target.value })} />
          {errors[field] && <p className="tp-error" id={`${base}-${field}-error`}>{errors[field]}</p>}
          {field === 'utcOffset' && <small id={`${base}-zone`}>Diferença para UTC na data escolhida.</small>}
        </div>)}</div>
        {item.excerpt && <p className="tp-evidence"><strong>Página {item.page}</strong> “{item.excerpt}”</p>}
      </fieldset>;
    })}</div>
    {!locked ? <div className="tp-review-footer"><div><label className="tp-choice"><input data-ack type="checkbox" checked={state.acknowledged} onChange={e => dispatch({ type: 'ACK', value: e.target.checked })} />Conferi as avaliações e a turma de destino.</label><p>{selected.length} selecionada(s). Alterar os campos exige nova conferência.</p>
      {attempted && !canConfirm(plan, state.acknowledged) && <p className="tp-error" role="alert">Selecione pelo menos uma avaliação, corrija os campos e confirme a conferência.</p>}</div>
      <button type="button" className="manage-button primary" onClick={confirm}>Confirmar e vincular plano<Icon>arrow_forward</Icon></button></div>
      : <div className="tp-review-footer"><p role="status">Plano conferido nesta simulação. Nenhum dado foi publicado.</p><button type="button" className="manage-button primary" onClick={() => dispatch({ type: 'STEP', step: 4 })}>Escolher datas para a agenda<Icon>arrow_forward</Icon></button></div>}
  </div>;
}

function DemoAgenda({ state, dispatch }) {
  const [message, setMessage] = useState('');
  const months = [...new Set([...state.periods.flatMap(demoMonths), ...state.events.map(event => event.date.slice(0, 7))])].sort();
  const [month, setMonth] = useState(() => demoMonths(state.activeCourse ? demoOffering(state.activeCourse).period : state.periods[0])[0]);
  const selectedCount = state.selectedCourses.reduce((sum, id) => sum + state.plans[id].candidates.filter(item => item.decision === 'selected' && !state.events.some(e => e.id === `${id}:${item.id}`)).length, 0);
  const monthEvents = state.events.filter(event => event.date.startsWith(month));
  const [year, monthNumber] = month.split('-').map(Number);
  const firstWeekday = new Date(year, monthNumber - 1, 1).getDay();
  const dayCount = new Date(year, monthNumber, 0).getDate();
  return <div>
    <header className="tp-section-heading"><div><h2>Leve as datas para o seu calendário.</h2><p>Prévia local de Meus Eventos. Nada será gravado na agenda real.</p></div></header>
    <div className="tp-agenda-layout"><div>{state.followedCourses.map(demoOffering).map(course => {
      const plan = state.plans[course.id];
      const imported = plan?.status === 'ready' && plan.candidates.filter(item => item.decision === 'selected').every(item => state.events.some(e => e.id === `${course.id}:${item.id}`));
      return <div className="tp-agenda-choice" key={course.id}><label className="tp-choice"><input type="checkbox" disabled={plan?.status !== 'ready' || imported} checked={state.selectedCourses.includes(course.id)} onChange={e => dispatch({ type: 'SELECT_COURSE', id: course.id, selected: e.target.checked })} /><span><strong>{course.title}</strong><small>{courseLabel(course)}</small><small>{imported ? 'Incluída na prévia' : plan?.status === 'ready' ? 'Plano pronto para selecionar' : 'Conclua o plano antes de selecionar'}</small></span></label><CourseStatus plan={plan} /></div>;
    })}<div className="tp-agenda-summary"><strong>{selectedCount} avaliação(ões) para incluir</strong><button type="button" className="manage-button primary" disabled={!selectedCount} onClick={() => {
      dispatch({ type: 'IMPORT' }); setMessage(`${selectedCount} avaliação(ões) incluída(s) na prévia local. Sua agenda real não foi alterada.`);
    }}><Icon>event_available</Icon>Simular envio para Meus Eventos</button><p role="status">{message || 'A confirmação repetida não duplica itens na prévia.'}</p></div></div>
    <aside className="tp-calendar"><header><h3>Prévia do calendário</h3><label className="sr-only" htmlFor="tp-month">Mês da prévia</label><select id="tp-month" value={month} onChange={e => setMonth(e.target.value)}>{[...new Set([...months, month])].sort().map(value => <option key={value} value={value}>{monthLabel.format(new Date(`${value}-01T00:00:00Z`))}</option>)}</select></header>
      <div className="tp-calendar-grid" aria-hidden="true">{['D', 'S', 'T', 'Q', 'Q', 'S', 'S'].map((day, i) => <span className="tp-weekday" key={`w${i}`}>{day}</span>)}{Array.from({ length: firstWeekday }, (_, i) => <span key={`empty${i}`} />)}{Array.from({ length: dayCount }, (_, i) => <span key={i} className={monthEvents.some(e => Number(e.date.slice(-2)) === i + 1) ? 'has-event' : ''}>{i + 1}</span>)}</div>
      {!monthEvents.length && <p className="tp-help">Nenhuma avaliação na prévia deste mês.</p>}
      <ul className="tp-calendar-events">{monthEvents.sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time)).map(event => <li key={event.id}><strong>{event.title}</strong><p>{event.date.split('-').reverse().join('/')} · {event.time} · UTC{event.utcOffset}</p><small>{demoOffering(event.courseId).title} · Plano de exemplo</small></li>)}</ul>
      <small>Datas fora destes meses continuam na lista completa abaixo.</small>
    </aside></div>
    {!!state.events.length && <details className="tp-event-details"><summary>Ver todas as avaliações incluídas ({state.events.length})</summary><ul>{state.events.map(event => <li key={event.id}>{event.title} · {event.date.split('-').reverse().join('/')} às {event.time} · UTC{event.utcOffset}</li>)}</ul></details>}
  </div>;
}

export default function TeachingPlanJourney({ userId, renderWorkspace }) {
  return userId ? <ConnectedTeachingPlanJourney key={userId} userId={userId} renderWorkspace={renderWorkspace} /> : <DemoTeachingPlanJourney />;
}

function DemoTeachingPlanJourney({ userId }) {
  const [saved] = useState(() => loadDemoFollows(userId));
  const [state, dispatch] = useReducer(demoReducer, saved.ids, ids => initialDemoState({ periods: catalogPeriods(), ids }));
  const [files, setFiles] = useState({});
  const [message, setMessage] = useState(saved.error ? 'Não foi possível recuperar suas turmas neste navegador.' : '');
  const [resetOpen, setResetOpen] = useState(false);
  const [catalogVersion, setCatalogVersion] = useState(0);
  const heading = useRef(null);
  const stepNavigation = useRef(null);
  const previousStep = useRef(state.step);
  const load = useCallback(() => loadDemoCatalog(state.periods), [state.periods]);
  const catalog = useSyllabusResource('demo-class-catalog', load, noPolling);
  const available = id => !catalog.loading && !catalog.error && !!catalog.data?.items.some(offer => offer.id === id);
  const plan = state.plans[state.activeCourse];
  const course = state.activeCourse ? demoOffering(state.activeCourse) : null;
  const processingId = Object.keys(state.plans).find(id => state.plans[id].status === 'processing');

  useEffect(() => {
    if (!processingId) return undefined;
    const timer = setTimeout(() => dispatch({ type: 'PROCESSED', id: processingId }), 650);
    return () => clearTimeout(timer);
  }, [processingId]);
  useEffect(() => {
    if (previousStep.current !== state.step) {
      heading.current?.focus({ preventScroll: true });
      stepNavigation.current?.scrollIntoView({ block: 'start', behavior: 'instant' });
      previousStep.current = state.step;
    }
  }, [state.step]);

  const save = (ids, feedback) => {
    try {
      saveDemoFollows(userId, ids);
      setMessage(feedback);
    } catch {
      setMessage(`${feedback} Não foi possível salvar esta alteração no navegador.`);
    }
  };
  const follow = (offer, following) => {
    if (following && !available(offer.id)) return;
    dispatch({ type: following ? 'FOLLOW' : 'UNFOLLOW', id: offer.id, available: available(offer.id) });
    save(following ? [...state.followedCourses, offer.id] : state.followedCourses.filter(id => id !== offer.id),
      following ? `${offer.title} · ${courseLabel(offer)} adicionada a Minhas turmas.` :
        `Você deixou de seguir ${offer.title} · ${courseLabel(offer)}. A agenda foi preservada.`);
  };

  return <div className="tp-journey">
    <div className="tp-demo-notice"><strong>Catálogo de demonstração</strong><p>Turmas, professores e planos são exemplos até a integração com o Followw. {userId ? 'As turmas seguidas ficam salvas neste navegador para a sua conta.' : 'Sem login, a seleção dura só nesta visita.'}</p></div>
    <nav ref={stepNavigation} className="tp-steps" aria-label="Etapas do plano de ensino">{steps.map((label, i) => <button type="button" key={label} aria-current={state.step === i + 1 ? 'step' : undefined}
      disabled={!canOpenDemoStep(state, i + 1)} onClick={() => dispatch({ type: 'STEP', step: i + 1 })}><span>{i + 1}</span>{label}</button>)}</nav>
    <h2 ref={heading} tabIndex={-1} className="sr-only">Etapa {state.step}: {steps[state.step - 1]}</h2>
    <div hidden={state.step !== 1}>
      <ClassCatalog key={catalogVersion} state={state} catalog={catalog} onFollow={follow} message={message}
        onOpen={id => { if (state.plans[id]?.candidates || available(id)) dispatch({ type: 'OPEN', id }); }} />
    </div>
    {state.step === 2 && course && <section className="tp-upload-layout" aria-labelledby="tp-plan-destination"><div className="tp-panel">
      <header className="tp-section-heading"><div><h2 id="tp-plan-destination">Plano de {course.title}</h2><p>{courseLabel(course)}</p></div><Icon>description</Icon></header>
      {!plan && !available(course.id) ? <div className="tp-linked"><h3>Oferta indisponível para envio</h3><p>Volte ao catálogo e selecione uma oferta disponível antes de preparar um plano.</p><button type="button" className="manage-button" onClick={() => dispatch({ type: 'STEP', step: 1 })}>Voltar ao catálogo</button></div>
        : !plan ? <><FilePicker key={course.id} label="Plano de ensino" name={files[course.id]} example={`plano_${course.code}_exemplo.pdf`} onFile={name => setFiles(previous => ({ ...previous, [course.id]: name }))} />
          <div className="tp-panel-footer"><small>As sugestões serão exemplos fixos.</small><button type="button" className="manage-button primary" disabled={!files[course.id]} onClick={() => dispatch({ type: 'PROCESS', available: available(course.id), name: files[course.id] })}>Simular extração<Icon>arrow_forward</Icon></button></div></>
          : plan.status === 'processing' ? <p role="status" className="tp-processing"><Icon>hourglass_top</Icon>Preparando avaliações de exemplo…</p>
          : <div className="tp-linked"><CourseStatus plan={plan} /><p>{plan.fileName}</p><button type="button" className="manage-button primary" onClick={() => dispatch({ type: 'STEP', step: 3 })}>Abrir avaliações<Icon>arrow_forward</Icon></button></div>}
    </div><aside className="tp-guidance"><h2>A turma certa, o plano certo.</h2><p>Confira o código, a turma e o período. Uma mesma disciplina pode ter cronogramas diferentes em cada oferta.</p><button type="button" className="manage-button" onClick={() => dispatch({ type: 'STEP', step: 1 })}>Voltar a Minhas turmas</button></aside></section>}
    {state.step === 3 && plan?.candidates && <DemoReview key={state.activeCourse} state={state} dispatch={dispatch} />}
    {state.step === 4 && <DemoAgenda state={state} dispatch={dispatch} />}
    <footer className="tp-demo-footer"><button type="button" className="management-text-button" onClick={() => setResetOpen(true)}>Reiniciar demonstração</button></footer>
    {resetOpen && <Modal title="Reiniciar demonstração?" onClose={() => setResetOpen(false)}><p>As turmas seguidas, as edições e a prévia serão apagadas desta demonstração.</p><div className="dialog-actions"><button type="button" className="manage-button" onClick={() => setResetOpen(false)}>Cancelar</button><button type="button" className="manage-button primary" onClick={() => {
      save([], 'Demonstração reiniciada.'); dispatch({ type: 'RESET' }); setFiles({}); setCatalogVersion(version => version + 1); setResetOpen(false);
    }}>Reiniciar</button></div></Modal>}
  </div>;
}
