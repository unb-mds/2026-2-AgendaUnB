import { createCandidateReviewDraft, updateCandidateReviewItem, validateReviewItem } from './syllabusReview.js';

export const reviewKey = (planId, item) => JSON.stringify([planId, item.versionId, item.id]);

export function fieldErrors(item) {
  return validateReviewItem({ ...item, decision: 'selected' }, true);
}

export function needsAttention(item) {
  return item.editable && (Object.keys(fieldErrors(item)).length > 0 || (item.ambiguous && !item.checked));
}

export function mergeReview(plan, schedule, previous) {
  return createCandidateReviewDraft(plan.candidates || [], schedule).map((draft, index) => {
    const candidate = plan.candidates[index];
    const key = reviewKey(plan.id, draft);
    const prior = previous[key];
    const item = {
      ...draft, key, candidate, ambiguous: candidate.ambiguous || candidate.ambiguousFields.length > 0,
      checked: false, selected: false, edits: {}, attention: false, planId: plan.id, offeringId: plan.offeringId,
    };
    if (!item.editable) return item;
    const edited = updateCandidateReviewItem(item, prior?.edits || {}, schedule);
    // Invalidate an evidence acknowledgment if the underlying evidence changed.
    const signature = JSON.stringify(candidate);
    const reviewed = prior?.signature === signature && prior.checked;
    const current = { ...edited, edits: prior?.edits || {}, checked: !!reviewed, signature };
    const attention = needsAttention(current);
    return { ...current, attention, selected: !attention && (prior?.selected ?? true) };
  });
}
