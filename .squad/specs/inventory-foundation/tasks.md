# Inventory Foundation — Execution Tasks

Date: 2026-03-07
Milestone: 1 — Household context and authoritative inventory foundation
Status: Execution-ready
Spec: `.squad/specs/inventory-foundation/feature-spec.md`

## 1. Current implementation baseline

Wave 1 is already approved and present in the repo:
- `apps/api/app/routers/inventory.py` already exposes explicit inventory mutation and history routes.
- `apps/api/app/services/inventory_store.py` is still an in-memory placeholder, not authoritative persistence.
- `apps/api/app/routers/session.py` still returns a stub unauthenticated `/api/v1/me` response.
- `apps/web/app/inventory/_components/InventoryView.tsx` can load, create, and archive inventory items, but it still depends on the stub session/auth posture and does not yet expose the full trust-review surface.

## 2. Implementation posture

The smallest trustworthy next wave is **not** broader UI breadth. It is:
1. real household-scoped session context,
2. SQL-backed authoritative inventory persistence,
3. household-safe authorization on inventory routes,
4. web wiring against the real household context,
5. regression evidence that proves replay safety and household isolation.

Do **not** start grocery, trip, or reconciliation work on top of the current in-memory/session-stub foundation.

## 3. Execution order

### Phase A — Start immediately
This is the next implementation wave that can begin now.

| ID | Task | Agent | Depends on | Ready now |
| --- | --- | --- | --- | --- |
| INF-00 | Keep progress ledger current | Scribe | None | Yes |
| INF-01 | Lock household session and request-scope contract | Scotty | Milestone 0 auth/bootstrap seam | Yes |
| INF-02 | Add SQL-backed household and inventory schema | Sulu | INF-01 | No |
| INF-03 | Replace the in-memory inventory store with SQL-backed persistence | Scotty | INF-02 | No |
| INF-04 | Enforce household-scoped authorization in inventory APIs | Scotty | INF-01, INF-03 | No |
| INF-05 | Rewire the web app to real household context | Uhura | INF-04 | No |
| INF-06 | Add milestone regression evidence and observability | McCoy | INF-03, INF-04, INF-05 | No |
| INF-07 | Phase A merge review and milestone cut-line check | Kirk | INF-06 | No |

### Phase B — Start only after Phase A exit criteria pass
These tasks complete the Milestone 1 trust surface on top of the authoritative foundation.

| ID | Task | Agent | Depends on |
| --- | --- | --- | --- |
| INF-08 | Tighten inventory detail/history read models for client trust review | Scotty | INF-07 |
| INF-09 | Add quantity, metadata, move, history, and correction UX flows | Uhura | INF-08 |
| INF-10 | Add frontend flow and E2E coverage for edit/history/correction paths | McCoy | INF-09 |
| INF-11 | Final Milestone 1 acceptance review against the feature spec | Kirk | INF-10 |

## 4. Task details

### INF-00 — Keep progress ledger current
**Agent:** Scribe  
**Depends on:** None  
**Goal:** keep `.squad/specs/inventory-foundation/progress.md` accurate while implementation runs.

**Work**
- Update task status, owner, and notes whenever a Milestone 1 task starts, finishes, or blocks.
- Record the latest evidence links or command outputs in human terms only.
- Keep the “ready now” task list honest so Ralph and Kirk can route work without rereading the whole spec.

**Done when**
- Progress stays current through every Phase A and Phase B handoff.

---

### INF-01 — Lock household session and request-scope contract
**Agent:** Scotty  
**Depends on:** Milestone 0 auth/bootstrap seam  
**Goal:** replace the current session stub with a real request-scoped contract the API can trust.

**Work**
- Turn `GET /api/v1/me` from a stub-only seam into a real session bootstrap contract that returns authenticated household membership context for the active user, with a deterministic dev/test seam if production auth wiring is still being finalized.
- Introduce a backend request dependency that resolves caller identity and active household once per request.
- Stop treating client-supplied `household_id` as the source of truth for inventory writes. If a temporary dev override is still needed, keep it explicit and test-only.
- Define and test the expected `401` / `403` / `404` behavior for unauthenticated access, wrong-household access, and missing inventory items.

**Repo touchpoints**
- `apps/api/app/routers/session.py`
- `apps/api/app/models/session.py`
- `apps/api/tests/test_session.py`
- any new API auth/session dependency modules required by the implementation

**Done when**
- The API can resolve household context from the session seam instead of trusting arbitrary client household input.
- Session tests cover authenticated, unauthenticated, and household-membership edge cases.

---

### INF-02 — Add SQL-backed household and inventory schema
**Agent:** Sulu  
**Depends on:** INF-01  
**Goal:** create the persistent schema Milestone 1 needs for authoritative household-scoped inventory.

**Work**
- Add SQLAlchemy-backed schema and migrations for households, household memberships, inventory items, inventory adjustments, and mutation receipts.
- Preserve the approved feature-spec rules: one primary unit per item, freshness basis (`known | estimated | unknown`), append-only adjustments, correction linkage, and per-household idempotency receipts.
- Add deterministic seed/fixture data for at least two households so isolation tests can prove one household cannot see or mutate another household’s inventory.
- Keep the schema aligned with the existing API contract wherever practical so the current router surface does not churn unnecessarily.

**Repo touchpoints**
- `apps/api/app/models/`
- migration or schema artifact location already used by the repo
- API test fixtures and seed helpers

**Done when**
- The repo can persist Milestone 1 inventory state beyond process memory.
- A test fixture can stand up two households with independent inventory histories.

---

### INF-03 — Replace the in-memory inventory store with SQL-backed persistence
**Agent:** Scotty  
**Depends on:** INF-02  
**Goal:** make the existing inventory route surface authoritative and durable.

**Work**
- Replace the placeholder implementation in `apps/api/app/services/inventory_store.py` with a database-backed repository/service.
- Persist inventory item balance changes, adjustment events, and mutation receipts in one transaction.
- Preserve explicit mutation behavior already exposed by the router: create, metadata update, increase, decrease, set quantity, move, archive, correction, and history.
- Preserve optimistic version conflict handling and duplicate replay behavior so the current route contracts remain trustworthy for offline-safe clients.

**Repo touchpoints**
- `apps/api/app/services/inventory_store.py`
- `apps/api/app/routers/inventory.py`
- SQLAlchemy model/repository modules added in INF-02
- inventory-related API tests

**Done when**
- Inventory state survives process restart.
- Duplicate retries do not create duplicate stock changes.
- Stale version conflicts still surface distinctly from duplicate replays.

---

### INF-04 — Enforce household-scoped authorization in inventory APIs
**Agent:** Scotty  
**Depends on:** INF-01, INF-03  
**Goal:** ensure the existing inventory contracts are safe for shared-household use.

**Work**
- Make list, detail, history, and mutation routes derive household scope from the resolved session context.
- Ensure one household cannot read, correct, archive, or mutate another household’s inventory or adjustment history.
- Keep conflict errors, validation errors, and authorization errors clearly distinct in API responses.
- Validate that history and correction chains remain household-scoped and auditable after the auth/persistence swap.

**Repo touchpoints**
- `apps/api/app/routers/inventory.py`
- session/auth dependency modules introduced in INF-01
- household-aware repository queries introduced in INF-03
- `apps/api/tests/test_inventory.py`

**Done when**
- Inventory APIs are household-safe by default.
- Cross-household access attempts are rejected and covered by tests.

---

### INF-05 — Rewire the web app to real household context
**Agent:** Uhura  
**Depends on:** INF-04  
**Goal:** make the web inventory flow consume the authenticated household context instead of the stub path.

**Work**
- Update the session bootstrap/provider flow so the web app consumes the real `/api/v1/me` result shape and handles loading, unauthenticated, unauthorized, and retry states clearly.
- Keep the current inventory list/create/archive flow working against the persisted API contract.
- Remove any client assumption that household scope is chosen outside the backend-owned session context.
- Preserve trust-relevant UX states already present: empty, loading, error, and stale/conflict feedback.

**Repo touchpoints**
- `apps/web/app/_providers/SessionContext.tsx`
- `apps/web/app/_lib/session.ts`
- `apps/web/app/_lib/inventory-api.ts`
- `apps/web/app/inventory/_components/InventoryView.tsx`
- related inventory/session UI tests

**Done when**
- A signed-in user can load and mutate only their household inventory from the web app.
- Signed-out and failed-bootstrap states remain understandable and recoverable.

---

### INF-06 — Add milestone regression evidence and observability
**Agent:** McCoy  
**Depends on:** INF-03, INF-04, INF-05  
**Goal:** prove the new authoritative foundation is safe before downstream milestones build on it.

**Work**
- Extend backend tests to cover SQL-backed mutation receipts, duplicate replay, stale version conflict, household isolation, and session bootstrap.
- Add or tighten frontend flow coverage for session bootstrap and inventory load/create/archive against the authenticated household context.
- Verify logs and diagnostics cover accepted, duplicate, conflicted, and forbidden inventory mutations with enough detail for debugging.
- Re-run the existing repo checks and capture the milestone evidence in progress updates.

**Required evidence**
- `npm run lint:web`
- `npm run typecheck:web`
- `npm run build:web`
- `python -m pytest apps/api/tests`

**Done when**
- The authoritative household-scoped inventory slice has automated evidence strong enough for Milestone 1 downstream work.

---

### INF-07 — Phase A merge review and milestone cut-line check
**Agent:** Kirk  
**Depends on:** INF-06  
**Goal:** keep Milestone 1 disciplined and prevent downstream work from building on placeholders again.

**Work**
- Review whether Phase A fully replaced the session stub and in-memory inventory foundation.
- Confirm grocery, trip, and reconciliation work are not being asked to depend on placeholder household or persistence behavior.
- Validate that open follow-up work is correctly pushed into Phase B instead of diluting Phase A merge criteria.

**Done when**
- Kirk signs off that the repo has a trustworthy Milestone 1 foundation for downstream specs and implementation.

---

### INF-08 — Tighten inventory detail/history read models for client trust review
**Agent:** Scotty  
**Depends on:** INF-07  
**Goal:** expose client-ready trust views on top of the authoritative store.

**Work**
- Refine detail and history read models so clients can show actor, before/after quantity, freshness transitions, location transitions, correction links, and workflow references without reconstructing them in the browser.
- Add pagination or summary structure if needed so mobile inventory history does not become payload-heavy.
- Preserve clear distinction between duplicate replay receipts, stale conflicts, and committed adjustments.

**Done when**
- The API serves detail/history shapes the web UI can render directly for trust review.

---

### INF-09 — Add quantity, metadata, move, history, and correction UX flows
**Agent:** Uhura  
**Depends on:** INF-08  
**Goal:** complete the user-facing Milestone 1 trust surface.

**Work**
- Add UI flows for quantity increase/decrease/set, metadata edit, move location, history review, and compensating correction.
- Keep freshness basis visibly labeled as known, estimated, or unknown everywhere it matters.
- Make conflict and retry states understandable on phone-sized and desktop layouts.
- Avoid any UI that implies destructive history rewrites.

**Done when**
- A user can inspect and correct inventory state from the web app without losing auditability.

---

### INF-10 — Add frontend flow and E2E coverage for edit/history/correction paths
**Agent:** McCoy  
**Depends on:** INF-09  
**Goal:** verify the full Milestone 1 trust loop, not just the backend transaction layer.

**Work**
- Add component/flow coverage for quantity edits, freshness changes, move flows, history review, and correction submission.
- Add E2E coverage for a trusted inventory sequence: create item -> adjust quantity -> review history -> apply correction -> confirm audit chain remains understandable.
- Ensure both success and conflict/error paths are exercised.

**Done when**
- Milestone 1 user-visible inventory trust flows have automated evidence, not just backend route tests.

---

### INF-11 — Final Milestone 1 acceptance review against the feature spec
**Agent:** Kirk  
**Depends on:** INF-10  
**Goal:** confirm Milestone 1 satisfies the approved feature spec before the team moves on.

**Work**
- Review completed implementation against the accepted inventory-foundation criteria.
- Confirm the repo now supports household-scoped authoritative inventory, idempotent mutation handling, audit history, correction chaining, freshness-basis preservation, and one-primary-unit enforcement.
- Identify any remaining gaps as explicit follow-up work instead of silent carryover.

**Done when**
- Milestone 1 can be declared complete without relying on undocumented assumptions.

## 5. Phase A exit criteria

Phase A is complete only when all of the following are true:
- `/api/v1/me` no longer behaves as a placeholder-only contract for core Milestone 1 flows.
- Inventory no longer depends on the in-memory placeholder store.
- Inventory routes are household-scoped by backend-owned session context.
- The web inventory flow works against the real household context.
- Repo checks and milestone tests pass with evidence captured in progress.

## 6. Hand-off note for the squad

Start with **INF-01** and **INF-00** immediately.  
Do not open Phase B UI-breadth work until **INF-07** confirms the authoritative household-scoped foundation is actually in place.
