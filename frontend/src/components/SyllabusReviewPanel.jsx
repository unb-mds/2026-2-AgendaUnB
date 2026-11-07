import SyllabusReviewEditor from './SyllabusReviewEditor';

// Uses only the tracking contract currently implemented by the API.
// Do not turn extractedEventsCount into synthetic candidates or assume a future payload.
export default function SyllabusReviewPanel({ selected = false, plan, loading = false, error }) {
  let message = 'Abra um plano em “Seus planos enviados” para consultar a disponibilidade das avaliações. Se ainda não enviou um plano, comece pelo formulário acima.';
  if (selected) {
    if (error) message = 'Não foi possível verificar as avaliações deste plano. Use “Tentar novamente” no acompanhamento para atualizar a consulta.';
    else if (loading && !plan) message = 'Consultando a disponibilidade das avaliações…';
    else if (plan?.status === 'pendente') message = 'Este plano aguarda processamento. Ainda não há avaliações disponíveis para revisão.';
    else if (plan?.status === 'processando') message = 'A análise está em andamento. Aguarde o resultado antes de revisar as avaliações.';
    else if (plan?.status === 'falha') message = 'A análise deste plano falhou. Confira as orientações no acompanhamento ou cadastre seus prazos em Meus Eventos.';
    else if (plan?.status === 'concluido' && plan.extractedEventsCount === 0) message = 'A análise terminou sem avaliações. Você pode cadastrar os prazos manualmente em Meus Eventos.';
    else if (plan?.status === 'concluido') message = 'A análise terminou, mas os detalhes das avaliações ainda não estão disponíveis para revisão. Nenhum evento foi incluído na sua agenda.';
    else message = 'Não foi possível identificar o estado da análise. Consulte novamente pelo acompanhamento.';
  }
  return <div className="plan-review-panel">
    <SyllabusReviewEditor value={[]} disabled emptyMessage={message} />
    <details className="plan-file-help">
      <summary>O que poderei revisar?</summary>
      <p>Você poderá corrigir título e tipo, informar data, horário e fuso e escolher quais avaliações incluir. Descartar um item não deverá criar um compromisso.</p>
      <p>A edição das avaliações e a inclusão na agenda ainda não estão disponíveis nesta página.</p>
    </details>
  </div>;
}
