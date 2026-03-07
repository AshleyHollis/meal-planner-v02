import { api, ApiError } from './api';
import type {
  GroceryConfirmedListBootstrap,
  GroceryIncompleteSlotWarning,
  GroceryLine,
  GroceryList,
  GroceryListStatus,
  GroceryTripState,
  GroceryMealSource,
  SyncAggregateRef,
  SyncConflictDetail,
  SyncConflictSummary,
  SyncMutationOutcome,
  SyncResolutionAction,
  SyncResolutionStatus,
  SyncStatus,
} from './types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

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

function toOptionalNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  return toNumber(value);
}

function normalizeStatus(value: unknown): GroceryListStatus {
  switch (value) {
    case 'no_plan_confirmed':
    case 'deriving':
    case 'draft':
    case 'stale_draft':
    case 'confirming':
    case 'confirmed':
    case 'trip_in_progress':
    case 'trip_complete_pending_reconciliation':
      return value;
    default:
      return 'draft';
  }
}

function normalizeTripState(value: unknown, status?: GroceryListStatus): GroceryTripState {
  switch (value) {
    case 'confirmed_list_ready':
    case 'trip_in_progress':
    case 'trip_complete_pending_reconciliation':
      return value;
    default:
      if (status === 'trip_in_progress') {
        return 'trip_in_progress';
      }
      if (status === 'trip_complete_pending_reconciliation') {
        return 'trip_complete_pending_reconciliation';
      }
      return 'confirmed_list_ready';
  }
}

function toRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function parseAggregate(raw: unknown): SyncAggregateRef {
  const value = toRecord(raw);
  return {
    aggregateType: (value.aggregateType ?? value.aggregate_type ?? 'grocery_list') as SyncAggregateRef['aggregateType'],
    aggregateId: String(value.aggregateId ?? value.aggregate_id ?? ''),
    aggregateVersion: toOptionalNumber(
      value.aggregateVersion ?? value.aggregate_version ?? value.server_version ?? value.current_server_version
    ),
    provisionalAggregateId: (value.provisionalAggregateId ??
      value.provisional_aggregate_id ??
      null) as string | null,
  };
}

function parseSyncStatus(value: unknown): SyncStatus {
  switch (value) {
    case 'queued_offline':
    case 'syncing':
    case 'synced':
    case 'retrying':
    case 'failed_retryable':
    case 'conflict':
    case 'review_required':
    case 'resolving':
    case 'resolved_keep_mine':
    case 'resolved_use_server':
    case 'error':
    case 'offline':
      return value;
    default:
      return 'idle';
  }
}

function parseResolutionActions(value: unknown): SyncResolutionAction[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (entry): entry is SyncResolutionAction => entry === 'keep_mine' || entry === 'use_server'
  );
}

function parseResolutionStatus(value: unknown): SyncResolutionStatus {
  switch (value) {
    case 'resolved_keep_mine':
    case 'resolved_use_server':
      return value;
    default:
      return 'pending';
  }
}

function parseMealSources(value: unknown): GroceryMealSource[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((entry) => {
      if (!isRecord(entry)) {
        return null;
      }

      const mealSlotId = entry.mealSlotId ?? entry.meal_slot_id ?? entry.meal_plan_slot_id;
      if (typeof mealSlotId !== 'string' || mealSlotId.trim().length === 0) {
        return null;
      }

      return {
        mealSlotId,
        mealName:
          typeof (entry.mealName ?? entry.meal_name) === 'string'
            ? String(entry.mealName ?? entry.meal_name)
            : null,
        contributedQuantity: toNumber(
          entry.contributedQuantity ?? entry.contributed_quantity ?? entry.quantity
        ),
      } satisfies GroceryMealSource;
    })
    .filter((entry): entry is GroceryMealSource => entry !== null);
}

function parseIncompleteWarnings(value: unknown): GroceryIncompleteSlotWarning[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((entry) => {
      if (!isRecord(entry)) {
        return null;
      }

      const mealSlotId = entry.mealSlotId ?? entry.meal_slot_id ?? entry.meal_plan_slot_id;
      if (typeof mealSlotId !== 'string' || mealSlotId.trim().length === 0) {
        return null;
      }

      return {
        mealSlotId,
        mealName:
          typeof (entry.mealName ?? entry.meal_name) === 'string'
            ? String(entry.mealName ?? entry.meal_name)
            : null,
        reason: String(entry.reason ?? 'missing_ingredient_data'),
        message:
          typeof entry.message === 'string' && entry.message.trim().length > 0
            ? entry.message
            : null,
      } satisfies GroceryIncompleteSlotWarning;
    })
    .filter((entry): entry is GroceryIncompleteSlotWarning => entry !== null);
}

export function mapLine(raw: Record<string, unknown>): GroceryLine {
  return {
    groceryLineId: String(raw.groceryLineId ?? raw.id ?? ''),
    groceryListId: String(raw.groceryListId ?? raw.grocery_list_id ?? ''),
    groceryListVersionId: String(raw.groceryListVersionId ?? raw.grocery_list_version_id ?? ''),
    name: String(raw.name ?? raw.ingredient_name ?? 'Item'),
    ingredientRefId: (raw.ingredientRefId ?? raw.ingredient_ref_id ?? null) as string | null,
    quantityNeeded: toNumber(raw.quantityNeeded ?? raw.required_quantity),
    unit: String(raw.unit ?? 'ea'),
    quantityCoveredByInventory: toNumber(
      raw.quantityCoveredByInventory ?? raw.offset_quantity
    ),
    quantityToBuy: toNumber(raw.quantityToBuy ?? raw.shopping_quantity),
    origin: (raw.origin ?? 'derived') as GroceryLine['origin'],
    mealSources: parseMealSources(raw.mealSources ?? raw.meal_sources),
    offsetInventoryItemId: (raw.offsetInventoryItemId ??
      raw.offset_inventory_item_id ??
      null) as string | null,
    offsetInventoryItemVersion: (raw.offsetInventoryItemVersion ??
      raw.offset_inventory_item_version ??
      null) as number | null,
    userAdjustedQuantity: toOptionalNumber(
      raw.userAdjustedQuantity ?? raw.user_adjusted_quantity ?? null
    ),
    userAdjustmentNote: (raw.userAdjustmentNote ??
      raw.user_adjustment_note ??
      null) as string | null,
    userAdjustmentFlagged: Boolean(
      raw.userAdjustmentFlagged ?? raw.user_adjustment_flagged ?? false
    ),
    adHocNote: (raw.adHocNote ?? raw.ad_hoc_note ?? null) as string | null,
    active: Boolean(raw.active ?? true),
    createdAt: String(raw.createdAt ?? raw.created_at ?? ''),
    updatedAt: String(raw.updatedAt ?? raw.updated_at ?? ''),
  };
}

export function mapGroceryList(raw: Record<string, unknown>, planPeriodStart = ''): GroceryList {
  const status = normalizeStatus(raw.status);
  const linesRaw = raw.lines ?? raw.items ?? [];
  const lines = Array.isArray(linesRaw)
    ? linesRaw
        .filter((line): line is Record<string, unknown> => isRecord(line))
        .map((line) => mapLine(line))
    : [];

  return {
    groceryListId: String(raw.groceryListId ?? raw.id ?? ''),
    householdId: String(raw.householdId ?? raw.household_id ?? ''),
    planPeriodStart: String(raw.planPeriodStart ?? raw.plan_period_start ?? planPeriodStart),
    planPeriodEnd: (raw.planPeriodEnd ?? raw.plan_period_end ?? null) as string | null,
    lines,
    derivedFromPlanId: (raw.derivedFromPlanId ?? raw.meal_plan_id ?? null) as string | null,
    lastDerivedAt: (raw.lastDerivedAt ?? raw.last_derived_at ?? null) as string | null,
    confirmedAt: (raw.confirmedAt ?? raw.confirmed_at ?? null) as string | null,
    tripState: normalizeTripState(raw.tripState ?? raw.trip_state, status),
    isStale: Boolean(raw.isStale ?? raw.is_stale ?? false),
    status,
    currentVersionNumber: Number(raw.currentVersionNumber ?? raw.current_version_number ?? 1),
    currentVersionId: (raw.currentVersionId ?? raw.current_version_id ?? null) as string | null,
    confirmedPlanVersion: (raw.confirmedPlanVersion ??
      raw.confirmed_plan_version ??
      null) as number | null,
    inventorySnapshotReference: (raw.inventorySnapshotReference ??
      raw.inventory_snapshot_reference ??
      null) as string | null,
    incompleteSlotWarnings: parseIncompleteWarnings(
      raw.incompleteSlotWarnings ?? raw.incomplete_slot_warnings
    ),
  };
}

function unwrapGroceryList(raw: Record<string, unknown>): Record<string, unknown> {
  const nested = raw.groceryList ?? raw.grocery_list;
  return isRecord(nested) ? nested : raw;
}

export function mapSyncMutationOutcome(raw: Record<string, unknown>): SyncMutationOutcome {
  return {
    clientMutationId: String(raw.clientMutationId ?? raw.client_mutation_id ?? ''),
    mutationType: String(raw.mutationType ?? raw.mutation_type ?? ''),
    aggregate: parseAggregate(raw.aggregate),
    outcome: String(raw.outcome ?? 'applied') as SyncMutationOutcome['outcome'],
    authoritativeServerVersion: toOptionalNumber(
      raw.authoritativeServerVersion ?? raw.authoritative_server_version ?? null
    ),
    conflictId: (raw.conflictId ?? raw.conflict_id ?? null) as string | null,
    retryable: Boolean(raw.retryable ?? false),
    duplicateOfClientMutationId: (raw.duplicateOfClientMutationId ??
      raw.duplicate_of_client_mutation_id ??
      null) as string | null,
    autoMergeReason: (raw.autoMergeReason ?? raw.auto_merge_reason ?? null) as string | null,
  };
}

export function mapSyncConflictSummary(raw: Record<string, unknown>): SyncConflictSummary {
  return {
    conflictId: String(raw.conflictId ?? raw.conflict_id ?? ''),
    householdId: String(raw.householdId ?? raw.household_id ?? ''),
    aggregate: parseAggregate(raw.aggregate),
    localMutationId: String(raw.localMutationId ?? raw.local_mutation_id ?? ''),
    mutationType: String(raw.mutationType ?? raw.mutation_type ?? ''),
    outcome: String(raw.outcome ?? 'review_required_other_unsafe') as SyncConflictSummary['outcome'],
    baseServerVersion: toOptionalNumber(raw.baseServerVersion ?? raw.base_server_version ?? null),
    currentServerVersion: toNumber(raw.currentServerVersion ?? raw.current_server_version ?? 0),
    requiresReview: Boolean(raw.requiresReview ?? raw.requires_review ?? true),
    summary: String(raw.summary ?? ''),
    localQueueStatus: parseSyncStatus(raw.localQueueStatus ?? raw.local_queue_status),
    allowedResolutionActions: parseResolutionActions(
      raw.allowedResolutionActions ?? raw.allowed_resolution_actions
    ),
    resolutionStatus: parseResolutionStatus(raw.resolutionStatus ?? raw.resolution_status),
    createdAt: String(raw.createdAt ?? raw.created_at ?? ''),
    resolvedAt: (raw.resolvedAt ?? raw.resolved_at ?? null) as string | null,
    resolvedByActorId: (raw.resolvedByActorId ?? raw.resolved_by_actor_id ?? null) as string | null,
  };
}

export function mapSyncConflictDetail(raw: Record<string, unknown>): SyncConflictDetail {
  const summary = mapSyncConflictSummary(raw);
  return {
    ...summary,
    localIntentSummary: toRecord(raw.localIntentSummary ?? raw.local_intent_summary),
    baseStateSummary: toRecord(raw.baseStateSummary ?? raw.base_state_summary),
    serverStateSummary: toRecord(raw.serverStateSummary ?? raw.server_state_summary),
  };
}

export function mapConfirmedListBootstrap(
  raw: Record<string, unknown>
): GroceryConfirmedListBootstrap {
  const status = normalizeStatus(raw.groceryListStatus ?? raw.grocery_list_status ?? raw.status);
  const linesRaw = raw.lines ?? [];
  return {
    householdId: String(raw.householdId ?? raw.household_id ?? ''),
    groceryListId: String(raw.groceryListId ?? raw.grocery_list_id ?? ''),
    groceryListVersionId: String(raw.groceryListVersionId ?? raw.grocery_list_version_id ?? ''),
    groceryListStatus: status,
    tripState: normalizeTripState(raw.tripState ?? raw.trip_state, status),
    aggregate: parseAggregate(raw.aggregate),
    confirmedAt: String(raw.confirmedAt ?? raw.confirmed_at ?? ''),
    confirmedPlanVersion: toOptionalNumber(
      raw.confirmedPlanVersion ?? raw.confirmed_plan_version ?? null
    ),
    inventorySnapshotReference: (raw.inventorySnapshotReference ??
      raw.inventory_snapshot_reference ??
      null) as string | null,
    incompleteSlotWarnings: parseIncompleteWarnings(
      raw.incompleteSlotWarnings ?? raw.incomplete_slot_warnings
    ),
    lines: Array.isArray(linesRaw)
      ? linesRaw
          .filter((line): line is Record<string, unknown> => isRecord(line))
          .map((line) => mapLine(line))
      : [],
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

export async function deriveGroceryList(
  householdId: string,
  planPeriodStart: string,
  clientMutationId: string
): Promise<GroceryList> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/derive`,
    {
      household_id: householdId,
      plan_period_start: planPeriodStart,
      client_mutation_id: clientMutationId,
    }
  );

  return mapGroceryList(unwrapGroceryList(raw), planPeriodStart);
}

export async function rederiveGroceryList(
  householdId: string,
  groceryListId: string,
  planPeriodStart: string,
  clientMutationId: string
): Promise<GroceryList> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/${groceryListId}/rederive`,
    {
      household_id: householdId,
      plan_period_start: planPeriodStart,
      client_mutation_id: clientMutationId,
    }
  );

  return mapGroceryList(unwrapGroceryList(raw), planPeriodStart);
}

export async function confirmGroceryList(
  householdId: string,
  groceryListId: string,
  clientMutationId: string
): Promise<GroceryList> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/${groceryListId}/confirm`,
    {
      grocery_list_id: groceryListId,
      household_id: householdId,
      client_mutation_id: clientMutationId,
    }
  );

  return mapGroceryList(unwrapGroceryList(raw));
}

export async function addAdHocLine(
  householdId: string,
  groceryListId: string,
  name: string,
  quantityNeeded: number,
  unit: string,
  clientMutationId: string,
  note?: string
): Promise<GroceryList> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/${groceryListId}/lines`,
    {
      grocery_list_id: groceryListId,
      household_id: householdId,
      ingredient_name: name,
      shopping_quantity: quantityNeeded,
      unit,
      ad_hoc_note: note?.trim() ? note.trim() : null,
      client_mutation_id: clientMutationId,
    }
  );

  return mapGroceryList(unwrapGroceryList(raw));
}

export async function adjustGroceryLine(
  householdId: string,
  groceryListId: string,
  groceryLineId: string,
  quantityToBuy: number,
  clientMutationId: string,
  note?: string
): Promise<GroceryList> {
  const raw = await api.patch<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/${groceryListId}/lines/${groceryLineId}`,
    {
      grocery_list_item_id: groceryLineId,
      household_id: householdId,
      user_adjusted_quantity: quantityToBuy,
      user_adjustment_note: note?.trim() ? note.trim() : null,
      client_mutation_id: clientMutationId,
    }
  );

  return mapGroceryList(unwrapGroceryList(raw));
}

export async function removeGroceryLine(
  householdId: string,
  groceryListId: string,
  groceryLineId: string,
  clientMutationId: string
): Promise<GroceryList> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/${groceryListId}/lines/${groceryLineId}/remove`,
    {
      grocery_list_item_id: groceryLineId,
      household_id: householdId,
      client_mutation_id: clientMutationId,
    }
  );

  return mapGroceryList(unwrapGroceryList(raw));
}

export async function uploadSyncMutations(
  householdId: string,
  mutations: Array<{
    client_mutation_id: string;
    household_id: string;
    actor_id: string;
    aggregate_type: string;
    aggregate_id: string | null;
    provisional_aggregate_id: string | null;
    mutation_type: string;
    payload: Record<string, unknown>;
    base_server_version: number | null;
    device_timestamp: string;
    local_queue_status: string;
  }>
): Promise<SyncMutationOutcome[]> {
  const raw = await api.post<Record<string, unknown>[]>(
    `/api/v1/households/${householdId}/grocery/sync/upload`,
    mutations
  );
  return raw.map((entry) => mapSyncMutationOutcome(entry));
}

export async function listSyncConflicts(householdId: string): Promise<SyncConflictSummary[]> {
  const raw = await api.get<Record<string, unknown>[]>(
    `/api/v1/households/${householdId}/grocery/sync/conflicts`
  );
  return raw.map((entry) => mapSyncConflictSummary(entry));
}

export async function getSyncConflict(
  householdId: string,
  conflictId: string
): Promise<SyncConflictDetail> {
  const raw = await api.get<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/sync/conflicts/${conflictId}`
  );
  return mapSyncConflictDetail(raw);
}

export async function resolveSyncConflictKeepMine(
  householdId: string,
  conflictId: string,
  clientMutationId: string,
  baseServerVersion?: number | null
): Promise<GroceryList> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/sync/conflicts/${conflictId}/resolve-keep-mine`,
    {
      conflict_id: conflictId,
      household_id: householdId,
      client_mutation_id: clientMutationId,
      base_server_version: baseServerVersion ?? null,
    }
  );
  return mapGroceryList(unwrapGroceryList(raw));
}

export async function resolveSyncConflictUseServer(
  householdId: string,
  conflictId: string,
  clientMutationId: string
): Promise<GroceryList> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/grocery/sync/conflicts/${conflictId}/resolve-use-server`,
    {
      conflict_id: conflictId,
      household_id: householdId,
      client_mutation_id: clientMutationId,
    }
  );
  return mapGroceryList(unwrapGroceryList(raw));
}
