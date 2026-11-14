import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PasswordField from '../components/PasswordField';
import { changePassword, validateNewPassword } from '../lib/auth';
import { createRecoveryClient, supabase } from '../lib/supabase';
import '../styles/auth.css';

const CONFIRMATION_ERROR = 'Este link de confirmação expirou, já foi usado ou é inválido. Solicite outro link.';
const RECOVERY_ERROR = 'Este link de recuperação expirou, já foi usado ou é inválido. Solicite outro link.';
const GOOGLE_ERROR = 'Não foi possível entrar com Google. Volte para tentar novamente ou entre com e-mail e senha.';

function readReturn() {
  const { search, hash } = window.location;
  const query = new URLSearchParams(search);
  const fragment = new URLSearchParams(hash.slice(1));
  return {
    code: query.get('code'),
    errorCode: query.get('error_code') || fragment.get('error_code') || query.get('error') || fragment.get('error'),
    type: fragment.get('type'),
    tokenHash: fragment.get('token_hash'),
  };
}

export default function AuthReturnPage() {
  const navigate = useNavigate();
  const [callback, setCallback] = useState(readReturn);
  const [phase, setPhase] = useState(callback.code ? 'google' : callback.tokenHash ? 'verify' : 'invalid');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const busy = useRef(false);
  const recoveryClient = useRef(null);
  const googleExchange = useRef(null);
  const heading = useRef(null);

  useEffect(() => {
    const cleanUrl = () => window.history.replaceState(window.history.state, '', window.location.pathname);
    cleanUrl();

    function openEmailLink() {
      const next = readReturn();
      if (!next.tokenHash) return;
      // A new email can open on the same pathname without reloading the SPA.
      window.location.reload();
    }
    window.addEventListener('hashchange', openEmailLink);
    return () => window.removeEventListener('hashchange', openEmailLink);
  }, []);

  useEffect(() => {
    heading.current?.focus();
  }, [phase]);

  useEffect(() => {
    if (phase !== 'google') return;
    let active = true;
    googleExchange.current ??= (async () => {
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(callback.code);
      return !exchangeError && Boolean(data?.session);
    })();
    async function exchange() {
      try {
        const result = await googleExchange.current;
        if (!active) return;
        if (result) {
          navigate('/eventos', { replace: true });
          return;
        }
      } catch {
        if (!active) return;
      }
      setCallback({ errorCode: 'google' });
      setPhase('invalid');
    }
    exchange();
    return () => { active = false; };
  }, [callback.code, navigate, phase]);

  async function verify() {
    if (busy.current) return;
    busy.current = true;
    setSending(true);
    setError('');
    try {
      const client = recovery ? createRecoveryClient() : supabase;
      const result = await client.auth.verifyOtp({ type: callback.type, token_hash: callback.tokenHash });
      if (result.error && (!result.error.status || result.error.status >= 500 || result.error.status === 429)) {
        setError('Não foi possível validar o link agora. Aguarde e tente novamente.');
        return;
      }
      if (result.error || !result.data.session) {
        setPhase('invalid');
      } else if (recovery) {
        recoveryClient.current = client;
        setPhase('password');
      } else {
        setPhase('confirmed');
      }
      setCallback({ type: callback.type });
    } catch {
      setError('Não foi possível validar o link agora. Verifique sua conexão e tente novamente.');
    } finally {
      busy.current = false;
      setSending(false);
    }
  }

  async function updatePassword(event) {
    event.preventDefault();
    if (busy.current) return;
    const form = new FormData(event.currentTarget);
    const password = form.get('password');
    const issue = validateNewPassword(password, form.get('confirmation'));
    setError(issue);
    if (issue) {
      event.currentTarget.elements.confirmation.focus();
      return;
    }
    busy.current = true;
    setSending(true);
    try {
      const result = await changePassword(recoveryClient.current, password);
      if (result.error) {
        setError(result.error);
      } else {
        const client = recoveryClient.current;
        recoveryClient.current = null;
        setPhase(result.expired ? 'invalid' : 'changed');
        // Ends the temporary recovery session without replacing the browser's normal session.
        void client.auth.signOut({ scope: 'local' }).catch(() => null);
      }
    } catch {
      setError('Não foi possível redefinir a senha. Verifique sua conexão e tente novamente.');
    } finally {
      busy.current = false;
      setSending(false);
    }
  }

  const recovery = callback.type === 'recovery';
  const validType = recovery || callback.type === 'email';
  const googleFailure = !callback.type && Boolean(callback.errorCode) && callback.errorCode !== 'otp_expired';
  const titles = {
    google: 'Entrando com Google',
    verify: recovery ? 'Redefina sua senha' : 'Confirme seu e-mail',
    invalid: googleFailure ? 'Não foi possível entrar com Google' : 'Não foi possível abrir o link',
    password: 'Escolha uma nova senha',
    confirmed: 'E-mail confirmado',
    changed: 'Senha redefinida',
  };
  const invalid = phase === 'invalid' || (phase === 'verify' && !validType);
  const emailError = recovery ? RECOVERY_ERROR : CONFIRMATION_ERROR;
  const invalidCopy = callback.errorCode === 'access_denied' && googleFailure
    ? 'O Google recusou a autorização. Volte para tentar novamente ou entre com e-mail e senha.'
    : googleFailure ? GOOGLE_ERROR : emailError;

  return (
    <main className="auth-return">
      <section className="modal-box auth-return-panel" aria-labelledby="auth-return-title">
        <div className="auth-dialog-content">
          <h1 className="auth-title" id="auth-return-title" tabIndex={-1} ref={heading}>
            {invalid ? titles.invalid : titles[phase]}
          </h1>
          {phase === 'google' && <p className="auth-description" role="status">Validando o retorno do Google…</p>}
          {invalid && (
            <>
              <p className="auth-description">{invalidCopy}</p>
              <Link className="auth-link auth-back" to={recovery ? '/?auth=recover' : callback.type === 'email' ? '/?auth=confirm' : '/?auth=login'}>
                {recovery ? 'Solicitar recuperação' : callback.type === 'email' ? 'Solicitar confirmação' : 'Voltar para entrar'}
              </Link>
              {!callback.type && <Link className="auth-link auth-back" to="/?auth=recover">Recuperar senha</Link>}
            </>
          )}
          {phase === 'verify' && validType && (
            <>
              <p className="auth-description">{recovery ? 'Valide o link para escolher uma nova senha.' : 'Confirme este endereço para concluir seu cadastro.'}</p>
              <button className="modal-btn-primary" type="button" onClick={verify} disabled={sending}>
                {sending ? 'Validando…' : recovery ? 'Validar link' : 'Confirmar e-mail'}
              </button>
            </>
          )}
          {phase === 'password' && (
            <form onSubmit={updatePassword}>
              <p className="auth-description" id="auth-new-password-hint">Use pelo menos 8 caracteres.</p>
              <PasswordField label="Nova senha" name="password" newPassword describedBy="auth-new-password-hint" />
              <PasswordField label="Confirmar nova senha" name="confirmation" newPassword />
              <button type="submit" className="modal-btn-primary" disabled={sending}>{sending ? 'Salvando…' : 'Salvar senha'}</button>
            </form>
          )}
          {phase === 'confirmed' && <Link className="modal-btn-primary auth-action" to="/eventos">Continuar para eventos</Link>}
          {phase === 'changed' && <Link className="modal-btn-primary auth-action" to="/?auth=login">Entrar com a nova senha</Link>}
          {error && (phase === 'password' || phase === 'verify') && <p className="auth-error" role="alert">{error}</p>}
        </div>
      </section>
    </main>
  );
}
