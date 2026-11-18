import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../lib/supabase';
import {
  DELETE_CONFIRMATION_PHRASE,
  accountApi,
  clearPendingSignupLegal,
  clearUserLocalData,
  formatAccountError,
  isValidDeleteConfirmation,
  notifyLegalDocumentsUpdated,
} from '../lib/accountApi';
import { Feedback, Icon, ManagementShell, Modal } from '../components/ManagementUI';

const ROLE_LABELS = {
  student: 'Estudante',
  professor: 'Professor',
  admin: 'Administrador',
};

const DOCUMENT_ITEMS = [
  { key: 'terms', title: 'Termos de Uso', href: '/termos.html' },
  { key: 'privacy', title: 'Política de Privacidade', href: '/privacidade.html' },
];

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
});

function formatTimestamp(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return dateFormatter.format(date);
}

export default function SettingsPage() {
  const { user, profile } = useAuth();
  const navigate = useNavigate();

  const [legalDocs, setLegalDocs] = useState(null);
  const [consents, setConsents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const [legalBusyKey, setLegalBusyKey] = useState('');
  const [legalFeedback, setLegalFeedback] = useState({ error: '', success: '' });

  const [consentBusy, setConsentBusy] = useState(false);
  const [consentFeedback, setConsentFeedback] = useState({ error: '', success: '' });

  const [exportBusy, setExportBusy] = useState(false);
  const [exportFeedback, setExportFeedback] = useState({ error: '', success: '' });

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmationInput, setConfirmationInput] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const confirmationInputRef = useRef(null);

  const loadAccountState = useCallback(async (signal) => {
    setLoading(true);
    setLoadError('');
    try {
      const [docsResult, consentsResult] = await Promise.all([
        accountApi.getLegalDocuments(signal),
        accountApi.getConsents(signal),
      ]);
      if (signal?.aborted) return;
      setLegalDocs(docsResult);
      setConsents(consentsResult.items);
    } catch (err) {
      if (!signal?.aborted) {
        setLoadError(formatAccountError(err, 'generic'));
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadAccountState(controller.signal);
    return () => controller.abort();
  }, [loadAccountState]);

  async function acceptDocument(docKey) {
    const doc = legalDocs?.[docKey];
    if (!doc || legalBusyKey) return;
    setLegalBusyKey(docKey);
    setLegalFeedback({ error: '', success: '' });
    try {
      await accountApi.acceptLegalDocument(docKey, doc.currentVersion);
      const updated = await accountApi.getLegalDocuments();
      setLegalDocs(updated);
      notifyLegalDocumentsUpdated();
      setLegalFeedback({ error: '', success: 'Aceite registrado para a versão vigente.' });
    } catch (err) {
      if (err?.status === 409) {
        setLegalFeedback({ error: formatAccountError(err, 'legal'), success: '' });
        try {
          setLegalDocs(await accountApi.getLegalDocuments());
        } catch {
          // Keep conflict feedback visible.
        }
      } else {
        setLegalFeedback({ error: formatAccountError(err, 'legal'), success: '' });
      }
    } finally {
      setLegalBusyKey('');
    }
  }

  async function revokeGoogleConsent() {
    if (consentBusy) return;
    setConsentBusy(true);
    setConsentFeedback({ error: '', success: '' });
    try {
      await accountApi.revokeConsent('google_agenda');
      const next = await accountApi.getConsents();
      setConsents(next.items);
      setConsentFeedback({
        error: '',
        success: 'Consentimento do Google Agenda revogado e conexão encerrada. Eventos já exportados permanecem na agenda "Agenda UnB" do Google até serem removidos por você.',
      });
    } catch (err) {
      setConsentFeedback({ error: formatAccountError(err, 'generic'), success: '' });
    } finally {
      setConsentBusy(false);
    }
  }

  async function handleDownloadExport() {
    if (exportBusy) return;
    setExportBusy(true);
    setExportFeedback({ error: '', success: '' });
    try {
      const filename = await accountApi.downloadDataExport();
      setExportFeedback({ error: '', success: `Arquivo ${filename} baixado com os seus dados.` });
    } catch (err) {
      setExportFeedback({ error: formatAccountError(err, 'export'), success: '' });
    } finally {
      setExportBusy(false);
    }
  }

  function openDeleteModal() {
    setConfirmationInput('');
    setDeleteError('');
    setDeleteOpen(true);
  }

  async function handleDeleteAccount(event) {
    event.preventDefault();
    if (deleting) return;
    setDeleteError('');

    if (!isValidDeleteConfirmation(confirmationInput)) {
      setDeleteError(`Digite exatamente "${DELETE_CONFIRMATION_PHRASE}" para confirmar a exclusão.`);
      confirmationInputRef.current?.focus();
      return;
    }

    setDeleting(true);
    try {
      await accountApi.deleteAccount(confirmationInput);
      const deletedEmail = user?.email;
      const deletedUserId = user?.id;
      clearUserLocalData(deletedUserId);
      await clearPendingSignupLegal(deletedEmail);
      setDeleteOpen(false);
      navigate('/?conta=excluida', { replace: true });
      void supabase.auth.signOut({ scope: 'local' }).catch(() => null);
    } catch (err) {
      setDeleteError(formatAccountError(err, 'delete'));
    } finally {
      setDeleting(false);
    }
  }

  const googleConsent = consents.find(item => item.purpose === 'google_agenda') || null;
  const activeGoogleConsent = consents.find(item => item.purpose === 'google_agenda' && item.active) || null;

  return (
    <ManagementShell
      title="Configurações e privacidade"
      description="Consulte versões aceitas, gerencie consentimentos, baixe uma cópia dos seus dados ou exclua sua conta."
    >
      <Feedback error={loadError} onRetry={() => loadAccountState()} />

      <div className="settings-grid">
        <section className="settings-card" aria-labelledby="settings-account-heading">
          <div className="settings-card-header">
            <h2 id="settings-account-heading">Conta</h2>
            <span className="management-tag">{ROLE_LABELS[profile?.papel] || 'Conta ativa'}</span>
          </div>
          <dl className="settings-definition-list">
            <div>
              <dt>Nome completo</dt>
              <dd>{profile?.nome_completo || user?.user_metadata?.nome_completo || 'Não informado'}</dd>
            </div>
            <div>
              <dt>E-mail cadastrado</dt>
              <dd>{user?.email || 'Não informado'}</dd>
            </div>
          </dl>
          <p className="management-muted">
            O endereço de e-mail identifica a conta e não é editável nesta tela.
          </p>
        </section>

        <section className="settings-card" aria-labelledby="settings-legal-heading">
          <div className="settings-card-header">
            <h2 id="settings-legal-heading">Termos de Uso e Política de Privacidade</h2>
          </div>
          <p className="management-muted">
            Estes aceites registram a leitura das regras gerais da plataforma e não substituem consentimentos opcionais.
          </p>

          <Feedback error={legalFeedback.error} success={legalFeedback.success} />

          {loading ? (
            <p className="management-muted" role="status">Carregando versões vigentes…</p>
          ) : !legalDocs ? (
            <p className="management-muted">Não foi possível verificar as versões aceitas no momento.</p>
          ) : (
            <ul className="settings-item-list">
              {DOCUMENT_ITEMS.map(({ key, title, href }) => {
                const doc = legalDocs[key];
                const isPending = doc.pending;
                const isBusy = legalBusyKey === key;
                return (
                  <li key={key} className="settings-item-row">
                    <div className="settings-item-info">
                      <div className="settings-item-title">
                        <strong>{title}</strong>
                        <span className={`settings-status-badge ${isPending ? 'pending' : 'ok'}`}>
                          {isPending ? 'Pendente' : 'Aceito'}
                        </span>
                      </div>
                      <p className="management-muted">
                        Versão vigente: <strong>{doc.currentVersion}</strong>
                        {doc.acceptedVersion
                          ? ` · Último aceite: ${doc.acceptedVersion}${doc.acceptedAt ? ` em ${formatTimestamp(doc.acceptedAt)}` : ''}`
                          : ' · Ainda não aceito'}
                      </p>
                    </div>
                    <div className="settings-item-actions">
                      <a className="management-link" href={href} target="_blank" rel="noopener noreferrer">
                        Ler documento
                        <Icon>open_in_new</Icon>
                      </a>
                      {isPending && (
                        <button
                          type="button"
                          className="manage-button primary"
                          disabled={Boolean(legalBusyKey)}
                          onClick={() => acceptDocument(key)}
                        >
                          {isBusy ? 'Registrando…' : 'Aceitar versão vigente'}
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="settings-card" aria-labelledby="settings-consents-heading">
          <div className="settings-card-header">
            <h2 id="settings-consents-heading">Consentimentos e compartilhamento</h2>
          </div>

          <Feedback error={consentFeedback.error} success={consentFeedback.success} />

          <ul className="settings-item-list">
            <li className="settings-item-row">
              <div className="settings-item-info">
                <div className="settings-item-title">
                  <strong>Google Agenda</strong>
                  <span className={`settings-status-badge ${activeGoogleConsent ? 'ok' : 'neutral'}`}>
                    {activeGoogleConsent ? 'Autorizado' : googleConsent?.revokedAt ? 'Revogado' : 'Não autorizado'}
                  </span>
                </div>
                <p className="management-muted">
                  {activeGoogleConsent
                    ? `Autorizado em ${formatTimestamp(activeGoogleConsent.grantedAt)}. Ao revogar, os tokens são apagados no servidor e eventos já exportados permanecem na agenda "Agenda UnB" do Google.`
                    : googleConsent?.revokedAt
                      ? `Última revogação em ${formatTimestamp(googleConsent.revokedAt)}. Você pode reconectar a qualquer momento em Meus Eventos.`
                      : 'Nenhuma conexão ativa com o Google Agenda.'}
                </p>
              </div>
              <div className="settings-item-actions">
                <Link className="management-link" to="/eventos?aba=meus">
                  Abrir Meus Eventos
                </Link>
                {activeGoogleConsent && (
                  <button
                    type="button"
                    className="manage-button"
                    disabled={consentBusy}
                    onClick={revokeGoogleConsent}
                  >
                    {consentBusy ? 'Revogando…' : 'Revogar consentimento e desconectar'}
                  </button>
                )}
              </div>
            </li>

            <li className="settings-item-row">
              <div className="settings-item-info">
                <div className="settings-item-title">
                  <strong>Análise de planos com IA (Gemini)</strong>
                  <span className="settings-status-badge neutral">Por plano</span>
                </div>
                <p className="management-muted">
                  A autorização é solicitada individualmente para cada plano de ensino após você revisar o texto exato que será enviado.
                </p>
              </div>
              <div className="settings-item-actions">
                <Link className="management-link" to="/plano-de-ensino">
                  Abrir Plano de Ensino
                </Link>
              </div>
            </li>

            <li className="settings-item-row">
              <div className="settings-item-info">
                <div className="settings-item-title">
                  <strong>Compartilhamento de planos na turma</strong>
                </div>
                <p className="management-muted">
                  Planos enviados começam privados. Quando compartilhados, você pode retirar o compartilhamento ou excluir o plano em Plano de Ensino; cópias já importadas por colegas permanecem nas agendas deles.
                </p>
              </div>
              <div className="settings-item-actions">
                <Link className="management-link" to="/plano-de-ensino">
                  Gerenciar planos
                </Link>
              </div>
            </li>
          </ul>
        </section>

        <section className="settings-card" aria-labelledby="settings-export-heading">
          <div className="settings-card-header">
            <h2 id="settings-export-heading">Meus dados</h2>
          </div>
          <p className="management-muted">
            Baixe em formato JSON os dados vinculados à sua conta (perfil, compromissos, eventos salvos e sugeridos, turmas seguidas, planos e revisões, operações de importação, votos, notificações, aceites e histórico de consentimentos). Tokens criptografados, caminhos internos de armazenamento e dados de outras contas não são incluídos.
          </p>
          <Feedback error={exportFeedback.error} success={exportFeedback.success} />
          <div className="settings-card-footer">
            <button
              type="button"
              className="manage-button primary"
              disabled={exportBusy}
              onClick={handleDownloadExport}
            >
              <Icon>download</Icon>
              {exportBusy ? 'Preparando arquivo…' : 'Baixar meus dados'}
            </button>
          </div>
        </section>

        <section className="settings-card settings-card-danger" aria-labelledby="settings-delete-heading">
          <div className="settings-card-header">
            <h2 id="settings-delete-heading">Excluir conta</h2>
          </div>
          <p className="management-muted">
            A exclusão é permanente e remove sua conta de autenticação, perfil e dados vinculados após revogar o acesso do Google Agenda e apagar eventuais arquivos antigos de planos.
          </p>
          <div className="settings-deletion-summary">
            <div>
              <h3>O que é apagado</h3>
              <ul>
                <li>Perfil, credenciais de login e histórico de aceites e consentimentos.</li>
                <li>Tokens e conexão com o Google Agenda (com solicitação de revogação no Google).</li>
                <li>Agenda pessoal, eventos salvos, notificações, turmas seguidas, votos e operações de importação.</li>
                <li>Planos de ensino enviados, revisões, candidatos, solicitações em andamento e eventos públicos sugeridos ou publicados por você.</li>
              </ul>
            </div>
            <div>
              <h3>O que permanece</h3>
              <ul>
                <li>Cópias independentes que colegas já importaram para as próprias agendas (sem vínculo com sua conta).</li>
                <li>Eventos já exportados para a agenda secundária “Agenda UnB” no seu Google Agenda, que precisam ser excluídos diretamente lá.</li>
                <li>Registro anônimo de que uma exclusão ocorreu, apenas com contagens agregadas e sem dados pessoais.</li>
              </ul>
            </div>
          </div>
          <div className="settings-card-footer">
            <button
              type="button"
              className="manage-button settings-danger-button"
              onClick={openDeleteModal}
            >
              <Icon>delete_forever</Icon>
              Excluir conta
            </button>
          </div>
        </section>
      </div>

      {deleteOpen && (
        <Modal
          title="Confirmar exclusão da conta"
          onClose={() => setDeleteOpen(false)}
          busy={deleting}
        >
          <form onSubmit={handleDeleteAccount}>
            <p className="management-muted">
              Esta ação não pode ser desfeita. Eventos já exportados para a agenda “Agenda UnB” no Google Agenda continuarão lá até você removê-los no Google.
            </p>
            <div className="settings-confirm-field">
              <label htmlFor="delete-account-confirmation">
                Digite <strong>{DELETE_CONFIRMATION_PHRASE}</strong> para confirmar:
              </label>
              <input
                ref={confirmationInputRef}
                id="delete-account-confirmation"
                name="confirmation"
                type="text"
                className="modal-input"
                value={confirmationInput}
                disabled={deleting}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                aria-invalid={deleteError ? 'true' : undefined}
                aria-describedby={deleteError ? 'delete-account-error delete-account-hint' : 'delete-account-hint'}
                onChange={event => {
                  setConfirmationInput(event.target.value);
                  if (deleteError) setDeleteError('');
                }}
              />
              <small id="delete-account-hint" className="management-muted">
                Use exatamente letras maiúsculas e espaços conforme mostrado acima.
              </small>
            </div>
            {deleteError && (
              <div id="delete-account-error" className="management-feedback error" role="alert">
                <Icon>error</Icon>
                <p>{deleteError}</p>
              </div>
            )}
            <div className="dialog-actions">
              <button
                type="button"
                className="manage-button"
                disabled={deleting}
                onClick={() => setDeleteOpen(false)}
                autoFocus
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="manage-button settings-danger-button"
                disabled={deleting}
              >
                {deleting ? 'Excluindo…' : 'Confirmar exclusão definitiva'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </ManagementShell>
  );
}
