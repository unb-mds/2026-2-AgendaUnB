import { useState, useMemo, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import NavBar from '../components/NavBar';

const CustomSelect = ({ value, onChange, options, placeholder, dropUp = false, className, wrapperWidth }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} style={{ position: 'relative', width: wrapperWidth || '100%', zIndex: isOpen ? 1000 : 1 }}>
      <div 
        className={className || "custom-input"}
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          cursor: 'pointer', userSelect: 'none'
        }}
      >
        <span style={{ color: value ? 'inherit' : 'var(--text-muted)' }}>
          {value ? options.find(o => o.value === value)?.label : placeholder}
        </span>
        <span className="material-symbols-outlined" style={{ fontSize: '1.2rem', transition: 'transform 0.2s', color: 'var(--text-muted)', transform: isOpen ? (dropUp ? 'rotate(0deg)' : 'rotate(180deg)') : (dropUp ? 'rotate(180deg)' : 'rotate(0deg)') }}>
          {dropUp ? 'expand_less' : 'expand_more'}
        </span>
      </div>
      
      {isOpen && (
        <div className="custom-picker-popup" style={{
          top: dropUp ? 'auto' : 'calc(100% + 8px)',
          bottom: dropUp ? 'calc(100% + 8px)' : 'auto',
          width: '100%', minWidth: '180px', maxHeight: '220px', overflowY: 'auto'
        }}>
          <div 
            onClick={() => { onChange(''); setIsOpen(false); }}
            className={`custom-picker-option ${!value ? 'active' : ''}`}
          >
            {placeholder}
          </div>
          {options.map(opt => (
            <div 
              key={opt.value}
              onClick={() => { onChange(opt.value); setIsOpen(false); }}
              className={`custom-picker-option ${value === opt.value ? 'active' : ''}`}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const CustomDatePicker = ({ value, onChange, placeholder, dropUp = false, className }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const [viewDate, setViewDate] = useState(() => value ? new Date(`${value}T12:00:00`) : new Date());

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const daysInMonth = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 0).getDate();
  const startDay = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1).getDay();
  
  const days = Array(startDay).fill(null).concat(Array.from({length: daysInMonth}, (_, i) => i + 1));
  const weekDays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

  const handleSelectDate = (d) => {
    if (!d) return;
    const yyyy = viewDate.getFullYear();
    const mm = String(viewDate.getMonth() + 1).padStart(2, '0');
    const dd = String(d).padStart(2, '0');
    onChange(`${yyyy}-${mm}-${dd}`);
    setIsOpen(false);
  };

  const changeMonth = (e, offset) => {
    e.stopPropagation();
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + offset, 1));
  };

  const displayValue = value ? value.split('-').reverse().join('/') : '';

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', zIndex: isOpen ? 1000 : 1 }}>
      <div 
        className={className || "custom-input"}
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          cursor: 'pointer', userSelect: 'none'
        }}
      >
        <span style={{ color: value ? 'inherit' : 'var(--text-muted)' }}>{displayValue || placeholder}</span>
        <span className="material-symbols-outlined" style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>calendar_today</span>
      </div>
      
      {isOpen && (
        <div className="custom-picker-popup" style={{
          top: dropUp ? 'auto' : 'calc(100% + 8px)', bottom: dropUp ? 'calc(100% + 8px)' : 'auto',
          width: '280px', padding: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <button type="button" onClick={(e) => changeMonth(e, -1)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: '4px', display: 'flex' }}>
              <span className="material-symbols-outlined">chevron_left</span>
            </button>
            <span style={{ fontWeight: 'bold', textTransform: 'capitalize' }}>
              {viewDate.toLocaleString('pt-BR', { month: 'long', year: 'numeric' })}
            </span>
            <button type="button" onClick={(e) => changeMonth(e, 1)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: '4px', display: 'flex' }}>
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', textAlign: 'center', marginBottom: '8px' }}>
            {weekDays.map(wd => <span key={wd} style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>{wd}</span>)}
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
            {days.map((d, i) => {
              const isSelected = value && d && value === `${viewDate.getFullYear()}-${String(viewDate.getMonth() + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
              const isToday = !value && d === new Date().getDate() && viewDate.getMonth() === new Date().getMonth() && viewDate.getFullYear() === new Date().getFullYear();
              
              let classes = 'custom-picker-option';
              if (isSelected) classes += ' active';
              
              return (
                <div 
                  key={i} 
                  className={classes}
                  onClick={() => handleSelectDate(d)}
                  style={{
                    height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    borderRadius: '8px', cursor: d ? 'pointer' : 'default', padding: 0,
                    border: isToday && !isSelected ? '1px solid var(--accent-color)' : '1px solid transparent',
                    color: !d ? 'transparent' : ''
                  }}
                >
                  {d}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

const CustomTimePicker = ({ value, onChange, placeholder, dropUp = false, className }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const hourRef = useRef(null);
  const minRef = useRef(null);

  const [tempHour, setTempHour] = useState('12');
  const [tempMin, setTempMin] = useState('00');

  useEffect(() => {
    if (value) {
      const [h, m] = value.split(':');
      if (h) setTempHour(h);
      if (m) setTempMin(m);
    }
  }, [value, isOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        hourRef.current?.scrollIntoView({ block: 'center' });
        minRef.current?.scrollIntoView({ block: 'center' });
      }, 10);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const hours = Array.from({length: 24}, (_, i) => String(i).padStart(2, '0'));
  const minutes = Array.from({length: 60}, (_, i) => String(i).padStart(2, '0'));

  const handleHourClick = (h) => {
    setTempHour(h);
    onChange(`${h}:${tempMin}`);
  };

  const handleMinClick = (m) => {
    setTempMin(m);
    onChange(`${tempHour}:${m}`);
  };

  // Esconder barra de rolagem (cross-browser)
  const hideScrollbarStyle = {
    msOverflowStyle: 'none',  // IE and Edge
    scrollbarWidth: 'none',  // Firefox
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', zIndex: isOpen ? 1000 : 1 }}>
      <div 
        className={className || "custom-input"}
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          cursor: 'pointer', userSelect: 'none'
        }}
      >
        <span style={{ color: value ? 'inherit' : 'var(--text-muted)' }}>{value || placeholder}</span>
        <span className="material-symbols-outlined" style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>schedule</span>
      </div>
      
      {isOpen && (
        <div className="custom-picker-popup" style={{
          top: dropUp ? 'auto' : 'calc(100% + 8px)', bottom: dropUp ? 'calc(100% + 8px)' : 'auto',
          width: '240px', padding: '0', overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            padding: '14px 16px', borderBottom: '1px solid var(--border-color)',
            background: 'rgba(0, 139, 255, 0.06)'
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: '1.1rem', color: 'var(--white)' }}>schedule</span>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--white)' }}>
              Selecione o horário
            </span>
          </div>

          {/* Column labels */}
          <div style={{
            display: 'flex', justifyContent: 'space-around', padding: '10px 16px 6px',
            fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)'
          }}>
            <span>Hora</span>
            <span>Minuto</span>
          </div>

          {/* Columns */}
          <div style={{ display: 'flex', gap: '0', height: '220px', padding: '4px 12px 12px' }}>
            <div style={{
              flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '3px',
              paddingRight: '6px', ...hideScrollbarStyle
            }}>
              {hours.map(h => (
                <div
                  key={h} ref={tempHour === h ? hourRef : null}
                  onClick={() => handleHourClick(h)}
                  className="time-picker-item"
                  style={{
                    padding: '8px 0', textAlign: 'center', borderRadius: '10px', cursor: 'pointer',
                    fontSize: '0.95rem', fontWeight: tempHour === h ? 700 : 400,
                    transition: 'all 0.2s',
                    background: tempHour === h ? 'rgba(0, 140, 255, 0.64)' : 'transparent',
                    color: tempHour === h ? 'var(--white)' : 'var(--text-color)',
                    border: tempHour === h ? '1px solid rgba(9, 14, 19, 0.74)' : '1px solid transparent',
                  }}
                >
                  {h}
                </div>
              ))}
            </div>

            {/* Divider */}
            <div style={{
              width: '1px', margin: '8px 0',
              background: 'linear-gradient(to bottom, transparent, var(--border-color), transparent)',
              borderRadius: '2px'
            }}></div>

            <div style={{
              flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '3px',
              paddingLeft: '6px', ...hideScrollbarStyle
            }}>
              {minutes.map(m => (
                <div
                  key={m} ref={tempMin === m ? minRef : null}
                  onClick={() => handleMinClick(m)}
                  className="time-picker-item"
                  style={{
                    padding: '8px 0', textAlign: 'center', borderRadius: '10px', cursor: 'pointer',
                    fontSize: '0.95rem', fontWeight: tempMin === m ? 700 : 400,
                    transition: 'all 0.2s',
                    background: tempMin === m ? 'rgba(0, 140, 255, 0.64)' : 'transparent',
                    color: tempMin === m ? 'var(--white)' : 'var(--text-color)',
                    border: tempMin === m ? '1px solid rgba(9, 14, 19, 0.74)' : '1px solid transparent',
                  }}
                >
                  {m}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      <style>{`
        /* Hack extra para garantir hide scrollbar webkit */
        ::-webkit-scrollbar { width: 0px; background: transparent; }
      `}</style>
    </div>
  );
};

export default function SegundaPagina() {
  const navigate = useNavigate();
  const { user, profile, signOut } = useAuth();
  // --- GERENCIAMENTO DE TEMA LOCAL ---
  const [theme, setTheme] = useState(() => document.body.classList.contains('light') ? 'light' : 'dark');
  
  useEffect(() => {
    document.body.classList.remove('light', 'dark');
    document.body.classList.add(theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');
  const isDark = theme === 'dark';

  // --- ESTADOS DA APLICAÇÃO ---
  const [eventos, setEventos] = useState([
        {
      id: 1,
      titulo: 'Encerramento da 26ª SEMUNI',
      data: '2026-09-25',
      horario: '17:00',
      campus: 'Darcy Ribeiro',
      local: 'Memorial Darcy Ribeiro',
      area: 'Cultura',
      descricao: 'Cerimônia de encerramento da 26ª Semana Universitária da UnB, que teve como tema "Democracia em cena: arte, cultura e pertencimento". Serão apresentados os resultados da semana, premiações de destaques e uma programação cultural de despedida com apresentações de grupos estudantis.',
      linkExterno: 'https://dex.unb.br/semanauniversitaria',
      visibilidade: 'Público',
      criadoPorMim: false
    },
    {
      id: 2,
      titulo: '32º Congresso de Iniciação Científica da UnB',
      data: '2026-09-25',
      horario: '10:00',
      campus: 'Darcy Ribeiro',
      local: 'Centro Comunitário Athos Bulcão',
      area: 'Acadêmico',
      descricao: 'Último dia do 32º Congresso de Iniciação Científica e 23º Congresso de Iniciação Científica do DF. Bolsistas do PIBIC, PIBITI e PIBIC-AF apresentam os resultados de suas pesquisas dos editais 2025/2026 em sessões de pôsteres e comunicações orais. Oportunidade para conhecer a ciência de ponta produzida na UnB e interagir com jovens pesquisadores.',
      linkExterno: 'https://proic.unb.br/',
      visibilidade: 'Público',
      criadoPorMim: false
    },
        {
      id: 3,
      titulo: '18º Encontro Nacional de História Oral',
      data: '2026-10-12',
      horario: '09:00',
      campus: 'Darcy Ribeiro',
      local: 'Campus Darcy Ribeiro',
      area: 'Acadêmico',
      descricao: 'Maior fórum de história oral do Brasil, promovido pela Associação Brasileira de História Oral (ABHO). O tema desta edição é "Oralidades plurais na construção de um futuro de justiça climática". O encontro ocorre de 12 a 16 de outubro e reúne pesquisadores, docentes, estudantes e representantes de movimentos sociais para reflexões sobre memória, narração e escuta.',
      linkExterno: 'https://doity.com.br/abho2026',
      visibilidade: 'Público',
      criadoPorMim: false
    },
    {
      id: 4,
      titulo: 'Conferência: Educar en Cultura Democrática',
      data: '2026-09-28',
      horario: '17:00',
      campus: 'Darcy Ribeiro',
      local: 'Auditório do Instituto de Ciências Sociais (ICS)',
      area: 'Acadêmico',
      descricao: 'Conferência internacional com o Prof. Antoni Santisteban Fernández, catedrático da Universidade Autônoma de Barcelona (UAB). O tema é "Educar en cultura democrática frente al avance de ideologías autoritarias". O evento é organizado pelo Laboratório de Ensino de Sociologia Lélia Gonzalez, com inscrições pelo SIGAA.',
      linkExterno: 'https://sigaa.unb.br/sigaa/public/',
      visibilidade: 'Público',
      criadoPorMim: false
    },
    {
      id: 5,
      titulo: 'Exposição Diapedesis - CAL',
      data: '2026-10-01',
      horario: '08:00',
      campus: 'Darcy Ribeiro',
      local: 'Casa da Cultura da América Latina (SCS Qd. 4)',
      area: 'Cultura',
      descricao: 'Com curadoria de Yana Tamayo, esta exposição apresenta trabalhos do "Grupo Analgesia", composto por pacientes, profissionais de saúde e artistas do Hospital Universitário de Brasília (HUB-UnB). A mostra propõe uma reflexão sobre arte, corpo, saúde e políticas de cuidado, usando a diapedese como metáfora. Visitação gratuita até 17 de outubro.',
      linkExterno: 'https://ddc.dex.unb.br/',
      visibilidade: 'Público',
      criadoPorMim: false
    },
    {
      id: 6,
      titulo: 'Prazo Final - Trancamento Parcial de Matrícula',
      data: '2026-10-09',
      horario: '23:59',
      campus: 'Darcy Ribeiro',
      local: 'Online (SIGAA)',
      area: 'Comunicado',
      descricao: 'Data-limite para realizar o trancamento parcial de matrícula no semestre 2026.2. O procedimento deve ser feito exclusivamente pelo sistema SIGAA. Atenção: após essa data, não será mais possível solicitar trancamento de disciplinas individuais neste período letivo.',
      linkExterno: 'https://sigaa.unb.br/sigaa/public/',
      visibilidade: 'Público',
      criadoPorMim: false
    },
  ]);

  const [visaoEventos, setVisaoEventos] = useState('Públicos');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Estados do Modal
  const [titulo, setTitulo] = useState('');
  const [data, setData] = useState('');
  const [horario, setHorario] = useState('');
  const [campus, setCampus] = useState('');
  const [local, setLocal] = useState('');
  const [area, setArea] = useState('');
  const [descricao, setDescricao] = useState('');
  const [visibilidade, setVisibilidade] = useState('');
  const [linkExterno, setLinkExterno] = useState('');

  // Estados dos Filtros
  const [searchQuery, setSearchQuery] = useState('');
  const [filtroArea, setFiltroArea] = useState('');
  const [filtroCampus, setFiltroCampus] = useState('');
  const [filtroTurno, setFiltroTurno] = useState('');

  // --- DADOS BASE PARA OS DROPDOWNS ---
  const areasOptions = ['Acadêmico', 'Cultura', 'Esporte', 'Extensão', 'Lazer', 'Comunicado'].map(a => ({ label: a, value: a }));
  const campiOptions = ['Darcy Ribeiro', 'FCTE - Gama', 'FCTS - Ceilândia', 'FUP - Planaltina', 'FAL'].map(c => ({ label: c, value: c }));
  const turnoOptions = [
    { label: 'Matutino (06h - 12h)', value: 'Matutino' },
    { label: 'Vespertino (12h - 18h)', value: 'Vespertino' },
    { label: 'Noturno (18h - 06h)', value: 'Noturno' }
  ];
  const visibilidadeOptions = [
    { label: 'Público', value: 'Público' },
    { label: 'Apenas para mim', value: 'Privado' }
  ];

  // --- FUNÇÕES AUXILIARES ---
  const getAreaIcon = (areaName) => {
    switch (areaName) {
      case 'Acadêmico': return 'school';
      case 'Cultura': return 'palette';
      case 'Esporte': return 'sports_soccer';
      case 'Extensão': return 'groups';
      case 'Lazer': return 'celebration';
      case 'Comunicado': return 'campaign';
      default: return 'event';
    }
  };

  const getTurnoByHorario = (horarioStr) => {
    if (!horarioStr) return null;
    const [hora] = horarioStr.split(':').map(Number);
    if (hora >= 6 && hora < 12) return 'Matutino';
    if (hora >= 12 && hora < 18) return 'Vespertino';
    return 'Noturno'; 
  };

  const formatarData = (dataStr) => {
    if (!dataStr) return '';
    const partes = dataStr.split('-');
    if (partes.length !== 3) return dataStr;
    const dataObj = new Date(`${dataStr}T12:00:00`);
    const mes = dataObj.toLocaleString('pt-BR', { month: 'short' }).replace('.', '');
    const diaSemana = dataObj.toLocaleString('pt-BR', { weekday: 'long' }).split('-')[0];
    const diaSemanaCap = diaSemana.charAt(0).toUpperCase() + diaSemana.slice(1);
    const mesCap = mes.charAt(0).toUpperCase() + mes.slice(1);
    return `${diaSemanaCap}, ${partes[2]} ${mesCap}`;
  };

  // --- HANDLERS ---
  const handleAdicionarEvento = (e) => {
    e.preventDefault();
    if (!titulo.trim() || !data || !horario) return;

    const novoEvento = {
      id: Date.now(),
      titulo,
      data,
      horario,
      campus,
      local,
      area,
      descricao,
      visibilidade,
      linkExterno,
      organizadorNome: profile?.nome_completo || user?.user_metadata?.nome_completo || user?.user_metadata?.full_name || user?.user_metadata?.name || user?.email || 'Organizador',
      organizadorFoto: profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture || null,
      criadoPorMim: true
    };

    setEventos([novoEvento, ...eventos]);
    setTitulo(''); setData(''); setHorario(''); setCampus(''); setLocal(''); setArea(''); setDescricao(''); setVisibilidade('Público');
    setIsModalOpen(false);
  };

  const handleRemoverEvento = (idParaRemover) => {
    setEventos(eventos.filter(ev => ev.id !== idParaRemover));
  };

  // --- LÓGICA DE FILTRAGEM ---
  const eventosFiltrados = useMemo(() => {
    return eventos.filter(evento => {
      const matchVisao = visaoEventos === 'Públicos' ? evento.visibilidade === 'Público' : evento.criadoPorMim === true;
      const matchBusca = evento.titulo.toLowerCase().includes(searchQuery.toLowerCase());
      const matchArea = filtroArea ? evento.area === filtroArea : true;
      const matchCampus = filtroCampus ? evento.campus === filtroCampus : true;
      const matchTurno = filtroTurno ? getTurnoByHorario(evento.horario) === filtroTurno : true;
      
      return matchVisao && matchBusca && matchArea && matchCampus && matchTurno;
    });
  }, [eventos, visaoEventos, searchQuery, filtroArea, filtroCampus, filtroTurno]);

  // --- ESTILIZAÇÃO DINÂMICA ---
  const bgColor = isDark ? '#080c16' : '#f0f4f8';
  const cardBg = isDark ? '#1a2235' : '#ffffff';
  const textColor = isDark ? '#ffffff' : '#1a1a2e';
  const textMuted = isDark ? '#94a3b8' : '#64748b';
  const accentColor = '#008bff';
  const borderColor = isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.15)';

  return (
    <div style={{ minHeight: '100vh', backgroundColor: bgColor, color: textColor, paddingBottom: '4rem', transition: 'background-color 0.3s' }}>
      
      <NavBar pageType="second" isDark={isDark} toggleTheme={toggleTheme} />

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '8rem 1.5rem 2rem' }}>
        
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '2.5rem' }}>
          <div className="btn-toggle-group">
            <button 
              onClick={() => setVisaoEventos('Públicos')}
              className={`btn-toggle-item ${visaoEventos === 'Públicos' ? 'active' : ''}`}
            >
              Eventos Públicos
            </button>
            <button 
              onClick={() => setVisaoEventos('MEUS')}
              className={`btn-toggle-item ${visaoEventos === 'MEUS' ? 'active' : ''}`}
            >
            Meus Eventos
            </button>
          </div>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '300px', position: 'relative' }}>
              <span className="material-symbols-outlined" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: textMuted }}>search</span>
              <input
                type="text" placeholder="Busque eventos, comunicados..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%', padding: '16px 20px 16px 48px', borderRadius: '24px',
                  border: `1px solid ${borderColor}`, background: cardBg, color: textColor, fontSize: '1.05rem',
                  boxShadow: isDark ? '0 4px 20px rgba(0,0,0,0.2)' : '0 4px 15px rgba(0,0,0,0.05)', outline: 'none'
                }}
              />
            </div>
            <button
              onClick={() => setIsModalOpen(true)}
              style={{
                padding: '0 24px', borderRadius: '26px', background: accentColor,
                color: '#fff', border: 'none', fontWeight: 600, fontSize: '1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                boxShadow: '0 4px 15px rgba(0, 140, 255, 0.19)', height: '56px'
              }}
            >
              <span className="material-symbols-outlined">add</span>
              Criar Evento
            </button>
          </div>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', zIndex: 11, position: 'relative' }}>
            <span style={{ color: textMuted, fontSize: '0.9rem', fontWeight: 600, marginRight: '4px' }}>Filtros:</span>
            
            <CustomSelect 
              options={areasOptions} value={filtroArea} onChange={setFiltroArea} placeholder="Todas as áreas"
              className="filter-pill" wrapperWidth="fit-content"
            />
            <CustomSelect 
              options={campiOptions} value={filtroCampus} onChange={setFiltroCampus} placeholder="Qualquer campus"
              className="filter-pill" wrapperWidth="fit-content"
            />
            <CustomSelect 
              options={turnoOptions} value={filtroTurno} onChange={setFiltroTurno} placeholder="Qualquer turno"
              className="filter-pill" wrapperWidth="fit-content"
            />

            {(filtroArea || filtroCampus || filtroTurno) && (
              <button 
                onClick={() => { setFiltroArea(''); setFiltroCampus(''); setFiltroTurno(''); }}
                style={{ background: 'transparent', border: 'none', color: accentColor, cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, padding: '8px', marginLeft: 'auto' }}
              >
                Limpar Filtros
              </button>
            )}
          </div>
        </div>

        <h2 style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '1.4rem', marginBottom: '1.5rem', color: isDark ? '#fff' : '#1a1a2e', display: 'flex', alignItems: 'center', gap: '8px' }}>
          {visaoEventos === 'MEUS' ? 'MEUS EVENTOS' : 'EVENTOS PÚBLICOS'}
          <span className="material-symbols-outlined" style={{ color: accentColor, fontSize: '1.4rem' }}>event</span>
        </h2>

        {eventosFiltrados.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 2rem', background: cardBg, borderRadius: '24px', border: `1px dashed ${borderColor}` }}>
            <span className="material-symbols-outlined" style={{ fontSize: '3rem', color: textMuted, marginBottom: '1rem' }}>event_busy</span>
            <h3 style={{ color: textColor, marginBottom: '0.5rem' }}>Nenhum evento encontrado</h3>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
            {eventosFiltrados.map((evento) => (
              <div 
                key={evento.id} 
                className="event-card" 
                onClick={() => navigate(`/evento/${evento.id}`, { state: { evento } })}
                style={{ cursor: 'pointer' }}
              >
                <div className="event-card-icon">
                  <span className="material-symbols-outlined" style={{ color: textColor }} >
                    {getAreaIcon(evento.area)}
                  </span>
                </div>

                <div className="event-card-body">
                  <h3 className="event-card-title">
                    {evento.titulo}
                  </h3>
                  <div className="event-card-date">
                    {formatarData(evento.data)} - {evento.horario}
                  </div>
                  {evento.descricao && (
                    <p className="event-card-desc">
                      {evento.descricao}
                    </p>
                  )}
                  <div className="event-card-footer">
                    {evento.campus && (
                      <span className="event-tag"><span className="material-symbols-outlined" style={{ fontSize: '0.9rem', flexShrink: 0 }}>location_on</span><span className="event-tag-text">{evento.campus}</span></span>
                    )}
                    {evento.local && (
                      <span className="event-tag"><span className="material-symbols-outlined" style={{ fontSize: '0.9rem', flexShrink: 0 }}>meeting_room</span><span className="event-tag-text">{evento.local}</span></span>
                    )}
                  </div>
                </div>

                {evento.criadoPorMim && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoverEvento(evento.id);
                    }} 
                    title="Excluir evento"
                    className="event-card-delete"
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: '1.1rem' }}>delete</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: '3.5rem' }}>
          <Link to="/" style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 22px',
            borderRadius: '999px', background: isDark ? '#1e293b' : '#e2e8f0', color: textColor,
            textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem'
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: '1.2rem' }}>arrow_back</span>
            Voltar para a Página Inicial
          </Link>
        </div>
      </main>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-container">
            <button 
              onClick={() => setIsModalOpen(false)}
              className="modal-close"
            >
              <span className="material-symbols-outlined" style={{ fontSize: '1.5rem' }}>close</span>
            </button>
            <h2 className="modal-title">
              <span className="material-symbols-outlined">event_note</span>
              Novo Evento
            </h2>
            <form onSubmit={handleAdicionarEvento} className="modal-form">
              
              <div>
                <label className="modal-label">TÍTULO DO EVENTO *</label>
                <input type="text" required value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Dê um título breve para o seu evento..." className="custom-input" />
              </div>
              <div>
                <label className="modal-label">DESCRIÇÃO</label>
                <textarea value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Forneça mais detalhes..." className="custom-input" style={{ resize: 'vertical', minHeight: '80px', fontFamily: 'inherit' }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="modal-label">DATA *</label>
                  <CustomDatePicker value={data} onChange={setData} placeholder="dd/mm/aaaa" isDark={isDark} className="custom-input" accentColor={accentColor} cardBg={cardBg} borderColor={borderColor} textColor={textColor} />
                </div>
                <div>
                  <label className="modal-label">HORÁRIO *</label>
                  <CustomTimePicker value={horario} onChange={setHorario} placeholder="-- : --" isDark={isDark} className="custom-input" accentColor={accentColor} cardBg={cardBg} borderColor={borderColor} textColor={textColor} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="modal-label">CAMPUS</label>
                  <CustomSelect options={campiOptions} value={campus} onChange={setCampus} placeholder="Selecione..." isDark={isDark} className="custom-input" accentColor={accentColor} cardBg={cardBg} borderColor={borderColor} textColor={textColor} dropUp={true} />
                </div>
                <div>
                  <label className="modal-label">ÁREA</label>
                  <CustomSelect options={areasOptions} value={area} onChange={setArea} placeholder="Selecione..." isDark={isDark} className="custom-input" accentColor={accentColor} cardBg={cardBg} borderColor={borderColor} textColor={textColor} dropUp={true} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="modal-label">LOCAL EXATO</label>
                  <input type="text" value={local} onChange={(e) => setLocal(e.target.value)} placeholder="Ex: Auditório, S9, MOCAP..." className="custom-input" />
                </div>
                <div>
                  <label className="modal-label">VISIBILIDADE</label>
                  <CustomSelect options={visibilidadeOptions} value={visibilidade} onChange={setVisibilidade} placeholder="Selecione..." isDark={isDark} className="custom-input" accentColor={accentColor} cardBg={cardBg} borderColor={borderColor} textColor={textColor} dropUp={true} />
                </div>
              </div>
              <div>
                <label className="modal-label">LINK EXTERNO</label>
                <input type="text" value={linkExterno} onChange={(e) => setLinkExterno(e.target.value)} placeholder="Ex: https://sigaa.unb.br/..." className="custom-input" />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '1rem' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} style={{ padding: '12px 20px', borderRadius: '16px', background: 'transparent', color: textMuted, border: `1px solid ${borderColor}`, cursor: 'pointer', fontWeight: 600 }}>
                  Cancelar
                </button>
                <button type="submit" style={{ padding: '12px 24px', borderRadius: '16px', background: 'rgba(0, 95, 210, 1)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600, boxShadow: '0 4px 15px rgba(0, 139, 255, 0.3)' }}>
                  Salvar Evento
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}



