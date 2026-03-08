import type { AISuggestionStatus, FallbackMode, PlanSlot } from './types';

export function getSuggestionBannerDetail(
  status: AISuggestionStatus,
  fallbackMode: FallbackMode,
  options?: { hasConfirmedPlan?: boolean }
): string | null {
  const confirmedPlanNote = options?.hasConfirmedPlan
    ? ' Your confirmed plan stays active until you explicitly confirm a replacement.'
    : '';

  switch (status) {
    case 'ready':
      return `Review the proposed meals before opening a draft.${confirmedPlanNote}`;
    case 'fallback_used':
      return fallbackMode === 'curated_fallback'
        ? `Some meals came from the planner's curated backup guidance, so review them before opening a draft.${confirmedPlanNote}`
        : `AI could only offer limited manual guidance from the current household context.${confirmedPlanNote}`;
    case 'insufficient_context':
      return `AI could not build a full weekly suggestion from the current household context. Review your meals, inventory, or try again once more planning context is available.${confirmedPlanNote}`;
    case 'failed':
      return `AI suggestions are unavailable right now. Retry when the planner service is reachable.${confirmedPlanNote}`;
    default:
      return confirmedPlanNote.trim() || null;
  }
}

export function getRegenerationFailureMessage(
  slot: Pick<PlanSlot, 'mealTitle' | 'origin' | 'originalSuggestion'>
): string {
  if (slot.origin === 'user_edited' && slot.mealTitle) {
    return 'Could not regenerate this slot. Keeping your last saved meal so you can retry or edit it manually.';
  }

  if (slot.originalSuggestion?.mealTitle) {
    return 'Could not regenerate this slot. Keeping the original AI suggestion so you can retry or edit it manually.';
  }

  if (slot.mealTitle) {
    return 'Could not regenerate this slot. Keeping the current meal so you can retry or edit it manually.';
  }

  return 'Could not regenerate this slot. Retry or edit it manually.';
}

export function getConfirmButtonLabel(hasConfirmedPlan: boolean, confirming: boolean): string {
  if (confirming) {
    return hasConfirmedPlan ? 'Replacing confirmed plan…' : 'Confirming…';
  }

  return hasConfirmedPlan ? 'Replace confirmed plan' : 'Confirm plan';
}
