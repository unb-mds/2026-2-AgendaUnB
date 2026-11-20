import { useCallback, useId, useState } from 'react';
import { useSemesterPlans } from '../contexts/SemesterPlansContext';
import { useSyllabusResource } from '../hooks/useSyllabusResource';
import { approvedTextSize, MAX_APPROVED_TEXT_BYTES } from '../lib/approvedText';
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

export default function SemesterTextReview({ plan, onClose }) {
  const workspace = useSemesterPlans();
  const { id } = plan;
  const load = useCallback(signal => syllabusApi.text(id, signal), [id]);
  const { data, loading, error, retry } = useSyllabusResource(id, load);
  const pages = workspace.texts[id]?.pages ?? data?.pages ?? [];
  const authorization = workspace.authorizations[id] || {};
  const active = isProcessing(plan);
  const reprocess = !plan.authorizationRequired;
  const [editing, setEditing] = useState(reprocess);
  const editorId = useId();
  const redactedCount = data?.redactedCount ?? 0;
  const size = approvedTextSize(pages);
  const blocked = workspace.confirming || loading || !!error || active || authorization.busy || authorization.uncertain ||
    !data?.providerAvailable || !pages.some(page => page.texto.trim()) || size > MAX_APPROVED_TEXT_BYTES;

  return <section className="semester-section semester-preview" aria-labelledby="semester-text-title">
    <header className="semester-section-heading">
      <div><h2 id="semester-text-title" tabIndex={-1}>{reprocess ? 'Texto do plano' : 'Confirmar extração'}</h2><p>{plan.disciplina || plan.fileName}</p></div>
      <button className="manage-button" type="button" onClick={onClose}>Voltar às avaliações</button>
    </header>
    {loading && <p role="status">Carregando texto…</p>}
    <Feedback error={error?.message} onRetry={retry} />
    <Feedback error={authorization.error} />
    {authorization.uncertain && <button className="manage-button" onClick={() => workspace.checkAuthorization(id)}>Consultar autorização</button>}
    {data && <form onSubmit={event => {
      event.preventDefault();
      if (!blocked) workspace.authorize(id, pages, reprocess);
    }}>
      <p id="semester-privacy">O {data.provider} recebe apenas o texto preparado para identificar as avaliações.</p>
      {redactedCount > 0 && <p role="status">
        {redactedCount === 1
          ? 'A preparação automática mascarou 1 ocorrência de dados pessoais.'
          : `A preparação automática mascarou ${redactedCount} ocorrências de dados pessoais.`}
      </p>}
      <button className="manage-button" type="button" aria-expanded={editing} aria-controls={editorId}
        onClick={() => setEditing(value => !value)}>{editing ? 'Ocultar texto' : 'Ver e editar texto'}</button>
      <div id={editorId} hidden={!editing}>
        {editing && <fieldset disabled={active || authorization.busy || authorization.uncertain}>
          <legend className="sr-only">Texto a enviar</legend>
          {pages.map((page, index) => <label className="semester-field" key={page.pagina ?? index}>
            {page.pagina == null ? 'Texto sem referência de página' : `Texto da página ${page.pagina}`}
            <textarea value={page.texto} rows={Math.max(4, Math.min(12, page.texto.split('\n').length + 1))}
              aria-describedby="semester-privacy" onChange={event => {
                const value = event.target.value;
                workspace.setText(id, { dirty: true, pages: pages.map((entry, i) => i === index ? { ...entry, texto: value } : entry) });
              }} />
          </label>)}
          <TextCapacity size={size} />
        </fieldset>}
      </div>
      {!editing && size > MAX_APPROVED_TEXT_BYTES && <p role="status">Abra o editor para reduzir o texto antes de confirmar.</p>}
      {!data.providerAvailable && <p role="status">A extração está indisponível no momento.</p>}
      {active ? <p role="status">Texto autorizado. A análise segue em segundo plano.</p> : <>
        <p id="semester-consent">Ao confirmar, você autoriza o envio deste texto e declara que ele está livre de informações pessoais, sensíveis ou confidenciais.</p>
        <button className="manage-button primary" aria-describedby="semester-consent semester-privacy" disabled={blocked}>
          {authorization.busy ? 'Autorizando…' : reprocess ? 'Autorizar nova análise' : 'Confirmar e extrair'}
        </button>
      </>}
    </form>}
  </section>;
}
