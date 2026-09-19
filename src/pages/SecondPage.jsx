import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function SegundaPagina({ theme: propTheme, toggleTheme: propToggleTheme }) {
  const [internalTheme, setInternalTheme] = useState('dark')
  const theme = propTheme || internalTheme
  const toggleTheme = propToggleTheme || (() => setInternalTheme(t => t === 'dark' ? 'light' : 'dark'))

  useEffect(() => {
    document.body.classList.remove('light', 'dark')
    document.body.classList.add(theme)
  }, [theme])
  return (
    <div style={{
      minHeight: '100vh',
      padding: '4rem 1.5rem 3rem',
      maxWidth: '1120px',
      margin: '0 auto',
      position: 'relative',
      zIndex: 2
    }}>

      {/* Barra superior de navegação */}
      <nav className="nav">
        <div>
          
        </div>
        
        <div className="nav-items">
          <a href="#eventos" style={{ color: theme === 'dark' ? '' : '#1a1a2e' }}>Eventos</a>
          <a href="#plano-de-ensino" style={{ color: theme === 'dark' ? '' : '#1a1a2e' }}>Plano de Ensino</a>
        </div>
        
        <div className="nav-right">
          {toggleTheme && (
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '1.2rem', color: theme === 'dark' ? '#fff' : '#1a1a2e' }}>
                {theme === 'dark' ? 'brightness_7' : 'bedtime'}
              </span>
            </button>
          )}

          {/* Botão de notificações */}
          <svg className="nav-bell" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={theme === 'dark' ? "currentColor" : "#1a1a2e"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>

          {/* Placeholder da Foto de Perfil */}
          <div className="nav-avatar" title="Perfil do Usuário" style={{ cursor: 'pointer' }}>
            U
          </div>
        </div>
      </nav>

      {/* Caixa de conteúdo / Placeholder */}
      <div style={{
        background: theme === 'dark' ? 'rgba(8, 12, 22, 0.75)' : 'rgba(255, 255, 255, 0.85)',
        border: '1px solid rgba(0, 139, 255, 0.25)',
        borderRadius: '16px',
        padding: '4rem 2rem',
        textAlign: 'center',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        boxShadow: theme === 'dark' ? '0 10px 40px rgba(0, 0, 0, 0.5)' : '0 10px 30px rgba(0, 0, 0, 0.08)'
      }}>
        <div className="section-label">Nova Rota</div>

        <h1 style={{
          fontFamily: "'Orbitron', sans-serif",
          fontSize: 'clamp(1.8rem, 4vw, 2.5rem)',
          fontWeight: 700,
          marginBottom: '1rem',
          color: theme === 'dark' ? '#fff' : '#1a1a2e'
        }}>
          TESTE
        </h1>

        <p style={{
          maxWidth: '560px',
          margin: '0 auto 2.5rem',
          color: theme === 'dark' ? 'rgba(255, 255, 255, 0.65)' : 'rgba(26, 26, 46, 0.7)',
          lineHeight: '1.6',
          fontSize: '0.95rem'
        }}>
          A rota <code>/segunda-pagina</code> está configurada com sucesso. Este espaço está pronto para você adicionar seu novo layout, formulários, componentes ou lógica.
        </p>

        <Link
          to="/"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 28px',
            borderRadius: '999px',
            background: 'linear-gradient(135deg, rgb(0, 95, 210), rgb(0, 139, 255))',
            color: '#fff',
            textDecoration: 'none',
            fontWeight: 600,
            fontSize: '0.9rem',
            boxShadow: '0 4px 20px rgba(0, 139, 255, 0.35)',
            transition: 'transform 0.2s ease'
          }}
        >
          ← Voltar para a Página Inicial
        </Link>
      </div>
    </div>
  )
}

