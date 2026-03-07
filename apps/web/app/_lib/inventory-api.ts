import { api } from './api';
import type {
  FreshnessBasis,
  FreshnessInfo,
  InventoryAdjustment,
  InventoryCorrectionLinks,
  InventoryFreshnessTransition,
  InventoryHistoryPage,
  InventoryHistorySummary,
  InventoryItem,
  InventoryItemDetail,
  InventoryLocationTransition,
  InventoryMutationRequest,
  InventoryQuantityTransition,
  InventoryWorkflowReference,
  MutationReceipt,
  StorageLocation,
} from './types';

type ApiFreshness = {
  basis?: FreshnessBasis;
  best_before?: string | null;
  estimated_note?: string | null;
};

type ApiQuantityTransition = {
  before?: number | string | null;
  after?: number | string | null;
  delta?: number | string | null;
  unit?: string | null;
  changed?: boolean;
};

type ApiLocationTransition = {
  before?: StorageLocation | null;
  after?: StorageLocation | null;
  changed?: boolean;
};

type ApiFreshnessTransition = {
  before?: ApiFreshness | null;
  after?: ApiFreshness | null;
  changed?: boolean;
};

type ApiWorkflowReference = {
  correlation_id?: string | null;
  causal_workflow_id?: string | null;
  causal_workflow_type?: string | null;
};

type ApiCorrectionLinks = {
  corrects_adjustment_id?: string | null;
  corrected_by_adjustment_ids?: string[];
  is_correction?: boolean;
  is_corrected?: boolean;
};

type ApiAdjustment = {
  inventory_adjustment_id?: string;
  inventory_item_id?: string;
  household_id?: string;
  mutation_type?: InventoryMutationRequest['mutationType'];
  delta_quantity?: number | string | null;
  quantity_before?: number | string | null;
  quantity_after?: number | string | null;
  storage_location_before?: StorageLocation | null;
  storage_location_after?: StorageLocation | null;
  freshness_before?: ApiFreshness | null;
  freshness_after?: ApiFreshness | null;
  reason_code?:
    | 'manual_create'
    | 'manual_edit'
    | 'manual_count_reset'
    | 'shopping_apply'
    | 'shopping_skip_or_reduce'
    | 'cooking_consume'
    | 'leftovers_create'
    | 'spoilage_or_discard'
    | 'location_move'
    | 'correction'
    | 'system_replay_duplicate';
  actor_user_id?: string;
  correlation_id?: string | null;
  client_mutation_id?: string | null;
  causal_workflow_id?: string | null;
  causal_workflow_type?: string | null;
  corrects_adjustment_id?: string | null;
  note?: string | null;
  created_at?: string;
  primary_unit?: string | null;
  quantity_transition?: ApiQuantityTransition | null;
  location_transition?: ApiLocationTransition | null;
  freshness_transition?: ApiFreshnessTransition | null;
  workflow_reference?: ApiWorkflowReference | null;
  correction_links?: ApiCorrectionLinks | null;
};

type ApiHistorySummary = {
  committed_adjustment_count?: number;
  correction_count?: number;
  latest_adjustment_id?: string | null;
  latest_mutation_type?: InventoryMutationRequest['mutationType'] | null;
  latest_actor_user_id?: string | null;
  latest_created_at?: string | null;
};

type ApiInventoryItem = {
  id?: string;
  inventory_item_id?: string;
  household_id?: string;
  name?: string;
  storage_location?: StorageLocation;
  quantity_on_hand?: number | string;
  primary_unit?: string;
  freshness_basis?: FreshnessBasis;
  freshness?: ApiFreshness;
  expiry_date?: string | null;
  estimated_expiry_date?: string | null;
  freshness_note?: string | null;
  freshness_updated_at?: string | null;
  is_active?: boolean;
  version?: number;
  updated_at?: string;
  history_summary?: ApiHistorySummary | null;
  latest_adjustment?: ApiAdjustment | null;
};

type ApiInventoryListResponse = {
  items?: ApiInventoryItem[];
};

type ApiInventoryHistoryResponse = {
  entries?: ApiAdjustment[];
  total?: number;
  limit?: number;
  offset?: number;
  has_more?: boolean;
  summary?: ApiHistorySummary | null;
};

type ApiAdjustmentReceipt = {
  inventory_adjustment_id?: string;
  inventory_item_id?: string;
  mutation_type?: InventoryMutationRequest['mutationType'];
  quantity_after?: number | string | null;
  version_after?: number;
  is_duplicate?: boolean;
  result_summary?: string;
};

function toNumber(value: number | string | null | undefined): number {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function isoDate(value: string | null | undefined): string | null {
  return value ?? null;
}

function mapFreshnessInfo(freshness: ApiFreshness | null | undefined): FreshnessInfo | null {
  if (!freshness) {
    return null;
  }

  return {
    basis: freshness.basis ?? 'unknown',
    bestBefore: freshness.best_before ?? null,
    estimatedNote: freshness.estimated_note ?? null,
  };
}

function mapQuantityTransition(
  transition: ApiQuantityTransition | null | undefined
): InventoryQuantityTransition | null {
  if (!transition) {
    return null;
  }

  return {
    before:
      transition.before === undefined || transition.before === null
        ? null
        : toNumber(transition.before),
    after:
      transition.after === undefined || transition.after === null
        ? null
        : toNumber(transition.after),
    delta:
      transition.delta === undefined || transition.delta === null
        ? null
        : toNumber(transition.delta),
    unit: transition.unit ?? null,
    changed: transition.changed ?? false,
  };
}

function mapLocationTransition(
  transition: ApiLocationTransition | null | undefined
): InventoryLocationTransition | null {
  if (!transition) {
    return null;
  }

  return {
    before: transition.before ?? null,
    after: transition.after ?? null,
    changed: transition.changed ?? false,
  };
}

function mapFreshnessTransition(
  transition: ApiFreshnessTransition | null | undefined
): InventoryFreshnessTransition | null {
  if (!transition) {
    return null;
  }

  return {
    before: mapFreshnessInfo(transition.before),
    after: mapFreshnessInfo(transition.after),
    changed: transition.changed ?? false,
  };
}

function mapWorkflowReference(
  workflow: ApiWorkflowReference | null | undefined
): InventoryWorkflowReference | null {
  if (!workflow) {
    return null;
  }

  return {
    correlationId: workflow.correlation_id ?? null,
    causalWorkflowId: workflow.causal_workflow_id ?? null,
    causalWorkflowType: workflow.causal_workflow_type ?? null,
  };
}

function mapCorrectionLinks(
  correction: ApiCorrectionLinks | null | undefined
): InventoryCorrectionLinks {
  return {
    correctsAdjustmentId: correction?.corrects_adjustment_id ?? null,
    correctedByAdjustmentIds: correction?.corrected_by_adjustment_ids ?? [],
    isCorrection: correction?.is_correction ?? false,
    isCorrected: correction?.is_corrected ?? false,
  };
}

function mapAdjustment(adjustment: ApiAdjustment | null | undefined): InventoryAdjustment | null {
  if (!adjustment) {
    return null;
  }

  return {
    inventoryAdjustmentId: adjustment.inventory_adjustment_id ?? '',
    inventoryItemId: adjustment.inventory_item_id ?? '',
    householdId: adjustment.household_id ?? '',
    mutationType: adjustment.mutation_type ?? 'create_item',
    deltaQuantity:
      adjustment.delta_quantity === undefined || adjustment.delta_quantity === null
        ? null
        : toNumber(adjustment.delta_quantity),
    quantityBefore:
      adjustment.quantity_before === undefined || adjustment.quantity_before === null
        ? null
        : toNumber(adjustment.quantity_before),
    quantityAfter:
      adjustment.quantity_after === undefined || adjustment.quantity_after === null
        ? null
        : toNumber(adjustment.quantity_after),
    storageLocationBefore: adjustment.storage_location_before ?? null,
    storageLocationAfter: adjustment.storage_location_after ?? null,
    freshnessBefore: mapFreshnessInfo(adjustment.freshness_before),
    freshnessAfter: mapFreshnessInfo(adjustment.freshness_after),
    reasonCode: adjustment.reason_code ?? 'manual_edit',
    actorUserId: adjustment.actor_user_id ?? 'unknown-user',
    correlationId: adjustment.correlation_id ?? null,
    clientMutationId: adjustment.client_mutation_id ?? null,
    causalWorkflowId: adjustment.causal_workflow_id ?? null,
    causalWorkflowType: adjustment.causal_workflow_type ?? null,
    correctsAdjustmentId: adjustment.corrects_adjustment_id ?? null,
    note: adjustment.note ?? null,
    createdAt: adjustment.created_at ?? new Date().toISOString(),
    primaryUnit: adjustment.primary_unit ?? null,
    quantityTransition: mapQuantityTransition(adjustment.quantity_transition),
    locationTransition: mapLocationTransition(adjustment.location_transition),
    freshnessTransition: mapFreshnessTransition(adjustment.freshness_transition),
    workflowReference: mapWorkflowReference(adjustment.workflow_reference),
    correctionLinks: mapCorrectionLinks(adjustment.correction_links),
  };
}

function mapHistorySummary(summary: ApiHistorySummary | null | undefined): InventoryHistorySummary {
  return {
    committedAdjustmentCount: summary?.committed_adjustment_count ?? 0,
    correctionCount: summary?.correction_count ?? 0,
    latestAdjustmentId: summary?.latest_adjustment_id ?? null,
    latestMutationType: summary?.latest_mutation_type ?? null,
    latestActorUserId: summary?.latest_actor_user_id ?? null,
    latestCreatedAt: summary?.latest_created_at ?? null,
  };
}

function mapInventoryItem(item: ApiInventoryItem): InventoryItem {
  const freshness = item.freshness;
  const basis = item.freshness_basis ?? freshness?.basis ?? 'unknown';
  const bestBefore = freshness?.best_before ?? null;

  return {
    inventoryItemId: item.inventory_item_id ?? item.id ?? '',
    householdId: item.household_id ?? '',
    name: item.name ?? 'Inventory item',
    storageLocation: item.storage_location ?? 'pantry',
    quantityOnHand: toNumber(item.quantity_on_hand),
    primaryUnit: item.primary_unit ?? 'ea',
    freshnessBasis: basis,
    expiryDate: basis === 'known' ? isoDate(item.expiry_date ?? bestBefore) : null,
    estimatedExpiryDate:
      basis === 'estimated' ? isoDate(item.estimated_expiry_date ?? bestBefore) : null,
    freshnessNote: item.freshness_note ?? freshness?.estimated_note ?? null,
    freshnessUpdatedAt: item.freshness_updated_at ?? null,
    isActive: item.is_active ?? true,
    serverVersion: item.version ?? 1,
    updatedAt: item.updated_at ?? new Date().toISOString(),
  };
}

function mapInventoryItemDetail(item: ApiInventoryItem): InventoryItemDetail {
  return {
    ...mapInventoryItem(item),
    historySummary: item.history_summary ? mapHistorySummary(item.history_summary) : null,
    latestAdjustment: mapAdjustment(item.latest_adjustment),
  };
}

function mapReceipt(
  receipt: ApiAdjustmentReceipt,
  mutation: InventoryMutationRequest
): MutationReceipt {
  return {
    clientMutationId: mutation.clientMutationId,
    inventoryAdjustmentId: receipt.inventory_adjustment_id ?? '',
    inventoryItemId: receipt.inventory_item_id ?? mutation.inventoryItemId ?? '',
    mutationType: receipt.mutation_type ?? mutation.mutationType,
    quantityAfter:
      receipt.quantity_after === undefined || receipt.quantity_after === null
        ? null
        : toNumber(receipt.quantity_after),
    versionAfter: receipt.version_after ?? mutation.lastKnownVersion ?? 1,
    isDuplicate: receipt.is_duplicate ?? false,
    message: receipt.result_summary,
  };
}

function buildFreshnessPayload(payload: Record<string, unknown>) {
  const basis = (payload.freshnessBasis as FreshnessBasis | undefined) ?? 'unknown';
  const bestBefore =
    (payload.expiryDate as string | undefined) ??
    (payload.estimatedExpiryDate as string | undefined) ??
    null;

  return {
    basis,
    best_before: bestBefore ? `${bestBefore}T00:00:00.000Z` : null,
    estimated_note: (payload.freshnessNote as string | undefined) ?? null,
  };
}

function buildMutationUrl(
  mutation: InventoryMutationRequest,
  activeHouseholdId: string
): { method: 'POST' | 'PATCH'; path: string; body: Record<string, unknown> } {
  if (mutation.mutationType === 'create_item') {
    return {
      method: 'POST',
      path: '/api/v1/inventory',
      body: {
        household_id: activeHouseholdId,
        name: mutation.payload.name,
        storage_location: mutation.payload.storageLocation,
        initial_quantity: mutation.payload.quantityOnHand,
        primary_unit: mutation.payload.primaryUnit,
        freshness: buildFreshnessPayload(mutation.payload),
        client_mutation_id: mutation.clientMutationId,
        note: mutation.payload.note ?? null,
      },
    };
  }

  const itemId = mutation.inventoryItemId;
  if (!itemId) {
    throw new Error('inventoryItemId is required for existing-item mutations.');
  }

  const version = mutation.lastKnownVersion ?? null;

    switch (mutation.mutationType) {
    case 'set_metadata':
      return {
        method: 'PATCH',
        path: `/api/v1/inventory/${itemId}/metadata`,
        body: {
          name: mutation.payload.name ?? null,
          storage_location: mutation.payload.storageLocation ?? null,
          freshness: buildFreshnessPayload(mutation.payload),
          note: mutation.payload.note ?? null,
          client_mutation_id: mutation.clientMutationId,
          version,
        },
      };
    case 'move_location':
      return {
        method: 'POST',
        path: `/api/v1/inventory/${itemId}/move`,
        body: {
          storage_location: mutation.payload.storageLocation,
          freshness: buildFreshnessPayload(mutation.payload),
          note: mutation.payload.note ?? null,
          client_mutation_id: mutation.clientMutationId,
          version,
        },
      };
    case 'archive_item':
      return {
        method: 'POST',
        path: `/api/v1/inventory/${itemId}/archive`,
        body: {
          client_mutation_id: mutation.clientMutationId,
          version,
          note: mutation.payload.note ?? null,
        },
      };
    case 'correction':
      return {
        method: 'POST',
        path: `/api/v1/inventory/${itemId}/corrections`,
        body: {
          delta_quantity: mutation.payload.deltaQuantity ?? null,
          corrects_adjustment_id: mutation.payload.correctsAdjustmentId,
          client_mutation_id: mutation.clientMutationId,
          version,
          note: mutation.payload.note ?? null,
        },
      };
    case 'increase_quantity':
    case 'decrease_quantity':
    case 'set_quantity':
      return {
        method: 'POST',
        path: `/api/v1/inventory/${itemId}/adjustments`,
        body: {
          mutation_type: mutation.mutationType,
          delta_quantity: mutation.payload.quantity ?? mutation.payload.deltaQuantity,
          reason_code:
            mutation.payload.reasonCode ??
            (mutation.mutationType === 'set_quantity'
              ? 'manual_count_reset'
              : 'manual_edit'),
          client_mutation_id: mutation.clientMutationId,
          version,
          note: mutation.payload.note ?? null,
        },
      };
    default:
      throw new Error(`Unsupported inventory mutation: ${mutation.mutationType}`);
  }
}

export async function getInventory(
  location?: StorageLocation
): Promise<InventoryItem[]> {
  const response = await api.get<ApiInventoryListResponse | ApiInventoryItem[]>(
    '/api/v1/inventory'
  );
  const items = Array.isArray(response) ? response : response.items ?? [];
  const mapped = items.map(mapInventoryItem).filter((item) => item.isActive);
  return location ? mapped.filter((item) => item.storageLocation === location) : mapped;
}

export async function getInventoryItemDetail(itemId: string): Promise<InventoryItemDetail> {
  const response = await api.get<ApiInventoryItem>(`/api/v1/inventory/${itemId}`);
  return mapInventoryItemDetail(response);
}

export async function getInventoryHistory(
  itemId: string,
  options: { limit?: number; offset?: number } = {}
): Promise<InventoryHistoryPage> {
  const search = new URLSearchParams();
  if (options.limit !== undefined) {
    search.set('limit', String(options.limit));
  }
  if (options.offset !== undefined) {
    search.set('offset', String(options.offset));
  }

  const query = search.size ? `?${search.toString()}` : '';
  const response = await api.get<ApiInventoryHistoryResponse>(
    `/api/v1/inventory/${itemId}/history${query}`
  );

  return {
    entries: (response.entries ?? []).map((entry) => mapAdjustment(entry)).filter(
      (entry): entry is InventoryAdjustment => entry !== null
    ),
    total: response.total ?? 0,
    limit: response.limit ?? options.limit ?? 25,
    offset: response.offset ?? options.offset ?? 0,
    hasMore: response.has_more ?? false,
    summary: mapHistorySummary(response.summary),
  };
}

export async function mutateInventory(
  activeHouseholdId: string,
  mutation: InventoryMutationRequest
): Promise<MutationReceipt> {
  const { method, path, body } = buildMutationUrl(mutation, activeHouseholdId);
  const receipt =
    method === 'PATCH'
      ? await api.patch<ApiAdjustmentReceipt>(path, body)
      : await api.post<ApiAdjustmentReceipt>(path, body);
  return mapReceipt(receipt, mutation);
}
