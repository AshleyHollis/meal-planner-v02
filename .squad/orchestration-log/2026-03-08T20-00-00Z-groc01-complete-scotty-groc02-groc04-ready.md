# Orchestration: GROC-01 Complete / Scotty Activation (GROC-02/GROC-04)

**Timestamp:** 2026-03-08T20-00-00Z  
**Orchestrator:** Scribe  
**Requested by:** Ashley Hollis (Milestone 3 execution directive)

---

## Event: GROC-01 Completion and Acceptance

**Task:** GROC-01 — Tighten grocery schema, lifecycle enums, and migration seams  
**Owner:** Sulu  
**Status:** ✅ **COMPLETE**

### Completion Evidence

- **Models:** `apps/api/app/models/grocery.py` enhanced with:
  - `GroceryMutationReceipt` table for household-scoped idempotent mutations (client_mutation_id replay boundary)
  - `GroceryList` confirmation mutation tracking for immutable confirmed-list contract
  - `GroceryListVersion` incomplete-slot warning payload storage (version-level warnings, not per-line)
  - Offset inventory version references for traceability
  - Active/removed line metadata to preserve confirmed-list semantics
  
- **Schemas:** `apps/api/app/schemas/grocery.py` updated with:
  - Parsed incomplete-slot warnings exposed to derivation/UI consumers
  - Meal-source traceability fields for confirmed-plan linkage
  - Ad hoc create command accepting Milestone 3 shopping-quantity contract
  - Backward-compatible legacy quantity field handling

- **Migrations:** Reversible alembic seam `apps/api/migrations/versions/rev_20260308_04_groc01_grocery_schema_seams.py`
  - Forward: Adds mutation receipts, warning payload, version references, active/removed fields
  - Backward: Safe rollback for development iteration

- **Test Coverage:** `apps/api/tests/test_groc01_migration.py` regression suite
  - Household isolation on mutation receipts
  - Version uniqueness enforcement
  - Warning payload persistence
  - Line active/removed state semantics
  - Offset reference metadata correctness

- **Validation Results (2026-03-08):**
  - API test suite: ✅ 151 tests passed
  - API compileall: ✅ All modules compile
  - Web lint: ✅ Clean
  - Web typecheck: ✅ Clean
  - Web build: ✅ Success
  - Worker tests: ✅ 9/9 passed

### Acceptance Criteria Met

1. ✅ Models reflect approved lifecycle (derived, draft, confirmed)
2. ✅ Version semantics and idempotency contract implemented
3. ✅ Lifecycle enums distinct from planner states
4. ✅ Quantity/unit handling follows inventory precedent (one primary unit, no silent cross-unit)
5. ✅ Line adjustments support override without losing offset traceability
6. ✅ Line items ready for per-unit cost and availability indicators (Milestone 3)
7. ✅ Migration seams exist and reversible
8. ✅ Deterministic fixtures prove household isolation and idempotency
9. ✅ Lint/typecheck/test clean (no new noise)

### Cross-Team Guidance from GROC-01 Decision

- **Scotty (GROC-02/GROC-04):** Treat `grocery_mutation_receipts` as authoritative idempotency seam; build derivation from confirmed-plan event + current inventory snapshot
- **Uhura (GROC-06/GROC-07):** Consume warning payload from grocery list version; present as list-level derivation honesty
- **McCoy (GROC-05):** Verify against contract names: `confirmed_plan_version`, `required_quantity`, `offset_quantity`, `shopping_quantity`, `active`, version-level `incomplete_slot_warnings`

---

## Event: GROC-02/GROC-04 Handoff to Scotty

**Tasks:** 
- GROC-02 — Implement derivation engine and authoritative persistence  
- GROC-04 — Implement grocery API router and mutation contracts

**Owner:** Scotty  
**Status:** 🚀 **READY NOW**

### Dependencies Satisfied

- ✅ GROC-01 schema complete and verified
- ✅ Confirmed-plan handoff contract verified from Milestone 2 (`plan_confirmed` event + payload)
- ✅ Inventory foundation stable (Milestone 1)
- ✅ Household session/auth trustworthy
- ✅ Zero blockers to GROC-02/GROC-04 implementation

### Scope Summary

**GROC-02 — Derivation Engine:**
- Build derivation service consuming `plan_confirmed` events (exclusive trigger)
- Derive grocery items from confirmed meal plan + current household inventory
- Implement incomplete-slot detection and warning payload storage
- Offset matching: conservative same-item, same-unit only (no fuzzy cross-unit conversion)
- Save derived list in draft state with `confirmed_plan_version` reference
- Preserve user adjustments across refresh cycles without silent mutation of confirmed lists

**GROC-04 — API Router:**
- Activate `/api/v1/grocery/*` endpoints in `apps/api/app/main.py`
- Implement mutation contracts: add/adjust/remove lines, list confirmation
- Use `GroceryMutationReceipt` for idempotent retries
- Expose contract-aligned schemas from GROC-01
- No active grocery router exists yet; this is the core backend activation

### Critical-Path Dependencies

GROC-02/GROC-04 completion **unblocks:**
- GROC-03 (Refresh and stale-draft orchestration by Scotty)
- GROC-05 (Backend verification gate by McCoy)
- GROC-06/GROC-07 (Frontend rewiring by Uhura)

### Watchpoints

1. **Confirmed-list immutability:** Refresh must never mutate a confirmed list silently
2. **Idempotency seam:** Use `GroceryMutationReceipt` for all client mutations
3. **Traceability:** Preserve offset references and meal-source links for Milestone 5 reconciliation
4. **Auth boundary:** Keep API-owned session/bootstrap; no frontend-owned auth assumptions
5. **Scope boundary:** Derivation and router only; stale detection (GROC-03), trip execution (Milestone 4), and reconciliation (Milestone 5) are explicit follow-ons

---

## Event: Milestone 3 Progress Ledger Update

**File:** `.squad/specs/grocery-derivation/progress.md`

### Status: GROC-01 Done → GROC-02/GROC-04 In_Progress Ready

| ID | Task | Agent | Status | Notes |
| --- | --- | --- | --- | --- |
| GROC-01 | Tighten grocery schema, lifecycle enums, and migration seams | Sulu | **done** | Completed 2026-03-08. Schema and models verified; all tests green. Ready for handoff. |
| GROC-02 | Implement derivation engine and authoritative persistence | Scotty | **pending** | Dependencies satisfied (GROC-01 done); ready to start now. |
| GROC-03 | Implement refresh and stale-draft orchestration | Scotty | **pending** | Blocked by GROC-02; queued behind GROC-04. |
| GROC-04 | Implement grocery API router and mutation contracts | Scotty | **pending** | Dependencies satisfied (GROC-01 done); parallel with GROC-02, critical-path for frontend unblock. |

### Ready-Now Targets

- **Scotty:** GROC-02 (derivation engine) and GROC-04 (API router) both clear to start. Backend slice can be parallelized. Target completion unlocks GROC-03, GROC-05, and frontend work.

---

## Event: Decision Inbox Consolidation

**File:** `.squad/decisions.md` (consolidated from inbox)

### Sulu GROC-01 Decision (Consolidated)

**Date:** 2026-03-08  
**Filename:** `.squad/decisions/consolidated/2026-03-08T20-00-00Z-sulu-groc01-schema-approved.md`

**Decision:** Use household-scoped grocery mutation receipt table + version-level incomplete-slot warning payloads as the Milestone 3 contract seam.

**Rationale:**
- Mutations require `client_mutation_id` for safe retries; generic receipt table keyed by `(household_id, client_mutation_id)` keeps replay safe without forcing line/list tables to become the replay store
- Incomplete ingredient data is a derivation-run outcome, not a line attribute; storing on `grocery_list_versions` keeps warning attached to exact plan+inventory snapshot

**Impact:**
- Scotty builds GROC-02/GROC-04 on mutation receipts as idempotency seam
- Uhura consumes version-level warning payload for list-level UI honesty
- McCoy verifies against new contract names: `confirmed_plan_version`, `required_quantity`, `offset_quantity`, `shopping_quantity`, `active`, `incomplete_slot_warnings`

**Status:** ✅ Consolidated into main decisions file

---

## Compliance Checklist

- ✅ GROC-01 completion recorded and verified (tests, validation)
- ✅ GROC-01 decision consolidated from inbox
- ✅ GROC-02/GROC-04 handoff to Scotty recorded
- ✅ Dependencies satisfied and blockers cleared
- ✅ Milestone 3 progress ledger updated with GROC-01 done
- ✅ Ready-now queue reflects GROC-02/GROC-04 activation
- ✅ Cross-team guidance captured (Scotty/Uhura/McCoy)
- ✅ Critical-path dependencies mapped (GROC-03, GROC-05, GROC-06/GROC-07 unblock chain)
- ✅ Scope boundaries reaffirmed (no Milestone 4/5 scope creep)

---

## Status Summary

**GROC-01:** ✅ **COMPLETE AND VERIFIED (2026-03-08T20-00-00Z)**

**GROC-02/GROC-04:** 🚀 **READY NOW FOR SCOTTY**

**Milestone 3 Execution Progress:**
- ✅ Spec and planning complete (from 2026-03-08T19-00-00Z)
- ✅ GROC-01 (schema foundation) complete
- 🚀 GROC-02/GROC-04 (backend derivation and router) active, zero blocking dependencies
- ⏳ GROC-03, GROC-05, GROC-06/GROC-07 queued for Scotty/McCoy/Uhura when GROC-02/GROC-04 unblocks
- ⏳ GROC-10/GROC-11 (frontend and final review) queued for final verification gate

**Ashley Hollis Directive Execution Status:**

Current: **Team, please build the full app and don't stop until it's complete and verified.**

Progress:
- ✅ Milestone 2 complete and verified (AIPLAN-01–AIPLAN-12, all 144 tests green)
- ✅ Milestone 3 planning complete and execution-ready
- ✅ GROC-01 foundation complete; schema and models locked
- 🚀 GROC-02/GROC-04 (backend) active and ready for Scotty
- ⏳ GROC-03, GROC-05, GROC-06/GROC-07, GROC-09, GROC-10, GROC-11 queued for parallel/sequential execution

**Next Orchestration:** Await Scotty completion of GROC-02/GROC-04; then McCoy gate (GROC-05) and Uhura frontend (GROC-06/GROC-07).
