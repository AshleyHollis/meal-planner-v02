import type {
  GroceryLine,
  GroceryList,
  SyncConflictSummary,
  SyncResolutionAction,
} from './types';

export type GroceryReviewSummary = {
  activeLineCount: number;
  removedLineCount: number;
  derivedLineCount: number;
  adHocLineCount: number;
  warningCount: number;
  overrideCount: number;
};

export type ConflictDetailField = {
  key: string;
  label: string;
  value: string;
};

const CONFLICT_OUTCOME_LABELS: Record<SyncConflictSummary['outcome'], string> = {
  applied: 'Applied change',
  duplicate_retry: 'Duplicate retry',
  auto_merged_non_overlapping: 'Auto-merged safely',
  failed_retryable: 'Retry needed',
  review_required_quantity: 'Quantity conflict',
  review_required_deleted_or_archived: 'Removed on server',
  review_required_freshness_or_location: 'Freshness or location conflict',
  review_required_other_unsafe: 'Other unsafe conflict',
};

const CONFLICT_OUTCOME_DESCRIPTIONS: Record<SyncConflictSummary['outcome'], string> = {
  applied: 'This change already applied successfully.',
  duplicate_retry: 'The server already accepted this same change earlier.',
  auto_merged_non_overlapping:
    'The server could safely replay this change without hiding someone else’s update.',
  failed_retryable: 'This change can retry automatically when the connection stabilizes.',
  review_required_quantity:
    'Someone changed the same shopping quantity or completion state on the server.',
  review_required_deleted_or_archived:
    'The item changed locally is no longer active on the server, so the app needs your choice.',
  review_required_freshness_or_location:
    'Freshness or storage details changed on both sides, so the app will not guess.',
  review_required_other_unsafe:
    'The server detected an unsafe stale replay and stopped before overwriting shared state.',
};

const CONFLICT_RESOLUTION_COPY: Record<SyncResolutionAction, string> = {
  keep_mine:
    'Keep mine replays your saved intent against the latest server state instead of discarding it.',
  use_server:
    'Use server accepts the current authoritative copy and clears this saved local change.',
};

const CONFLICT_FIELD_LABELS: Record<string, string> = {
  ingredient_name: 'Item',
  grocery_line_id: 'Shopping line',
  quantity_to_buy: 'Quantity to buy',
  shopping_quantity: 'Shopping quantity',
  quantity_needed: 'Required quantity',
  quantity_remaining: 'Remaining quantity',
  active: 'Still active',
  user_adjustment_note: 'Adjustment note',
  ad_hoc_note: 'Ad hoc note',
  mutation_type: 'Saved change',
  completion_state: 'Completion state',
  storage_location: 'Storage location',
  freshness_basis: 'Freshness basis',
  freshness_date: 'Freshness date',
};

function humanizeConflictKey(key: string): string {
  const normalized = key.trim().replaceAll('-', '_');
  if (normalized.length === 0) {
    return 'Detail';
  }

  return normalized
    .split('_')
    .filter((part) => part.length > 0)
    .map((part, index) =>
      index === 0 ? `${part[0]?.toUpperCase() ?? ''}${part.slice(1)}` : part
    )
    .join(' ');
}

export function getConflictOutcomeLabel(outcome: SyncConflictSummary['outcome']): string {
  return CONFLICT_OUTCOME_LABELS[outcome];
}

export function getConflictOutcomeDescription(outcome: SyncConflictSummary['outcome']): string {
  return CONFLICT_OUTCOME_DESCRIPTIONS[outcome];
}

export function getConflictResolutionActionLabel(action: SyncResolutionAction): string {
  return action === 'keep_mine' ? 'Keep mine' : 'Use server';
}

export function getConflictResolutionActionCopy(action: SyncResolutionAction): string {
  return CONFLICT_RESOLUTION_COPY[action];
}

export function getConflictDetailFields(summary: Record<string, unknown>): ConflictDetailField[] {
  return Object.entries(summary).map(([key, value]) => ({
    key,
    label: CONFLICT_FIELD_LABELS[key] ?? humanizeConflictKey(key),
    value: formatConflictDetailValue(value),
  }));
}

export function formatConflictDetailValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return 'Unknown';
  }

  if (Array.isArray(value)) {
    return value.map((entry) => formatConflictDetailValue(entry)).join(', ');
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.00$/, '');
  }

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  return String(value);
}

export function getEffectiveQuantity(line: GroceryLine): number {
  return line.userAdjustedQuantity ?? line.quantityToBuy;
}

export function hasQuantityOverride(line: GroceryLine): boolean {
  return line.userAdjustedQuantity !== null;
}

export function getMealTraceLabel(line: GroceryLine): string | null {
  const meals = line.mealSources
    .map((source) => source.mealName ?? `Meal slot ${source.mealSlotId}`)
    .filter((value, index, values) => values.indexOf(value) === index);

  return meals.length > 0 ? `From ${meals.join(', ')}` : null;
}

export function getActiveLines(list: GroceryList): GroceryLine[] {
  return list.lines.filter((line) => line.active);
}

export function getRemovedLines(list: GroceryList): GroceryLine[] {
  return list.lines.filter((line) => !line.active);
}

export function getReviewSummary(list: GroceryList): GroceryReviewSummary {
  const activeLines = getActiveLines(list);

  return {
    activeLineCount: activeLines.length,
    removedLineCount: getRemovedLines(list).length,
    derivedLineCount: activeLines.filter((line) => line.origin === 'derived').length,
    adHocLineCount: activeLines.filter((line) => line.origin === 'ad_hoc').length,
    warningCount: list.incompleteSlotWarnings.length,
    overrideCount: activeLines.filter((line) => hasQuantityOverride(line)).length,
  };
}

export function getConfirmationSummary(list: GroceryList): string {
  const summary = getReviewSummary(list);
  const parts = [`${summary.activeLineCount} shopping line${summary.activeLineCount === 1 ? '' : 's'}`];

  if (summary.adHocLineCount > 0) {
    parts.push(`${summary.adHocLineCount} ad hoc`);
  }

  if (summary.overrideCount > 0) {
    parts.push(`${summary.overrideCount} override${summary.overrideCount === 1 ? '' : 's'}`);
  }

  return parts.join(' • ');
}

export function getReviewHeadline(list: GroceryList): string {
  const summary = getReviewSummary(list);

  if (list.status === 'stale_draft' || list.isStale) {
    return 'This draft is stale. Review changes before confirming.';
  }

  if (summary.warningCount > 0) {
    return 'Some meals could not fully derive grocery needs.';
  }

  if (summary.overrideCount > 0) {
    return 'User quantity overrides are active on this draft.';
  }

  return 'Review the draft before confirming it for shopping.';
}
