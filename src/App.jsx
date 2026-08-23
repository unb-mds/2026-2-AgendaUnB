import { Canvas } from '@react-three/fiber'
import { useRef, useState, useEffect } from 'react'
import * as THREE from 'three'
import VideoPlane from './components/VideoPlane.jsx'

// ============================================================
// ⚙️ CONFIGURAÇÃO DO EFEITO — altere os valores aqui!
// ============================================================
const settings = {
  gridSize: 6,
  dotSize: 0.45,
  contrast: 1.4,
  brightness: 0.0,
  effectStrength: 1.0,
  color: [0.4, 0.2, 0.8],
}

export default function App() {
  const videoRef = useRef(null)
  const [texture, setTexture] = useState(null)

  // Cria a textura quando o vídeo estiver pronto
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

    // Tenta dar play (pode falhar se autoplay for bloqueado)
    video.play().then(() => {
      video.playbackRate = 0.03   // ~1 frame por segundo (em vídeos 30fps)
      createTexture()
    }).catch(() => {
      console.log('⚠️ Autoplay bloqueado — clique na tela para iniciar')
    })

    return () => video.removeEventListener('playing', createTexture)
  }, [])

  // Fallback: se autoplay foi bloqueado, um clique inicia o vídeo
  const handleClick = () => {
    const video = videoRef.current
    if (video && video.paused) {
      video.play()
    }
  }

  return (
    <div onClick={handleClick} style={{ width: '100vw', height: '100vh', cursor: 'pointer' }}>
      <style>{`
        * { margin:0; padding:0; box-sizing:border-box; }
        html, body, #root { width:100%; height:100%; overflow:hidden; background:#000; }
      `}</style>

      <video
        ref={videoRef}
        src="/video.mp4"
        autoPlay loop muted playsInline
        crossOrigin="anonymous"
        style={{ display: 'none' }}
      />

      <Canvas
        orthographic
        camera={{ position: [0, 0, 1] }}
        gl={{ antialias: false, alpha: false }}
        style={{ width: '100%', height: '100%', display: 'block' }}
      >
        {texture && <VideoPlane videoTexture={texture} settings={settings} />}
      </Canvas>

      {/* Overlay do Título */}
      <div style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'left',
        pointerEvents: 'none', // Para não bloquear os cliques no canvas
        justifyContent: 'center',
        pointerEvents: 'none', // O container não bloqueia clique, mas o botão sim
        gap: '1rem',
      }}>
        
        {/* Texto minimalista fino */}
        <p style={{
          fontFamily: "'Orbitron', sans-serif",
          fontWeight: 200,
          fontSize: "1.2rem",
          color: "#7b38ff",
            textShadow: `
                0 0 4px #262424,
                0 0 10px rgba(138, 92, 246, 0.39),
                0 0 25px rgba(124, 58, 237, 0.14)
              `,

          margin: 0,
          paddingTop: 200,
          paddingRight:600,
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
          justifyContent: 'left',
        }}>
          Sejam bem vindos ao
        </p>

        {/* Título Principal */}
        <h1 style={{
          fontFamily: "'Orbitron', sans-serif",
              fontSize: "clamp(3rem, 7vw, 7rem)",
              fontWeight: 600,
              letterSpacing: "0.12em",
              lineHeight: 1,
              textTransform: "uppercase",

              textShadow: `
                0 0 4px #5500ff,
                0 0 10px rgba(138, 92, 246, 0.39),
                0 0 25px rgba(124, 58, 237, 0.14)
              `,

              transform: "scaleX(0.95)",
              transformOrigin: "center",

              margin: 0,
              padding: 0,
        }}>
          AGENDA UNB
        </h1>

        {/* Botão Google Liquid Glass */}
        <button style={{
          pointerEvents: 'auto', // Reativa o clique para o botão
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 28px',
          borderRadius: '30px',
          border: '1px solid rgba(255, 255, 255, 0.25)',
          background: 'rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          color: 'white',
          fontFamily: "'Inter', sans-serif",
          fontWeight: 400,
          fontSize: '18px',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
          transition: 'all 0.3s ease',
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)'
          e.currentTarget.style.transform = 'translateY(-2px)'
          e.currentTarget.style.boxShadow = '0 12px 40px 0 rgba(0, 0, 0, 0.4)'
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 8px 32px 0 rgba(0, 0, 0, 0.3)'
        }}
        >
          {/* SVG do Logo do Google */}
          <svg width="24" height="24" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.7 17.74 9.5 24 9.5z" />
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
          </svg>
          Continuar com o Google
        </button>
      </div>
    </div>
  )
}
