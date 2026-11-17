import { useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from './ManagementUI';

const TIPS = [
  'EM BREVE - pergunte ao Nyx',
  'Provas sem horário no PDF recebem automaticamente o horário da sua turma no catálogo.',
  'Trabalhos e entregas sem horário entram como dia inteiro na sua agenda.',
  'Você também pode importar datas já revisadas por colegas na biblioteca da turma abaixo.',
];

// Grade em pixels (cada unidade do viewBox = 1 pixel da arte).
const WIDTH = 50;
const HEIGHT = 49;
const CX = 25; // coluna central do corpo
const mirror = col => 2 * CX - col;

// Silhueta frontal sentada: [linha, meia-largura a partir do centro].
const BODY_HALF_WIDTHS = [
  [5, 7], // arco entre as orelhas
  [6, 8], [7, 8], [8, 8], [9, 8], // parte superior da cabeça
  [10, 9], [11, 9], [12, 9], [13, 9], // bochechas
  [14, 8], [15, 7], [16, 6], // queixo arredondado
  [17, 5], [18, 5], [19, 6], // pescoço definido
  [20, 7], [21, 8], [22, 8], [23, 8], // ombros
  [24, 9], [25, 9], [26, 9], [27, 9], [28, 9], [29, 9], [30, 9], // tronco vertical
  [31, 10], [32, 10], [33, 10], [34, 10], [35, 10], [36, 10], [37, 10], [38, 10], // quadris
  [39, 9], [40, 9], [41, 8], [42, 8], [43, 7], // quadris curvam para dentro
  [44, 6], [45, 5], // patinhas dianteiras no centro
];

// Orelhas pontudas com borda externa reta (linhas 0–5, lado esquerdo; o direito é espelhado).
const LEFT_EAR_SPANS = [[0, 17, 18], [1, 17, 19], [2, 17, 20], [3, 17, 21], [4, 17, 22], [5, 17, 22]];
const LEFT_EAR_INNER = [[1, 18], [2, 18], [2, 19], [3, 18], [3, 19], [3, 20], [4, 19], [4, 20], [4, 21]];

const key = (x, y) => `${x},${y}`;

function classify(filled) {
  const grid = new Map();
  filled.forEach(k => {
    const [x, y] = k.split(',').map(Number);
    const edge = [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => !filled.has(key(x + dx, y + dy)));
    grid.set(k, edge ? 'o' : 'k');
  });
  return grid;
}

function setIfInterior(grid, x, y, code) {
  if (grid.get(key(x, y)) === 'k') grid.set(key(x, y), code);
}

function toRects(grid) {
  const rects = [];
  for (let y = 0; y < HEIGHT; y += 1) {
    let x = 0;
    while (x < WIDTH) {
      const code = grid.get(key(x, y));
      if (!code) { x += 1; continue; }
      let end = x + 1;
      while (end < WIDTH && grid.get(key(end, y)) === code) end += 1;
      rects.push({ key: `${x}-${y}-${code}`, x, y, w: end - x, code });
      x = end;
    }
  }
  return rects;
}

function buildBody() {
  const filled = new Set();
  BODY_HALF_WIDTHS.forEach(([y, half]) => {
    for (let x = CX - half; x <= CX + half; x += 1) filled.add(key(x, y));
  });
  LEFT_EAR_SPANS.forEach(([y, from, to]) => {
    for (let x = from; x <= to; x += 1) {
      filled.add(key(x, y));
      filled.add(key(mirror(x), y));
    }
  });

  const grid = classify(filled);

  LEFT_EAR_INNER.forEach(([y, x]) => {
    setIfInterior(grid, x, y, 'i');
    setIfInterior(grid, mirror(x), y, 'i');
  });

  // Luz suave vinda do alto à esquerda: cabeça e quadril esquerdo.
  [[19, 7], [20, 7], [21, 7], [19, 8], [20, 8]].forEach(([x, y]) => setIfInterior(grid, x, y, 'h'));
  for (let y = 32; y <= 38; y += 1) {
    setIfInterior(grid, 16, y, 'h');
    if (y >= 33 && y <= 37) setIfInterior(grid, 17, y, 'h');
  }

  // Patas dianteiras discretas e divisão central das patinhas apoiadas.
  for (let y = 31; y <= 43; y += 1) {
    setIfInterior(grid, CX - 4, y, 's');
    setIfInterior(grid, CX + 4, y, 's');
  }
  for (let y = 36; y <= 44; y += 1) setIfInterior(grid, CX, y, 's');
  grid.set(key(CX, 45), 'o');

  // Nariz pequeno.
  [[24, 14], [25, 14], [26, 14], [25, 15]].forEach(([x, y]) => grid.set(key(x, y), 'n'));

  // Bigodes encostados nas bochechas.
  [[11, 12], [12, 12], [13, 12], [14, 12], [15, 12], [12, 14], [13, 14], [14, 14], [15, 14], [16, 14]].forEach(([x, y]) => {
    grid.set(key(x, y), 'w');
    grid.set(key(mirror(x), y), 'w');
  });

  // Sombra no chão acompanhando a base compacta das patas.
  for (let x = 16; x <= 34; x += 1) grid.set(key(x, 46), 'f');
  for (let x = 19; x <= 31; x += 1) grid.set(key(x, 47), 'f');

  return toRects(grid);
}

// Cauda: curva Bézier cúbica saindo do quadril, subindo pela esquerda e curvando a ponta.
function buildTail([p0, p1, p2, p3]) {
  const filled = new Set();
  for (let t = 0; t <= 1; t += 0.005) {
    const u = 1 - t;
    const x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0];
    const y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1];
    const r = 2.1 - t * 0.7;
    for (let px = Math.floor(x - r); px <= Math.ceil(x + r); px += 1) {
      for (let py = Math.floor(y - r); py <= Math.ceil(y + r); py += 1) {
        if (px < 0 || py < 0) continue;
        if ((px + 0.5 - x) ** 2 + (py + 0.5 - y) ** 2 <= r * r) filled.add(key(px, py));
      }
    }
  }
  return toRects(classify(filled));
}

const BODY_RECTS = buildBody();
const TAIL_POSES = [
  [[16, 40], [4, 42], [4, 29], [9, 24]],
  [[16, 40], [4, 42], [3, 29], [7, 24]],
  [[16, 40], [4, 42], [3, 30], [5, 25]],
  [[16, 40], [4, 42], [3, 29], [7, 24]],
].map(buildTail);

const EYES = [20, 30]; // colunas centrais dos olhos

export default function HalftonePet({ mode = 'idle' }) {
  const stageRef = useRef(null);
  const [lookStep, setLookStep] = useState(0);
  const [tailIdx, setTailIdx] = useState(0);
  const [blinking, setBlinking] = useState(false);
  const [chirpIndex, setChirpIndex] = useState(0);
  const [excited, setExcited] = useState(false);

  const reducedMotion = () => typeof window === 'undefined'
    || window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;

  useEffect(() => {
    if (reducedMotion()) return undefined;
    const handleMove = event => {
      const rect = stageRef.current?.getBoundingClientRect();
      if (!rect) return;
      const dx = event.clientX - (rect.left + rect.width / 2);
      setLookStep(dx < -45 ? -1 : dx > 45 ? 1 : 0);
    };
    window.addEventListener('pointermove', handleMove, { passive: true });
    return () => window.removeEventListener('pointermove', handleMove);
  }, []);

  useEffect(() => {
    if (reducedMotion()) return undefined;
    const id = setInterval(() => setTailIdx(current => (current + 1) % TAIL_POSES.length),
      excited || mode === 'processing' ? 180 : 420);
    return () => clearInterval(id);
  }, [excited, mode]);

  useEffect(() => {
    if (reducedMotion()) return undefined;
    let closeTimer;
    const cycle = setInterval(() => {
      setBlinking(true);
      closeTimer = setTimeout(() => setBlinking(false), 160);
    }, 4800);
    return () => { clearInterval(cycle); clearTimeout(closeTimer); };
  }, []);

  useEffect(() => {
    if (!excited) return undefined;
    const timer = setTimeout(() => setExcited(false), 620);
    return () => clearTimeout(timer);
  }, [excited]);

  const statusText = useMemo(() => {
    if (mode === 'awaiting_auth') return 'Texto pronto: revise e autorize o plano na fila ao lado.';
    if (mode === 'processing') return 'Analisando seu plano em segundo plano…';
    if (mode === 'filtered') return 'Nenhuma avaliação neste filtro. Alterne para "Todas" para ver o restante.';
    return TIPS[chirpIndex % TIPS.length];
  }, [mode, chirpIndex]);

  const step = mode === 'awaiting_auth' ? -1 : lookStep;

  const interact = () => {
    setExcited(true);
    setChirpIndex(current => (current + 1) % TIPS.length);
  };

  const renderRects = rects => rects.map(rect => (
    <rect key={rect.key} x={rect.x} y={rect.y} width={rect.w} height={1} className={`pixel-cat-${rect.code}`} />
  ));

  return (
    <div ref={stageRef} className={`halftone-pet-stage is-${mode}${excited ? ' is-excited' : ''}`}>
      <div className="halftone-pet-canvas-wrap">
        <svg
          className="halftone-pet-svg"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          shapeRendering="crispEdges"
          aria-hidden="true"
          focusable="false"
        >
          <g className="pixel-cat-tail">{renderRects(TAIL_POSES[tailIdx])}</g>
          <g className="pixel-cat-body">{renderRects(BODY_RECTS)}</g>
          <g className="pixel-cat-eyes">
            {EYES.map(cx => (blinking ? (
              <rect key={cx} x={cx - 2} y={12} width={5} height={1} className="pixel-cat-eye-top" />
            ) : (
              <g key={cx}>
                <rect x={cx - 1} y={10} width={3} height={1} className="pixel-cat-eye-top" />
                <rect x={cx - 2} y={11} width={5} height={2} className="pixel-cat-eye-iris" />
                <rect x={cx - 1} y={13} width={3} height={1} className="pixel-cat-eye-glow" />
                <rect x={cx + step} y={10} width={1} height={3} className="pixel-cat-eye-pupil" />
                <rect x={cx - 1 + step} y={11} width={1} height={1} className="pixel-cat-eye-glint" />
              </g>
            )))}
          </g>
        </svg>

        <button
          type="button"
          className="halftone-pet-trigger"
          onClick={interact}
          aria-label="Alternar dica do gato Nyx"
        >
          <Icon>auto_awesome</Icon>
          <span>Dica do Nyx</span>
        </button>
      </div>

      <p className="halftone-pet-speech">
        {statusText === TIPS[0] ? <strong>{statusText}</strong> : <><strong>Nyx:</strong> {statusText}</>}
      </p>
    </div>
  );
}
