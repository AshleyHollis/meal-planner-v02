# AI Plan Acceptance Progress

Date: 2026-03-08
Status: 🟡 **PLANNING COMPLETE — MILESTONE 2 EXECUTION QUEUE READY**
Spec: `.squad/specs/ai-plan-acceptance/feature-spec.md`
Tasks: `.squad/specs/ai-plan-acceptance/tasks.md`

## 1. Current summary

- Milestone 1 is complete and approved; household-scoped inventory, idempotent mutation handling, audit history, and backend-owned session context are now trustworthy foundations for planner work.
- Milestone 2 planning has been refreshed into an execution-ready task queue for weekly planner + explainable AI suggestions.
- The repo already contains meaningful planner/AI models and frontend scaffolding, but the planner API/router, worker execution path, stale detection, confirmation lifecycle, and grocery handoff are not implemented yet.

## 2. Discovery and alignment status

- Ashley’s approved Milestone 2 decisions are already captured in:
  - `.squad/specs/ai-plan-acceptance/feature-spec.md`
  - `.squad/project/architecture/ai-architecture.md`
  - `.squad/decisions.md` (§AI Planning Decisions, §AI Technical Architecture, §AI Plan Acceptance Decisions)
- This run did not have an interactive `ask_user` channel available, so no new discovery round was possible here. The planning refresh therefore used the existing approved Ashley decisions as the authoritative discovery baseline instead of inventing new scope.
- The refreshed task plan is aligned with the constitution, PRD, roadmap, AI architecture, and the Milestone 1 completion record in `.squad/specs/inventory-foundation/progress.md`.

## 3. Ready-now queue

| ID | Task | Agent | Status | Notes |
| --- | --- | --- | --- | --- |
| AIPLAN-00 | Keep Milestone 2 progress ledger current | Scribe | in_progress | This ledger is now active and should be updated on every task transition. |
| AIPLAN-01 | Tighten planner SQL model and migration seams | Sulu | done | Completed 2026-03-08. Planner drafts now enforce one active draft per household + period, AI request idempotency is household-scoped, regen linkage fields/migration seams landed, and planner lineage/history tests are green. |
| AIPLAN-02 | Implement planner service and API router | Scotty | pending | Backend-owned household context from `GET /api/v1/me` remains mandatory. |
| AIPLAN-03 | Implement AI request lifecycle contracts in the API | Scotty | pending | Ready to run in parallel with AIPLAN-02 once AIPLAN-01 lands. |
| AIPLAN-04 | Implement worker grounding, prompt building, validation, and fallback | Sulu | pending | Worker is currently scaffold-only, so this is a major Milestone 2 unlock. |
| AIPLAN-05 | Implement stale detection, confirmation flow, and history writes | Scotty | pending | Must preserve confirmed-plan protection and append-only provenance history. |
| AIPLAN-06 | Verify backend and worker contract slice | McCoy | pending | First formal acceptance gate for the backend/worker portion. |
| AIPLAN-07 | Wire the web planner client to real planner endpoints | Uhura | pending | Frontend scaffolding exists; it needs the real API contract, not more mock behavior. |
| AIPLAN-08 | Complete planner review, draft, regen, and confirmation UX | Uhura | pending | Includes stale-warning UX, regen failure recovery, fallback messaging, and confirmed-plan presentation. |
| AIPLAN-09 | Emit and contract-test the grocery handoff seam | Scotty | pending | Milestone 2 must prove the trigger contract while keeping full derivation in Milestone 3. |
| AIPLAN-10 | Add planner observability and deterministic fixtures | Scotty | pending | Required for diagnosable AI runs and deterministic verification. |
| AIPLAN-11 | Verify planner UI and E2E journeys | McCoy | pending | Required before any Milestone 2 completion claim. |
| AIPLAN-12 | Final Milestone 2 acceptance review | Kirk | pending | Final spec/constitution/roadmap check. |

## 4. Blocked or cross-milestone queue

| ID | Task | Agent | Status | Blocked by | Notes |
| --- | --- | --- | --- | --- | --- |
| AIPLAN-13 | Thread planner mutations through the offline sync queue and conflict review flow | Uhura + Scotty | blocked | Milestone 4 sync foundation | Feature-spec expectations are real, but the roadmap intentionally sequences full replay/conflict handling later. Do not hide this gap. |
| AIPLAN-14 | Complete grocery derivation consumption of confirmed plans | Scotty + Sulu | blocked | Milestone 3 grocery implementation | Milestone 2 must emit the confirmed-plan seam cleanly, not absorb the whole grocery engine. |

## 5. Risks and watchpoints

- **Offline scope tension:** the feature spec describes offline-aware planner behavior, while the roadmap defers full sync/conflict machinery to Milestone 4. This is tracked explicitly rather than silently collapsed into Milestone 2.
- **Authoritative-state boundary risk:** planner drafts, AI suggestions, and confirmed plans must remain distinct in storage, API shape, and UI. Any shortcut that lets AI results act like confirmed plans is a defect against constitution 2.4 and 2.5.
- **Confirmed-plan overwrite risk:** requesting a new suggestion while a plan already exists for the same period must never mutate the confirmed plan until explicit user confirmation.
- **AI ops risk:** prompt/result versioning, fallback mode visibility, and correlation IDs need to ship with the first real worker slice, not as post-hoc instrumentation.
- **Auth boundary risk:** the backend-only Auth0 rule remains locked. Planner work must continue using API-owned session bootstrap and must not add frontend Auth0 packages or config.

## 6. Baseline evidence for starting implementation

Latest approved repo evidence, inherited from the Milestone 1 completion ledger:
- `npm run lint:web`
- `npm run typecheck:web`
- `npm run build:web`
- `npm --prefix apps\web run test`
- `python -m pytest apps\api\tests`

Result: latest Milestone 1 validation was green, so Milestone 2 work starts from a verified household/inventory baseline rather than from placeholders.

## 7. Planning exit criteria met

- `tasks.md` has been refreshed into an implementation-ready queue with dependencies, parallelism, blocked work, and verification gates.
- `progress.md` now exists for Milestone 2 execution tracking.
- Current planning artifacts explicitly call out the two cross-milestone dependencies that must remain visible: planner offline sync and grocery derivation completion.

## 8. AIPLAN-01 completion evidence

- **Planner SQL seams tightened:** `apps/api/app/models/meal_plan.py` now enforces one active draft per household + period via an indexed draft-only uniqueness seam, adds plan/result linkage at the plan level, and carries slot-level lineage + regen fields (`slot_key`, summary, AI request/result IDs, explanations, fallback flag, regen status, pending regen request ID).
- **AI request/result seams tightened:** `apps/api/app/models/ai_planning.py` now scopes request idempotency by household, links regen requests back to the parent draft + slot, and gives AI result slots stable `slot_key` + summary storage needed for Milestone 2 review/regeneration flow.
- **Schema + migration coverage added:** planner/AI schema reads now expose the new lineage/regen fields, and `apps/api/migrations/versions/rev_20260308_01_aiplan01_planner_seams.py` provides an explicit reversible migration for the planner seam changes.
- **Verification evidence:** 
  - `python -m pytest tests\models\test_meal_plan_models.py tests\models\test_ai_planning_models.py tests\schemas\test_meal_plan_schemas.py tests\schemas\test_ai_planning_schemas.py tests\test_aiplan01_migration.py`
  - `python -m pytest tests`
  - `python -m compileall app tests migrations`

## 9. Next handoff

Recommended start order:
1. AIPLAN-02 and AIPLAN-03 in parallel now that AIPLAN-01 is landed
2. AIPLAN-04 once Scotty has the finalized router/service seam in flight
3. AIPLAN-05 after the router and worker seams are both in place
4. AIPLAN-06 before widening frontend work

If Ashley wants full queued offline planner editing/confirmation inside Milestone 2 rather than Milestone 4, that needs an explicit scope decision before the team can honestly claim this milestone complete.
