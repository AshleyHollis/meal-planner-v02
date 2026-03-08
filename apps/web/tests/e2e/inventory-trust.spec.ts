import { expect, test, type Page, type Request } from '@playwright/test';

type StorageLocation = 'pantry' | 'fridge' | 'freezer' | 'leftovers';
type FreshnessBasis = 'known' | 'estimated' | 'unknown';
type MutationType =
  | 'create_item'
  | 'set_metadata'
  | 'increase_quantity'
  | 'decrease_quantity'
  | 'set_quantity'
  | 'move_location'
  | 'archive_item'
  | 'correction';

type ItemState = {
  inventoryItemId: string;
  householdId: string;
  name: string;
  storageLocation: StorageLocation;
  quantityOnHand: number;
  primaryUnit: string;
  freshnessBasis: FreshnessBasis;
  expiryDate: string | null;
  estimatedExpiryDate: string | null;
  freshnessNote: string | null;
  version: number;
  updatedAt: string;
  isActive: boolean;
};

type AdjustmentState = {
  inventoryAdjustmentId: string;
  inventoryItemId: string;
  householdId: string;
  mutationType: MutationType;
  reasonCode:
    | 'manual_create'
    | 'manual_edit'
    | 'manual_count_reset'
    | 'shopping_apply'
    | 'shopping_skip_or_reduce'
    | 'cooking_consume'
    | 'leftovers_create'
    | 'spoilage_or_discard'
    | 'location_move'
    | 'correction';
  actorUserId: string;
  createdAt: string;
  clientMutationId: string | null;
  note: string | null;
  quantityTransition: {
    before: number | null;
    after: number | null;
    delta: number | null;
    unit: string | null;
    changed: boolean;
  } | null;
  locationTransition: {
    before: StorageLocation | null;
    after: StorageLocation | null;
    changed: boolean;
  } | null;
  freshnessTransition: {
    before: ApiFreshness | null;
    after: ApiFreshness | null;
    changed: boolean;
  } | null;
  correctionLinks: {
    correctsAdjustmentId: string | null;
    correctedByAdjustmentIds: string[];
    isCorrection: boolean;
    isCorrected: boolean;
  };
};

type ApiFreshness = {
  basis: FreshnessBasis;
  best_before: string | null;
  estimated_note: string | null;
};

type MockResponse = {
  status: number;
  body: unknown;
};

type Scenario = {
  householdId: string;
  userId: string;
  items: Record<string, ItemState>;
  histories: Record<string, AdjustmentState[]>;
  requestCounts: {
    metadata: number;
  };
  queuedResponses: Map<string, Array<(request: Request, scenario: Scenario) => MockResponse>>;
  itemCounter: number;
  adjustmentCounter: number;
  clock: number;
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function createScenario(): Scenario {
  return {
    householdId: 'household-abc',
    userId: 'user-123',
    items: {},
    histories: {},
    requestCounts: {
      metadata: 0,
    },
    queuedResponses: new Map(),
    itemCounter: 0,
    adjustmentCounter: 0,
    clock: 0,
  };
}

function nextTimestamp(scenario: Scenario): string {
  const timestamp = new Date(Date.UTC(2026, 2, 8, 12, scenario.clock, 0)).toISOString();
  scenario.clock += 1;
  return timestamp;
}

function nextItemId(scenario: Scenario): string {
  scenario.itemCounter += 1;
  return `item-${scenario.itemCounter}`;
}

function nextAdjustmentId(scenario: Scenario): string {
  scenario.adjustmentCounter += 1;
  return `adj-${scenario.adjustmentCounter}`;
}

function queueResponse(
  scenario: Scenario,
  key: string,
  responder: (request: Request, current: Scenario) => MockResponse
) {
  const existing = scenario.queuedResponses.get(key) ?? [];
  existing.push(responder);
  scenario.queuedResponses.set(key, existing);
}

function shiftQueuedResponse(scenario: Scenario, key: string) {
  const existing = scenario.queuedResponses.get(key);
  if (!existing || existing.length === 0) {
    return null;
  }

  const next = existing.shift() ?? null;
  if (existing.length === 0) {
    scenario.queuedResponses.delete(key);
  }
  return next;
}

function toApiFreshness(item: ItemState): ApiFreshness {
  return {
    basis: item.freshnessBasis,
    best_before:
      item.freshnessBasis === 'known'
        ? item.expiryDate
        : item.freshnessBasis === 'estimated'
          ? item.estimatedExpiryDate
          : null,
    estimated_note: item.freshnessNote,
  };
}

function quantityTransition(
  before: number | null,
  after: number | null,
  unit: string
): AdjustmentState['quantityTransition'] {
  const delta = before === null || after === null ? after : after - before;
  return {
    before,
    after,
    delta,
    unit,
    changed: before !== after,
  };
}

function addHistoryEntry(scenario: Scenario, itemId: string, entry: AdjustmentState) {
  const current = scenario.histories[itemId] ?? [];
  scenario.histories[itemId] = [entry, ...current];
}

function createItem(
  scenario: Scenario,
  values: {
    name: string;
    quantityOnHand: number;
    primaryUnit: string;
    storageLocation: StorageLocation;
    freshnessBasis: FreshnessBasis;
    expiryDate?: string | null;
    estimatedExpiryDate?: string | null;
    freshnessNote?: string | null;
    note?: string | null;
    clientMutationId?: string;
  }
) {
  const inventoryItemId = nextItemId(scenario);
  const inventoryAdjustmentId = nextAdjustmentId(scenario);
  const updatedAt = nextTimestamp(scenario);
  const item: ItemState = {
    inventoryItemId,
    householdId: scenario.householdId,
    name: values.name,
    storageLocation: values.storageLocation,
    quantityOnHand: values.quantityOnHand,
    primaryUnit: values.primaryUnit,
    freshnessBasis: values.freshnessBasis,
    expiryDate: values.expiryDate ?? null,
    estimatedExpiryDate: values.estimatedExpiryDate ?? null,
    freshnessNote: values.freshnessNote ?? null,
    version: 1,
    updatedAt,
    isActive: true,
  };
  scenario.items[inventoryItemId] = item;
  addHistoryEntry(scenario, inventoryItemId, {
    inventoryAdjustmentId,
    inventoryItemId,
    householdId: scenario.householdId,
    mutationType: 'create_item',
    reasonCode: 'manual_create',
    actorUserId: scenario.userId,
    createdAt: updatedAt,
    clientMutationId: values.clientMutationId ?? null,
    note: values.note ?? null,
    quantityTransition: quantityTransition(null, values.quantityOnHand, values.primaryUnit),
    locationTransition: {
      before: null,
      after: values.storageLocation,
      changed: true,
    },
    freshnessTransition: {
      before: null,
      after: toApiFreshness(item),
      changed: item.freshnessBasis !== 'unknown' || Boolean(item.freshnessNote),
    },
    correctionLinks: {
      correctsAdjustmentId: null,
      correctedByAdjustmentIds: [],
      isCorrection: false,
      isCorrected: false,
    },
  });
  return item;
}

function applyQuantityMutation(
  scenario: Scenario,
  itemId: string,
  values: {
    mutationType: 'increase_quantity' | 'decrease_quantity' | 'set_quantity';
    quantity: number;
    reasonCode:
      | 'manual_edit'
      | 'manual_count_reset'
      | 'shopping_apply'
      | 'shopping_skip_or_reduce'
      | 'cooking_consume'
      | 'leftovers_create'
      | 'correction';
    note?: string | null;
    clientMutationId?: string | null;
  }
) {
  const item = scenario.items[itemId];
  if (!item) {
    throw new Error(`Unknown item ${itemId}`);
  }

  const before = item.quantityOnHand;
  const after =
    values.mutationType === 'increase_quantity'
      ? before + values.quantity
      : values.mutationType === 'decrease_quantity'
        ? before - values.quantity
        : values.quantity;
  item.quantityOnHand = after;
  item.version += 1;
  item.updatedAt = nextTimestamp(scenario);

  const entry: AdjustmentState = {
    inventoryAdjustmentId: nextAdjustmentId(scenario),
    inventoryItemId: itemId,
    householdId: scenario.householdId,
    mutationType: values.mutationType,
    reasonCode: values.reasonCode,
    actorUserId: scenario.userId,
    createdAt: item.updatedAt,
    clientMutationId: values.clientMutationId ?? null,
    note: values.note ?? null,
    quantityTransition: quantityTransition(before, after, item.primaryUnit),
    locationTransition: {
      before: item.storageLocation,
      after: item.storageLocation,
      changed: false,
    },
    freshnessTransition: {
      before: toApiFreshness(item),
      after: toApiFreshness(item),
      changed: false,
    },
    correctionLinks: {
      correctsAdjustmentId: null,
      correctedByAdjustmentIds: [],
      isCorrection: false,
      isCorrected: false,
    },
  };
  addHistoryEntry(scenario, itemId, entry);
  return entry;
}

function applyMetadataMutation(
  scenario: Scenario,
  itemId: string,
  values: {
    name: string;
    freshnessBasis: FreshnessBasis;
    expiryDate?: string | null;
    estimatedExpiryDate?: string | null;
    freshnessNote?: string | null;
    note?: string | null;
    clientMutationId?: string | null;
  }
) {
  const item = scenario.items[itemId];
  if (!item) {
    throw new Error(`Unknown item ${itemId}`);
  }

  const beforeFreshness = toApiFreshness(item);
  const beforeName = item.name;
  item.name = values.name;
  item.freshnessBasis = values.freshnessBasis;
  item.expiryDate = values.freshnessBasis === 'known' ? values.expiryDate ?? null : null;
  item.estimatedExpiryDate =
    values.freshnessBasis === 'estimated' ? values.estimatedExpiryDate ?? null : null;
  item.freshnessNote = values.freshnessNote ?? null;
  item.version += 1;
  item.updatedAt = nextTimestamp(scenario);

  const entry: AdjustmentState = {
    inventoryAdjustmentId: nextAdjustmentId(scenario),
    inventoryItemId: itemId,
    householdId: scenario.householdId,
    mutationType: 'set_metadata',
    reasonCode: 'manual_edit',
    actorUserId: scenario.userId,
    createdAt: item.updatedAt,
    clientMutationId: values.clientMutationId ?? null,
    note: values.note ?? null,
    quantityTransition: quantityTransition(item.quantityOnHand, item.quantityOnHand, item.primaryUnit),
    locationTransition: {
      before: item.storageLocation,
      after: item.storageLocation,
      changed: false,
    },
    freshnessTransition: {
      before: beforeFreshness,
      after: toApiFreshness(item),
      changed:
        beforeName !== item.name ||
        JSON.stringify(beforeFreshness) !== JSON.stringify(toApiFreshness(item)),
    },
    correctionLinks: {
      correctsAdjustmentId: null,
      correctedByAdjustmentIds: [],
      isCorrection: false,
      isCorrected: false,
    },
  };
  addHistoryEntry(scenario, itemId, entry);
  return entry;
}

function applyMoveMutation(
  scenario: Scenario,
  itemId: string,
  values: {
    storageLocation: StorageLocation;
    note?: string | null;
    clientMutationId?: string | null;
  }
) {
  const item = scenario.items[itemId];
  if (!item) {
    throw new Error(`Unknown item ${itemId}`);
  }

  const before = item.storageLocation;
  item.storageLocation = values.storageLocation;
  item.version += 1;
  item.updatedAt = nextTimestamp(scenario);

  const entry: AdjustmentState = {
    inventoryAdjustmentId: nextAdjustmentId(scenario),
    inventoryItemId: itemId,
    householdId: scenario.householdId,
    mutationType: 'move_location',
    reasonCode: 'location_move',
    actorUserId: scenario.userId,
    createdAt: item.updatedAt,
    clientMutationId: values.clientMutationId ?? null,
    note: values.note ?? null,
    quantityTransition: quantityTransition(item.quantityOnHand, item.quantityOnHand, item.primaryUnit),
    locationTransition: {
      before,
      after: item.storageLocation,
      changed: before !== item.storageLocation,
    },
    freshnessTransition: {
      before: toApiFreshness(item),
      after: toApiFreshness(item),
      changed: false,
    },
    correctionLinks: {
      correctsAdjustmentId: null,
      correctedByAdjustmentIds: [],
      isCorrection: false,
      isCorrected: false,
    },
  };
  addHistoryEntry(scenario, itemId, entry);
  return entry;
}

function applyCorrectionMutation(
  scenario: Scenario,
  itemId: string,
  values: {
    correctsAdjustmentId: string;
    deltaQuantity: number;
    note: string;
    clientMutationId?: string | null;
  }
) {
  const item = scenario.items[itemId];
  if (!item) {
    throw new Error(`Unknown item ${itemId}`);
  }

  const target = (scenario.histories[itemId] ?? []).find(
    (entry) => entry.inventoryAdjustmentId === values.correctsAdjustmentId
  );
  if (!target) {
    throw new Error(`Unknown correction target ${values.correctsAdjustmentId}`);
  }

  const before = item.quantityOnHand;
  item.quantityOnHand += values.deltaQuantity;
  item.version += 1;
  item.updatedAt = nextTimestamp(scenario);

  const correctionId = nextAdjustmentId(scenario);
  const entry: AdjustmentState = {
    inventoryAdjustmentId: correctionId,
    inventoryItemId: itemId,
    householdId: scenario.householdId,
    mutationType: 'correction',
    reasonCode: 'correction',
    actorUserId: scenario.userId,
    createdAt: item.updatedAt,
    clientMutationId: values.clientMutationId ?? null,
    note: values.note,
    quantityTransition: quantityTransition(before, item.quantityOnHand, item.primaryUnit),
    locationTransition: {
      before: item.storageLocation,
      after: item.storageLocation,
      changed: false,
    },
    freshnessTransition: {
      before: toApiFreshness(item),
      after: toApiFreshness(item),
      changed: false,
    },
    correctionLinks: {
      correctsAdjustmentId: values.correctsAdjustmentId,
      correctedByAdjustmentIds: [],
      isCorrection: true,
      isCorrected: false,
    },
  };
  target.correctionLinks.isCorrected = true;
  target.correctionLinks.correctedByAdjustmentIds = [
    ...target.correctionLinks.correctedByAdjustmentIds,
    correctionId,
  ];
  addHistoryEntry(scenario, itemId, entry);
  return entry;
}

function historySummary(entries: AdjustmentState[]) {
  return {
    committed_adjustment_count: entries.length,
    correction_count: entries.filter((entry) => entry.correctionLinks.isCorrection).length,
    latest_adjustment_id: entries[0]?.inventoryAdjustmentId ?? null,
    latest_mutation_type: entries[0]?.mutationType ?? null,
    latest_actor_user_id: entries[0]?.actorUserId ?? null,
    latest_created_at: entries[0]?.createdAt ?? null,
  };
}

function toApiAdjustment(entry: AdjustmentState) {
  return {
    inventory_adjustment_id: entry.inventoryAdjustmentId,
    inventory_item_id: entry.inventoryItemId,
    household_id: entry.householdId,
    mutation_type: entry.mutationType,
    reason_code: entry.reasonCode,
    actor_user_id: entry.actorUserId,
    created_at: entry.createdAt,
    client_mutation_id: entry.clientMutationId,
    note: entry.note,
    primary_unit: scenarioPrimaryUnit(entry),
    quantity_transition: entry.quantityTransition,
    location_transition: entry.locationTransition,
    freshness_transition: entry.freshnessTransition,
    correction_links: {
      corrects_adjustment_id: entry.correctionLinks.correctsAdjustmentId,
      corrected_by_adjustment_ids: entry.correctionLinks.correctedByAdjustmentIds,
      is_correction: entry.correctionLinks.isCorrection,
      is_corrected: entry.correctionLinks.isCorrected,
    },
  };
}

function scenarioPrimaryUnit(entry: AdjustmentState) {
  return entry.quantityTransition?.unit ?? null;
}

function toApiItemSummary(item: ItemState) {
  return {
    inventory_item_id: item.inventoryItemId,
    household_id: item.householdId,
    name: item.name,
    storage_location: item.storageLocation,
    quantity_on_hand: item.quantityOnHand,
    primary_unit: item.primaryUnit,
    freshness_basis: item.freshnessBasis,
    freshness: toApiFreshness(item),
    expiry_date: item.expiryDate,
    estimated_expiry_date: item.estimatedExpiryDate,
    freshness_note: item.freshnessNote,
    is_active: item.isActive,
    version: item.version,
    updated_at: item.updatedAt,
  };
}

function toApiItemDetail(scenario: Scenario, item: ItemState) {
  const entries = scenario.histories[item.inventoryItemId] ?? [];
  return {
    ...toApiItemSummary(item),
    history_summary: historySummary(entries),
    latest_adjustment: entries[0] ? toApiAdjustment(entries[0]) : null,
  };
}

async function fulfill(page: Page, scenario: Scenario) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const key = `${request.method()} ${url.pathname}`;
    const queued = shiftQueuedResponse(scenario, key);
    if (queued) {
      const response = queued(request, scenario);
      await route.fulfill({ status: response.status, json: response.body });
      return;
    }

    if (request.method() === 'GET' && url.pathname === '/api/v1/me') {
      await route.fulfill({
        status: 200,
        json: {
          authenticated: true,
          user: {
            user_id: scenario.userId,
            email: 'ashley@example.com',
            display_name: 'Ashley',
            active_household_id: scenario.householdId,
            households: [
              {
                household_id: scenario.householdId,
                household_name: 'Primary Household',
                role: 'owner',
              },
            ],
          },
        },
      });
      return;
    }

    if (request.method() === 'GET' && url.pathname === '/api/v1/inventory') {
      const items = Object.values(scenario.items).filter((item) => item.isActive);
      await route.fulfill({
        status: 200,
        json: {
          items: items.map((item) => toApiItemSummary(item)),
          total: items.length,
        },
      });
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/v1/inventory') {
      const body = request.postDataJSON() as {
        name: string;
        initial_quantity: number;
        primary_unit: string;
        storage_location: StorageLocation;
        freshness?: ApiFreshness;
        note?: string | null;
        client_mutation_id?: string;
      };
      const item = createItem(scenario, {
        name: body.name,
        quantityOnHand: body.initial_quantity,
        primaryUnit: body.primary_unit,
        storageLocation: body.storage_location,
        freshnessBasis: body.freshness?.basis ?? 'unknown',
        expiryDate: body.freshness?.basis === 'known' ? body.freshness.best_before : null,
        estimatedExpiryDate:
          body.freshness?.basis === 'estimated' ? body.freshness.best_before : null,
        freshnessNote: body.freshness?.estimated_note ?? null,
        note: body.note ?? null,
        clientMutationId: body.client_mutation_id,
      });
      await route.fulfill({
        status: 201,
        json: {
          inventory_adjustment_id: scenario.histories[item.inventoryItemId]?.[0]?.inventoryAdjustmentId,
          inventory_item_id: item.inventoryItemId,
          mutation_type: 'create_item',
          quantity_after: item.quantityOnHand,
          version_after: item.version,
          is_duplicate: false,
          result_summary: `created ${item.name}`,
        },
      });
      return;
    }

    const match = url.pathname.match(/^\/api\/v1\/inventory\/([^/]+)(?:\/(history|metadata|adjustments|move|corrections))?$/);
    if (!match) {
      throw new Error(`Unhandled request: ${key}`);
    }

    const itemId = match[1] ?? '';
    const subresource = match[2] ?? null;
    const item = scenario.items[itemId];
    if (!item) {
      await route.fulfill({ status: 404, json: { detail: 'Inventory item not found' } });
      return;
    }

    if (request.method() === 'GET' && subresource === null) {
      await route.fulfill({ status: 200, json: toApiItemDetail(scenario, item) });
      return;
    }

    if (request.method() === 'GET' && subresource === 'history') {
      const limit = Number(url.searchParams.get('limit') ?? '25');
      const offset = Number(url.searchParams.get('offset') ?? '0');
      const entries = scenario.histories[itemId] ?? [];
      await route.fulfill({
        status: 200,
        json: {
          entries: entries.slice(offset, offset + limit).map((entry) => toApiAdjustment(entry)),
          total: entries.length,
          limit,
          offset,
          has_more: offset + limit < entries.length,
          summary: historySummary(entries),
        },
      });
      return;
    }

    if (request.method() === 'PATCH' && subresource === 'metadata') {
      scenario.requestCounts.metadata += 1;
      const body = request.postDataJSON() as {
        name: string;
        freshness: ApiFreshness;
        note?: string | null;
        client_mutation_id?: string;
      };
      const entry = applyMetadataMutation(scenario, itemId, {
        name: body.name,
        freshnessBasis: body.freshness?.basis ?? 'unknown',
        expiryDate: body.freshness?.basis === 'known' ? body.freshness.best_before : null,
        estimatedExpiryDate:
          body.freshness?.basis === 'estimated' ? body.freshness.best_before : null,
        freshnessNote: body.freshness?.estimated_note ?? null,
        note: body.note ?? null,
        clientMutationId: body.client_mutation_id ?? null,
      });
      await route.fulfill({
        status: 200,
        json: {
          inventory_adjustment_id: entry.inventoryAdjustmentId,
          inventory_item_id: itemId,
          mutation_type: 'set_metadata',
          quantity_after: scenario.items[itemId]?.quantityOnHand,
          version_after: scenario.items[itemId]?.version,
          is_duplicate: false,
          result_summary: 'metadata updated',
        },
      });
      return;
    }

    if (request.method() === 'POST' && subresource === 'adjustments') {
      const body = request.postDataJSON() as {
        mutation_type: 'increase_quantity' | 'decrease_quantity' | 'set_quantity';
        delta_quantity: number;
        reason_code:
          | 'manual_edit'
          | 'manual_count_reset'
          | 'shopping_apply'
          | 'shopping_skip_or_reduce'
          | 'cooking_consume'
          | 'leftovers_create'
          | 'correction';
        note?: string | null;
        client_mutation_id?: string;
      };
      const entry = applyQuantityMutation(scenario, itemId, {
        mutationType: body.mutation_type,
        quantity: Number(body.delta_quantity),
        reasonCode: body.reason_code,
        note: body.note ?? null,
        clientMutationId: body.client_mutation_id ?? null,
      });
      await route.fulfill({
        status: 201,
        json: {
          inventory_adjustment_id: entry.inventoryAdjustmentId,
          inventory_item_id: itemId,
          mutation_type: body.mutation_type,
          quantity_after: scenario.items[itemId]?.quantityOnHand,
          version_after: scenario.items[itemId]?.version,
          is_duplicate: false,
          result_summary: 'quantity updated',
        },
      });
      return;
    }

    if (request.method() === 'POST' && subresource === 'move') {
      const body = request.postDataJSON() as {
        storage_location: StorageLocation;
        note?: string | null;
        client_mutation_id?: string;
      };
      const entry = applyMoveMutation(scenario, itemId, {
        storageLocation: body.storage_location,
        note: body.note ?? null,
        clientMutationId: body.client_mutation_id ?? null,
      });
      await route.fulfill({
        status: 201,
        json: {
          inventory_adjustment_id: entry.inventoryAdjustmentId,
          inventory_item_id: itemId,
          mutation_type: 'move_location',
          quantity_after: scenario.items[itemId]?.quantityOnHand,
          version_after: scenario.items[itemId]?.version,
          is_duplicate: false,
          result_summary: 'location updated',
        },
      });
      return;
    }

    if (request.method() === 'POST' && subresource === 'corrections') {
      const body = request.postDataJSON() as {
        corrects_adjustment_id: string;
        delta_quantity: number;
        note: string;
        client_mutation_id?: string;
      };
      const entry = applyCorrectionMutation(scenario, itemId, {
        correctsAdjustmentId: body.corrects_adjustment_id,
        deltaQuantity: Number(body.delta_quantity),
        note: body.note,
        clientMutationId: body.client_mutation_id ?? null,
      });
      await route.fulfill({
        status: 201,
        json: {
          inventory_adjustment_id: entry.inventoryAdjustmentId,
          inventory_item_id: itemId,
          mutation_type: 'correction',
          quantity_after: scenario.items[itemId]?.quantityOnHand,
          version_after: scenario.items[itemId]?.version,
          is_duplicate: false,
          result_summary: 'correction recorded',
        },
      });
      return;
    }

    throw new Error(`Unhandled request: ${key}`);
  });
}

function seedConflictScenario() {
  const scenario = createScenario();
  const item = createItem(scenario, {
    name: 'Spinach',
    quantityOnHand: 4,
    primaryUnit: 'bags',
    storageLocation: 'fridge',
    freshnessBasis: 'known',
    expiryDate: '2026-03-12T00:00:00.000Z',
    note: 'created from market trip',
    clientMutationId: 'seed-create',
  });
  applyQuantityMutation(scenario, item.inventoryItemId, {
    mutationType: 'increase_quantity',
    quantity: 2,
    reasonCode: 'shopping_apply',
    note: 'restocked after delivery',
    clientMutationId: 'seed-increase',
  });
  applyMoveMutation(scenario, item.inventoryItemId, {
    storageLocation: 'pantry',
    note: 'temporarily shelved',
    clientMutationId: 'seed-move-out',
  });
  applyMoveMutation(scenario, item.inventoryItemId, {
    storageLocation: 'fridge',
    note: 'returned to fridge',
    clientMutationId: 'seed-move-back',
  });
  applyMetadataMutation(scenario, item.inventoryItemId, {
    name: 'Spinach',
    freshnessBasis: 'known',
    expiryDate: '2026-03-15T00:00:00.000Z',
    freshnessNote: 'label confirmed',
    note: 'checked label',
    clientMutationId: 'seed-metadata',
  });
  applyQuantityMutation(scenario, item.inventoryItemId, {
    mutationType: 'decrease_quantity',
    quantity: 1,
    reasonCode: 'cooking_consume',
    note: 'used for lunch',
    clientMutationId: 'seed-decrease',
  });
  applyQuantityMutation(scenario, item.inventoryItemId, {
    mutationType: 'set_quantity',
    quantity: 5,
    reasonCode: 'manual_count_reset',
    note: 'counted remaining stock',
    clientMutationId: 'seed-set',
  });
  return { scenario, itemId: item.inventoryItemId };
}

test('trusted inventory sequence keeps quantity history and correction chains understandable', async ({
  page,
}) => {
  const scenario = createScenario();
  await fulfill(page, scenario);

  await page.goto('/inventory');
  await expect(page.getByText('Nothing here yet')).toBeVisible();

  await page.getByRole('button', { name: '+ Add item' }).click();
  const addForm = page.getByRole('form', { name: 'Add inventory item' });
  await addForm.getByLabel('Item name').fill('Oat Milk');
  await addForm.getByLabel('Quantity').fill('2');
  await addForm.getByLabel('Unit').fill('litres');
  await addForm.getByLabel('Storage location').selectOption('fridge');
  await addForm.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText(/Added Oat Milk/)).toBeVisible();
  await expect(page.getByRole('button', { name: /Review trust details for Oat Milk/ })).toBeVisible();

  await page.getByRole('button', { name: /Review trust details for Oat Milk/ }).click();
  const trustPanel = page.getByRole('region', { name: /Oat Milk trust review/ });
  await expect(trustPanel).toContainText('2 litres in Fridge');
  await expect(page.getByRole('region', { name: 'Inventory history' })).toContainText(
    'Created item'
  );

  const quantityForm = trustPanel.locator('form').nth(0);
  await quantityForm.locator('input[type="number"]').first().fill('1');
  await quantityForm.getByLabel('Note').fill('added a fresh carton');
  await quantityForm.getByRole('button', { name: 'Save quantity change' }).click();

  await expect(page.getByText(/Increased quantity saved\./)).toBeVisible();
  await expect(trustPanel).toContainText('3 litres in Fridge');

  const metadataForm = trustPanel.locator('form').nth(1);
  await metadataForm.getByLabel('Freshness basis').selectOption('known');
  await metadataForm.getByLabel('Exact expiry date').fill('2026-03-20');
  await metadataForm.getByLabel('Freshness note').fill('label confirmed on delivery');
  await metadataForm.getByLabel('Audit note').fill('confirmed the printed date');
  await metadataForm.getByRole('button', { name: 'Save metadata' }).click();

  await expect(page.getByText(/Saved metadata\./)).toBeVisible();
  await expect(trustPanel).toContainText('Current freshness');

  const correctionForm = trustPanel.locator('form').nth(3);
  await expect(correctionForm).toContainText('Correcting: Increased quantity');
  await correctionForm.getByLabel('Why is a correction needed?').fill('counted one carton twice');
  await correctionForm.getByRole('button', { name: 'Record correction' }).click();

  await expect(page.getByText(/Recorded a compensating correction\./)).toBeVisible();
  await expect(trustPanel).toContainText('2 litres in Fridge');

  const history = page.getByRole('region', { name: 'Inventory history' });
  await expect(history).toContainText('Correction event');
  await expect(history).toContainText('Corrected later');
  await expect(history).toContainText('Corrects');
  await expect(history).toContainText('adj-2');
  await expect(history).toContainText('Corrected by');
  await expect(history).toContainText('adj-4');
});

test('history review, freshness change, move flow, and conflict or error states stay explainable', async ({
  page,
}) => {
  const { scenario, itemId } = seedConflictScenario();
  queueResponse(scenario, `POST /api/v1/inventory/${itemId}/adjustments`, () => {
    applyQuantityMutation(scenario, itemId, {
      mutationType: 'increase_quantity',
      quantity: 1,
      reasonCode: 'manual_edit',
      note: 'another user already updated this item',
      clientMutationId: 'external-conflict',
    });
    return {
      status: 409,
      body: {
        detail: {
          code: 'stale_inventory_version',
          message: 'The inventory item changed since the client last read it.',
          expected_version: 7,
          current_version: scenario.items[itemId]?.version,
        },
      },
    };
  });
  queueResponse(scenario, `POST /api/v1/inventory/${itemId}/corrections`, () => ({
    status: 500,
    body: {
      detail: {
        message: 'Inventory service unavailable for corrections.',
      },
    },
  }));
  await fulfill(page, scenario);

  await page.goto('/inventory');
  await page.getByRole('button', { name: /Review trust details for Spinach/ }).click();

  const trustPanel = page.getByRole('region', { name: /Spinach trust review/ });
  const history = page.getByRole('region', { name: 'Inventory history' });
  await expect(history).toContainText('Load older history');
  await page.getByRole('button', { name: 'Load older history' }).click();
  await expect(history).toContainText('created from market trip');

  const quantityForm = trustPanel.locator('form').nth(0);
  await quantityForm.locator('input[type="number"]').first().fill('1');
  await quantityForm.getByLabel('Note').fill('try to add one more bag');
  await quantityForm.getByRole('button', { name: 'Save quantity change' }).click();

  await expect(
    page.getByText(
      /The inventory item changed since the client last read it\. Server version is now 8\./
    )
  ).toBeVisible();
  await expect(trustPanel).toContainText('v8');

  const metadataForm = trustPanel.locator('form').nth(1);
  await metadataForm.getByLabel('Freshness basis').selectOption('unknown');
  await expect(
    metadataForm.getByText('I understand this reduces freshness precision and should stay visible in history.')
  ).toBeVisible();
  await metadataForm.getByRole('button', { name: 'Save metadata' }).click();
  await expect.poll(() => scenario.requestCounts.metadata).toBe(0);

  await metadataForm
    .getByText('I understand this reduces freshness precision and should stay visible in history.')
    .click();
  await metadataForm.getByLabel('Audit note').fill('source label was unreadable');
  await metadataForm.getByRole('button', { name: 'Save metadata' }).click();
  await expect.poll(() => scenario.requestCounts.metadata).toBe(1);
  await expect(page.getByText(/Saved metadata\./)).toBeVisible();

  const moveForm = trustPanel.locator('form').nth(2);
  await moveForm.getByLabel('New storage location').selectOption('freezer');
  await moveForm.getByLabel('Note').fill('moved to the freezer for later');
  await moveForm.getByRole('button', { name: 'Save location move' }).click();

  await expect(page.getByText(/Spinach moved to Freezer\./)).toBeVisible();
  await expect(page.getByRole('button', { name: /Review trust details for Spinach/ })).toHaveCount(0);

  await page.getByRole('tab', { name: /Freezer/ }).click();
  await page.getByRole('button', { name: /Review trust details for Spinach/ }).click();
  const freezerPanel = page.getByRole('region', { name: /Spinach trust review/ });
  const correctionForm = freezerPanel.locator('form').nth(3);
  await correctionForm.getByLabel('Why is a correction needed?').fill('service error should be visible');
  await correctionForm.getByRole('button', { name: 'Record correction' }).click();

  await expect(page.getByText('Inventory service unavailable for corrections.')).toBeVisible();
});
