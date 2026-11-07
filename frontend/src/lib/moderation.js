import { supabase } from './supabase';

function check(error) {
  if (!error) return;
  const messages = {
    '42501': 'Você não tem permissão para esta ação. Atualize a página para conferir seu perfil.',
    '23514': 'O perfil de professor exige um e-mail institucional @unb.br.',
    'PGRST301': 'Sua sessão expirou. Entre novamente para continuar.',
  };
  throw new Error(messages[error.code] || (['P0002', '22023'].includes(error.code)
    ? error.message : 'Não foi possível concluir a solicitação. Verifique sua conexão e tente novamente.'));
}

async function rpc(name, params) {
  const { data, error } = await supabase.rpc(name, params);
  check(error);
  return data;
}

export const moderationApi = {
  suggestions: (status, search, page) => rpc('listar_sugestoes', {
    p_status: status, p_busca: search, p_offset: page * 20,
  }),
  decide: (id, status, reason) => rpc('moderar_sugestao', {
    p_evento_id: id, p_status: status, p_justificativa: reason || null,
  }),
  users: (search, role, confirmed, page) => rpc('admin_buscar_usuarios', {
    p_busca: search, p_papel: role, p_confirmado: confirmed, p_offset: page * 20,
  }),
  changeRole: (user, role) => rpc('admin_definir_papel', {
    p_usuario_id: user.id, p_novo_papel: role, p_papel_atual: user.papel,
  }),
  notifications: async (userId, page = 0) => {
    const [{ data, error, count }, unread] = await Promise.all([
      supabase.from('notificacoes').select('*', { count: 'exact' }).eq('usuario_id', userId)
        .order('criado_em', { ascending: false }).order('id').range(page * 20, page * 20 + 19),
      supabase.from('notificacoes').select('id', { count: 'exact', head: true }).eq('usuario_id', userId).is('lida_em', null),
    ]);
    check(error); check(unread.error);
    return { items: data, total: count, unread: unread.count };
  },
  markRead: async (userId, ids) => {
    const { error } = await supabase.from('notificacoes').update({ lida_em: new Date().toISOString() })
      .eq('usuario_id', userId).in('id', ids).is('lida_em', null);
    check(error);
  },
};

export function formatDate(value) {
  if (!value) return 'Ainda não acessou';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Data indisponível' : new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo',
  }).format(date);
}

export function safeEventUrl(value) {
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; }
  catch { return null; }
}

export const ROLE_LABELS = { student: 'Estudante', professor: 'Professor', admin: 'Administrador' };
