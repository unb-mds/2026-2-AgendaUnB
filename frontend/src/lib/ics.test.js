import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildIcsCalendar,
  buildIcsEventUid,
  escapeIcsText,
  foldIcsLine,
  formatBrasiliaDateTime,
  formatUtcTimestamp,
} from './ics.js';
import { toUiEvent } from './publicEventsCache.js';

test('escapeIcsText escapa barras, ponto-e-vírgula, vírgulas e quebras de linha conforme RFC 5545', () => {
  const raw = 'Prova 1, Sala S9; trazer caneta\\lápis\r\nLinha 2\nLinha 3';
  assert.equal(
    escapeIcsText(raw),
    'Prova 1\\, Sala S9\\; trazer caneta\\\\lápis\\nLinha 2\\nLinha 3',
  );
});

test('foldIcsLine respeita limite de 75 octetos UTF-8 sem partir caracteres acentuados multibyte', () => {
  const longAccented = 'SUMMARY:Avaliação de Programação Concorrente — Apresentação de Trabalhos Acadêmicos na UnB (Campus Darcy Ribeiro)';
  const folded = foldIcsLine(longAccented);
  const physicalLines = folded.split('\r\n');
  assert.ok(physicalLines.length >= 2);
  const encoder = new TextEncoder();
  const decoder = new TextDecoder('utf-8', { fatal: true });

  for (const [index, line] of physicalLines.entries()) {
    const bytes = encoder.encode(line);
    assert.ok(bytes.length <= 75, `Linha ${index} excedeu 75 octetos: ${bytes.length}`);
    // Garante que nenhum caractere UTF-8 foi truncado no meio
    assert.equal(decoder.decode(bytes), line);
    if (index > 0) {
      assert.ok(line.startsWith(' '), 'Linhas de continuação devem iniciar com espaço');
    }
  }

  const unfolded = physicalLines.map((line, idx) => (idx === 0 ? line : line.slice(1))).join('');
  assert.equal(unfolded, longAccented);
});

test('buildIcsCalendar gera VCALENDAR válido para Apple Calendar e Outlook com prova, trabalho dia inteiro e evento público salvo', () => {
  const fixedNow = new Date('2026-11-18T12:00:00Z');

  const examEvent = toUiEvent({
    id: '11111111-1111-4111-8111-111111111111',
    title: 'Prova 1 de Métodos de Desenvolvimento de Software',
    description: 'Tipo de avaliação: Prova\n\nUnidades 1 a 4, sala Mocap',
    starts_at: '2026-11-20T17:00:00Z',
    ends_at: '2026-11-20T18:50:00Z',
    all_day: false,
    campus: 'Faculdade do Gama (FCTE)',
    category: 'Acadêmico',
    location: 'Sala Mocap',
  }, true);

  const assignmentAllDay = toUiEvent({
    id: '22222222-2222-4222-8222-222222222222',
    title: 'Entrega do Trabalho Final — Relatório Técnico',
    description: 'Tipo de avaliação: Trabalho\n\nEnvio pela plataforma até 23h59',
    starts_at: '2026-11-24T03:00:00Z',
    all_day: true,
    start_date: '2026-11-24',
    end_date: '2026-11-25',
    category: 'Acadêmico',
  }, true);

  const savedMultiDayPublic = {
    ...toUiEvent({
      id: '33333333-3333-4333-8333-333333333333',
      title: 'Semana Universitária UnB 2026',
      description: 'Mostra de cursos, extensão e pesquisa.',
      starts_at: '2026-11-18T03:00:00Z',
      all_day: true,
      start_date: '2026-11-18',
      end_date: '2026-11-21',
      campus: 'Darcy Ribeiro (Plano Piloto)',
      category: 'Extensão',
      location: 'Centro Comunitário Athos Bulcão',
    }, false),
    salvoNaAgenda: true,
  };

  const ics = buildIcsCalendar(
    [examEvent, assignmentAllDay, savedMultiDayPublic],
    { includeDescription: true, now: fixedNow },
  );

  // Deve usar CRLF em todo o arquivo
  assert.ok(ics.endsWith('\r\n'));
  const unfolded = ics.replace(/\r\n /g, '');

  assert.match(unfolded, /BEGIN:VCALENDAR\r\n/);
  assert.match(unfolded, /VERSION:2\.0\r\n/);
  assert.match(unfolded, /BEGIN:VTIMEZONE\r\nTZID:America\/Sao_Paulo\r\n/);
  assert.match(unfolded, /DTSTAMP:20261118T120000Z\r\n/);

  // UID estável por tipo e ID
  assert.equal(buildIcsEventUid(examEvent), 'personal-11111111-1111-4111-8111-111111111111@agendaunb.unb.br');
  assert.equal(buildIcsEventUid(savedMultiDayPublic), 'saved-33333333-3333-4333-8333-333333333333@agendaunb.unb.br');
  assert.match(unfolded, /UID:personal-11111111-1111-4111-8111-111111111111@agendaunb\.unb\.br\r\n/);
  assert.match(unfolded, /UID:saved-33333333-3333-4333-8333-333333333333@agendaunb\.unb\.br\r\n/);

  // Prova com horário em America/Sao_Paulo (17:00Z -> 14:00 BRT, 18:50Z -> 15:50 BRT)
  assert.match(unfolded, /DTSTART;TZID=America\/Sao_Paulo:20261120T140000\r\n/);
  assert.match(unfolded, /DTEND;TZID=America\/Sao_Paulo:20261120T155000\r\n/);
  assert.match(unfolded, /LOCATION:Sala Mocap - Faculdade do Gama \(FCTE\)\r\n/);

  // Trabalho dia inteiro (1 dia: 2026-11-24 -> DTEND exclusivo 2026-11-25)
  assert.match(unfolded, /DTSTART;VALUE=DATE:20261124\r\n/);
  assert.match(unfolded, /DTEND;VALUE=DATE:20261125\r\n/);

  // Evento público salvo de múltiplos dias (18 a 20/11 inclusive -> DTEND exclusivo 20261121)
  assert.match(unfolded, /DTSTART;VALUE=DATE:20261118\r\n/);
  assert.match(unfolded, /DTEND;VALUE=DATE:20261121\r\n/);
  assert.match(unfolded, /DESCRIPTION:Tipo de avaliação: Prova\\n\\nUnidades 1 a 4\\, sala Mocap\r\n/);
});

test('buildIcsCalendar omite DESCRIPTION quando includeDescription=false e usa 1h padrão sem endsAt', () => {
  const singleInstant = toUiEvent({
    id: '44444444-4444-4444-8444-444444444444',
    title: 'Orientação de TCC',
    description: 'Anotação privada',
    starts_at: '2026-11-19T13:00:00Z',
    all_day: false,
  }, true);

  const ics = buildIcsCalendar([singleInstant], {
    includeDescription: false,
    now: '2026-11-18T12:00:00Z',
  });

  assert.equal(formatUtcTimestamp('2026-11-18T12:00:00Z'), '20261118T120000Z');
  assert.equal(formatBrasiliaDateTime('2026-11-19T13:00:00Z'), '20261119T100000');
  assert.match(ics, /DTSTART;TZID=America\/Sao_Paulo:20261119T100000\r\n/);
  assert.match(ics, /DTEND;TZID=America\/Sao_Paulo:20261119T110000\r\n/);
  assert.doesNotMatch(ics, /DESCRIPTION:/);
});
