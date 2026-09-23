import { useState } from 'react'
import { Link } from 'react-router-dom'
 export default function SegundaPagina({ theme = 'dark', toggleTheme }) {
  // 1. Estado da lista de eventos (começa com alguns exemplos, mas você pode apagar todos se quiser)
  const [eventos, setEventos] = useState([
   
  ]);

  // 2. Estados para guardar o que o usuário digita no formulário
  const [titulo, setTitulo] = useState('');
  const [data, setData] = useState('');
  const [local, setLocal] = useState('');

  // 3. Função chamada quando o usuário clica em "Adicionar Evento"
  const handleAdicionarEvento = (e) => {
    e.preventDefault();
    if (!titulo.trim()) return; // Não adiciona se o título estiver vazio

    const novoEvento = {
      id: Date.now(), // Cria um ID único baseado no horário atual
      titulo: titulo,
      data: data || 'A definir',
      local: local || 'Campus UnB'
    };

    // Adiciona o novo evento no início da lista
    setEventos([novoEvento, ...eventos]);

    // Limpa os campos do formulário
    setTitulo('');
    setData('');
    setLocal('');
  };

  // (Opcional) Função para excluir um evento
  const handleRemoverEvento = (idParaRemover) => {
    setEventos(eventos.filter(ev => ev.id !== idParaRemover));
  };
  return (
    <div style={{
      minHeight: '100vh',
      padding: '8rem 1.5rem 3rem',
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

      
      <div style={{
        background: theme === 'dark' ? 'rgba(8, 12, 22, 0.75)' : 'rgba(255, 255, 255, 0.85)',
        border: '1px solid rgba(0, 139, 255, 0.25)',
        borderRadius: '16px',
        padding: '2rem 1.5rem',
        textAlign: 'center',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        boxShadow: theme === 'dark' ? '0 10px 40px rgba(0, 0, 0, 0.5)' : '0 10px 30px rgba(0, 0, 0, 0.08)'
      }}>
                {/* Formulário para Adicionar Eventos Manualmente */}
        <form 
          onSubmit={handleAdicionarEvento} 
          style={{
            background: theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(0, 0, 0, 0.03)',
            border: '1px solid rgba(0, 139, 255, 0.25)',
            borderRadius: '12px',
            padding: '1.2rem',
            marginBottom: '2rem',
            textAlign: 'left'
          }}
        >
          <h3 style={{
            fontSize: '1rem',
            fontFamily: "'Orbitron', sans-serif",
            color: 'rgb(0, 139, 255)',
            marginBottom: '1rem'
          }}>
            + Novo Evento
          </h3>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '10px',
            marginBottom: '12px'
          }}>
            <input
              type="text"
              placeholder="Título do Evento (ex: Prova 2)"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              required
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid rgba(0, 139, 255, 0.3)',
                background: theme === 'dark' ? '#0b1120' : '#ffffff',
                color: theme === 'dark' ? '#ffffff' : '#1a1a2e',
                outline: 'none'
              }}
            />

            <input
              type="text"
              placeholder="Data e Horário (ex: 28 Out - 14h)"
              value={data}
              onChange={(e) => setData(e.target.value)}
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid rgba(0, 139, 255, 0.3)',
                background: theme === 'dark' ? '#0b1120' : '#ffffff',
                color: theme === 'dark' ? '#ffffff' : '#1a1a2e',
                outline: 'none'
              }}
            />

            <input
              type="text"
              placeholder="Local (ex: ICC Norte)"
              value={local}
              onChange={(e) => setLocal(e.target.value)}
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid rgba(0, 139, 255, 0.3)',
                background: theme === 'dark' ? '#0b1120' : '#ffffff',
                color: theme === 'dark' ? '#ffffff' : '#1a1a2e',
                outline: 'none'
              }}
            />
          </div>

          <button
            type="submit"
            style={{
              padding: '10px 22px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgb(0, 95, 210), rgb(0, 139, 255))',
              color: '#fff',
              border: 'none',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0, 139, 255, 0.3)'
            }}
          >
            Adicionar Evento
          </button>
        </form>
        {/* Caixa de Eventos*/}
        <h2 style={{
          fontFamily: "'Orbitron', sans-serif",
          color: theme === 'dark' ? '#fff' : '#1a1a2e',
          textAlign: 'left',
          marginBottom: '1.5rem'
        }}>
          Próximos Eventos
        </h2>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          {eventos.map((evento) => (
            <div key={evento.id} style={{
              background: theme === 'dark' ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255, 255, 255, 0.9)',
              border: '1px solid rgba(0, 139, 255, 0.2)',
              borderRadius: '12px',
              padding: '1.2rem',
              textAlign: 'left',
              boxShadow: '0 4px 15px rgba(0, 0, 0, 0.1)'
            }}>
              <h3 style={{ color: 'rgb(0, 139, 255)', marginBottom: '8px', fontSize: '1rem' }}>
                {evento.titulo}
              </h3>
              <p style={{ fontSize: '0.85rem', color: theme === 'dark' ? '#bbb' : '#444', marginBottom: '4px' }}>
              {evento.data}
              </p>
              <p style={{ fontSize: '0.85rem', color: theme === 'dark' ? '#bbb' : '#444', marginBottom: '8px' }}>
               {evento.local}
              </p>
                 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ color: 'rgb(0, 139, 255)', marginBottom: '8px', fontSize: '1rem' }}>
                  {evento.titulo}
                </h3>
                <button
                style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    color: "red"
                  }}
                  onClick={() => handleRemoverEvento(evento.id)} className="delete-btn">
                      <span className="material-symbols-outlined">delete
                          </span>
                </button>
              </div>
            </div>
          ))}
          
        </div>

        {/* Botão de Voltar (mantido no final) */}
        <Link
          to="/"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 20px',
            borderRadius: '999px',
            background: 'linear-gradient(135deg, rgb(0, 95, 210), rgb(0, 139, 255))',
            color: '#fff',
            textDecoration: 'none',
            fontWeight: 600,
            fontSize: '0.8rem',
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
