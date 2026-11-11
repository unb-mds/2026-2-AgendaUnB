import { useRef, useState } from 'react';
import SyllabusReviewEditor from './SyllabusReviewEditor';
import { Feedback } from './ManagementUI';
import { syllabusApi } from '../lib/syllabusApi';
import { validateReviewItem } from '../lib/syllabusReview';

export default function JourneyPlanReview({ plan, onConfirmed }) {
  const [draft, setDraft] = useState(() => (plan.candidates || []).filter(c => c.status !== 'descartado' && c.status !== 'confirmado').map(c => ({
    id: c.id, title: c.title || '', type: c.type || '', date: c.suggestedDate || c.startsAt?.slice(0, 10) || '',
    time: c.suggestedTime?.slice(0, 5) || c.startsAt?.slice(11, 16) || '', utcOffset: '', decision: 'pending',
  })));
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [error, setError] = useState('');
  const selected = draft.filter(c => c.decision === 'selected');
  async function confirm() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {
      await syllabusApi.confirm(plan.id, selected.map(c => ({ candidateId: c.id, title: c.title.trim(), startsAt: `${c.date}T${c.time}:00${c.utcOffset}` })));
      onConfirmed();
    } catch (failure) { setError(failure.message); }
    finally { pending.current = false; setBusy(false); }
  }
  return <div><h2>A IA sugere. Você confere.</h2>
    <SyllabusReviewEditor value={draft} disabled={busy} onChange={items => { setDraft(items); setAcknowledged(false); }} />
    <label className="tp-choice"><input type="checkbox" checked={acknowledged} onChange={e => setAcknowledged(e.target.checked)} disabled={busy} />Conferi as avaliações e a turma de destino.</label>
    <Feedback error={error} />
    <button className="manage-button primary" disabled={busy || !acknowledged || !selected.length || selected.some(c => Object.keys(validateReviewItem(c)).length || c.title.trim().length < 3)} onClick={confirm}>{busy ? 'Incluindo avaliações…' : 'Confirmar e enviar à agenda'}</button>
  </div>;
}
