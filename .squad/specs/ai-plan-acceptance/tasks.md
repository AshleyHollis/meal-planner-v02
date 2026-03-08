# AI Plan Acceptance — Implementation Tasks

Date: 2026-03-08
Milestone: 2 (Weekly planner and explainable AI suggestions)
Status: Execution-ready planning refresh
Spec: `.squad/specs/ai-plan-acceptance/feature-spec.md`

This task plan translates the approved Milestone 2 feature decisions into an implementation queue that is grounded in the current codebase. It is aligned with the constitution, PRD, roadmap, AI architecture, and the now-complete Milestone 1 inventory foundation.

## 1. Planning cut line

### Milestone 2 outcome
Deliver an authoritative weekly planner flow where a household can:
- request an async AI suggestion,
- review and edit a draft,
- regenerate a single slot,
- confirm the final plan explicitly,
- preserve per-slot AI origin history for audit/support,
- keep grocery derivation gated on confirmed plan state only.

### Locked implementation rules
- **Backend-owned auth/session only:** planner work must keep using API-owned session bootstrap via `GET /api/v1/me`; no Auth0 SDK or Auth0 runtime config may be added to `apps/web`.
- **AI is advisory only:** AI results populate suggestion and draft state, never authoritative meal-plan, grocery, or inventory state without explicit confirmation.
- **Confirmed plan protection is unconditional:** new suggestions and new drafts never overwrite an existing confirmed plan for the same household + period.
- **SQL-backed trust data:** build on the existing SQL-backed household and inventory foundation from Milestone 1; do not reintroduce client-owned authority or in-memory planner trust state.
- **Roadmap-aware dependency honesty:** full offline replay/conflict handling still depends on the Milestone 4 sync foundation. Milestone 2 implementation must preserve the contract and honest UX states without inventing unsafe sync shortcuts.

## 2. Current codebase starting point

- `apps/api/app/models/meal_plan.py` and `apps/api/app/models/ai_planning.py` already contain substantial planner and AI persistence primitives.
- `apps/web/app/_lib/planner-api.ts` and `apps/web/app/planner/_components/*` already model the intended frontend flow, but depend on backend endpoints that do not exist yet.
- `apps/worker/app/main.py` is still a scaffold; the AI worker lifecycle, grounding, provider integration, validation, and fallback behavior are not implemented.
- Grocery models exist, but Milestone 3 derivation logic is not complete, so Milestone 2 should emit and test the handoff contract rather than absorb full grocery derivation scope.

## 3. Ready-now implementation queue

| ID | Task | Agent | Depends on | Parallel | Notes |
| --- | --- | --- | --- | --- | --- |
| AIPLAN-00 | Keep Milestone 2 progress ledger current | Scribe | — | [P] | Update `progress.md` at every task transition, blocker, and verification result. |
| AIPLAN-01 | Tighten planner SQL model and migration seams | Sulu | INF-11 |  | Finalize active-draft uniqueness per household + period, regen linkage fields, confirmation idempotency fields, and slot-origin history completeness. Honor constitution 2.4, 5.4. |
| AIPLAN-02 | Implement planner service and API router | Scotty | AIPLAN-01 |  | Add household-scoped suggestion, draft, slot edit/revert, slot regen request, confirm, and confirmed-plan reads using backend-owned session context. No client-owned authoritative household scope. |
| AIPLAN-03 | Implement AI request lifecycle contracts in the API | Scotty | AIPLAN-01 | [P] | Persist request state, request dedupe/idempotency, request/result polling shapes, slot-scoped regen requests, and status transitions defined by `ai-architecture.md`. |
| AIPLAN-04 | Implement worker grounding, prompt building, validation, and fallback | Sulu | AIPLAN-03 |  | Build the worker-backed generation path: queue consume, authoritative grounding, structured output validation, tiered fallback, and single-slot regeneration support. |
| AIPLAN-05 | Implement stale detection, confirmation flow, and history writes | Scotty | AIPLAN-02, AIPLAN-04 |  | Add stale-warning triggers, stale acknowledgment enforcement, confirmed-plan protection, per-slot provenance history, and `plan_confirmed` event emission. |
| AIPLAN-06 | Verify backend and worker contract slice | McCoy | AIPLAN-02, AIPLAN-04, AIPLAN-05 | [VERIFY] | Add and run API/worker tests for draft creation, slot edit/revert, regen lifecycle, stale detection, confirmation idempotency, provenance writes, and failure/fallback paths. |
| AIPLAN-07 | Wire the web planner client to real planner endpoints | Uhura | AIPLAN-02, AIPLAN-03 |  | Replace placeholder/mock assumptions in `planner-api.ts` and the planner page flow with the real backend contract and session-owned household context. |
| AIPLAN-08 | Complete planner review, draft, regen, and confirmation UX | Uhura | AIPLAN-05, AIPLAN-07 |  | Finish the user journey for review/edit/confirm, including stale warning visibility, per-slot failure recovery, confirmed-plan view without AI badges, and clear AI fallback messaging. |
| AIPLAN-09 | Emit and contract-test the grocery handoff seam | Scotty | AIPLAN-05 | [P] | Ensure only confirmed plans emit the grocery refresh trigger and prove draft/suggestion states never feed grocery derivation. Full derivation remains Milestone 3 scope. |
| AIPLAN-10 | Add planner observability and deterministic fixtures | Scotty | AIPLAN-04, AIPLAN-05 | [P] | Log request/draft/regen/confirm lifecycle with correlation IDs and add deterministic AI fixtures for happy path, stale, fallback, and failure coverage. |
| AIPLAN-11 | Verify planner UI and E2E journeys | McCoy | AIPLAN-08, AIPLAN-09, AIPLAN-10 | [VERIFY] | Add E2E coverage for request→review→edit→confirm, stale-warning acknowledgment, per-slot regen, confirmed-plan protection, and visible failure/manual fallback paths. |
| AIPLAN-12 | Final Milestone 2 acceptance review | Kirk | AIPLAN-06, AIPLAN-11 | [VERIFY] | Review implementation against the feature spec acceptance criteria, constitution rules, and roadmap cut line before the team claims Milestone 2 complete. |

## 4. Blocked or cross-milestone follow-on work

These items must stay visible because the feature spec references them, but they depend on broader milestone work and should not be hidden inside Milestone 2 execution status.

| ID | Task | Agent | Blocked by | Why it stays tracked |
| --- | --- | --- | --- | --- |
| AIPLAN-13 | Thread planner mutations through the offline sync queue and conflict review flow | Uhura + Scotty | Milestone 4 sync foundation (`.squad/specs/offline-sync-conflicts/feature-spec.md`) | The planner spec requires offline-aware draft behavior, but the roadmap intentionally sequences full replay/conflict handling into Milestone 4. Milestone 2 must keep honest “requires connection” states and preserve seams instead of inventing unsafe offline writes. |
| AIPLAN-14 | Complete grocery derivation consumption of confirmed plans | Scotty + Sulu | Milestone 3 grocery implementation | Milestone 2 must emit and prove the confirmed-plan handoff contract, but the actual derived grocery-list engine is still a separate milestone. |

## 5. Execution notes for downstream implementers

- Prefer building the backend/worker contract before changing the planner UI further; the frontend scaffolding already exists and should conform to the final API instead of freezing a mock contract.
- Reuse the Milestone 1 trust patterns: household-scoped authorization, SQL-backed idempotency, append-only audit records, and explicit conflict/error surfaces.
- Keep AI-specific version fields (`prompt_family`, `prompt_version`, `policy_version`, `context_contract_version`, `result_contract_version`) in request/result persistence from the start; do not defer them to “later telemetry cleanup.”
- Treat per-slot regeneration as the same AI lifecycle with narrower scope, not a special-case synchronous endpoint.
- Verification is part of delivery. Do not advance past AIPLAN-06 or AIPLAN-11 with only manual spot checks.

## 6. Suggested implementation order

1. **Backend/data spine:** AIPLAN-01 → AIPLAN-02 + AIPLAN-03.
2. **AI execution spine:** AIPLAN-04 → AIPLAN-05.
3. **Proof of correctness:** AIPLAN-06.
4. **Frontend wiring and UX completion:** AIPLAN-07 → AIPLAN-08.
5. **Cross-feature seam hardening:** AIPLAN-09 + AIPLAN-10.
6. **Acceptance evidence:** AIPLAN-11 → AIPLAN-12.

This sequence keeps the authoritative planner contract, explainable AI behavior, and acceptance evidence ahead of milestone-claim language.
