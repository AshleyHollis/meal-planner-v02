# AIPLAN-05 Completion and AIPLAN-06 / AIPLAN-08 Launch
**Date:** 2026-03-08T15:00:00Z  
**Recorded by:** Scribe  
**Authorization:** Ashley Hollis (Team, please build the full app and don't stop until it's complete and verified.)

## Status Summary

### AIPLAN-05 Completion: Stale Detection, Confirmation Flow, and History Writes
**Owner:** Scotty  
**Status:** ✅ DONE (2026-03-08)

**Completion Evidence:**
- **Stale-warning triggers:** `apps/api/app/services/planner_service.py` now compares completed suggestion requests against the worker grounding hash contract so inventory/context changes surface `stale` suggestions and `stale_warning` drafts on read/confirm.
- **Confirmed-plan protection:** confirmation now advances the new authoritative version for the same household+period without mutating prior confirmed rows; new suggestions/drafts leave the previously confirmed plan untouched until the next explicit confirmation.
- **Confirmation writes:** confirming a draft writes `meal_plan_slot_history` per slot and a durable `planner_events` row with `event_type = plan_confirmed` plus the confirmation payload needed for downstream grocery derivation work.
- **Schema + migration:** `apps/api/app/models/planner_event.py`, `apps/api/app/schemas/planner.py`, and `apps/api/migrations/versions/rev_20260308_03_aiplan05_planner_events.py` add the event persistence contract and reversible migration seam.
- **Regression coverage:** `apps/api/tests/test_planner.py`, `apps/api/tests/test_aiplan05_migration.py`, `apps/api/tests/schemas/test_planner_schemas.py`, and `apps/worker/tests/test_generation_worker.py` prove stale triggering from grounding changes, confirmed-plan protection, one-time history/event writes, migration round-trip behavior, event payload shape, and worker non-reuse when grounding changes.

**Verification Run:**
```
cd apps\api && python -m pytest tests\test_planner.py tests\test_aiplan05_migration.py tests\schemas\test_planner_schemas.py
cd apps\worker && python -m pytest tests\test_generation_worker.py
cd apps\api && python -m pytest tests
cd apps\worker && python -m pytest tests
cd apps\api && python -m compileall app tests migrations
cd apps\worker && python -m compileall app worker_runtime tests
```
Result: **All green** ✅

**Unblocks:**
- **AIPLAN-06 (McCoy):** First formal acceptance gate for backend/worker portion; can now proceed as a mandatory verification gate.
- **AIPLAN-09 (Scotty):** Emit and contract-test the grocery handoff seam.
- **AIPLAN-10 (Scotty):** Add planner observability and deterministic fixtures.

---

## AIPLAN-06 Launch: Verify Backend and Worker Contract Slice
**Owner:** McCoy  
**Status:** 🟡 LAUNCHED (2026-03-08T15:00:00Z)  
**Dependencies:** ✅ All satisfied
- AIPLAN-01 (Planner SQL model) ✅ done
- AIPLAN-02/03 (Planner service/API router) ✅ done
- AIPLAN-04 (Worker grounding/prompt/validation/fallback) ✅ done
- AIPLAN-05 (Stale detection/confirmation/history) ✅ done

**Scope:** First formal acceptance gate for the backend/worker portion. Verify that:
1. Planner SQL schema enforces household-scoped idempotency, one-active-draft per period, and proper lineage fields.
2. Worker execution path is authoritative and deterministic: grounding hash, prompt assembly, structured validation, tiered fallback.
3. API request/result lifecycle contracts are stable: request polling, household-scoped idempotency, active-request dedupe, status transitions.
4. Stale detection, confirmation flow, and history writes are solid: grounding drift triggers stale warnings, confirmation protects and appends to history, events are durable.
5. End-to-end integration: request → worker → draft → confirm → event emission.

**Verification Gates (must pass before AIPLAN-06 closure):**
- Unit tests for AIPLAN-01, 02, 03, 04, 05 all green (deterministic, repeatable).
- Integration tests proving request-to-confirmed-plan flow across multiple households.
- Fallback mode visibility and tiered fallback behavior under stale/missing data conditions.
- History/event append-only correctness and no confirmed-plan overwrites on new suggestion.

---

## AIPLAN-08 Launch: Complete Planner Review, Draft, Regen, and Confirmation UX
**Owner:** Uhura  
**Status:** 🟡 LAUNCHED (2026-03-08T15:00:00Z)  
**Dependencies:** ✅ All satisfied
- AIPLAN-04 (Worker implementation) ✅ done
- AIPLAN-07 (Wire web planner client to real endpoints) ✅ done

**Scope:** Complete the planner UI layer with stale-warning UX, regen failure recovery, fallback messaging, and confirmed-plan presentation. Builds on real backend contract and real worker execution now in place.

**Tasks:**
1. Render stale-warning UI when `stale_warning` is true on draft read.
2. Handle regen request failures gracefully: show fallback mode visibility, explain why suggestion fell back to curated/manual guidance.
3. Display confirmed-plan snapshot for review before accepting new suggestions for the same period.
4. Show reason codes and explanation text from worker output on each meal slot.
5. Update draft slot UI to show pending regen requests and refresh on completion.

**Verification Gates (must pass before AIPLAN-08 closure):**
- `npm run lint:web` passes (style/lint compliance).
- `npm run typecheck:web` passes (TypeScript strict mode).
- `npm run build:web` passes (production build clean).
- `npm --prefix apps\web run test` passes (planner component unit tests).
- Planner UX renders stale warnings, fallback modes, and confirmed-plan snapshots correctly against backend responses.

---

## Parallel Execution Status

| Task | Owner | Status | Notes |
| --- | --- | --- | --- |
| AIPLAN-06 | McCoy | 🟡 in_progress | Backend/worker verification gate launched; all dependencies satisfied. |
| AIPLAN-08 | Uhura | 🟡 in_progress | Planner UX completion launched; real backend contract now stable. |
| AIPLAN-09 | Scotty | 🟡 pending | Emit and contract-test grocery handoff seam; blocked until AIPLAN-05 complete. Now unblocked. |
| AIPLAN-10 | Scotty | 🟡 pending | Observability and deterministic fixtures; blocked until AIPLAN-05 complete. Now unblocked. |
| AIPLAN-11 | McCoy | 🟡 pending | E2E verification; blocked until AIPLAN-08 complete. |
| AIPLAN-12 | Kirk | 🟡 pending | Final Milestone 2 acceptance review; blocked until AIPLAN-06, AIPLAN-11 complete. |

**Next Checkpoints:**
- McCoy completes AIPLAN-06 verification gate → unblocks AIPLAN-11 (McCoy, E2E verification).
- Uhura completes AIPLAN-08 UX → unblocks AIPLAN-11 (McCoy, E2E verification).
- Scotty completes AIPLAN-09 grocery handoff seam and AIPLAN-10 observability in parallel.
- McCoy completes AIPLAN-11 E2E verification → unblocks AIPLAN-12 (Kirk, final acceptance).
- Kirk completes AIPLAN-12 final acceptance review → Milestone 2 complete and approved.

---

## Decision Summary

### No decision inbox items pending
All prior inbox decisions merged into `.squad/decisions.md`. No new decisions blocking AIPLAN-06 or AIPLAN-08 launch.

---

## Milestone 2 Readiness Checkpoint

**Completed Foundation:**
- ✅ AIPLAN-01: Planner SQL model, household-scoped idempotency, lineage fields
- ✅ AIPLAN-02: Planner service and API router
- ✅ AIPLAN-03: AI request lifecycle contracts
- ✅ AIPLAN-04: Worker grounding, prompt, validation, fallback
- ✅ AIPLAN-05: Stale detection, confirmation, history writes
- ✅ AIPLAN-07: Web planner client wired to real endpoints

**Ready-Now Work:**
- 🟡 AIPLAN-06: Verification gate (McCoy)
- 🟡 AIPLAN-08: Planner UX (Uhura)
- 🟡 AIPLAN-09: Grocery handoff seam (Scotty) — now unblocked
- 🟡 AIPLAN-10: Observability (Scotty) — now unblocked
- 🟡 AIPLAN-11: E2E verification (McCoy) — depends on AIPLAN-06, AIPLAN-08
- 🟡 AIPLAN-12: Final acceptance (Kirk) — depends on AIPLAN-06, AIPLAN-11

**Cross-Milestone Dependencies (Intentional, roadmap-tracked):**
- AIPLAN-13: Offline sync queueing/conflict review → Milestone 4 sync foundations
- AIPLAN-14: Grocery derivation consumption → Milestone 3 grocery implementation

---

## Next Recommended Actions

1. **Scotty** starts AIPLAN-09 (grocery handoff seam) immediately.
2. **Scotty** starts AIPLAN-10 (observability) immediately (parallelizable with AIPLAN-09).
3. **McCoy** proceeds with AIPLAN-06 verification gate; all prerequisites in place.
4. **Uhura** proceeds with AIPLAN-08 planner UX; real backend contract stable.
5. **McCoy** will start AIPLAN-11 (E2E verification) once both AIPLAN-06 and AIPLAN-08 complete.
6. **Kirk** will conduct AIPLAN-12 (final acceptance) once AIPLAN-06 and AIPLAN-11 complete.

No blocking decisions or configuration changes required. Full app build executable with current state.
