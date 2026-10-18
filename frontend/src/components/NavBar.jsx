import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import NotificationBell from './NotificationBell';

export default function NavBar({ pageType = 'home', isDark, toggleTheme, onLoginClick, onCreateAccountClick }) {
  const { user, profile, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const nav = useRef(null);
  const menuButton = useRef(null);
  const canModerate = ['professor', 'admin'].includes(profile?.papel);
  useEffect(() => { setMenuOpen(false); }, [location]);
  useEffect(() => {
    if (!menuOpen) return;
    const close = e => {
      if (e.type === 'keydown' && e.key === 'Escape') { setMenuOpen(false); menuButton.current?.focus(); }
      else if (e.type === 'pointerdown' && !nav.current?.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('keydown', close); document.addEventListener('pointerdown', close);
    return () => { document.removeEventListener('keydown', close); document.removeEventListener('pointerdown', close); };
  }, [menuOpen]);
  const avatar = profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture;
  return <nav ref={nav} className={`nav app-nav ${pageType === 'home' ? 'home-nav' : ''} ${menuOpen ? 'menu-open' : ''}`} aria-label="Navegação principal">
    <button ref={menuButton} className="manage-icon-button nav-menu-toggle" aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'} aria-expanded={menuOpen} aria-controls="main-nav-links" onClick={() => setMenuOpen(v => !v)}>
      <span className="material-symbols-outlined" aria-hidden="true">{menuOpen ? 'close' : 'menu'}</span>
    </button>
    <div className="nav-items" id="main-nav-links" onClick={() => setMenuOpen(false)}>
      {pageType === 'home' ? <>{[['#eventos', 'Funcionalidades'], ['#organizer', 'Sobre'], ['#equipe', 'Equipe']].map(([hash, label]) =>
        <Link key={hash} to={`/${hash}`} className={location.hash === hash ? 'active' : ''} aria-current={location.hash === hash ? 'location' : undefined}>{label}</Link>)}</>
        : <><NavLink to="/eventos" className={({ isActive }) => isActive || location.pathname.startsWith('/evento/') ? 'active' : ''}>Eventos</NavLink><NavLink to="/plano-de-ensino">Plano de Ensino</NavLink></>}
      {canModerate && <NavLink to="/sugestoes">Sugestões</NavLink>}
      {profile?.papel === 'admin' && <NavLink to="/admin" className="nav-admin-link">Admin</NavLink>}
    </div>
    <div className="nav-right">
      {toggleTheme && <button className="theme-toggle" onClick={toggleTheme} aria-label={isDark ? 'Ativar tema claro' : 'Ativar tema escuro'} title={isDark ? 'Tema claro' : 'Tema escuro'}>
        <span className="material-symbols-outlined" aria-hidden="true">{isDark ? 'brightness_7' : 'bedtime'}</span>
      </button>}
      {user && profile?.papel === 'student' && <NotificationBell key={user.id} userId={user.id} />}
      {user && <button className="nav-avatar" title="Sair da conta" aria-label="Sair da conta" onClick={signOut}>
        {avatar ? <img src={avatar} referrerPolicy="no-referrer" alt="" /> : (profile?.nome_completo?.[0] || user.email?.[0] || 'U').toUpperCase()}
      </button>}
      {!user && pageType === 'home' && <><button className="nav-btn-account" onClick={onCreateAccountClick}>Criar conta</button><button className="nav-btn-account-login" onClick={onLoginClick}>Entrar</button></>}
    </div>
  </nav>;
}
