import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  applySyncOutcomeToMutation,
  createConfirmedListSnapshot,
  createInMemoryOfflineSyncDriver,
  createOfflineConflictRecord,
  createOfflineSyncScope,
  createOfflineSyncStore,
  createQueuedMutationRecord,
  getOfflineSyncStatus,
  markQueuedMutationRetryable,
} from './offline-sync';
import type { GroceryList } from './types';

function createConfirmedList(
  overrides: Partial<GroceryList> = {}
): GroceryList {
  return {
    groceryListId: 'grocery-1',
    householdId: 'household-1',
    planPeriodStart: '2026-03-09',
    planPeriodEnd: '2026-03-15',
    lines: [
      {
        groceryLineId: 'line-1',
        groceryListId: 'grocery-1',
        groceryListVersionId: 'version-4',
        name: 'Tomatoes',
        ingredientRefId: 'ingredient-1',
        quantityNeeded: 4,
        unit: 'ea',
        quantityCoveredByInventory: 1,
        quantityToBuy: 3,
        origin: 'derived',
        mealSources: [
          {
            mealSlotId: 'slot-1',
            mealName: 'Pasta Night',
            contributedQuantity: 4,
          },
        ],
        offsetInventoryItemId: 'inventory-1',
        offsetInventoryItemVersion: 3,
        userAdjustedQuantity: null,
        userAdjustmentNote: null,
        userAdjustmentFlagged: false,
        adHocNote: null,
        active: true,
        createdAt: '2026-03-09T09:00:00Z',
        updatedAt: '2026-03-09T09:05:00Z',
      },
    ],
    derivedFromPlanId: 'plan-1',
    lastDerivedAt: '2026-03-09T09:00:00Z',
    confirmedAt: '2026-03-09T10:00:00Z',
    tripState: 'confirmed_list_ready',
    isStale: false,
    status: 'confirmed',
    currentVersionNumber: 4,
    currentVersionId: 'version-4',
    confirmedPlanVersion: 7,
    inventorySnapshotReference: 'inventory-5',
    incompleteSlotWarnings: [],
    ...overrides,
  };
}

test('createConfirmedListSnapshot stores the locked Milestone 4 confirmed-list seam', () => {
  const list = createConfirmedList();
  const snapshot = createConfirmedListSnapshot(list, '2026-03-09T11:00:00Z');

  assert.ok(snapshot);
  assert.equal(snapshot.scope.groceryListVersionId, 'version-4');
  assert.equal(snapshot.bootstrap.aggregate.aggregateVersion, 4);
  assert.equal(snapshot.mealPlanContext.confirmedPlanVersion, 7);
  assert.equal(snapshot.inventorySnapshot.inventorySnapshotReference, 'inventory-5');
});

test('confirmed snapshot storage persists grocery list snapshot plus related context by household', async () => {
  const store = createOfflineSyncStore(createInMemoryOfflineSyncDriver());
  const older = createConfirmedListSnapshot(
    createConfirmedList({
      groceryListId: 'grocery-older',
      currentVersionId: 'version-3',
      currentVersionNumber: 3,
      confirmedAt: '2026-03-09T08:00:00Z',
    }),
    '2026-03-09T08:30:00Z'
  );
  const latest = createConfirmedListSnapshot(createConfirmedList(), '2026-03-09T11:30:00Z');

  assert.ok(older);
  assert.ok(latest);

  await store.saveConfirmedListSnapshot(older);
  await store.saveConfirmedListSnapshot(latest);

  const hydrated = await store.getLatestConfirmedListSnapshot('household-1');

  assert.ok(hydrated);
  assert.equal(hydrated.groceryList.currentVersionId, 'version-4');
  assert.equal(hydrated.mealPlanContext.planPeriodStart, '2026-03-09');
  assert.equal(hydrated.inventorySnapshot.inventorySnapshotReference, 'inventory-5');
});

test('retry state and review-required conflict preservation stay durable across store reloads', async () => {
  const store = createOfflineSyncStore(createInMemoryOfflineSyncDriver());
  const list = createConfirmedList();
  const scope = createOfflineSyncScope(list);
  assert.ok(scope);

  const queued = createQueuedMutationRecord(
    {
      clientMutationId: 'offline-001',
      householdId: 'household-1',
      actorId: 'user-1',
      aggregateType: 'grocery_line',
      aggregateId: 'line-1',
      provisionalAggregateId: null,
      mutationType: 'adjust_quantity',
      payload: { quantity_to_buy: 3 },
      baseServerVersion: 4,
      deviceTimestamp: '2026-03-09T11:31:00Z',
      localQueueStatus: 'queued_offline',
      scope,
    },
    '2026-03-09T11:31:00Z'
  );

  await store.enqueueMutation(queued);

  const retrying = markQueuedMutationRetryable(
    queued,
    'Connection lost.',
    '2026-03-09T11:32:00Z'
  );
  await store.enqueueMutation(retrying);

  const reviewed = applySyncOutcomeToMutation(
    retrying,
    {
      clientMutationId: 'offline-001',
      mutationType: 'adjust_quantity',
      aggregate: {
        aggregateType: 'grocery_line',
        aggregateId: 'line-1',
        aggregateVersion: 6,
        provisionalAggregateId: null,
      },
      outcome: 'review_required_quantity',
      authoritativeServerVersion: 6,
      conflictId: 'conflict-1',
      retryable: false,
      duplicateOfClientMutationId: null,
      autoMergeReason: null,
    },
    '2026-03-09T11:33:00Z'
  );
  await store.enqueueMutation(reviewed);

  const conflict = createOfflineConflictRecord(
    {
      conflict: {
        conflictId: 'conflict-1',
        householdId: 'household-1',
        aggregate: {
          aggregateType: 'grocery_line',
          aggregateId: 'line-1',
          aggregateVersion: 6,
          provisionalAggregateId: null,
        },
        localMutationId: 'offline-001',
        mutationType: 'adjust_quantity',
        outcome: 'review_required_quantity',
        baseServerVersion: 4,
        currentServerVersion: 6,
        requiresReview: true,
        summary: 'Quantity changed on another client.',
        localQueueStatus: 'review_required',
        allowedResolutionActions: ['keep_mine', 'use_server'],
        resolutionStatus: 'pending',
        createdAt: '2026-03-09T11:33:00Z',
        resolvedAt: null,
        resolvedByActorId: null,
        localIntentSummary: { quantity_to_buy: 3 },
        baseStateSummary: { quantity_to_buy: 2 },
        serverStateSummary: { quantity_to_buy: 4 },
      },
      scope,
      localMutation: reviewed,
    },
    '2026-03-09T11:33:00Z'
  );
  await store.saveConflict(conflict);

  const [queueState, conflicts, storedMutation] = await Promise.all([
    store.getQueueState('household-1'),
    store.listConflicts('household-1'),
    store.getQueuedMutation('offline-001'),
  ]);

  assert.equal(queueState.retryingCount, 0);
  assert.equal(queueState.reviewRequiredCount, 1);
  assert.equal(queueState.conflictCount, 1);
  assert.equal(getOfflineSyncStatus(queueState, true), 'review_required');
  assert.equal(storedMutation?.localQueueStatus, 'review_required');
  assert.equal(storedMutation?.baseServerVersion, 6);
  assert.equal(conflicts[0]?.localMutation?.retryCount, 1);
  assert.equal(conflicts[0]?.conflict.serverStateSummary.quantity_to_buy, 4);
});

test('clearing a resolved conflict removes it from the saved review queue', async () => {
  const store = createOfflineSyncStore(createInMemoryOfflineSyncDriver());
  const list = createConfirmedList();
  const scope = createOfflineSyncScope(list);
  assert.ok(scope);

  const reviewed = createQueuedMutationRecord(
    {
      clientMutationId: 'offline-002',
      householdId: 'household-1',
      actorId: 'user-1',
      aggregateType: 'grocery_line',
      aggregateId: 'line-1',
      provisionalAggregateId: null,
      mutationType: 'adjust_quantity',
      payload: { quantity_to_buy: 5 },
      baseServerVersion: 6,
      deviceTimestamp: '2026-03-09T12:01:00Z',
      localQueueStatus: 'review_required',
      scope,
    },
    '2026-03-09T12:01:00Z'
  );
  await store.enqueueMutation(reviewed);

  await store.saveConflict(
    createOfflineConflictRecord(
      {
        conflict: {
          conflictId: 'conflict-2',
          householdId: 'household-1',
          aggregate: {
            aggregateType: 'grocery_line',
            aggregateId: 'line-1',
            aggregateVersion: 6,
            provisionalAggregateId: null,
          },
          localMutationId: 'offline-002',
          mutationType: 'adjust_quantity',
          outcome: 'review_required_quantity',
          baseServerVersion: 4,
          currentServerVersion: 6,
          requiresReview: true,
          summary: 'Quantity changed on another client.',
          localQueueStatus: 'review_required',
          allowedResolutionActions: ['keep_mine', 'use_server'],
          resolutionStatus: 'pending',
          createdAt: '2026-03-09T12:01:00Z',
          resolvedAt: null,
          resolvedByActorId: null,
          localIntentSummary: { quantity_to_buy: 5 },
          baseStateSummary: { quantity_to_buy: 3 },
          serverStateSummary: { quantity_to_buy: 2 },
        },
        scope,
        localMutation: reviewed,
      },
      '2026-03-09T12:01:00Z'
    )
  );

  await store.clearQueuedMutation('offline-002');
  await store.clearConflict('conflict-2');

  const queueState = await store.getQueueState('household-1');
  assert.equal(queueState.reviewRequiredCount, 0);
  assert.equal(queueState.conflictCount, 0);
  assert.equal(getOfflineSyncStatus(queueState, true), 'idle');
});
