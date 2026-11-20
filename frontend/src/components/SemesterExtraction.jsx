import { useCallback } from 'react';
import { useSemesterPlans } from '../contexts/SemesterPlansContext';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import { MAX_APPROVED_TEXT_BYTES } from '../lib/approvedText';
import { syllabusApi } from '../lib/syllabusApi';
import { isProcessing } from '../lib/syllabus';
import { Feedback } from './ManagementUI';

export function TextCapacity({ size }) {
  const percent = Math.ceil(size / MAX_APPROVED_TEXT_BYTES * 100);
  const exceeded = size > MAX_APPROVED_TEXT_BYTES;
  return <div className="semester-capacity" data-exceeded={exceeded}>
    <div className="semester-capacity-heading">
      <span>Capacidade do texto</span>
      <strong>{percent}%</strong>
    </div>
    <progress aria-label="Capacidade do texto usada" aria-valuetext={exceeded ? `${percent}% — limite excedido` : undefined}
      max={100} value={Math.min(percent, 100)} />
    {exceeded && <span className="semester-capacity-message" role="status">Limite excedido. Reduza o texto.</span>}
  </div>;
}

export default function SemesterExtraction({ plan, onClose }) {
  const workspace = useSemesterPlans();
  const { id } = plan;
  const load = useCallback(signal => syllabusApi.text(id, signal), [id]);
  const { data, loading, error, retry } = useSyllabusResource(id, load);
  const authorization = workspace.authorizations[id] || {};
  const active = isProcessing(plan);
  const reprocess = !plan.authorizationRequired;
  const redactedCount = data?.redactedCount ?? 0;
  const blocked = workspace.confirming || loading || !!error || active || authorization.busy || authorization.uncertain ||
    !data?.providerAvailable;

  return <section className="semester-section semester-preview" aria-labelledby="semester-extraction-title">
    <header className="semester-section-heading">
      <div><h2 id="semester-extraction-title" tabIndex={-1}>{reprocess ? 'Nova análise' : 'Extrair avaliações'}</h2><p>{plan.disciplina || plan.fileName}</p></div>
      <button className="manage-button" type="button" onClick={onClose}>Voltar às avaliações</button>
    </header>
    {loading && <p role="status">Verificando disponibilidade da extração…</p>}
    <Feedback error={error?.message} onRetry={retry} />
    <Feedback error={authorization.error} />
    {authorization.uncertain && <button className="manage-button" onClick={() => workspace.checkAuthorization(id)}>Consultar andamento</button>}
    {data && <>
      <p id="semester-privacy">Ao iniciar, você autoriza o envio do texto sanitizado ao {data.provider} para identificar as avaliações.</p>
      {redactedCount > 0 && <p role="status">
        {redactedCount === 1
          ? 'A preparação automática mascarou 1 ocorrência de dados pessoais.'
          : `A preparação automática mascarou ${redactedCount} ocorrências de dados pessoais.`}
      </p>}
      {!data.providerAvailable && <p role="status">A extração está indisponível no momento.</p>}
      {active ? <p role="status">A análise segue em segundo plano.</p> :
        <button className="manage-button primary" type="button" aria-describedby="semester-privacy" disabled={blocked}
          onClick={() => workspace.authorize(id, data.pages, reprocess)}>
          {authorization.busy ? 'Iniciando…' : reprocess ? 'Iniciar nova análise' : 'Iniciar extração'}
        </button>}
    </>}
  </section>;
}
