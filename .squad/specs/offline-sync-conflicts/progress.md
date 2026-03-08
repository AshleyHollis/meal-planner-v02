# Offline Sync Conflicts Progress

Date: 2026-03-09
Status: 🚀 **MILESTONE 4 EXECUTION ADVANCING** — contract seam, client durability foundation, mobile trip mode, backend replay/conflict handling, sync observability, and conflict-review UX complete; independent verification remains in flight
Spec: `.squad/specs/offline-sync-conflicts/feature-spec.md`
Tasks: `.squad/specs/offline-sync-conflicts/tasks.md`

## 1. Current summary

- **Milestone 1 is complete and approved.** Household-scoped authoritative inventory, idempotent mutation handling, audit history, and backend-owned session context are already trustworthy foundations for offline replay work.
- **Milestone 2 is complete and approved.** Confirmed weekly plans and the `plan_confirmed` handoff seam already exist and remain the only planner input path for downstream grocery/trip work.
- **Milestone 3 is complete and approved.** Kirk signed off GROC-11 on 2026-03-08T23-00-00Z, and the grocery slice now provides the stable confirmed-list handoff seam Milestone 4 needs: `grocery_list_version_id`, stable `grocery_line_id`, `confirmed_at`, household-scoped mutation receipts, and confirmed-list immutability.
- **Milestone 4 execution is now advancing.** SYNC-01 through SYNC-08 are complete. Trip mode now queues and replays over the confirmed snapshot with durable offline storage, conflict classification runs server-side with consumer-safe deduplication and auto-merge boundaries, explicit keep-mine/use-server resolution commands refresh authoritative read models, sync reconnect diagnostics/fixtures make backend behavior release-traceable and deterministic, and the web trip flow now exposes a phone-first conflict summary/detail review path instead of a placeholder warning.
- **Local development environment restored (2026-03-09T06-00-00Z).** Build cache corruption cleared; typecheck, lint, and build all passing; web/API/worker services responsive; database schema intact with Milestone 3/4 contract seams stable.
- **No new user interview was required for honest task breakdown.** The conflict-resolution product decisions are already locked in the approved offline-sync-conflicts spec and mirrored in `.squad/decisions.md`.
- **The main implementation gap is now independent verification.** Current code now has the Milestone 4 contract seam, a durable client offline store/runtime foundation, confirmed-snapshot caching, mobile trip-mode queue/replay wiring, persisted conflict records, conflict classification, explicit keep-mine/use-server resolution commands, correlation-aware sync diagnostics with deterministic reconnect/conflict fixtures, and the dedicated phone-first conflict review UX. The remaining release gates are reviewer-owned SYNC-09/10/11 validation, including the milestone-end manual smoke evidence in SYNC-10.

## 2. Discovery and alignment status

- Ashley’s approved Milestone 4 direction is already captured in:
  - `.squad/specs/offline-sync-conflicts/feature-spec.md`
  - `.squad/specs/offline-sync-conflicts/conflict-matrix.md`
  - `.squad/project/constitution.md`
  - `.squad/project/prd.md`
  - `.squad/project/roadmap.md`
  - `.squad/decisions.md` (§Offline Sync Conflicts Decisions)
- Milestone 3 completion and the confirmed grocery handoff seam are now confirmed in:
  - `.squad/specs/grocery-derivation/progress.md`
  - `.squad/decisions/inbox/kirk-groc-11-milestone-review.md`
- The refreshed Milestone 4 task plan is aligned with the roadmap cut line: mobile trip mode, offline queueing, and conflict-safe sync are in scope; shopping reconciliation remains Milestone 5.

## 3. Ready-now queue

**Reviewer ownership rule:** SYNC-09, SYNC-10, and SYNC-11 only count when the person closing the gate did not implement the slice being reviewed. Named squad roles are routing labels, not a substitute for independent review ownership.

| ID | Task | Agent | Status | Notes |
| --- | --- | --- | --- | --- |
| SYNC-00 | Keep Milestone 4 progress ledger current | Scribe | in_progress | Ledger is now active and should be updated on every transition, blocker, and verification result. |
| SYNC-01 | Lock the trip/offline contract seam across API and web types | Sulu | ✅ done | Completed 2026-03-08. Confirmed-list bootstrap, queue metadata, sync outcomes, conflict read models, and explicit resolution commands are now locked across API and web contracts. |
| SYNC-02 | Build the durable client offline store and queue foundation | Uhura | ✅ done | Completed 2026-03-09. IndexedDB-backed confirmed snapshot, queue/retry/conflict durability, offline runtime provider, and grocery fallback hydration now exist in web. |
| SYNC-03 | Implement mobile trip mode over the confirmed-list snapshot | Uhura | ✅ done | Completed 2026-03-09. GroceryView now offers phone-first trip actions over the confirmed snapshot, durable offline queueing, reconnect sync upload, and visible local sync state without claiming conflict-resolution work is done. |
| SYNC-04 | Add sync upload API and stale-detection foundations | Scotty | ✅ done | Completed 2026-03-09. Household-scoped sync upload, durable conflict records, and stale replay foundations are live in API. |
| SYNC-05 | Implement the MVP conflict classifier and replay rules | Scotty | ✅ done | Completed 2026-03-09. Duplicate retry, narrow safe auto-merge, explicit review-required classes, and same-list replay stop now follow the approved conflict matrix. |
| SYNC-06 | Implement explicit resolution commands and read-model refresh | Scotty | ✅ done | Completed 2026-03-09. Keep-mine/use-server commands now resolve conflicts explicitly, supersede stale local intent via audit metadata, and return refreshed authoritative grocery snapshots. |
| SYNC-07 | Wire the mobile conflict-review UX and resolution flow | Uhura | ✅ done | Completed 2026-03-09. Trip mode now shows mobile conflict summary/detail views, distinguishes retryable vs review-required states, preserves local intent for review, and supports explicit keep-mine/use-server resolution with refreshed local state. |
| SYNC-08 | Add observability, diagnostics, and deterministic sync fixtures | Scotty | ✅ done | Completed 2026-03-09. Sync replay/resolution logs now carry correlation-aware outcome context, and deterministic reconnect/conflict fixtures/helpers now cover duplicate, auto-merge, review-required, and manual-resolution paths. |
| SYNC-09 | Verify the backend sync/conflict slice | McCoy | pending | Depends on SYNC-04, SYNC-05, SYNC-06, and SYNC-08. This gate must be closed by someone other than the backend implementation owner(s). |
| SYNC-10 | Verify mobile trip/offline behavior end to end | McCoy | pending | Depends on SYNC-02, SYNC-03, SYNC-07, and SYNC-08. This is the planned single milestone-end visual smoke gate for Milestone 4 closure evidence, and it must stay independent from the implementation owner(s) of the trip/conflict UX slice. |
| SYNC-11 | Final Milestone 4 acceptance review | Kirk | pending | Final milestone cut-line and acceptance review after verification gates are complete, consuming the smoke evidence already captured in SYNC-10. Final approval ownership must stay independent from Milestone 4 implementation ownership. |

## 4. Blocked or cross-milestone queue

| ID | Task | Agent | Status | Blocked by | Notes |
| --- | --- | --- | --- | --- | --- |
| SYNC-12 | Convert confirmed trip outcomes into authoritative inventory updates | Scotty + Sulu | blocked | Milestone 5 shopping reconciliation | Milestone 4 stops at trustworthy trip outcomes and conflict-safe sync. Inventory apply remains an explicit downstream review/apply slice. |
| SYNC-13 | Add richer simultaneous multi-shopper coordination and live presence | Uhura + Scotty | blocked | Phase 2 collaboration scope | MVP requires conflict-safe shared state, not presence indicators or real-time collaboration polish. |
| SYNC-14 | Expand auto-merge beyond the locked MVP-safe classes | Scotty | blocked | Phase 2 merge policy approval | Broad semantic merge automation remains intentionally outside MVP. |

## 5. Risks and watchpoints

- **Independent verification risk:** SYNC-07 is now implemented, but milestone closure still depends on reviewer-owned SYNC-10 evidence, including the single manual desktop + phone smoke gate.
- **Conflict-trust risk:** the contract and UX are now implemented, but SYNC-09/SYNC-10 still need to verify that reconnect, review-required pauses, and manual resolutions behave trustworthily under independent reviewer scrutiny.
- **Scope-bleed risk:** it will be tempting to push shopping reconciliation into trip completion or to invent richer live-collaboration behavior. The roadmap explicitly keeps those concerns in later milestones.
- **Known inherited noise:** the repo still carries the non-blocking `datetime.utcnow()` warning noise in parts of the API test suite and the dual-lockfile Next.js warning during web build. Neither is a Milestone 4 planning blocker, but both remain worth cleanup later.

## 6. Current codebase watchpoints

- `apps/api/app/models/grocery.py` and `apps/api/app/schemas/grocery.py` already expose the stable confirmed-list identity seam (`stable_line_id`/`grocery_line_id`, `grocery_list_version_id`, `confirmed_at`) that trip mode should consume directly.
- `apps/api/app/routers/grocery.py` and `apps/api/app/services/grocery_service.py` now accept offline replay metadata such as `base_server_version`, return explicit sync outcome classes, persist durable conflict records, and expose keep-mine/use-server resolution commands plus conflict reads for the mobile UX.
- `apps/web/app/_lib/offline-sync.ts` now provides the web offline durability seam for confirmed snapshots, queue state, retry metadata, preserved conflicts, and local cleanup after a conflict is resolved; downstream work should extend it rather than forking new local state.
- `apps/web/app/grocery/_components/GroceryView.tsx` now runs the active phone-first trip flow over the confirmed snapshot: quick quantity changes, mark-done intent queueing, ad hoc trip items, reconnect upload, review-required conflict summary/detail rendering, and explicit keep-mine/use-server resolution all sit on top of the SYNC-02 offline store.

## 7. Baseline evidence for this planning refresh

Repo validation was re-run for this planning update using the existing repository checks:
- `npm run lint:web`
- `npm run typecheck:web`
- `npm run build:web`
- `npm run test:api`
- `npm run test:worker`

Result: all five commands passed for this planning refresh. Web lint, typecheck, and build are green; API tests passed at 171/171 with known non-blocking `datetime.utcnow()` warning noise; worker tests passed at 9/9. This planning-only update changes squad artifacts and the session plan, not application runtime code.

## 8. Planning exit criteria met

- `tasks.md` has been refreshed into an execution-ready Milestone 4 queue with dependencies, verification gates, and explicit cross-milestone follow-ons.
- `progress.md` now exists for Milestone 4 tracking.
- The approved offline-sync-conflicts behavior and the completed Milestone 3 confirmed-list seam are now treated as resolved prerequisites instead of open questions.
- The session `plan.md` has been refreshed to show Milestone 3 complete and Milestone 4 planning active.

## 9. SYNC-01 complete — trip/offline contract seam locked (2026-03-08)

- **Status:** ✅ complete
- **Owner:** Sulu
- **Scope delivered:** API and web contract/types now lock the Milestone 4 seam for confirmed-list bootstrap, queueable mutation metadata, sync outcomes, conflict read models, and explicit resolution commands.

### Delivered contract changes

- Added explicit Milestone 4 enums for:
  - `trip_state` (`confirmed_list_ready`, `trip_in_progress`, `trip_complete_pending_reconciliation`)
  - queue/local mutation states (`queued_offline`, `syncing`, `synced`, `retrying`, `failed_retryable`, `review_required`, `resolving`, `resolved_keep_mine`, `resolved_use_server`)
  - sync outcomes (`applied`, `duplicate_retry`, `auto_merged_non_overlapping`, the locked `review_required_*` classes, and `failed_retryable`)
  - explicit resolution actions/status (`keep_mine`, `use_server`, `pending`, resolved states)
- Added API schema/read-model contracts for:
  - `QueueableSyncMutation`
  - `SyncAggregateRef`
  - `GroceryConfirmedListBootstrapRead`
  - `SyncMutationOutcomeRead`
  - `SyncConflictSummaryRead`
  - `SyncConflictDetailRead`
  - `SyncConflictKeepMineCommand`
  - `SyncConflictUseServerCommand`
- Added `trip_state` as an explicit property on the grocery model/read contract so Milestone 4 can bootstrap trip/offline behavior from the confirmed-list seam without overloading placeholder grocery lifecycle wording.
- Updated web shared types and grocery API mapping/tests to match the backend contract seam.
- Corrected misleading placeholder trip copy in `GroceryView` so the UI now describes confirmed-list snapshot/trip bootstrap semantics instead of implying a delivered trip workflow that does not yet exist in this screen.

### Verification evidence

- `npm run lint:web`
- `npm run typecheck:web`
- `npm run build:web`
- `npm --prefix apps/web run test` → 37 passing
- `cd apps\api && python -m pytest tests` → 176 passing
- `cd apps\worker && python -m pytest tests` → 9 passing

### Notes for downstream tasks

- SYNC-02 / SYNC-04 / SYNC-06 should consume the new explicit `trip_state` + `SyncAggregateRef` seam instead of inferring trip bootstrap or conflict scope only from `GroceryListStatus`.
- Keep-mine/use-server resolution is now an explicit command contract, not a retry-side effect.

## 10. SYNC-02 complete — durable offline store and queue foundation (2026-03-09)

- **Status:** ✅ complete
- **Owner:** Uhura
- **Scope delivered:** Web now has an IndexedDB-backed offline sync foundation for confirmed grocery-trip snapshots, queue durability, retry metadata, conflict preservation, and downstream runtime plumbing without claiming the unfinished trip/conflict UX.

### Delivered frontend changes

- Added a durable client offline store in `apps/web/app/_lib/offline-sync.ts` with separate persisted records for:
  - confirmed-list snapshots (`GroceryConfirmedListBootstrap` + full grocery list snapshot),
  - related meal-plan context (`confirmedPlanVersion`, period boundaries, derived plan id),
  - inventory snapshot reference metadata,
  - queued sync mutations with retry counters/timestamps,
  - preserved local conflict detail records.
- Added `OfflineSyncProvider` / `useOfflineSync()` so downstream Milestone 4 UI work can access browser online/offline state plus queue/snapshot APIs without rebuilding storage wiring.
- Wired `GroceryView` to persist confirmed/trip snapshot baselines whenever the server returns them and to hydrate the last local confirmed snapshot when the network/server copy is unavailable, while staying read-only and honest about SYNC-03 still owning real trip-mode mutation UX.
- Added focused web tests covering confirmed snapshot creation, durable snapshot hydration, retry-state updates, and local conflict preservation across store reads.

### Verification evidence

- `npm run lint:web`
- `npm run typecheck:web`
- `npm run build:web`
- `npm --prefix apps\\web run test` → 40 passing

### Notes for downstream tasks

- SYNC-03 should queue only trip-mode intents against the stored confirmed snapshot scope; this task intentionally did **not** repurpose draft grocery review mutations into hidden offline behavior.
- SYNC-04 / SYNC-05 / SYNC-06 can now rely on preserved `client_mutation_id`, base server version, and conflict detail records surviving browser refresh/restart.
- The single Milestone 4 manual desktop/phone smoke gate remains assigned to SYNC-10 / McCoy per reviewer-separation rules; this implementation step does not close that gate.

## 11. SYNC-04 complete — sync upload API and stale-detection foundations (2026-03-09)

- **Status:** ✅ complete
- **Owner:** Scotty
- **Scope delivered:** The backend now accepts queued grocery sync uploads against confirmed/in-progress lists, advances authoritative grocery-list versions per accepted replay, detects stale uploads against the confirmed-list version seam, persists durable conflict records, and exposes conflict list/detail reads for downstream mobile review work.

### Delivered backend changes

- Added a new household-scoped `grocery_sync_conflicts` persistence model plus migration coverage for durable review artifacts keyed by `(household_id, local_mutation_id)`.
- Added `POST /api/v1/households/{household_id}/grocery/sync/upload` using the SYNC-01 `QueueableSyncMutation` seam and returning per-mutation `SyncMutationOutcomeRead` outcomes.
- Added `GET /api/v1/households/{household_id}/grocery/sync/conflicts` and `GET /api/v1/households/{household_id}/grocery/sync/conflicts/{conflict_id}` so downstream UX can read persisted summary/detail comparison data.
- Reused the existing household-scoped grocery mutation receipt pattern for duplicate retry detection and mapped those receipts into explicit `duplicate_retry` upload outcomes.
- Added confirmed-list/trip replay version advancement by cloning the current grocery-list snapshot into a new authoritative version for each accepted sync mutation, so `base_server_version` comparisons now have a durable integer seam.
- Added stale-detection foundations that compare uploaded mutations against the list version present at batch start, stop replay for stale conflicts, preserve per-mutation local/base/server summaries, and continue applying independent mutations for other lists in the same batch.

### Verification evidence

- `python -m pytest apps\api\tests\models\test_grocery_models.py apps\api\tests\test_sync04_migration.py apps\api\tests\test_grocery.py -q` → 30 passing
- `python -m pytest apps\api\tests -q` → 185 passing
- Local dev environment confirmed reachable:
  - API health responding on `http://127.0.0.1:8000/health`
  - Next.js dev web responding on `http://127.0.0.1:3000`

### Notes for downstream tasks

- SYNC-05 should refine the conservative stale classifier from the current foundation (`review_required_other_unsafe` / deleted-or-archived detection) into the approved conflict-matrix classes and narrow auto-merge behavior.
- SYNC-06 should build on the persisted `grocery_sync_conflicts` artifact and the explicit conflict read endpoints rather than inventing a parallel resolution store.
- The single Milestone 4 manual desktop/phone smoke gate remains assigned to SYNC-10 / McCoy per reviewer-separation rules; this implementation step does not close that gate.

## 12. SYNC-05 complete — MVP conflict classifier and replay rules (2026-03-09)

- **Status:** ✅ complete
- **Owner:** Scotty
- **Scope delivered:** The backend now classifies stale sync replays into the Milestone 4 MVP outcomes, auto-merges only narrow non-overlapping cases, preserves auto-merge rationale in upload/log outputs, and stops same-list replay once a review-required conflict is encountered.

### Delivered backend changes

- Added a stale replay classifier in `GroceryService` that keeps duplicate retry handling intact, emits `review_required_quantity` when same-line quantity/completion semantics changed, keeps deleted/archived targets explicit, and falls back to `review_required_other_unsafe` for ambiguous same-line drift.
- Added narrow `auto_merged_non_overlapping` handling for clearly safe stale replays where the local mutation does not overlap newer authoritative server changes, including stale independent ad hoc line adds and unchanged target-line removals/quantity edits.
- Preserved safe-merge rationale in the returned `SyncMutationOutcomeRead.auto_merge_reason` and the backend mutation log context so SYNC-07/SYNC-08 can explain why a stale replay applied automatically without inventing client merge logic.
- Kept replay-stop behavior list-scoped: once a review-required conflict is created for a grocery list within a batch, later queued mutations for that same list now stop with explicit review-required outcomes instead of continuing automatically.
- Enriched conflict detail summaries with adjustment notes, ad hoc notes, and purchase-state fields so downstream conflict-review UX has the authoritative context it needs.

### Verification evidence

- `apps\api\.venv\Scripts\python.exe -m pytest tests\test_grocery.py -q` → 22 passing
- `apps\api\.venv\Scripts\python.exe -m pytest tests -q` → 187 passing

### Notes for downstream tasks

- SYNC-06 can rely on the new classifier outcomes and persisted review artifacts instead of re-deriving stale categories during resolution commands.
- SYNC-07 should surface `auto_merge_reason` when helpful for trust messaging, but must continue treating `review_required_*` as a hard stop that needs explicit user action.
- SYNC-08 should extend observability from the new classifier/log seam rather than introducing a second source of truth for auto-merge rationale.
- The single Milestone 4 manual desktop/phone smoke gate remains assigned to SYNC-10 / McCoy per reviewer-separation rules; this implementation step does not close that gate.

## 13. SYNC-06 complete — explicit resolution commands and read-model refresh (2026-03-09)

- **Status:** ✅ complete
- **Owner:** Scotty
- **Scope delivered:** The backend now resolves review-required grocery sync conflicts through explicit keep-mine/use-server commands, preserves superseded local intent on the durable conflict record, refreshes conflict/read-model server snapshots before resolution, and returns refreshed authoritative grocery-list state for client snapshot updates.

### Delivered backend changes

- Added `POST /api/v1/households/{household_id}/grocery/sync/conflicts/{conflict_id}/resolve-keep-mine` and `POST /api/v1/households/{household_id}/grocery/sync/conflicts/{conflict_id}/resolve-use-server` on top of the existing household-scoped conflict store.
- Keep-mine now creates an explicit follow-up resolution command using a new `client_mutation_id`, replays the saved local intent against the latest authoritative version, and marks the original stale conflict resolved instead of erasing it.
- When a deleted-or-archived line is explicitly kept, the backend now restores that line only through the explicit resolution path so the user's intent is preserved without hidden replay.
- Use-server now resolves the durable conflict without creating a second grocery mutation, preserves the original conflict audit trail, and returns the current server-truth grocery snapshot so the client can refresh local state immediately.
- Conflict list/detail reads now refresh pending conflicts' current server version + server-state summary before rendering, keeping review comparisons honest if the authoritative grocery list changed again after the conflict was first recorded.

### Verification evidence

- `python -m pytest apps\api\tests\test_grocery.py -q` → 25 passing
- `python -m pytest apps\api\tests -q` → 190 passing
- `npm --prefix apps\web run test -- grocery-api.test.ts` → passing (45 total web library tests in the current harness run)
- `npm run typecheck:web`
- `npm run lint:web`

### Notes for downstream tasks

- SYNC-07 should use the resolution command response as the authoritative snapshot refresh payload and the conflict detail endpoint for audit/detail rendering, rather than issuing an optimistic client-side merge.
- The resolution audit link now lives on the durable conflict record under `local_intent_summary.resolution`; downstream UX can surface it if/when that provenance becomes user-visible.
- The single Milestone 4 manual desktop/phone smoke gate remains assigned to SYNC-10 / McCoy per reviewer-separation rules; this implementation step does **not** close that gate.

## 14. SYNC-08 complete — observability, diagnostics, and deterministic sync fixtures (2026-03-09)

- **Status:** ✅ complete
- **Owner:** Scotty
- **Scope delivered:** The backend now emits correlation-aware diagnostics for duplicate replay, safe auto-merge, review-required conflict creation, replay re-encounter of persisted conflicts, and explicit keep-mine/use-server resolutions. Deterministic sync fixtures/helpers now make reconnect and conflict scenarios repeatable in regression coverage without inventing a second sync truth source.

### Delivered backend changes

- Extended grocery sync mutation logging so replay outcomes now carry aggregate identity, base/current server version context, provisional aggregate IDs, durable conflict IDs, resolution action metadata, and auto-merge rationale in the existing structured log seam.
- Duplicate sync replays now emit an explicit `duplicate_retry` diagnostic instead of silently returning a receipt-only outcome, and persisted conflicts re-surfacing on reconnect now log their durable review-required outcome with the same correlation thread.
- New deterministic sync fixtures/helpers in `apps/api/tests/grocery_fixtures.py` now generate reproducible upload payloads for reconnect add/adjust flows plus named fixture constants for duplicate retry, auto-merge, review-required conflict, and manual resolution diagnostics.
- Added focused grocery API regression coverage proving the emitted diagnostics for duplicate replay, safe auto-merge, review-required quantity conflicts, and both manual resolution commands.

### Verification evidence

- `cmd /c "cd apps\\api && python -m pytest tests\\test_grocery.py -q"` → 29 passing
- `npm run test:api`
- `npm run test:worker`

### Notes for downstream tasks

- SYNC-07 should reuse the new deterministic sync fixture constants/helpers when adding mobile conflict-review UI coverage, rather than hand-authoring reconnect payloads in each test.
- SYNC-09 can treat the structured sync log seam as the reviewer-facing backend observability baseline for Milestone 4, with durable conflicts/receipts still remaining the audit source of truth.
- The single Milestone 4 manual desktop/phone smoke gate remains assigned to SYNC-10 / McCoy per reviewer-separation rules; this implementation step does **not** close that gate.

## 15. McCoy local visual smoke review (2026-03-07)

- **Status:** ✅ local app reviewed and highest-value breakages corrected before Milestone 4 acceptance work continues.
- **Supported local flow exercised:** FastAPI on `127.0.0.1:8000` plus Next.js dev web on `127.0.0.1:3004` (moved off `3000` because that port was already occupied in the shared workspace).

## 16. Local dev environment recovery refresh (2026-03-08)

- **Status:** ✅ recovered and re-verified
- **Observed breakages:**
  - `npm run dev:worker` failed immediately with `ModuleNotFoundError: No module named 'worker_runtime'` because the worker entrypoint was being launched as a script without `apps\worker` on `sys.path`.
  - `python -m pytest apps\worker\tests -q` and `npm run test:worker` could fail during collection because the worker test bootstrap put `apps\worker` ahead of `apps\api`, causing `import app.models` to resolve the worker's `app` package instead of the API package.
  - The shared workspace still behaves exactly like the earlier watchpoint: orphaned repo-specific node/python processes can leave `http://127.0.0.1:3000` returning 500 while a stale API is still alive elsewhere.
- **Recovery actions taken:**
  - Bootstrapped `apps\worker` onto `sys.path` inside `apps\worker\app\main.py` so the supported root command `npm run dev:worker` works again.
  - Forced API import-path priority in `apps\worker\worker_runtime\runtime.py` and aligned `apps\worker\tests\conftest.py` so worker runtime/tests resolve the API `app.models` package consistently.
  - Cleared repo-specific orphaned node/python processes before relaunching Aspire, then restarted the supported local path cleanly.
- **Re-verified supported local commands/URLs:**
  - `aspire run --project .\apps\apphost\MealPlanner.AppHost.csproj`
    - web: `http://127.0.0.1:3000`
    - session bootstrap: `http://127.0.0.1:3000/api/v1/me`
    - dashboard: logged localhost HTTPS Aspire port (observed `https://localhost:17185`)
  - `npm run dev:api` → `http://127.0.0.1:8000/health` returned 200 during smoke
  - `npm run dev:worker` → scaffold starts successfully again
- **Verification evidence:**
  - `npm run lint:web`
  - `npm run typecheck:web`
  - `npm run build:web`
  - `npm --prefix apps\web run test` → 44 passing
  - `python -m pytest apps\api\tests -q` → passing
  - `python -m pytest apps\worker\tests -q` → 9 passing
  - `npm run test:worker` → 9 passing
- **Broken before fix:** planner and grocery screens were crashing behind 500s because the default local SQLite file still carried pre-planner/pre-grocery schema, and local web dev/build/smoke runs were sharing one `.next` output tree, making the app brittle during review.
- **Fixes verified:** local API now quarantines incompatible local SQLite state into a backup or process-specific fallback DB instead of crashing the app; web dev/build now isolate Next output directories so manual smoke/build runs stop trampling the main local dev output; desktop/mobile smoke now loads honest empty states for planner/grocery instead of generic failure banners.
- **Manual smoke evidence captured:** `test-results\\home-desktop.png`, `home-mobile.png`, `inventory-desktop.png`, `inventory-mobile.png`, `planner-desktop.png`, `planner-mobile.png`, `grocery-desktop.png`, `grocery-mobile.png`, plus live-flow evidence in `inventory-added-desktop.png` and `planner-requested-desktop.png`.
- **Functional verification:** inventory add-item flow succeeded (`Milk`, 2 litres); planner request-suggestion flow succeeded and returned an AI suggestion grounded in the new inventory state; planner/grocery empty-state copy remained responsive with no horizontal overflow on iPhone 13 viewport.
- **Validation rerun after fixes:** `npm run lint:web`, `npm run typecheck:web`, `npm run build:web`, `npm --prefix apps/web run test`, `python -m pytest apps\api\tests -q`, and `npm run test:worker` all passed.
- **Acceptance expectation updated:** each milestone now needs one manual visual smoke pass on desktop and phone-sized viewports at the milestone-end verification gate, with final acceptance consuming that same evidence instead of rerunning smoke at every intermediate sub-step.

## 17. Local dev environment confirmed for Milestone 4 work (2026-03-07)

- **Status:** ✅ running in the repo-supported orchestration path.
- **Supported startup path confirmed:** `aspire run --project .\apps\apphost\MealPlanner.AppHost.csproj` from the repo root.
- **Usable local entrypoints observed in this session:** web at `http://127.0.0.1:3000`, Aspire dashboard on the localhost HTTPS port printed by the AppHost log, and API health on the AppHost-assigned Uvicorn port rather than a fixed `127.0.0.1:8000` assumption.
- **Health evidence:** web root plus `/inventory`, `/planner`, and `/grocery` all returned HTTP 200; direct API `/health` returned HTTP 200 on the current AppHost-assigned port; proxied session bootstrap at `http://127.0.0.1:3000/api/v1/me` returned the expected authenticated dev session payload.
- **Workaround required:** stale/orphaned repo-specific Aspire, Next.js, and Uvicorn processes were leaving port `3000` in a broken 500 state and misleadingly preserving old random API ports. Cleaning those repo-specific leftovers and restarting AppHost restored a healthy local environment.
- **Guidance change for Milestone 4 implementers:** when local startup looks half-alive, do not trust an old `3000` or `8000` process by itself. Restart the repo through AppHost, then take the dashboard port and current API port from the fresh AppHost log/output.

## 18. SYNC-03 complete — mobile trip mode over the confirmed snapshot (2026-03-09)

- **Status:** ✅ complete
- **Owner:** Uhura
- **Scope delivered:** Web grocery now exposes a true phone-first trip flow over the confirmed-list snapshot with durable local edits, reconnect replay wiring, and honest sync-state surfaces while keeping conflict resolution explicitly out of scope for this slice.

### Delivered frontend changes

- `GroceryView` now switches into **Trip mode** for confirmed/trip snapshots and shows:
  - large touch targets,
  - quick `-1 / +1` quantity changes,
  - mark-done check-off flow,
  - quick-add ad hoc trip items,
  - local queued/retrying/review-needed sync state in both the page header and affected lines.
- Trip actions now enqueue durable `adjust_quantity`, `remove_line`, and `add_ad_hoc` intents against the stored confirmed snapshot scope from SYNC-02, then replay them through the SYNC-04 upload API when the device is online.
- Local optimistic trip working state now survives reload/offline fallback by updating the durable snapshot copy immediately, while preserving local conflict artifacts for later dedicated review work.
- Added focused web tests for optimistic trip-mode helpers plus grocery API sync upload/conflict reads, and expanded Playwright grocery acceptance coverage to include offline queueing + reconnect sync on a phone-sized viewport.

### Verification evidence

- `npm --prefix apps\\web run test` → 44 passing
- `npm --prefix apps\\web run lint`
- `npm --prefix apps\\web run typecheck`
- `npm --prefix apps\\web run build`
- `npm --prefix apps\\web run test:e2e -- grocery-acceptance.spec.ts` → 4 passing

### Notes for downstream tasks

- SYNC-07 should build the dedicated mobile conflict summary/detail + keep-mine/use-server flow on top of the now-visible saved review-required state instead of replacing the queue/snapshot wiring.
- The Milestone 4 manual desktop/phone smoke gate remains owned by SYNC-10 / McCoy per reviewer-separation rules; this implementation step does **not** close that gate.

## 19. SYNC-07 complete — mobile conflict-review UX and resolution flow (2026-03-09)

- **Status:** ✅ complete
- **Owner:** Uhura
- **Scope delivered:** Trip mode now gives shoppers a mobile-friendly conflict summary/detail flow with explicit keep-mine/use-server actions, durable local review context, and authoritative snapshot refresh after a resolution is chosen.

### Delivered frontend changes

- Replaced the placeholder trip sync warning in `apps/web/app/grocery/_components/GroceryView.tsx` with a real saved-conflict summary surface that:
  - distinguishes review-required conflicts from retryable connection/service failures,
  - shows per-conflict class labels plus server/base version context,
  - lets the shopper open a dedicated detail view from a phone-sized screen.
- Added a dedicated conflict review dialog (`SyncConflictReviewModal`) that explains:
  - what the shopper changed locally,
  - what changed on the server,
  - what the base snapshot looked like before the device went offline,
  - what keep mine vs use server will do next.
- Wired explicit resolution actions to Scotty’s SYNC-06 APIs so the UI now:
  - sends a fresh resolution mutation ID,
  - clears the stale queued mutation + local conflict record after success,
  - refreshes the saved confirmed snapshot from the authoritative resolution response,
  - leaves retryable failures in their own non-conflict surface instead of collapsing everything into “sync failed.”
- Added pure helper coverage for conflict copy/field formatting, offline-store coverage for clearing resolved conflicts out of the local review queue, and Playwright phone-sized conflict flows for both keep-mine and use-server outcomes.

### Verification evidence

- `npm --prefix apps\\web run lint`
- `npm --prefix apps\\web run typecheck`
- `npm --prefix apps\\web run test` → 48 passing
- `npm --prefix apps\\web run build`
- `npm --prefix apps\\web run test:e2e -- grocery-acceptance.spec.ts` → 6 passing

### Notes for downstream tasks

- SYNC-10 / McCoy still owns the milestone-end manual desktop + phone smoke evidence. This implementation step added automated coverage only and does **not** close the reviewer-separation smoke gate.
- If Kirk or McCoy want richer reviewer-facing provenance later, the local conflict detail rendering already preserves base/local/server summaries and can surface additional resolution audit metadata without changing the mobile flow shape.
