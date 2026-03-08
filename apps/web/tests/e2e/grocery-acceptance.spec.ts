import { expect, test, type Page, type Request } from '@playwright/test';

type ApiMealSource = {
  meal_slot_id: string;
  meal_name: string | null;
  contributed_quantity: string;
};

type ApiWarning = {
  meal_slot_id: string;
  meal_name: string | null;
  reason: string;
  message: string | null;
};

type ApiLine = {
  id: string;
  grocery_list_id: string;
  grocery_list_version_id: string;
  ingredient_name: string;
  ingredient_ref_id: string | null;
  required_quantity: string;
  unit: string;
  offset_quantity: string;
  shopping_quantity: string;
  origin: 'derived' | 'ad_hoc';
  meal_sources: ApiMealSource[];
  offset_inventory_item_id: string | null;
  offset_inventory_item_version: number | null;
  user_adjusted_quantity: string | null;
  user_adjustment_note: string | null;
  user_adjustment_flagged: boolean;
  ad_hoc_note: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type ApiList = {
  id: string;
  household_id: string;
  meal_plan_id: string | null;
  status: 'draft' | 'stale_draft' | 'confirmed' | 'trip_in_progress';
  current_version_number: number;
  current_version_id: string;
  confirmed_at: string | null;
  last_derived_at: string;
  plan_period_start: string;
  plan_period_end: string;
  confirmed_plan_version: number;
  inventory_snapshot_reference: string;
  is_stale: boolean;
  trip_state?: 'confirmed_list_ready' | 'trip_in_progress' | 'trip_complete_pending_reconciliation';
  incomplete_slot_warnings: ApiWarning[];
  lines: ApiLine[];
};

type GroceryScenario = {
  householdId: string;
  userId: string;
  periodStart: string;
  list: ApiList | null;
  syncConflict?:
    | {
        detail: Record<string, unknown>;
        keepMineList: ApiList;
        useServerList: ApiList;
      }
    | null;
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function isoMonday(now = new Date()): string {
  const date = new Date(now);
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  date.setDate(date.getDate() + diff);
  return date.toISOString().slice(0, 10);
}

function createList(
  periodStart: string,
  overrides: Partial<ApiList> = {},
  lineOverrides: Partial<ApiLine>[] = []
): ApiList {
  const lines: ApiLine[] = [
    {
      id: 'line-1',
      grocery_list_id: 'grocery-1',
      grocery_list_version_id: 'version-3',
      ingredient_name: 'Tomatoes',
      ingredient_ref_id: 'ingredient-1',
      required_quantity: '4',
      unit: 'ea',
      offset_quantity: '1',
      shopping_quantity: '3',
      origin: 'derived',
      meal_sources: [
        {
          meal_slot_id: 'slot-1',
          meal_name: 'Pasta Night',
          contributed_quantity: '2',
        },
        {
          meal_slot_id: 'slot-2',
          meal_name: 'Taco Bowls',
          contributed_quantity: '2',
        },
      ],
      offset_inventory_item_id: 'inventory-1',
      offset_inventory_item_version: 9,
      user_adjusted_quantity: '4',
      user_adjustment_note: 'Need extra for lunch leftovers',
      user_adjustment_flagged: true,
      ad_hoc_note: null,
      active: true,
      created_at: '2026-03-08T10:00:00Z',
      updated_at: '2026-03-08T10:05:00Z',
    },
    {
      id: 'line-2',
      grocery_list_id: 'grocery-1',
      grocery_list_version_id: 'version-3',
      ingredient_name: 'Milk',
      ingredient_ref_id: null,
      required_quantity: '1',
      unit: 'carton',
      offset_quantity: '0',
      shopping_quantity: '1',
      origin: 'ad_hoc',
      meal_sources: [],
      offset_inventory_item_id: null,
      offset_inventory_item_version: null,
      user_adjusted_quantity: null,
      user_adjustment_note: null,
      user_adjustment_flagged: false,
      ad_hoc_note: 'For breakfasts',
      active: true,
      created_at: '2026-03-08T10:00:00Z',
      updated_at: '2026-03-08T10:05:00Z',
    },
  ];

  lineOverrides.forEach((override, index) => {
    lines[index] = {
      ...lines[index],
      ...override,
    };
  });

  return {
    id: 'grocery-1',
    household_id: 'household-abc',
    meal_plan_id: 'plan-1',
    status: 'stale_draft',
    current_version_number: 3,
    current_version_id: 'version-3',
    confirmed_at: null,
    last_derived_at: '2026-03-08T10:00:00Z',
    plan_period_start: periodStart,
    plan_period_end: '2026-03-15',
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
    lines,
    ...overrides,
  };
}

function createScenario(list?: ApiList | null): GroceryScenario {
  const periodStart = isoMonday();

  return {
    householdId: 'household-abc',
    userId: 'user-123',
    periodStart,
    list: list === undefined ? createList(periodStart) : list,
    syncConflict: null,
  };
}

async function fulfillGrocery(page: Page, scenario: GroceryScenario) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

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

    const groceryPath = `/api/v1/households/${scenario.householdId}/grocery`;

    if (request.method() === 'GET' && url.pathname === groceryPath) {
      if (!scenario.list) {
        await route.fulfill({ status: 404, json: { detail: 'No grocery list found' } });
        return;
      }

      await route.fulfill({ status: 200, json: clone(scenario.list) });
      return;
    }

    if (request.method() === 'POST' && url.pathname === `${groceryPath}/sync/upload`) {
      const body = request.postDataJSON() as Array<{
        aggregate_id: string | null;
        provisional_aggregate_id: string | null;
        mutation_type: string;
        payload: Record<string, unknown>;
        client_mutation_id: string;
      }>;

      if (!scenario.list) {
        await route.fulfill({ status: 404, json: { detail: 'No grocery list found' } });
        return;
      }

      if (scenario.syncConflict) {
        const syncConflict = scenario.syncConflict;
        const currentServerVersion = Number(
          syncConflict.detail.current_server_version ?? scenario.list.current_version_number
        );
        const outcomes = body.map((mutation) => ({
          client_mutation_id: mutation.client_mutation_id,
          mutation_type: mutation.mutation_type,
          aggregate: {
            aggregate_type: mutation.aggregate_id ? 'grocery_line' : 'grocery_list',
            aggregate_id: mutation.aggregate_id ?? scenario.list!.id,
            aggregate_version: currentServerVersion,
            provisional_aggregate_id: mutation.provisional_aggregate_id,
          },
          outcome: String(syncConflict.detail.outcome ?? 'review_required_quantity'),
          authoritative_server_version: currentServerVersion,
          conflict_id: String(syncConflict.detail.conflict_id),
          retryable: false,
          duplicate_of_client_mutation_id: null,
          auto_merge_reason: null,
        }));

        await route.fulfill({ status: 200, json: outcomes });
        return;
      }

      const outcomes = body.map((mutation, index) => {
        scenario.list!.status = 'trip_in_progress';
        scenario.list!.trip_state = 'trip_in_progress';
        scenario.list!.current_version_number += 1;
        scenario.list!.current_version_id = `version-${scenario.list!.current_version_number}`;

        if (mutation.mutation_type === 'remove_line' && mutation.aggregate_id) {
          const line = scenario.list!.lines.find((entry) => entry.id === mutation.aggregate_id);
          if (line) {
            line.active = false;
            line.updated_at = `2026-03-08T12:5${index}:00Z`;
          }
        }

        if (mutation.mutation_type === 'adjust_quantity' && mutation.aggregate_id) {
          const line = scenario.list!.lines.find((entry) => entry.id === mutation.aggregate_id);
          if (line) {
            const quantity = Number(
              mutation.payload.quantity_to_buy ?? mutation.payload.user_adjusted_quantity ?? 1
            );
            line.user_adjusted_quantity = String(quantity);
            line.user_adjustment_flagged = true;
            line.updated_at = `2026-03-08T12:5${index}:00Z`;
          }
        }

        if (mutation.mutation_type === 'add_ad_hoc') {
          scenario.list!.lines.push({
            id: mutation.provisional_aggregate_id ?? `line-sync-${index}`,
            grocery_list_id: scenario.list!.id,
            grocery_list_version_id: scenario.list!.current_version_id,
            ingredient_name: String(mutation.payload.ingredient_name ?? 'Trip item'),
            ingredient_ref_id: null,
            required_quantity: String(mutation.payload.shopping_quantity ?? 1),
            unit: String(mutation.payload.unit ?? 'ea'),
            offset_quantity: '0',
            shopping_quantity: String(mutation.payload.shopping_quantity ?? 1),
            origin: 'ad_hoc',
            meal_sources: [],
            offset_inventory_item_id: null,
            offset_inventory_item_version: null,
            user_adjusted_quantity: null,
            user_adjustment_note: null,
            user_adjustment_flagged: false,
            ad_hoc_note: (mutation.payload.ad_hoc_note as string | undefined) ?? null,
            active: true,
            created_at: '2026-03-08T12:55:00Z',
            updated_at: '2026-03-08T12:55:00Z',
          });
        }

        return {
          client_mutation_id: mutation.client_mutation_id,
          mutation_type: mutation.mutation_type,
          aggregate: {
            aggregate_type:
              mutation.mutation_type === 'add_ad_hoc' ? 'grocery_list' : 'grocery_line',
            aggregate_id:
              mutation.mutation_type === 'add_ad_hoc'
                ? scenario.list!.id
                : mutation.aggregate_id,
            aggregate_version: scenario.list!.current_version_number,
            provisional_aggregate_id: mutation.provisional_aggregate_id,
          },
          outcome: 'applied',
          authoritative_server_version: scenario.list!.current_version_number,
          conflict_id: null,
          retryable: false,
          duplicate_of_client_mutation_id: null,
          auto_merge_reason: null,
        };
      });

      await route.fulfill({ status: 200, json: outcomes });
      return;
    }

    const syncConflictListPath = `${groceryPath}/sync/conflicts`;
    if (request.method() === 'GET' && url.pathname === syncConflictListPath) {
      await route.fulfill({
        status: 200,
        json: scenario.syncConflict ? [clone(scenario.syncConflict.detail)] : [],
      });
      return;
    }

    const syncConflictMatch = url.pathname.match(
      new RegExp(`^${groceryPath}/sync/conflicts/([^/]+)$`)
    );
    if (request.method() === 'GET' && syncConflictMatch) {
      if (!scenario.syncConflict || syncConflictMatch[1] !== scenario.syncConflict.detail.conflict_id) {
        await route.fulfill({ status: 404, json: { detail: 'Conflict not found' } });
        return;
      }

      await route.fulfill({ status: 200, json: clone(scenario.syncConflict.detail) });
      return;
    }

    const keepMineMatch = url.pathname.match(
      new RegExp(`^${groceryPath}/sync/conflicts/([^/]+)/resolve-keep-mine$`)
    );
    if (request.method() === 'POST' && keepMineMatch) {
      if (!scenario.syncConflict || keepMineMatch[1] !== scenario.syncConflict.detail.conflict_id) {
        await route.fulfill({ status: 404, json: { detail: 'Conflict not found' } });
        return;
      }

      scenario.list = clone(scenario.syncConflict.keepMineList);
      scenario.syncConflict = null;
      await route.fulfill({
        status: 200,
        json: {
          mutation_kind: 'resolve_keep_mine',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    const useServerMatch = url.pathname.match(
      new RegExp(`^${groceryPath}/sync/conflicts/([^/]+)/resolve-use-server$`)
    );
    if (request.method() === 'POST' && useServerMatch) {
      if (!scenario.syncConflict || useServerMatch[1] !== scenario.syncConflict.detail.conflict_id) {
        await route.fulfill({ status: 404, json: { detail: 'Conflict not found' } });
        return;
      }

      scenario.list = clone(scenario.syncConflict.useServerList);
      scenario.syncConflict = null;
      await route.fulfill({
        status: 200,
        json: {
          mutation_kind: 'resolve_use_server',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    if (request.method() === 'POST' && url.pathname === `${groceryPath}/derive`) {
      scenario.list = createList(scenario.periodStart, {
        status: 'draft',
        current_version_number: 1,
        current_version_id: 'version-1',
        is_stale: false,
        incomplete_slot_warnings: [],
        lines: [
          {
            id: 'line-1',
            grocery_list_id: 'grocery-1',
            grocery_list_version_id: 'version-1',
            ingredient_name: 'Tomatoes',
            ingredient_ref_id: 'ingredient-1',
            required_quantity: '4',
            unit: 'ea',
            offset_quantity: '1',
            shopping_quantity: '3',
            origin: 'derived',
            meal_sources: [
              {
                meal_slot_id: 'slot-1',
                meal_name: 'Pasta Night',
                contributed_quantity: '2',
              },
              {
                meal_slot_id: 'slot-2',
                meal_name: 'Taco Bowls',
                contributed_quantity: '2',
              },
            ],
            offset_inventory_item_id: 'inventory-1',
            offset_inventory_item_version: 9,
            user_adjusted_quantity: null,
            user_adjustment_note: null,
            user_adjustment_flagged: false,
            ad_hoc_note: null,
            active: true,
            created_at: '2026-03-08T10:00:00Z',
            updated_at: '2026-03-08T10:05:00Z',
          },
        ],
      });

      await route.fulfill({
        status: 201,
        json: {
          mutation_kind: 'derive',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    if (request.method() === 'POST' && url.pathname === `${groceryPath}/${scenario.list?.id}/rederive`) {
      if (!scenario.list) {
        await route.fulfill({ status: 404, json: { detail: 'No grocery list found' } });
        return;
      }

      scenario.list.status = 'draft';
      scenario.list.is_stale = false;
      scenario.list.current_version_number += 1;
      scenario.list.current_version_id = `version-${scenario.list.current_version_number}`;
      scenario.list.last_derived_at = '2026-03-08T12:30:00Z';
      scenario.list.incomplete_slot_warnings = [
        {
          meal_slot_id: 'slot-4',
          meal_name: 'Friday Dinner',
          reason: 'missing_ingredient_data',
          message: 'Recipe ingredients are incomplete.',
        },
      ];
      scenario.list.lines = scenario.list.lines.map((line) => {
        if (line.id !== 'line-1') {
          return {
            ...line,
            grocery_list_version_id: scenario.list!.current_version_id,
          };
        }

        return {
          ...line,
          grocery_list_version_id: scenario.list!.current_version_id,
          required_quantity: '5',
          shopping_quantity: '4',
          offset_quantity: '1',
          user_adjustment_flagged: line.user_adjusted_quantity !== null,
          updated_at: '2026-03-08T12:30:00Z',
        };
      });

      await route.fulfill({
        status: 200,
        json: {
          mutation_kind: 'rederive',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    if (request.method() === 'POST' && url.pathname === `${groceryPath}/${scenario.list?.id}/lines`) {
      if (!scenario.list) {
        await route.fulfill({ status: 404, json: { detail: 'No grocery list found' } });
        return;
      }

      const body = request.postDataJSON() as {
        ingredient_name: string;
        shopping_quantity: number;
        unit: string;
        ad_hoc_note?: string | null;
      };

      scenario.list.lines.push({
        id: 'line-new',
        grocery_list_id: scenario.list.id,
        grocery_list_version_id: scenario.list.current_version_id,
        ingredient_name: body.ingredient_name,
        ingredient_ref_id: null,
        required_quantity: String(body.shopping_quantity),
        unit: body.unit,
        offset_quantity: '0',
        shopping_quantity: String(body.shopping_quantity),
        origin: 'ad_hoc',
        meal_sources: [],
        offset_inventory_item_id: null,
        offset_inventory_item_version: null,
        user_adjusted_quantity: null,
        user_adjustment_note: null,
        user_adjustment_flagged: false,
        ad_hoc_note: body.ad_hoc_note ?? null,
        active: true,
        created_at: '2026-03-08T12:35:00Z',
        updated_at: '2026-03-08T12:35:00Z',
      });

      await route.fulfill({
        status: 201,
        json: {
          mutation_kind: 'add_ad_hoc',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    const adjustMatch = url.pathname.match(
      new RegExp(`^${groceryPath}/grocery-1/lines/([^/]+)$`)
    );
    if (request.method() === 'PATCH' && adjustMatch && scenario.list) {
      const lineId = adjustMatch[1] ?? '';
      const body = request.postDataJSON() as {
        user_adjusted_quantity: number;
        user_adjustment_note?: string | null;
      };
      const line = scenario.list.lines.find((entry) => entry.id === lineId);
      if (!line) {
        await route.fulfill({ status: 404, json: { detail: 'Line not found' } });
        return;
      }

      line.user_adjusted_quantity = String(body.user_adjusted_quantity);
      line.user_adjustment_note = body.user_adjustment_note ?? null;
      line.user_adjustment_flagged = true;
      line.updated_at = '2026-03-08T12:36:00Z';

      await route.fulfill({
        status: 200,
        json: {
          mutation_kind: 'adjust_line',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    const removeMatch = url.pathname.match(
      new RegExp(`^${groceryPath}/grocery-1/lines/([^/]+)/remove$`)
    );
    if (request.method() === 'POST' && removeMatch && scenario.list) {
      const lineId = removeMatch[1] ?? '';
      const line = scenario.list.lines.find((entry) => entry.id === lineId);
      if (!line) {
        await route.fulfill({ status: 404, json: { detail: 'Line not found' } });
        return;
      }

      line.active = false;
      line.updated_at = '2026-03-08T12:37:00Z';

      await route.fulfill({
        status: 200,
        json: {
          mutation_kind: 'remove_line',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    if (request.method() === 'POST' && url.pathname === `${groceryPath}/${scenario.list?.id}/confirm`) {
      if (!scenario.list) {
        await route.fulfill({ status: 404, json: { detail: 'No grocery list found' } });
        return;
      }

      scenario.list.status = 'confirmed';
      scenario.list.confirmed_at = '2026-03-08T12:40:00Z';
      scenario.list.trip_state = 'confirmed_list_ready';

      await route.fulfill({
        status: 200,
        json: {
          mutation_kind: 'confirm_list',
          grocery_list: clone(scenario.list),
        },
      });
      return;
    }

    throw new Error(`Unhandled request: ${request.method()} ${url.pathname}`);
  });
}

test('grocery flow supports derive, review, adjust, and confirm from a confirmed plan', async ({
  page,
}) => {
  const scenario = createScenario(null);
  await fulfillGrocery(page, scenario);

  await page.goto('/grocery');

  await expect(page.getByText('No grocery draft yet')).toBeVisible();
  await page.getByRole('button', { name: 'Derive grocery draft' }).click();
  await expect(
    page.getByText('Derived a grocery draft from the confirmed plan and current inventory.')
  ).toBeVisible();

  const tomatoesRow = page.getByRole('listitem').filter({ hasText: 'Tomatoes' });
  await expect(page.getByText('Review the draft before confirming it for shopping.')).toBeVisible();
  await tomatoesRow.getByRole('button', { name: 'Show details' }).click();
  await expect(tomatoesRow.getByText('From Pasta Night, Taco Bowls')).toBeVisible();
  await expect(tomatoesRow.getByText('Inventory match: inventory-1 (snapshot v9)')).toBeVisible();
  await expect(tomatoesRow.getByText('2 ea')).toHaveCount(2);

  await tomatoesRow.getByRole('button', { name: 'Edit quantity' }).click();
  await tomatoesRow.getByLabel('Shopping quantity').fill('5');
  await tomatoesRow.getByLabel('Review note').fill('Need extra sauce');
  await tomatoesRow.getByRole('button', { name: 'Save quantity' }).click();
  await expect(page.getByText('Updated Tomatoes to 5 ea.')).toBeVisible();
  await expect(tomatoesRow.getByText('Override note: Need extra sauce')).toBeVisible();

  await page.getByRole('button', { name: 'Review and confirm' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByText('1 shopping line • 1 override')).toBeVisible();
  await page.getByRole('button', { name: 'Confirm for shopping' }).click();
  await expect(
    page.getByText('Confirmed this grocery list for shopping. This version is now locked from edits.')
  ).toBeVisible();
  await expect(
    page.getByText(
      'This confirmed list is ready for phone-first trip mode. Local edits stay on this device until they sync safely.'
    )
  ).toBeVisible();
  await expect(page.getByRole('button', { name: '+ Quick add trip item' })).toBeVisible();
});

test('stale refresh preserves user overrides and ad hoc intent with visible traceability', async ({
  page,
}) => {
  const scenario = createScenario();
  await fulfillGrocery(page, scenario);

  await page.goto('/grocery');

  await expect(page.getByRole('heading', { name: 'Grocery List' })).toBeVisible();
  await expect(page.getByText('This draft is stale. Review changes before confirming.')).toBeVisible();
  await expect(page.getByText('Friday Dinner')).toBeVisible();
  await expect(page.getByText('Need extra for lunch leftovers')).toBeVisible();

  const tomatoesRow = page.getByRole('listitem').filter({ hasText: 'Tomatoes' });
  await tomatoesRow.getByRole('button', { name: 'Show details' }).click();
  await expect(tomatoesRow.getByText('Meal traceability')).toBeVisible();
  await expect(tomatoesRow.getByText('From Pasta Night, Taco Bowls')).toBeVisible();
  await expect(tomatoesRow.getByText('Inventory match: inventory-1 (snapshot v9)')).toBeVisible();
  await expect(tomatoesRow.getByText('2 ea')).toHaveCount(2);

  await page.getByRole('button', { name: '+ Add item' }).click();
  await page.getByLabel('Item name').fill('Sparkling water');
  await page.getByRole('spinbutton', { name: 'Quantity' }).fill('2');
  await page.getByRole('combobox', { name: 'Unit' }).fill('box');
  await page.getByLabel('Ad hoc note').fill('For brunch');
  await page.getByRole('button', { name: 'Add to list' }).click();
  await expect(page.getByText('Added the ad hoc grocery item to the current draft.')).toBeVisible();
  await expect(page.getByRole('listitem').filter({ hasText: 'Sparkling water' })).toBeVisible();

  await page.getByRole('button', { name: 'Refresh draft' }).click();
  await expect(
    page.getByText('Refreshed the grocery draft and preserved existing quantity overrides for review.')
  ).toBeVisible();
  await expect(page.getByText('Draft list')).toBeVisible();
  await expect(page.getByText('Version 4')).toBeVisible();
  await expect(page.getByText('Review override — derived quantity changed.')).toBeVisible();
  await expect(tomatoesRow.getByText('Review quantity override — shopping quantity is 4 ea.')).toBeVisible();
  await expect(tomatoesRow.getByText('Confirmed 4 ea')).toBeVisible();
  await expect(tomatoesRow.getByText('Override note: Need extra for lunch leftovers')).toBeVisible();
  await expect(page.getByRole('listitem').filter({ hasText: 'Sparkling water' })).toBeVisible();

  const addedRow = page.getByRole('listitem').filter({ hasText: 'Sparkling water' });
  await addedRow.getByRole('button', { name: 'Remove' }).click();
  await addedRow.getByRole('button', { name: 'Confirm remove' }).click();
  await expect(page.getByText('Removed Sparkling water from the current draft.')).toBeVisible();
  await expect(page.getByRole('heading', { name: /Removed from this draft/i })).toBeVisible();

  await page.getByRole('button', { name: 'Review and confirm' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByText('2 shopping lines • 1 ad hoc • 1 override')).toBeVisible();
  await page.getByRole('button', { name: 'Confirm for shopping' }).click();
  await expect(page.getByText('Confirmed this grocery list for shopping. This version is now locked from edits.')).toBeVisible();
  await expect(page.getByRole('button', { name: '+ Quick add trip item' })).toBeVisible();
});

test('grocery review stays usable on a phone-sized viewport', async ({ page }) => {
  const scenario = createScenario();
  await fulfillGrocery(page, scenario);

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/grocery');

  await expect(page.getByRole('button', { name: 'Refresh draft' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Review and confirm' })).toBeVisible();

  const tomatoesRow = page.getByRole('listitem').filter({ hasText: 'Tomatoes' });
  await tomatoesRow.getByRole('button', { name: 'Show details' }).click();
  await expect(tomatoesRow.getByText('Meal traceability')).toBeVisible();

  await page.getByRole('button', { name: 'Review and confirm' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm for shopping' })).toBeVisible();
});

test('trip mode queues offline changes and syncs them after reconnect on a phone-sized viewport', async ({
  page,
}) => {
  const scenario = createScenario(
    createList(isoMonday(), {
      status: 'confirmed',
      confirmed_at: '2026-03-08T12:40:00Z',
      is_stale: false,
      incomplete_slot_warnings: [],
      trip_state: 'confirmed_list_ready',
    })
  );
  await fulfillGrocery(page, scenario);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/grocery');

  await expect(page.getByRole('heading', { name: 'Trip mode' })).toBeVisible();

  const tomatoesRow = page.getByRole('listitem').filter({ hasText: 'Tomatoes' });
  await page.context().setOffline(true);
  await tomatoesRow.getByRole('button', { name: 'Mark done' }).click();
  await tomatoesRow.getByRole('button', { name: 'Confirm done' }).click();
  await expect(
    page.getByText('Marked Tomatoes done on this phone. It will sync when the connection is ready.')
  ).toBeVisible();
  await expect(page.getByText('Offline — this phone is using the saved confirmed-list snapshot.')).toBeVisible();

  await page.context().setOffline(false);
  await page.reload();
  await expect(page.getByText('Trip sync active')).toBeVisible();
  await expect(page.getByRole('heading', { name: /Done on this phone/i })).toBeVisible();
  await expect(page.getByRole('listitem').filter({ hasText: 'Tomatoes' })).toBeVisible();
});

test('trip mode lets a shopper review a conflict and keep their saved change on phone-sized screens', async ({
  page,
}) => {
  const periodStart = isoMonday();
  const baseList = createList(periodStart, {
    status: 'confirmed',
    current_version_number: 4,
    current_version_id: 'version-4',
    confirmed_at: '2026-03-08T12:40:00Z',
    is_stale: false,
    incomplete_slot_warnings: [],
    trip_state: 'confirmed_list_ready',
  });
  const keepMineList = createList(periodStart, {
    status: 'trip_in_progress',
    current_version_number: 6,
    current_version_id: 'version-6',
    confirmed_at: '2026-03-08T12:40:00Z',
    is_stale: false,
    incomplete_slot_warnings: [],
    trip_state: 'trip_in_progress',
  });
  keepMineList.lines[0]!.user_adjusted_quantity = '5';
  keepMineList.lines[0]!.user_adjustment_note = 'Need more for the shared dinner';
  keepMineList.lines[0]!.user_adjustment_flagged = true;
  keepMineList.lines[0]!.shopping_quantity = '3';
  keepMineList.lines[0]!.updated_at = '2026-03-08T13:10:00Z';

  const useServerList = createList(periodStart, {
    status: 'trip_in_progress',
    current_version_number: 5,
    current_version_id: 'version-5',
    confirmed_at: '2026-03-08T12:40:00Z',
    is_stale: false,
    incomplete_slot_warnings: [],
    trip_state: 'trip_in_progress',
  });
  useServerList.lines[0]!.shopping_quantity = '2';
  useServerList.lines[0]!.user_adjusted_quantity = null;
  useServerList.lines[0]!.user_adjustment_note = null;
  useServerList.lines[0]!.user_adjustment_flagged = false;
  useServerList.lines[0]!.updated_at = '2026-03-08T13:00:00Z';

  const scenario: GroceryScenario = {
    householdId: 'household-abc',
    userId: 'user-123',
    periodStart,
    list: baseList,
    syncConflict: {
      detail: {
        conflict_id: 'conflict-qty-1',
        household_id: 'household-abc',
        aggregate: {
          aggregate_type: 'grocery_line',
          aggregate_id: 'line-1',
          aggregate_version: 5,
          provisional_aggregate_id: null,
        },
        local_mutation_id: 'offline-local-change',
        mutation_type: 'adjust_quantity',
        outcome: 'review_required_quantity',
        base_server_version: 4,
        current_server_version: 5,
        requires_review: true,
        summary: 'Tomatoes changed on another phone while you were offline.',
        local_queue_status: 'review_required',
        allowed_resolution_actions: ['keep_mine', 'use_server'],
        resolution_status: 'pending',
        created_at: '2026-03-08T13:01:00Z',
        resolved_at: null,
        resolved_by_actor_id: null,
        local_intent_summary: {
          ingredient_name: 'Tomatoes',
          quantity_to_buy: 5,
          user_adjustment_note: 'Need more for the shared dinner',
        },
        base_state_summary: {
          ingredient_name: 'Tomatoes',
          quantity_to_buy: 3,
        },
        server_state_summary: {
          ingredient_name: 'Tomatoes',
          quantity_to_buy: 2,
          user_adjustment_note: 'Another shopper already updated the quantity',
        },
      },
      keepMineList,
      useServerList,
    },
  };
  await fulfillGrocery(page, scenario);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/grocery');

  const tomatoesRow = page.getByRole('listitem').filter({ hasText: 'Tomatoes' });
  await page.context().setOffline(true);
  await tomatoesRow.getByRole('button', { name: 'Set amount' }).click();
  await tomatoesRow.getByLabel('Remaining amount to buy').fill('5');
  await tomatoesRow.getByLabel('Optional trip note').fill('Need more for the shared dinner');
  await tomatoesRow.getByRole('button', { name: 'Save amount' }).click();

  await page.context().setOffline(false);
  await page.reload();

  await expect(page.getByRole('heading', { name: 'Saved sync issues' })).toBeVisible();
  await expect(
    page.getByText('Tomatoes changed on another phone while you were offline.')
  ).toBeVisible();
  await expect(page.getByText('Quantity conflict')).toBeVisible();

  await page.getByRole('button', { name: 'Review details' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByText('Your saved change')).toBeVisible();
  await expect(page.getByText('Server version now')).toBeVisible();
  await expect(page.getByText('Need more for the shared dinner')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Keep mine' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Use server' })).toBeVisible();

  await page.getByRole('button', { name: 'Keep mine' }).click();
  await expect(
    page.getByText('Kept your saved trip change and refreshed this phone from the latest server state.')
  ).toBeVisible();
  await expect(page.getByText('Kept mine')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Saved sync issues' })).toHaveCount(0);
  await expect(tomatoesRow.getByText('5 ea', { exact: true })).toBeVisible();
  await expect(tomatoesRow.getByText('Override note: Need more for the shared dinner')).toBeVisible();
});

test('trip mode lets a shopper discard the local change and use the server copy on phone-sized screens', async ({
  page,
}) => {
  const periodStart = isoMonday();
  const baseList = createList(periodStart, {
    status: 'confirmed',
    current_version_number: 4,
    current_version_id: 'version-4',
    confirmed_at: '2026-03-08T12:40:00Z',
    is_stale: false,
    incomplete_slot_warnings: [],
    trip_state: 'confirmed_list_ready',
  });
  const keepMineList = clone(baseList);
  const useServerList = createList(periodStart, {
    status: 'trip_in_progress',
    current_version_number: 5,
    current_version_id: 'version-5',
    confirmed_at: '2026-03-08T12:40:00Z',
    is_stale: false,
    incomplete_slot_warnings: [],
    trip_state: 'trip_in_progress',
  });
  useServerList.lines[0]!.shopping_quantity = '2';
  useServerList.lines[0]!.user_adjusted_quantity = null;
  useServerList.lines[0]!.user_adjustment_note = null;
  useServerList.lines[0]!.user_adjustment_flagged = false;
  useServerList.lines[0]!.updated_at = '2026-03-08T13:00:00Z';

  const scenario: GroceryScenario = {
    householdId: 'household-abc',
    userId: 'user-123',
    periodStart,
    list: baseList,
    syncConflict: {
      detail: {
        conflict_id: 'conflict-qty-2',
        household_id: 'household-abc',
        aggregate: {
          aggregate_type: 'grocery_line',
          aggregate_id: 'line-1',
          aggregate_version: 5,
          provisional_aggregate_id: null,
        },
        local_mutation_id: 'offline-local-change-2',
        mutation_type: 'adjust_quantity',
        outcome: 'review_required_quantity',
        base_server_version: 4,
        current_server_version: 5,
        requires_review: true,
        summary: 'Tomatoes changed on another phone while you were offline.',
        local_queue_status: 'review_required',
        allowed_resolution_actions: ['keep_mine', 'use_server'],
        resolution_status: 'pending',
        created_at: '2026-03-08T13:01:00Z',
        resolved_at: null,
        resolved_by_actor_id: null,
        local_intent_summary: {
          ingredient_name: 'Tomatoes',
          quantity_to_buy: 5,
        },
        base_state_summary: {
          ingredient_name: 'Tomatoes',
          quantity_to_buy: 3,
        },
        server_state_summary: {
          ingredient_name: 'Tomatoes',
          quantity_to_buy: 2,
        },
      },
      keepMineList,
      useServerList,
    },
  };
  await fulfillGrocery(page, scenario);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/grocery');

  const tomatoesRow = page.getByRole('listitem').filter({ hasText: 'Tomatoes' });
  await page.context().setOffline(true);
  await tomatoesRow.getByRole('button', { name: 'Set amount' }).click();
  await tomatoesRow.getByLabel('Remaining amount to buy').fill('5');
  await tomatoesRow.getByRole('button', { name: 'Save amount' }).click();

  await page.context().setOffline(false);
  await page.reload();

  await page.getByRole('button', { name: 'Review details' }).click();
  await page.getByRole('button', { name: 'Use server' }).click();

  await expect(
    page.getByText('Accepted the server copy and refreshed this phone to match it.')
  ).toBeVisible();
  await expect(page.getByText('Used server')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Saved sync issues' })).toHaveCount(0);
  await expect(tomatoesRow.getByText('2 ea', { exact: true })).toBeVisible();
});
