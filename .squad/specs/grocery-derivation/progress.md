# Grocery Derivation Progress

Date: 2026-03-08
Status: 🚀 **MILESTONE 3 PLANNING ACTIVE**
Spec: `.squad/specs/grocery-derivation/feature-spec.md`
Tasks: `.squad/specs/grocery-derivation/tasks.md`

## 1. Current summary

- Milestone 1 is complete and approved; household-scoped authoritative inventory, idempotent mutation handling, audit history, and backend-owned session context are now trustworthy foundations for grocery work.
- Milestone 2 is complete and approved; confirmed weekly plans, stale-warning rules, per-slot provenance history, and the `plan_confirmed` handoff seam are now available for Milestone 3 consumption.
- Milestone 3 planning is now active. This run refreshed the grocery task plan into an execution-ready queue and opened a dedicated progress ledger for implementation tracking.
- GROC-01 is now complete. Grocery list/version/line persistence and schemas now carry the Milestone 3 lifecycle states, confirmation/idempotency seam, version traceability, incomplete-slot warning payloads, offset version references, and active/removed line fields needed before derivation/service work can start safely.
- No new user interview was required for honest task breakdown: the grocery MVP decisions are already resolved in the approved feature spec and mirrored in `.squad/decisions.md`.

## 2. Discovery and alignment status

- Ashley’s approved grocery decisions are already captured in:
  - `.squad/specs/grocery-derivation/feature-spec.md`
  - `.squad/project/constitution.md`
  - `.squad/project/prd.md`
  - `.squad/project/roadmap.md`
  - `.squad/decisions.md` (§Grocery Derivation MVP Rules)
- Milestone 2 completion and the planner→grocery handoff seam are confirmed in:
  - `.squad/specs/ai-plan-acceptance/progress.md`
  - `.squad/identity/now.md`
- The refreshed Milestone 3 task plan is aligned with the roadmap cut line: deliver trustworthy grocery derivation and review before the trip, while keeping full offline trip execution and shopping reconciliation explicitly in later milestones.

## 3. Ready-now queue

| ID | Task | Agent | Status | Notes |
| --- | --- | --- | --- | --- |
| GROC-00 | Keep Milestone 3 progress ledger current | Scribe | in_progress | Ledger is now active and should be updated on every transition, blocker, and verification result. |
| GROC-01 | Tighten grocery schema, lifecycle enums, and migration seams | Sulu | **done** | Completed 2026-03-08. Added household-backed grocery confirmation/idempotency seams, warning payload storage, version traceability fields, migration coverage, and updated model/schema regression tests. |
| GROC-02 | Implement derivation engine and authoritative persistence | Scotty | **pending** | GROC-01 now complete; derivation can build from confirmed plans plus authoritative inventory. Ready now. |
| GROC-03 | Implement refresh and stale-draft orchestration | Scotty | pending | Must preserve user adjustments/ad hoc lines and never mutate a confirmed list silently. Blocked by GROC-02. |
| GROC-04 | Implement grocery API router and mutation contracts | Scotty | **pending** | No active grocery router exists yet in `apps/api/app/main.py`; this is the core backend activation step. GROC-01 complete; ready now. |
| GROC-05 | Verify backend derivation and contract slice | McCoy | pending | Mandatory acceptance gate before frontend completion is treated as trustworthy. Blocked by GROC-02, GROC-04. |
| GROC-06 | Rewire the web grocery client to the real API contracts | Uhura | pending | Current `grocery-api.ts` and `GroceryView.tsx` still reflect pre-spec placeholder states and assumptions. Blocked by GROC-04 API activation. |
| GROC-07 | Complete grocery review and confirmation UX | Uhura | pending | Mobile-readable review/confirm flow is part of the milestone, not cleanup work. Blocked by GROC-04 API activation. |
| GROC-08 | Land confirmed-list handoff seams for trip mode and reconciliation | Scotty | pending | Must make list versions stable for downstream milestones without pulling those milestones forward. Blocked by GROC-07 confirmation. |
| GROC-09 | Add grocery observability and deterministic fixtures | Scotty | pending | Derivation and stale behavior need diagnosable evidence from the start. Blocked by GROC-04, GROC-05. |
| GROC-10 | Verify grocery UI and end-to-end flows | McCoy | pending | Required before Milestone 3 completion claim per the constitution and roadmap. Blocked by GROC-06, GROC-07 completion. |
| GROC-11 | Final Milestone 3 acceptance review | Kirk | pending | Final cut-line review must confirm Milestone 3 did not silently absorb Milestones 4 or 5. Blocked by GROC-10 completion. |

## 4. Blocked or cross-milestone queue

| ID | Task | Agent | Status | Blocked by | Notes |
| --- | --- | --- | --- | --- | --- |
| GROC-12 | Persist confirmed grocery list into the real offline client store | Uhura + Scotty | blocked | Milestone 4 offline-sync foundation | Milestone 3 must define the confirmed-list payload and version seam now, but the real offline store and replay engine belong to Milestone 4. |
| GROC-13 | Execute active trip flows against the confirmed grocery list with conflict review | Uhura + Scotty | blocked | Milestone 4 trip mode + conflict UX | Confirmed list stability is required now; active trip behavior is not. |
| GROC-14 | Convert confirmed grocery outcomes into authoritative inventory updates | Scotty + Sulu | blocked | Milestone 5 shopping reconciliation | Grocery derivation must preserve downstream traceability, but reconciliation remains a separate implementation milestone. |

## 5. Risks and watchpoints

- **Contract drift risk:** the current grocery frontend scaffold uses placeholder status names (`current`, `shopping`, `completed`) that do not match the approved lifecycle contract. Backend and frontend must be realigned before UI work continues.
- **Scope bleed risk:** it will be tempting to solve trip execution, offline queueing, or reconciliation inside grocery work. The roadmap explicitly forbids that cut-line blur.
- **Trust risk:** any derivation shortcut that applies fuzzy matching, cross-unit conversion, or silent override loss would violate constitution §§2.4 and 6.2.
- **Confirmed-list stability risk:** refresh behavior must distinguish draft refresh from confirmed-list immutability, especially now that planner handoff events are real.
- **Auth boundary risk:** grocery work must keep using API-owned session/bootstrap rules and must not reintroduce frontend-owned auth assumptions.

## 6. Current codebase watchpoints

- `apps/api/app/models/grocery.py` already has list/version/item tables, but the lifecycle and line fields still need to be tightened to the approved Milestone 3 contract.
- `apps/api/app/main.py` does **not** register a grocery router today; grocery remains an inactive slice even though planner and inventory are now active.
- `apps/api/app/services/planner_service.py` already emits `plan_confirmed` events. Milestone 3 should treat that as the authoritative trigger instead of deriving from draft planner state.
- `apps/web/app/_lib/grocery-api.ts` and `apps/web/app/grocery/_components/GroceryView.tsx` are valuable scaffolds, but they are not yet spec-aligned and should not be mistaken for completed Milestone 3 behavior.

## 7. Baseline evidence for this planning refresh

Repo validation was re-run for this planning update using the existing repository checks:
- `npm run lint:web`
- `npm run typecheck:web`
- `npm run build:web`
- `npm run test:api`
- `npm run test:worker`

Result: all five commands passed for this planning refresh. Web lint, typecheck, and build are green; API tests passed; worker tests passed (9/9). This planning-only update does not change application code paths.

## 8. GROC-01 completion evidence

- Updated `apps/api/app/models/grocery.py` to enforce the approved grocery lifecycle/status contract at the schema layer, add confirmation mutation tracking, persist incomplete-slot warning payloads on list versions, track offset inventory versions, and introduce household-scoped grocery mutation receipts for idempotent list mutations.
- Updated `apps/api/app/schemas/grocery.py` to expose contract-aligned version/line fields, parsed meal traceability and incomplete-slot warnings, and an ad hoc create command that accepts the Milestone 3 shopping-quantity contract while remaining backward-compatible with the legacy quantity field name.
- Added reversible migration seam `apps/api/migrations/versions/rev_20260308_04_groc01_grocery_schema_seams.py` plus regression coverage in `apps/api/tests/test_groc01_migration.py`.
- Expanded grocery model/schema tests so the contract is now guarded by automated coverage for warning payloads, active/removed line state, offset reference metadata, list-version uniqueness, and household-scoped mutation receipts.
- Validation after implementation:
  - `cd apps\\api && python -m pytest tests`
  - `cd apps\\api && python -m compileall app tests migrations`
  - `npm run lint:web`
  - `npm run typecheck:web`
  - `npm run build:web`
  - `npm run test:worker`
- Result: all six commands passed. API test suite passed (151 tests); API compileall passed; web lint/typecheck/build passed; worker tests passed (9/9).

## 9. Planning exit criteria met

- `tasks.md` has been refreshed into an execution-ready Milestone 3 queue with dependencies, verification gates, and blocked cross-milestone follow-ons.
- `progress.md` now exists for Milestone 3 tracking.
- The Milestone 2 completion state and planner→grocery handoff are now treated as resolved prerequisites instead of open questions.
- The session plan has been refreshed to show Milestone 2 complete and Milestone 3 planning active.
