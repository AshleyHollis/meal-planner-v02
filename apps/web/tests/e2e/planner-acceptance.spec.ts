import { expect, test, type Page, type Request } from '@playwright/test';

type MealType = 'breakfast' | 'lunch' | 'dinner';
type PlanSlotOrigin = 'ai_suggested' | 'user_edited' | 'manually_added';
type PlanSlotState = 'idle' | 'pending_regen' | 'regenerating' | 'regen_failed';
type FallbackMode = 'none' | 'curated_fallback' | 'manual_guidance';

type ApiSlot = {
  id: string;
  day_of_week: number;
  meal_type: MealType;
  meal_title: string | null;
  meal_summary: string | null;
  slot_origin: PlanSlotOrigin;
  reason_codes: string[];
  explanation_entries: string[];
  uses_on_hand: string[];
  missing_hints: string[];
  slot_state?: PlanSlotState;
  slot_message?: string | null;
  fallback_mode?: FallbackMode | null;
  original_suggestion?: {
    meal_title: string | null;
    meal_summary: string | null;
    reason_codes: string[];
    explanation_entries: string[];
    uses_on_hand: string[];
    missing_hints: string[];
  } | null;
};

type ApiSuggestion = {
  request_id: string | null;
  suggestion_id: string;
  household_id: string;
  plan_period_start: string;
  status: 'queued' | 'generating' | 'completed' | 'completed_with_fallback' | 'failed' | 'stale';
  fallback_mode: FallbackMode;
  is_stale: boolean;
  created_at: string;
  slots: ApiSlot[];
};

type ApiDraft = {
  id: string;
  household_id: string;
  period_start: string;
  slots: ApiSlot[];
  stale_warning: boolean;
  stale_warning_acknowledged: boolean;
  created_at: string;
  updated_at: string;
  ai_suggestion_request_id: string | null;
};

type ApiConfirmedPlan = {
  id: string;
  household_id: string;
  plan_period_start: string;
  confirmed_at: string;
  ai_suggestion_request_id: string | null;
  stale_warning_acknowledged: boolean;
  slots: ApiSlot[];
};

type MockResponse = {
  status: number;
  body: unknown;
};

type PlannerScenario = {
  householdId: string;
  userId: string;
  periodStart: string;
  suggestion: ApiSuggestion | null;
  draft: ApiDraft | null;
  confirmed: ApiConfirmedPlan | null;
  queuedResponses: Map<
    string,
    Array<
      (
        request: Request,
        scenario: PlannerScenario,
        url: URL
      ) => MockResponse | Promise<MockResponse>
    >
  >;
};

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;
const MEAL_TYPES: MealType[] = ['breakfast', 'lunch', 'dinner'];

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function isoMonday(now = new Date()): string {
  const date = new Date(now);
  const day = date.getDay();
  const diff = (day === 0 ? -6 : 1 - day);
  date.setDate(date.getDate() + diff);
  return date.toISOString().slice(0, 10);
}

function createScenario(): PlannerScenario {
  return {
    householdId: 'household-abc',
    userId: 'user-123',
    periodStart: isoMonday(),
    suggestion: null,
    draft: null,
    confirmed: null,
    queuedResponses: new Map(),
  };
}

function queueResponse(
  scenario: PlannerScenario,
  key: string,
  responder: (
    request: Request,
    current: PlannerScenario,
    url: URL
  ) => MockResponse | Promise<MockResponse>
) {
  const existing = scenario.queuedResponses.get(key) ?? [];
  existing.push(responder);
  scenario.queuedResponses.set(key, existing);
}

function shiftQueuedResponse(scenario: PlannerScenario, key: string) {
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

function slotSnapshot(slot: ApiSlot) {
  return {
    meal_title: slot.meal_title,
    meal_summary: slot.meal_summary,
    reason_codes: [...slot.reason_codes],
    explanation_entries: [...slot.explanation_entries],
    uses_on_hand: [...slot.uses_on_hand],
    missing_hints: [...slot.missing_hints],
  };
}

function slotTitle(dayOfWeek: number, mealType: MealType, prefix: string): string {
  return `${prefix} ${DAY_LABELS[dayOfWeek]} ${mealType}`;
}

function makeSlot(
  dayOfWeek: number,
  mealType: MealType,
  prefix: string,
  overrides: Partial<ApiSlot> = {}
): ApiSlot {
  const defaultTitle = slotTitle(dayOfWeek, mealType, prefix);
  return {
    id: `${dayOfWeek}-${mealType}`,
    day_of_week: dayOfWeek,
    meal_type: mealType,
    meal_title: defaultTitle,
    meal_summary: `${defaultTitle} keeps the week moving.`,
    slot_origin: 'ai_suggested',
    reason_codes: ['uses_on_hand'],
    explanation_entries: [`${defaultTitle} uses household inventory and preferences.`],
    uses_on_hand: ['beans', 'rice'],
    missing_hints: ['cilantro'],
    slot_state: 'idle',
    slot_message: null,
    fallback_mode: 'none',
    ...overrides,
  };
}

function makeWeeklySlots(prefix: string, overrides: Record<string, Partial<ApiSlot>> = {}) {
  return DAY_LABELS.flatMap((_, dayOfWeek) =>
    MEAL_TYPES.map((mealType) => {
      const key = `${dayOfWeek}-${mealType}`;
      return makeSlot(dayOfWeek, mealType, prefix, overrides[key] ?? {});
    })
  );
}

function createSuggestion(
  scenario: PlannerScenario,
  prefix: string,
  overrides: Partial<ApiSuggestion> = {},
  slotOverrides: Record<string, Partial<ApiSlot>> = {}
): ApiSuggestion {
  return {
    request_id: overrides.request_id ?? 'req-suggestion',
    suggestion_id: overrides.suggestion_id ?? 'suggestion-1',
    household_id: scenario.householdId,
    plan_period_start: scenario.periodStart,
    status: overrides.status ?? 'completed',
    fallback_mode: overrides.fallback_mode ?? 'none',
    is_stale: overrides.is_stale ?? false,
    created_at: overrides.created_at ?? '2026-03-08T12:00:00Z',
    slots: overrides.slots ?? makeWeeklySlots(prefix, slotOverrides),
  };
}

function createDraftFromSuggestion(
  scenario: PlannerScenario,
  suggestion: ApiSuggestion,
  overrides: Partial<ApiDraft> = {}
): ApiDraft {
  return {
    id: overrides.id ?? 'draft-1',
    household_id: scenario.householdId,
    period_start: scenario.periodStart,
    slots: clone(suggestion.slots).map((slot) => ({
      ...slot,
      slot_state: slot.slot_state ?? 'idle',
      slot_message: slot.slot_message ?? null,
      original_suggestion: slot.original_suggestion ?? slotSnapshot(slot),
    })),
    stale_warning: overrides.stale_warning ?? suggestion.is_stale,
    stale_warning_acknowledged: overrides.stale_warning_acknowledged ?? false,
    created_at: overrides.created_at ?? '2026-03-08T12:05:00Z',
    updated_at: overrides.updated_at ?? '2026-03-08T12:05:00Z',
    ai_suggestion_request_id: overrides.ai_suggestion_request_id ?? suggestion.request_id,
  };
}

function createConfirmedPlan(
  scenario: PlannerScenario,
  prefix: string,
  overrides: Partial<ApiConfirmedPlan> = {},
  slotOverrides: Record<string, Partial<ApiSlot>> = {}
): ApiConfirmedPlan {
  return {
    id: overrides.id ?? 'confirmed-1',
    household_id: scenario.householdId,
    plan_period_start: scenario.periodStart,
    confirmed_at: overrides.confirmed_at ?? '2026-03-08T08:00:00Z',
    ai_suggestion_request_id: overrides.ai_suggestion_request_id ?? 'confirmed-request',
    stale_warning_acknowledged: overrides.stale_warning_acknowledged ?? false,
    slots: overrides.slots ?? makeWeeklySlots(prefix, slotOverrides),
  };
}

async function fulfillPlanner(page: Page, scenario: PlannerScenario) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const key = `${request.method()} ${url.pathname}`;
    const queued = shiftQueuedResponse(scenario, key);
    if (queued) {
      const response = await queued(request, scenario, url);
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

    const householdPath = `/api/v1/households/${scenario.householdId}/plans`;

    if (request.method() === 'GET' && url.pathname === `${householdPath}/suggestion`) {
      if (!scenario.suggestion) {
        await route.fulfill({ status: 404, json: { detail: 'No suggestion found' } });
        return;
      }
      await route.fulfill({ status: 200, json: clone(scenario.suggestion) });
      return;
    }

    if (request.method() === 'GET' && url.pathname === `${householdPath}/draft`) {
      if (!scenario.draft) {
        await route.fulfill({ status: 404, json: { detail: 'No draft found' } });
        return;
      }
      await route.fulfill({ status: 200, json: clone(scenario.draft) });
      return;
    }

    if (request.method() === 'GET' && url.pathname === `${householdPath}/confirmed`) {
      if (!scenario.confirmed) {
        await route.fulfill({ status: 404, json: { detail: 'No confirmed plan found' } });
        return;
      }
      await route.fulfill({ status: 200, json: clone(scenario.confirmed) });
      return;
    }

    if (request.method() === 'POST' && url.pathname === `${householdPath}/draft`) {
      if (!scenario.suggestion) {
        await route.fulfill({ status: 409, json: { detail: 'No suggestion available' } });
        return;
      }
      scenario.draft = createDraftFromSuggestion(scenario, scenario.suggestion, {
        stale_warning: scenario.suggestion.is_stale,
      });
      await route.fulfill({ status: 201, json: clone(scenario.draft) });
      return;
    }

    const slotMatch = url.pathname.match(
      new RegExp(
        `^${householdPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/draft/([^/]+)/slots/([^/]+)(?:/(revert|regenerate))?$`
      )
    );
    if (slotMatch) {
      const draftId = slotMatch[1] ?? '';
      const slotId = slotMatch[2] ?? '';
      const action = slotMatch[3] ?? null;
      if (!scenario.draft || scenario.draft.id !== draftId) {
        await route.fulfill({ status: 404, json: { detail: 'Draft not found' } });
        return;
      }

      const slot = scenario.draft.slots.find((entry) => entry.id === slotId);
      if (!slot) {
        await route.fulfill({ status: 404, json: { detail: 'Slot not found' } });
        return;
      }

      if (request.method() === 'PATCH' && !action) {
        const body = request.postDataJSON() as {
          mealTitle?: string | null;
          mealSummary?: string | null;
        };
        if (!slot.original_suggestion) {
          slot.original_suggestion = slotSnapshot(slot);
        }
        slot.meal_title = body.mealTitle ?? null;
        slot.meal_summary = body.mealSummary ?? null;
        slot.slot_origin = 'user_edited';
        slot.reason_codes = [];
        slot.explanation_entries = [];
        slot.uses_on_hand = [];
        slot.missing_hints = [];
        slot.fallback_mode = 'none';
        slot.slot_state = 'idle';
        slot.slot_message = null;
        scenario.draft.updated_at = '2026-03-08T12:10:00Z';
        await route.fulfill({ status: 200, json: clone(slot) });
        return;
      }

      if (request.method() === 'POST' && action === 'revert') {
        if (!slot.original_suggestion) {
          await route.fulfill({ status: 409, json: { detail: 'No original suggestion available' } });
          return;
        }
        slot.meal_title = slot.original_suggestion.meal_title;
        slot.meal_summary = slot.original_suggestion.meal_summary;
        slot.slot_origin = 'ai_suggested';
        slot.reason_codes = [...slot.original_suggestion.reason_codes];
        slot.explanation_entries = [...slot.original_suggestion.explanation_entries];
        slot.uses_on_hand = [...slot.original_suggestion.uses_on_hand];
        slot.missing_hints = [...slot.original_suggestion.missing_hints];
        slot.slot_state = 'idle';
        slot.slot_message = null;
        slot.fallback_mode = 'none';
        scenario.draft.updated_at = '2026-03-08T12:11:00Z';
        await route.fulfill({ status: 200, json: clone(slot) });
        return;
      }
    }

    const confirmMatch = url.pathname.match(
      new RegExp(
        `^${householdPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/draft/([^/]+)/confirm$`
      )
    );
    if (request.method() === 'POST' && confirmMatch) {
      if (!scenario.draft) {
        await route.fulfill({ status: 404, json: { detail: 'Draft not found' } });
        return;
      }
      const body = request.postDataJSON() as { staleWarningAcknowledged?: boolean };
      scenario.confirmed = {
        id: 'confirmed-replacement',
        household_id: scenario.householdId,
        plan_period_start: scenario.periodStart,
        confirmed_at: '2026-03-08T12:30:00Z',
        ai_suggestion_request_id: scenario.draft.ai_suggestion_request_id,
        stale_warning_acknowledged: Boolean(body.staleWarningAcknowledged),
        slots: clone(scenario.draft.slots).map((slot) => ({
          ...slot,
          slot_state: 'idle',
          slot_message: null,
        })),
      };
      scenario.draft = null;
      scenario.suggestion = null;
      await route.fulfill({ status: 200, json: clone(scenario.confirmed) });
      return;
    }

    throw new Error(`Unhandled request: ${key}`);
  });
}

test('planner request, review, edit, regen, stale acknowledgment, and confirmed-plan protection stay intact', async ({
  page,
}) => {
  const scenario = createScenario();
  scenario.confirmed = createConfirmedPlan(scenario, 'Confirmed', {
    id: 'confirmed-existing',
  });

  const replacementSuggestion = createSuggestion(
    scenario,
    'Suggested',
    {
      request_id: 'req-happy',
      suggestion_id: 'suggestion-happy',
      status: 'completed',
      is_stale: true,
    },
    {
      '0-dinner': {
        meal_title: 'Suggested Mon dinner',
        meal_summary: 'Pantry pasta for the first night.',
        explanation_entries: ['Uses pantry pasta and spinach already on hand.'],
        uses_on_hand: ['pasta', 'spinach'],
        missing_hints: ['parmesan'],
      },
      '1-lunch': {
        meal_title: 'Suggested Tue lunch',
        meal_summary: 'Quick grain bowl for a busy day.',
        explanation_entries: ['Builds around cooked rice and leftover vegetables.'],
        uses_on_hand: ['rice', 'vegetables'],
        missing_hints: ['avocado'],
      },
    }
  );

  queueResponse(
    scenario,
    `POST /api/v1/households/${scenario.householdId}/plans/suggestion`,
    async () => ({
      status: 202,
      body: {
        request_id: 'req-happy',
        household_id: scenario.householdId,
        plan_period_start: scenario.periodStart,
        status: 'queued',
        fallback_mode: 'none',
        is_stale: false,
        created_at: '2026-03-08T12:00:00Z',
        slots: [],
      },
    })
  );
  queueResponse(
    scenario,
    `GET /api/v1/households/${scenario.householdId}/plans/requests/req-happy`,
    async () => {
      scenario.suggestion = clone(replacementSuggestion);
      return {
        status: 200,
        body: clone(replacementSuggestion),
      };
    }
  );
  queueResponse(
    scenario,
    `POST /api/v1/households/${scenario.householdId}/plans/draft/draft-1/slots/1-lunch/regenerate`,
    async () => ({
      status: 202,
      body: {
        request_id: 'req-regen-happy',
        suggestion_id: 'req-regen-happy',
        household_id: scenario.householdId,
        plan_period_start: scenario.periodStart,
        status: 'generating',
        fallback_mode: 'none',
        is_stale: false,
        created_at: '2026-03-08T12:15:00Z',
        slots: [],
      },
    })
  );
  queueResponse(
    scenario,
    `GET /api/v1/households/${scenario.householdId}/plans/requests/req-regen-happy`,
    async () => {
      await page.waitForTimeout(250);
      if (!scenario.draft) {
        throw new Error('Draft should exist during regeneration.');
      }
      const regenerated = makeSlot(1, 'lunch', 'Regenerated', {
        meal_title: 'Regenerated Tue lunch',
        meal_summary: 'Updated grain bowl after the fresh grounding pass.',
        explanation_entries: ['Refresh uses the latest rice, greens, and tofu inventory.'],
        uses_on_hand: ['rice', 'greens', 'tofu'],
        missing_hints: [],
      });
      regenerated.original_suggestion = slotSnapshot(regenerated);
      const targetIndex = scenario.draft.slots.findIndex((slot) => slot.id === '1-lunch');
      scenario.draft.slots[targetIndex] = regenerated;
      scenario.draft.updated_at = '2026-03-08T12:16:00Z';
      return {
        status: 200,
        body: {
          request_id: 'req-regen-happy',
          suggestion_id: 'regen-result-happy',
          household_id: scenario.householdId,
          plan_period_start: scenario.periodStart,
          status: 'completed',
          fallback_mode: 'none',
          is_stale: false,
          created_at: '2026-03-08T12:16:00Z',
          slots: [clone(regenerated)],
        },
      };
    }
  );

  await fulfillPlanner(page, scenario);
  await page.goto('/planner');

  const confirmedSection = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'Confirmed plan' }),
  });
  await expect(confirmedSection.getByText('Confirmed Mon dinner', { exact: true })).toBeVisible();
  await expect(confirmedSection.getByText('AI', { exact: true })).toHaveCount(0);

  const idleBanner = page.getByRole('status').filter({
    has: page.getByText('No suggestion yet'),
  });
  await idleBanner.getByRole('button', { name: 'Request AI suggestion' }).click();
  await expect(page.getByText('AI suggestion ready')).toBeVisible();
  await expect(
    page.getByText(/confirmed plan stays active until you explicitly confirm a replacement/i)
  ).toBeVisible();

  const suggestionSection = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'Latest AI suggestion' }),
  });
  const monDinnerCard = suggestionSection.locator('[aria-label="Mon dinner"]');
  await expect(monDinnerCard.getByText('Suggested Mon dinner', { exact: true })).toBeVisible();
  await expect(monDinnerCard.getByText(/uses on hand:\s*pasta, spinach/i)).toBeVisible();
  await monDinnerCard.locator('summary').click();
  await expect(
    monDinnerCard.getByText('Uses pantry pasta and spinach already on hand.')
  ).toBeVisible();

  await page.getByRole('button', { name: 'Review suggestion' }).click();
  await expect(page.getByRole('heading', { name: 'Editable draft' })).toBeVisible();
  await expect(
    page.getByText(/this draft may be out of date/i).first()
  ).toBeVisible();

  const currentConfirmedSection = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'Current confirmed plan' }),
  });
  await expect(
    currentConfirmedSection.getByText('Confirmed Mon dinner', { exact: true })
  ).toBeVisible();
  await expect(
    currentConfirmedSection.getByText(/still active until you explicitly confirm a replacement/i)
  ).toBeVisible();
  await expect(currentConfirmedSection.getByText('AI', { exact: true })).toHaveCount(0);

  await page.getByRole('button', { name: 'Edit dinner on Mon' }).click();
  await page.getByLabel('Meal title').fill('Manual Chili');
  await page.getByLabel('Summary').fill('Family pick with pantry beans and peppers.');
  await page.getByRole('button', { name: 'Save slot' }).click();
  await expect(page.getByText('Manual Chili')).toBeVisible();
  await expect(page.getByText('Edited', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Regenerate lunch on Tue' }).click();
  await expect(page.getByText('Refreshing this suggestion…')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Edit dinner on Mon' })).toBeEnabled();
  await expect(page.getByText('Regenerated Tue lunch')).toBeVisible();

  await page.getByRole('button', { name: 'Replace confirmed plan' }).click();
  await expect(
    page.getByText(/acknowledge the stale-draft warning before confirming this plan/i)
  ).toBeVisible();

  await page
    .getByLabel('I understand this draft may not reflect the latest household context.')
    .check();
  await page.getByRole('button', { name: 'Replace confirmed plan' }).click();

  const finalConfirmedSection = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'Confirmed plan' }),
  });
  await expect(finalConfirmedSection.getByText('Manual Chili', { exact: true })).toBeVisible();
  await expect(
    finalConfirmedSection.getByText('Regenerated Tue lunch', { exact: true })
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Editable draft' })).toHaveCount(0);
  await expect(finalConfirmedSection.getByText('AI', { exact: true })).toHaveCount(0);
  await expect(finalConfirmedSection.getByText('Edited', { exact: true })).toHaveCount(0);
});

test('per-slot regeneration failure keeps the last safe meal visible and guides manual recovery', async ({
  page,
}) => {
  const scenario = createScenario();
  const draftSuggestion = createSuggestion(scenario, 'Draft Source');
  scenario.draft = createDraftFromSuggestion(scenario, draftSuggestion);
  const mondayDinner = scenario.draft.slots.find((slot) => slot.id === '0-dinner');
  if (!mondayDinner) {
    throw new Error('Missing Monday dinner slot.');
  }
  mondayDinner.original_suggestion = slotSnapshot(mondayDinner);
  mondayDinner.meal_title = 'Manual Chili';
  mondayDinner.meal_summary = 'Keep the family favorite for dinner.';
  mondayDinner.slot_origin = 'user_edited';
  mondayDinner.reason_codes = [];
  mondayDinner.explanation_entries = [];
  mondayDinner.uses_on_hand = [];
  mondayDinner.missing_hints = [];

  queueResponse(
    scenario,
    `POST /api/v1/households/${scenario.householdId}/plans/draft/${scenario.draft.id}/slots/0-dinner/regenerate`,
    async () => ({
      status: 202,
      body: {
        request_id: 'req-regen-fail',
        suggestion_id: 'req-regen-fail',
        household_id: scenario.householdId,
        plan_period_start: scenario.periodStart,
        status: 'generating',
        fallback_mode: 'none',
        is_stale: false,
        created_at: '2026-03-08T13:00:00Z',
        slots: [],
      },
    })
  );
  queueResponse(
    scenario,
    `GET /api/v1/households/${scenario.householdId}/plans/requests/req-regen-fail`,
    async () => {
      await page.waitForTimeout(200);
      return {
        status: 200,
        body: {
          request_id: 'req-regen-fail',
          suggestion_id: 'regen-failed-result',
          household_id: scenario.householdId,
          plan_period_start: scenario.periodStart,
          status: 'failed',
          fallback_mode: 'manual_guidance',
          is_stale: false,
          created_at: '2026-03-08T13:01:00Z',
          slots: [],
        },
      };
    }
  );

  await fulfillPlanner(page, scenario);
  await page.goto('/planner');

  await expect(page.getByText('Manual Chili')).toBeVisible();
  await page.getByRole('button', { name: 'Regenerate dinner on Mon' }).click();
  await expect(page.getByText('Refreshing this suggestion…')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Edit lunch on Tue' })).toBeEnabled();
  await expect(
    page.getByText(/keeping your last saved meal so you can retry or edit it manually/i)
  ).toBeVisible();
  await expect(
    page.getByText(/ai could not produce a better replacement from the current context/i)
  ).toBeVisible();
  await expect(page.getByText('Manual Chili')).toBeVisible();
  await expect(page.getByText('Sync error')).toBeVisible();
});

test('manual-guidance fallback and request failures stay visible and honest', async ({ page }) => {
  const scenario = createScenario();
  scenario.suggestion = createSuggestion(scenario, 'Fallback', {
    request_id: 'req-manual-guidance',
    suggestion_id: 'suggestion-manual-guidance',
    status: 'completed_with_fallback',
    fallback_mode: 'manual_guidance',
    slots: [],
  });

  queueResponse(
    scenario,
    `POST /api/v1/households/${scenario.householdId}/plans/suggestion`,
    async () => ({
      status: 503,
      body: { detail: 'Planner service unavailable' },
    })
  );

  await fulfillPlanner(page, scenario);
  await page.goto('/planner');

  await expect(page.getByText('Not enough context for a full suggestion')).toBeVisible();
  await expect(
    page.getByText(/could not build a full weekly suggestion from the current household context/i)
  ).toBeVisible();
  const banner = page.getByRole('status').filter({
    has: page.getByText('Not enough context for a full suggestion'),
  });
  await expect(banner.getByRole('button', { name: 'Request AI suggestion' })).toBeVisible();

  await banner.getByRole('button', { name: 'Request AI suggestion' }).click();
  await expect(page.getByText('Suggestion failed')).toBeVisible();
  await expect(
    page.getByText(/ai suggestion requests are unavailable right now/i)
  ).toBeVisible();
  const failedBanner = page.getByRole('status').filter({
    has: page.getByText('Suggestion failed'),
  });
  await expect(failedBanner.getByRole('button', { name: 'Request AI suggestion' })).toBeVisible();
});
