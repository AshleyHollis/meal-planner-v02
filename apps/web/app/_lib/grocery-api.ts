import { api, ApiError } from './api';
import type {
  GroceryLine,
  GroceryList,
  GroceryListStatus,
  GroceryReviewState,
} from './types';

function toNumber(value: unknown): number {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function parseSourceMeals(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((entry): entry is string => typeof entry === 'string');
  }
  if (typeof value === 'string' && value.trim()) {
    return value
      .split('|')
      .flatMap((chunk) => chunk.split(','))
      .map((entry) => entry.trim())
      .filter(Boolean);
  }
  return [];
}

function deriveReviewState(status: GroceryListStatus): GroceryReviewState {
  return status === 'shopping' || status === 'completed' ? 'confirmed' : 'draft';
}

function mapLine(raw: Record<string, unknown>): GroceryLine {
  const sourceMeals = parseSourceMeals(raw.sourceMeals ?? raw.meal_sources);

  return {
    groceryLineId: String(raw.groceryLineId ?? raw.id ?? ''),
    groceryListId: String(raw.groceryListId ?? raw.grocery_list_id ?? ''),
    name: String(raw.name ?? raw.ingredient_name ?? 'Item'),
    quantityNeeded: toNumber(raw.quantityNeeded ?? raw.quantity_needed),
    unit: String(raw.unit ?? 'ea'),
    quantityCoveredByInventory: toNumber(
      raw.quantityCoveredByInventory ?? raw.quantity_offset
    ),
    quantityToBuy: toNumber(raw.quantityToBuy ?? raw.quantity_to_buy),
    origin: (raw.origin ?? 'meal_derived') as GroceryLine['origin'],
    sourceMealIds: Array.isArray(raw.sourceMealIds)
      ? raw.sourceMealIds.filter((entry): entry is string => typeof entry === 'string')
      : [],
    sourceMeals,
    checked: Boolean(raw.checked ?? raw.is_purchased ?? false),
    offsetInventoryItemId: (raw.offsetInventoryItemId ??
      raw.offset_inventory_item_id ??
      null) as string | null,
    userAdjustedQuantity: (raw.userAdjustedQuantity ??
      raw.user_adjusted_quantity ??
      null) as number | null,
    userAdjustmentFlagged: Boolean(
      raw.userAdjustmentFlagged ?? raw.user_adjustment_flagged ?? false
    ),
  };
}

function mapGroceryList(
  raw: Record<string, unknown>,
  planPeriodStart: string
): GroceryList {
  const status = (raw.status ?? 'current') as GroceryListStatus;
  const linesRaw = raw.lines ?? raw.items ?? [];
  const lines = Array.isArray(linesRaw)
    ? linesRaw.map((line) => mapLine(line as Record<string, unknown>))
    : [];

  return {
    groceryListId: String(raw.groceryListId ?? raw.id ?? ''),
    householdId: String(raw.householdId ?? raw.household_id ?? ''),
    planPeriodStart: String(raw.planPeriodStart ?? raw.plan_period_start ?? planPeriodStart),
    lines,
    derivedFromPlanId: (raw.derivedFromPlanId ?? raw.meal_plan_id ?? null) as string | null,
    lastDerivedAt: (raw.lastDerivedAt ?? raw.updated_at ?? null) as string | null,
    isStale: Boolean(raw.isStale ?? false),
    status,
    reviewState: deriveReviewState(status),
    currentVersionNumber: Number(raw.currentVersionNumber ?? raw.current_version_number ?? 1),
  };
}

export async function getGroceryList(
  householdId: string,
  planPeriodStart: string
): Promise<GroceryList | null> {
  try {
    const raw = await api.get<Record<string, unknown>>(
      `/api/v1/households/${householdId}/grocery?period=${planPeriodStart}`
    );
    return mapGroceryList(raw, planPeriodStart);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function checkGroceryLine(
  householdId: string,
  groceryListId: string,
  groceryLineId: string,
  checked: boolean,
  clientMutationId: string
): Promise<void> {
  return api.patch(
    `/api/v1/households/${householdId}/grocery/${groceryListId}/lines/${groceryLineId}`,
    { checked, clientMutationId }
  );
}

export function addAdHocLine(
  householdId: string,
  groceryListId: string,
  name: string,
  quantityNeeded: number,
  unit: string,
  clientMutationId: string
): Promise<void> {
  return api.post(
    `/api/v1/households/${householdId}/grocery/${groceryListId}/lines`,
    {
      grocery_list_id: groceryListId,
      household_id: householdId,
      ingredient_name: name,
      quantity_needed: quantityNeeded,
      unit,
      origin: 'ad_hoc',
      client_mutation_id: clientMutationId,
    }
  );
}
