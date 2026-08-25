import { Canvas } from '@react-three/fiber'
import { useRef, useState, useEffect } from 'react'
import * as THREE from 'three'
import VideoPlane from './components/VideoPlane.jsx'

// ============================================================
// ⚙️ CONFIGURAÇÃO DO EFEITO — altere os valores aqui!
// ============================================================
const settings = {
  gridSize: 7,
  dotSize: 0.18,
  contrast: 1.4,
  brightness: -0.1,
  effectStrength: 1.5,
  color: [0, 0.547, 1],
}

// ============================================================
// 🎨 CSS
// ============================================================
const globalCSS = `
  * { margin:0; padding:0; box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body, #root { width:100%; min-height:100%; background:#050508; font-family:'Inter',sans-serif; color:#fff; }

  ::-webkit-scrollbar { width:6px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:rgba(0,139,255,0.35); border-radius:3px; }

  /* ── Navbar ── */
  .nav {
    position:fixed; top:18px; left:50%; transform:translateX(-50%);
    width:92%; max-width:1100px; height:56px;
    background:rgba(5,5,12,0.82); backdrop-filter:blur(14px);
    -webkit-backdrop-filter:blur(14px);
    border:1px solid rgba(0,139,255,0.15); border-radius:999px;
    display:flex; align-items:center; justify-content:space-between;
    padding:0 28px; z-index:900;
    box-shadow:0 4px 30px rgba(0,0,0,0.55);
  }
  .nav-brand {
    font-family:'Orbitron',sans-serif; font-weight:800;
    font-size:1.1rem; letter-spacing:0.04em; font-style:italic;
  }
  .nav-brand em { font-style:italic; color:rgb(0,139,255); }
  .nav-items { display:flex; gap:28px; }
  @media(max-width:768px){ .nav-items{display:none;} }
  .nav-items a {
    color:rgba(255,255,255,0.6); font-size:0.72rem; font-weight:600;
    text-transform:uppercase; letter-spacing:0.12em; cursor:pointer;
    text-decoration:none; transition:color .25s;
  }
  .nav-items a:hover { color:rgb(0,139,255); }
  .nav-right { display:flex; align-items:center; gap:18px; }
  .nav-bell { color:rgba(255,255,255,0.55); cursor:pointer; transition:color .25s; }
  .nav-bell:hover { color:#fff; }
  .nav-avatar {
    width:32px; height:32px; border-radius:50%;
    background:rgb(0,139,255); display:grid; place-items:center;
    font-weight:700; font-size:0.85rem;
    box-shadow:0 0 12px rgba(0,139,255,0.45);
  }

  /* ── Section ── */
  .section { padding:5rem 1.5rem; max-width:1120px; margin:0 auto; position:relative; z-index:2; }
  .section-label {
    display:inline-block; font-size:0.7rem; font-weight:700;
    text-transform:uppercase; letter-spacing:0.18em;
    color:rgb(0,139,255); border:1px solid rgba(0,139,255,0.35);
    padding:5px 14px; border-radius:999px; margin-bottom:1rem;
  }
  .section-h2 {
    font-family:'Orbitron',sans-serif; font-size:clamp(1.6rem,3.5vw,2.2rem);
    font-weight:700; margin-bottom:0.6rem; letter-spacing:0.03em;
  }
  .section-sub { color:rgba(255,255,255,0.55); font-size:0.95rem; max-width:540px; line-height:1.65; margin-bottom:3rem; }

  /* ── Feature cards ── */
  .feat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1.25rem; }
  .feat {
    background:rgba(8,12,22,0.65); border:1px solid rgba(0,139,255,0.12);
    border-radius:14px; padding:28px 22px;
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
    transition:transform .3s, border-color .3s, box-shadow .3s;
  }
  .feat:hover {
    transform:translateY(-4px);
    border-color:rgba(0,139,255,0.5);
    box-shadow:0 8px 32px rgba(0,139,255,0.12);
  }
  .feat-icon {
    width:44px; height:44px; border-radius:10px;
    background:rgba(0,139,255,0.1); display:grid; place-items:center;
    font-size:1.3rem; margin-bottom:16px;
  }
  .feat h3 { font-size:1.05rem; font-weight:600; margin-bottom:8px; }
  .feat p { color:rgba(255,255,255,0.55); font-size:0.88rem; line-height:1.6; }

  /* ── Team ── */
  .team-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1.25rem; }
  .team-card {
    background:linear-gradient(175deg,rgba(12,16,28,0.92),rgba(6,8,16,0.96));
    border:1px solid rgba(0,139,255,0.18); border-radius:14px;
    padding:32px 18px 24px; text-align:center; position:relative;
    transition:transform .3s, border-color .3s;
  }
  .team-card:hover {
    transform:translateY(-4px);
    border-color:rgba(0,139,255,0.6);
    box-shadow:0 8px 28px rgba(0,139,255,0.1);
  }
  .team-pic-ring {
    width:82px; height:82px; border-radius:50%; margin:0 auto 18px;
    padding:3px;
    background:linear-gradient(135deg,rgb(0,139,255),rgba(0,90,180,0.25));
  }
  .team-pic {
    width:100%; height:100%; border-radius:50%;
    background:#111; display:flex; align-items:center; justify-content:center;
    font-size:1.6rem; font-weight:700; color:rgba(0,139,255,0.7);
  }
  .team-name { font-weight:700; font-size:1.05rem; margin-bottom:3px; }
  .team-role { color:rgb(0,139,255); font-size:0.8rem; font-weight:600; margin-bottom:14px; }
  .team-desc { color:rgba(255,255,255,0.4); font-size:0.78rem; line-height:1.45; }

  /* ── Divider ── */
  .divider {
    width:100%; max-width:1120px; margin:0 auto;
    height:1px; background:linear-gradient(90deg,transparent,rgba(0,139,255,0.2),transparent);
  }

  /* ── Scroll hint ── */
  @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(8px)} }
  .scroll-hint {
    position:absolute; bottom:2.5rem; left:50%; transform:translateX(-50%);
    display:flex; flex-direction:column; align-items:center; gap:6px;
    color:#ffffff; font-size:0.7rem; letter-spacing:0.15em;
    text-transform:uppercase; pointer-events:none;
  }
  .scroll-hint svg { stroke:#ffffff; animation:float 2.5s ease-in-out infinite; }

  /* ── Footer ── */
  .footer {
    text-align:center; padding:3rem 1.5rem 2rem; color:rgba(255,255,255,0.25);
    font-size:0.75rem; position:relative; z-index:2;
  }
`

// ============================================================
// Dados da equipe
// ============================================================
const teamMembers = [
  { initials:'AF', name:'Arthur Fernandes',  role:'Fundador', desc:'Qualidade, testes e modelagem de dados' },
  { initials:'AR', name:'Arthur Ramalho',    role:'Fundador', desc:'Design, documentação e planejamento' },
  { initials:'EA', name:'Erick Alves',       role:'Fundador', desc:'Frontend e condução do Scrum' },
  { initials:'FP', name:'Felipe Pedroza',    role:'Fundador', desc:'Banco de dados, ciência de dados e backend' },
  { initials:'GG', name:'Guilherme Gusmão',  role:'Fundador', desc:'Interfaces e identidade visual do produto' },
  { initials:'GC', name:'Gustavo Choueiri',  role:'Fundador', desc:'IA, automações e pipelines de dados' },
  { initials:'VP', name:'Vinícius Pereira',  role:'Fundador', desc:'Frontend e renderização do fluxograma' },
  { initials:'VM', name:'Vitor Marconi',     role:'Fundador', desc:'Fullstack, arquitetura visual e manutenção' },
]

// ============================================================
// Componente principal
// ============================================================
export default function App() {
  const videoRef = useRef(null)
  const [texture, setTexture] = useState(null)

  // ── Cria a textura quando o vídeo estiver pronto (NÃO ALTERE) ──
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    let created = false

    const createTexture = () => {
      if (created) return
      created = true
      console.log('✅ Criando VideoTexture')
      const tex = new THREE.VideoTexture(video)
      tex.minFilter = THREE.LinearFilter
      tex.magFilter = THREE.LinearFilter
      setTexture(tex)
    }

    video.addEventListener('playing', createTexture)

    video.play().then(() => {
      video.playbackRate = 0.03
      createTexture()
    }).catch(() => {
      console.log('⚠️ Autoplay bloqueado — clique na tela para iniciar')
    })

    return () => video.removeEventListener('playing', createTexture)
  }, [])

  const handleClick = () => {
    const video = videoRef.current
    if (video && video.paused) video.play()
  }

  // ────────────────────────────────────────────
  // RENDER
  // ────────────────────────────────────────────
  return (
    <>
      <style>{globalCSS}</style>
      <video
        ref={videoRef}
        autoPlay loop muted playsInline
        crossOrigin="anonymous"
        style={{ display: 'none' }}
      >
        <source src="/video.webm" type="video/webm" />
        <source src="/video.mp4" type="video/mp4" />
      </video>

      {/* ═══ CANVAS FIXO — fundo halftone ═══ */}
      <div style={{ position:'fixed', inset:0, zIndex:0 }} onClick={handleClick}>
        <Canvas
          orthographic
          camera={{ position: [0, 0, 1] }}
          gl={{ antialias: false, alpha: false }}
          style={{ width:'100%', height:'100%', display:'block' }}
        >
          {texture && <VideoPlane videoTexture={texture} settings={settings} />}
        </Canvas>
      </div>

      {/* ═══ CONTEÚDO SCROLLÁVEL ═══ */}
      <div style={{ position:'relative', zIndex:1 }}>

        {/* Navbar */}
        <nav className="nav">
          <div></div>
          <div className="nav-items">
            <a href="#eventos">Eventos</a>
            <a href="#organizer">Smart Organizer</a>
            <a href="#equipe">Equipe</a>
          </div>
          <div className="nav-right">
            <svg className="nav-bell" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            <div className="nav-avatar">TA</div>
          </div>
        </nav>

        {/* ══════ HERO ══════ */}
        <section style={{
          minHeight:'100vh', display:'flex', flexDirection:'column',
          alignItems:'center', justifyContent:'center', position:'relative',
          textAlign:'center', padding:'0 1.5rem',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', textAlign: 'left', width: 'fit-content', maxWidth: '100%', marginBottom: '2.5rem' }}>
            <p style={{
              fontFamily:"'Orbitron',sans-serif", fontWeight:300, fontSize:'0.95rem',
              color:'rgb(255, 255, 255)', letterSpacing:'0.2em', textTransform:'uppercase',
              marginBottom:'0.6rem',
            }}>
              Sejam bem vindos à
            </p>

            <h1 style={{
              fontFamily:"'Orbitron',sans-serif", fontSize:'clamp(2.8rem,8vw,6.5rem)',
              fontWeight:800, letterSpacing:'0.1em', lineHeight:1,
              textTransform:'uppercase',
              textShadow:'0 0 30px rgba(0,139,255,0.45), 0 0 80px rgba(0,139,255,0.15)',
              margin:0,
            }}>
              AGENDA UNB
            </h1>
          </div>

          {/* Botão Login */}
          <button
            style={{
              cursor:'pointer', display:'flex', alignItems:'center', gap:'12px',
              padding:'13px 30px', borderRadius:'999px',
              border:'1px solid rgba(0,139,255,0.35)',
              background:'rgba(0,20,50,0.4)', backdropFilter:'blur(14px)',
              WebkitBackdropFilter:'blur(14px)',
              color:'#fff', fontFamily:"'Inter',sans-serif", fontWeight:500,
              fontSize:'1rem', transition:'all .3s ease',
              boxShadow:'0 4px 24px rgba(0,139,255,0.15)',
            }}
            onMouseOver={e => {
              e.currentTarget.style.background='rgba(0,60,120,0.55)'
              e.currentTarget.style.borderColor='rgba(0,139,255,0.6)'
              e.currentTarget.style.transform='translateY(-2px)'
            }}
            onMouseOut={e => {
              e.currentTarget.style.background='rgba(0,20,50,0.4)'
              e.currentTarget.style.borderColor='rgba(0,139,255,0.35)'
              e.currentTarget.style.transform='translateY(0)'
            }}
          >
            <svg width="22" height="22" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.7 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            Entrar com Google
          </button>

          <div className="scroll-hint">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>
          </div>
        </section>

        {/* Gradiente de transição Hero → seções opacas */}
        <div style={{
          height:'140px',
          background:'linear-gradient(to bottom, transparent 0%, #050508 100%)',
          position:'relative', zIndex:2, marginTop:'-140px',
        }}/>

        {/* ── Fundo opaco para seções abaixo ── */}
        <div style={{ background:'#050508', position:'relative', zIndex:2 }}>

          {/* ══════ MÓDULO A ══════ */}
          <section id="eventos" className="section">
            <div className="section-label">Módulo A</div>
            <h2 className="section-h2">Campus Hub</h2>
            <p className="section-sub">Todos os eventos da universidade em uma agenda unificada — institutos, CAs, DCE, esportes e cultura.</p>

            <div className="feat-grid">
              <div className="feat">
                <div className="feat-icon">📅</div>
                <h3>Agenda Unificada</h3>
                <p>Visualize todos os eventos do campus em um único calendário inteligente, filtrável por categoria, data e instituto.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">✏️</div>
                <h3>Submissão de Eventos</h3>
                <p>Usuários logados podem submeter novos eventos para o campus. Um fluxo simples que vai do rascunho à publicação.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">🛡️</div>
                <h3>Moderação</h3>
                <p>Administradores aprovam ou rejeitam submissões antes da publicação, garantindo a qualidade do conteúdo na agenda.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">🔗</div>
                <h3>Importação Automática</h3>
                <p>Busca e importa eventos de fontes externas como perfis do Instagram, feeds RSS e sites das faculdades.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">🎟️</div>
                <h3>Inscrição Direta</h3>
                <p>Inscreva-se em eventos diretamente pela plataforma com apenas um clique, sem redirecionamentos externos.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">✨</div>
                <h3>Recomendações por IA</h3>
                <p>Receba sugestões personalizadas com base nas suas preferências e no seu histórico de navegação e participação.</p>
              </div>
            </div>
          </section>

          <div className="divider"/>

          {/* ══════ MÓDULO B ══════ */}
          <section id="organizer" className="section">
            <div className="section-label">Módulo B</div>
            <h2 className="section-h2">Smart Organizer</h2>
            <p className="section-sub">Faça upload dos seus planos de ensino e deixe a IA organizar suas datas de provas, trabalhos e entregas.</p>

            <div className="feat-grid">
              <div className="feat">
                <div className="feat-icon">📄</div>
                <h3>Upload de Planos</h3>
                <p>Envie múltiplos planos de ensino nos formatos PDF ou DOCX e deixe o sistema processar automaticamente.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">🧠</div>
                <h3>Extração NLP</h3>
                <p>Algoritmo de processamento de linguagem natural identifica datas, tipos de avaliação e pesos com 85%+ de precisão.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">🗓️</div>
                <h3>Calendário Pessoal</h3>
                <p>Todas as datas extraídas são alocadas em um calendário privado do aluno, pronto para revisar e editar.</p>
              </div>
              <div className="feat">
                <div className="feat-icon">🔔</div>
                <h3>Lembretes Inteligentes</h3>
                <p>Configure alertas personalizados — 1 semana, 3 dias ou 1 dia antes de cada avaliação. Nunca mais perca um prazo.</p>
              </div>
            </div>
          </section>

          <div className="divider"/>

          {/* ══════ EQUIPE ══════ */}
          <section id="equipe" className="section">
            <div className="section-label">Quem somos</div>
            <h2 className="section-h2">A Equipe</h2>
            <p className="section-sub">O time que está tirando a Agenda UnB do papel.</p>

            <div className="team-grid">
              {teamMembers.map((m, i) => (
                <div className="team-card" key={i}>
                  <div className="team-pic-ring">
                    <div className="team-pic">{m.initials}</div>
                  </div>
                  <div className="team-name">{m.name}</div>
                  <div className="team-role">{m.role}</div>
                  <div className="team-desc">{m.desc}</div>
                </div>
              ))}
            </div>
          </section>

          {/* ── Footer ── */}
          <footer className="footer">
            <img src="/Marca-UnB.png" alt="Logo UnB" style={{ width:'70px', marginBottom:'1rem', opacity:0.5 }}/>
            <p>Agenda UnB — Universidade de Brasília © 2025</p>
          </footer>

        </div>
      </div>
    </>
  )
}
