export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const SYLLABUS_PAGE_SIZE = 10;
export const isProcessing = plan => ['pendente', 'processando'].includes(plan?.status);

export const PLAN_STATES = {
  pendente: { label: 'Pendente', icon: 'schedule', title: 'Seu plano está na fila', description: 'O arquivo foi recebido e aguarda processamento. Você pode sair desta página e acompanhar depois pelo histórico.' },
  processando: { label: 'Processando', icon: 'autorenew', title: 'Analisando seu plano', description: 'Estamos procurando avaliações no documento. Esta página será atualizada automaticamente.' },
  concluido: { label: 'Concluído', icon: 'check_circle', title: 'Análise concluída', description: 'O processamento terminou. Nenhum compromisso foi adicionado à sua agenda automaticamente.' },
  falha: { label: 'Falha', icon: 'error', title: 'Não foi possível analisar o plano', description: 'Confira se o PDF permite selecionar o texto, não tem senha e possui até 10 páginas. Você pode enviar outro arquivo ou cadastrar seus prazos manualmente.' },
};

export function validatePdf(file) {
  if (!file) return 'Selecione um arquivo PDF para continuar.';
  if (!/\.pdf$/i.test(file.name) || (file.type && file.type !== 'application/pdf')) return 'Escolha um arquivo no formato PDF (.pdf).';
  if (!file.size) return 'O arquivo está vazio. Escolha outro PDF.';
  if (file.size > MAX_PDF_BYTES) return 'O PDF ultrapassa 10 MB. Reduza o tamanho ou escolha outro arquivo.';
  return '';
}

export function normalizePlan(plan) {
  if (!plan || typeof plan.id !== 'string' || !plan.id) throw new Error('Resposta do plano inválida. Tente consultar novamente.');
  return {
    id: plan.id,
    status: plan.status,
    fileName: plan.fileName || 'Plano de ensino.pdf',
    disciplina: plan.disciplina || '',
    semestre: plan.semestre ?? null,
    ano: plan.ano ?? null,
    createdAt: plan.createdAt ?? null,
    fileSize: plan.fileSize ?? null,
    // Missing counts are not an empty extraction. Only an explicit zero is.
    extractedEventsCount: Number.isInteger(plan.extractedEventsCount) && plan.extractedEventsCount >= 0 ? plan.extractedEventsCount : null,
    errorMessage: typeof plan.errorMessage === 'string' ? plan.errorMessage : null,
  };
}

export function normalizePlanList(result) {
  if (!Array.isArray(result?.items) || !Number.isInteger(result.total) || result.total < 0) {
    throw new Error('O histórico retornou uma resposta inválida. Tente novamente.');
  }
  return { items: result.items.map(normalizePlan), total: result.total };
}

export function syllabusError(error, context = 'consulta') {
  if (error.status === 401) return 'Sua sessão expirou. Entre novamente para acessar seus planos.';
  if (error.status === 403) return 'Sua conta não tem permissão para realizar esta ação.';
  if ([404, 405, 501].includes(error.status) && context === 'historico') return 'O histórico ainda não está disponível. Tente novamente mais tarde. Você ainda pode acompanhar um envio aberto.';
  if (error.status === 404) return 'Plano não encontrado ou indisponível para sua conta. Abra outro plano pelo histórico.';
  if (error.status === 429) return 'Muitas solicitações em pouco tempo. Aguarde um momento antes de tentar novamente.';
  if (error.name === 'TimeoutError' || error instanceof TypeError || error.status >= 500) {
    return context === 'envio'
      ? 'Não foi possível confirmar o envio. Confira o histórico antes de tentar de novo para evitar um envio repetido.'
      : 'Não foi possível atualizar os dados. Verifique sua conexão e tente novamente.';
  }
  return error.message || 'Não foi possível concluir a solicitação. Tente novamente.';
}

export function formatPlanDate(value) {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(date) : 'Data não informada';
}

export function formatFileSize(bytes) {
  if (!Number.isFinite(bytes)) return '';
  return bytes < 1024 * 1024
    ? `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(bytes / 1024)} KB`
    : `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(bytes / (1024 * 1024))} MB`;
}
