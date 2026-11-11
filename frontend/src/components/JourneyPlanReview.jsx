import { useState } from 'react';
import SyllabusReviewPanel from './SyllabusReviewPanel';

export default function JourneyPlanReview({ plan, onConfirmed }) {
  const [acknowledged, setAcknowledged] = useState(false);
  return <div>
    <h2>A IA sugere. Você confere.</h2>
    <label className="tp-choice">
      <input type="checkbox" checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} />
      Conferi as avaliações e a turma de destino.
    </label>
    <SyllabusReviewPanel selected plan={plan} confirmationAllowed={acknowledged} onConfirmed={onConfirmed} onEdited={() => setAcknowledged(false)} />
  </div>;
}
