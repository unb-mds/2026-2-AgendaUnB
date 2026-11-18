import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clearStoredEventFilters,
  EVENT_FILTERS_STORAGE_KEY,
  getStoredEventFilters,
  getStoredTheme,
  setStoredEventFilters,
  setStoredTheme,
  THEME_STORAGE_KEY,
} from './preferences.js';

function createMemoryStorage() {
  const store = new Map();
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => { store.set(key, String(value)); },
    removeItem: (key) => { store.delete(key); },
  };
}

test('persiste e recupera tema dark e light com fallback seguro', () => {
  const storage = createMemoryStorage();
  assert.equal(getStoredTheme(storage), 'dark');

  setStoredTheme('light', storage);
  assert.equal(storage.getItem(THEME_STORAGE_KEY), 'light');
  assert.equal(getStoredTheme(storage), 'light');

  setStoredTheme('valor-invalido', storage);
  assert.equal(getStoredTheme(storage), 'dark');
});

test('persiste, recupera e limpa filtros úteis da agenda ignorando JSON inválido', () => {
  const storage = createMemoryStorage();
  storage.setItem(EVENT_FILTERS_STORAGE_KEY, '{corrompido');
  assert.deepEqual(getStoredEventFilters(storage), {
    visaoEventos: 'Públicos',
    modoVisualizacao: 'lista',
    searchQuery: '',
    filtroArea: '',
    filtroCampus: '',
    filtroTurno: '',
    filtroDataInicio: '',
    filtroDataFim: '',
  });

  setStoredEventFilters(
    {
      visaoEventos: 'MEUS',
      modoVisualizacao: 'calendario',
      searchQuery: 'semana',
      filtroArea: 'Cultura',
      filtroCampus: 'Faculdade do Gama (FCTE)',
      filtroTurno: 'Vespertino',
      filtroDataInicio: '2026-11-18',
      filtroDataFim: '2026-11-22',
    },
    storage,
  );

  assert.deepEqual(getStoredEventFilters(storage), {
    visaoEventos: 'MEUS',
    modoVisualizacao: 'calendario',
    searchQuery: 'semana',
    filtroArea: 'Cultura',
    filtroCampus: 'Faculdade do Gama (FCTE)',
    filtroTurno: 'Vespertino',
    filtroDataInicio: '2026-11-18',
    filtroDataFim: '2026-11-22',
  });

  clearStoredEventFilters(storage);
  assert.equal(getStoredEventFilters(storage).filtroCampus, '');
  assert.equal(getStoredEventFilters(storage).visaoEventos, 'Públicos');
});
