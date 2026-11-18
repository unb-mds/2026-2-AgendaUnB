import { useEffect, useId, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';

const ROLE_LABELS = {
  admin: 'Administrador',
  professor: 'Professor',
  student: 'Estudante',
};

export default function ProfileMenu({ user, profile, avatar, signOut }) {
  const panelId = useId();
  const containerRef = useRef(null);
  const buttonRef = useRef(null);
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState('');

  const displayName = (
    profile?.nome_completo?.trim()
    || user?.user_metadata?.nome_completo?.trim()
    || user?.user_metadata?.full_name?.trim()
    || user?.user_metadata?.name?.trim()
    || 'Usuário UnB'
  );
  const initial = (displayName[0] || user?.email?.[0] || 'U').toUpperCase();
  const roleLabel = ROLE_LABELS[profile?.papel] || '';

  useEffect(() => {
    setOpen(false);
    setError('');
  }, [location]);

  useEffect(() => {
    if (!open) return undefined;
    const dismiss = event => {
      if (event.type === 'keydown' && event.key === 'Escape') {
        event.preventDefault();
        setOpen(false);
        buttonRef.current?.focus();
      } else if (event.type === 'pointerdown' && !containerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('keydown', dismiss);
    document.addEventListener('pointerdown', dismiss);
    return () => {
      document.removeEventListener('keydown', dismiss);
      document.removeEventListener('pointerdown', dismiss);
    };
  }, [open]);

  const handleSignOut = async () => {
    if (signingOut) return;
    setSigningOut(true);
    setError('');
    try {
      await signOut();
      setOpen(false);
    } catch (err) {
      setError(err?.message || 'Não foi possível sair da conta. Tente novamente.');
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <div className="profile-anchor" ref={containerRef}>
      <button
        ref={buttonRef}
        type="button"
        className={`nav-avatar${open ? ' open' : ''}`}
        aria-label={`Menu do perfil de ${displayName}`}
        title={displayName}
        aria-haspopup="dialog"
        aria-controls={open ? panelId : undefined}
        aria-expanded={open}
        onClick={() => {
          setError('');
          setOpen(value => !value);
        }}
      >
        {avatar ? <img src={avatar} referrerPolicy="no-referrer" alt="" /> : initial}
      </button>
      {open && (
        <section id={panelId} className="profile-popover" role="dialog" aria-label="Perfil e sessão">
          <div className="profile-popover-header">
            <div className="profile-popover-avatar" aria-hidden="true">
              {avatar ? <img src={avatar} referrerPolicy="no-referrer" alt="" /> : initial}
            </div>
            <div className="profile-popover-identity">
              <strong className="profile-popover-name">{displayName}</strong>
              {user?.email && <span className="profile-popover-email">{user.email}</span>}
              {roleLabel && <span className="management-tag profile-popover-role">{roleLabel}</span>}
            </div>
          </div>
          {error && <p className="profile-popover-error" role="alert">{error}</p>}
          <div className="profile-popover-actions">
            <button
              type="button"
              className="profile-logout-btn"
              disabled={signingOut}
              onClick={handleSignOut}
            >
              <span className="material-symbols-outlined" aria-hidden="true">logout</span>
              {signingOut ? 'Saindo…' : 'Sair da conta'}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
