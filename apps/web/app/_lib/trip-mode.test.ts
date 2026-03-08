import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  applyOptimisticTripAdHocLine,
  applyOptimisticTripCompletion,
  applyOptimisticTripQuantity,
  getTripProgressSummary,
} from './trip-mode';
import type { GroceryList } from './types';

function createConfirmedList(overrides: Partial<GroceryList> = {}): GroceryList {
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
        mealSources: [],
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
      {
        groceryLineId: 'line-2',
        groceryListId: 'grocery-1',
        groceryListVersionId: 'version-4',
        name: 'Milk',
        ingredientRefId: null,
        quantityNeeded: 1,
        unit: 'carton',
        quantityCoveredByInventory: 0,
        quantityToBuy: 1,
        origin: 'ad_hoc',
        mealSources: [],
        offsetInventoryItemId: null,
        offsetInventoryItemVersion: null,
        userAdjustedQuantity: null,
        userAdjustmentNote: null,
        userAdjustmentFlagged: false,
        adHocNote: 'For cereal',
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

test('trip progress summary separates remaining, completed, ad hoc, and adjusted lines', () => {
  const list = createConfirmedList({
    lines: [
      {
        ...createConfirmedList().lines[0]!,
        userAdjustedQuantity: 4,
        userAdjustmentFlagged: true,
      },
      {
        ...createConfirmedList().lines[1]!,
        active: false,
      },
    ],
  });

  assert.deepEqual(getTripProgressSummary(list), {
    totalLineCount: 2,
    remainingLineCount: 1,
    completedLineCount: 1,
    adHocLineCount: 0,
    adjustedLineCount: 1,
  });
});

test('optimistic trip updates move a confirmed list into trip mode without changing snapshot identity', () => {
  const list = createConfirmedList();
  const adjusted = applyOptimisticTripQuantity(
    list,
    'line-1',
    5,
    'Need extra',
    '2026-03-09T11:00:00Z'
  );
  const completed = applyOptimisticTripCompletion(adjusted, 'line-1', '2026-03-09T11:05:00Z');

  assert.equal(adjusted.status, 'trip_in_progress');
  assert.equal(adjusted.currentVersionId, 'version-4');
  assert.equal(adjusted.lines[0]?.userAdjustedQuantity, 5);
  assert.equal(adjusted.lines[0]?.userAdjustmentNote, 'Need extra');
  assert.equal(completed.lines[0]?.active, false);
});

test('optimistic ad hoc trip adds keep a local provisional line until the server assigns identity', () => {
  const list = createConfirmedList();
  const next = applyOptimisticTripAdHocLine(
    list,
    {
      provisionalLineId: 'local-line-1',
      name: 'Ice',
      quantity: 2,
      unit: 'bag',
      note: 'For the cooler',
    },
    '2026-03-09T11:10:00Z'
  );

  assert.equal(next.status, 'trip_in_progress');
  assert.equal(next.lines.length, 3);
  assert.equal(next.lines[2]?.groceryLineId, 'local-line-1');
  assert.equal(next.lines[2]?.origin, 'ad_hoc');
  assert.equal(next.lines[2]?.adHocNote, 'For the cooler');
});
