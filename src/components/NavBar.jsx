import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function NavBar({ 
  pageType = 'home', // 'home', 'second', 'evento'
  isDark,
  toggleTheme,
  onLoginClick,
  onCreateAccountClick
}) {
  const { user, profile, signOut } = useAuth();

  const showNotification = user && pageType !== 'home';
  const showAvatar = !!user;
  const showLoginButtons = !user && pageType === 'home';

  return (
    <nav className="nav" style={{ 
      position: 'fixed', top: '18px', zIndex: 1000, display: 'flex', alignItems: 'center', 
      justifyContent: 'space-between', padding: '0 28px',
      background: isDark ? 'rgba(5,5,12,0.82)' : 'rgba(255, 255, 255, 0.85)',
      borderColor: isDark ? 'rgba(0, 139, 255, 0.15)' : 'rgba(0, 139, 255, 0.2)'
    }}>
      <div className="nav-brand"></div>

      <div className="nav-items" style={pageType === 'second' ? { 
        position: 'absolute', left: '50%', transform: 'translateX(-50%)',
        display: 'flex', gap: '2rem' 
      } : {}}>
        {pageType === 'home' && (
          <>
            <a href="#eventos">Funcionalidades</a>
            <a href="#organizer">Sobre</a>
            <a href="#equipe">Equipe</a>
          </>
        )}
        {pageType === 'second' && (
          <>
            <a href="#eventos">Eventos</a>
            <a href="#plano-de-ensino">Plano de Ensino</a>
          </>
        )}
        {pageType === 'evento' && (
          <Link to="/segunda-pagina">Explorar Eventos</Link>
        )}
      </div>

      <div className="nav-right" style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '1rem' }}>
        {toggleTheme && (
          <button 
            className="theme-toggle" 
            onClick={toggleTheme} 
            title={isDark ? 'Tema claro' : 'Tema escuro'}
            style={!isDark ? { background: 'rgba(0,0,0,0.06)', borderColor: 'rgba(0,0,0,0.12)', color: '#555' } : {}}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '1.2rem' }}>
              {isDark ? 'brightness_7' : 'bedtime'}
            </span>
          </button>
        )}

        {showNotification && (
          <svg className="nav-bell" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: isDark ? 'rgba(255,255,255,0.55)' : 'rgba(26,26,46,0.5)' }}>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
        )}

        {showAvatar && (
          <div 
            className="nav-avatar" 
            title="Sair"
            onClick={signOut}
            style={{ cursor: 'pointer', background: 'rgb(0, 139, 255)', color: '#fff', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', overflow: 'hidden' }}
          >
            {user.user_metadata?.avatar_url || user.user_metadata?.picture ? (
              <img src={user.user_metadata.avatar_url || user.user_metadata.picture} referrerPolicy="no-referrer" alt="Avatar" style={{width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover'}} />
            ) : (
              profile?.nome_completo?.[0]?.toUpperCase() || user.email?.charAt(0).toUpperCase() || 'U'
            )}
          </div>
        )}

        {showLoginButtons && (
          <>
            <button className="nav-btn-account" onClick={onCreateAccountClick}>Criar conta</button>
            <button className="nav-btn-account-login" onClick={onLoginClick}>Entrar</button>
          </>
        )}
      </div>
    </nav>
  );
}
