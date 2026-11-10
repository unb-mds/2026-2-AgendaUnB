import SyllabusReviewEditor from './SyllabusReviewEditor';

const states = { pendente: 'Pendente de confirmação', confirmado: 'Confirmado', descartado: 'Descartado' };
const fields = { title: 'título', titulo: 'título', type: 'tipo', tipo: 'tipo', date: 'data', data: 'data', time: 'horário', hora: 'horário', timezone: 'fuso horário', fuso: 'fuso horário' };

// Uses candidate details from the existing private-plan API contract.
// Do not turn extractedEventsCount into synthetic candidates or assume a future payload.
export default function SyllabusReviewPanel({ selected = false, plan, loading = false, error }) {
  const candidates = selected && !error && !loading && plan?.status === 'concluido' && !plan.authorizationRequired ? plan.candidates : null;
  let message = 'Abra um plano em “Seus planos enviados” para consultar a disponibilidade das avaliações. Se ainda não enviou um plano, comece pelo formulário acima.';
  if (selected) {
    if (error) message = 'Não foi possível verificar as avaliações deste plano. Use “Tentar novamente” no acompanhamento para atualizar a consulta.';
    else if (loading) message = 'Consultando a disponibilidade das avaliações…';
    else if (plan?.status === 'pendente') message = 'Este plano aguarda processamento. Ainda não há avaliações disponíveis para revisão.';
    else if (plan?.status === 'processando') message = 'A análise está em andamento. Aguarde o resultado antes de revisar as avaliações.';
    else if (plan?.status === 'falha') message = 'A análise deste plano falhou. Confira as orientações no acompanhamento ou cadastre seus prazos em Meus Eventos.';
    else if (plan?.status === 'concluido' && plan.extractedEventsCount === 0) message = 'A análise terminou sem avaliações. Você pode cadastrar os prazos manualmente em Meus Eventos.';
    else if (plan?.status === 'concluido') message = 'A análise terminou, mas os detalhes das avaliações ainda não estão disponíveis para revisão. Nenhum evento foi incluído na sua agenda.';
    else message = 'Não foi possível identificar o estado da análise. Consulte novamente pelo acompanhamento.';
  }
  return <div className="plan-review-panel">
    {candidates?.length ? <section className="syllabus-review" aria-labelledby="candidate-review-heading">
      <h2 id="candidate-review-heading">Revisar avaliações</h2>
      <p>Confira as avaliações identificadas e os trechos de origem. A seleção, edição e confirmação ainda não estão disponíveis nesta etapa.</p>
      <ul className="syllabus-candidates">{candidates.map(candidate => <li key={candidate.id} className="syllabus-candidate">
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
      </li>)}</ul>
    </section> : <SyllabusReviewEditor value={[]} disabled emptyMessage={candidates?.length === 0 ? 'A análise terminou sem avaliações. Você pode cadastrar os prazos manualmente em Meus Eventos.' : message} />}
    <details className="plan-file-help">
      <summary>O que poderei revisar?</summary>
      <p>Você poderá corrigir título e tipo, informar data, horário e fuso e escolher quais avaliações incluir. Descartar um item não deverá criar um compromisso.</p>
      <p>A edição das avaliações e a inclusão na agenda ainda não estão disponíveis nesta página.</p>
    </details>
  </div>;
}
