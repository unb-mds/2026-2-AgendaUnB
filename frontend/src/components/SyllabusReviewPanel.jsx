import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { syllabusError } from '../lib/syllabus';
import { syllabusApi } from '../lib/syllabusApi';
import { buildReviewConfirmation, createCandidateReviewDraft } from '../lib/syllabusReview';
import { Feedback, Icon } from './ManagementUI';
import SyllabusReviewEditor from './SyllabusReviewEditor';

const states = { pendente: 'Pendente de confirmação', confirmado: 'Confirmado', descartado: 'Descartado' };
const fields = { title: 'título', titulo: 'título', type: 'tipo', tipo: 'tipo', date: 'data', data: 'data', time: 'horário', hora: 'horário', timezone: 'fuso horário', fuso: 'fuso horário' };

// Uses candidate details from the existing private-plan API contract.
// Do not turn extractedEventsCount into synthetic candidates or assume a future payload.
export default function SyllabusReviewPanel({ selected = false, plan, loading = false, error, onConfirmed, onEdited, confirmationAllowed = true }) {
  const candidates = selected && !error && !loading && plan?.status === 'concluido' && !plan.authorizationRequired ? plan.candidates : null;
  let message = 'Abra um plano em “Seus planos enviados” para consultar a disponibilidade das avaliações. Se ainda não enviou um plano, comece pelo formulário acima.';
  if (selected) {
    if (error) message = 'Não foi possível verificar as avaliações deste plano. Use “Tentar novamente” no acompanhamento para atualizar a consulta.';
    else if (loading) message = 'Consultando a disponibilidade das avaliações…';
    else if (plan?.status === 'pendente') message = 'Este plano aguarda processamento. Ainda não há avaliações disponíveis para revisão.';
    else if (plan?.status === 'processando') message = 'A análise está em andamento. Aguarde o resultado antes de revisar as avaliações.';
    else if (plan?.status === 'falha') message = 'A análise deste plano falhou. Confira as orientações no acompanhamento ou cadastre seus prazos em Meus Eventos.';
    else if (plan?.status === 'concluido' && plan.extractedEventsCount === 0) message = 'A análise terminou sem avaliações. Você pode cadastrar os prazos manualmente em Meus Eventos.';
    else if (plan?.status === 'concluido') message = 'A análise terminou, mas os detalhes das avaliações ainda não estão disponíveis para revisão.';
    else message = 'Não foi possível identificar o estado da análise. Consulte novamente pelo acompanhamento.';
  }
  return <div className="plan-review-panel">
    {candidates?.length ? <CandidateReview key={JSON.stringify([plan.id, candidates])} planId={plan.id} initialCandidates={candidates} onConfirmed={onConfirmed} onEdited={onEdited} confirmationAllowed={confirmationAllowed} /> : <SyllabusReviewEditor value={[]} disabled emptyMessage={candidates?.length === 0 ? 'A análise terminou sem avaliações. Você pode cadastrar os prazos manualmente em Meus Eventos.' : message} />}
    <details className="plan-file-help">
      <summary>O que poderei revisar?</summary>
      <p>Você pode corrigir título, tipo, data, horário e fuso. Somente as avaliações selecionadas entram na agenda quando você confirma a importação.</p>
    </details>
  </div>;
}

function CandidateReview({ planId, initialCandidates, onConfirmed, onEdited, confirmationAllowed }) {
  const [candidates, setCandidates] = useState(initialCandidates);
  const [draft, setDraft] = useState(() => createCandidateReviewDraft(initialCandidates));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [unverifiedIds, setUnverifiedIds] = useState(null);
  const requestRef = useRef(null);
  useEffect(() => () => requestRef.current?.abort(), []);

  async function confirm() {
    if (requestRef.current || unverifiedIds || !confirmationAllowed) return;
    const controller = new AbortController();
    requestRef.current = controller;
    setBusy(true);
    setError('');
    setSuccess('');
    let batch;
    try {
      batch = buildReviewConfirmation(draft, candidates);
      const events = await syllabusApi.confirm(planId, batch, controller.signal);
      if (controller.signal.aborted) return;
      const confirmed = new Set(batch.map(item => item.candidateId));
      // The API also accepts already-confirmed candidates whose events were removed.
      setCandidates(current => current.map(item => confirmed.has(item.id) ? { ...item, status: 'confirmado' } : item));
      setDraft(current => current.map(item => confirmed.has(item.id)
        ? { ...item, decision: 'pending', status: 'confirmado', editable: false } : item));
      if (events.length === batch.length) {
        setSuccess(events.length === 1 ? '1 avaliação confirmada na agenda.' : `${events.length} avaliações confirmadas na agenda.`);
      } else {
        setSuccess(`Confirmação concluída. ${events.length} de ${batch.length} eventos disponíveis na agenda. Eventos removidos não são recriados.`);
      }
      onConfirmed?.();
    } catch (failure) {
      if (controller.signal.aborted) return;
      if (batch && (!failure.status || failure.status >= 500 || [409, 422].includes(failure.status))) {
        setUnverifiedIds(new Set(batch.map(item => item.candidateId)));
        setError(failure.status === 409 || failure.status === 422
          ? `${syllabusError(failure)} Atualize as avaliações antes de tentar novamente.`
          : 'Não foi possível verificar o resultado. Atualize as avaliações antes de tentar novamente.');
      } else {
        setError(syllabusError(failure));
      }
    } finally {
      requestRef.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  async function refresh() {
    if (requestRef.current || !unverifiedIds) return;
    const controller = new AbortController();
    requestRef.current = controller;
    setBusy(true);
    setError('');
    try {
      const latest = await syllabusApi.get(planId, controller.signal);
      if (controller.signal.aborted) return;
      if (latest.id !== planId || latest.status !== 'concluido' || latest.authorizationRequired || !latest.candidates) {
        setError('As avaliações não estão disponíveis para confirmação. Atualize novamente ou reabra o acompanhamento do plano.');
        return;
      }
      const previous = new Map(draft.map(item => [item.id, item]));
      const reconciled = createCandidateReviewDraft(latest.candidates).map(item => {
        const prior = previous.get(item.id);
        return item.editable && prior?.editable && item.versionId === prior.versionId ? prior : item;
      });
      setCandidates(latest.candidates);
      setDraft(reconciled);
      setUnverifiedIds(null);
      const confirmed = latest.candidates.filter(item => unverifiedIds.has(item.id) && item.status === 'confirmado').length;
      setSuccess(`Avaliações atualizadas. ${confirmed} de ${unverifiedIds.size} itens do último envio constam como confirmados. Revise os itens que ainda estiverem pendentes.`);
    } catch (failure) {
      if (!controller.signal.aborted) setError(syllabusError(failure));
    } finally {
      requestRef.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return <>
    <SyllabusReviewEditor value={draft} onChange={items => { setDraft(items); onEdited?.(); }} onConfirm={confirm}
      confirmationAllowed={confirmationAllowed} busy={busy} disabled={busy || Boolean(unverifiedIds)} renderCandidate={(_, index) => {
    const candidate = candidates[index];
    return <div className="syllabus-candidate">
        <h3>{candidate.title}</h3>
        <p>Estado: <strong>{states[candidate.status] || 'Estado indisponível'}</strong></p>
        <dl>
          <div><dt>Tipo</dt><dd>{candidate.type || 'Não informado'}</dd></div>
          <div><dt>Data sugerida</dt><dd>{candidate.suggestedDate || 'Não informada'}</dd></div>
          <div><dt>Horário sugerido</dt><dd>{candidate.suggestedTime || 'Não informado'}</dd></div>
          {candidate.startsAt && <div><dt>Data e horário registrados</dt><dd>{candidate.startsAt}</dd></div>}
        </dl>
        {(candidate.ambiguous || candidate.ambiguousFields.length > 0) && <p className="syllabus-review-error">Requer conferência{candidate.ambiguousFields.length ? `: ${candidate.ambiguousFields.map(field => fields[field] || field).join(', ')}` : ': informações incertas no documento'}.</p>}
        {(!candidate.suggestedDate || !candidate.suggestedTime) && !candidate.startsAt && <p>Data ou horário incompletos. Será necessário informá-los antes da confirmação, com fuso horário.</p>}
        <p><strong>Origem:</strong> {candidate.sourcePage === null ? 'Sem referência de página' : `Página ${candidate.sourcePage}`}</p>
        {candidate.sourceExcerpt ? <blockquote>{candidate.sourceExcerpt}</blockquote> : <p>Trecho de origem não informado.</p>}
    </div>;
    }} />
    <Feedback error={error} success={success} />
    {!busy && candidates.some(candidate => candidate.status === 'confirmado') &&
      <Link className="manage-button" to="/eventos?aba=meus">
        <Icon>event_available</Icon>Abrir Meus Eventos
      </Link>}
    {unverifiedIds && <button className="manage-button" type="button" disabled={busy} onClick={refresh}>Atualizar avaliações</button>}
  </>;
}
