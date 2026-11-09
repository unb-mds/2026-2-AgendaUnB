import { useEffect, useId, useReducer, useRef, useState } from 'react';
import { Icon, Modal } from './ManagementUI';
import { validatePdf } from '../lib/syllabus';
import { validateReviewItem } from '../lib/syllabusReview';
import { canConfirm, DEMO_COURSES, demoReducer, initialDemoState } from '../lib/teachingPlanDemo';

const steps = ['Vincular matrícula', 'Conectar planos', 'Revisar datas', 'Enviar à agenda'];
const statusLabels = { processing: 'Preparando exemplo', review: 'Revisão pendente', ready: 'Plano vinculado' };
const courseLabel = course => `Turma ${course.group} · ${course.campus} · 2026.2`;

function FilePicker({ label, onFile, example, disabled = false }) {
  const errorId = useId();
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const input = useRef(null);
  return <div className="tp-file-picker">
    <Icon>upload_file</Icon><h3>{label}</h3>
    <p>Escolha um PDF local ou use um arquivo de exemplo.</p>
    <label className="manage-button tp-file-button">Selecionar PDF
      <input ref={input} type="file" accept=".pdf,application/pdf" aria-label={label} disabled={disabled} aria-invalid={!!error} aria-describedby={error ? errorId : undefined}
        onChange={event => {
          const file = event.target.files?.[0];
          if (!file) return;
          const message = validatePdf(file);
          setError(message);
          if (!message) { setName(file.name); onFile(file.name); }
          event.target.value = '';
        }} />
    </label>
    <button type="button" className="management-text-button" disabled={disabled} onClick={() => {
      setError(''); setName(example); onFile(example);
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
  const course = DEMO_COURSES.find(c => c.id === state.activeCourse);
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
  const [month, setMonth] = useState('2026-11');
  const selectedCount = state.selectedCourses.reduce((sum, id) => sum + state.plans[id].candidates.filter(item => item.decision === 'selected' && !state.events.some(e => e.id === `${id}:${item.id}`)).length, 0);
  const monthEvents = state.events.filter(event => event.date.startsWith(month));
  const [year, monthNumber] = month.split('-').map(Number);
  const firstWeekday = new Date(year, monthNumber - 1, 1).getDay();
  const dayCount = new Date(year, monthNumber, 0).getDate();
  return <div>
    <header className="tp-section-heading"><div><h2>Leve as datas para o seu calendário.</h2><p>Prévia local de Meus Eventos. Nada será gravado na agenda real.</p></div></header>
    <div className="tp-agenda-layout"><div>{DEMO_COURSES.filter(c => c.enrolled).map(course => {
      const plan = state.plans[course.id];
      const imported = plan?.status === 'ready' && plan.candidates.filter(item => item.decision === 'selected').every(item => state.events.some(e => e.id === `${course.id}:${item.id}`));
      return <div className="tp-agenda-choice" key={course.id}><label className="tp-choice"><input type="checkbox" disabled={plan?.status !== 'ready' || imported} checked={state.selectedCourses.includes(course.id)} onChange={e => dispatch({ type: 'SELECT_COURSE', id: course.id, selected: e.target.checked })} /><span><strong>{course.title}</strong><small>Turma {course.group} · {imported ? 'Incluída na prévia' : plan?.status === 'ready' ? 'Plano pronto para selecionar' : 'Conclua o plano antes de selecionar'}</small></span></label><CourseStatus plan={plan} /></div>;
    })}<div className="tp-agenda-summary"><strong>{selectedCount} avaliação(ões) para incluir</strong><button type="button" className="manage-button primary" disabled={!selectedCount} onClick={() => {
      dispatch({ type: 'IMPORT' }); setMessage(`${selectedCount} avaliação(ões) incluída(s) na prévia local. Sua agenda real não foi alterada.`);
    }}><Icon>event_available</Icon>Simular envio para Meus Eventos</button><p role="status">{message || 'A confirmação repetida não duplica itens na prévia.'}</p></div></div>
    <aside className="tp-calendar"><header><h3>Prévia do calendário</h3><label className="sr-only" htmlFor="tp-month">Mês da prévia</label><select id="tp-month" value={month} onChange={e => setMonth(e.target.value)}><option value="2026-11">Novembro de 2026</option><option value="2026-12">Dezembro de 2026</option></select></header>
      <div className="tp-calendar-grid" aria-hidden="true">{['D', 'S', 'T', 'Q', 'Q', 'S', 'S'].map((day, i) => <span className="tp-weekday" key={`w${i}`}>{day}</span>)}{Array.from({ length: firstWeekday }, (_, i) => <span key={`empty${i}`} />)}{Array.from({ length: dayCount }, (_, i) => <span key={i} className={monthEvents.some(e => Number(e.date.slice(-2)) === i + 1) ? 'has-event' : ''}>{i + 1}</span>)}</div>
      {!monthEvents.length && <p className="tp-help">Nenhuma avaliação na prévia deste mês.</p>}
      <ul className="tp-calendar-events">{monthEvents.sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time)).map(event => <li key={event.id}><strong>{event.title}</strong><p>{event.date.split('-').reverse().join('/')} · {event.time} · UTC{event.utcOffset}</p><small>{DEMO_COURSES.find(c => c.id === event.courseId).title} · Plano de exemplo</small></li>)}</ul>
      <small>Datas fora destes meses continuam na lista completa abaixo.</small>
    </aside></div>
    {!!state.events.length && <details className="tp-event-details"><summary>Ver todas as avaliações incluídas ({state.events.length})</summary><ul>{state.events.map(event => <li key={event.id}>{event.title} · {event.date.split('-').reverse().join('/')} às {event.time} · UTC{event.utcOffset}</li>)}</ul></details>}
  </div>;
}

export default function TeachingPlanJourney() {
  const [state, dispatch] = useReducer(demoReducer, undefined, initialDemoState);
  const [enrollmentFile, setEnrollmentFile] = useState('');
  const [files, setFiles] = useState({});
  const [query, setQuery] = useState('');
  const [campus, setCampus] = useState('');
  const [resetOpen, setResetOpen] = useState(false);
  const [pickerVersion, setPickerVersion] = useState(0);
  const heading = useRef(null);
  const stepNavigation = useRef(null);
  const previousStep = useRef(state.step);
  const plan = state.plans[state.activeCourse];
  const course = DEMO_COURSES.find(c => c.id === state.activeCourse);
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
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const filtered = DEMO_COURSES.filter(c => normalize(`${c.title} ${c.initials}`).includes(normalize(query)) && (!campus || c.campus === campus));
  return <div className="tp-journey">
    <div className="tp-demo-notice"><div><strong>Demonstração interativa · 2026.2</strong><p>Turmas e avaliações ilustrativas. Sem leitura de PDFs, envio ao servidor ou alteração de Meus Eventos. Recarregar ou sair desta demonstração reinicia os dados.</p></div><button type="button" className="manage-button" onClick={() => setResetOpen(true)}>Reiniciar demonstração</button></div>
    <nav ref={stepNavigation} className="tp-steps" aria-label="Etapas do plano de ensino">{steps.map((label, i) => <button type="button" key={label} aria-current={state.step === i + 1 ? 'step' : undefined}
      disabled={(i > 0 && !state.enrollment) || (i === 2 && !plan?.candidates)} onClick={() => dispatch({ type: 'STEP', step: i + 1 })}><span>{i + 1}</span>{label}</button>)}</nav>
    <h2 ref={heading} tabIndex={-1} className="sr-only">Etapa {state.step}: {steps[state.step - 1]}</h2>
    {state.step === 1 && <section className="tp-upload-layout"><div className="tp-panel"><header className="tp-section-heading"><div><h2>Sua matrícula é o ponto de partida.</h2><p>Identifique as turmas que fazem parte do seu semestre.</p></div><Icon>school</Icon></header>
      {state.enrollment ? <div className="tp-linked"><Icon>check_circle</Icon><h3>3 turmas de exemplo vinculadas</h3><p>{state.enrollment}</p><button className="manage-button primary" onClick={() => dispatch({ type: 'STEP', step: 2 })}>Ver minhas turmas<Icon>arrow_forward</Icon></button></div> : <>
        <FilePicker key={pickerVersion} label="Comprovante de matrícula" example="comprovante_exemplo_2026_2.pdf" onFile={setEnrollmentFile} />
        <div className="tp-panel-footer"><small><Icon>lock</Icon> Seu comprovante permanece no dispositivo.</small><button type="button" className="manage-button primary" disabled={!enrollmentFile} onClick={() => dispatch({ type: 'ENROLL', name: enrollmentFile })}>Vincular turmas de exemplo<Icon>arrow_forward</Icon></button></div>
      </>}</div><aside className="tp-guidance"><h2>Do plano ao próximo compromisso.</h2><ol><li><strong>Vincule sua matrícula</strong><p>Nesta demonstração, qualquer PDF válido vincula as mesmas três turmas de exemplo.</p></li><li><strong>Complete os planos ausentes</strong><p>Escolha a turma certa e confira as datas sugeridas antes de vincular o plano.</p></li><li><strong>Escolha o que vai para a agenda</strong><p>Somente avaliações selecionadas e conferidas entram na prévia.</p></li></ol></aside></section>}
    {state.step === 2 && <section><header className="tp-section-heading"><div><h2>Minhas turmas</h2><p>3 turmas de exemplo vinculadas · período 2026.2</p></div><a className="management-text-button" href="#tp-catalog">Explorar catálogo de exemplo<Icon>arrow_forward</Icon></a></header>
      <div className="tp-course-list">{DEMO_COURSES.filter(c => c.enrolled).map(c => <article className="tp-course" key={c.id}><span className="tp-initials">{c.initials}</span><div><h3>{c.title}</h3><p>{courseLabel(c)}</p></div><CourseStatus plan={state.plans[c.id]} /><button type="button" className="manage-button" disabled={state.plans[c.id]?.status === 'processing'} onClick={() => dispatch({ type: 'OPEN', id: c.id })}>{state.plans[c.id]?.candidates ? 'Ver avaliações' : 'Selecionar turma'}<Icon>arrow_forward</Icon></button></article>)}</div>
      <div className="tp-upload-layout tp-spaced"><div className="tp-panel"><header className="tp-section-heading"><div><h2>Complete o plano da turma</h2><p>{course.title}</p></div><Icon>description</Icon></header><div className="tp-destination"><strong>Turma de destino</strong><p>{courseLabel(course)}</p></div>
        {!plan ? <><FilePicker key={`${state.activeCourse}-${pickerVersion}`} label="Plano de ensino" example={`plano_${state.activeCourse}_exemplo.pdf`} onFile={name => setFiles(previous => ({ ...previous, [state.activeCourse]: name }))} />
          {files[state.activeCourse] && <p className="tp-help">Selecionado: {files[state.activeCourse]}</p>}
          <div className="tp-panel-footer"><small>As sugestões serão exemplos fixos.</small><button type="button" className="manage-button primary" disabled={!files[state.activeCourse]} onClick={() => dispatch({ type: 'PROCESS', name: files[state.activeCourse] })}>Simular extração<Icon>arrow_forward</Icon></button></div></>
          : plan.status === 'processing' ? <p role="status" className="tp-processing"><Icon>hourglass_top</Icon>Preparando avaliações de exemplo…</p>
          : <div className="tp-linked"><CourseStatus plan={plan} /><p>{plan.fileName}</p><button type="button" className="manage-button primary" onClick={() => dispatch({ type: 'STEP', step: 3 })}>Abrir avaliações<Icon>arrow_forward</Icon></button></div>}
      </div><aside className="tp-guidance"><h2>A turma certa, o plano certo.</h2><p>Confira disciplina, turma e período. Planos de semestres diferentes podem ter cronogramas diferentes.</p><div className="tp-quiet-note"><strong>O que já está pronto?</strong><p>Cálculo 1 vem com um plano de exemplo já vinculado. Você pode usá-lo para experimentar a etapa de agenda imediatamente.</p><button type="button" className="manage-button" onClick={() => dispatch({ type: 'STEP', step: 4 })}>Experimentar a agenda</button></div></aside></div>
    </section>}
    {state.step === 3 && plan?.candidates && <DemoReview key={state.activeCourse} state={state} dispatch={dispatch} />}
    {state.step === 4 && <DemoAgenda state={state} dispatch={dispatch} />}
    <section id="tp-catalog" className="tp-catalog"><header className="tp-section-heading"><div><h2>Explore as turmas da UnB</h2><p>Catálogo ilustrativo · a busca filtra apenas os cinco exemplos abaixo.</p></div><span className="tp-badge">Amostra de turmas</span></header>
      <div className="tp-filters"><label>Disciplina ou sigla<input value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar disciplina ou sigla" /></label><div><label htmlFor="tp-campus">Campus</label><select id="tp-campus" value={campus} onChange={e => setCampus(e.target.value)}><option value="">Todos os campi</option><option>Darcy Ribeiro</option><option>Faculdade do Gama</option></select></div><button type="button" className="manage-button" onClick={() => { setQuery(''); setCampus(''); }} disabled={!query && !campus}>Limpar filtros</button></div>
      <p className="tp-help" role="status">{filtered.length} turma(s) encontrada(s)</p>
      {!filtered.length && <p className="tp-empty">Nenhuma turma corresponde aos filtros. Tente outro nome ou limpe os filtros.</p>}
      {filtered.map(c => <article key={c.id} className="tp-catalog-row"><div><h3>{c.title}</h3><p>{courseLabel(c)}</p></div><CourseStatus plan={state.plans[c.id]} /><span>{state.enrollment && c.enrolled ? 'Na matrícula de exemplo' : state.enrollment ? 'Fora da sua matrícula' : 'Vincule a matrícula para identificar suas turmas'}</span></article>)}
    </section>
    {resetOpen && <Modal title="Reiniciar demonstração?" onClose={() => setResetOpen(false)}><p>As edições e a prévia local serão descartadas. Nenhum dado real será alterado.</p><div className="dialog-actions"><button type="button" className="manage-button" onClick={() => setResetOpen(false)}>Cancelar</button><button type="button" className="manage-button primary" onClick={() => {
      dispatch({ type: 'RESET' }); setEnrollmentFile(''); setFiles({}); setQuery(''); setCampus(''); setPickerVersion(v => v + 1); setResetOpen(false);
    }}>Reiniciar</button></div></Modal>}
  </div>;
}
