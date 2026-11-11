import { useCallback, useState } from 'react';
import { Feedback } from './ManagementUI';
import { catalogApi } from '../lib/classCatalogApi';
import { useSyllabusResource } from '../hooks/useSyllabusResource';

export default function SharedClassPlans({ offeringId }) {
  const [offset, setOffset] = useState(0);
  const load = useCallback(signal => catalogApi.shared(offeringId, offset, signal), [offeringId, offset]);
  const plans = useSyllabusResource(`${offeringId}:${offset}`, load);
  return <section className="plan-history" aria-labelledby="shared-class-plans"><h2 id="shared-class-plans">Planos compartilhados com a turma</h2>
    <Feedback error={plans.error?.message} onRetry={plans.retry} />
    {plans.loading && <p role="status">Consultando planos compartilhados…</p>}
    {!plans.loading && !plans.error && plans.data?.total === 0 && <p>Ainda não há plano compartilhado nesta oferta. Você pode enviar seu plano particular acima.</p>}
    {plans.data?.items.map(plan => <details key={plan.id} className="plan-text-review"><summary>Versão {plan.number} · {plan.author_role === 'professor' ? 'Autoria de perfil professor' : plan.author_role === 'admin' ? 'Contribuição de administrador' : 'Contribuição estudantil'}</summary>
      <p>{plan.institutional_provenance ? 'Origem institucional verificada.' : 'Sem comprovação de origem institucional.'}</p>
      {plan.candidates.length ? <ul>{plan.candidates.map(item => <li key={item.id}>{item.title} — {item.starts_at ? new Date(item.starts_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' }) : item.suggested_date || 'Data a confirmar'}{item.ambiguous ? ' · Requer conferência' : ''}</li>)}</ul> : <p>Esta versão não possui avaliações disponíveis.</p>}
    </details>)}
    {!!plans.data?.total && <nav className="plan-pagination" aria-label="Páginas de planos compartilhados"><button className="manage-button" disabled={plans.loading || !offset} onClick={() => setOffset(offset - 20)}>Anterior</button><button className="manage-button" disabled={plans.loading || offset + 20 >= plans.data.total} onClick={() => setOffset(offset + 20)}>Próxima</button></nav>}
  </section>;
}
