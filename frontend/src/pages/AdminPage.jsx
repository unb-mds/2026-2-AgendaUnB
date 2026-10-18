import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Feedback, Icon, ManagementSelect, ManagementShell, Modal, Pagination, useDebounced } from '../components/ManagementUI';
import { formatDate, moderationApi, ROLE_LABELS } from '../lib/moderation';

export default function AdminPage() {
  const { user } = useAuth();
  const [search, setSearch] = useState('');
  const query = useDebounced(search);
  const [role, setRole] = useState('');
  const [confirmed, setConfirmed] = useState('');
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState({ items: [], total: 0, all: 0, unconfirmed: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [change, setChange] = useState(null);
  const [changeError, setChangeError] = useState('');
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    moderationApi.users(query, role, confirmed, page).then(data => {
      if (!active) return;
      if (page > 0 && !data.items.length) setPage(page - 1);
      else setResult(data);
    }).catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [query, role, confirmed, page, revision]);
  const clear = () => { setSearch(''); setRole(''); setConfirmed(''); setPage(0); };
  const submit = async e => {
    e.preventDefault();
    if (submitting.current) return;
    submitting.current = true; setBusy(true); setChangeError('');
    try {
      await moderationApi.changeRole(change.user, change.role);
      setSuccess(`Perfil de ${change.user.nome_completo} alterado para ${ROLE_LABELS[change.role]}.`);
      setChange(null); setRevision(v => v + 1);
    } catch (err) { setChangeError(err.message); }
    finally { submitting.current = false; setBusy(false); }
  };
  return <ManagementShell title="Admin" description="Gerencie as contas e os acessos da comunidade Agenda UnB.">
    <div className="management-toolbar"><p className="management-summary"><strong>{result.all}</strong> contas cadastradas
      <span> · {result.unconfirmed} com e-mail não confirmado</span></p>
      <button className="manage-button" disabled={loading} onClick={() => setRevision(v => v + 1)}><Icon>refresh</Icon>Atualizar</button>
    </div>
    <div className="admin-filters">
      <label className="management-search"><Icon>search</Icon><span className="sr-only">Buscar usuários por nome ou e-mail</span>
        <input value={search} maxLength={120} onChange={e => { setSearch(e.target.value); setPage(0); }} placeholder="Buscar por nome ou e-mail" /></label>
      <div className="management-filter"><span>Perfil</span><ManagementSelect label="Filtrar por perfil" value={role}
        options={[{ value: '', label: 'Todos os perfis' }, ...Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))]}
        onChange={next => { setRole(next); setPage(0); }} /></div>
      <div className="management-filter"><span>E-mail</span><ManagementSelect label="Filtrar por e-mail" value={confirmed}
        options={[{ value: '', label: 'Todos os e-mails' }, { value: 'sim', label: 'Confirmado' }, { value: 'nao', label: 'Não confirmado' }]}
        onChange={next => { setConfirmed(next); setPage(0); }} /></div>
      {(search || role || confirmed) && <button className="manage-button" onClick={clear}>Limpar filtros</button>}
    </div>
    <Feedback error={error} success={success} onRetry={() => setRevision(v => v + 1)} />
    {loading ? <div className="management-state" role="status">Carregando usuários…</div>
      : !error && !result.items.length ? <div className="management-state"><Icon>person_search</Icon><h2>Nenhum usuário encontrado</h2><p>Experimente outro nome, e-mail ou remova os filtros.</p><button className="manage-button" onClick={clear}>Limpar filtros</button></div>
      : !error && <div className="admin-table-container"><table className="admin-table">
        <caption className="sr-only">Usuários cadastrados e seus privilégios</caption>
        <thead><tr><th scope="col">Usuário</th><th scope="col">E-mail</th><th scope="col">Último acesso</th><th scope="col">Perfil de acesso</th></tr></thead>
        <tbody>{result.items.map(account => <tr key={account.id}>
          <td><div className="admin-identity"><span className="admin-initial" aria-hidden="true">{Array.from(account.nome_completo || '?')[0].toUpperCase()}</span>
            <div><strong>{account.nome_completo}</strong>{account.id === user.id && <span className="management-tag">Você</span>}
              <small>Cadastro em {formatDate(account.criado_em)}</small></div></div></td>
          <td><span className="admin-email">{account.email}</span><small className="admin-confirmation"><Icon>{account.email_confirmado ? 'verified' : 'schedule'}</Icon>{account.email_confirmado ? 'Confirmado' : 'Não confirmado'}</small></td>
          <td data-label="Último acesso">{formatDate(account.ultimo_login)}</td>
          <td><ManagementSelect label={`Perfil de ${account.nome_completo}`} value={account.papel} disabled={account.id === user.id}
            options={Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))}
            onChange={next => { setChange({ user: account, role: next }); setChangeError(''); setSuccess(''); }} />
            <small>{account.id === user.id ? 'Seu acesso de admin está protegido.' : 'Alterações exigem confirmação.'}</small>
          </td>
        </tr>)}</tbody>
      </table></div>}
    {!error && <Pagination page={page} total={result.total} onPage={setPage} busy={loading} />}
    <aside className="management-help"><Icon>info</Icon><p><strong>Sobre os acessos.</strong> Professores podem publicar e moderar eventos. Administradores também gerenciam contas. Um e-mail não confirmado pode impedir o login; a pessoa deve conferir sua caixa de entrada e spam.</p></aside>
    {change && <Modal title="Alterar perfil de acesso" busy={busy} onClose={() => setChange(null)}><form onSubmit={submit}>
      <p className="dialog-event-title">{change.user.nome_completo}</p><p className="management-muted">{change.user.email}</p>
      <p className="role-change-summary">{ROLE_LABELS[change.user.papel]} <Icon>arrow_forward</Icon> <strong>{ROLE_LABELS[change.role]}</strong></p>
      <p>{change.role === 'admin' ? 'Esta pessoa poderá gerenciar contas e alterar os privilégios de outros usuários.' : change.role === 'professor' ? 'Esta pessoa poderá publicar eventos e aprovar ou recusar sugestões.' : 'Esta pessoa perderá o acesso à moderação e ao gerenciamento de contas. Poderá continuar enviando sugestões como estudante.'}</p>
      <Feedback error={changeError} /><footer className="dialog-actions"><button type="button" className="manage-button" disabled={busy} onClick={() => setChange(null)}>Cancelar</button>
        <button className="manage-button primary" disabled={busy}>{busy ? 'Salvando…' : 'Confirmar alteração'}</button></footer>
    </form></Modal>}
  </ManagementShell>;
}
