import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { AUTH_RETURN_PATH } from '../lib/auth';
import {
  LEGAL_DOCUMENTS_UPDATED_EVENT,
  accountApi,
  formatAccountError,
  getPendingLegalDocumentKeys,
  hasPendingLegalDocuments,
  notifyLegalDocumentsUpdated,
} from '../lib/accountApi';
import { Feedback, Icon } from './ManagementUI';

const DOCUMENT_LABELS = {
  terms: { title: 'Termos de Uso', href: '/termos.html' },
  privacy: { title: 'Política de Privacidade', href: '/privacidade.html' },
};

export default function LegalAcceptanceGate() {
  const { user, profile, loading, signOut } = useAuth();
  const location = useLocation();
  const dialogRef = useRef(null);
  const [docs, setDocs] = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const loadDocuments = useCallback(async (signal) => {
    if (loading || !user || !profile) {
      setDocs(null);
      return;
    }
    try {
      const next = await accountApi.getLegalDocuments(signal);
      if (signal?.aborted) return;
      if (next && hasPendingLegalDocuments(next)) {
        setDocs(next);
      } else {
        setDocs(null);
        setDismissed(false);
      }
    } catch {
      if (!signal?.aborted) {
        setDocs(null);
      }
    }
  }, [loading, profile, user]);

  useEffect(() => {
    setDismissed(false);
    setError('');
  }, [user?.id]);

  useEffect(() => {
    if (loading || !user || !profile) {
      setDocs(null);
      return undefined;
    }
    if (location.pathname === AUTH_RETURN_PATH || location.pathname === '/configuracoes') {
      return undefined;
    }
    const controller = new AbortController();
    void loadDocuments(controller.signal);
    return () => controller.abort();
  }, [loadDocuments, loading, location.pathname, profile, user]);

  useEffect(() => {
    function handleUpdated() {
      const controller = new AbortController();
      void loadDocuments(controller.signal);
    }
    window.addEventListener(LEGAL_DOCUMENTS_UPDATED_EVENT, handleUpdated);
    return () => window.removeEventListener(LEGAL_DOCUMENTS_UPDATED_EVENT, handleUpdated);
  }, [loadDocuments]);

  const pendingKeys = getPendingLegalDocumentKeys(docs);
  const shouldShowDialog = Boolean(
    user
    && profile
    && !loading
    && location.pathname !== AUTH_RETURN_PATH
    && location.pathname !== '/configuracoes'
    && pendingKeys.length > 0
    && !dismissed,
  );

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;
    if (shouldShowDialog && !dialog.open) {
      dialog.showModal();
    } else if (!shouldShowDialog && dialog.open) {
      dialog.close();
    }
    return undefined;
  }, [shouldShowDialog]);

  if (!user || !profile || pendingKeys.length === 0 || location.pathname === AUTH_RETURN_PATH || location.pathname === '/configuracoes') {
    return null;
  }

  const isUpdate = pendingKeys.some(key => docs[key]?.acceptedVersion !== null);

  async function acceptAll() {
    if (busy || !docs) return;
    setBusy(true);
    setError('');
    try {
      await accountApi.acceptPendingLegalDocuments(docs);
      setDocs(null);
      setDismissed(false);
      notifyLegalDocumentsUpdated();
    } catch (err) {
      if (err?.status === 409) {
        setError(formatAccountError(err, 'legal'));
        try {
          const refreshed = await accountApi.getLegalDocuments();
          if (refreshed && hasPendingLegalDocuments(refreshed)) {
            setDocs(refreshed);
          } else {
            setDocs(null);
          }
        } catch {
          // Keep current conflict message visible.
        }
      } else {
        setError(formatAccountError(err, 'legal'));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <dialog
        ref={dialogRef}
        className="manage-dialog legal-gate-dialog"
        aria-labelledby="legal-gate-title"
        onCancel={event => {
          event.preventDefault();
          if (!busy) setDismissed(true);
        }}
      >
        <header>
          <h2 id="legal-gate-title">
            {isUpdate ? 'Atualização dos documentos legais' : 'Confirme os documentos da plataforma'}
          </h2>
          <button
            type="button"
            className="manage-icon-button"
            aria-label="Adiar confirmação"
            disabled={busy}
            onClick={() => setDismissed(true)}
          >
            <Icon>close</Icon>
          </button>
        </header>

        <p>
          {isUpdate
            ? 'Publicamos uma nova versão dos documentos abaixo. Leia e confirme para registrar seu aceite vigente.'
            : 'Para continuar usando os recursos da sua conta, confirme a leitura dos documentos vigentes abaixo.'}
        </p>

        <ul className="legal-gate-list">
          {pendingKeys.map(key => {
            const doc = docs[key];
            const meta = DOCUMENT_LABELS[key];
            return (
              <li key={key}>
                <div>
                  <strong>{meta.title}</strong>
                  <span className="management-muted">
                    Versão vigente: {doc.currentVersion}
                    {doc.acceptedVersion ? ` (último aceite: ${doc.acceptedVersion})` : ' (ainda não aceito)'}
                  </span>
                </div>
                <a className="management-link" href={meta.href} target="_blank" rel="noopener noreferrer">
                  Ler documento
                  <Icon>open_in_new</Icon>
                </a>
              </li>
            );
          })}
        </ul>

        <p className="management-muted">
          Este aceite registra a ciência dos Termos e da Política de Privacidade. Permissões opcionais como Google Agenda e envio de texto à IA pedem autorização separada quando usadas.
        </p>

        <Feedback error={error} />

        <div className="dialog-actions legal-gate-actions">
          <button type="button" className="management-text-button" disabled={busy} onClick={signOut}>
            Sair da conta
          </button>
          <Link className="manage-button" to="/configuracoes" onClick={() => setDismissed(true)}>
            Gerenciar em Configurações
          </Link>
          <button type="button" className="manage-button" disabled={busy} onClick={() => setDismissed(true)}>
            Agora não
          </button>
          <button type="button" className="manage-button primary" disabled={busy} onClick={acceptAll} autoFocus>
            {busy ? 'Registrando…' : 'Aceitar e continuar'}
          </button>
        </div>
      </dialog>

      {dismissed && (
        <aside className="legal-gate-banner" role="status" aria-label="Documentos pendentes">
          <p>Há documentos legais pendentes de aceite na sua conta.</p>
          <div className="legal-gate-banner-actions">
            <button type="button" className="manage-button primary" onClick={() => setDismissed(false)}>
              Revisar e aceitar
            </button>
            <Link className="manage-button" to="/configuracoes">
              Configurações
            </Link>
          </div>
        </aside>
      )}
    </>
  );
}
