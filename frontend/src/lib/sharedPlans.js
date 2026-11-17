import { fieldErrors, needsAttention } from './semesterReview.js';
import { BRASILIA_UTC_OFFSET, createCandidateReviewDraft, updateCandidateReviewItem, validReviewDate } from './syllabusReview.js';

export function authorRoleLabel(role) {
  if (role === 'professor') return 'Perfil professor';
  if (role === 'admin') return 'Perfil administrador';
  return 'Contribuição de estudante';
}

export function formatVersionTimestamp(value) {
  if (!value) return 'Data não informada';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Data não informada';
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(date);
}

function timestampOf(version) {
  const raw = version?.updated_at || version?.shared_at || version?.created_at;
  if (!raw) return 0;
  const ms = new Date(raw).getTime();
  return Number.isNaN(ms) ? 0 : ms;
}

export function sortSharedVersions(versions) {
  return [...(versions || [])].sort((a, b) => {
    const voteDiff = (b.confirm_count || 0) - (a.confirm_count || 0);
    if (voteDiff !== 0) return voteDiff;
    const timeDiff = timestampOf(b) - timestampOf(a);
    if (timeDiff !== 0) return timeDiff;
    const numberDiff = (b.number || 0) - (a.number || 0);
    if (numberDiff !== 0) return numberDiff;
    return String(a.id || '').localeCompare(String(b.id || ''));
  });
}

export function normalizeSharedCandidate(candidate, versionId) {
  return {
    id: candidate.id,
    title: candidate.title || '',
    type: candidate.type ?? null,
    status: candidate.imported ? 'confirmado' : 'pendente',
    startsAt: candidate.starts_at ?? null,
    suggestedDate: candidate.suggested_date ?? null,
    suggestedTime: candidate.suggested_time ?? null,
    ambiguous: Boolean(candidate.ambiguous),
    ambiguousFields: Array.isArray(candidate.ambiguous_fields) ? [...candidate.ambiguous_fields] : [],
    sourcePage: candidate.source_page ?? null,
    sourceExcerpt: candidate.source_excerpt ?? null,
    versionId: versionId ?? candidate.version_id ?? null,
    imported: Boolean(candidate.imported),
    modifiedSinceImport: Boolean(candidate.modified_since_import),
  };
}

export function buildSharedDrafts(plan, classSchedule, previous = {}) {
  const candidates = (plan?.candidates || []).map(c => normalizeSharedCandidate(c, plan.id));
  const drafts = createCandidateReviewDraft(candidates, classSchedule);
  return drafts.map((draft, index) => {
    const candidate = candidates[index];
    const key = `${plan.id}:${candidate.id}`;
    const prior = previous[key];
    const base = {
      ...draft,
      key,
      candidate,
      ambiguous: candidate.ambiguous || candidate.ambiguousFields.length > 0,
      checked: Boolean(prior?.checked),
      edits: prior?.edits || {},
      imported: candidate.imported,
      modifiedSinceImport: candidate.modifiedSinceImport,
    };
    const edited = updateCandidateReviewItem(
      { ...base, editable: true },
      prior?.edits || {},
      classSchedule,
    );
    const current = {
      ...edited,
      editable: !candidate.imported,
      checked: Boolean(prior?.checked),
    };
    const attention = current.editable ? needsAttention(current) : false;
    const defaultSelected = current.editable && !attention;
    return {
      ...current,
      attention,
      selected: current.editable && !attention && (prior?.selected ?? defaultSelected),
    };
  });
}

export function validateSharedRevisionItem(item) {
  const errors = fieldErrors({ ...item, decision: 'selected' });
  if (!validReviewDate(item.date)) errors.date = 'Informe uma data válida.';
  return errors;
}

export function buildRevisionCandidatesPayload(items) {
  if (!items.length) throw new Error('Mantenha ao menos uma avaliação na versão revisada.');
  return items.map(item => {
    const errors = validateSharedRevisionItem(item);
    if (Object.keys(errors).length) {
      throw new Error(`Corrija os campos de "${item.title || 'avaliação'}" antes de publicar a revisão.`);
    }
    const normalizedType = (item.type || '').toLowerCase();
    const hasTime = Boolean(item.time && item.time.trim());
    const cleanTime = hasTime ? (item.time.length === 5 ? `${item.time}:00` : item.time.slice(0, 8)) : null;
    const startsAt = cleanTime ? `${item.date}T${cleanTime}${BRASILIA_UTC_OFFSET}` : null;
    return {
      candidateId: item.id,
      title: item.title.trim(),
      type: normalizedType,
      suggestedDate: item.date,
      suggestedTime: cleanTime,
      startsAt,
      sourcePage: item.candidate?.sourcePage ?? null,
      sourceExcerpt: item.candidate?.sourceExcerpt ?? null,
      ambiguous: false,
      ambiguousFields: [],
    };
  });
}
