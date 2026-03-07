import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { getInventory, getInventoryHistory, getInventoryItemDetail, mutateInventory } from './inventory-api';
import type { InventoryMutationRequest } from './types';

const originalFetch = globalThis.fetch;

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('getInventory loads active items for the requested location', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(200, {
      items: [
        {
          inventory_item_id: 'item-1',
          household_id: 'household-abc',
          name: 'Milk',
          storage_location: 'fridge',
          quantity_on_hand: 2,
          primary_unit: 'litres',
          freshness_basis: 'unknown',
          is_active: true,
          version: 4,
          updated_at: '2026-03-08T00:00:00Z',
        },
        {
          inventory_item_id: 'item-2',
          household_id: 'household-abc',
          name: 'Beans',
          storage_location: 'pantry',
          quantity_on_hand: 1,
          primary_unit: 'can',
          freshness_basis: 'unknown',
          is_active: true,
          version: 2,
          updated_at: '2026-03-08T00:00:00Z',
        },
        {
          inventory_item_id: 'item-3',
          household_id: 'household-abc',
          name: 'Old stock',
          storage_location: 'fridge',
          quantity_on_hand: 1,
          primary_unit: 'ea',
          freshness_basis: 'unknown',
          is_active: false,
          version: 1,
          updated_at: '2026-03-08T00:00:00Z',
        },
      ],
    });
  }) as typeof fetch;

  const items = await getInventory('fridge');

  assert.equal(calls.length, 1);
  assert.equal(String(calls[0].input), '/api/v1/inventory');
  assert.equal(items.length, 1);
  assert.equal(items[0]?.inventoryItemId, 'item-1');
  assert.equal(items[0]?.serverVersion, 4);
});

test('mutateInventory creates items in the authenticated household context', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(201, {
      inventory_adjustment_id: 'adj-1',
      inventory_item_id: 'item-1',
      mutation_type: 'create_item',
      quantity_after: 2,
      version_after: 1,
      is_duplicate: false,
    });
  }) as typeof fetch;

  const mutation: InventoryMutationRequest = {
    clientMutationId: 'mutation-1',
    mutationType: 'create_item',
    payload: {
      name: 'Oat Milk',
      quantityOnHand: 2,
      primaryUnit: 'litres',
      storageLocation: 'fridge',
      freshnessBasis: 'known',
      expiryDate: '2026-03-10',
      note: 'opened today',
    },
  };

  const receipt = await mutateInventory('household-abc', mutation);

  assert.equal(String(calls[0]?.input), '/api/v1/inventory');
  assert.equal(calls[0]?.init?.method, 'POST');
  const body = JSON.parse(String(calls[0]?.init?.body));
  assert.equal(body.household_id, 'household-abc');
  assert.equal(body.client_mutation_id, 'mutation-1');
  assert.equal(body.freshness.best_before, '2026-03-10T00:00:00.000Z');
  assert.deepEqual(receipt, {
    clientMutationId: 'mutation-1',
    inventoryAdjustmentId: 'adj-1',
    inventoryItemId: 'item-1',
    mutationType: 'create_item',
    quantityAfter: 2,
    versionAfter: 1,
    isDuplicate: false,
    message: undefined,
  });
});

test('mutateInventory archives items with the last known version', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(201, {
      inventory_adjustment_id: 'adj-archive',
      inventory_item_id: 'item-9',
      mutation_type: 'archive_item',
      quantity_after: 1,
      version_after: 8,
      is_duplicate: false,
      result_summary: 'archived',
    });
  }) as typeof fetch;

  const receipt = await mutateInventory('household-abc', {
    clientMutationId: 'mutation-archive',
    mutationType: 'archive_item',
    inventoryItemId: 'item-9',
    lastKnownVersion: 7,
    payload: {},
  });

  assert.equal(String(calls[0]?.input), '/api/v1/inventory/item-9/archive');
  const body = JSON.parse(String(calls[0]?.init?.body));
  assert.equal(body.client_mutation_id, 'mutation-archive');
  assert.equal(body.version, 7);
  assert.equal(receipt.versionAfter, 8);
  assert.equal(receipt.message, 'archived');
});

test('mutateInventory uses PATCH for metadata updates', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(200, {
      inventory_adjustment_id: 'adj-meta',
      inventory_item_id: 'item-3',
      mutation_type: 'set_metadata',
      quantity_after: 2,
      version_after: 5,
      is_duplicate: false,
      result_summary: 'metadata updated',
    });
  }) as typeof fetch;

  const receipt = await mutateInventory('household-abc', {
    clientMutationId: 'mutation-metadata',
    mutationType: 'set_metadata',
    inventoryItemId: 'item-3',
    lastKnownVersion: 4,
    payload: {
      name: 'Greek Yogurt',
      freshnessBasis: 'known',
      expiryDate: '2026-03-12',
      note: 'label confirmed',
    },
  });

  assert.equal(String(calls[0]?.input), '/api/v1/inventory/item-3/metadata');
  assert.equal(calls[0]?.init?.method, 'PATCH');
  const body = JSON.parse(String(calls[0]?.init?.body));
  assert.equal(body.name, 'Greek Yogurt');
  assert.equal(body.version, 4);
  assert.equal(body.freshness.best_before, '2026-03-12T00:00:00.000Z');
  assert.equal(receipt.mutationType, 'set_metadata');
  assert.equal(receipt.versionAfter, 5);
});

test('mutateInventory sends quantity adjustments to the adjustment endpoint', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(201, {
      inventory_adjustment_id: 'adj-qty',
      inventory_item_id: 'item-4',
      mutation_type: 'increase_quantity',
      quantity_after: 3,
      version_after: 6,
      is_duplicate: false,
    });
  }) as typeof fetch;

  const receipt = await mutateInventory('household-abc', {
    clientMutationId: 'mutation-quantity',
    mutationType: 'increase_quantity',
    inventoryItemId: 'item-4',
    lastKnownVersion: 5,
    payload: {
      quantity: 1,
      reasonCode: 'shopping_apply',
      note: 'restocked after delivery',
    },
  });

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/inventory/item-4/adjustments'
  );
  assert.equal(calls[0]?.init?.method, 'POST');
  const body = JSON.parse(String(calls[0]?.init?.body));
  assert.equal(body.mutation_type, 'increase_quantity');
  assert.equal(body.delta_quantity, 1);
  assert.equal(body.reason_code, 'shopping_apply');
  assert.equal(body.version, 5);
  assert.equal(receipt.versionAfter, 6);
});

test('mutateInventory sends move requests to the move endpoint', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(201, {
      inventory_adjustment_id: 'adj-move',
      inventory_item_id: 'item-5',
      mutation_type: 'move_location',
      quantity_after: 2,
      version_after: 4,
      is_duplicate: false,
      result_summary: 'moved to freezer',
    });
  }) as typeof fetch;

  const receipt = await mutateInventory('household-abc', {
    clientMutationId: 'mutation-move',
    mutationType: 'move_location',
    inventoryItemId: 'item-5',
    lastKnownVersion: 3,
    payload: {
      storageLocation: 'freezer',
      note: 'preserving it for later',
    },
  });

  assert.equal(String(calls[0]?.input), '/api/v1/inventory/item-5/move');
  const body = JSON.parse(String(calls[0]?.init?.body));
  assert.equal(body.storage_location, 'freezer');
  assert.equal(body.version, 3);
  assert.equal(receipt.mutationType, 'move_location');
  assert.equal(receipt.message, 'moved to freezer');
});

test('mutateInventory sends compensating corrections with the linked adjustment id', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(201, {
      inventory_adjustment_id: 'adj-correction',
      inventory_item_id: 'item-6',
      mutation_type: 'correction',
      quantity_after: 2,
      version_after: 9,
      is_duplicate: false,
      result_summary: 'correction recorded',
    });
  }) as typeof fetch;

  const receipt = await mutateInventory('household-abc', {
    clientMutationId: 'mutation-correction',
    mutationType: 'correction',
    inventoryItemId: 'item-6',
    lastKnownVersion: 8,
    payload: {
      deltaQuantity: -1,
      correctsAdjustmentId: 'adj-qty',
      note: 'counted one unit twice',
    },
  });

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/inventory/item-6/corrections'
  );
  const body = JSON.parse(String(calls[0]?.init?.body));
  assert.equal(body.delta_quantity, -1);
  assert.equal(body.corrects_adjustment_id, 'adj-qty');
  assert.equal(body.version, 8);
  assert.equal(receipt.inventoryAdjustmentId, 'adj-correction');
  assert.equal(receipt.message, 'correction recorded');
});

test('getInventoryItemDetail maps trust review fields from the backend read model', async () => {
  globalThis.fetch = (async () =>
    jsonResponse(200, {
      inventory_item_id: 'item-7',
      household_id: 'household-abc',
      name: 'Spinach',
      storage_location: 'fridge',
      quantity_on_hand: 2,
      primary_unit: 'bags',
      freshness: {
        basis: 'estimated',
        best_before: '2026-03-12T00:00:00Z',
        estimated_note: 'store estimate',
      },
      is_active: true,
      version: 4,
      updated_at: '2026-03-08T14:00:00Z',
      history_summary: {
        committed_adjustment_count: 3,
        correction_count: 1,
        latest_adjustment_id: 'adj-3',
        latest_mutation_type: 'set_metadata',
        latest_actor_user_id: 'user-123',
        latest_created_at: '2026-03-08T13:30:00Z',
      },
      latest_adjustment: {
        inventory_adjustment_id: 'adj-3',
        inventory_item_id: 'item-7',
        household_id: 'household-abc',
        mutation_type: 'set_metadata',
        reason_code: 'manual_edit',
        actor_user_id: 'user-123',
        created_at: '2026-03-08T13:30:00Z',
        freshness_transition: {
          changed: true,
          before: {
            basis: 'unknown',
          },
          after: {
            basis: 'estimated',
            best_before: '2026-03-12T00:00:00Z',
            estimated_note: 'store estimate',
          },
        },
        correction_links: {
          is_correction: false,
          is_corrected: false,
          corrected_by_adjustment_ids: [],
        },
      },
    })) as typeof fetch;

  const detail = await getInventoryItemDetail('item-7');

  assert.equal(detail.inventoryItemId, 'item-7');
  assert.equal(detail.freshnessBasis, 'estimated');
  assert.equal(detail.estimatedExpiryDate, '2026-03-12T00:00:00Z');
  assert.equal(detail.historySummary?.committedAdjustmentCount, 3);
  assert.equal(detail.latestAdjustment?.freshnessTransition?.after?.basis, 'estimated');
  assert.equal(detail.latestAdjustment?.freshnessTransition?.after?.estimatedNote, 'store estimate');
});

test('getInventoryHistory maps paginated correction chains directly from the API', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(200, {
      entries: [
        {
          inventory_adjustment_id: 'adj-correction',
          inventory_item_id: 'item-7',
          household_id: 'household-abc',
          mutation_type: 'correction',
          delta_quantity: -2,
          quantity_before: 5,
          quantity_after: 3,
          reason_code: 'correction',
          actor_user_id: 'user-123',
          client_mutation_id: 'mutation-correction',
          created_at: '2026-03-08T15:00:00Z',
          primary_unit: 'bags',
          quantity_transition: {
            before: 5,
            after: 3,
            delta: -2,
            unit: 'bags',
            changed: true,
          },
          workflow_reference: {
            correlation_id: 'corr-1',
            causal_workflow_id: 'wf-7',
            causal_workflow_type: 'shopping_reconciliation',
          },
          correction_links: {
            is_correction: true,
            is_corrected: false,
            corrects_adjustment_id: 'adj-shopping',
            corrected_by_adjustment_ids: [],
          },
        },
      ],
      total: 7,
      limit: 1,
      offset: 2,
      has_more: true,
      summary: {
        committed_adjustment_count: 7,
        correction_count: 1,
        latest_adjustment_id: 'adj-correction',
        latest_mutation_type: 'correction',
        latest_actor_user_id: 'user-123',
        latest_created_at: '2026-03-08T15:00:00Z',
      },
    });
  }) as typeof fetch;

  const history = await getInventoryHistory('item-7', { limit: 1, offset: 2 });

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/inventory/item-7/history?limit=1&offset=2'
  );
  assert.equal(history.total, 7);
  assert.equal(history.hasMore, true);
  assert.equal(history.entries[0]?.correctionLinks.correctsAdjustmentId, 'adj-shopping');
  assert.equal(history.entries[0]?.workflowReference?.causalWorkflowType, 'shopping_reconciliation');
  assert.equal(history.summary.correctionCount, 1);
});

