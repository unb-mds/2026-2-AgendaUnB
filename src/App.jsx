import { Canvas } from '@react-three/fiber'
import { useRef, useState, useEffect } from 'react'
import * as THREE from 'three'
import VideoPlane from './components/VideoPlane.jsx'

const getSettings = (theme) => ({
  gridSize: 7,
  dotSize: 0.18,
  contrast: theme === 'dark' ? 1.4 : 800,
  brightness: theme === 'dark' ? -0.1 : 1,
  effectStrength: 1.5,
  color: theme === 'dark' ? [0, 0.547, 1] : [0, 0.547, 1],
  bgColor: theme === 'dark' ? [0.02, 0.02, 0.03] : [1, 1, 1],
})

// ............................
//  CSS
// ............................
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
  .section-sub { color:rgba(255,255,255,0.55); font-size:0.95rem; max-width:570px; line-height:1.65; margin-bottom:3rem; }

  /* ── Feature cards ── */
  .feat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1.25rem; }
  .feat {
    text-align: justify;
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
    background:rgba(0,139,255,0.1); border:1px solid rgba(0,139,255,0.25);
    display:grid; place-items:center;
    color:rgb(0,139,255); margin-bottom:16px;
  }
  .feat-icon .material-symbols-outlined {
    font-size:1.4rem;
  }
  .feat h3 { font-size:1.05rem; font-weight:600; margin-bottom:8px; }
  .feat p { color:rgba(255,255,255,0.55); font-size:0.88rem; line-height:1.6; }

  /* ── Team ── */
  .team-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1.25rem; }
  .team-card {
    background:linear-gradient(175deg,rgba(12,16,28,0.92),rgba(6,8,16,0.96));
    border:1px solid rgba(0,139,255,0.18); border-radius:14px;
    padding:28px 20px 24px; text-align:center; position:relative;
    transition:transform .3s, border-color .3s;
    display:flex; flex-direction:column; align-items:center;
  }
  .team-card:hover {
    transform:translateY(-4px);
    border-color:rgba(0,139,255,0.6);
    box-shadow:0 8px 28px rgba(0,139,255,0.1);
  }
  .team-pic-ring {
    width:82px; height:82px; border-radius:50%; margin:0 auto 16px;
    padding:3px;
    background:linear-gradient(135deg,rgb(0,139,255),rgba(0,90,180,0.25));
  }
  .team-pic {
    width:100%; height:100%; border-radius:50%;
    background:#111; display:flex; align-items:center; justify-content:center;
    font-size:1.4rem; font-weight:700; color:rgba(0,139,255,0.85);
    overflow:hidden;
  }
  .team-name { font-weight:700; font-size:1.02rem; margin-bottom:4px; line-height:1.3; }
  .team-role {
    color:rgb(0,139,255); font-size:0.75rem; font-weight:700;
    text-transform:uppercase; letter-spacing:0.1em;
    background:rgba(0,139,255,0.1); padding:3px 10px; border-radius:999px;
    border:1px solid rgba(0,139,255,0.25);
    margin-bottom:14px;
  }
  .team-links {
    display:flex; flex-direction:column; gap:6px; margin-top:auto;
    width:100%; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);
  }
  .team-link-item {
    display:flex; align-items:center; justify-content:center; gap:6px;
    font-size:0.75rem; color:rgba(255,255,255,0.55);
    text-decoration:none; transition:color .2s;
  }
  .team-link-item:hover { color:rgb(0,139,255); }

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

  /* ── Modal ── */
  .modal-overlay {
    position: fixed; inset: 0; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(2, 6, 16, 0.85);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    z-index: 99999; display: flex; justify-content: center; align-items: center;
    padding: 20px; animation: fadeIn 0.25s ease-out;
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.97); }
    to { opacity: 1; transform: scale(1); }
  }
  .modal-box {
    background: linear-gradient(180deg, rgba(10, 18, 36, 0.95) 0%, rgba(5, 9, 20, 0.98) 100%);
    border: 1px solid rgba(0, 139, 255, 0.35);
    border-radius: 20px;
    width: 100%; max-width: 520px;
    padding: 44px 36px 36px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 35px rgba(0, 139, 255, 0.2);
    position: relative; color: #fff;
  }
  .modal-close {
    position: absolute; top: 18px; right: 18px;
    width: 34px; height: 34px; border-radius: 50%;
    background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.7); display: flex; justify-content: center; align-items: center;
    cursor: pointer; transition: all 0.2s; font-size: 14px;
  }
  .modal-close:hover {
    background: rgba(0, 139, 255, 0.2); border-color: rgba(0, 139, 255, 0.5); color: #fff;
  }
  .modal-input-group { margin-bottom: 18px; text-align: left; }
  .modal-label {
    display: block; font-size: 0.78rem; font-weight: 600;
    color: rgba(255, 255, 255, 0.8); text-transform: uppercase; letter-spacing: 0.05em;
    margin-bottom: 6px;
  }
  .modal-input {
    width: 100%; padding: 13px 16px; border-radius: 10px;
    border: 1px solid rgba(0, 139, 255, 0.25);
    background: rgba(0, 15, 35, 0.6); color: #fff;
    font-size: 0.92rem; font-family: 'Inter', sans-serif; outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .modal-input::placeholder { color: rgba(255, 255, 255, 0.35); }
  .modal-input:focus {
    border-color: rgba(0, 139, 255, 0.8);
    box-shadow: 0 0 12px rgba(0, 139, 255, 0.3);
  }
  .modal-btn-primary {
    width: 100%; padding: 14px; margin-top: 8px; margin-bottom: 16px;
    background: linear-gradient(135deg, rgb(0, 139, 255), rgba(0, 95, 210, 1));
    color: #fff; border: none; border-radius: 10px;
    font-weight: 600; font-size: 0.95rem; font-family: 'Inter', sans-serif;
    cursor: pointer; box-shadow: 0 4px 20px rgba(0, 139, 255, 0.35);
    transition: all 0.25s ease;
  }
  .modal-btn-primary:hover {
    background: linear-gradient(135deg, rgb(30, 155, 255), rgb(0, 120, 240));
    box-shadow: 0 6px 25px rgba(0, 139, 255, 0.5);
    transform: translateY(-1px);
  }
  .modal-divider {
    display: flex; align-items: center; gap: 12px;
    color: rgba(255, 255, 255, 0.35); font-size: 0.78rem; text-transform: uppercase;
    letter-spacing: 0.08em; margin: 16px 0;
  }
  .modal-divider::before, .modal-divider::after {
    content: ''; flex: 1; height: 1px; background: rgba(255, 255, 255, 0.1);
  }
  .modal-btn-google {
    width: 100%; padding: 12px; background: rgba(255, 255, 255, 0.05);
    color: #fff; border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 10px;
    font-weight: 500; font-size: 0.9rem; font-family: 'Inter', sans-serif;
    cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 10px;
    transition: all 0.25s ease; backdrop-filter: blur(8px);
  }
  .modal-btn-google:hover {
    background: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.3);
  }
  .nav-btn-account {
    cursor: pointer; background: rgba(0, 139, 255, 0.15);
    border: 1px solid rgba(0, 139, 255, 0.4); color: #fff;
    padding: 7px 18px; border-radius: 999px; font-weight: 600; font-size: 0.82rem;
    font-family: 'Inter', sans-serif; transition: all 0.25s ease;
    box-shadow: 0 0 12px rgba(0, 139, 255, 0.2);
  }
  .nav-btn-account:hover {
    background: rgba(0, 139, 255, 0.35); border-color: rgba(0, 139, 255, 0.7);
    box-shadow: 0 0 20px rgba(0, 139, 255, 0.4); transform: translateY(-1px);
  }

  /* ── Theme Toggle ── */
  .theme-toggle {
    width: 36px; height: 36px; border-radius: 50%;
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15);
    color: rgba(255, 255, 255, 0.7); display: grid; place-items: center;
    cursor: pointer; transition: all 0.25s; font-size: 1.1rem;
  }
  .theme-toggle:hover {
    background: rgba(0, 139, 255, 0.2); border-color: rgba(0, 139, 255, 0.5); color: #fff;
  }

  /* ── Light Theme ── */
  body.light, body.light #root {
    background: #f5f6fa; color: #1a1a2e;
  }
  body.light ::-webkit-scrollbar-thumb { background: rgba(0, 139, 255, 0.5); }

  body.light .nav {
    background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(14px);
    border-color: rgba(0, 139, 255, 0.2);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
  }
  body.light .nav-items a { color: rgba(26, 26, 46, 0.6); }
  body.light .nav-items a:hover { color: rgb(0, 139, 255); }
  body.light .nav-bell { color: rgba(26, 26, 46, 0.5); }
  body.light .nav-bell:hover { color: #1a1a2e; }
  body.light .nav-avatar { background: rgb(0, 139, 255); color: #fff; }
  body.light .nav-btn-account {
    background: rgba(0, 139, 255, 0.1); border-color: rgba(0, 139, 255, 0.35); color: #1a1a2e;
  }
  body.light .nav-btn-account:hover {
    background: rgba(0, 139, 255, 0.25); border-color: rgba(0, 139, 255, 0.6);
  }
  body.light .theme-toggle {
    background: rgba(0, 0, 0, 0.06); border-color: rgba(0, 0, 0, 0.12); color: #555;
  }
  body.light .theme-toggle:hover {
    background: rgba(0, 139, 255, 0.15); border-color: rgba(0, 139, 255, 0.4); color: rgb(0, 139, 255);
  }

  body.light .section-label { color: rgb(0, 139, 255); border-color: rgba(0, 139, 255, 0.35); }
  body.light .section-h2 { color: #1a1a2e; }
  body.light .section-sub { color: rgba(26, 26, 46, 0.6); }

  body.light .feat {
    background: rgba(255, 255, 255, 0.85); border-color: rgba(0, 139, 255, 0.15);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  }
  body.light .feat:hover {
    border-color: rgba(0, 139, 255, 0.5);
    box-shadow: 0 8px 32px rgba(0, 139, 255, 0.1);
  }
  body.light .feat h3 { color: #1a1a2e; }
  body.light .feat p { color: rgba(26, 26, 46, 0.6); }

  body.light .team-card {
    background: linear-gradient(175deg, rgba(255, 255, 255, 0.95), rgba(245, 246, 250, 0.98));
    border-color: rgba(0, 139, 255, 0.18);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  }
  body.light .team-card:hover {
    border-color: rgba(0, 139, 255, 0.6);
    box-shadow: 0 8px 28px rgba(0, 139, 255, 0.1);
  }
  body.light .team-pic { background: #e8eaef; color: rgba(0, 139, 255, 0.85); }
  body.light .team-name { color: #1a1a2e; }
  body.light .team-links { border-top-color: rgba(0, 0, 0, 0.08); }
  body.light .team-link-item { color: rgba(26, 26, 46, 0.55); }
  body.light .team-link-item:hover { color: rgb(0, 139, 255); }

  body.light .divider { background: linear-gradient(90deg, transparent, rgba(0, 139, 255, 0.25), transparent); }
  body.light .footer { color: rgba(26, 26, 46, 0.35); }

  body.light .scroll-hint { color: #1a1a2e; }
  body.light .scroll-hint svg { stroke: #1a1a2e; }

  body.light .modal-overlay { background: rgba(245, 246, 250, 0.85); }
  body.light .modal-box {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(245, 246, 250, 0.99));
    border-color: rgba(0, 139, 255, 0.3); color: #1a1a2e;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15), 0 0 35px rgba(0, 139, 255, 0.1);
  }
  body.light .modal-close {
    background: rgba(0, 0, 0, 0.05); border-color: rgba(0, 0, 0, 0.1); color: rgba(0, 0, 0, 0.6);
  }
  body.light .modal-close:hover {
    background: rgba(0, 139, 255, 0.15); border-color: rgba(0, 139, 255, 0.4); color: rgb(0, 139, 255);
  }
  body.light .modal-label { color: rgba(26, 26, 46, 0.75); }
  body.light .modal-input {
    background: rgba(0, 0, 0, 0.03); border-color: rgba(0, 139, 255, 0.2); color: #1a1a2e;
  }
  body.light .modal-input::placeholder { color: rgba(26, 26, 46, 0.35); }
  body.light .modal-input:focus {
    border-color: rgba(0, 139, 255, 0.7); box-shadow: 0 0 12px rgba(0, 139, 255, 0.2);
  }
  body.light .modal-divider { color: rgba(26, 26, 46, 0.3); }
  body.light .modal-divider::before, body.light .modal-divider::after { background: rgba(0, 0, 0, 0.1); }
  body.light .modal-btn-google {
    background: rgba(0, 0, 0, 0.04); border-color: rgba(0, 0, 0, 0.15); color: #1a1a2e;
  }
  body.light .modal-btn-google:hover {
    background: rgba(0, 0, 0, 0.08); border-color: rgba(0, 0, 0, 0.25);
  }
`

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
  const videoRef = useRef(null)
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [texture, setTexture] = useState(null)
  const [theme, setTheme] = useState('dark')

  const settings = getSettings(theme)

  // Sincroniza a classe do body com o tema
  useEffect(() => {
    document.body.classList.remove('light', 'dark')
    document.body.classList.add(theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    let created = false

    const createTexture = () => {
      if (created) return
      created = true
      console.log('Criando VideoTexture')
      const tex = new THREE.VideoTexture(video)
      tex.minFilter = THREE.LinearFilter
      tex.magFilter = THREE.LinearFilter
      setTexture(tex)
    }

    video.addEventListener('playing', createTexture)

    video.play().then(() => {
      video.playbackRate = 0.03
      createTexture()
    })
    return () => video.removeEventListener('playing', createTexture)
  }, [])

  const handleClick = () => {
    const video = videoRef.current
    if (video && video.paused) video.play()
  }

  // ............................
  // RENDER
  // ............................
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
              Criar Conta
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

              {/* Campos do Formulário */}
              <div className="modal-input-group">
                <label className="modal-label">Nome Completo <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="text" placeholder="Seu nome completo" className="modal-input" />
              </div>

              <div className="modal-input-group">
                <label className="modal-label">Email <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="email" placeholder="seu@email.com" className="modal-input" />
              </div>

              <div className="modal-input-group">
                <label className="modal-label">Senha <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="password" placeholder="Mínimo 8 caracteres" className="modal-input" />
              </div>

              <div className="modal-input-group">
                <label className="modal-label">Confirmar Senha <span style={{color: 'rgb(0, 139, 255)'}}>*</span></label>
                <input type="password" placeholder="Mínimo 8 caracteres" className="modal-input" />
              </div>


              <button className="modal-btn-primary">
                Criar Conta
              </button>

              <div className="modal-divider">ou</div>

              <button className="modal-btn-google">
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
          </div>
        {/* HERO */}
        <section style={{
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
              Sejam bem vindos à
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
                <p>Administradores aprovam ou rejeitam submissões antes da publicação, garantindo a qualidade do conteúdo na agenda.</p>
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
            <img src="/Marca-UnB.png" alt="Logo UnB" style={{ width:'70px', marginBottom:'1rem', opacity:0.5 }}/>
            <p>Agenda UnB — Universidade de Brasília © 2026</p>
          </footer>

        </div>
    </> 
  )
}
