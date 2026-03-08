# AI Plan Acceptance Progress

Date: 2026-03-08
Status: 🟢 **MILESTONE 2 APPROVED**
Spec: `.squad/specs/ai-plan-acceptance/feature-spec.md`
Tasks: `.squad/specs/ai-plan-acceptance/tasks.md`

## 1. Current summary

- Milestone 1 is complete and approved; household-scoped inventory, idempotent mutation handling, audit history, and backend-owned session context are now trustworthy foundations for planner work.
- Milestone 2 execution is now underway with planner API lifecycle contracts, real worker-backed AI generation, and completed planner review/edit/confirm UX all landed on top of the Milestone 1 data foundation.
- The backend/worker contract slice has now cleared its first formal acceptance gate: AIPLAN-06 is approved with added regression coverage for pending regen state, slot provenance refresh, stale-confirm provenance persistence, and worker fallback metadata writes.
- The backend/worker contract gate (AIPLAN-06) and the planner UI/E2E gate (AIPLAN-11) are now both approved; Milestone 2 is down to the final Kirk acceptance review plus stabilization of a shared-workspace Next.js build issue outside the planner-specific test paths.

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
| AIPLAN-02 | Implement planner service and API router | Scotty | done | Completed 2026-03-08. Household-scoped planner router/service landed for suggestion reads, draft open/read, slot edit/revert, slot regeneration requests, confirmation, and confirmed-plan reads with backend-owned session enforcement. |
| AIPLAN-03 | Implement AI request lifecycle contracts in the API | Scotty | done | Completed 2026-03-08. Request/result polling, household-scoped request idempotency, active-request dedupe, request status transitions, stale-warning inheritance, and confirmation idempotency are now covered by API tests. |
| AIPLAN-04 | Implement worker grounding, prompt building, validation, and fallback | Sulu | done | Completed 2026-03-08. Worker runtime now owns authoritative grounding, prompt bundle assembly, structured result validation, tiered fallback, equivalent-result reuse, and single-slot regeneration behavior with deterministic API/worker tests. |
| AIPLAN-05 | Implement stale detection, confirmation flow, and history writes | Scotty | done | Completed 2026-03-08. Draft stale warnings now trigger from grounding changes, confirmation writes durable per-slot history plus `plan_confirmed` planner events, and confirmed plans stay protected while new drafts are reviewed. |
| AIPLAN-06 | Verify backend and worker contract slice | McCoy | done | Completed 2026-03-08. Approved after adding regression coverage for regen pending→complete provenance, stale-confirm audit persistence, and worker fallback/regen metadata. |
| AIPLAN-07 | Wire the web planner client to real planner endpoints | Uhura | done | Completed 2026-03-08. Planner web client now uses active-household session context, real draft slot edit/revert endpoints, request lifecycle polling, and backend-owned draft replacement instead of local placeholder planner state. |
| AIPLAN-08 | Complete planner review, draft, regen, and confirmation UX | Uhura | done | Completed 2026-03-08. Planner review now keeps confirmed and draft states visibly separate, surfaces stale warnings on the confirmation path, shows per-slot regen recovery/fallback messaging, and suppresses AI provenance in confirmed-plan presentation. |
| AIPLAN-09 | Emit and contract-test the grocery handoff seam | Scotty | done | Completed 2026-03-08. Confirmed-plan events now carry an explicit grocery refresh trigger payload, and API regression coverage proves suggestion/draft states emit no grocery handoff signal. |
| AIPLAN-10 | Add planner observability and deterministic fixtures | Scotty | done | Completed 2026-03-08. Planner API + worker lifecycle logs now carry correlation IDs, and deterministic fixtures cover happy path, stale, fallback, and failure outcomes. |
| AIPLAN-11 | Verify planner UI and E2E journeys | McCoy | done | Completed 2026-03-08. Added planner Playwright acceptance coverage for request→review→edit→confirm, stale-warning acknowledgment, per-slot regeneration, confirmed-plan protection, and visible fallback/failure paths; approved with evidence below. |
| AIPLAN-12 | Final Milestone 2 acceptance review | Kirk | done | Completed 2026-03-08. APPROVED — all 14 acceptance criteria verified independently, full evidence suite green (144 API + 9 worker + 26 web tests, lint/typecheck/build clean), constitution alignment confirmed. See §18 for full verdict. |

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
- **Acceptance status:** AIPLAN-06 and AIPLAN-11 are now approved, so Milestone 2 is down to Kirk’s final cut-line review plus the visible shared-workspace web-build stabilization issue noted in the AIPLAN-11 evidence.

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

Recommended next acceptance order:
1. AIPLAN-12 for final Milestone 2 acceptance review

If Ashley wants full queued offline planner editing/confirmation inside Milestone 2 rather than Milestone 4, that still needs an explicit scope decision before the team can honestly claim this milestone complete.

## 10. AIPLAN-02 and AIPLAN-03 completion evidence

- **Planner router/service landed:** `apps/api/app/routers/planner.py` and `apps/api/app/services/planner_service.py` now expose backend-owned household-scoped planner endpoints for:
  - `POST/GET /api/v1/households/{household_id}/plans/suggestion`
  - `GET /api/v1/households/{household_id}/plans/requests/{request_id}`
  - `POST/GET /api/v1/households/{household_id}/plans/draft`
  - `PATCH /api/v1/households/{household_id}/plans/draft/{draft_id}/slots/{slot_id}`
  - `POST /api/v1/households/{household_id}/plans/draft/{draft_id}/slots/{slot_id}/revert`
  - `POST /api/v1/households/{household_id}/plans/draft/{draft_id}/slots/{slot_id}/regenerate`
  - `POST /api/v1/households/{household_id}/plans/draft/{draft_id}/confirm`
  - `GET /api/v1/households/{household_id}/plans/confirmed`
- **Distinct planner states preserved:** AI request/result rows remain separate from editable draft rows and confirmed plan rows. Draft slot revert uses the stored AI result lineage (`ai_suggestion_result_id` + `slot_key`) instead of collapsing draft state back into the suggestion table.
- **Lifecycle contracts covered:** request idempotency is household-scoped, active request dedupe is scoped by household + period + slot scope, status transitions flow through `queued` → `generating` → `completed`, stale suggestions propagate to draft warnings, and confirmation is idempotent through `confirmation_client_mutation_id`.
- **Frontend contract seam refreshed:** `apps/web/app/_lib/planner-api.ts` now understands backend-supplied `original_suggestion` snapshots and polls the canonical request endpoint when a suggestion request is still generating.
- **Verification evidence:**
  - `python -m pytest apps\api\tests`
  - `npm run typecheck:web`
  - `npm run build:web`

## 11. AIPLAN-07 completion evidence

- **Planner household scope now comes from the backend session contract:** `apps/web/app/planner/_components/PlannerView.tsx` now uses `user.activeHouseholdId` for suggestion, draft, regeneration, and confirmation calls instead of relying on the compatibility alias or client-owned household assumptions.
- **Placeholder planner authority removed:** the planner page no longer fabricates local drafts or local-only slot changes. Opening a suggestion-backed draft now uses Scotty's `replaceExisting` contract, and slot edits/restores call the real draft slot PATCH/POST endpoints in `apps/web/app/_lib/planner-api.ts`.
- **Request lifecycle wiring is real end-to-end:** suggestion and slot-regeneration flows now poll the canonical planner request endpoint, preserve stale-ready results, and refresh the draft from backend state after regeneration.
- **Frontend regression coverage added:** `apps/web/app/_lib/planner-api.test.ts` now proves request polling, replace-existing draft open, slot edit/revert mapping, regen request wiring, and stale-result normalization against the backend contract.
- **Verification evidence:**
  - `npm run lint:web`
  - `npm run typecheck:web`
  - `npm run build:web`
  - `npm --prefix apps\web run test`

## 12. AIPLAN-04 completion evidence

- **Worker execution path is now real and authoritative:** `apps/worker/worker_runtime/runtime.py` now processes queued planner requests against SQL-backed household state instead of the old scaffold-only deterministic materializers. The worker assembles grounding from authoritative household/inventory/confirmed-plan data, computes a normalized grounding hash, versions prompt/policy/context/result contracts, and updates canonical request/result rows used by Scotty’s request polling endpoints.
- **Prompt + validation spine landed in code:** the worker now builds explicit system/task/context/schema prompt layers, validates provider output through app-owned structured contracts, and persists normalized slot payloads with reason codes, explanation text, `uses_on_hand`, `missing_hints`, and visible fallback modes.
- **Tiered fallback behavior is implemented:** the runtime first reuses fresh equivalent results by grounding hash, then drops to curated deterministic meal-template fallback, then returns visible `manual_guidance` when no safe curated fallback exists. Single-slot regeneration keeps sibling draft slots untouched and preserves the user’s previous slot choice if regen can only return manual guidance.
- **Fallback provenance is now explicit instead of boolean-only:** planner persistence now stores `fallback_mode` as a string contract (`none`, `curated_fallback`, `manual_guidance`) across AI results, draft slots, and confirmation history, and `apps/api/migrations/versions/rev_20260308_02_aiplan04_fallback_modes.py` makes that seam reversible.
- **Verification evidence:**
  - `cd apps\api && python -m pytest tests`
  - `cd apps\api && python -m compileall app tests migrations`
  - `cd apps\worker && python -m pytest tests`
  - `cd apps\worker && python -m compileall app worker_runtime tests`

## 13. AIPLAN-05 completion evidence

- **Stale-warning triggers now use live grounding drift instead of only manual status flips:** `apps/api/app/services/planner_service.py` now compares completed suggestion requests against the worker grounding hash contract so inventory/context changes surface `stale` suggestions and `stale_warning` drafts on read/confirm without collapsing request, draft, and confirmed states together.
- **Confirmed-plan protection remains explicit while new drafts stay separate:** confirmation now advances the new authoritative version for the same household+period without mutating prior confirmed rows, and new suggestions/drafts leave the previously confirmed plan untouched until the next explicit confirmation.
- **Confirmation writes remain append-only and now include the handoff seam:** confirming a draft still writes `meal_plan_slot_history` per slot, and now also writes a durable `planner_events` row with `event_type = plan_confirmed` plus the confirmation payload needed for downstream grocery derivation work.
- **Schema + migration coverage added:** `apps/api/app/models/planner_event.py`, `apps/api/app/schemas/planner.py`, and `apps/api/migrations/versions/rev_20260308_03_aiplan05_planner_events.py` add the event persistence contract and reversible migration seam.
- **Regression coverage added:** `apps/api/tests/test_planner.py`, `apps/api/tests/test_aiplan05_migration.py`, `apps/api/tests/schemas/test_planner_schemas.py`, and `apps/worker/tests/test_generation_worker.py` now prove stale triggering from grounding changes, confirmed-plan protection, one-time history/event writes, migration round-trip behavior, event payload shape, and worker non-reuse when grounding changes.
- **Verification evidence:**
  - `cd apps\api && python -m pytest tests\test_planner.py tests\test_aiplan05_migration.py tests\schemas\test_planner_schemas.py`
  - `cd apps\worker && python -m pytest tests\test_generation_worker.py`
  - `cd apps\api && python -m pytest tests`
  - `cd apps\worker && python -m pytest tests`
  - `cd apps\api && python -m compileall app tests migrations`
  - `cd apps\worker && python -m compileall app worker_runtime tests`

## 14. AIPLAN-06 verification evidence

- **Verdict:** APPROVED. The backend and worker Milestone 2 contract slice now has explicit regression coverage for every acceptance area requested by AIPLAN-06: draft creation, slot edit/revert, regen lifecycle, stale detection, confirmation idempotency, provenance/history/event writes, and fallback/manual-guidance behavior.
- **API verification tightened:** `apps/api/tests/test_planner.py` now proves slot regeneration exposes `pending_regen` state before worker completion, dedupes retried regen requests, clears pending state after completion, and refreshes slot provenance fields (`ai_suggestion_request_id`, `ai_suggestion_result_id`, `prompt_family`, `prompt_version`, `fallback_mode`) from the regen result. It also proves stale-warning acknowledgment persists through confirmation into the confirmed plan, slot-history rows, and the emitted `plan_confirmed` event payload.
- **Worker verification tightened:** `apps/worker/tests/test_generation_worker.py` now proves curated fallback results persist visible fallback metadata (`reason_codes`, explanation text, uses-on-hand, missing-hints) and that a successful slot regeneration rewrites only the targeted slot while updating request/result lineage, prompt metadata, and regen status cleanup.
- **Verification evidence:**
  - `cd apps\api && python -m pytest tests\test_planner.py`
  - `cd apps\worker && python -m pytest tests\test_generation_worker.py`
  - `cd apps\api && python -m pytest tests`
  - `cd apps\worker && python -m pytest tests`

## 15. AIPLAN-08 completion evidence

- **Planner review and confirmation flow completed:** `apps/web/app/planner/_components/PlannerView.tsx` now keeps the current confirmed plan visible while a new AI suggestion or editable draft is under review, repeats stale-warning acknowledgement on the confirmation path, and uses replacement-focused confirmation copy when a confirmed plan already exists.
- **Fallback and per-slot recovery messaging clarified:** `apps/web/app/planner/_components/AISuggestionBanner.tsx`, `PlanSlotCard.tsx`, and `apps/web/app/_lib/planner-ui.ts` now explain curated fallback/manual-guidance states in plain language, surface reason-code/on-hand/missing-hint review details for AI-backed slots, and keep per-slot regeneration failures anchored to the user's last safe slot value or original AI suggestion.
- **Confirmed-plan presentation now stays human-owned:** `WeeklyGrid.tsx` and `PlanSlotCard.tsx` suppress AI badges/explanation provenance in the confirmed-plan presentation while preserving richer AI review metadata in suggestion and draft states.
- **Frontend regression coverage added:** `apps/web/app/_lib/planner-api.test.ts` now verifies slot fallback/on-hand/hint mapping from the backend contract, and `apps/web/app/_lib/planner-ui.test.ts` covers curated fallback detail text, insufficient-context messaging, regeneration recovery copy, and replacement confirmation labels.
- **Verification evidence:**
  - `npm run lint:web`
  - `npm run typecheck:web`
  - `npm --prefix apps\web run test`
  - `npm run build:web`

## 16. AIPLAN-09 and AIPLAN-10 completion evidence

- **Confirmed-plan grocery handoff is now explicit and gated:** `apps/api/app/schemas/planner.py` and `apps/api/app/services/planner_service.py` now embed a `grocery_refresh_trigger` payload inside the durable `plan_confirmed` event, including `source_plan_status = confirmed`, confirmed plan/version identifiers, and the lifecycle correlation ID that downstream grocery derivation can trust. `apps/api/tests/test_planner.py` proves suggestion and draft states create no planner events, so they cannot feed grocery derivation accidentally.
- **Planner observability now spans API and worker lifecycle:** `apps/api/app/services/planner_service.py` logs suggestion, draft-open, regeneration, and confirmation outcomes with correlation IDs and grocery-trigger flags, while `apps/worker/worker_runtime/runtime.py` logs request start/reuse/completion/failure with request-scoped correlation IDs and converts unexpected worker exceptions into durable `failed` request states instead of silent crashes.
- **Deterministic planner fixtures now cover the required backend/worker paths:** `apps/worker/tests/planner_fixtures.py` centralizes deterministic provider fixtures, and `apps/worker/tests/test_generation_worker.py` now covers happy path, stale reuse invalidation, curated fallback/manual-guidance behavior, and explicit failure handling/logging. `apps/api/tests/schemas/test_planner_schemas.py` and `apps/api/tests/test_planner.py` validate the handoff payload contract and planner observability seam.
- **Verification evidence:**
  - `cd apps\api && python -m pytest tests\test_planner.py tests\schemas\test_planner_schemas.py`
  - `cd apps\worker && python -m pytest tests\test_generation_worker.py`
  - `cd apps\api && python -m pytest tests -x -vv -s`
  - `npm run test:worker`

## 17. AIPLAN-11 verification evidence

- **Verdict:** APPROVED. The planner UI slice now has direct automated evidence for the Milestone 2 journeys McCoy was assigned to verify: request → review → edit → confirm, stale-warning acknowledgment, per-slot regeneration, confirmed-plan protection, and visible failure/manual fallback paths.
- **Planner E2E coverage added:** `apps/web/tests/e2e/planner-acceptance.spec.ts` now exercises a protected-confirmed-plan replacement journey end to end, proves stale-warning acknowledgment is required on the confirmation path, shows targeted-slot-only regeneration while sibling slots stay interactive, and verifies both regeneration-failure/manual-recovery messaging and manual-guidance/request-failure banner honesty.
- **Frontend contract coverage tightened:** `apps/web/app/_lib/planner-api.test.ts` now verifies stale-warning draft mapping and the confirmation payload/response contract so the E2E layer is backed by explicit API-shape assertions, not only UI clicks.
- **Verification evidence:**
  - `npm --prefix apps\web run test`
  - `npm --prefix apps\web run test:e2e -- tests/e2e/inventory-trust.spec.ts`
  - `npm --prefix apps\web run test:e2e -- tests/e2e/planner-acceptance.spec.ts`
  - `npm run lint:web`
  - `npm run typecheck:web`
  - `python -m pytest apps\api\tests\test_planner.py`
  - `npm run test:worker`
  - `npm run test:api`
- **Shared-workspace note:** `npm run build:web` currently fails in this working tree with pre-existing Next.js page collection errors for `/api/[...path]`, `/_not-found`, and `/grocery`. That failure sits outside the planner acceptance journeys exercised here, so McCoy is approving the AIPLAN-11 slice while leaving the fresh-build stabilization issue visible for the final Milestone 2 reviewer.

## 18. AIPLAN-12 — Final Milestone 2 Acceptance Review (Kirk)

**Verdict: ✅ MILESTONE 2 APPROVED**

Date: 2026-03-08
Reviewer: Kirk (Lead)
Spec under review: `.squad/specs/ai-plan-acceptance/feature-spec.md`

### Independent evidence suite (run by Kirk, not inherited from progress claims)

| Check | Result |
| --- | --- |
| `python -m pytest apps\api\tests -x -v --tb=short` | 144 passed, 0 failed |
| `python -m pytest apps\worker\tests -x -v --tb=short` | 9 passed, 0 failed |
| `npm --prefix apps\web run test` | 26 passed, 0 failed |
| `npm run lint:web` | Clean — 0 errors, 0 warnings |
| `npm run typecheck:web` | Clean — no errors |
| `npm run build:web` | SUCCESS — all 7 routes generated (previously noted failure is now resolved) |

### Acceptance criteria verification (feature spec §12)

| # | Criterion | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Request AI suggestion → async result → open draft with AI slots | ✅ | `test_request_poll_and_open_draft_flow`, planner service `request_suggestion` + `open_draft_from_suggestion`, E2E coverage |
| 2 | Each AI slot shows title, summary, reason codes, explanation | ✅ | `PlanSlotCard.tsx` renders all four fields + usesOnHand/missingHints during draft/review |
| 3 | Replace slot → marked `user_edited`, original retained | ✅ | `test_edit_and_revert_slot_preserves_original_suggestion`, slot PATCH transitions origin, `original_suggestion` snapshot preserved |
| 4 | Per-slot regen → only targeted slot enters generating state | ✅ | `test_slot_regeneration_updates_only_targeted_slot`, `target_slot_id` scoping, worker single-slot support, E2E coverage |
| 5 | Mixed drafts confirmable (any combination of origins) | ✅ | `test_confirm_writes_slot_history_and_plan_confirmed_event_once` confirms ai_suggested + user_edited mix; E2E confirms mixed post-edit/regen plan |
| 6 | Stale warning visible before confirmation | ✅ | `test_inventory_change_marks_existing_draft_stale`, grounding hash comparison in `_plan_is_stale()`, `StaleDraftWarning` component, E2E coverage |
| 7 | Stale warning doesn't block but must be acknowledged | ✅ | Frontend blocks confirm without acknowledgment checkbox; API requires `stale_warning_acknowledged`; `test_confirm_requires_stale_warning_acknowledgement` |
| 8 | Confirmed plan protected from new suggestions/drafts | ✅ | `test_new_suggestion_and_draft_do_not_overwrite_existing_confirmed_plan`, draft operations never load confirmed status, E2E coverage |
| 9 | Confirmation is idempotent | ✅ | Unique constraint `uq_meal_plan_confirmation_mutation`, `_get_confirmed_by_mutation()` dedup check, tested explicitly |
| 10 | After confirmation: confirmed record + per-slot history | ✅ | `MealPlanSlotHistory` model with all required fields, one-time write verified in tests, history includes prompt_family/version/fallback_mode/stale_warning |
| 11 | Confirmed plan UI suppresses AI badges | ✅ | `WeeklyGrid` renders with `showOriginBadges={false}` + `showSuggestionMeta={false}` for confirmed plans |
| 12 | Grocery derivation only from confirmed state | ✅ | `plan_confirmed` event with `grocery_refresh_trigger` payload; tests prove suggestion/draft states emit no events |
| 13 | Test coverage for all required areas | ✅ | All 8 sub-areas have automated coverage (see test coverage analysis below) |
| 14 | Stale-confirm history captures `stale_warning_present_at_confirmation` | ✅ | `test_confirming_stale_draft_persists_acknowledged_provenance` verifies flag in history rows and event payload |

### Constitution alignment

| Rule | Status |
| --- | --- |
| 2.4 Trustworthy Planning | ✅ Confirmed plan is sole authority for grocery; AI suggestions never silently promote |
| 2.5 Explainable AI | ✅ Reason codes, explanations, fallback modes visible during review; AI origin stored but not emphasized post-confirm |
| 2.3 Shared Household | ✅ One active draft per household+period; confirmed plan protection unconditional |
| 2.2 Offline Required | ⏳ Explicitly deferred to Milestone 4 (AIPLAN-13); honest "requires connection" states in place |
| 2.7 UX Quality | ✅ Stale warning, regen indicators, fallback messaging, confirmation error recovery all present |
| 4.1 Spec-First | ✅ Feature spec preceded all implementation |
| 5.1/5.2/5.3 Quality Gates | ✅ Automated tests cover all required state transitions |

### Explicit follow-ups (non-silent carryover)

These items are **not Milestone 2 gaps** — they are either cross-milestone work or known inherited follow-ups:

1. **AIPLAN-13 — Offline planner sync (Milestone 4):** Feature spec §9.1 describes offline-aware draft behavior. The roadmap intentionally defers full replay/conflict handling to Milestone 4. Honest "requires connection" states are in place. This is tracked openly.
2. **AIPLAN-14 — Grocery derivation consumption (Milestone 3):** The confirmed-plan handoff seam exists and is contract-tested. Full grocery derivation engine is Milestone 3 scope.
3. **`manually_added` slot in mixed confirmation test:** Test suite verifies ai_suggested + user_edited combinations thoroughly but does not have a dedicated test confirming all three origins in a single draft. Minor gap — the data model treats all origins identically at confirmation. Recommend adding coverage in Milestone 3 test hardening.
4. **Auth0 production wiring:** Still using dev header seam (`X-Dev-*`). Known from Milestone 1 follow-ups, not Milestone 2 scope.
5. **`datetime.utcnow()` deprecation warnings:** 172 warnings in API tests. Known since Milestone 1. Non-blocking; recommend addressing before Python 3.14.
6. **Dual lockfile warning:** Next.js warns about multiple lockfiles. Non-blocking.

### Previously noted build failure — resolved

The `npm run build:web` failure noted in AIPLAN-11 evidence (Next.js page collection errors for `/api/[...path]`, `/_not-found`, `/grocery`) is **now resolved**. Kirk's independent build run produced a clean success with all 7 routes generated.

### Decision

**Milestone 2 is APPROVED.** The repo now supports the planner/AI milestone outcome as defined in the feature spec: a household can request an async AI suggestion, review and edit a draft, regenerate individual slots, confirm the final plan explicitly, preserve per-slot AI origin history, and keep grocery derivation gated on confirmed plan state only. All 14 acceptance criteria pass. The evidence suite is green. Constitution alignment is verified. Cross-milestone deferred work is tracked openly, not hidden.
