# McCoy History

## Project Context
- **User:** Ashley Hollis
- **Project:** AI-Assisted Household Meal Planner
- **Stack:** REST API, modern web UI, AI assistance, inventory/product mapping workflows
- **Description:** Build a connected household meal planning platform spanning inventory, meal plans, substitutions, store mapping, shopping trips, and inventory updates after shopping or cooking.
- **Team casting:** Star Trek TOS first.

## Learnings
- Team initialized on 2026-03-07 for Ashley Hollis.
- Current focus is spec-first setup for the AI-assisted household meal planning platform.
- **Auth placement (2026-03-07):** Auth0 must NOT be installed in the Next.js frontend. Installing the Auth0 Next.js SDK prevents the app from starting on Azure Static Web Apps (SWA). Auth0 belongs exclusively on the FastAPI backend (API). The frontend authenticates through API-owned session endpoints. Four architecture docs currently imply or state frontend Auth0 SDK usage and require correction before implementation begins: `overview.md`, `frontend-offline-sync.md`, `api-worker-architecture.md`, `deployment-environments.md`. Review note written to `.squad/decisions/inbox/mccoy-auth-review.md`.
- **SWA constraint pattern:** Any SDK or package that takes over Next.js server startup (e.g., Auth0 Next.js SDK, certain middleware packages) must be treated as SWA-incompatible until verified. Frontend auth on SWA must use API-proxy patterns or SWA's built-in auth layer, not third-party SDK-owned OIDC flows.
- **Wave 1 backend review (2026-03-07):** Reviewed Scotty's Wave 1 backend slice (inventory foundation + session seam). 29/29 tests pass. The `GET /api/v1/me` seam shape is correct and auth-direction-compliant. The inventory mutation model, idempotency, append-only history, and correction chains are solid. REJECTED on three blocking gaps: (1) AC#4 stale-mutation concurrency conflict entirely unimplemented — commands accept no `version` field and the store has no conflict-detection path; (2) AC#11 missing test coverage for stale conflict, freshness basis transitions, and negative-quantity validation; (3) §12.2 negative-quantity prohibition not enforced — `decrease_quantity` can commit a sub-zero balance. Scotty is locked out of authoring the next revision per reviewer lockout rules. Review written to `.squad/decisions/inbox/mccoy-backend-wave1-review.md`.
- **Inventory spec enforcement pattern:** The inventory-foundation spec requires optimistic concurrency tokens in command shapes (not just on the item record) so stale conflicts can be detected at mutation time. Without a `version` field in the command, the API cannot distinguish a duplicate retry from a stale write — these are two different outcomes with different required responses. This must be checked in every future inventory mutation review.
- **Wave 1 data review (2026-03-07):** Passing model/schema tests can still hide readiness gaps if the state machine and audit fields are underspecified. For this project, always verify grocery `draft`/`confirmed` lifecycle fields, reconciliation apply conflict/failure states plus leftovers continuation mapping, AI plan confirmation idempotency/history completeness, and inventory freshness/history before/after traceability — not just basic table creation or enum parsing.
- **Wave 1 frontend review (2026-03-07):** Uhura kept the Auth0/SWA direction intact in `apps/web`: no Auth0 SDK dependency, and session bootstraps via `GET /api/v1/me`. However, the slice is REJECTED because the frontend contracts and UI states diverge from the approved specs: inventory mutations still omit a concurrency/version token, planner lacks the required request/edit/manual flows and slot-failure handling, and grocery mutations/states omit idempotency and explicit derivation lifecycle states. Review written to `.squad/decisions/inbox/mccoy-frontend-wave1-review.md`.
- **Wave 1 backend re-review (2026-03-07):** Kirk fixed the three original blockers: inventory mutations now accept `version` tokens and return explicit stale conflicts, negative quantity writes are rejected, and backend tests now cover stale conflict, freshness-basis transition, and negative-quantity validation. However, the slice remains REJECTED because idempotency receipts in `apps/api/app/services/inventory_store.py` are keyed only by `client_mutation_id`, not by household plus client mutation ID as required by the spec. A replay in household B can be incorrectly treated as a duplicate of household A, returning the wrong item/receipt and silently skipping the second household write. Next owner must be someone other than Kirk; route to Bones.

## Team Updates (2026-03-07)

**Scribe consolidation (Wave 1 data foundation + backend re-review, 2026-03-07T21:40:29Z):**
- McCoy completed Wave 1 data foundation review; identified 5 blocking gaps (inventory freshness, grocery lifecycle, reconciliation states, AI plan audit, test coverage).
- McCoy completed Wave 1 backend re-review; identified 1 critical blocker (idempotency scope causes cross-household replay corruption).
- Two new orchestration logs created:
  - `.squad/orchestration-log/2026-03-07T21-34-42Z-mccoy.md` — data foundation review, 5 gaps, rejection
  - `.squad/orchestration-log/2026-03-07T21-40-29Z-scotty.md` — Scotty assigned to revise data foundation
- New session log at `.squad/log/2026-03-07T21-40-29Z-data-rejection.md` documenting data foundation rejection.
- Both McCoy reviews merged into `.squad/decisions.md` from inbox; inbox files deleted.
- Next owners: Scotty (data foundation), Bones (backend idempotency fix per reviewer lockout).

**Scribe consolidation:**
- Three backend decisions merged into `.squad/decisions.md` from inbox (Scotty decisions + McCoy review).
- Orchestration log created at `.squad/orchestration-log/2026-03-07T21-34-42Z-mccoy.md` documenting review rejection and blocking gaps.
- Session log summarizing Wave 1 frontend + backend review outcomes written to `.squad/log/2026-03-07T21-34-42Z-frontend-wave1-review.md`.
- Decision inbox merged and deleted; no entries older than 30 days for archival at this time.
- Next owner for backend revision: Bones or Kirk (Scotty locked out per reviewer lockout rules).

**Scribe update 2026-03-07T11:38:29Z:**
- McCoy completed Wave 1 frontend review, identified 5 blocking gaps in inventory contracts, planner workflow, error handling, and grocery mutations.
- New orchestration logs created:
  - `.squad/orchestration-log/2026-03-07T11-38-29Z-mccoy.md` — frontend review completion, 5 gaps, rejection
  - `.squad/orchestration-log/2026-03-07T11-38-29Z-kirk.md` — launched to own frontend revision, assign non-Uhura owner
- Session log at `.squad/log/2026-03-07T11-38-29Z-frontend-rejection.md` documenting final rejection.
- McCoy frontend review decision merged into `.squad/decisions.md` from inbox.
- Kirk assigned to designate non-Uhura frontend owner for revision (Uhura locked out per reviewer lockout rules).
- **Wave 1 backend final review (2026-03-07):** Reviewed Sulu's backend revision. 35/35 tests pass (including 3 health/session tests). Verified that idempotency is now correctly scoped by (household_id, client_mutation_id) and that regression tests explicitly cover cross-household collision scenarios for create, metadata, and correction flows. Previous blockers (stale checks, negative quantity, auth seam) remain fixed and covered. APPROVED. Review written to .squad/decisions/inbox/mccoy-backend-wave1-final-review.md.
- **New Skill (2026-03-07):** Documented idempotency-scope pattern in .squad/skills/idempotency/SKILL.md after correcting the cross-household collision bug.
- **Wave 1 data re-review (2026-03-07):** Reviewed Scotty's data revision. 83/83 tests pass. Confirmed freshness basis rules, audit snapshotting, grocery lifecycle states, reconciliation failure modes, and meal plan confirmation history. APPROVED. Review written to .squad/decisions/inbox/mccoy-data-wave1-rereview.md.
- **New Skill (2026-03-07):** Documented audit-snapshot pattern in .squad/skills/audit-snapshot/SKILL.md to standardize history fidelity.
- **Wave 1 frontend re-review (2026-03-07):** Reviewed Kirk's frontend revision. Validated that inventory mutations now correctly use optimistic concurrency (version passing + 409 handling), planner flows implement the required 3-state boundary and error handling, grocery mutations are idempotent and show lifecycle state, and auth is strictly API-owned. Lint/build/typecheck passed. APPROVED. Review written to .squad/decisions/inbox/mccoy-frontend-wave1-rereview.md.
- **New Skill (2026-03-07):** Documented optimistic concurrency UI pattern in .squad/skills/optimistic-concurrency-ui/SKILL.md.

**Wave 1 fully approved (2026-03-07T22-00-03Z):**
- McCoy completed all three Wave 1 approvals: backend (Sulu, idempotency scoped correctly), data (Scotty, freshness/lifecycle/reconciliation contracts complete), frontend (Kirk, concurrency/planner/grocery/auth contracts complete).
- All revisions verified and approved by McCoy.
- Decisions consolidated by Scribe: all three approval reviews merged into `.squad/decisions.md` from inbox.
- Inbox cleared and consolidated; three orchestration logs created documenting each approval.
- Session log marks Wave 1 fully approved; next phase is integration and Wave 2 planning.
- **INF-06 verification (2026-03-08):** Approved the inventory-foundation milestone regression slice after adding backend observability assertions for accepted/duplicate/conflict/forbidden mutations and frontend regression tests for session bootstrap plus inventory load/create/archive household wiring. Required evidence all passed (`npm run lint:web`, `npm run typecheck:web`, `npm run build:web`, `npm --prefix apps\web run test`, and `python -m pytest apps/api/tests`). Keep treating structured mutation logs plus durable SQL receipts as the minimum acceptable observability baseline until metrics infrastructure exists; non-blocking warnings remain the pre-existing `datetime.utcnow()` pytest noise and a Next.js multiple-lockfile build warning.
