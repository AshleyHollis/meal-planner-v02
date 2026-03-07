# Uhura — GROC-06 API Wiring Decision

**Date:** 2026-03-08  
**Consolidated by:** Scribe  
**Status:** ✅ APPROVED

## Decision

The grocery web client treats the grocery surface as a **review/confirmation flow**, not an active trip execution flow. Removed the unsupported purchased-line checkbox assumption from the current page and wired only the actions that exist in Scotty's live router: derive, re-derive, confirm, and add ad hoc while the list is still a draft.

## Why

- The approved backend grocery contract exposes draft/confirmed/trip lifecycle states, but it does **not** expose a purchased-line mutation for Milestone 3 grocery review.
- Leaving the old checkbox in place would make the UI promise a trip-mode behavior that the backend cannot honor and would blur the Milestone 3 / Milestone 4 boundary.
- This keeps the frontend honest about the current authority line while still exposing the real grocery lifecycle and mutation seams McCoy can verify now.

## Follow-on impact

- GROC-07 can build richer review UX on top of the contract-aligned seam without having to unwind fake status or optimistic purchase behavior.
- Milestone 4 trip-mode work should introduce explicit trip execution APIs/read models before the frontend brings back interactive purchased/skipped item handling.

## Implementation Evidence

✅ GROC-06 complete and verified:
- `apps/web/app/_lib/types.ts` and `apps/web/app/_lib/grocery-api.ts` now map backend lifecycle (`draft`, `stale_draft`, `confirmed`, trip states) and origins (`derived`, `ad_hoc`)
- `apps/web/app/grocery/_components/GroceryView.tsx`, `GroceryLineRow.tsx`, and CSS updated to use `activeHouseholdId`, remove purchased-line flow, expose derive/re-derive/confirm/ad-hoc actions, surface stale/incomplete states
- `apps/web/app/_lib/grocery-api.test.ts` added with contract regression coverage
- All validation commands passed: lint, typecheck, test (30 tests including new grocery coverage), build

## Approval chain

- **Proposed by:** Uhura (2026-03-08)
- **Consolidated by:** Scribe (2026-03-08T21-00-00Z)
- **Locked in:** Milestone 3 execution, GROC-06 complete
