export const THEME_STORAGE_KEY = 'agenda_unb_theme_v1';
export const EVENT_FILTERS_STORAGE_KEY = 'agenda_unb_event_filters_v1';

const DEFAULT_FILTERS = {
  visaoEventos: 'Públicos',
  modoVisualizacao: 'lista',
  searchQuery: '',
  filtroArea: [],
  filtroCampus: [],
  filtroTurno: [],
  filtroDataInicio: '',
  filtroDataFim: '',
};

function normalizeFilterList(value) {
  if (Array.isArray(value)) {
    return [...new Set(
      value
        .filter((item) => typeof item === 'string' && item.trim())
        .map((item) => item.trim()),
    )];
  }
  if (typeof value === 'string' && value.trim()) {
    return [value.trim()];
  }
  return [];
}

function defaultStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function getStoredTheme(storage = defaultStorage()) {
  try {
    const saved = storage?.getItem?.(THEME_STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
  } catch {
    // Ignore storage errors in restricted contexts.
  }
  if (typeof document !== 'undefined' && document.body?.classList?.contains('light')) {
    return 'light';
  }
  return 'dark';
}

export function setStoredTheme(theme, storage = defaultStorage()) {
  const normalized = theme === 'light' ? 'light' : 'dark';
  if (typeof document !== 'undefined' && document.body?.classList) {
    document.body.classList.remove('light', 'dark');
    document.body.classList.add(normalized);
  }
  try {
    storage?.setItem?.(THEME_STORAGE_KEY, normalized);
  } catch {
    // Ignore storage errors in restricted contexts.
  }
  return normalized;
}

export function getStoredEventFilters(storage = defaultStorage()) {
  try {
    const raw = storage?.getItem?.(EVENT_FILTERS_STORAGE_KEY);
    if (!raw) return { ...DEFAULT_FILTERS };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return { ...DEFAULT_FILTERS };
    return {
      visaoEventos: parsed.visaoEventos === 'MEUS' ? 'MEUS' : 'Públicos',
      modoVisualizacao: parsed.modoVisualizacao === 'calendario' ? 'calendario' : 'lista',
      searchQuery: typeof parsed.searchQuery === 'string' ? parsed.searchQuery : '',
      filtroArea: normalizeFilterList(parsed.filtroArea),
      filtroCampus: normalizeFilterList(parsed.filtroCampus),
      filtroTurno: normalizeFilterList(parsed.filtroTurno),
      filtroDataInicio: typeof parsed.filtroDataInicio === 'string' ? parsed.filtroDataInicio : '',
      filtroDataFim: typeof parsed.filtroDataFim === 'string' ? parsed.filtroDataFim : '',
    };
  } catch {
    return { ...DEFAULT_FILTERS };
  }
}

export function setStoredEventFilters(filters, storage = defaultStorage()) {
  const next = {
    visaoEventos: filters?.visaoEventos === 'MEUS' ? 'MEUS' : 'Públicos',
    modoVisualizacao: filters?.modoVisualizacao === 'calendario' ? 'calendario' : 'lista',
    searchQuery: typeof filters?.searchQuery === 'string' ? filters.searchQuery : '',
    filtroArea: normalizeFilterList(filters?.filtroArea),
    filtroCampus: normalizeFilterList(filters?.filtroCampus),
    filtroTurno: normalizeFilterList(filters?.filtroTurno),
    filtroDataInicio: typeof filters?.filtroDataInicio === 'string' ? filters.filtroDataInicio : '',
    filtroDataFim: typeof filters?.filtroDataFim === 'string' ? filters.filtroDataFim : '',
  };
  try {
    storage?.setItem?.(EVENT_FILTERS_STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Ignore storage errors in restricted contexts.
  }
  return next;
}

export function clearStoredEventFilters(storage = defaultStorage()) {
  try {
    storage?.removeItem?.(EVENT_FILTERS_STORAGE_KEY);
  } catch {
    // Ignore storage errors in restricted contexts.
  }
  return { ...DEFAULT_FILTERS };
}
