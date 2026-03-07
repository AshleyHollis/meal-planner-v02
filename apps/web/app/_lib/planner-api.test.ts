import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import {
  confirmDraft,
  getDraft,
  openDraftFromSuggestion,
  pollAISuggestionRequest,
  requestAISuggestion,
  requestSlotRegen,
  revertDraftSlot,
  updateDraftSlot,
} from './planner-api';

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

test('requestAISuggestion follows the backend request lifecycle until the suggestion is ready', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  let callIndex = 0;
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    callIndex += 1;

    if (callIndex === 1) {
      return jsonResponse(202, {
        request_id: 'req-123',
        household_id: 'household-abc',
        plan_period_start: '2026-03-09',
        status: 'queued',
        slots: [],
        fallback_mode: 'none',
        created_at: '2026-03-08T10:00:00Z',
      });
    }

    return jsonResponse(200, {
      request_id: 'req-123',
      suggestion_id: 'result-123',
      household_id: 'household-abc',
      plan_period_start: '2026-03-09',
      status: 'completed',
      fallback_mode: 'none',
      created_at: '2026-03-08T10:00:00Z',
      slots: [
        {
          id: 'slot-1',
          day_of_week: 0,
          meal_type: 'dinner',
          meal_title: 'Lentil Tacos',
          meal_summary: 'Fast pantry dinner.',
          slot_origin: 'ai_suggested',
          reason_codes: ['uses_on_hand'],
          explanation_entries: ['Uses pantry lentils and tortillas.'],
          uses_on_hand: ['lentils', 'tortillas'],
          missing_hints: ['cilantro'],
          fallback_mode: 'curated_fallback',
          original_suggestion: {
            meal_title: 'Lentil Tacos',
            meal_summary: 'Fast pantry dinner.',
            reason_codes: ['uses_on_hand'],
            explanation_entries: ['Uses pantry lentils and tortillas.'],
            uses_on_hand: ['lentils', 'tortillas'],
            missing_hints: ['cilantro'],
          },
        },
      ],
    });
  }) as typeof fetch;

  const result = await requestAISuggestion('household-abc', '2026-03-09', 'mutation-1');

  assert.equal(String(calls[0]?.input), '/api/v1/households/household-abc/plans/suggestion');
  assert.equal(String(calls[1]?.input), '/api/v1/households/household-abc/plans/requests/req-123');
  assert.equal(calls[0]?.init?.method, 'POST');
  assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
    planPeriodStart: '2026-03-09',
    targetSlotId: null,
    requestIdempotencyKey: 'mutation-1',
  });
  assert.equal(result.status, 'ready');
  assert.equal(result.suggestionId, 'result-123');
  assert.equal(result.requestId, 'req-123');
  assert.equal(result.slots[0]?.originalSuggestion?.explanation, 'Uses pantry lentils and tortillas.');
  assert.deepEqual(result.slots[0]?.usesOnHand, ['lentils', 'tortillas']);
  assert.deepEqual(result.slots[0]?.missingHints, ['cilantro']);
  assert.equal(result.slots[0]?.fallbackMode, 'curated_fallback');
});

test('openDraftFromSuggestion includes the replaceExisting flag for backend-owned draft replacement', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(201, {
      id: 'draft-1',
      household_id: 'household-abc',
      period_start: '2026-03-09',
      slots: [],
      stale_warning: false,
      stale_warning_acknowledged: false,
      created_at: '2026-03-08T10:00:00Z',
      updated_at: '2026-03-08T10:00:00Z',
      ai_suggestion_request_id: 'req-123',
    });
  }) as typeof fetch;

  const draft = await openDraftFromSuggestion('household-abc', 'result-123', {
    replaceExisting: true,
  });

  assert.equal(String(calls[0]?.input), '/api/v1/households/household-abc/plans/draft');
  assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
    suggestionId: 'result-123',
    replaceExisting: true,
  });
  assert.equal(draft.draftId, 'draft-1');
});

test('planner slot mutations use real draft endpoints and preserve original suggestions', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });

    switch (calls.length) {
      case 1:
        return jsonResponse(200, {
          id: 'slot-1',
          day_of_week: 0,
          meal_type: 'dinner',
          meal_title: 'Manual Stir Fry',
          meal_summary: 'Use the last greens first.',
          slot_origin: 'user_edited',
          reason_codes: [],
          explanation_entries: [],
          original_suggestion: {
            meal_title: 'Veggie Pasta',
            meal_summary: 'Pantry-first dinner.',
            reason_codes: ['uses_on_hand'],
            explanation_entries: ['Keeps fresh produce moving.'],
          },
        });
      case 2:
        return jsonResponse(200, {
          id: 'slot-1',
          day_of_week: 0,
          meal_type: 'dinner',
          meal_title: 'Veggie Pasta',
          meal_summary: 'Pantry-first dinner.',
          slot_origin: 'ai_suggested',
          reason_codes: ['uses_on_hand'],
          explanation_entries: ['Keeps fresh produce moving.'],
          original_suggestion: {
            meal_title: 'Veggie Pasta',
            meal_summary: 'Pantry-first dinner.',
            reason_codes: ['uses_on_hand'],
            explanation_entries: ['Keeps fresh produce moving.'],
          },
        });
      default:
        return jsonResponse(202, {
          request_id: 'regen-123',
          household_id: 'household-abc',
          plan_period_start: '2026-03-09',
          status: 'generating',
          meal_plan_id: 'draft-1',
          created_at: '2026-03-08T10:00:00Z',
          slots: [],
        });
    }
  }) as typeof fetch;

  const editedSlot = await updateDraftSlot('household-abc', 'draft-1', 'slot-1', {
    mealTitle: 'Manual Stir Fry',
    mealSummary: 'Use the last greens first.',
  });
  const revertedSlot = await revertDraftSlot('household-abc', 'draft-1', 'slot-1');
  const regenRequest = await requestSlotRegen('household-abc', 'draft-1', 'slot-1', 'regen-mutation');

  assert.equal(calls[0]?.init?.method, 'PATCH');
  assert.equal(String(calls[0]?.input), '/api/v1/households/household-abc/plans/draft/draft-1/slots/slot-1');
  assert.equal(calls[1]?.init?.method, 'POST');
  assert.equal(String(calls[1]?.input), '/api/v1/households/household-abc/plans/draft/draft-1/slots/slot-1/revert');
  assert.equal(String(calls[2]?.input), '/api/v1/households/household-abc/plans/draft/draft-1/slots/slot-1/regenerate');
  assert.equal(editedSlot.origin, 'user_edited');
  assert.equal(editedSlot.originalSuggestion?.mealTitle, 'Veggie Pasta');
  assert.equal(revertedSlot.origin, 'ai_suggested');
  assert.equal(revertedSlot.explanation, 'Keeps fresh produce moving.');
  assert.equal(regenRequest.requestId, 'regen-123');
  assert.equal(regenRequest.status, 'generating');
});

test('pollAISuggestionRequest keeps stale results visible as stale-ready suggestions', async () => {
  globalThis.fetch = (async () =>
    jsonResponse(200, {
      request_id: 'req-stale',
      suggestion_id: 'result-stale',
      household_id: 'household-abc',
      plan_period_start: '2026-03-09',
      status: 'stale',
      fallback_mode: 'none',
      is_stale: true,
      created_at: '2026-03-08T10:00:00Z',
      slots: [
        {
          id: 'slot-1',
          day_of_week: 1,
          meal_type: 'lunch',
          meal_title: 'Tomato Soup',
          meal_summary: 'Use older tomatoes first.',
          slot_origin: 'ai_suggested',
          reason_codes: ['uses_on_hand'],
          explanation_entries: ['Built from the earlier pantry snapshot.'],
        },
      ],
    })) as typeof fetch;

  const result = await pollAISuggestionRequest('household-abc', 'req-stale', {
    maxAttempts: 1,
    planPeriodStart: '2026-03-09',
  });

  assert.equal(result.status, 'ready');
  assert.equal(result.isStale, true);
  assert.equal(result.slots[0]?.mealTitle, 'Tomato Soup');
});

test('getDraft maps stale warning state and original suggestion snapshots from the backend', async () => {
  globalThis.fetch = (async () =>
    jsonResponse(200, {
      id: 'draft-1',
      household_id: 'household-abc',
      period_start: '2026-03-09',
      stale_warning: true,
      stale_warning_acknowledged: false,
      created_at: '2026-03-08T10:00:00Z',
      updated_at: '2026-03-08T10:05:00Z',
      ai_suggestion_request_id: 'req-123',
      slots: [
        {
          id: 'slot-1',
          day_of_week: 0,
          meal_type: 'dinner',
          meal_title: 'Veggie Pasta',
          meal_summary: 'Pantry-first dinner.',
          slot_origin: 'ai_suggested',
          reason_codes: ['uses_on_hand'],
          explanation_entries: ['Keeps fresh produce moving.'],
          uses_on_hand: ['spinach'],
          missing_hints: ['parmesan'],
        },
      ],
    })) as typeof fetch;

  const draft = await getDraft('household-abc', '2026-03-09');

  assert.ok(draft);
  assert.equal(draft.staleWarning, true);
  assert.equal(draft.slots[0]?.originalSuggestion?.mealTitle, 'Veggie Pasta');
  assert.equal(draft.slots[0]?.originalSuggestion?.explanation, 'Keeps fresh produce moving.');
});

test('confirmDraft posts stale-warning acknowledgment and returns the confirmed plan contract', async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return jsonResponse(200, {
      id: 'confirmed-1',
      household_id: 'household-abc',
      plan_period_start: '2026-03-09',
      confirmed_at: '2026-03-08T10:15:00Z',
      ai_suggestion_request_id: 'req-123',
      stale_warning_acknowledged: true,
      slots: [
        {
          id: 'slot-1',
          day_of_week: 0,
          meal_type: 'dinner',
          meal_title: 'Manual Stir Fry',
          meal_summary: 'Use the last greens first.',
          slot_origin: 'user_edited',
          reason_codes: [],
          explanation_entries: [],
          original_suggestion: {
            meal_title: 'Veggie Pasta',
            meal_summary: 'Pantry-first dinner.',
            reason_codes: ['uses_on_hand'],
            explanation_entries: ['Keeps fresh produce moving.'],
          },
        },
      ],
    });
  }) as typeof fetch;

  const confirmedPlan = await confirmDraft('household-abc', 'draft-1', {
    clientMutationId: 'confirm-1',
    staleWarningAcknowledged: true,
  });

  assert.equal(
    String(calls[0]?.input),
    '/api/v1/households/household-abc/plans/draft/draft-1/confirm'
  );
  assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
    clientMutationId: 'confirm-1',
    staleWarningAcknowledged: true,
  });
  assert.equal(confirmedPlan.planId, 'confirmed-1');
  assert.equal(confirmedPlan.staleWarningAcknowledged, true);
  assert.equal(confirmedPlan.slots[0]?.origin, 'user_edited');
  assert.equal(confirmedPlan.slots[0]?.originalSuggestion?.mealTitle, 'Veggie Pasta');
});

