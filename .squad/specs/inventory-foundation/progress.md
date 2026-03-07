# Inventory Foundation Progress

Date: 2026-03-08 (Phase A approved 2026-03-08T02-30Z, INF-08 completed 2026-03-08T03-00Z, INF-09 completed 2026-03-08T04-00Z, INF-10 completed 2026-03-08T05-15Z, INF-11 approved 2026-03-08T06-00Z)
Status: ✅ **MILESTONE 1 COMPLETE** — All 11 acceptance criteria verified and approved by Kirk
Spec: `.squad/specs/inventory-foundation/feature-spec.md`
Tasks: `.squad/specs/inventory-foundation/tasks.md`

## 1. Current summary

- **Milestone 1 (Household + Inventory Foundation) is APPROVED AND COMPLETE.**
- Kirk independently verified all 11 feature-spec acceptance criteria against the implementation code and ran the full evidence suite (111 backend tests, 16 web unit tests, lint/typecheck/build all green).
- The repo supports household-scoped authoritative inventory with idempotent mutation handling, append-only audit history, correction chaining, freshness-basis preservation, and one-primary-unit enforcement.
- Explicit follow-up work is documented in INF-11 completion notes (§18 below) — nothing is silently carried.

## 2. Ready-now queue

| ID | Task | Agent | Status | Notes |
| --- | --- | --- | --- | --- |
| INF-00 | Keep progress ledger current | Scribe | in_progress | Ledger now active; will update on every task transition. |
| INF-02 | Add SQL-backed household and inventory schema | Sulu | done | Households, memberships, items, adjustments, and receipts now SQL-backed with household-scoped idempotency and freshness enforcement. Two-household fixtures prove isolation. |
| INF-03 | Replace the in-memory inventory store with SQL-backed persistence | Scotty | done | Inventory mutations now commit durable item state, append-only adjustments, and household-scoped mutation receipts in one SQL transaction while preserving replay and stale-conflict behavior. |
| INF-04 | Enforce household-scoped authorization in inventory APIs | Scotty | done | Inventory routes now prove session-derived household scope on reads and mutations, with cross-household item access returning scoped 404s and correction targets staying household-scoped. |
| INF-05 | Rewire the web app to real household context | Uhura | done | Frontend now consumes backend-owned household scope from `/api/v1/me` session bootstrap; inventory flows no longer depend on client-selected household scope; explicit session states for loading, retrying, auth, and failure. |
| INF-06 | Add milestone regression evidence and observability | McCoy | done | Backend tests cover SQL receipts, duplicate replays, stale conflicts, household isolation, and mutation diagnostics. Web tests verify session bootstrap and inventory load/create/archive household wiring. All repo validation green (109 backend tests, web suite passed). |
| INF-10 | Add frontend flow and E2E coverage for edit/history/correction paths | McCoy | ready_now | INF-09 completed. McCoy can now add frontend flow and E2E coverage for the completed trust-review surface. |

## 3. Planned queue

| ID | Task | Agent | Status | Blocked by |
| --- | --- | --- | --- | --- |

| INF-07 | Phase A merge review and milestone cut-line check | Kirk | done | **APPROVED.** All five Phase A exit criteria verified independently. See §13 below. |
| INF-08 | Tighten inventory detail/history read models for client trust review | Scotty | done | Detail reads now include latest committed adjustment + history summary; history reads are paginated and surface quantity/freshness/location/correction/workflow context directly. |
| INF-09 | Add quantity, metadata, move, history, and correction UX flows | Uhura | done | Inventory review panel now renders quantity, metadata, move, history, and correction flows against backend detail/history read models with explicit freshness basis labels and conflict/retry messaging. |
| INF-11 | Final Milestone 1 acceptance review against the feature spec | Kirk | done | **APPROVED.** All 11 acceptance criteria verified independently. See §18 below. |

## 4. Risks and watchpoints

- Household context still depends on the explicit dev/test header seam, so Phase A must not regress into trusting client-owned household IDs in business payloads.
- Until membership persistence is wired into the session/auth path, the SQL inventory store may need to provision a household shell row on first write for a valid request-scoped household to satisfy foreign-key constraints.
- The existing repo checks currently pass, but the API test suite emits pre-existing `datetime.utcnow()` deprecation warnings in tests; those warnings are worth tracking but are not this planning task's scope.
- `npm run build:web` now succeeds with a non-blocking Next.js warning about multiple lockfiles (`package-lock.json` at repo root and `apps/web/package-lock.json`); this did not block INF-06 evidence but is worth cleanup later.

## 5. Baseline evidence

Validated against the current repo before this planning update:
- `npm run lint:web`
- `npm run typecheck:web`
- `npm run build:web`
- `python -m pytest apps/api/tests`

Result: passing baseline with existing warning noise from API tests.

## 6. Latest implementation evidence

- INF-01 validation passed on the targeted backend slice: session bootstrap and inventory route tests now cover authenticated success, `401` unauthenticated requests, `403` wrong-household access, and `404` missing inventory items.
- Full `apps/api/tests` suite passed after the session-contract change.
- Pre-existing API warning noise about `datetime.utcnow()` remains unchanged and was not expanded by INF-01.
- INF-02 validation passed on the relevant backend slice: `python -m pytest tests\models tests\schemas tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api`.
- Model coverage now includes deterministic two-household inventory fixtures, per-household replay receipt scope with a shared mutation ID, DB-level freshness-basis enforcement, and SQLite foreign-key enforcement for inventory-linked records.
- INF-03 validation passed on the relevant backend slice: `python -m pytest tests\models\test_inventory_models.py tests\schemas\test_inventory_schemas.py tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api`.
- The API inventory slice now exercises SQL-backed persistence end-to-end while keeping duplicate replay, stale version conflicts, negative-quantity guards, correction linkage, archive/history behavior, and two-household replay isolation intact.
- INF-04 validation passed on the relevant backend slice: `python -m pytest tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api`.
- Inventory API regressions now prove backend-owned household scope on normal reads and mutations, preserve `403` for explicit wrong-household overrides, return household-scoped `404` for foreign item IDs, and keep correction-target validation inside the same household/item audit chain.
- INF-06 validation passed on the full milestone slice: `npm run lint:web`, `npm run typecheck:web`, `npm run build:web`, `npm --prefix apps\web run test`, and `python -m pytest apps\api\tests`.
- Backend regression coverage now explicitly exercises SQL-backed mutation receipts, duplicate replays, stale-version conflicts, household isolation, session bootstrap, and structured accepted/duplicate/conflict/forbidden mutation diagnostics.
- Frontend regression coverage now proves `/api/v1/me` bootstrap mapping and the inventory load/create/archive request wiring against the authenticated household context.
- Structured mutation diagnostics are now emitted via backend logs with actor, household, item, client mutation ID, and version details for accepted, duplicate, conflicted, and forbidden inventory mutations. Metrics remain a later follow-on once instrumentation infrastructure exists.
- INF-08 validation passed on the backend inventory slice: `python -m pytest apps\api\tests\test_inventory.py` and `python -m pytest apps\api\tests`.
- Inventory detail reads now include a history summary plus the latest committed adjustment, so clients can render actor and recent trust context without stitching audit state together in the browser.
- Inventory history reads now return a paginated response ordered newest-first with committed-adjustment totals, correction counts, quantity/location/freshness transition objects, correction-link metadata, and workflow-reference metadata. Duplicate replay receipts and stale conflicts remain mutation-response concerns and do not inflate committed history totals.
- INF-09 validation passed on the web trust-review slice: `npm run lint:web`, `npm run typecheck:web`, `npm run build:web`, and `npm --prefix apps\web run test`.
- The inventory UI now loads backend detail/history read models for the selected item, renders append-only audit history with correction-link visibility, supports quantity increase/decrease/set plus metadata and move mutations with explicit freshness-basis labels, and records compensating corrections without implying destructive history rewrites.
- Web tests now cover metadata PATCH wiring plus detail/history trust-model mapping and freshness-label helpers so Phase B UI work keeps using Scotty's server-provided trust read models instead of browser reconstruction.

## 7. INF-01 Completion (2026-03-07)

- **Completed by:** Scotty
- **Deliverable:** `/api/v1/me` now resolves request-scoped caller identity and active household; inventory routes reject unauthenticated and wrong-household requests; write payloads no longer trust client-provided household IDs.
- **Decision:** Backend-authoritative household session contract via explicit dev/test header seam (X-Dev-User-Id, X-Dev-Active-Household-Id, etc.) until production Auth0 wiring is complete.
- **Evidence:** All targeted route and session tests passing; full API test suite passing.
- **Handoff:** INF-02 (Sulu) now ready to begin SQL schema and household/inventory table work on top of the locked request-scoped session contract.

## 8. INF-02 Completion (2026-03-08)

- **Completed by:** Sulu
- **Deliverable:** SQL-backed `households` and `household_memberships` tables; `inventory_items`, `inventory_adjustments`, and `mutation_receipts` now explicitly household-backed with foreign-key constraints; mutation receipts unique on `(household_id, client_mutation_id)` for household-scoped idempotency.
- **Decision:** Household and inventory schema enforces freshness-basis rules and non-negative quantity expectations at the database layer; deterministic two-household seed fixtures with intentional shared `client_mutation_id` prove isolation and idempotency scope at the schema level.
- **Evidence:** Deterministic two-household inventory fixtures validate household-scoped receipt idempotency; all model/schema tests passing; full API test suite passing; `python -m pytest tests\models tests\schemas tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api` confirmed.
- **Handoff:** INF-03 (Scotty) now ready to begin SQL-backed persistence implementation on top of locked request-scoped household session and concrete household/inventory schema.

## 9. INF-03 Completion (2026-03-08)

- **Completed by:** Scotty
- **Deliverable:** `apps/api/app/services/inventory_store.py` now uses SQLAlchemy-backed persistence instead of process memory; default app storage is durable SQLite, while tests still inject isolated in-memory SQLite stores for clean backend validation.
- **Decision:** Each accepted inventory mutation now commits the authoritative item change, append-only adjustment event, and per-household mutation receipt in one transaction; duplicate replays return the original receipt, while stale-version conflicts still surface as `409` rather than being mistaken for replays.
- **Evidence:** `python -m pytest tests\models\test_inventory_models.py tests\schemas\test_inventory_schemas.py tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api` passed; the deterministic two-household fixture coverage for shared mutation IDs remains green.
- **Handoff:** INF-04 (Scotty) can now enforce household-scoped authorization on top of a durable authoritative inventory store instead of the placeholder implementation.

## 10. INF-04 Completion (2026-03-08)

- **Completed by:** Scotty
- **Deliverable:** inventory reads and mutations now consistently run inside the resolved request household scope on top of the SQL-backed store, with foreign household item IDs hidden behind scoped `404` results and explicit household mismatch attempts still rejected as `403`.
- **Decision:** correction targets are now looked up inside the same household and inventory item scope, so invalid or foreign adjustment references stay `422` validation failures without leaking another household's adjustment existence.
- **Evidence:** `python -m pytest tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api` passed after adding cross-household read/history/mutation coverage and household-scoped correction-target validation.
- **Handoff:** INF-05 (Uhura) can consume the inventory API as backend-owned household context by default, without relying on client-selected household scope for normal inventory operations.

## 11. INF-05 Completion (2026-03-08)

- **Completed by:** Uhura
- **Deliverable:** Web SessionProvider now treats GET /api/v1/me as a backend-owned session bootstrap contract with explicit UI states for loading, retrying, unauthenticated, unauthorized, authenticated, and transport failure; inventory list/mutations no longer send household_id query parameters because household scope is now backend-owned.
- **Decision:** Web inventory flows read household scope from the authenticated session context instead of client-selected parameters. Create-item command still includes household ID for backend validation (may be removed in later cleanup). Bootstrap failures now surface as clear, recoverable UI feedback.
- **Evidence:** npm run lint:web, npm run typecheck:web, and npm run build:web all passed. Inventory list/create/archive flows remain intact with household scope read from session bootstrap instead of query parameters.
- **Handoff:** INF-06 (McCoy) can now add milestone regression evidence and observability on top of confirmed backend-owned household authorization and web session bootstrap.

## 12. INF-06 Completion (2026-03-08)

- **Completed by:** McCoy
- **Deliverable:** Added frontend regression tests for session bootstrap and inventory load/create/archive request wiring, plus backend observability coverage for accepted, duplicate, conflicted, and forbidden inventory mutations.
- **Decision:** Phase A may treat structured mutation logs plus durable SQL receipts as the accepted observability baseline until formal metrics infrastructure exists. Kirk can proceed to INF-07 with this evidence set.
- **Evidence:** `npm run lint:web`, `npm run typecheck:web`, `npm run build:web`, `npm --prefix apps\web run test`, and `python -m pytest apps\api\tests` all passed. Full API suite finished green at 109 passed with the pre-existing `datetime.utcnow()` warning noise unchanged.
- **Handoff:** INF-07 (Kirk) is now ready to perform the Phase A merge review and milestone cut-line check.

## 13. INF-07 Completion — Phase A Merge Review (2026-03-08)

- **Completed by:** Kirk
- **Verdict:** ✅ **APPROVED** — Phase A foundation is trustworthy for downstream Milestone 1 work.

### Exit criteria verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `/api/v1/me` no longer behaves as a placeholder-only contract | ✅ Pass | `session.py` resolves request-scoped caller identity and household from backend-owned headers via `get_request_session()`. `test_session.py` covers authenticated, 401 unauthenticated, and 403 household-membership failure. |
| 2 | Inventory no longer depends on the in-memory placeholder store | ✅ Pass | `inventory_store.py` uses SQLAlchemy engine, sessionmaker, and explicit `session.begin()` transaction blocks. All mutations (create, adjust, metadata, move, archive, correction) commit item state, adjustment event, and mutation receipt atomically. Default storage is file-backed SQLite. |
| 3 | Inventory routes are household-scoped by backend-owned session context | ✅ Pass | `get_request_household_id()` validates query-param overrides against the resolved session. `assert_household_access()` rejects mismatches with 403. Cross-household reads return scoped 404. Tests cover cross-household item read, history, adjustment, and correction-target isolation. |
| 4 | Web inventory flow works against the real household context | ✅ Pass | `SessionContext.tsx` bootstraps from `/api/v1/me` with loading, retrying, error, unauthenticated, unauthorized, and authenticated states. `inventory-api.ts` reads household ID from session, not client input. `InventoryView.tsx` gates all operations on authenticated session status. |
| 5 | Repo checks and milestone tests pass | ✅ Pass | Kirk independently verified: `python -m pytest apps/api/tests` — 109 passed; `npm run lint:web` — clean; `npm run typecheck:web` — clean; `npm run build:web` — succeeded; `npm --prefix apps/web run test` — 6/6 passed. |

### Cut-line check

- **Phase B boundary is clean.** INF-08 through INF-11 (detail/history read models, full mutation UX, frontend flow/E2E coverage, final acceptance) are correctly scoped as Phase B and do not leak into Phase A merge criteria.
- **No downstream grocery/trip/reconciliation work depends on placeholders.** Schema and model definitions exist for grocery, reconciliation, meal plan, and AI planning, but no routers or services are registered in `main.py` beyond session and inventory. There is no active code path from grocery/trip/reconciliation features to the old in-memory store or stub session.
- **Known non-blocking noise:** Pre-existing `datetime.utcnow()` deprecation warnings in model tests remain from schema definitions outside Phase A scope. Dual `package-lock.json` Next.js warning persists from repo structure. Neither blocks Phase A or downstream work.

### Immediate next step

INF-08 (Scotty) is now ready: tighten inventory detail/history read models for the client trust-review surface on top of the authoritative SQL-backed foundation.

## 14. INF-08 Completion (2026-03-08)

- **Completed by:** Scotty
- **Deliverable:** `GET /api/v1/inventory/{item_id}` now returns the current item plus a history summary and latest committed adjustment; `GET /api/v1/inventory/{item_id}/history` now returns a paginated newest-first read model with client-ready quantity, freshness, location, correction, workflow, and actor context.
- **Decision:** Inventory history pagination defaults to a mobile-safe window while still reporting total committed adjustments and correction counts. Read models now favor explicit transition/link objects over browser-side reconstruction.
- **Evidence:** `python -m pytest apps\api\tests\test_inventory.py` passed at 49 tests; `python -m pytest apps\api\tests` passed at 111 tests with only the pre-existing `datetime.utcnow()` warning noise.
- **Handoff:** INF-09 (Uhura) can render history review, correction chains, and latest-adjustment trust surfaces directly from the backend contract without rebuilding transitions in the client.

## 15. INF-09 Completion (2026-03-08)

- **Completed by:** Uhura
- **Deliverable:** Inventory now exposes a trust-review panel in the web app with quantity increase/decrease/set flows, metadata editing, location move, paginated history review, and compensating correction submission wired directly to the backend detail/history read models.
- **Decision:** Freshness basis is now rendered as known, estimated, or unknown everywhere the user reviews state or history, and reducing freshness precision requires explicit user intent in the metadata flow. Correction UX is intentionally append-only: users select a target event, record a balancing delta, and keep the original event visible in history.
- **Evidence:** `npm run lint:web`, `npm run typecheck:web`, `npm run build:web`, and `npm --prefix apps\web run test` all passed after the trust-review UI changes. Web unit coverage now exercises metadata PATCH wiring, backend detail/history mapping, and freshness-label formatting.
- **Handoff:** INF-10 (McCoy) is now ready to add richer flow/E2E coverage for the completed trust-review surface.

## 16. INF-10 Ready — Frontend Flow and E2E Coverage (2026-03-08)

- **Assigned to:** McCoy
- **Task:** Add frontend flow and E2E coverage for edit/history/correction paths
- **Dependency:** INF-09 completed ✅
- **Next:** McCoy can now build comprehensive E2E tests and frontend flow coverage demonstrating the trust-review surface working end-to-end across quantity adjustments, metadata changes, location moves, history review, and correction submission against backend read models.

## 17. INF-10 Completion — Frontend Flow and E2E Coverage (2026-03-08)

- **Completed by:** McCoy
- **Verdict:** ✅ **APPROVED** — the inventory trust-review surface now has automated frontend evidence for the full Milestone 1 loop.
- **Deliverable:** Playwright coverage for trusted inventory sequence (create → adjust → review history → correct → confirm audit chain) plus flows for history pagination, freshness precision-reduction, move-to-new-location, stale conflict recovery, and correction error messaging. Tightened inventory-api tests for quantity, move, and correction mutation wiring.
- **Evidence:** `npm run lint:web`, `npm run typecheck:web`, `npm run build:web`, `npm --prefix apps\web run test`, and `python -m pytest apps\api\tests` all passed. 16/16 web unit tests, 111 backend tests green.
- **Handoff:** INF-11 (Kirk) ready for final Milestone 1 acceptance review.

## 18. INF-11 Completion — Final Milestone 1 Acceptance Review (2026-03-08)

- **Completed by:** Kirk
- **Verdict:** ✅ **APPROVED** — Milestone 1 (Household + Inventory Foundation) is complete and satisfies the approved feature spec.

### Acceptance criteria verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Item creation supports pantry, fridge, freezer, leftovers with quantity, primary unit, and freshness basis | ✅ Pass | `StorageLocation` enum covers all 4 locations; `InventoryItemModel` has `quantity_on_hand`, `primary_unit`, `freshness_basis` with DB check constraints; `CreateItemCommand` schema accepts all fields. |
| 2 | Explicit mutation types for create, metadata update, increase, decrease, set, move, archive, correction | ✅ Pass | `MutationType` enum defines all 8 types; each exposed via distinct router endpoints; `InventoryStore` implements all 8 methods with atomic commit and adjustment events. |
| 3 | Client mutation ID accepted; duplicate retries create no duplicate stock changes or audit events | ✅ Pass | All 6 command schemas require `client_mutation_id`; `mutation_receipts` table with `(household_id, client_mutation_id)` unique constraint; `_get_receipt()` checks before applying; duplicates return cached receipt with `is_duplicate=True`. |
| 4 | Stale mutations distinguishable from duplicate retries with explicit conflict response | ✅ Pass | Duplicate check runs first (returns receipt); version check runs second (raises `InventoryConflictError` → 409 with `expected_version`/`current_version`); logging differentiates `duplicate` (INFO) vs `conflict` (WARNING). |
| 5 | Quantity-changing actions create audit records with actor, time, mutation type, reason code, before/after | ✅ Pass | `InventoryAdjustmentModel` captures `actor_id`, `created_at`, `mutation_type`, `reason_code`, `quantity_before`, `quantity_after`, `delta_quantity`; history endpoint returns all fields. |
| 6 | Corrections append new events referencing original; no rewriting or deleting history | ✅ Pass | `correction` mutation creates new adjustment with `corrects_adjustment_id` FK; self-correction blocked by DB constraint; no `.update()` or `.delete()` on adjustment records in `inventory_store.py`. |
| 7 | Freshness stored as known, estimated, or unknown with correct date semantics | ✅ Pass | DB check constraints enforce: `known` → `expiry_date` required, `estimated` → `estimated_expiry_date` required, `unknown` → no dates; schema `model_validator` mirrors rules. |
| 8 | Estimated freshness visibly labeled as estimated in read models and history | ✅ Pass | `FreshnessInfo.basis` always present in API schemas; history includes `freshness_transition` with before/after basis; frontend `formatFreshnessBasis()` renders "Estimated freshness" distinctly. |
| 9 | One primary stored unit per item; no silent cross-unit conversion | ✅ Pass | `primary_unit` is non-nullable `String(64)` set at creation; mutation schemas carry no unit field — all quantity changes use item's primary unit; no conversion logic exists. |
| 10 | Grocery, trip, planner, AI consume inventory through explicit boundaries | ✅ Pass | Only `session` and `inventory` routers registered in `main.py`; feature spec §13 documents boundaries; grocery/reconciliation/AI models hold reference-only FKs, no direct inventory writes. |
| 11 | Tests cover idempotent replay, stale conflict, correction chaining, freshness transitions, quantity/unit validation | ✅ Pass | Backend: idempotent replay, stale 409, correction chaining, freshness transitions, negative-quantity rejection. Frontend: 16 unit tests for API wiring and trust-model mapping. E2E: Playwright flows for create→adjust→history→correct→audit chain. |

### Independent evidence run

| Check | Result |
|-------|--------|
| `python -m pytest apps/api/tests` | 111 passed |
| `npm run lint:web` | Clean |
| `npm run typecheck:web` | Clean |
| `npm run build:web` | Succeeded |
| `npm --prefix apps/web run test` | 16/16 passed |

### Explicit follow-up work (not carried silently)

1. **Production Auth0 wiring.** Dev/test header seam (`X-Dev-*`) is still the active session posture. Auth0 JWT validation and real household membership resolution required before preview/production deployment.
2. **`datetime.utcnow()` deprecation warnings.** 134 warnings from model/test code. Housekeeping cleanup.
3. **Dual `package-lock.json` warning.** Next.js warns about lockfiles at both repo root and `apps/web/`. Non-blocking.
4. **Metrics and instrumentation.** Feature spec §15 calls for duplicate-replay rate, conflict rate, correction rate, and freshness-basis distribution metrics. Current posture is structured logs only.
5. **Batch mutation support.** Feature spec §8.4 describes batch behavior for sync uploads. Needed when offline sync queue is built.
6. **E2E tests against live API.** Current Playwright flows use mocked API responses. Full integration E2E deferred to deployment readiness.

### Milestone 1 declaration

**Milestone 1 (Household + Inventory Foundation) is APPROVED and COMPLETE.** The repo supports household-scoped authoritative inventory with idempotent mutation handling, append-only audit history, correction chaining, freshness-basis preservation, and one-primary-unit enforcement. All 11 acceptance criteria pass. Follow-up work is explicitly documented above rather than silently carried.

### Decision

Recorded at `.squad/decisions/inbox/kirk-inf-11-milestone-review.md`.
