import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  describeAdjustmentSummary,
  describeFreshnessInfo,
  describeItemFreshness,
  formatMutationType,
  toDateInputValue,
} from './inventory-trust';

test('describeItemFreshness keeps estimated freshness visibly labeled', () => {
  const label = describeItemFreshness({
    freshnessBasis: 'estimated',
    expiryDate: null,
    estimatedExpiryDate: '2026-03-12T00:00:00Z',
    freshnessNote: 'store estimate',
  });

  assert.equal(label, 'Estimated freshness · 2026-03-12');
});

test('describeFreshnessInfo preserves unknown basis instead of implying certainty', () => {
  assert.equal(
    describeFreshnessInfo({
      basis: 'unknown',
      bestBefore: null,
      estimatedNote: null,
    }),
    'Unknown freshness'
  );
});

test('describeAdjustmentSummary uses user-facing action labels', () => {
  const summary = describeAdjustmentSummary({
    inventoryAdjustmentId: 'adj-1',
    inventoryItemId: 'item-1',
    householdId: 'household-abc',
    mutationType: 'correction',
    deltaQuantity: -1,
    quantityBefore: 2,
    quantityAfter: 1,
    storageLocationBefore: 'fridge',
    storageLocationAfter: 'fridge',
    freshnessBefore: null,
    freshnessAfter: null,
    reasonCode: 'correction',
    actorUserId: 'user-1',
    correlationId: null,
    clientMutationId: 'mutation-1',
    causalWorkflowId: null,
    causalWorkflowType: null,
    correctsAdjustmentId: 'adj-0',
    note: 'Undo mistaken add',
    createdAt: '2026-03-08T15:00:00Z',
    primaryUnit: 'ea',
    quantityTransition: {
      before: 2,
      after: 1,
      delta: -1,
      unit: 'ea',
      changed: true,
    },
    locationTransition: null,
    freshnessTransition: null,
    workflowReference: null,
    correctionLinks: {
      correctsAdjustmentId: 'adj-0',
      correctedByAdjustmentIds: [],
      isCorrection: true,
      isCorrected: false,
    },
  });

  assert.match(summary, /Applied correction/);
});

test('helper formatting stays aligned with trust-review wording', () => {
  assert.equal(formatMutationType('set_quantity'), 'Set quantity');
  assert.equal(toDateInputValue('2026-03-12T08:15:00Z'), '2026-03-12');
});
