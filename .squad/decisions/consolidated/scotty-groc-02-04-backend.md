# Scotty Decision Inbox — GROC-02 / GROC-04 Backend Ingredient Seam

Date: 2026-03-08
Requested by: Ashley Hollis
Task: GROC-02 / GROC-04

## Decision

Use a temporary backend-owned meal ingredient catalog seam keyed by `meal_reference_id` (with deterministic title-slug fallback) for grocery derivation until the real recipe/meal-definition persistence lands.

## Why

- The grocery derivation rules are ready now, but the repo still does not have a durable recipe ingredient store for confirmed plan slots.
- Scotty still needed an authoritative, testable input seam for GROC-02/GROC-04 that does **not** invent ingredient data from AI summaries or fuzzy text parsing.
- This keeps the trust boundary honest: slots with no catalog entry surface incomplete-slot warnings instead of silently fabricating grocery needs.

## Implementation Notes

- `apps/api/app/services/grocery_service.py` now resolves ingredients from an injected `MealIngredientCatalog`.
- The catalog prefers explicit `meal_reference_id`; only a deterministic title slug is used as a narrow fallback seam for tests and temporary local data.
- Grocery derivation remains confirmed-plan-only, exact-name/exact-unit for inventory offsets, and warning-driven when ingredient data is absent.

## Consequences

- Backend and API contract work can proceed now without blocking on the future recipe domain.
- Real recipe persistence should later replace the catalog lookup behind the same service seam rather than forcing another router contract rewrite.
- Until that swap happens, many AI-generated confirmed meals without known references will honestly derive warnings instead of full grocery lines.
