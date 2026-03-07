# Scotty — GROC-03 Refresh Orchestration Decision

**Date:** 2026-03-08  
**Consolidated by:** Scribe  
**Status:** ✅ APPROVED

## Decision

For GROC-03, grocery refresh orchestration consumes the durable `planner_events.plan_confirmed` record as the authoritative refresh trigger, while planner and inventory API routes perform only best-effort immediate refresh kickoff after their authoritative write succeeds.

Inventory-driven stale detection is scoped to ingredient names/units relevant to the confirmed plan being derived, not to the entire household inventory snapshot.

## Rationale

- The confirmed-plan event is already persisted in the same transaction as planner confirmation, so using that row as the grocery consumer input preserves idempotency and avoids inventing a second planner→grocery trigger seam.
- Best-effort route-triggered processing gives users immediate refresh/stale behavior in the current single-process MVP without making planner confirmation or inventory mutation responses depend on a downstream grocery side effect succeeding in the same request.
- Comparing only relevant inventory state prevents unrelated pantry churn from flipping grocery drafts to `stale_draft`, which better matches the approved spec language about inventory changes that affect a derived grocery need.

## Consequences

- Grocery refresh remains diagnosable and replayable because unpublished `plan_confirmed` rows can still be re-consumed later if immediate orchestration fails.
- Inventory create/update/archive/correction flows now participate in grocery stale orchestration, but only drafts whose confirmed-plan ingredient surface overlaps the changed inventory can become stale.
- Confirmed grocery lists stay immutable: automatic refresh creates a new draft when needed instead of rewriting the confirmed list in place.

## Implementation Evidence

✅ GROC-03 complete and verified:
- `apps/api/app/services/grocery_service.py` now implements refresh orchestration consuming `plan_confirmed` events
- `apps/api/app/routers/planner.py` triggers best-effort grocery refresh after draft confirmation
- `apps/api/app/routers/inventory.py` triggers best-effort stale-refresh orchestration
- Regression tests cover planner-event-driven derivation, draft refresh with state preservation, confirmed-list immutability, and inventory-scoped stale detection
- All validation commands passed: pytest (11 focused + 75 regression + 164 full suite), compileall

## Approval chain

- **Proposed by:** Scotty (2026-03-08)
- **Consolidated by:** Scribe (2026-03-08T21-00-00Z)
- **Locked in:**  Milestone 3 execution, GROC-03 complete
