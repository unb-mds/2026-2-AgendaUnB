import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Feedback, Icon, ManagementSelect, ManagementShell, Modal, Pagination, useDebounced } from '../components/ManagementUI';
import { formatDate, moderationApi, ROLE_LABELS } from '../lib/moderation';

export default function AdminPage() {
  const { user } = useAuth();
  const [section, setSection] = useState('users');

  // --- Estados de Usuários e Papéis ---
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

  // --- Estados de Categorias (exclusivo Admin) ---
  const [categories, setCategories] = useState([]);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [catError, setCatError] = useState('');
  const [catSuccess, setCatSuccess] = useState('');
  const [catRevision, setCatRevision] = useState(0);
  const [newCatName, setNewCatName] = useState('');
  const [newCatColor, setNewCatColor] = useState('#008bff');
  const [creatingCat, setCreatingCat] = useState(false);
  const [catToDelete, setCatToDelete] = useState(null);
  const [deletingCat, setDeletingCat] = useState(false);

  useEffect(() => {
    if (section !== 'users') return undefined;
    let active = true;
    setLoading(true);
    setError('');
    moderationApi.users(query, role, confirmed, page).then(data => {
      if (!active) return;
      if (page > 0 && !data.items.length) setPage(page - 1);
      else setResult(data);
    }).catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [section, query, role, confirmed, page, revision]);

  useEffect(() => {
    if (section !== 'categories') return undefined;
    let active = true;
    setLoadingCategories(true);
    setCatError('');
    moderationApi.categories()
      .then(data => {
        if (active) setCategories(Array.isArray(data) ? data : []);
      })
      .catch(err => {
        if (active) setCatError(err.message);
      })
      .finally(() => {
        if (active) setLoadingCategories(false);
      });
    return () => { active = false; };
  }, [section, catRevision]);

  const clear = () => { setSearch(''); setRole(''); setConfirmed(''); setPage(0); };

  const submitRoleChange = async e => {
    e.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setChangeError('');
    try {
      await moderationApi.changeRole(change.user, change.role);
      setSuccess(`Perfil de ${change.user.nome_completo} alterado para ${ROLE_LABELS[change.role]}.`);
      setChange(null);
      setRevision(v => v + 1);
    } catch (err) {
      setChangeError(err.message);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  const handleCreateCategory = async e => {
    e.preventDefault();
    if (creatingCat) return;
    const cleaned = newCatName.trim();
    if (cleaned.length < 2) {
      setCatError('Informe um nome com pelo menos 2 caracteres.');
      return;
    }
    setCreatingCat(true);
    setCatError('');
    setCatSuccess('');
    try {
      await moderationApi.createCategory(cleaned, newCatColor);
      setCatSuccess(`Categoria "${cleaned}" criada com sucesso.`);
      setNewCatName('');
      setNewCatColor('#008bff');
      setCatRevision(v => v + 1);
    } catch (err) {
      setCatError(err.message);
    } finally {
      setCreatingCat(false);
    }
  };

  const handleConfirmDeleteCategory = async () => {
    if (!catToDelete || deletingCat) return;
    setDeletingCat(true);
    setCatError('');
    setCatSuccess('');
    try {
      await moderationApi.deleteCategory(catToDelete.id);
      setCatSuccess(`Categoria "${catToDelete.nome}" excluída.`);
      setCatToDelete(null);
      setCatRevision(v => v + 1);
    } catch (err) {
      setCatError(err.message);
      setCatToDelete(null);
    } finally {
      setDeletingCat(false);
    }
  };

  return (
    <ManagementShell title="Admin" description="Gerencie contas, papéis de acesso e categorias de eventos da comunidade Agenda UnB.">
      <div className="management-toolbar" style={{ marginBottom: '20px' }}>
        <div className="management-tabs" role="group" aria-label="Seções administrativas">
          <button
            type="button"
            className={section === 'users' ? 'active' : ''}
            aria-pressed={section === 'users'}
            onClick={() => setSection('users')}
          >
            Contas e Papéis
          </button>
          <button
            type="button"
            className={section === 'categories' ? 'active' : ''}
            aria-pressed={section === 'categories'}
            onClick={() => setSection('categories')}
          >
            Categorias de Eventos
          </button>
        </div>
      </div>

      {section === 'users' ? (
        <>
          <div className="management-toolbar">
            <p className="management-summary">
              <strong>{result.all}</strong> contas cadastradas
              <span> · {result.unconfirmed} com e-mail não confirmado</span>
            </p>
            <button type="button" className="manage-button" disabled={loading} onClick={() => setRevision(v => v + 1)}>
              <Icon>refresh</Icon>Atualizar
            </button>
          </div>
          <div className="admin-filters">
            <label className="management-search">
              <Icon>search</Icon>
              <span className="sr-only">Buscar usuários por nome ou e-mail</span>
              <input value={search} maxLength={120} onChange={e => { setSearch(e.target.value); setPage(0); }} placeholder="Buscar por nome ou e-mail" />
            </label>
            <div className="management-filter">
              <span>Perfil</span>
              <ManagementSelect
                label="Filtrar por perfil"
                value={role}
                options={[{ value: '', label: 'Todos os perfis' }, ...Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))]}
                onChange={next => { setRole(next); setPage(0); }}
              />
            </div>
            <div className="management-filter">
              <span>E-mail</span>
              <ManagementSelect
                label="Filtrar por e-mail"
                value={confirmed}
                options={[{ value: '', label: 'Todos os e-mails' }, { value: 'sim', label: 'Confirmado' }, { value: 'nao', label: 'Não confirmado' }]}
                onChange={next => { setConfirmed(next); setPage(0); }}
              />
            </div>
            {(search || role || confirmed) && (
              <button type="button" className="manage-button" onClick={clear}>Limpar filtros</button>
            )}
          </div>
          <Feedback error={error} success={success} onRetry={() => setRevision(v => v + 1)} />
          {loading ? (
            <div className="management-state" role="status">Carregando usuários…</div>
          ) : !error && !result.items.length ? (
            <div className="management-state">
              <Icon>person_search</Icon>
              <h2>Nenhum usuário encontrado</h2>
              <p>Experimente outro nome, e-mail ou remova os filtros.</p>
              <button type="button" className="manage-button" onClick={clear}>Limpar filtros</button>
            </div>
          ) : !error && (
            <div className="admin-table-container">
              <table className="admin-table">
                <caption className="sr-only">Usuários cadastrados e seus privilégios</caption>
                <thead>
                  <tr>
                    <th scope="col">Usuário</th>
                    <th scope="col">E-mail</th>
                    <th scope="col">Último acesso</th>
                    <th scope="col">Perfil de acesso</th>
                  </tr>
                </thead>
                <tbody>
                  {result.items.map(account => (
                    <tr key={account.id}>
                      <td>
                        <div className="admin-identity">
                          <span className="admin-initial" aria-hidden="true">{Array.from(account.nome_completo || '?')[0].toUpperCase()}</span>
                          <div>
                            <strong>{account.nome_completo}</strong>
                            {account.id === user.id && <span className="management-tag">Você</span>}
                            <small>Cadastro em {formatDate(account.criado_em)}</small>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="admin-email">{account.email}</span>
                        <small className="admin-confirmation">
                          <Icon>{account.email_confirmado ? 'verified' : 'schedule'}</Icon>
                          {account.email_confirmado ? 'Confirmado' : 'Não confirmado'}
                        </small>
                      </td>
                      <td data-label="Último acesso">{formatDate(account.ultimo_login)}</td>
                      <td>
                        <ManagementSelect
                          label={`Perfil de ${account.nome_completo}`}
                          value={account.papel}
                          disabled={account.id === user.id}
                          options={Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))}
                          onChange={next => { setChange({ user: account, role: next }); setChangeError(''); setSuccess(''); }}
                        />
                        <small>{account.id === user.id ? 'Seu acesso de admin está protegido.' : 'Alterações exigem confirmação.'}</small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!error && <Pagination page={page} total={result.total} onPage={setPage} busy={loading} />}
          {change && (
            <Modal title="Alterar perfil de acesso" busy={busy} onClose={() => setChange(null)}>
              <form onSubmit={submitRoleChange}>
                <p className="dialog-event-title">{change.user.nome_completo}</p>
                <p className="management-muted">{change.user.email}</p>
                <p className="role-change-summary">
                  {ROLE_LABELS[change.user.papel]} <Icon>arrow_forward</Icon> <strong>{ROLE_LABELS[change.role]}</strong>
                </p>
                <p>
                  {change.role === 'admin'
                    ? 'Esta pessoa poderá gerenciar contas, categorias e alterar os privilégios de outros usuários.'
                    : change.role === 'professor'
                      ? 'Esta pessoa poderá publicar eventos e aprovar ou recusar sugestões.'
                      : 'Esta pessoa perderá o acesso à moderação e ao gerenciamento de contas. Poderá continuar enviando sugestões como estudante.'}
                </p>
                <Feedback error={changeError} />
                <footer className="dialog-actions">
                  <button type="button" className="manage-button" disabled={busy} onClick={() => setChange(null)}>Cancelar</button>
                  <button type="submit" className="manage-button primary" disabled={busy}>{busy ? 'Salvando…' : 'Confirmar alteração'}</button>
                </footer>
              </form>
            </Modal>
          )}
        </>
      ) : (
        <>
          <div className="management-toolbar">
            <p className="management-summary">
              <strong>{categories.length}</strong> categorias disponíveis para eventos públicos e pessoais.
            </p>
            <button type="button" className="manage-button" disabled={loadingCategories} onClick={() => setCatRevision(v => v + 1)}>
              <Icon>refresh</Icon>Atualizar
            </button>
          </div>

          <form className="admin-filters" onSubmit={handleCreateCategory} aria-label="Criar nova categoria">
            <label className="management-search" style={{ flex: '1 1 240px' }}>
              <Icon>label</Icon>
              <span className="sr-only">Nome da nova categoria</span>
              <input
                value={newCatName}
                minLength={2}
                maxLength={80}
                required
                onChange={e => setNewCatName(e.target.value)}
                placeholder="Nome da nova categoria (ex.: Seminário)"
              />
            </label>
            <label className="management-filter" style={{ minWidth: '120px' }}>
              <span>Cor</span>
              <input
                type="color"
                aria-label="Cor da categoria"
                value={newCatColor}
                onChange={e => setNewCatColor(e.target.value)}
                style={{ width: '100%', height: '48px', padding: '4px', borderRadius: '10px', border: '1px solid var(--manage-border)', background: 'var(--manage-input)', cursor: 'pointer' }}
              />
            </label>
            <button type="submit" className="manage-button primary" disabled={creatingCat}>
              <Icon>add</Icon>{creatingCat ? 'Criando…' : 'Criar categoria'}
            </button>
          </form>

          <Feedback error={catError} success={catSuccess} onRetry={() => setCatRevision(v => v + 1)} />

          {loadingCategories ? (
            <div className="management-state" role="status">Carregando categorias…</div>
          ) : !categories.length ? (
            <div className="management-state">
              <Icon>category</Icon>
              <h2>Nenhuma categoria cadastrada</h2>
              <p>Crie a primeira categoria acima para organizar os eventos.</p>
            </div>
          ) : (
            <div className="admin-table-container">
              <table className="admin-table">
                <caption className="sr-only">Categorias de eventos cadastradas</caption>
                <thead>
                  <tr>
                    <th scope="col">Categoria</th>
                    <th scope="col">Cor</th>
                    <th scope="col">Eventos vinculados</th>
                    <th scope="col">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map(cat => (
                    <tr key={cat.id}>
                      <td><strong>{cat.nome}</strong></td>
                      <td data-label="Cor">
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                          <span aria-hidden="true" style={{ width: '16px', height: '16px', borderRadius: '50%', background: cat.cor || '#008bff', border: '1px solid var(--manage-border)' }} />
                          <code>{cat.cor || '#008bff'}</code>
                        </span>
                      </td>
                      <td data-label="Eventos vinculados">{cat.events_count ?? 0}</td>
                      <td>
                        <button
                          type="button"
                          className="manage-button"
                          disabled={(cat.events_count ?? 0) > 0}
                          title={(cat.events_count ?? 0) > 0 ? 'Não é possível excluir uma categoria vinculada a eventos' : `Excluir categoria ${cat.nome}`}
                          onClick={() => setCatToDelete(cat)}
                        >
                          <Icon>delete</Icon>Excluir
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {catToDelete && (
            <Modal title="Excluir categoria" busy={deletingCat} onClose={() => setCatToDelete(null)}>
              <p className="dialog-event-title">{catToDelete.nome}</p>
              <p>Esta ação removerá permanentemente a categoria do catálogo. Deseja continuar?</p>
              <footer className="dialog-actions">
                <button type="button" className="manage-button" disabled={deletingCat} onClick={() => setCatToDelete(null)}>
                  Cancelar
                </button>
                <button type="button" className="manage-button primary" disabled={deletingCat} onClick={handleConfirmDeleteCategory}>
                  {deletingCat ? 'Excluindo…' : 'Confirmar exclusão'}
                </button>
              </footer>
            </Modal>
          )}
        </>
      )}
    </ManagementShell>
  );
}
