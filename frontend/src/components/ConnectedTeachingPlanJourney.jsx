import { useCallback, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Feedback, Icon } from './ManagementUI';
import RealClassCatalog from './RealClassCatalog';
import EventCalendar from './EventCalendar';
import { eventsApi, toUiEvent } from '../lib/api';
import { catalogApi } from '../lib/classCatalogApi';
import { useSyllabusResource } from '../hooks/useSyllabusResource';

const steps = ['Selecionar turmas', 'Conectar planos', 'Revisar datas', 'Enviar à agenda'];
const loadEvents = () => eventsApi.listPersonal();

function JourneyAgenda() {
  const events = useSyllabusResource('journey-personal-events', loadEvents);
  return <div className="tp-panel"><h2>Leve as datas para o seu calendário.</h2><p>As avaliações confirmadas na revisão aparecem na sua agenda particular.</p>
    <Feedback error={events.error?.message} onRetry={events.retry} />
    <EventCalendar events={(events.data || []).map(event => toUiEvent(event, true))} loading={events.loading} error={!!events.error} />
    <Link className="manage-button primary" to="/eventos?aba=meus">Abrir Meus Eventos<Icon>arrow_forward</Icon></Link></div>;
}

export default function ConnectedTeachingPlanJourney({ userId, renderWorkspace }) {
  const [params, setParams] = useSearchParams();
  const offeringId = params.get('oferta');
  const initial = params.has('plano') ? 3 : offeringId || params.get('modo') === 'envios' ? 2 : 1;
  const requestedStep = Number(params.get("etapa"));
  const step = [1, 2, 3, 4].includes(requestedStep) ? requestedStep : initial;
  const heading = useRef(null);
  const previous = useRef(step);
  const loadOffer = useCallback(async signal => {
    if (!offeringId) return null;
    const [selected, followed] = await Promise.all([catalogApi.get(offeringId, signal), catalogApi.followed(signal)]);
    if (selected?.id !== offeringId || typeof selected.available !== 'boolean' || !Array.isArray(followed?.items)) {
      throw new Error('Resposta da turma inválida. Tente consultar novamente.');
    }
    return { ...selected, following: followed.items.some(item => item?.id === offeringId) };
  }, [offeringId]);
  const offer = useSyllabusResource(`${userId}:${offeringId}`, loadOffer);
  useEffect(() => { if (previous.current !== step) { heading.current?.focus(); previous.current = step; } }, [step]);
  const changeStep = next => setParams(previous => {
    if (next === 1) return {};
    const updated = new URLSearchParams(previous);
    updated.set('etapa', String(next));
    return updated;
  });
  return <div className="tp-journey">
    <div className="tp-demo-notice"><strong>Seus planos de ensino</strong><p>Escolha sua turma, conecte o plano, confira as datas e envie à sua agenda. Com login, seus vínculos e planos ficam salvos na sua conta.</p></div>
    <nav className="tp-steps" aria-label="Etapas do plano de ensino">{steps.map((label, index) => <button key={label} type="button" aria-current={step === index + 1 ? 'step' : undefined}
      disabled={(index === 1 && !offeringId && !params.has('plano')) || (index === 2 && !params.has('plano'))} onClick={() => changeStep(index + 1)}><span>{index + 1}</span>{label}</button>)}</nav>
    <h2 className="sr-only" ref={heading} tabIndex={-1}>Etapa {step}: {steps[step - 1]}</h2>
    {step === 1 && <RealClassCatalog userId={userId} onOpen={selected => { setParams({ oferta: selected.id, etapa: '2' }); }} />}
    {(step === 2 || step === 3) && (offer.loading ? <p role="status">Carregando oferta…</p> : offer.error ? <><Feedback error="Não foi possível verificar a oferta e suas turmas seguidas." onRetry={offer.retry} /><Link className="management-text-button" to="/plano-de-ensino">Voltar ao catálogo de turmas</Link></> :
      <div className="tp-panel">{renderWorkspace(offer.data, step, changeStep)}</div>)}
    {step === 4 && <JourneyAgenda />}
  </div>;
}
