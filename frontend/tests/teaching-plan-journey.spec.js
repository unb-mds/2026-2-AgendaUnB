import { test, expect } from '@playwright/test';
import { confirmation, makeOffer, setupSemester } from './fixtures/semester.js';

function makeSharedVersion(overrides = {}) {
  return {
    id: 'ver-1',
    syllabus_id: 'plan-1',
    offering_id: 'class-1',
    number: 1,
    author_id: 'author-1',
    author_name: 'Maria Aluna',
    author_role: 'student',
    source_version_id: null,
    source_version_number: null,
    institutional_provenance: false,
    institutional_source_url: null,
    created_at: '2026-11-16T10:00:00Z',
    shared_at: '2026-11-16T10:00:00Z',
    updated_at: '2026-11-16T10:00:00Z',
    confirm_count: 1,
    contest_count: 0,
    my_vote: null,
    is_default: false,
    can_withdraw: false,
    can_edit: true,
    has_imported_update: false,
    imported_from_version_number: null,
    candidates: [
      {
        id: 'cand-1',
        title: 'Prova 1',
        type: 'prova',
        starts_at: '2026-11-25T14:00:00-03:00',
        suggested_date: '2026-11-25',
        suggested_time: '14:00:00',
        ambiguous: false,
        ambiguous_fields: [],
        source_page: 2,
        source_excerpt: 'Prova 1 em 25/11/2026 às 14h.',
        order: 0,
        imported: false,
        modified_since_import: false,
        confirm_count: 1,
        contest_count: 0,
        my_vote: null,
      },
    ],
    ...overrides,
  };
}

test('visitante não vê demonstração e recebe convite para login', async ({ page }) => {
  const calls = [];
  await setupSemester(page, { guest: true });
  page.on('request', req => {
    if (/\/api\/v1\/(class-offerings|syllabus)/.test(req.url())) calls.push(req.url());
  });
  await page.goto('/plano-de-ensino');
  await expect(page.getByRole('heading', { name: 'Entre na sua conta para acessar planos de ensino' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Entrar na conta' })).toHaveAttribute('href', '/?auth=login');
  await expect(page.getByText(/demonstração/i)).toHaveCount(0);
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
  expect(calls).toEqual([]);
});

test('novo seguidor importa sem reenviar arquivo, vota para priorizar e revisa com histórico e retirada', async ({ page }) => {
  const offer = makeOffer(1);
  await setupSemester(page, { offers: [offer], followed: [] });

  let versions = [
    makeSharedVersion({
      id: 'ver-1',
      number: 1,
      author_name: 'Maria Aluna',
      author_role: 'student',
      confirm_count: 1,
      updated_at: '2026-11-16T10:00:00Z',
    }),
    makeSharedVersion({
      id: 'ver-2',
      number: 2,
      author_name: 'Prof. Carlos',
      author_role: 'professor',
      source_version_id: 'ver-1',
      source_version_number: 1,
      institutional_provenance: true,
      institutional_source_url: 'https://fcte.unb.br/plano-1.pdf',
      confirm_count: 1,
      updated_at: '2026-11-16T13:00:00Z',
      candidates: [
        {
          id: 'cand-2',
          title: 'Prova 1',
          type: 'prova',
          starts_at: '2026-11-26T14:00:00-03:00',
          suggested_date: '2026-11-26',
          suggested_time: '14:00:00',
          ambiguous: false,
          ambiguous_fields: [],
          source_page: 2,
          source_excerpt: 'Prova 1 em 26/11/2026 às 14h.',
          order: 0,
          imported: false,
          modified_since_import: false,
        },
      ],
    }),
  ];
  const confirmCalls = [];

  await page.route('**/api/v1/class-offerings/*/shared-plans?*', route => route.fulfill({
    json: { items: versions, total: versions.length, limit: 20, offset: 0 },
  }));
  await page.route('**/api/v1/syllabus/*/versions/*/vote', route => {
    const versionId = route.request().url().split('/').at(-2);
    const { value } = route.request().postDataJSON();
    versions = versions.map(v => v.id !== versionId ? v : {
      ...v,
      confirm_count: value === 'confirm' ? (v.confirm_count || 0) + 1 : v.confirm_count,
      my_vote: value === 'confirm' ? 'confirma' : 'contesta',
    });
    return route.fulfill({ json: { versionId, confirmCount: 2, contestCount: 0, myVote: 'confirma' } });
  });
  await page.route('**/api/v1/syllabus/*/confirm', route => {
    const body = route.request().postDataJSON();
    confirmCalls.push(body);
    versions = versions.map(v => v.id !== body.versionId ? v : {
      ...v,
      candidates: v.candidates.map(c => body.candidates.some(item => item.candidateId === c.id) ? { ...c, imported: true } : c),
    });
    return route.fulfill({ json: confirmation({ id: 'plan-1' }, body.candidates) });
  });
  await page.route('**/api/v1/syllabus/*/versions', route => {
    const body = route.request().postDataJSON();
    const created = makeSharedVersion({
      id: 'ver-3',
      number: 3,
      author_id: 'student-test',
      author_name: 'Estudante',
      author_role: 'student',
      source_version_id: body.sourceVersionId,
      source_version_number: 2,
      institutional_provenance: false,
      confirm_count: 3,
      updated_at: '2026-11-16T16:00:00Z',
      can_withdraw: true,
      has_imported_update: true,
      imported_from_version_number: 2,
      candidates: body.candidates.map((item, idx) => ({
        id: `cand-3-${idx}`,
        title: item.title,
        type: item.type,
        starts_at: item.startsAt,
        suggested_date: item.suggestedDate,
        suggested_time: item.suggestedTime,
        ambiguous: false,
        ambiguous_fields: [],
        source_page: item.sourcePage ?? 2,
        source_excerpt: item.sourceExcerpt ?? 'Trecho revisado',
        order: idx,
        imported: false,
        modified_since_import: true,
      })),
    });
    versions = [created, ...versions];
    return route.fulfill({ status: 201, json: { id: created.id, syllabusId: 'plan-1', number: 3, visibility: 'compartilhada' } });
  });
  await page.route('**/api/v1/syllabus/*/versions/*/sharing', route => {
    const versionId = route.request().url().split('/').at(-2);
    versions = versions.filter(v => v.id !== versionId);
    return route.fulfill({ json: { id: versionId, syllabusId: 'plan-1', number: 3, visibility: 'privada', withdrawnAt: '2026-11-16T17:00:00Z' } });
  });

  await page.goto('/plano-de-ensino');
  await expect(page.getByText('EM BREVE - pergunte ao Nyx')).toBeVisible();
  const initialSpeech = await page.locator('.halftone-pet-speech').textContent();
  await page.getByRole('button', { name: 'Alternar dica do gato Nyx' }).click();
  await expect(page.locator('.halftone-pet-speech')).not.toHaveText(initialSpeech || '');
  await page.getByRole('button', { name: 'Buscar turmas', exact: true }).click();
  const catalog = page.getByRole('region', { name: 'Catálogo de turmas' });
  await catalog.getByRole('button', { name: 'Buscar turmas', exact: true }).click();
  await catalog.locator('summary').filter({ hasText: 'Disciplina 1' }).click();
  await catalog.getByRole('checkbox', { name: 'Selecionar turma 01 de Disciplina 1' }).check();
  await catalog.getByRole('button', { name: 'Seguir 1 turma selecionada' }).click();
  await page.getByRole('button', { name: 'Fechar catálogo', exact: true }).click();

  // Em empate de 1 voto entre v1 e v2, a versão mais recente (v2) aparece como padrão e diferencia perfil professor.
  const library = page.getByRole('region', { name: 'Planos compartilhados da turma' });
  await expect(library).toBeVisible();
  const card = library.locator('.shared-version-card');
  await expect(card).toContainText('Versão 2');
  await expect(card).toContainText('Versão padrão');
  await expect(card).toContainText('Perfil professor');
  await expect(card).toContainText('Origem institucional verificada');
  await expect(library.locator('.shared-version-history-list')).toContainText('Contribuição de estudante');

  // Novo seguidor importa da versão existente sem enviar PDF.
  await library.getByRole('button', { name: 'Importar 1 avaliação para a agenda' }).click();
  await expect(library.getByText('1 avaliação importada para sua agenda.')).toBeVisible();
  expect(confirmCalls[0].versionId).toBe('ver-2');

  // Abre v1 pelo histórico e vota positivamente -> v1 passa a ter 2 votos e vira a versão padrão prioritária!
  await library.locator('.shared-version-history-list').getByRole('button', { name: 'Abrir versão' }).click();
  await expect(card).toContainText('Versão 1');
  await card.getByRole('button', { name: /Confirmar \(1\)/ }).click();
  await expect(card).toContainText('Versão 1');
  await expect(card).toContainText('Versão padrão');

  // Estudante revisa datas criando nova versão (v3), preservando o evento importado e exibindo alerta de atualização.
  await card.getByRole('button', { name: 'Revisar datas desta versão' }).click();
  await library.getByLabel('Título').fill('Prova 1 Remarcada');
  await library.getByLabel('Data').fill('2026-12-02');
  await library.getByRole('button', { name: 'Publicar versão revisada' }).click();
  await expect(library.getByText('Alterações disponíveis na Versão 3')).toBeVisible();
  await expect(library.getByText('Atualizado', { exact: true })).toBeVisible();

  // Autor da revisão retira a própria versão.
  await card.getByRole('button', { name: 'Retirar versão' }).click();
  await card.getByRole('button', { name: 'Confirmar retirada' }).click();
  await expect(library.getByText(/Versão 3 retirada da turma/)).toBeVisible();
});

for (const width of [360, 768, 1365]) for (const theme of ['dark', 'light']) {
  test(`biblioteca compartilhada responsiva ${width}px tema ${theme}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    await setupSemester(page, { offers: [makeOffer(1)], followed: [makeOffer(1)] });
    const sample = [
      makeSharedVersion({
        id: 'ver-1',
        number: 1,
        author_name: 'Prof. Carlos',
        author_role: 'professor',
        institutional_provenance: true,
        confirm_count: 3,
        is_default: true,
        can_withdraw: true,
        has_imported_update: true,
        imported_from_version_number: 1,
      }),
    ];
    await page.route('**/api/v1/class-offerings/*/shared-plans?*', route => route.fulfill({
      json: { items: sample, total: 1, limit: 20, offset: 0 },
    }));
    await page.goto('/plano-de-ensino');
    if (theme === 'light') await page.getByRole('button', { name: /tema/i }).click();
    await expect(page.getByRole('heading', { name: 'Planos compartilhados da turma' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`shared-${width}-${theme}.png`), fullPage: true });
  });
}
