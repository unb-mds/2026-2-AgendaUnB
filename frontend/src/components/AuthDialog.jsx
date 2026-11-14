import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  EMAIL_RETRY_SECONDS, sendConfirmation, sendRecovery, signInWithEmail, signInWithGoogle,
  signUpWithEmail, validateNewPassword,
} from '../lib/auth';
import GoogleMark from './GoogleMark';
import PasswordField from './PasswordField';
import '../styles/auth.css';

const TITLES = {
  login: 'Entrar', signup: 'Criar conta', confirm: 'Confirme seu e-mail', recover: 'Recuperar senha',
};
const pendingSends = { confirm: new Map(), recover: new Map() };

export default function AuthDialog({ mode, setMode }) {
  const navigate = useNavigate();
  const dialog = useRef(null);
  const heading = useRef(null);
  const busy = useRef(false);
  const [sending, setSending] = useState(false);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('student');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [now, setNow] = useState(Date.now);
  const signup = mode === 'signup';
  const login = mode === 'login';
  const emailFlow = !signup && !login;
  const emailKey = email.trim().toLowerCase();
  const seconds = Math.max(0, Math.ceil(((pendingSends[mode]?.get(emailKey) || 0) - now) / 1000));

  useEffect(() => {
    const element = dialog.current;
    const trigger = document.activeElement;
    element.showModal();
    return () => {
      element.close();
      trigger?.focus();
    };
  }, []);

  useEffect(() => {
    heading.current?.focus();
  }, [mode]);

  useEffect(() => {
    function restoreAfterRedirect(event) {
      if (!event.persisted) return;
      busy.current = false;
      setSending(false);
    }
    window.addEventListener('pageshow', restoreAfterRedirect);
    return () => window.removeEventListener('pageshow', restoreAfterRedirect);
  }, []);

  useEffect(() => {
    if (!seconds) return;
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, [seconds]);

  function changeMode(nextMode) {
    setError('');
    setPasswordError('');
    setMessage('');
    setMode(nextMode);
  }

  function startCooldown(kind) {
    const time = Date.now();
    for (const [key, deadline] of pendingSends[kind]) {
      if (deadline <= time) pendingSends[kind].delete(key);
    }
    pendingSends[kind].set(emailKey, time + EMAIL_RETRY_SECONDS * 1000);
    setNow(time);
  }

  async function submit(event) {
    event.preventDefault();
    if (busy.current || (emailFlow && seconds)) return;
    setError('');
    setPasswordError('');
    setMessage('');
    const form = new FormData(event.currentTarget);
    const password = form.get('password');
    if (signup) {
      const issue = validateNewPassword(password, form.get('confirmation'));
      if (issue) {
        setPasswordError(issue);
        event.currentTarget.elements.confirmation.focus();
        return;
      }
    }

    busy.current = true;
    setSending(true);
    try {
      if (signup || login) {
        const result = signup
          ? await signUpWithEmail({ email, password, nomeCompleto: form.get('name'), papel: role })
          : await signInWithEmail(email, password);
        if (result.error) {
          setError(result.error);
        } else if (result.needsConfirmation || (signup && !result.signedIn)) {
          changeMode('confirm');
          if (signup) {
            startCooldown('confirm');
            setMessage('Se o cadastro estiver pendente, enviamos um link de confirmação.');
          } else {
            setMessage('Confirme seu e-mail para entrar. Você pode solicitar outro link abaixo.');
          }
        } else {
          setMode(null);
          navigate('/eventos');
        }
      } else {
        const result = await (mode === 'confirm' ? sendConfirmation(email) : sendRecovery(email));
        if (!result.error || result.rateLimited) startCooldown(mode);
        if (result.error) setError(result.error);
        else setMessage(mode === 'confirm'
          ? 'Se o cadastro estiver pendente, enviamos outro link de confirmação.'
          : 'Se houver uma conta com esse e-mail, você receberá um link para redefinir a senha.');
      }
    } catch {
      setError('Não foi possível concluir a solicitação. Verifique sua conexão e tente novamente.');
    } finally {
      busy.current = false;
      setSending(false);
    }
  }

  async function continueWithGoogle() {
    if (busy.current) return;
    busy.current = true;
    setSending(true);
    setError('');
    try {
      const result = await signInWithGoogle();
      if (result.redirecting) return;
      setError(result.error);
    } catch {
      setError('Não foi possível iniciar o login com Google. Tente novamente.');
    }
    busy.current = false;
    setSending(false);
  }

  const action = { signup: 'Criar conta', login: 'Entrar', confirm: 'Reenviar confirmação', recover: 'Enviar link' }[mode];

  return (
    <dialog
      className="modal-box auth-dialog" ref={dialog} aria-labelledby="auth-dialog-title"
      onCancel={event => { event.preventDefault(); if (!busy.current) setMode(null); }}
      onClick={event => { if (event.target === event.currentTarget && !busy.current) setMode(null); }}
    >
      <div className="auth-dialog-content">
        <button type="button" className="modal-close" aria-label="Fechar" disabled={sending} onClick={() => setMode(null)}>
          <span className="material-symbols-outlined" aria-hidden="true">close</span>
        </button>
        <h2 className="auth-title" id="auth-dialog-title" ref={heading} tabIndex={-1}>{TITLES[mode]}</h2>
        {mode === 'confirm' && <p className="auth-description">Abra o link no e-mail para confirmar sua conta. Confira também a pasta de spam.</p>}
        {mode === 'recover' && <p className="auth-description">Informe seu e-mail para receber o link de redefinição.</p>}

        <form key={mode} onSubmit={submit}>
          {signup && (
            <>
              <div className="role-selector" role="group" aria-label="Perfil da conta">
                {[['student', 'Estudante'], ['professor', 'Professor']].map(([value, label]) => (
                  <button key={value} type="button" disabled={sending} aria-pressed={role === value}
                    className={role === value ? 'modal-btn-secondary-on' : 'modal-btn-secondary-off'}
                    onClick={() => setRole(value)}>{label}</button>
                ))}
              </div>
              <div className="modal-input-group">
                <label className="modal-label" htmlFor="auth-name">Nome completo</label>
                <input id="auth-name" name="name" className="modal-input" autoComplete="name" required minLength={2} />
              </div>
            </>
          )}
          <div className="modal-input-group">
            <label className="modal-label" htmlFor="auth-email">E-mail</label>
            <input
              id="auth-email" name="email" className="modal-input" type="email" required
              autoComplete={emailFlow ? 'email' : 'username'} value={email} readOnly={sending}
              onChange={event => { setEmail(event.target.value); setNow(Date.now()); setError(''); setMessage(''); }}
              aria-describedby={signup && role === 'professor' ? 'auth-email-hint' : undefined}
            />
            {signup && role === 'professor' && <p className="auth-field-hint" id="auth-email-hint">Use seu e-mail @unb.br.</p>}
          </div>
          {(signup || login) && <PasswordField label="Senha" name="password" newPassword={signup} describedBy={signup ? 'auth-password-hint' : undefined} />}
          {signup && (
            <>
              <p className="auth-field-hint auth-password-hint" id="auth-password-hint">Use pelo menos 8 caracteres.</p>
              <PasswordField label="Confirmar senha" name="confirmation" newPassword
                invalid={Boolean(passwordError)} describedBy={passwordError ? 'auth-password-error' : undefined} />
              {passwordError && <p id="auth-password-error" className="auth-error" role="alert">{passwordError}</p>}
            </>
          )}
          {login && <button type="button" className="auth-link" disabled={sending} onClick={() => changeMode('recover')}>Esqueci minha senha</button>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          {message && <p className="auth-description" role="status">{message}</p>}
          <button className="modal-btn-primary" type="submit" disabled={sending || (emailFlow && seconds > 0)}>
            {sending ? 'Aguarde…' : action}
          </button>
          {emailFlow && seconds > 0 && <p className="auth-field-hint auth-countdown">Novo envio em {seconds} s</p>}
        </form>

        {(login || (signup && role === 'student')) && (
          <>
            <div className="modal-divider">ou</div>
            <button type="button" className="modal-btn-google" disabled={sending} onClick={continueWithGoogle}>
              <GoogleMark /> Continuar com Google
            </button>
          </>
        )}
        {emailFlow && <button type="button" className="auth-link auth-back" disabled={sending} onClick={() => changeMode('login')}>Voltar para entrar</button>}
      </div>
    </dialog>
  );
}
