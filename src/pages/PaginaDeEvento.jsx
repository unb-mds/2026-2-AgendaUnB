import React, { useState } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../styles/global.css';

export default function PaginaDeEvento() {
  const { id } = useParams();
  const { user, signOut } = useAuth();
  const location = useLocation();
  
  const [interessados, setInteressados] = useState(10);
  const [hasClicked, setHasClicked] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

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
        foto: user.user_metadata?.avatar_url || null,
        iniciais: nome.charAt(0).toUpperCase()
      };
    }
  };

  const organizador = getOrganizadorInfo() || { nome: 'Organizador', foto: null, iniciais: 'O' };

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
        return <p key={idx} style={{ marginTop: '1.5rem', fontWeight: 600, color: '#fff' }}>{para.replace(/\*\*/g, '')}</p>;
      }
      if (para.startsWith('-')) {
        return (
          <ul key={idx} className="event-list">
            {para.split('\n').map((item, i) => (
              <li key={i}>{item.replace('-', '').trim()}</li>
            ))}
          </ul>
        )
      }
      return <p key={idx}>{para}</p>;
    });
  };

  return (
    <div className="event-page-wrapper">
      <nav className="nav">
        <div className="nav-brand"></div>
        <div className="nav-items">
          <Link to="/segunda-pagina">Explorar Eventos</Link>
        </div>
        <div className="nav-right">
          <span className="material-symbols-outlined nav-bell">notifications</span>
          {user ? (
            <div 
              className="nav-avatar" 
              title="Sair"
              onClick={signOut}
              style={{ cursor: 'pointer', background: 'rgb(0, 139, 255)', color: '#fff', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
              {user.user_metadata?.avatar_url ? (
                <img src={user.user_metadata.avatar_url} alt="Avatar" style={{width: '100%', height: '100%', borderRadius: '50%'}} />
              ) : (
                user.email ? user.email.charAt(0).toUpperCase() : 'U'
              )}
            </div>
          ) : (
            <Link to="/" style={{ color: '#008bff', textDecoration: 'none', fontWeight: 700, fontSize: '0.8rem' }}>ENTRAR</Link>
          )}
        </div>
      </nav>

      <main className="event-page-content">
        <div className="event-main-col">
          <div className="event-header">
            <div className="event-badges">
              <span className="ds-section-label">{evento.categoria}</span>
              <span className="ds-section-label campus-badge">{evento.campus}</span>
            </div>
            <h1 className="event-title">{evento.titulo}</h1>
            
            <div className="event-organizer-box">
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
                <span className="org-label">Organizado por</span>
                <span className="org-name">{evento.organizador.nome}</span>
              </div>
            </div>
          </div>

          <div className="event-body">
            {renderDescricao()}
          </div>
        </div>

        <aside className="event-side-col">
          <div className="event-action-card">
            <div className="event-info-line">
              <span className="material-symbols-outlined icon-blue">calendar_month</span>
              <span>{evento.data}</span>
            </div>
            <div className="event-info-line">
              <span className="material-symbols-outlined icon-blue">location_on</span>
              <span>{evento.local}</span>
            </div>
            
            <div className="event-actions">
              <button className="ds-btn-primary" onClick={handleConferir}>
                <span className="material-symbols-outlined">open_in_new</span>
                CONFERIR EVENTO
              </button>
              
              <div className="social-counter">
                <span className="material-symbols-outlined icon-hot">local_fire_department</span>
                <strong>{interessados}</strong> {interessados === 1 ? 'pessoa interessada' : 'pessoas interessadas'}
              </div>

              <button className="ds-btn-secondary" onClick={handleShare}>
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
