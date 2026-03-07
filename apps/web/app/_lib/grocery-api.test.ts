import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import {
  addAdHocLine,
  adjustGroceryLine,
  confirmGroceryList,
  deriveGroceryList,
  getSyncConflict,
  getGroceryList,
  listSyncConflicts,
  mapConfirmedListBootstrap,
  mapSyncConflictDetail,
  mapSyncMutationOutcome,
  removeGroceryLine,
  resolveSyncConflictKeepMine,
  resolveSyncConflictUseServer,
  rederiveGroceryList,
  uploadSyncMutations,
} from './grocery-api';

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

test('getGroceryList maps the backend grocery read model and lifecycle statuses', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(200, {
      id: 'grocery-1',
      household_id: 'household-abc',
      plan_period_start: '2026-03-09',
      plan_period_end: '2026-03-15',
      meal_plan_id: 'plan-1',
      status: 'stale_draft',
      current_version_number: 3,
      current_version_id: 'version-3',
      last_derived_at: '2026-03-08T10:00:00Z',
      confirmed_plan_version: 7,
      inventory_snapshot_reference: 'inventory-v5',
      is_stale: true,
      incomplete_slot_warnings: [
        {
          meal_slot_id: 'slot-4',
          meal_name: 'Friday Dinner',
          reason: 'missing_ingredient_data',
          message: 'Recipe ingredients are incomplete.',
        },
      ],
      lines: [
        {
          id: 'line-1',
          grocery_list_id: 'grocery-1',
          grocery_list_version_id: 'version-3',
          ingredient_name: 'Tomatoes',
          ingredient_ref_id: 'ingredient-1',
          required_quantity: '4.5',
          unit: 'ea',
          offset_quantity: '1.5',
          shopping_quantity: '3',
          origin: 'derived',
          meal_sources: [
            {
              meal_slot_id: 'slot-1',
              meal_name: 'Pasta Night',
              contributed_quantity: '2',
            },
          ],
          offset_inventory_item_id: 'inventory-1',
          offset_inventory_item_version: 9,
          user_adjusted_quantity: null,
          user_adjustment_note: null,
          user_adjustment_flagged: true,
          ad_hoc_note: null,
          active: true,
          created_at: '2026-03-08T10:00:00Z',
          updated_at: '2026-03-08T10:05:00Z',
        },
      ],
    });
  }) as typeof fetch;

  const list = await getGroceryList('household-abc', '2026-03-09');

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/households/household-abc/grocery?period=2026-03-09'
  );
  assert.ok(list);
  assert.equal(list?.status, 'stale_draft');
  assert.equal(list?.tripState, 'confirmed_list_ready');
  assert.equal(list?.currentVersionId, 'version-3');
  assert.equal(list?.incompleteSlotWarnings[0]?.mealName, 'Friday Dinner');
  assert.equal(list?.lines[0]?.origin, 'derived');
  assert.equal(list?.lines[0]?.mealSources[0]?.mealName, 'Pasta Night');
  assert.equal(list?.lines[0]?.quantityNeeded, 4.5);
  assert.equal(list?.lines[0]?.quantityToBuy, 3);
  assert.equal(list?.lines[0]?.quantityCoveredByInventory, 1.5);
  assert.equal(list?.lines[0]?.userAdjustmentFlagged, true);
});

test('getGroceryList returns null when the backend has no grocery list for the period', async () => {
  globalThis.fetch = (async () => jsonResponse(404, { detail: 'not found' })) as typeof fetch;

  const list = await getGroceryList('household-abc', '2026-03-09');

  assert.equal(list, null);
});

test('deriveGroceryList posts the real derive command and unwraps the mutation result', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(201, {
      mutation_kind: 'derive',
      grocery_list: {
        id: 'grocery-2',
        household_id: 'household-abc',
        plan_period_start: '2026-03-09',
        status: 'draft',
        current_version_number: 1,
        current_version_id: 'version-1',
        is_stale: false,
        lines: [],
        incomplete_slot_warnings: [],
      },
      is_duplicate: false,
    });
  }) as typeof fetch;

  const list = await deriveGroceryList('household-abc', '2026-03-09', 'derive-1');

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/households/household-abc/grocery/derive'
  );
  assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
    household_id: 'household-abc',
    plan_period_start: '2026-03-09',
    client_mutation_id: 'derive-1',
  });
  assert.equal(list.groceryListId, 'grocery-2');
  assert.equal(list.status, 'draft');
});

test('rederive, confirm, addAdHocLine, adjust, and remove use the approved grocery mutation contracts', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    if (calls.length === 1) {
      return jsonResponse(200, {
        mutation_kind: 'rederive',
        grocery_list: {
          id: 'grocery-3',
          household_id: 'household-abc',
          plan_period_start: '2026-03-09',
          status: 'draft',
          current_version_number: 4,
          current_version_id: 'version-4',
          is_stale: false,
          lines: [],
          incomplete_slot_warnings: [],
        },
      });
    }
    if (calls.length === 2) {
      return jsonResponse(200, {
        mutation_kind: 'confirm_list',
        grocery_list: {
          id: 'grocery-3',
          household_id: 'household-abc',
          plan_period_start: '2026-03-09',
          status: 'confirmed',
          current_version_number: 4,
          current_version_id: 'version-4',
          confirmed_at: '2026-03-08T12:00:00Z',
          is_stale: false,
          lines: [],
          incomplete_slot_warnings: [],
        },
      });
    }
    if (calls.length === 3) {
      return jsonResponse(201, {
        mutation_kind: 'add_ad_hoc',
        grocery_list: {
          id: 'grocery-3',
          household_id: 'household-abc',
          plan_period_start: '2026-03-09',
          status: 'draft',
          current_version_number: 4,
          current_version_id: 'version-4',
          is_stale: false,
          lines: [
            {
              id: 'line-ad-hoc',
              grocery_list_id: 'grocery-3',
              grocery_list_version_id: 'version-4',
              ingredient_name: 'Tea bags',
              required_quantity: '2',
              shopping_quantity: '2',
              offset_quantity: '0',
              unit: 'box',
              origin: 'ad_hoc',
              meal_sources: [],
              user_adjustment_flagged: false,
              ad_hoc_note: 'For the trip',
              active: true,
              created_at: '2026-03-08T12:05:00Z',
              updated_at: '2026-03-08T12:05:00Z',
            },
          ],
          incomplete_slot_warnings: [],
        },
      });
    }
    if (calls.length === 4) {
      return jsonResponse(200, {
        mutation_kind: 'adjust_line',
        grocery_list: {
          id: 'grocery-3',
          household_id: 'household-abc',
          plan_period_start: '2026-03-09',
          status: 'draft',
          current_version_number: 4,
          current_version_id: 'version-4',
          is_stale: false,
          lines: [
            {
              id: 'line-ad-hoc',
              grocery_list_id: 'grocery-3',
              grocery_list_version_id: 'version-4',
              ingredient_name: 'Tea bags',
              required_quantity: '2',
              shopping_quantity: '2',
              offset_quantity: '0',
              unit: 'box',
              origin: 'ad_hoc',
              meal_sources: [],
              user_adjusted_quantity: '3',
              user_adjustment_note: 'Need extra',
              user_adjustment_flagged: true,
              active: true,
              created_at: '2026-03-08T12:05:00Z',
              updated_at: '2026-03-08T12:06:00Z',
            },
          ],
          incomplete_slot_warnings: [],
        },
      });
    }
    return jsonResponse(200, {
      mutation_kind: 'remove_line',
      grocery_list: {
        id: 'grocery-3',
        household_id: 'household-abc',
        plan_period_start: '2026-03-09',
        status: 'draft',
        current_version_number: 4,
        current_version_id: 'version-4',
        is_stale: false,
        lines: [
          {
            id: 'line-ad-hoc',
            grocery_list_id: 'grocery-3',
            grocery_list_version_id: 'version-4',
            ingredient_name: 'Tea bags',
            required_quantity: '2',
            shopping_quantity: '2',
            offset_quantity: '0',
            unit: 'box',
            origin: 'ad_hoc',
            meal_sources: [],
            user_adjustment_flagged: false,
            active: false,
            created_at: '2026-03-08T12:05:00Z',
            updated_at: '2026-03-08T12:07:00Z',
          },
        ],
        incomplete_slot_warnings: [],
      },
    });
  }) as typeof fetch;

  const rederived = await rederiveGroceryList(
    'household-abc',
    'grocery-3',
    '2026-03-09',
    'rederive-1'
  );
  const confirmed = await confirmGroceryList('household-abc', 'grocery-3', 'confirm-1');
  const updated = await addAdHocLine(
    'household-abc',
    'grocery-3',
    'Tea bags',
    2,
    'box',
    'add-1',
    'For the trip'
  );
  const adjusted = await adjustGroceryLine(
    'household-abc',
    'grocery-3',
    'line-ad-hoc',
    3,
    'adjust-1',
    'Need extra'
  );
  const removed = await removeGroceryLine('household-abc', 'grocery-3', 'line-ad-hoc', 'remove-1');

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/households/household-abc/grocery/grocery-3/rederive'
  );
  assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
    household_id: 'household-abc',
    plan_period_start: '2026-03-09',
    client_mutation_id: 'rederive-1',
  });
  assert.equal(
    String(calls[1]?.input),
    '/api/v1/households/household-abc/grocery/grocery-3/confirm'
  );
  assert.deepEqual(JSON.parse(String(calls[1]?.init?.body)), {
    grocery_list_id: 'grocery-3',
    household_id: 'household-abc',
    client_mutation_id: 'confirm-1',
  });
  assert.equal(
    String(calls[2]?.input),
    '/api/v1/households/household-abc/grocery/grocery-3/lines'
  );
  assert.deepEqual(JSON.parse(String(calls[2]?.init?.body)), {
    grocery_list_id: 'grocery-3',
    household_id: 'household-abc',
    ingredient_name: 'Tea bags',
    shopping_quantity: 2,
    unit: 'box',
    ad_hoc_note: 'For the trip',
    client_mutation_id: 'add-1',
  });
  assert.equal(
    String(calls[3]?.input),
    '/api/v1/households/household-abc/grocery/grocery-3/lines/line-ad-hoc'
  );
  assert.deepEqual(JSON.parse(String(calls[3]?.init?.body)), {
    grocery_list_item_id: 'line-ad-hoc',
    household_id: 'household-abc',
    user_adjusted_quantity: 3,
    user_adjustment_note: 'Need extra',
    client_mutation_id: 'adjust-1',
  });
  assert.equal(
    String(calls[4]?.input),
    '/api/v1/households/household-abc/grocery/grocery-3/lines/line-ad-hoc/remove'
  );
  assert.deepEqual(JSON.parse(String(calls[4]?.init?.body)), {
    grocery_list_item_id: 'line-ad-hoc',
    household_id: 'household-abc',
    client_mutation_id: 'remove-1',
  });
  assert.equal(rederived.currentVersionNumber, 4);
  assert.equal(confirmed.status, 'confirmed');
  assert.equal(updated.lines[0]?.origin, 'ad_hoc');
  assert.equal(adjusted.lines[0]?.userAdjustedQuantity, 3);
  assert.equal(removed.lines[0]?.active, false);
});

test('confirmed list bootstrap mapping preserves aggregate identity and trip bootstrap state', () => {
  const bootstrap = mapConfirmedListBootstrap({
    household_id: 'household-abc',
    grocery_list_id: 'grocery-3',
    grocery_list_version_id: 'version-4',
    grocery_list_status: 'confirmed',
    trip_state: 'confirmed_list_ready',
    aggregate: {
      aggregate_type: 'grocery_list',
      aggregate_id: 'grocery-3',
      aggregate_version: 4,
    },
    confirmed_at: '2026-03-08T12:00:00Z',
    confirmed_plan_version: 7,
    inventory_snapshot_reference: 'inventory-v5',
    incomplete_slot_warnings: [
      {
        meal_slot_id: 'slot-4',
        meal_name: 'Friday Dinner',
        reason: 'missing_ingredient_data',
      },
    ],
    lines: [
      {
        id: 'line-1',
        grocery_list_id: 'grocery-3',
        grocery_list_version_id: 'version-4',
        ingredient_name: 'Tomatoes',
        required_quantity: '3',
        offset_quantity: '1',
        shopping_quantity: '2',
        unit: 'ea',
        origin: 'derived',
        meal_sources: [],
        user_adjustment_flagged: false,
        active: true,
        created_at: '2026-03-08T10:00:00Z',
        updated_at: '2026-03-08T10:05:00Z',
      },
    ],
  });

  assert.equal(bootstrap.tripState, 'confirmed_list_ready');
  assert.equal(bootstrap.aggregate.aggregateVersion, 4);
  assert.equal(bootstrap.lines[0]?.groceryLineId, 'line-1');
});

test('sync mutation outcome and conflict detail mapping preserve Milestone 4 conflict contract fields', () => {
  const outcome = mapSyncMutationOutcome({
    client_mutation_id: 'offline-001',
    mutation_type: 'adjust_quantity',
    aggregate: {
      aggregate_type: 'grocery_line',
      aggregate_id: 'line-1',
      current_server_version: 7,
    },
    outcome: 'duplicate_retry',
    authoritative_server_version: 7,
    duplicate_of_client_mutation_id: 'offline-000',
  });
  const conflict = mapSyncConflictDetail({
    conflict_id: 'conflict-001',
    household_id: 'household-abc',
    aggregate: {
      aggregate_type: 'grocery_line',
      aggregate_id: 'line-1',
      aggregate_version: 8,
    },
    local_mutation_id: 'offline-001',
    mutation_type: 'adjust_quantity',
    outcome: 'review_required_quantity',
    base_server_version: 6,
    current_server_version: 8,
    requires_review: true,
    summary: 'Quantity changed on both clients.',
    local_queue_status: 'review_required',
    allowed_resolution_actions: ['keep_mine', 'use_server'],
    resolution_status: 'pending',
    created_at: '2026-03-08T12:10:00Z',
    local_intent_summary: { quantity_to_buy: 3 },
    base_state_summary: { quantity_to_buy: 2 },
    server_state_summary: { quantity_to_buy: 4 },
  });

  assert.equal(outcome.aggregate.aggregateVersion, 7);
  assert.equal(outcome.duplicateOfClientMutationId, 'offline-000');
  assert.equal(conflict.localQueueStatus, 'review_required');
  assert.deepEqual(conflict.allowedResolutionActions, ['keep_mine', 'use_server']);
  assert.equal(conflict.serverStateSummary.quantity_to_buy, 4);
});

test('sync upload and conflict reads use the approved Milestone 4 endpoints', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    const url = String(input);

    if (url.endsWith('/sync/upload')) {
      return jsonResponse(200, [
        {
          client_mutation_id: 'trip-1',
          mutation_type: 'remove_line',
          aggregate: {
            aggregate_type: 'grocery_line',
            aggregate_id: 'line-1',
            aggregate_version: 5,
          },
          outcome: 'applied',
          authoritative_server_version: 5,
          conflict_id: null,
          retryable: false,
          duplicate_of_client_mutation_id: null,
          auto_merge_reason: null,
        },
      ]);
    }

    if (url.endsWith('/sync/conflicts/conflict-1')) {
      return jsonResponse(200, {
        conflict_id: 'conflict-1',
        household_id: 'household-abc',
        aggregate: {
          aggregate_type: 'grocery_line',
          aggregate_id: 'line-1',
          aggregate_version: 6,
        },
        local_mutation_id: 'trip-2',
        mutation_type: 'adjust_quantity',
        outcome: 'review_required_quantity',
        base_server_version: 4,
        current_server_version: 6,
        requires_review: true,
        summary: 'Quantity changed on another client.',
        local_queue_status: 'review_required',
        allowed_resolution_actions: ['keep_mine', 'use_server'],
        resolution_status: 'pending',
        created_at: '2026-03-09T11:33:00Z',
        resolved_at: null,
        resolved_by_actor_id: null,
        local_intent_summary: { quantity_to_buy: 3 },
        base_state_summary: { quantity_to_buy: 2 },
        server_state_summary: { quantity_to_buy: 4 },
      });
    }

    return jsonResponse(200, [
      {
        conflict_id: 'conflict-1',
        household_id: 'household-abc',
        aggregate: {
          aggregate_type: 'grocery_line',
          aggregate_id: 'line-1',
          aggregate_version: 6,
        },
        local_mutation_id: 'trip-2',
        mutation_type: 'adjust_quantity',
        outcome: 'review_required_quantity',
        base_server_version: 4,
        current_server_version: 6,
        requires_review: true,
        summary: 'Quantity changed on another client.',
        local_queue_status: 'review_required',
        allowed_resolution_actions: ['keep_mine', 'use_server'],
        resolution_status: 'pending',
        created_at: '2026-03-09T11:33:00Z',
        resolved_at: null,
        resolved_by_actor_id: null,
      },
    ]);
  }) as typeof fetch;

  const [outcomes, summaries, detail] = await Promise.all([
    uploadSyncMutations('household-abc', [
      {
        client_mutation_id: 'trip-1',
        household_id: 'household-abc',
        actor_id: 'user-1',
        aggregate_type: 'grocery_line',
        aggregate_id: 'line-1',
        provisional_aggregate_id: null,
        mutation_type: 'remove_line',
        payload: {
          grocery_line_id: 'line-1',
          grocery_list_id: 'grocery-1',
        },
        base_server_version: 4,
        device_timestamp: '2026-03-09T11:32:00Z',
        local_queue_status: 'queued_offline',
      },
    ]),
    listSyncConflicts('household-abc'),
    getSyncConflict('household-abc', 'conflict-1'),
  ]);

  assert.equal(String(calls[0]?.input), '/api/v1/households/household-abc/grocery/sync/upload');
  assert.equal(String(calls[1]?.input), '/api/v1/households/household-abc/grocery/sync/conflicts');
  assert.equal(
    String(calls[2]?.input),
    '/api/v1/households/household-abc/grocery/sync/conflicts/conflict-1'
  );
  assert.equal(outcomes[0]?.authoritativeServerVersion, 5);
  assert.equal(summaries[0]?.summary, 'Quantity changed on another client.');
  assert.equal(detail.serverStateSummary.quantity_to_buy, 4);
});

test('sync conflict resolution commands return refreshed grocery snapshots', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    const url = String(input);

    if (url.endsWith('/resolve-keep-mine')) {
      return jsonResponse(200, {
        mutation_kind: 'resolve_keep_mine',
        grocery_list: {
          id: 'grocery-1',
          household_id: 'household-abc',
          meal_plan_id: 'plan-1',
          status: 'trip_in_progress',
          current_version_number: 7,
          current_version_id: 'version-7',
          confirmed_at: '2026-03-09T10:00:00Z',
          trip_state: 'trip_in_progress',
          plan_period_start: '2026-03-09',
          plan_period_end: '2026-03-15',
          confirmed_plan_version: 3,
          inventory_snapshot_reference: 'inventory-v7',
          is_stale: false,
          incomplete_slot_warnings: [],
          lines: [
            {
              id: 'line-1',
              grocery_line_id: 'line-1',
              grocery_list_id: 'grocery-1',
              grocery_list_version_id: 'version-7',
              ingredient_name: 'Pasta',
              required_quantity: '500',
              unit: 'grams',
              offset_quantity: '0',
              shopping_quantity: '500',
              origin: 'derived',
              meal_sources: [],
              user_adjusted_quantity: '900',
              user_adjustment_note: 'Need extra',
              user_adjustment_flagged: true,
              active: true,
              created_at: '2026-03-09T10:00:00Z',
              updated_at: '2026-03-09T11:00:00Z',
            },
          ],
          created_at: '2026-03-09T10:00:00Z',
          updated_at: '2026-03-09T11:00:00Z',
        },
        item: null,
      });
    }

    return jsonResponse(200, {
      mutation_kind: 'resolve_use_server',
      grocery_list: {
        id: 'grocery-1',
        household_id: 'household-abc',
        meal_plan_id: 'plan-1',
        status: 'trip_in_progress',
        current_version_number: 7,
        current_version_id: 'version-7',
        confirmed_at: '2026-03-09T10:00:00Z',
        trip_state: 'trip_in_progress',
        plan_period_start: '2026-03-09',
        plan_period_end: '2026-03-15',
        confirmed_plan_version: 3,
        inventory_snapshot_reference: 'inventory-v7',
        is_stale: false,
        incomplete_slot_warnings: [],
        lines: [],
        created_at: '2026-03-09T10:00:00Z',
        updated_at: '2026-03-09T11:00:00Z',
      },
      item: null,
    });
  }) as typeof fetch;

  const [keptMine, usedServer] = await Promise.all([
    resolveSyncConflictKeepMine('household-abc', 'conflict-1', 'resolve-keep-001', 6),
    resolveSyncConflictUseServer('household-abc', 'conflict-2', 'resolve-server-001'),
  ]);

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/households/household-abc/grocery/sync/conflicts/conflict-1/resolve-keep-mine'
  );
  assert.equal(
    String(calls[1]?.input),
    '/api/v1/households/household-abc/grocery/sync/conflicts/conflict-2/resolve-use-server'
  );
  assert.equal(keptMine.currentVersionNumber, 7);
  assert.equal(keptMine.lines[0]?.userAdjustedQuantity, 900);
  assert.equal(usedServer.currentVersionId, 'version-7');
});

