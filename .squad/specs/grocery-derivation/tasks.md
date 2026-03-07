# Grocery Derivation — Implementation Tasks

Date: 2026-03-07
Milestone: 3 (Grocery calculation and review before the trip)
Status: Draft — ready for implementation planning
Spec: `.squad/specs/grocery-derivation/feature-spec.md`

These tasks are ordered roughly by dependency. They are intentionally implementation-oriented but spec-level: they do not prescribe schema column names, endpoint paths, or component file names beyond what the spec has already decided.

---

## Domain and API

### GROC-01 — Define grocery list and grocery line data models
Define the authoritative data model for:
- `grocery_list` (including `household_id`, `plan_period_reference`, `confirmed_plan_version_id`, `inventory_snapshot_reference`, `derived_at`, `status`, `confirmed_at`),
- `grocery_line` (including `origin`, `ingredient_name`, optional `canonical_ingredient_ref`, `required_quantity`, `offset_quantity`, `shopping_quantity`, `unit`, `inventory_item_ref`, `meal_sources`, `user_adjusted_quantity`, `active`).

Include migration scripts or schema artifacts. Align with inventory foundation one-primary-unit-per-item rule and data-architecture bounded context for Grocery and Trip.

**Dependencies:** Inventory foundation data model, meal-plan slot schema.

---

### GROC-02 — Implement ingredient expansion from confirmed meal plan
Implement the service logic that reads the current confirmed meal plan for a household and expands each linked meal slot's ingredient list into raw grocery need entries.

Rules:
- Only confirmed/accepted meal slots contribute to derivation.
- Meal slots with no linked ingredient data produce no grocery lines and emit an incomplete-slot indicator.
- Each raw need carries: `ingredient_name`, `required_quantity`, `unit`, `source_meal_slot_id`.

Write unit tests covering: full ingredient data, partial slots with missing ingredients, confirmed versus draft slot filtering.

**Dependencies:** GROC-01, Meal plan confirmed-state contracts (Milestone 2).

---

### GROC-03 — Implement conservative inventory offset logic
Implement the inventory offset check per raw grocery need:
- Match only on obvious same-item, same-unit identity (shared canonical ingredient reference preferred; exact case-insensitive name + unit as fallback).
- Do not apply fuzzy name matching, unit conversion, or synonym resolution.
- Full cover: produce no grocery line; record the offset for traceability.
- Partial cover: produce a line for the remaining quantity only; record offset amount and inventory item reference.
- No match or uncertain match: produce a line at the full required quantity; do not apply any partial inferred offset.

Write unit tests covering: full match, partial match, name-only match without identifier (should not apply inferred offset for non-obvious cases), unit mismatch, archived/inactive inventory item (must not offset), unknown-unit item.

**Dependencies:** GROC-01, GROC-02, Inventory foundation authoritative balances API.

---

### GROC-04 — Implement duplicate consolidation and meal traceability
After inventory offsets, group remaining grocery needs by ingredient identity and unit:
- Same ingredient + same unit → sum quantities into one consolidated line; attach `meal_sources` list with per-meal contribution amounts.
- Same ingredient + different units → keep as separate lines; do not consolidate.

Write unit tests covering: two meals needing same item+unit, three meals needing same item+unit, same ingredient but different units kept separate, single-meal lines (no consolidation needed), consolidation preserving traceability references.

**Dependencies:** GROC-03.

---

### GROC-05 — Implement derivation run orchestration and result persistence
Implement the derivation orchestration entry point that:
1. Reads the confirmed plan for the household/period.
2. Expands ingredients (GROC-02).
3. Applies inventory offsets (GROC-03).
4. Consolidates duplicates (GROC-04).
5. Persists the grocery list version with all derived lines and `status: draft`.
6. Emits incomplete-slot indicators when applicable.
7. Preserves existing ad hoc items and user adjustments from any prior draft version when re-deriving.

Derivation should be idempotent given the same confirmed plan version and inventory snapshot: running it twice must not duplicate lines.

Write integration tests covering: full derivation from seeded plan + inventory, re-derivation preserving ad hoc items, re-derivation flagging changed user overrides.

**Dependencies:** GROC-01 through GROC-04.

---

### GROC-06 — Implement automatic refresh triggers
Wire up refresh triggers so the derivation re-runs or the grocery list is marked `stale_draft` when:
- the confirmed meal plan changes (new confirmation, slot edit, plan replacement),
- inventory changes affect an item referenced in the current derivation (quantity change, archive, unit change).

Decide in implementation whether to re-derive immediately on the event or to mark the draft stale and re-derive on next fetch. Either approach must not silently alter a `confirmed` list that a trip is operating against.

Write tests covering: plan change triggers stale or refresh, inventory change on matched item triggers stale or refresh, confirmed list is not silently altered by a plan or inventory change after confirmation.

**Dependencies:** GROC-05, Inventory mutation event hooks, Meal-plan confirmation event hooks.

---

### GROC-07 — Implement ad hoc grocery item commands
Implement API commands to:
- add an ad hoc grocery item (name, quantity, unit, optional note),
- remove an ad hoc item,
- edit an ad hoc item's quantity or note.

Ad hoc items must:
- be labeled `origin: ad_hoc` in all read models,
- survive automatic derivation refresh,
- be idempotent via client mutation ID,
- respect household authorization.

Write unit and integration tests covering: add, edit quantity, remove, survival across re-derive, idempotent re-add.

**Dependencies:** GROC-01, GROC-05.

---

### GROC-08 — Implement user adjustment commands on derived lines
Implement the API command for a user to override the shopping quantity on a derived grocery line:
- Store as `user_adjusted_quantity` alongside the original `shopping_quantity`.
- On subsequent re-derivation: if the underlying derived quantity changes, flag the line with a `user_adjustment_needs_review` indicator but preserve the user's adjusted value.
- The user may accept the new derived value (clearing their override) or keep their adjusted value explicitly.

Write tests covering: adjustment saved, adjustment survives re-derive, re-derive with changed derived quantity sets the flag, user accepting new derived value clears adjustment flag.

**Dependencies:** GROC-05, GROC-06.

---

### GROC-09 — Implement grocery list confirmation command
Implement the API command to confirm the draft grocery list for a trip:
- Transition list status from `draft` to `confirmed`.
- Record `confirmed_at` and actor.
- A `stale_draft` list must require re-derivation acknowledgment or re-derivation before confirmation is allowed (implementation may require explicit re-derive before confirm, or allow confirming a stale draft with a warning; spec does not prescribe which but the staleness must not be hidden).
- Confirmation must be idempotent: confirming an already-confirmed list returns the existing confirmed state without creating a duplicate.

Write tests covering: confirm draft, confirm stale draft behavior (per implementation choice), idempotent re-confirm, confirm fails or warns if plan version has changed since last derivation.

**Dependencies:** GROC-05.

---

### GROC-10 — Implement grocery list read models and API endpoints
Expose API endpoints for:
- list summary: all active lines (derived + ad hoc), shopping quantities, origin labels, meal traceability summary, list status, stale indicator.
- line detail: full offset breakdown (required, offset amount, offset item reference), meal traceability detail (per-meal contributions), user adjustment status.
- incomplete-slot warnings from the most recent derivation run.
- list history or last-derived-at metadata.

Read models must be optimized for both desktop review and mobile consumption (lightweight summary path available).

Write contract/integration tests for each endpoint shape. Verify mobile-relevant payload size is not unnecessarily bloated.

**Dependencies:** GROC-05 through GROC-09.

---

### GROC-11 — Wire grocery derivation into trip list hand-off
Ensure the confirmed grocery list version is the authoritative input handed to the trip execution flow (Milestone 4):
- Trip sessions reference a specific `grocery_list_version_id`.
- The trip list is initialized from the confirmed lines of that version.
- A re-derivation or new confirmation after the trip starts does not mutate the trip's list version.

This task may be partly deferred to Milestone 4 implementation, but the version-identity seam must be defined and tested here so Milestone 4 has a stable contract to depend on.

Write integration tests covering: trip session referencing correct list version, new derivation does not alter existing trip's list version.

**Dependencies:** GROC-09, Milestone 4 trip session contracts.

---

## Frontend and UX

### GROC-12 — Implement grocery list view (desktop and mobile)
Build the grocery list UI component that shows:
- derived lines and ad hoc lines in a unified list with clear origin labeling,
- shopping quantity (remaining to buy) prominently,
- traceability summary (contributing meals) accessible without cluttering the default view,
- stale-draft indicator when the list may not reflect latest plan or inventory,
- incomplete-slot warnings with enough detail to understand which meals are affected,
- list status (draft, confirmed, stale) clearly visible.

Mobile layout must meet the mobile-shopping-first requirements: readable at phone size, adequate touch targets for key actions.

Write component tests for derived line rendering, ad hoc line rendering, stale indicator visibility, traceability detail expand/collapse, empty-state (no confirmed plan), and loading/error states.

**Dependencies:** GROC-10.

---

### GROC-13 — Implement add / edit / remove ad hoc item UX
Build the UX flow for adding, editing, and removing ad hoc grocery items:
- Minimal input: name, quantity, unit at minimum.
- Should be operable on mobile without significant typing friction.
- Confirmation of remove when removing an item from a confirmed list.

Write component tests for: add form validation, quantity edit, remove with confirmation, mobile usability check on touch targets.

**Dependencies:** GROC-07, GROC-12.

---

### GROC-14 — Implement user adjustment UX on derived lines
Build the UX affordance for adjusting the shopping quantity on a derived grocery line:
- Display current `shopping_quantity` with an edit affordance.
- After adjustment, show the user's value alongside an indicator that the original derived amount differed (if it does).
- If a re-derivation flags a `user_adjustment_needs_review` change, surface the notice clearly with the option to keep the user's value or adopt the new derived value.

Write component tests for: initial display of derived quantity, inline edit, needs-review notice display, accept-new-value action, keep-adjusted-value action.

**Dependencies:** GROC-08, GROC-12.

---

### GROC-15 — Implement grocery list confirmation flow
Build the confirm-for-trip UX:
- Prominent confirm action on the draft list view.
- If the list is stale, surface the staleness and require acknowledgment or re-derivation before confirming.
- After confirmation, show confirmed state clearly and make the trip-start action accessible.

Write component and E2E tests for: confirm from clean draft, confirm from stale draft (acknowledgment or block per implementation choice), already-confirmed list behavior.

**Dependencies:** GROC-09, GROC-12.

---

### GROC-16 — Implement meal traceability detail view
Build the drill-down view for a consolidated grocery line that shows:
- the list of meals contributing to this line,
- each meal's individual quantity contribution.

This should be accessible without cluttering the default list view (e.g., expandable row, detail panel, or tooltip appropriate to mobile and desktop).

Write component tests for: single-meal line (no traceability detail needed beyond origin), multi-meal consolidated line with all contributions shown.

**Dependencies:** GROC-10, GROC-12.

---

## Offline and Sync

### GROC-17 — Offline-cache the confirmed grocery list snapshot
Ensure the confirmed grocery list (lines, quantities, meal traceability, origin labels) is written to the client's offline store (IndexedDB) when confirmed and kept available for offline trip access.

The cached snapshot must be:
- the specific confirmed list version, not a live-derived projection,
- available when the client is fully offline,
- clearly timestamped so the user understands when it was last confirmed.

Write tests covering: cache written on confirmation, cache readable when offline, cache remains stable after a new derivation (trip is against the confirmed version, not the new draft).

**Dependencies:** GROC-09, Offline sync infrastructure (Milestone 4 foundations).

---

### GROC-18 — Idempotent offline grocery list mutations
Ensure all list-mutating commands (add ad hoc, remove, adjust quantity, confirm) carry a client mutation ID and are accepted idempotently by the server:
- Duplicate submissions (offline retry, reconnect replay) must not create duplicate lines or double-apply quantity changes.
- Idempotency receipts must follow the same pattern established in the inventory foundation and offline sync conflict specs.

Write tests covering: duplicate add ad hoc (idempotent result), duplicate quantity adjustment (idempotent result), duplicate confirm (idempotent result), batch reconnect replay.

**Dependencies:** GROC-07, GROC-08, GROC-09, Sync mutation receipt infrastructure.

---

### GROC-19 — Stale-draft detection and notification for shared-household changes
Implement the shared-household notification path that marks the grocery draft `stale_draft` when:
- another household member confirms a new meal plan while the draft is open,
- another household member changes inventory for an item used in the current derivation.

The notification must surface visibly to the current user (e.g., a stale banner on the list view) without silently re-deriving and overwriting their draft adjustments or ad hoc items.

Write integration tests covering: plan change by another member triggers stale state, inventory change by another member triggers stale state, stale state visible to current user on next list load, ad hoc items not lost when stale is detected.

**Dependencies:** GROC-06, GROC-12, Shared household event/notification path.

---

## Observability and Tests

### GROC-20 — Derivation run observability
Add structured logging and metrics for each derivation run:
- Log: plan period, plan version, inventory snapshot reference, raw need count, offset need count, consolidated line count, incomplete-slot count.
- Log: list confirmation events with actor and household.
- Metrics (when telemetry infrastructure exists): derivation run count, offset rate, incomplete-slot rate, ad hoc addition rate, user adjustment rate, stale-draft detection rate.

Ensure correlation IDs from the request flow are included in derivation log entries.

**Dependencies:** GROC-05, GROC-09, Project observability conventions.

---

### GROC-21 — Backend unit and integration test suite for derivation rules
Establish a comprehensive test suite for all derivation rules:
- Full derivation from a complete plan (no inventory offset): all meal ingredients appear.
- Partial inventory offset: line shows remaining amount only.
- Full inventory offset: no grocery line produced.
- No inventory match: line at full quantity.
- Consolidated duplicate needs: one line, correct summed quantity, all meal sources listed.
- Non-consolidated different-unit needs: two separate lines.
- Staple with no inventory: staple appears on list.
- Staple fully covered by inventory: staple does not appear.
- Incomplete meal slot: warning emitted, remaining slots derive normally.
- Ad hoc items survive re-derivation.
- User override flagged after re-derivation that changes derived quantity.
- Confirmed list not altered by re-derivation.

**Dependencies:** GROC-05 through GROC-09.

---

### GROC-22 — E2E test: weekly planning to confirmed grocery list
Implement an E2E test covering the full flow from confirmed meal plan to confirmed grocery list:
1. Seed a household with inventory (some items fully covering needs, some partially, some not present).
2. Confirm a weekly meal plan.
3. Trigger derivation.
4. Assert grocery lines: correct items, correct remaining quantities, offset items absent or reduced, consolidated lines with traceability.
5. Add an ad hoc item.
6. Confirm the grocery list.
7. Assert: confirmed status, ad hoc item present, derived lines correct.

This E2E evidence is required before Milestone 3 is considered complete per the roadmap quality gates.

**Dependencies:** GROC-21, E2E harness (Milestone 0).

---

### GROC-23 — E2E test: grocery list refresh and shared-household stale scenario
Implement an E2E test covering the refresh and stale-detection flow:
1. Derive a draft grocery list.
2. Add an ad hoc item and a user adjustment.
3. Simulate a plan change (another actor confirms a new plan).
4. Assert: list marked stale, ad hoc item still present, user adjustment still present.
5. Re-derive.
6. Assert: list updated to new plan needs, ad hoc item preserved, user adjustment flagged if underlying derived quantity changed.

**Dependencies:** GROC-22.

---

## Task Summary

| ID | Area | Description |
| --- | --- | --- |
| GROC-01 | Data model | Grocery list and grocery line schema |
| GROC-02 | Domain | Ingredient expansion from confirmed meal plan |
| GROC-03 | Domain | Conservative inventory offset logic |
| GROC-04 | Domain | Duplicate consolidation and meal traceability |
| GROC-05 | Domain | Derivation orchestration and result persistence |
| GROC-06 | Domain | Automatic refresh triggers |
| GROC-07 | API | Ad hoc item commands |
| GROC-08 | API | User adjustment commands on derived lines |
| GROC-09 | API | Grocery list confirmation command |
| GROC-10 | API | Read models and endpoints |
| GROC-11 | API | Trip list hand-off seam |
| GROC-12 | Frontend | Grocery list view (desktop and mobile) |
| GROC-13 | Frontend | Add/edit/remove ad hoc item UX |
| GROC-14 | Frontend | User adjustment UX on derived lines |
| GROC-15 | Frontend | Grocery list confirmation flow |
| GROC-16 | Frontend | Meal traceability detail view |
| GROC-17 | Offline | Offline-cache confirmed list snapshot |
| GROC-18 | Offline | Idempotent offline grocery list mutations |
| GROC-19 | Offline | Stale-draft detection for shared-household changes |
| GROC-20 | Observability | Derivation run logging and metrics |
| GROC-21 | Tests | Backend unit/integration test suite |
| GROC-22 | Tests | E2E: plan to confirmed grocery list |
| GROC-23 | Tests | E2E: refresh and stale-household scenario |
