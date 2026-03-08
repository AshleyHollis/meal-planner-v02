import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  formatConflictDetailValue,
  getConflictDetailFields,
  getConflictOutcomeDescription,
  getConflictOutcomeLabel,
  getConflictResolutionActionCopy,
  getActiveLines,
  getConfirmationSummary,
  getEffectiveQuantity,
  getMealTraceLabel,
  getRemovedLines,
  getReviewHeadline,
  getReviewSummary,
  hasQuantityOverride,
} from './grocery-ui';
import type { GroceryList } from './types';

function createList(overrides: Partial<GroceryList> = {}): GroceryList {
  return {
    groceryListId: 'grocery-1',
    householdId: 'household-1',
    planPeriodStart: '2026-03-09',
    planPeriodEnd: '2026-03-15',
    derivedFromPlanId: 'plan-1',
    lastDerivedAt: '2026-03-08T10:00:00Z',
    confirmedAt: null,
    tripState: 'confirmed_list_ready',
    isStale: false,
    status: 'draft',
    currentVersionNumber: 1,
    currentVersionId: 'version-1',
    confirmedPlanVersion: 2,
    inventorySnapshotReference: 'inventory-1',
    incompleteSlotWarnings: [],
    lines: [
      {
        groceryLineId: 'line-derived',
        groceryListId: 'grocery-1',
        groceryListVersionId: 'version-1',
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
        userAdjustedQuantity: 5,
        userAdjustmentNote: 'Party night',
        userAdjustmentFlagged: true,
        adHocNote: null,
        active: true,
        createdAt: '2026-03-08T10:00:00Z',
        updatedAt: '2026-03-08T10:05:00Z',
      },
      {
        groceryLineId: 'line-ad-hoc',
        groceryListId: 'grocery-1',
        groceryListVersionId: 'version-1',
        name: 'Tea',
        ingredientRefId: null,
        quantityNeeded: 1,
        unit: 'box',
        quantityCoveredByInventory: 0,
        quantityToBuy: 1,
        origin: 'ad_hoc',
        mealSources: [],
        offsetInventoryItemId: null,
        offsetInventoryItemVersion: null,
        userAdjustedQuantity: null,
        userAdjustmentNote: null,
        userAdjustmentFlagged: false,
        adHocNote: 'For guests',
        active: true,
        createdAt: '2026-03-08T10:00:00Z',
        updatedAt: '2026-03-08T10:05:00Z',
      },
      {
        groceryLineId: 'line-removed',
        groceryListId: 'grocery-1',
        groceryListVersionId: 'version-1',
        name: 'Bananas',
        ingredientRefId: null,
        quantityNeeded: 6,
        unit: 'ea',
        quantityCoveredByInventory: 0,
        quantityToBuy: 6,
        origin: 'derived',
        mealSources: [],
        offsetInventoryItemId: null,
        offsetInventoryItemVersion: null,
        userAdjustedQuantity: null,
        userAdjustmentNote: null,
        userAdjustmentFlagged: false,
        adHocNote: null,
        active: false,
        createdAt: '2026-03-08T10:00:00Z',
        updatedAt: '2026-03-08T10:05:00Z',
      },
    ],
    ...overrides,
  };
}

test('grocery review helpers prefer user overrides and separate active from removed lines', () => {
  const list = createList();

  assert.equal(getEffectiveQuantity(list.lines[0]!), 5);
  assert.equal(hasQuantityOverride(list.lines[0]!), true);
  assert.equal(getActiveLines(list).length, 2);
  assert.equal(getRemovedLines(list).length, 1);
});

test('grocery review summary counts active derived, ad hoc, warnings, and overrides', () => {
  const list = createList({
    incompleteSlotWarnings: [
      {
        mealSlotId: 'slot-4',
        mealName: 'Friday Dinner',
        reason: 'missing_ingredient_data',
        message: 'Recipe ingredients are incomplete.',
      },
    ],
  });

  assert.deepEqual(getReviewSummary(list), {
    activeLineCount: 2,
    removedLineCount: 1,
    derivedLineCount: 1,
    adHocLineCount: 1,
    warningCount: 1,
    overrideCount: 1,
  });
  assert.equal(getConfirmationSummary(list), '2 shopping lines • 1 ad hoc • 1 override');
});

test('grocery review headline prioritizes stale warnings over other review copy', () => {
  const stale = createList({ status: 'stale_draft', isStale: true });
  const warned = createList({
    incompleteSlotWarnings: [
      {
        mealSlotId: 'slot-4',
        mealName: 'Friday Dinner',
        reason: 'missing_ingredient_data',
        message: null,
      },
    ],
  });
  const overridden = createList();

  assert.equal(getReviewHeadline(stale), 'This draft is stale. Review changes before confirming.');
  assert.equal(getReviewHeadline(warned), 'Some meals could not fully derive grocery needs.');
  assert.equal(getReviewHeadline(overridden), 'User quantity overrides are active on this draft.');
});

test('meal trace labels deduplicate repeated meal names and fall back to slot ids', () => {
  const list = createList();
  const derivedLine = list.lines[0]!;
  const repeatedMealLine = {
    ...derivedLine,
    mealSources: [
      ...derivedLine.mealSources,
      {
        mealSlotId: 'slot-2',
        mealName: 'Pasta Night',
        contributedQuantity: 1,
      },
      {
        mealSlotId: 'slot-3',
        mealName: null,
        contributedQuantity: 2,
      },
    ],
  };

  assert.equal(getMealTraceLabel(repeatedMealLine), 'From Pasta Night, Meal slot slot-3');
  assert.equal(getMealTraceLabel({ ...derivedLine, mealSources: [] }), null);
});

test('confirmation summary omits ad hoc and override fragments when not present', () => {
  const list = createList({
    lines: [
      {
        ...createList().lines[0]!,
        groceryLineId: 'line-derived-only',
        userAdjustedQuantity: null,
        userAdjustmentNote: null,
        userAdjustmentFlagged: false,
        active: true,
      },
      {
        ...createList().lines[2]!,
        groceryLineId: 'line-removed-only',
      },
    ],
  });

  assert.equal(getConfirmationSummary(list), '1 shopping line');
});

test('conflict helpers keep review-required copy explicit and human-readable', () => {
  assert.equal(getConflictOutcomeLabel('review_required_quantity'), 'Quantity conflict');
  assert.match(
    getConflictOutcomeDescription('review_required_deleted_or_archived'),
    /no longer active on the server/i
  );
  assert.match(
    getConflictResolutionActionCopy('keep_mine'),
    /replays your saved intent/i
  );
});

test('conflict detail field formatting keeps saved summaries readable on mobile', () => {
  assert.equal(formatConflictDetailValue(true), 'Yes');
  assert.equal(formatConflictDetailValue(['pantry', 'fridge']), 'pantry, fridge');

  assert.deepEqual(
    getConflictDetailFields({
      ingredient_name: 'Tomatoes',
      quantity_to_buy: 3,
      storage_location: 'fridge',
      active: false,
    }),
    [
      { key: 'ingredient_name', label: 'Item', value: 'Tomatoes' },
      { key: 'quantity_to_buy', label: 'Quantity to buy', value: '3' },
      { key: 'storage_location', label: 'Storage location', value: 'fridge' },
      { key: 'active', label: 'Still active', value: 'No' },
    ]
  );
});
