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
