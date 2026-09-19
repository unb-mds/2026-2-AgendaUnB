import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import './styles/global.css'

// ............................
// Dados da equipe
// ............................
const teamMembers = [
  {
    name: 'Thomas Araujo',
    role: 'Frontend',
    github: 'thomas4ugust0',
    email: 'thomasgusto12@gmail.com',
    foto: 'https://github.com/thomas4ugust0.png'
  },
  {
    name: 'Heitor Monteiro',
    role: 'Backend',
    github: 'heitormontt',
    email: 'heitormont.unb@gmail.com',
    foto: 'https://github.com/heitormontt.png'
  },
  {
    name: 'Luis Davi',
    role: 'Banco de Dados',
    github: 'pontesluis',
    email: 'pontesluis1912@gmail.com',
    foto: 'https://github.com/pontesluis.png'
  },
    {
    name: 'Gabriel Escramin',
    role: 'Frontend',
    github: 'Bielziin07', 
    email: 'escramingabriel@gmail.com',
    foto: 'https://github.com/Bielziin07.png'
  },
  {
    name: 'Thomaz Marra',
    role: 'Backend',
    github: 'marrathomaz',
    email: 'marrathomaz05@gmail.com',
    foto: 'https://github.com/marrathomaz.png'
  },
  {
    name: 'Felipe Duque',
    role: 'Banco de Dados',
    github: 'felipecduque7',
    email: 'felipecoutoduque07@gmail.com',
    foto: 'https://github.com/felipecduque7.png'
  },

]

// ............................
// Componente principal
// ............................
export default function App() {
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [theme, setTheme] = useState('dark')
  const [role, setRole] = useState('estudante')
  const heroRef = useRef(null)
  const videoRef = useRef(null)

  // Sincroniza a classe do body com o tema
  useEffect(() => {
    document.body.classList.remove('light', 'dark')
    document.body.classList.add(theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  // Para fechar o modal com ESC
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsMenuOpen(false);
        setIsLoginOpen(false);
      }
    };

    if (isMenuOpen || isLoginOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMenuOpen, isLoginOpen]);

  // Quando sair da tela, o video para
  useEffect(() => {
    const video = videoRef.current;
    const hero = heroRef.current;
    
    if (!video || !hero) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        video.play().catch(() => {}); // Retoma se estiver na tela
      } else {
        video.pause(); // Pausa quando some
      }
    }, { 
      // 0 significa que quando 1 pixel entrar na tela ele dispara,
      // e assim que 100% sumir, dispara também.
      threshold: 0 
    });

    observer.observe(hero);

    return () => observer.disconnect();
  }, [theme]); // Depende do theme pois a tag de vídeo é recriada na troca de tema

  // ............................
  // RENDER
  // ............................
  return (
    <>
      <div style={{ position:'fixed', inset:0, zIndex:0 }}>
        <video
          ref={videoRef}
          key={theme} /* Fazer o react a remontar a tag quando o tema mudar, pra recarregar a source certa */
          autoPlay loop muted playsInline
          style={{ width:'100%', height:'100%', objectFit:'cover', display:'block' }}
        >
          <source src={`/shaderopt-${theme}.webm`} type="video/webm" />
        </video>
      </div>

      {/* Navbar */}
      <nav className="nav">
          <div></div>
          <div className="nav-items">
            <a href="#eventos">Funcionalidades</a>
            <a href="#organizer">Sobre</a>
            <a href="#equipe">Equipe</a>
          </div>
          <div className="nav-right">
            <button className="theme-toggle" onClick={toggleTheme} title={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}>
              <span className="material-symbols-outlined" style={{ fontSize: '1.2rem' }}>
                {theme === 'dark' ? 'brightness_7' : 'bedtime'}
              </span>
            </button>
            <svg className="nav-bell" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            
            {/* Criar conta*/}
            <button 
              className="nav-btn-account"
              onClick={() => setIsMenuOpen(true)}
            >
              Criar conta
            </button>
            <button 
              className="nav-btn-account-login"
              onClick={() => setIsLoginOpen(true)}
            >
              Entrar
            </button>
          </div>
        </nav>

        {/*MODAL CRIAR CONTA*/}
        {isMenuOpen && (
          <div className="modal-overlay" onClick={() => setIsMenuOpen(false)}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
              
              {/* Botão Fechar */}
              <button 
                className="modal-close"
                onClick={() => setIsMenuOpen(false)}
              >
                ✕
              </button>
              <h2 style={{
                textAlign: 'center',
                fontFamily: "'Orbitron', sans-serif",
                color: theme === 'dark' ? '#ffffff' : '#1a1a2e',
                fontSize: '1.65rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                marginBottom: '6px',
                textShadow: theme === 'dark' ? '0 0 20px rgba(0, 139, 255, 0.45)' : 'none'
              }}>
                Criar Conta
              </h2>
              <p style={{
                textAlign: 'center',
                color: theme === 'dark' ? 'rgba(255, 255, 255, 0.55)' : 'rgba(26, 26, 46, 0.6)',
                fontSize: '0.85rem',
                marginBottom: '26px'
              }}>
                Crie sua conta para acessar o portal da Agenda UnB
              </p>
              <container className="role-selector">
                <button 
                  onClick={() => setRole('estudante')}
                  className={role === 'estudante' ? "modal-btn-secondary-on" : "modal-btn-secondary-off"}
                >
                  Estudante
                </button>
                <button 
                  onClick={() => setRole('professor')}
                  className={role === 'professor' ? "modal-btn-secondary-on" : "modal-btn-secondary-off"}
                >
                  Professor
                </button>
              </container>

              {/* Campos do Formulário */}
              <div className="modal-input-group">
                <label className="modal-label">Nome Completo <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="text" placeholder="Seu nome completo" className="modal-input" />
              </div>

              <div className="modal-input-group">
                <label className="modal-label">Email <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input 
                  type="email" 
                  placeholder={role === 'professor' ? "nome.sobrenome@unb.br" : "seu@email.com"} 
                  className="modal-input" 
                />
              </div>

              <div className="modal-input-group">
                <label className="modal-label">Senha <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="password" placeholder="Mínimo 8 caracteres" className="modal-input" />
              </div>

              <div className="modal-input-group">
                <label className="modal-label">Confirmar Senha <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="password" placeholder="Mínimo 8 caracteres" className="modal-input" />
              </div>


              <button 
                className="modal-btn-primary"
                onClick={() => navigate('/segunda-pagina')}
              >
                Criar Conta
              </button>

              <div className="modal-divider">ou</div>

              <button 
                className="modal-btn-google"
                onClick={() => navigate('/segunda-pagina')}
              >
                <svg width="18" height="18" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.7 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                Cadastrar com Google
              </button>

            </div>
          </div>
        )}

        {/*MODAL LOGIN*/}
        {isLoginOpen && (
          <div className="modal-overlay" onClick={() => setIsLoginOpen(false)}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
              
              {/* Botão Fechar */}
              <button 
                className="modal-close"
                onClick={() => setIsLoginOpen(false)}
              >
                ✕
              </button>
              <h2 style={{
                textAlign: 'center',
                fontFamily: "'Orbitron', sans-serif",
                color: theme === 'dark' ? '#ffffff' : '#1a1a2e',
                fontSize: '1.65rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                marginBottom: '6px',
                textShadow: theme === 'dark' ? '0 0 20px rgba(0, 139, 255, 0.45)' : 'none'
              }}>
                Entrar
              </h2>
              <p style={{
                textAlign: 'center',
                color: theme === 'dark' ? 'rgba(255, 255, 255, 0.55)' : 'rgba(26, 26, 46, 0.6)',
                fontSize: '0.85rem',
                marginBottom: '26px'
              }}>
                Acesse sua conta do portal Agenda UnB
              </p>

              {/* Campos do Formulário */}
              <div className="modal-input-group">
                <label className="modal-label">Email <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="email" placeholder="seu@email.com" className="modal-input" />
              </div>

              <div className="modal-input-group">
                <label className="modal-label">Senha <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="password" placeholder="Sua senha" className="modal-input" />
              </div>

              <button 
                className="modal-btn-primary"
                onClick={() => navigate('/segunda-pagina')}
              >
                Entrar
              </button>

              <div className="modal-divider">ou</div>

              <button 
                className="modal-btn-google"
                onClick={() => navigate('/segunda-pagina')}
              >
                <svg width="18" height="18" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.7 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                Entrar com Google
              </button>

            </div>
          </div>
        )}

        {/* HERO */}
        <section 
          ref={heroRef}
          style={{
          minHeight:'100vh', display:'flex', flexDirection:'column',
          alignItems:'center', justifyContent:'center', position:'relative',
          textAlign:'center', padding:'0 1.5rem',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', textAlign: 'left', width: 'fit-content', maxWidth: '100%', marginBottom: '2.5rem' }}>
            <p style={{
              fontFamily:"'Orbitron',sans-serif", fontWeight:300, fontSize:'0.95rem',
              color: theme === 'dark' ? 'rgb(255, 255, 255)' : '#1a1a2e', letterSpacing:'0.2em', textTransform:'uppercase',
              marginBottom:'0.6rem',
            }}>
              Sejam bem-vindos ao
            </p>

            <h1 style={{
              fontFamily:"'Orbitron',sans-serif", fontSize:'clamp(2.8rem,8vw,6.5rem)',
              fontWeight:800, letterSpacing:'0.1em', lineHeight:1,
              textTransform:'uppercase',
              color: theme === 'dark' ? '#fff' : '#1a1a2e',
              textShadow: theme === 'dark'
                ? '0 0 30px rgba(0,139,255,0.45), 0 0 80px rgba(0,139,255,0.15)'
                : '0 0 30px rgba(0,139,255,0.25)',
              margin:0,
            }}>
              AGENDA UNB
            </h1>
          </div>

          {/* Botão Login */}
          <button
            onClick={() => navigate('/segunda-pagina')}
            style={{
              cursor:'pointer', display:'flex', alignItems:'center', gap:'12px',
              padding:'13px 30px', borderRadius:'999px',
              border:'1px solid rgba(0,139,255,0.35)',
              background: theme === 'dark' ? 'rgba(0,20,50,0.4)' : 'rgba(255,255,255,0.85)',
              backdropFilter:'blur(14px)',
              WebkitBackdropFilter:'blur(14px)',
              color: theme === 'dark' ? '#fff' : '#1a1a2e',
              fontFamily:"'Inter',sans-serif", fontWeight:500,
              fontSize:'1rem', transition:'all .3s ease',
              boxShadow: theme === 'dark' ? '0 4px 24px rgba(0,139,255,0.15)' : '0 4px 24px rgba(0,0,0,0.08)',
            }}
            onMouseOver={e => {
              e.currentTarget.style.background = theme === 'dark' ? 'rgba(0,60,120,0.55)' : 'rgba(0,139,255,0.1)'
              e.currentTarget.style.borderColor='rgba(0,139,255,0.6)'
              e.currentTarget.style.transform='translateY(-2px)'
            }}
            onMouseOut={e => {
              e.currentTarget.style.background = theme === 'dark' ? 'rgba(0,20,50,0.4)' : 'rgba(255,255,255,0.85)'
              e.currentTarget.style.borderColor='rgba(0,139,255,0.35)'
              e.currentTarget.style.transform='translateY(0)'
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            Entrar como convidado
          </button>

          <div className="scroll-hint">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>
          </div>
        </section>
        <div style={{
          height:'140px',
          background: theme === 'dark'
            ? 'linear-gradient(to bottom, transparent 0%, #050508 100%)'
            : 'linear-gradient(to bottom, transparent 0%, #f5f6fa 100%)',
          position:'relative', zIndex:2, marginTop:'-140px',
        }}/>
        <div style={{ background: theme === 'dark' ? '#050508' : '#f5f6fa', position:'relative', zIndex:2 }}>

          {/* Funcionalidades */}
          <section id="eventos" className="section">
            <div className="section-label">Funcionalidades</div>
            <h2 className="section-h2">Organize seus estudos</h2>
            <p className="section-sub">No Agenda UnB você pode visualizar desde datas acadêmicas importantes para você até os eventos mais recentes da UnB.</p>

            <div className="feat-grid">
              <div className="feat">
                <div className="feat-icon"><span className="material-symbols-outlined">calendar_month</span></div>
                <h3>Agenda Unificada</h3>
                <p>Visualize todos os eventos do campus em um único calendário inteligente, filtrável por categoria, data e instituto.</p>
              </div>
              <div className="feat">
                <div className="feat-icon"><span className="material-symbols-outlined">edit_calendar</span></div>
                <h3>Submissão de Eventos</h3>
                <p>Usuários logados podem submeter novos eventos. Aqui você pode deixar todo mundo sabendo sobre eles.</p>
              </div>
              <div className="feat">
                <div className="feat-icon"><span className="material-symbols-outlined">upload_file</span></div>
                <h3>Upload de Planos de Ensino</h3>
                <p>Envie múltiplos planos de ensino nos formatos PDF ou em texto bruto e deixe o sistema processar automaticamente.</p>
              </div>
              <div className="feat">
                <div className="feat-icon"><span className="material-symbols-outlined">admin_panel_settings</span></div>
                <h3>Moderação</h3>
                <p>Administradores controlam as submissões antes da publicação, garantindo a qualidade do conteúdo na agenda.</p>
              </div>
              <div className="feat">
                <div className="feat-icon"><span className="material-symbols-outlined">sync</span></div>
                <h3>Importação Automática</h3>
                <p>Busca e importa eventos de fontes externas como perfis do Instagram, feeds e sites da universidade.</p>
              </div>
              <div className="feat">
                <div className="feat-icon"><span className="material-symbols-outlined">how_to_reg</span></div>
                <h3>Inscrição Direta</h3>
                <p>Inscreva-se em eventos diretamente pela plataforma com apenas um clique, sem redirecionamentos externos.</p>
              </div>
              </div>
          </section>

          <div className="divider"/>

          {/* Sobre */}
          <section id="organizer" className="section">
            <div className="section-label">Sobre o projeto</div>
            <h2 className="section-h2">Tudo o que acontece no campus</h2>
            <p className="section-sub">Uma solução que criamos do zero para organizar eventos relevantes pra você.</p>

            <div className="feat-grid">
              <div className="feat">
                <h3>O que é o Agenda UnB?</h3>
                <p>O Agenda UnB é um projeto desenvolvido na matéria de Métodos de Desenvolvimento de Software da Universidade de Brasília, feito para centralizar todos os eventos dos campi da universidade em um único lugar, facilitando a organização e o acesso a informações importantes.</p>
                  <br></br>
                <p>Fizemos um sistema que visa ir além de um calendário colaborativo, mas que também se integra com um organizador acadêmico inteligente. Assim, a plataforma permite que os estudantes façam o upload de seus planos de ensino, extraindo automaticamente as datas de provas,
                   trabalhos e seminários. Essas informações são alocadas em um calendário privado e editável, que melhora a experiência do aluno ao se organizar para suas atividades acadêmicas. Desse modo, nossa aplicação une a vida social do campus e a gestão da rotina de estudos em um único lugar.</p>             
               </div>
            </div>
          </section>

          <div className="divider"/>

          {/* EQUIPE */}
          <section id="equipe" className="section">
            <div className="section-label">Quem somos</div>
            <h2 className="section-h2">A Equipe</h2>
            <p className="section-sub">O time que está tirando a Agenda UnB do papel.</p>

            <div className="team-grid">
              {teamMembers.map((m, i) => (
                <div className="team-card" key={i}>
                  <div className="team-pic-ring">
                    <img 
                        src={m.foto} 
                        alt={m.name} 
                        className="team-pic" 
                        style={{ objectFit: 'cover', width: '100%', height: '100%', borderRadius: '50%' }}
  />
                  </div>
                  <div className="team-name">{m.name}</div>
                  <div className="team-role">{m.role}</div>
                  
                  <div className="team-links">
                    <a
                      href={`https://github.com/${m.github}`}
                      target="_blank"
                      rel="noreferrer"
                      className="team-link-item"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                      </svg>
                      @{m.github}
                    </a>
                    <a
                      href={`mailto:${m.email}`}
                      className="team-link-item"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                        <polyline points="22,6 12,13 2,6"/>
                      </svg>
                      {m.email}
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Footer */}
          <footer className="footer">
            <img src="/Marca-UnB.png" alt="Logo UnB" style={{ width:'70px', marginBottom:'1rem', opacity:0.5, filter: theme === 'light' ? 'invert(1)' : 'none' }}/>
            <p>Agenda UnB — Universidade de Brasília © 2026</p>
          </footer>

        </div>
    </> 
  )
}
