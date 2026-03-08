# Milestone 3: GROC-05 and GROC-07 Launch (2026-03-08T21-00-00Z)

**Recorded by:** Scribe  
**On behalf of:** Ashley Hollis  
**Directive:** Build the full app and don't stop until it's complete and verified.

## Previous State

- **GROC-03** (refresh and stale-draft orchestration): ✅ **COMPLETE AND VERIFIED** 
  - Planner confirmation now consumes durable `plan_confirmed` events for automatic grocery refresh
  - Inventory mutations mark only relevant drafts stale
  - Ad hoc/override state survives refresh
  - Confirmed lists spawn a fresh draft instead of being mutated in place
  - All regression tests passing

- **GROC-06** (web grocery client API wiring): ✅ **COMPLETE AND VERIFIED**
  - Replaced placeholder grocery statuses/origins with backend contract (`draft`, `stale_draft`, `confirmed`, trip states; `derived`, `ad_hoc`)
  - Removed unsupported purchased-line checkbox flow
  - Wired derive/re-derive/confirm/ad-hoc actions to live router
  - Switched grocery calls to `activeHouseholdId`
  - All frontend tests passing (30 tests including new grocery coverage)

## Current State

### GROC-05: Backend Derivation and Contract Slice Verification
- **Owner:** McCoy
- **Status:** in_progress (launched 2026-03-08T21-00-00Z)
- **Dependencies:** GROC-03 ✅, GROC-06 ✅ (both complete)
- **Scope:** Mandatory acceptance gate covering:
  - Derivation engine correctness (confirmed-plan-only, conservative offsets, duplicate consolidation)
  - Contract alignment (derive/read/detail/re-derive/add-ad-hoc/adjust/remove/confirm endpoints)
  - Idempotency properties (household-scoped mutation receipts)
  - Stale detection behavior (inventory-scoped, relevant-ingredients-only)
  - Integration with refresh orchestration
- **Unblocks:** GROC-10 (E2E verification gate) cannot proceed until GROC-05 signs off

### GROC-07: Grocery Review and Confirmation UX Completion
- **Owner:** Uhura
- **Status:** in_progress (launched 2026-03-08T21-00-00Z)
- **Dependencies:** GROC-06 ✅ (contract-aligned seam in place)
- **Scope:** Mobile-readable review/confirmation flow including:
  - List presentation with derived + ad hoc items
  - Stale/incomplete state indication
  - Derive/re-derive/confirm/add-ad-hoc action exposure
  - Per-item adjustment UX (on top of backend contract)
  - Proper seaming to GROC-08 and downstream trip/reconciliation
- **Unblocks:** GROC-10 (E2E verification), GROC-08 (confirmed-list handoff seams)

## Decision Consolidation

**Two pending decisions consolidated and archived:**

1. **GROC-03 Refresh Orchestration (Scotty):**
   - Durable `plan_confirmed` event consumption as authoritative trigger ✅
   - Best-effort route-triggered immediate processing ✅
   - Inventory-scoped stale detection (only relevant ingredients) ✅
   - Confirmed-list immutability via fresh-draft spawning ✅
   - **Filed:** `.squad/decisions/consolidated/2026-03-08T21-00-00Z-groc03-refresh-decision.md`

2. **GROC-06 API Wiring (Uhura):**
   - Review/confirmation flow (not active trip execution) ✅
   - No purchased-line checkbox (defer to Milestone 4) ✅
   - Contract-aligned derive/re-derive/confirm/ad-hoc only ✅
   - Milestone 3 / Milestone 4 boundary preserved ✅
   - **Filed:** `.squad/decisions/consolidated/2026-03-08T21-00-00Z-groc06-api-wiring-decision.md`

**Decision inbox status:** ✅ **CLEAR** (0 items remaining)

## Readiness Check

- ✅ Full app buildable (`npm run build:web`, `cd apps/api && python -m compileall`)
- ✅ All prior tests passing (GROC-01/02/03/04/06 complete + verified)
- ✅ GROC-05 and GROC-07 dependencies satisfied
- ✅ No blocking decisions
- ✅ Team synchronized on Milestone 3 / Milestone 4 boundaries

## Next Readiness Windows

| Task | Owner | Status | Preconditions |
| --- | --- | --- | --- |
| GROC-08 | Scotty | ready_now (pending GROC-07) | Waiting for GROC-07 confirmation UX closure to finalize confirmed-list handoff seams for trip/reconciliation |
| GROC-09 | Scotty | blocked | Waiting for GROC-05 verification sign-off to add observability/fixtures |
| GROC-10 | McCoy | ready_now (pending GROC-05+07) | McCoy will execute E2E verification after GROC-05 backend gate + GROC-07 UX completion |
| GROC-11 | Kirk | ready_now (pending GROC-10) | Final Milestone 3 acceptance review; no technical dependencies remain |

## Execution Status

- **Parallel execution:** GROC-05 (McCoy), GROC-07 (Uhura) both in_progress
- **Critical path:** GROC-05 → GROC-10, GROC-07 → GROC-10 → GROC-11
- **Zero blockers:** All upstream work complete, all decisions consolidated, team ready
- **Build verification:** ✅ Full app buildable, testable, and verifiable through Milestone 3 execution

---

**Milestone 3 Status:** Backend derivation and API contracts verified pending (GROC-05). Frontend UX completion in progress (GROC-07). All upstream work (GROC-01 through GROC-06) complete and locked. Decision inbox consolidated. Team executing on Ashley Hollis directive: build full app, don't stop until complete and verified.
