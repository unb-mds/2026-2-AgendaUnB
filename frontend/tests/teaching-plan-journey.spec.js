import { test, expect } from '@playwright/test';
import { confirmation, makeOffer, makePlan, setupSemester } from './fixtures/semester.js';

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
    divergent: false,
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
        divergent: false,
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

test('Nyx brinca com a ampulheta apenas durante o processamento do plano', async ({ page }) => {
  const plan = makePlan(1, { status: 'pendente', authorizationRequired: true, preparedTextAvailable: true, extractedEventsCount: 0 });
  const { data } = await setupSemester(page, { plans: [plan] });
  await page.route(`**/api/v1/syllabus/${plan.id}/text`, route => route.fulfill({
    json: { pages: [{ pagina: 1, texto: 'Prova 1 em 25/11/2026.' }], provider: 'Google Gemini API', providerAvailable: true },
  }));
  await page.route(`**/api/v1/syllabus/${plan.id}/extractions`, route => {
    const next = { ...plan, authorizationRequired: false, status: 'pendente' };
    data.set(plan.id, next);
    return route.fulfill({ status: 202, json: next });
  });
  await page.goto('/plano-de-ensino');
  const toy = page.locator('.pixel-cat-toy');
  await expect(page.locator('.pixel-cat-body')).toBeVisible();
  await expect(page.getByRole('button', { name: /demo/i })).toHaveCount(0);
  await expect(toy).toHaveCount(0);

  await page.getByRole('button', { name: `Extrair avaliações: ${plan.fileName}`, exact: true }).click();
  await page.getByRole('button', { name: 'Iniciar extração', exact: true }).click();
  await expect(toy).toBeVisible();

  data.set(plan.id, { ...plan, authorizationRequired: false, status: 'processando' });
  await expect(toy).toBeVisible({ timeout: 12000 });
  data.set(plan.id, { ...plan, authorizationRequired: false, status: 'concluido', candidates: [] });
  await expect(page.locator('.pixel-cat-body')).toBeVisible({ timeout: 12000 });
  await expect(toy).toHaveCount(0);
});

test('mascote Nyx alterna dicas no estado vazio', async ({ page }) => {
  await setupSemester(page, { offers: [makeOffer(1)], followed: [], plans: [] });
  await page.goto('/plano-de-ensino');
  await page.getByRole('button', { name: /Organizar datas/ }).click();
  await expect(page.getByText('EM BREVE - pergunte ao Nyx')).toBeVisible();
  const initialSpeech = await page.locator('.halftone-pet-speech').textContent();
  await page.getByRole('button', { name: 'Alternar dica do gato Nyx' }).click();
  await expect(page.locator('.halftone-pet-speech')).not.toHaveText(initialSpeech || '');
});

test('novo seguidor importa sem reenviar arquivo, vota com divergência e autor publica, revisa e retira', async ({ page }) => {
  const offer = makeOffer(1);
  const ownPlan = {
    id: 'plan-own',
    userId: 'student-test',
    offeringId: offer.id,
    fileName: 'meu-plano.pdf',
    disciplina: offer.subject_name,
    ano: 2026,
    semestre: 2,
    status: 'concluido',
    extractedEventsCount: 1,
    createdAt: '2026-11-16T09:00:00Z',
    candidates: [
      {
        id: 'cand-own-1',
        title: 'Prova 1 Própria',
        type: 'prova',
        status: 'pendente',
        ambiguous: false,
        ambiguousFields: [],
        suggestedDate: '2026-11-28',
        suggestedTime: '14:00:00',
        sourcePage: 1,
        sourceExcerpt: 'Prova 1 em 28/11/2026 às 14h.',
        versionId: 'ver-own-1',
      },
    ],
  };
  await setupSemester(page, { offers: [offer], followed: [], plans: [ownPlan] });

  let versions = [
    makeSharedVersion({
      id: 'ver-1',
      number: 1,
      author_id: 'author-1',
      author_name: 'Maria Aluna',
      author_role: 'student',
      confirm_count: 1,
      updated_at: '2026-11-16T10:00:00Z',
    }),
    makeSharedVersion({
      id: 'ver-2',
      number: 2,
      author_id: 'prof-1',
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
          confirm_count: 0,
          contest_count: 0,
          divergent: false,
          my_vote: null,
        },
      ],
    }),
  ];
  const confirmCalls = [];
  const revisionCalls = [];
  let sharedOwn = false;

  await page.route('**/api/v1/class-offerings/*/shared-plans?*', route => route.fulfill({
    json: {
      membership_type: 'autodeclarado',
      shared_content_notice: 'Vínculo autodeclarado com a turma. Votação sinaliza divergência sem alterar datas.',
      items: versions,
      total: versions.length,
      limit: 20,
      offset: 0,
    },
  }));
  await page.route('**/api/v1/syllabus/*/versions/*/vote', route => {
    const versionId = route.request().url().split('/').at(-2);
    const { value } = route.request().postDataJSON();
    versions = versions.map(v => v.id !== versionId ? v : {
      ...v,
      confirm_count: value === 'confirm' ? (v.confirm_count || 0) + 1 : v.confirm_count,
      contest_count: value === 'contest' ? (v.contest_count || 0) + 1 : v.contest_count,
      divergent: value === 'contest' || Boolean(v.divergent),
      my_vote: value === 'confirm' ? 'confirma' : 'contesta',
    });
    const updated = versions.find(v => v.id === versionId);
    return route.fulfill({
      json: {
        versionId,
        confirmCount: updated?.confirm_count ?? 1,
        contestCount: updated?.contest_count ?? 0,
        divergent: Boolean(updated?.divergent),
        myVote: value === 'confirm' ? 'confirma' : 'contesta',
      },
    });
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
    if (route.request().method() === 'GET') {
      return route.fulfill({
        json: {
          syllabusId: 'plan-own',
          offeringId: offer.id,
          membershipType: 'autodeclarado',
          sharedContentNotice: 'Vínculo autodeclarado.',
          items: [
            {
              id: 'ver-own-1',
              syllabusId: 'plan-own',
              offeringId: offer.id,
              number: 1,
              visibility: sharedOwn ? 'compartilhada' : 'privada',
              authorId: 'student-test',
              authorRole: 'student',
              sharedContentNotice: 'Vínculo autodeclarado.',
              candidates: [],
            },
          ],
          total: 1,
        },
      });
    }
    const body = route.request().postDataJSON();
    revisionCalls.push(body);
    const created = makeSharedVersion({
      id: 'ver-own-2',
      syllabus_id: 'plan-own',
      number: 2,
      author_id: 'student-test',
      author_name: 'Estudante',
      author_role: 'student',
      source_version_id: body.sourceVersionId,
      source_version_number: 1,
      institutional_provenance: false,
      confirm_count: 5,
      updated_at: '2026-11-16T16:00:00Z',
      can_withdraw: true,
      can_edit: true,
      has_imported_update: true,
      imported_from_version_number: 1,
      candidates: body.candidates.map((item, idx) => ({
        id: `cand-3-${idx}`,
        title: item.title,
        type: item.type,
        starts_at: item.startsAt,
        suggested_date: item.suggestedDate,
        suggested_time: item.suggestedTime,
        ambiguous: false,
        ambiguous_fields: [],
        source_page: item.sourcePage ?? 1,
        source_excerpt: item.sourceExcerpt ?? 'Trecho revisado',
        order: idx,
        imported: false,
        modified_since_import: true,
        confirm_count: 0,
        contest_count: 0,
        divergent: false,
        my_vote: null,
      })),
    });
    versions = [created, ...versions];
    return route.fulfill({ status: 201, json: { id: created.id, syllabusId: 'plan-own', number: 2, visibility: 'compartilhada' } });
  });
  await page.route('**/api/v1/syllabus/*/versions/*/sharing', route => {
    const versionId = route.request().url().split('/').at(-2);
    if (route.request().method() === 'PUT') {
      sharedOwn = true;
      const ownShared = makeSharedVersion({
        id: 'ver-own-1',
        syllabus_id: 'plan-own',
        number: 1,
        author_id: 'student-test',
        author_name: 'Estudante',
        author_role: 'student',
        confirm_count: 4,
        updated_at: '2026-11-16T15:00:00Z',
        can_withdraw: true,
        can_edit: true,
        candidates: [
          {
            id: 'cand-own-1',
            title: 'Prova 1 Própria',
            type: 'prova',
            starts_at: '2026-11-28T14:00:00-03:00',
            suggested_date: '2026-11-28',
            suggested_time: '14:00:00',
            ambiguous: false,
            ambiguous_fields: [],
            source_page: 1,
            source_excerpt: 'Prova 1 em 28/11/2026 às 14h.',
            order: 0,
            imported: false,
            modified_since_import: false,
            confirm_count: 0,
            contest_count: 0,
            divergent: false,
            my_vote: null,
          },
        ],
      });
      versions = [ownShared, ...versions];
      return route.fulfill({ json: { id: versionId, syllabusId: 'plan-own', number: 1, visibility: 'compartilhada' } });
    }
    versions = versions.filter(v => v.id !== versionId);
    return route.fulfill({ json: { id: versionId, syllabusId: 'plan-own', number: 2, visibility: 'privada', withdrawnAt: '2026-11-16T17:00:00Z' } });
  });
  await page.route('**/api/v1/syllabus/*/versions/*/candidates/*', route => {
    const parts = route.request().url().split('/');
    const candidateId = parts.at(-1);
    const versionId = parts.at(-3);
    versions = versions.map(v => v.id !== versionId ? v : {
      ...v,
      candidates: v.candidates.filter(c => c.id !== candidateId),
    });
    return route.fulfill({ status: 204 });
  });

  await page.goto('/plano-de-ensino');
  await page.getByRole('navigation', { name: 'Etapas dos planos de ensino' }).getByRole('button', { name: /Selecionar turmas/ }).click();
  const catalog = page.getByRole('region', { name: 'Catálogo de turmas' });
  await catalog.getByRole('button', { name: 'Buscar turmas', exact: true }).click();
  await catalog.locator('summary').filter({ hasText: 'Disciplina 1' }).click();
  await catalog.getByRole('checkbox', { name: 'Selecionar turma 01 de Disciplina 1' }).check();
  await catalog.getByRole('button', { name: 'Seguir 1 turma selecionada' }).click();
  await page.getByRole('button', { name: 'Avançar para organizar datas' }).first().click();
  await page.getByRole('tab', { name: 'Planos compartilhados da turma' }).click();

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

  // Abre v1 pelo histórico, vota positivamente e contesta -> sinaliza divergência sem alterar data.
  await library.locator('.shared-version-history-list').getByRole('button', { name: 'Abrir versão' }).click();
  await expect(card).toContainText('Versão 1');
  await card.getByRole('button', { name: /Confirmar \(1\)/ }).click();
  await expect(card).toContainText('Versão padrão');
  await card.getByRole('button', { name: /Contestar \(0\)/ }).click();
  await expect(card).toContainText('Divergência sinalizada');

  // Outro estudante seguidor revisa datas de v1 criando nova versão (v2 no mock com maior pontuação), preservando evento importado e sinalizando atualização.
  await card.getByRole('button', { name: 'Revisar datas desta versão' }).click();
  await library.getByLabel('Título').fill('Prova 1 Remarcada');
  await library.getByLabel('Data').fill('2026-12-02');
  await library.getByRole('button', { name: 'Publicar versão revisada' }).click();
  await expect(library.getByText('Alterações disponíveis na Versão 2')).toBeVisible();
  expect(revisionCalls[0]).toMatchObject({ share: true });
  await expect(library.getByText('Atualizado', { exact: true })).toBeVisible();

  // Autor da revisão retira o evento individual e depois retira a versão inteira.
  await card.getByRole('button', { name: 'Ver detalhes de Prova 1 Remarcada' }).click();
  await card.getByRole('button', { name: 'Retirar evento' }).click();
  await card.locator('.semester-candidate-detail').getByRole('button', { name: 'Confirmar retirada' }).click();
  await expect(library.getByText('Evento retirado desta versão compartilhada.')).toBeVisible();

  await card.getByRole('button', { name: 'Retirar versão' }).click();
  await card.locator('.shared-version-toolbar').getByRole('button', { name: 'Confirmar retirada' }).click();
  await expect(library.getByText(/Versão 2 retirada da turma/)).toBeVisible();

  // Autora compartilha voluntariamente o próprio plano privado após listagem vazia/restante.
  await library.getByRole('button', { name: 'Compartilhar com a turma' }).click();
  await library.getByRole('button', { name: 'Confirmar publicação' }).click();
  await expect(card).toContainText('Prova 1 Própria');
});

for (const width of [360, 768, 1365]) for (const theme of ['dark', 'light']) {
  test(`biblioteca compartilhada responsiva ${width}px tema ${theme}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 1000 });
    await setupSemester(page, { offers: [
      { ...makeOffer(1), subject_name: 'Fundamentos de Arquitetura de Computadores' },
      makeOffer(2),
    ] });
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
    const upload = page.getByRole('button', { name: 'Ir para envio de plano', exact: true });
    const openShared = page.getByRole('button', { name: 'Ver planos compartilhados', exact: true });
    await expect(openShared).toBeVisible();
    const [uploadBox, sharedBox] = await Promise.all([upload.boundingBox(), openShared.boundingBox()]);
    expect(sharedBox.width).toBe(uploadBox.width);
    expect(sharedBox.height).toBe(uploadBox.height);
    await openShared.click();
    await expect(page.getByRole('heading', { name: 'Planos compartilhados da turma' })).toBeVisible();
    const picker = page.getByRole('combobox', { name: 'Selecionar turma da biblioteca' });
    const [pickerBox, arrowBox] = await Promise.all([
      picker.boundingBox(), page.locator('.shared-offer-picker .material-symbols-outlined').boundingBox(),
    ]);
    expect(arrowBox.x).toBeGreaterThan(pickerBox.x);
    expect(arrowBox.x + arrowBox.width).toBeLessThan(pickerBox.x + pickerBox.width);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`shared-${width}-${theme}.png`), fullPage: true });
  });
}
