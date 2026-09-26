import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import NavBar from '../components/NavBar';
import '../styles/global.css';

export default function PaginaDeEvento() {
  const { id } = useParams();
  const { user, signOut } = useAuth();
  const location = useLocation();
  
  const [interessados, setInteressados] = useState(10);
  const [hasClicked, setHasClicked] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const [theme, setTheme] = useState(() => document.body.classList.contains('light') ? 'light' : 'dark');
  
  useEffect(() => {
    document.body.classList.remove('light', 'dark');
    document.body.classList.add(theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');
  const isDark = theme === 'dark';

  const eventoState = location.state?.evento;

  const getOrganizadorInfo = () => {
    if (eventoState?.organizadorNome) {
      return {
        nome: eventoState.organizadorNome,
        foto: eventoState.organizadorFoto,
        iniciais: eventoState.organizadorNome.charAt(0).toUpperCase()
      };
    }
    if (user) {
      const nome = user.user_metadata?.full_name || user.user_metadata?.name || user.email || "Organizador";
      return {
        nome,
        foto: user.user_metadata?.avatar_url || user.user_metadata?.picture || null,
        iniciais: nome.charAt(0).toUpperCase()
      };
    }
    
    return {
      nome: "Convidado",
      foto: null,
      iniciais: "C"
    };
  };

  const organizador = getOrganizadorInfo();

  // Dados mockados fundidos com os passados pelo estado
  const evento = {
    titulo: eventoState?.titulo || "Abertura Oficial da 26ª Semuni",
    data: eventoState ? `${eventoState.data} - ${eventoState.horario}` : "Sexta, 21 de Setembro - 14:00",
    local: eventoState?.local || "Memorial Darcy Ribeiro (Beijódromo) - Darcy Ribeiro",
    campus: eventoState?.campus || "Darcy Ribeiro",
    categoria: eventoState?.area || "Cultura",
    organizador,
    descricao: eventoState?.descricao || `Cerimônia de abertura da 26ª Semana Universitária com o tema "Democracia em cena: arte, cultura e pertencimento".
    
Venha celebrar o início do evento mais importante do calendário acadêmico da Universidade de Brasília! Teremos apresentações artísticas, discursos das autoridades da universidade e a presença de convidados ilustres.

**Destaques do Evento:**
- Apresentação da Orquestra Sinfônica da UnB.
- Mesa redonda com grandes pensadores sobre a Democracia.
- Intervenções artísticas no entorno do Beijódromo.

Não perca!`,
    linkOriginal: eventoState?.linkExterno || "https://sigaa.unb.br"
  };

  const handleConferir = () => {
    if (!hasClicked) {
      setInteressados(prev => prev + 1);
      setHasClicked(true);
    }
    // Abre o link do evento em nova aba
    window.open(evento.linkOriginal, "_blank");
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  // Conversão rudimentar de markdown-like text para parágrafos
  const renderDescricao = () => {
    return evento.descricao.split('\n\n').map((para, idx) => {
      if (para.startsWith('**')) {
        return <p key={idx} style={{ 
          marginTop: '2rem', 
          fontWeight: 700, 
          fontSize: '1.2rem',
          color: isDark ? '#fff' : '#1a1a2e',
          borderLeft: '4px solid rgb(0, 139, 255)',
          paddingLeft: '1rem',
          background: isDark ? 'linear-gradient(90deg, rgba(0, 139, 255, 0.1), transparent)' : 'linear-gradient(90deg, rgba(0, 139, 255, 0.05), transparent)',
          padding: '0.5rem 1rem'
        }}>{para.replace(/\*\*/g, '')}</p>;
      }
      if (para.startsWith('-')) {
        return (
          <ul key={idx} className="event-list" style={{ color: isDark ? 'rgba(255,255,255,0.8)' : 'rgba(26,26,46,0.8)' }}>
            {para.split('\n').map((item, i) => (
              <li key={i} style={{ paddingLeft: '0.5rem', marginBottom: '0.75rem' }}>{item.replace('-', '').trim()}</li>
            ))}
          </ul>
        )
      }
      return <p key={idx} style={{ color: isDark ? 'rgba(255,255,255,0.75)' : 'rgba(26,26,46,0.75)', fontSize: '1.05rem', lineHeight: '1.8' }}>{para}</p>;
    });
  };

  return (
    <div className="event-page-wrapper" style={{ position: 'relative', overflow: 'hidden' }}>
      
      {/* Background radial gradient to make it less monochromatic */}
      <div 
        style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, height: '600px',
          background: isDark 
            ? 'radial-gradient(ellipse at 50% 0%, rgba(0, 139, 255, 0.15), transparent 70%)'
            : 'radial-gradient(ellipse at 50% 0%, rgba(0, 139, 255, 0.1), transparent 70%)',
          zIndex: 0,
          pointerEvents: 'none'
        }}
      />

      <NavBar pageType="evento" isDark={isDark} toggleTheme={toggleTheme} />

      <main className="event-page-content" style={{ position: 'relative', zIndex: 1 }}>
        <div className="event-main-col">
          <div className="event-header">
            <div className="event-badges">
              <span className="ds-section-label" style={{ 
                background: 'linear-gradient(135deg, rgb(0, 139, 255), rgba(0, 95, 210, 1))',
                color: '#fff',
                borderColor: 'transparent',
                boxShadow: '0 4px 15px rgba(0, 139, 255, 0.35)'
              }}>{evento.categoria}</span>
              <span className="ds-section-label campus-badge" style={{
                color: isDark ? 'rgba(255,255,255,0.8)' : 'rgba(26,26,46,0.8)',
                borderColor: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)',
                background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
              }}>{evento.campus}</span>
            </div>
            <h1 className="event-title" style={{ 
              color: isDark ? '#fff' : '#1a1a2e',
              textShadow: isDark ? '0 0 30px rgba(0,139,255,0.25)' : 'none',
              fontSize: 'clamp(2.5rem, 5vw, 4rem)',
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              marginBottom: '2.5rem'
            }}>{evento.titulo}</h1>
            
            <div className="event-organizer-box" style={{ borderColor: isDark ? 'rgba(0, 139, 255, 0.15)' : 'rgba(0, 139, 255, 0.2)' }}>
              <div className="organizer-avatar">
                {evento.organizador.foto ? (
                  <img 
                    src={evento.organizador.foto} 
                    alt={evento.organizador.nome} 
                    style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} 
                  />
                ) : (
                  evento.organizador.iniciais
                )}
              </div>
              <div className="organizer-info">
                <span className="org-label" style={{ color: isDark ? 'rgba(255, 255, 255, 0.45)' : 'rgba(26, 26, 46, 0.55)' }}>Organizado por</span>
                <span className="org-name" style={{ color: isDark ? '#fff' : '#1a1a2e', fontSize: '1.1rem' }}>{evento.organizador.nome}</span>
              </div>
            </div>
          </div>

          <div className="event-body">
            {renderDescricao()}
          </div>
        </div>

        <aside className="event-side-col">
          <div className="event-action-card" style={{
            background: isDark ? 'rgba(8, 12, 22, 0.78)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(0, 139, 255, 0.15)' : 'rgba(0, 139, 255, 0.25)',
            boxShadow: isDark ? '0 20px 40px rgba(0,0,0,0.4), 0 0 40px rgba(0, 139, 255, 0.1)' : '0 12px 30px rgba(0, 0, 0, 0.08)'
          }}>
            <div className="event-info-line" style={{ color: isDark ? '#fff' : '#1a1a2e' }}>
              <span className="material-symbols-outlined icon-blue" style={{ fontSize: '1.6rem' }}>calendar_month</span>
              <span style={{ fontWeight: 600 }}>{evento.data}</span>
            </div>
            <div className="event-info-line" style={{ color: isDark ? '#fff' : '#1a1a2e' }}>
              <span className="material-symbols-outlined icon-blue" style={{ fontSize: '1.6rem' }}>location_on</span>
              <span style={{ fontWeight: 600 }}>{evento.local}</span>
            </div>
            
            <div className="event-actions">
              <button className="ds-btn-primary" onClick={handleConferir} style={{ 
                background: 'linear-gradient(135deg, rgb(0, 95, 210), rgb(0, 139, 255))',
                height: '56px',
                fontSize: '1rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                <span className="material-symbols-outlined">open_in_new</span>
                CONFERIR EVENTO
              </button>
              
              <div className="social-counter" style={{
                background: isDark ? 'rgba(0, 139, 255, 0.05)' : 'rgba(0, 139, 255, 0.08)',
                color: isDark ? 'rgba(255,255,255,0.65)' : 'rgba(26,26,46,0.65)',
                padding: '12px'
              }}>
                <span className="material-symbols-outlined icon-hot">local_fire_department</span>
                <strong style={{ color: isDark ? '#fff' : '#1a1a2e', fontSize: '1rem' }}>{interessados}</strong> 
                <span>{interessados === 1 ? 'pessoa interessada' : 'pessoas interessadas'}</span>
              </div>

              <button className="ds-btn-secondary" onClick={handleShare} style={{
                color: isDark ? 'rgba(255, 255, 255, 0.7)' : 'rgba(26, 26, 46, 0.7)',
                borderColor: isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.15)',
                height: '50px'
              }}>
                <span className="material-symbols-outlined">{isCopied ? 'check' : 'share'}</span>
                {isCopied ? 'Link Copiado!' : 'Compartilhar evento'}
              </button>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
