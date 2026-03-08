# Scotty History

## Project Context
- **User:** Ashley Hollis
- **Project:** AI-Assisted Household Meal Planner
- **Stack:** REST API, modern web UI, AI assistance, inventory/product mapping workflows
- **Description:** Build a connected household meal planning platform spanning inventory, meal plans, substitutions, store mapping, shopping trips, and inventory updates after shopping or cooking.
- **Team casting:** Star Trek TOS first.

## Learnings
- Team initialized on 2026-03-07 for Ashley Hollis.
- Current focus is spec-first setup for the AI-assisted household meal planning platform.
- Inventory audit contracts need explicit before/after freshness and location snapshots on metadata events; current-state reads alone are not enough to reconstruct trust-sensitive changes later.
- For confirmed-plan idempotency, carrying the confirmation mutation ID on the authoritative plan record is a practical Wave 1 contract seam while the broader persistence/receipt layer is still lightweight.

## Wave 1 Backend — 2026-03-07

### What was built
- Module structure added: `app/models/`, `app/routers/`, `app/services/`.
- `app/models/session.py` — `SessionResponse`, `SessionUser`, `HouseholdMembership`, `HouseholdRole` contract shapes.
- `app/models/inventory.py` — full domain model per inventory-foundation spec: `InventoryItem`, `InventoryAdjustment`, all 8 `MutationType` enums, all `ReasonCode` enums, `FreshnessBasis`, `StorageLocation`, and all command / receipt response models.
- `app/services/inventory_store.py` — in-memory `InventoryStore` with idempotent receipt cache. Drop-in replaceable with a real repository when the DB layer arrives.
- `app/routers/session.py` — `GET /api/v1/me` contract seam (unauthenticated stub, locked shape).
- `app/routers/inventory.py` — full inventory REST surface: list, get, create, adjust-quantity (increase/decrease/set), set-metadata, move-location, archive, corrections, history.
- `tests/test_session.py` — 3 tests covering the session bootstrap contract.
- `tests/test_inventory.py` — 26 tests covering all mutation types, idempotency, household scoping, 404 paths, history, and archive behaviour.
- `pyproject.toml` — added `httpx` as dev dependency for `TestClient`.
- 29/29 tests pass.

### Key learnings / constraints surfaced
- `household_id` must be passed explicitly in Wave 1 (no JWT yet). This will invert when auth lands — flagged in decisions inbox.
- `actor_user_id` is a stub string. Every adjustment record carries it for audit trail; will be replaced by JWT subject claim.
- `model_copy(update=...)` is the correct Pydantic v2 pattern for overriding a field on an existing model instance. `model_dump()` + keyword override fails when the field is already present in the dump.
- `dependency_overrides` on the FastAPI app singleton works well for injecting a fresh per-test store; test isolation is clean.
- In-memory store is intentionally un-thread-safe. Sufficient for single-process dev/test. A real DB-backed repo must replace it before production.
- The `TestClient` fixture must clean up `dependency_overrides` after each test to avoid cross-test contamination (done via fixture yield + pop).

## Team Updates (2026-03-07)

**Scribe consolidation (Wave 1 data foundation review assignment, 2026-03-07T21:40:29Z):**
- McCoy completed Wave 1 data foundation review and rejected for 5 spec-alignment gaps:
  1. Inventory freshness/audit contracts (validators, history traceability)
  2. Grocery derivation lifecycle fields (draft/confirmed state, version, confirmed_at)
  3. Reconciliation state variants (not purchased, conflict/review-required, leftovers targeting)
  4. AI plan audit fields (required client_mutation_id, slot origin, result ID, prompt family, confirmation-time)
  5. Test coverage gaps
- McCoy also completed Wave 1 backend re-review and rejected for critical idempotency bug (receipts keyed globally, not by household + mutation ID, causes cross-household corruption).
- Scotty assigned to revise Wave 1 data foundation (Sulu locked out per reviewer lockout rules).
- Bones assigned to fix backend idempotency bug (Kirk locked out per reviewer lockout rules).
- New orchestration logs: `.squad/orchestration-log/2026-03-07T21-40-29Z-scotty.md` (data assignment).
- Decisions consolidated: `.squad/decisions.md` now includes both McCoy reviews; inbox files deleted.

**Wave 1 fully approved (2026-03-07T22-00-03Z):**
- Scotty's data revision approved after addressing all five blocking gaps (freshness validators, audit snapshots, grocery lifecycle, reconciliation conflict states, AI plan history).
- 83 tests pass, all required spec elements verified.
- Decision merged into `.squad/decisions.md` from inbox.
- Data Wave 1 ready for integration.

## INF-01 Session Contract — 2026-03-07

### What changed
- Added a request-scoped session dependency that resolves caller identity plus active household once per request and caches it on the FastAPI request state.
- Replaced the `/api/v1/me` stub with an authenticated session bootstrap contract backed by that dependency; unauthenticated requests now return `401` instead of a fake anonymous success payload.
- Inventory routes now use the resolved request household for scope, reject mismatched client-supplied household identifiers with `403`, and keep `404` reserved for missing items inside the authorized household scope.

### Learnings
- A deterministic header seam is a practical bridge when real auth is not ready yet, as long as it is explicit (`X-Dev-*`) and backend-owned rather than implied by arbitrary business payload fields.
- Request-state caching lets multiple dependencies reuse the same resolved session context in one request without duplicating resolver work or route-specific parsing.
- Keeping wrong-household mismatches as `403` and missing items as `404` makes downstream API behavior much easier to reason about and test.

## INF-03 Inventory Persistence Swap — 2026-03-08

### What changed
- Replaced the process-local inventory placeholder with a SQLAlchemy-backed inventory store that persists inventory items, append-only adjustments, and mutation receipts.
- Kept the existing inventory router contract stable while moving duplicate replay, optimistic version conflict handling, archive/history reads, and correction linkage onto SQL transactions.
- Default app storage now uses durable SQLite under `apps/api/build/`, while API tests still inject isolated in-memory SQLite stores so route validation stays fast and deterministic.

### Learnings
- Storing a replayable receipt summary alongside the mutation receipt is a simple way to preserve duplicate-response fidelity without forcing replay code to rebuild responses from live mutable state.
- A temporary household shell row is a practical bridge between request-scoped session context and strict inventory foreign keys when auth/membership persistence is landing in adjacent phases.
- Keeping tests on injected in-memory SQLite preserves isolation while still exercising the same SQL-backed repository path the app uses in development.

## INF-04 Household-Scoped Inventory Authorization — 2026-03-08

### What changed
- Tightened SQL-backed correction lookup so a correction can only target an adjustment from the same household and inventory item, instead of loading adjustment IDs globally and then rejecting them afterward.
- Refreshed the inventory API regression suite so normal reads and mutations now exercise backend-owned household scope without query overrides, while explicit wrong-household overrides still prove `403` behavior.
- Added cross-household isolation coverage for detail, history, quantity adjustment, metadata update, move, archive, and correction flows to confirm foreign household item IDs stay invisible and correction chains remain auditable.

### Learnings
- In a household-scoped API, foreign resource identifiers should usually collapse to the same not-found path as absent identifiers once request authorization has already fixed the tenant scope.
- Correction-link validation is safer when the lookup itself is tenant-scoped; doing a global fetch and then comparing ownership leaks more than the API needs to reveal.

## INF-08 Inventory Trust Read Models — 2026-03-08

### What changed
- Extended inventory detail reads to include a history summary and the latest committed adjustment so clients can show current trust context, actor, and recent transitions without chaining extra reconstruction logic in the browser.
- Reworked inventory history reads into a paginated newest-first response that carries quantity, freshness, and location transition objects plus workflow references and correction-link metadata for each committed adjustment.
- Tightened tests so duplicate replay receipts and stale conflicts remain distinct mutation outcomes and do not inflate committed history totals.

### Learnings
- A trust-review API is easier for clients to consume when raw before/after fields are preserved for fidelity but mirrored by explicit transition objects for direct rendering.
- Mobile-friendly history views need both pagination and summary metadata; otherwise the client has to choose between overfetching or losing context like correction counts and latest actor.

## Aspire Local Startup Investigation — 2026-03-08

### What changed
- Wired `apps/apphost/AppHost.cs` to actually launch the FastAPI API and Next.js web app under Aspire, including local wait/reference behavior and a deterministic local household session seed for backend-owned auth bootstrap.
- Added a Next.js `/api/[...path]` proxy route so browser requests stay same-origin while the server forwards to the API and injects the explicit `X-Dev-*` headers required by the current backend session seam.
- Fixed `apps/api/pyproject.toml` setuptools discovery so Aspire's `pip install .` step stops failing on the sibling `migrations/` folder, and tightened `.gitignore` for Aspire/API/web local artifacts.

### Learnings
- The concrete local Aspire blocker was not Auth0 or shared-infra first; it was repo-local orchestration and packaging: an empty AppHost plus Python package discovery that broke Aspire's installer flow.
- Backend-only auth can still be honored locally if the frontend acts only as a server-side proxy for dev headers; the browser never needs direct Auth0 or fake identity configuration.
- Aspire's Python integration installs the app as a package by default, so repo layouts with extra top-level Python directories need explicit setuptools discovery rules even when direct `uvicorn --app-dir ...` development already works.

## Aspire Verification Follow-up — 2026-03-08

### What was verified
- Re-ran local startup from the current repo state with `aspire run --project .\apps\apphost\MealPlanner.AppHost.csproj` and confirmed the AppHost stays up with the dashboard on `https://localhost:17185`.
- Confirmed the web app serves locally on `http://127.0.0.1:3000`, the homepage renders, and the inventory page loads through the Aspire-launched frontend.
- Confirmed auth/session bootstrap works locally through the web proxy seam: `GET /api/v1/me` returned `200` from the browser-facing app with the expected Ashley/Local Household session payload, even though the API itself is bound to an Aspire-assigned internal port instead of fixed `:8000`.

### Learnings
- The current local-dev path does not require Terraform or shared-infra changes to prove bootstrap/auth behavior; those remain separate preview/prod concerns for real Auth0 provisioning and deployment wiring.
- For Aspire-local verification, the correct user-facing entry point is the web resource on port `3000`; probing `http://127.0.0.1:8000` directly is misleading because Aspire assigns the API its own endpoint and the Next proxy owns the browser contract.
- I did not publish or push anything during verification because the repository already contained unrelated in-progress changes from other teammates; local validation was completed without disturbing that shared work.

## AIPLAN-02 / AIPLAN-03 Backend Slice — 2026-03-08

### What changed
- Added a SQL-backed `PlannerService` plus `app/routers/planner.py` so the backend now owns household-scoped planner suggestion requests, request/result polling, draft open/read, slot edit/revert, slot regeneration entrypoints, confirmation, and confirmed-plan reads.
- Kept AI request/result rows, editable draft rows, and confirmed plan rows distinct while wiring idempotent request creation, active-request dedupe by household + period + slot scope, stale-warning inheritance, and confirmation idempotency.
- Refreshed the web planner client seam so it can parse backend-provided original-suggestion snapshots and poll the canonical request endpoint when a suggestion request is still generating.

### Learnings
- Using `ai_suggestion_result_id` + `slot_key` as the revert source is enough to restore original AI content without inventing a second draft-only copy of the same suggestion payload.
- Keeping both a period-scoped planner read and a request-ID polling read is a practical bridge between the current planner UI scaffold and the approved worker-centric AI lifecycle.
- Backend enforcement still matters even when the current UI does some local optimism: stale-warning acknowledgement and household path/session matching need to stay server-side or the trust boundary gets fuzzy again.

## AIPLAN-05 Confirmation Hardening — 2026-03-08

### What changed
- Added planner-side stale detection that compares completed suggestion requests against the worker grounding hash, so draft reads and confirmation can surface honest stale warnings after inventory/context drift instead of relying only on manually forced stale statuses.
- Kept confirmed plans protected while allowing new review cycles by leaving prior confirmed rows intact, bumping the newly confirmed plan version for the same household/period, and continuing to keep suggestion, draft, and confirmed records separate.
- Added durable `planner_events` storage plus a `plan_confirmed` payload written in the same confirmation transaction as the confirmed plan mutation and per-slot provenance history.

### Learnings
- Grounding hashes are useful beyond worker-side reuse: re-evaluating them during planner reads gives a lightweight stale-warning trigger without introducing a second planner-specific freshness ledger.
- If a downstream trigger matters to trust-sensitive workflows, persisting it in the same transaction as the authoritative mutation is safer than relying on an after-response callback that can be lost on retries or process interruption.
- Versioning a newly confirmed plan against the latest confirmed sibling for the same period is a simple way to preserve append-only confirmed history while still letting “latest confirmed” reads stay deterministic.

## AIPLAN-09 / AIPLAN-10 Handoff Hardening — 2026-03-08

### What changed
- Hardened the `plan_confirmed` event payload so the grocery handoff is explicit: downstream consumers now get a `grocery_refresh_trigger` contract that states the source is a confirmed plan, includes the confirmed plan/version identifiers, and carries the lifecycle correlation ID.
- Added planner lifecycle observability in both API and worker code so suggestion, draft-open, regeneration, confirmation, request reuse, completion, fallback, and unexpected failure paths all emit structured logs with correlation IDs.
- Introduced deterministic worker-side provider fixtures plus an explicit unexpected-failure regression so happy path, stale drift, fallback/manual guidance, and durable failure handling are all covered by repeatable tests.

### Learnings
- If a downstream seam must never consume draft or suggestion state, encoding the authoritative source status directly into the event payload is safer than depending on naming conventions alone.
- Reusing the originating AI request ID as the correlation ID gives API logs, worker logs, and downstream handoff payloads one diagnosable thread without adding extra persistence columns.
- Worker paths still need a durable failure state even when most provider problems degrade to fallback; otherwise true runtime faults disappear into crashes instead of becoming supportable request outcomes.

## GROC-02 / GROC-04 Backend Activation — 2026-03-08

### What changed
- Added a SQL-backed `GroceryService` plus `app/routers/grocery.py`, activating derive, current read, detail read, re-derive, add ad hoc, adjust line, remove line, and confirm routes under household-scoped backend session enforcement.
- Implemented authoritative grocery derivation from confirmed plans plus authoritative inventory with exact-name/exact-unit offsets, duplicate consolidation, remaining-to-buy calculation, incomplete-slot warnings, stale-draft detection, and durable list/version persistence.
- Wired re-derive so ad hoc lines and user quantity overrides survive forward into the new draft version, while confirmed lists remain immutable and spawn a fresh draft instead of being overwritten.

### Learnings
- A temporary ingredient-catalog seam keyed by `meal_reference_id` is a practical Wave 1 bridge when grocery rules are ready before the real recipe store exists, as long as missing ingredient data stays explicit and produces warnings instead of invented lines.
- Grocery idempotency is easiest to keep honest when the receipt stores the full mutation envelope, not just identifiers; duplicate retries can then replay the original accepted response even after the list changes again later.
- Stale-draft detection can stay lightweight by comparing the stored confirmed-plan version and an inventory snapshot hash at read time; the backend does not need a separate grocery event processor just to tell the client a draft has drifted.

## GROC-03 Refresh and Stale-Draft Orchestration — 2026-03-08

### What changed
- Extended `GroceryService` so it now consumes unpublished `plan_confirmed` events, auto-derives a draft when the confirmed period has no grocery list yet, refreshes an existing draft in place, and spawns a new draft instead of mutating a confirmed list.
- Tightened grocery stale detection so inventory drift is scoped only to ingredient names/units relevant to the confirmed plan, preventing unrelated household inventory edits from falsely staling a grocery draft.
- Wired planner confirmation and inventory mutation routes to trigger best-effort grocery orchestration immediately after the authoritative planner/inventory write succeeds, while keeping the durable planner event as the source of truth for refresh intent.

### Learnings
- Using the persisted `planner_events` row as the consumption source keeps planner→grocery refresh idempotent and diagnosable; the router can trigger processing without creating a second handoff contract.
- Relevant-inventory stale detection must be computed from the confirmed plan's ingredient surface, not the entire household inventory snapshot, or harmless pantry churn will create noisy stale drafts.
- Best-effort orchestration after the authoritative write is a safer MVP posture than coupling planner confirmation or inventory mutation success to a downstream grocery refresh side effect.

## GROC-08 / GROC-09 Handoff and Observability Hardening — 2026-03-08

### What changed
- Added explicit grocery handoff read-model seams: `grocery_list_version_id` now names the current/confirmed snapshot version, and each line now exposes a stable `grocery_line_id` backed by a persisted `stable_line_id` that survives logical carry-forward across re-derives.
- Hardened grocery observability so derivation, incomplete-slot warnings, stale detection, and confirmation all emit structured diagnostics with correlation IDs and list/version identifiers.
- Added a follow-on migration plus deterministic grocery diagnostics fixtures and regression coverage for confirmed-list identity stability, correlation-aware stale detection, and confirmation diagnostics.

### Learnings
- Downstream trip/reconciliation work should not infer the authoritative grocery snapshot from mutable list-row conventions; exposing the version identity explicitly keeps offline/trip seams honest before those milestones land.
- Stable line references need to be decoupled from per-version row primary keys; otherwise any re-derive/carry-forward implementation detail leaks into downstream contracts.
- In a multi-step derived workflow, correlation IDs are most useful when they flow through both success and warning diagnostics; incomplete-slot and stale-detection logs are much easier to support when they share the same thread as the triggering mutation.

## Seed Classification Audit — 2026-03-09

### What was verified
- Reviewed the untracked reviewer seed module (`apps/api/app/seeds/__init__.py`, `__main__.py`, `reviewer.py`) plus its two untracked API test files and traced repo references across app code, tests, docs, and squad logs.
- Confirmed the seed module is handwritten backend/test infrastructure rather than generated residue: it exposes a reusable API surface, a CLI entrypoint (`python -m app.seeds reviewer-reset`), deterministic smoke data, environment safety guards, and opt-in scenario overlays for Milestone 4 sync/trip review.
- Confirmed the tests are also intentional infrastructure, but `apps/api/tests/test_reviewer_seed.py` is not integration-clean yet: `python -m pytest tests/test_seeds.py tests/test_reviewer_seed.py -q` currently fails one legacy row-id sync-upload assertion because the backend now resolves sync line aggregates by stable `grocery_line_id`, matching the locked grocery-line identity decision.

### Learnings
- The reviewer seed package is aligned with the approved smoke-testing posture: one small deterministic baseline household plus opt-in edge scenarios is now encoded in code, not just planning notes.
- Clean integration still needs one explicit product-facing hook: the repo does not yet wire the seed CLI into startup/docs/scripts, so the next step is to document or script `python -m app.seeds reviewer-reset` for local reviewer bootstrap.
- Seed verification must track the stable-line contract, not mutable grocery row IDs; otherwise the seed suite will drift against the downstream offline/sync seam it is supposed to protect.

## Reviewer Seed Integration Cleanup — 2026-03-09

### What changed
- Replaced the stale reviewer sync-upload expectation with a single contract test that uses `grocery_line_id` as the line aggregate while still proving seeded payloads can carry the current row id as `grocery_list_item_id`.
- Added a root `npm run seed:api:reviewer-reset` helper and README usage note so the intentional reviewer reseed flow is discoverable from normal repo-facing entrypoints.
- Merged the reviewer seed classification inbox note into canonical decisions and cleared the inbox artifact.

### Learnings
- The reviewer reseed flow is worth exposing at the repo root because the seed package lives under `apps/api`, but the smoke workflow spans backend, web, and reviewer validation.
- Stable `grocery_line_id` is the sync contract; `grocery_list_item_id` remains a current-row hint, not an interchangeable aggregate identifier.
- Seed integration work is small but cross-team: when deterministic fixtures become part of a reviewer workflow, the contract, script, docs, and squad memory need to move together.
