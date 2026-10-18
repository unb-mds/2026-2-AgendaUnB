import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import NavBar from './NavBar';

export function Icon({ children }) {
  return <span className="material-symbols-outlined" aria-hidden="true">{children}</span>;
}

export function ManagementSelect({ label, value, options, onChange, disabled = false }) {
  const [open, setOpen] = useState(false);
  const [dropUp, setDropUp] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const optionRefs = useRef([]);
  const listId = useId();
  const selected = options.find(option => option.value === value);

  useEffect(() => {
    if (!open) return undefined;
    const closeOutside = event => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', closeOutside);
    return () => document.removeEventListener('pointerdown', closeOutside);
  }, [open]);

  const showOptions = () => {
    const rect = triggerRef.current.getBoundingClientRect();
    const menuHeight = Math.min(options.length * 44 + 12, 232);
    setDropUp(window.innerHeight - rect.bottom < menuHeight && rect.top > menuHeight);
    setOpen(true);
    requestAnimationFrame(() => optionRefs.current[Math.max(0, options.findIndex(option => option.value === value))]?.focus());
  };
  const choose = nextValue => {
    setOpen(false);
    if (nextValue !== value) onChange(nextValue);
    triggerRef.current?.focus();
  };
  const handleKeyDown = event => {
    if (event.key === 'Escape' && open) {
      event.preventDefault();
      event.stopPropagation();
      setOpen(false);
      triggerRef.current?.focus();
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) { showOptions(); return; }
      const currentIndex = optionRefs.current.indexOf(document.activeElement);
      const direction = event.key === 'ArrowDown' ? 1 : -1;
      optionRefs.current[(currentIndex + direction + options.length) % options.length]?.focus();
    } else if (open && (event.key === 'Home' || event.key === 'End')) {
      event.preventDefault();
      optionRefs.current[event.key === 'Home' ? 0 : options.length - 1]?.focus();
    }
  };

  return <div ref={rootRef} className={`management-select${open ? ' open' : ''}${dropUp ? ' drop-up' : ''}`}
    onKeyDown={handleKeyDown} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <button ref={triggerRef} type="button" className="management-select-trigger" aria-label={label}
      aria-haspopup="listbox" aria-expanded={open} aria-controls={open ? listId : undefined}
      disabled={disabled} onClick={() => open ? setOpen(false) : showOptions()}>
      <span>{selected?.label ?? ''}</span><Icon>expand_more</Icon>
    </button>
    {open && <div id={listId} className="management-select-menu" role="listbox" aria-label={label}>
      {options.map((option, index) => <button key={option.value} ref={element => { optionRefs.current[index] = element; }}
        type="button" role="option" aria-selected={option.value === value}
        className={`management-select-option${option.value === value ? ' selected' : ''}`}
        onClick={() => choose(option.value)}>{option.label}</button>)}
    </div>}
  </div>;
}

export function ManagementShell({ title, description, children }) {
  const [isDark, setIsDark] = useState(() => !document.body.classList.contains('light'));
  const toggleTheme = () => {
    document.body.classList.toggle('light', isDark);
    document.body.classList.toggle('dark', !isDark);
    setIsDark(!isDark);
  };
  return <div className="management-shell">
    <NavBar pageType="management" isDark={isDark} toggleTheme={toggleTheme} />
    <main className="management-main">
      <header className="management-heading"><h1>{title}</h1><p>{description}</p></header>
      {children}
    </main>
  </div>;
}

export function ProtectedRoute({ roles, children }) {
  const { user, profile, loading } = useAuth();
  if (loading) return <div className="management-state" role="status">Verificando acesso…</div>;
  if (!user || !roles.includes(profile?.papel)) return <ManagementShell title="Acesso restrito" description={user
    ? 'Seu perfil não tem permissão para acessar esta página.' : 'Entre na sua conta para acessar esta página.'}>
    <Link className="manage-button primary" to={user ? '/eventos' : '/'}>{user ? 'Voltar aos eventos' : 'Ir para o login'}</Link>
  </ManagementShell>;
  return children;
}

export function Feedback({ error, success, onRetry }) {
  if (!error && !success) return null;
  return <div className={`management-feedback ${error ? 'error' : ''}`} role={error ? 'alert' : 'status'}>
    <Icon>{error ? 'error' : 'check_circle'}</Icon><p>{error || success}</p>
    {error && onRetry && <button className="manage-button" onClick={onRetry}>Tentar novamente</button>}
  </div>;
}

export function Pagination({ page, total, onPage, busy }) {
  if (total <= 20) return null;
  return <nav className="management-pagination" aria-label="Paginação">
    <span>{page * 20 + 1}–{Math.min((page + 1) * 20, total)} de {total}</span>
    <button className="manage-button" disabled={busy || page === 0} onClick={() => onPage(page - 1)}><Icon>chevron_left</Icon>Anterior</button>
    <button className="manage-button" disabled={busy || (page + 1) * 20 >= total} onClick={() => onPage(page + 1)}>Próxima<Icon>chevron_right</Icon></button>
  </nav>;
}

export function Modal({ title, children, onClose, busy = false, className = '' }) {
  const ref = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const dialog = ref.current;
    const previousFocus = document.activeElement;
    dialog.showModal();
    dialog.querySelector('input, textarea')?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      dialog.close(); document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, []);
  return <dialog className={`manage-dialog ${className}`} ref={ref} aria-labelledby="manage-dialog-title"
    onCancel={e => { e.preventDefault(); if (!busy) closeRef.current(); }}>
    <header><h2 id="manage-dialog-title">{title}</h2>
      <button className="manage-icon-button" aria-label="Fechar janela" disabled={busy} onClick={onClose}><Icon>close</Icon></button>
    </header>{children}
  </dialog>;
}

export function useDebounced(value) {
  const [result, setResult] = useState(value);
  useEffect(() => { const id = setTimeout(() => setResult(value), 300); return () => clearTimeout(id); }, [value]);
  return result;
}
