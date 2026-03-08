import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  getConfirmButtonLabel,
  getRegenerationFailureMessage,
  getSuggestionBannerDetail,
} from './planner-ui';

test('getSuggestionBannerDetail explains curated fallback and confirmed-plan protection', () => {
  const detail = getSuggestionBannerDetail('fallback_used', 'curated_fallback', {
    hasConfirmedPlan: true,
  });

  assert.match(detail ?? '', /curated backup guidance/i);
  assert.match(detail ?? '', /confirmed plan stays active/i);
});

test('getSuggestionBannerDetail explains insufficient context honestly', () => {
  const detail = getSuggestionBannerDetail('insufficient_context', 'manual_guidance');

  assert.match(detail ?? '', /could not build a full weekly suggestion/i);
  assert.match(detail ?? '', /try again/i);
});

test('getRegenerationFailureMessage keeps the user on their last safe slot value', () => {
  assert.match(
    getRegenerationFailureMessage({
      mealTitle: 'Manual Stir Fry',
      origin: 'user_edited',
      originalSuggestion: {
        mealTitle: 'Veggie Pasta',
        mealSummary: 'Pantry-first dinner.',
        reasonCodes: ['uses_on_hand'],
        explanation: 'Keeps fresh produce moving.',
        usesOnHand: ['greens'],
        missingHints: [],
      },
    }),
    /keeping your last saved meal/i
  );

  assert.match(
    getRegenerationFailureMessage({
      mealTitle: 'Veggie Pasta',
      origin: 'ai_suggested',
      originalSuggestion: {
        mealTitle: 'Veggie Pasta',
        mealSummary: 'Pantry-first dinner.',
        reasonCodes: ['uses_on_hand'],
        explanation: 'Keeps fresh produce moving.',
        usesOnHand: ['greens'],
        missingHints: [],
      },
    }),
    /keeping the original ai suggestion/i
  );
});

test('getConfirmButtonLabel distinguishes replacement confirmation', () => {
  assert.equal(getConfirmButtonLabel(false, false), 'Confirm plan');
  assert.equal(getConfirmButtonLabel(true, false), 'Replace confirmed plan');
  assert.equal(getConfirmButtonLabel(true, true), 'Replacing confirmed plan…');
});
