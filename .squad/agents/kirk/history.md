# Kirk History

## Project Context
- **User:** Ashley Hollis
- **Project:** AI-Assisted Household Meal Planner
- **Stack:** REST API, modern web UI, AI assistance, inventory/product mapping workflows
- **Description:** Build a connected household meal planning platform spanning inventory, meal plans, substitutions, store mapping, shopping trips, and inventory updates after shopping or cooking.
- **Team casting:** Star Trek TOS first.

## Learnings
- Team initialized on 2026-03-07 for Ashley Hollis.
- Current focus is spec-first setup for the AI-assisted household meal planning platform.
- McCoy's auth review identified 7 locations across 4 architecture docs where frontend Auth0 SDK usage was implied. Spec revised all docs. Kirk independently verified all 7 fixes are present and correct. Decision recorded at `.squad/decisions/inbox/kirk-backend-auth0-api-only.md`.
- Auth0 is locked as backend-only (API). No `@auth0/nextjs-auth0` or equivalent in `apps/web`. Frontend authenticates via API endpoints (`GET /api/v1/me`). This is a platform constraint — Auth0 Next.js SDK breaks Azure Static Web Apps startup.
- When McCoy rejects docs, the revision path should be owned, verified, and closed with a Kirk decision record so the team has a single traceable acceptance point.
- Inventory Wave 1 now uses optional per-command item versions for optimistic concurrency on existing-item mutations; duplicate replays remain idempotent receipts, while stale version mismatches surface as explicit 409 conflicts.
- Existing-item metadata, move, archive, and correction mutations must also advance the item version, otherwise freshness/location conflicts cannot be detected reliably.
- **Wave 1 frontend revision ownership (2026-03-07T11:38:29Z):** McCoy rejected Uhura's Wave 1 frontend on 5 blocking gaps (inventory version contract, planner workflow, planner errors, grocery idempotency, grocery state visibility). Uhura is locked out. Kirk launched to own frontend revision and designate non-Uhura author. Orchestration logs created at `.squad/orchestration-log/2026-03-07T11-38-29Z-mccoy.md` and `.squad/orchestration-log/2026-03-07T11-38-29Z-kirk.md`. Decision merged to `.squad/decisions.md`.
- Frontend session bootstrap must normalize the backend `GET /api/v1/me` wrapper shape and fail closed to explicit signed-out UI; otherwise the web app can hang forever waiting for a user object that never arrives.
- Planner and grocery frontend contracts benefit from local UI state machines even before full backend endpoints exist, but confirmed-plan authority and Auth0 ownership still stay server-side; the web app should expose manual fallback and explicit lifecycle messaging rather than pretending the browser is authoritative.
- **Wave 1 post-review status (2026-03-07):** McCoy rejected all three Wave 1 slices (backend, frontend, data) with specific blocking gaps. Backend gap: idempotency receipts scoped globally instead of by household + client_id, causing cross-household corruption. Frontend gaps: missing inventory version contract, planner workflow, grocery idempotency, state visibility. Data gaps: missing state machines, audit contracts, concurrency models for inventory/grocery/reconciliation. Bones assigned to fix idempotency scoping. Spec-first discipline validated: all gaps are spec-driven and mechanically addressable.
- **Milestone 1 (Household + Inventory Foundation) recommendation (2026-03-07):** Next MVP wave should be Inventory Foundation implementation, running in parallel with Wave 1 revision completion. Inventory Foundation spec is approved and ready. Household authorization model must be scoped MVP-only (primary-planner role, no fine-grained hierarchy). Grocery Derivation deferred to Wave 3 (post-Planner finalization). Decision recorded at `.squad/decisions/inbox/kirk-next-wave.md`. Spec review gate established: McCoy to approve specs before implementation begins.

## Team Updates (2026-03-07)

**Wave 1 fully approved (2026-03-07T22-00-03Z):**
- Approved all three Wave 1 revisions: backend (Sulu), data (Scotty), frontend (Kirk).
- All revisions addressed blocking gaps and passed reviewer verification.
- Decisions merged into `.squad/decisions.md`; inbox cleaned.
- Next phase: integration and Wave 2 planning.

## INF-07 Phase A Merge Review (2026-03-08)

- **Phase A approved.** All five exit criteria verified independently by Kirk: session contract is backend-owned, inventory store is SQL-backed with transactional mutations, routes are household-scoped via session dependency, web app bootstraps from real `/api/v1/me`, and all repo checks pass green.
- Cut-line is clean: Phase B tasks (INF-08–INF-11) stay scoped as follow-on breadth work; no grocery/trip/reconciliation code depends on placeholders.
- Decision recorded at `.squad/decisions/inbox/kirk-inf-07-phase-a-review.md`.
- The dev/test header seam (`X-Dev-*`) is an accepted transitional posture until production Auth0 wiring completes; it is not a Phase A gap.
- When reviewing milestone gates, independently running the full evidence suite (pytest, lint, typecheck, build, web test) before signing off proved essential — progress ledger claims alone are insufficient for a merge decision.
- Next immediate step: INF-08 (Scotty) to tighten inventory detail/history read models for the client trust-review surface.

## INF-11 Milestone 1 Final Acceptance (2026-03-08)

- **Milestone 1 APPROVED.** All 11 feature-spec acceptance criteria independently verified against implementation code. Full evidence suite run independently: 111 backend tests, 16 web unit tests, lint/typecheck/build all green.
- Verified criteria include: household-scoped authoritative inventory (SQL-backed, backend-owned session), idempotent mutation handling (per-household receipts with `_get_receipt()` checked before every mutation), append-only audit history with actor/timestamp/reason/before-after, correction chaining via `corrects_adjustment_id` FK, freshness-basis enforcement at DB and schema level, and one-primary-unit enforcement with no cross-unit conversion logic.
- Six explicit follow-ups documented as non-silent carryover: Auth0 production wiring, `datetime.utcnow()` deprecation, dual lockfile cleanup, metrics/instrumentation, batch mutation support, and live-API E2E tests.
- Decision recorded at `.squad/decisions/inbox/kirk-inf-11-milestone-review.md`.
- Running the evidence suite independently before signing off continues to prove essential — progress ledger claims alone are never sufficient for a milestone gate.
- Milestone completion means downstream milestones (Meal Planning, Grocery/Trip, Reconciliation) can safely build on this foundation without placeholder dependencies.

## Local Startup + Auth + Git Triage (2026-03-08)

- **Root cause of Aspire load failure:** `AppHost.cs` registers zero resources — the Aspire dashboard starts but has nothing to orchestrate. This is Milestone 0 foundation work that was scaffolded but never completed.
- **Auth blocker for local dev:** API uses `X-Dev-*` headers for session resolution (known transitional posture). No browser-usable auth bridge exists, so the web app always gets 401 on `/api/v1/me`. Need a local auto-session for dev mode.
- **.gitignore was broken:** All directory patterns used Windows backslashes instead of forward slashes. This caused build artifacts (bin/, obj/) and node_modules to leak into git tracking. Fixed and committed — removed ~35K accidentally tracked files.
- **22 commits unpushed on main:** The entire Milestone 1 implementation and Milestone 2 kickoff was local-only. Critical data loss risk. Ashley must push immediately.
- **shared-infra gaps for auth:** No GitHub OIDC federated credential for meal-planner-v02, no meal-planner Key Vault entries, no Auth0 Terraform module. All must be added before production auth or preview environments can work.
- **Terraform in this repo is skeleton-only:** Just a resource group data source. Needs real resource declarations before any deploy workflow can function.
- `.aspire/` directory was not gitignored — now fixed.
- Decision record at `.squad/decisions/inbox/kirk-local-startup-triage.md`.
- **Key learning:** Milestone 0 "scaffolding" was treated as done when directory structure existed, but the actual wiring (AppHost resource registration, auth bridge, Terraform resources) was never completed. Foundation gates need to verify that services actually start and connect, not just that files exist.
- **Git publish readiness follow-up:** API build outputs were still tracked (`apps/api/build/`, `apps/api/meal_planner_api.egg-info/`). Root `.gitignore` now covers egg-info and Playwright outputs, tracked generated files were removed from version control, and publish remains intentionally blocked until local Aspire verification is complete. Decision recorded at `.squad/decisions/inbox/kirk-git-publish-readiness.md`.
- **Publish-history repair learning (2026-03-08):** When a feature branch inherits unpublished large-file history, the safest recovery path is to back up the contaminated head, branch fresh from `origin/main`, and replay the verified tree state in clean commits. That preserves source work without force-rewriting the original local branch or reintroducing tracked dependency artifacts.

## AIPLAN-12 Milestone 2 Final Acceptance (2026-03-08)

- **Milestone 2 APPROVED.** All 14 feature-spec acceptance criteria independently verified against implementation code. Full evidence suite run independently: 144 API tests, 9 worker tests, 26 web unit tests, lint/typecheck/build all green.
- Verified criteria include: three-state plan model (suggestion/draft/confirmed) cleanly separated in storage/API/UI, per-slot regeneration scoped to single slot with sibling isolation, stale detection via grounding hash comparison, confirmed plan protection unconditional, confirmation idempotency via unique constraint + dedup check, per-slot AI origin history with all required metadata fields, grocery handoff gated exclusively on confirmed state via plan_confirmed events.
- Previously noted `npm run build:web` failure (from AIPLAN-11 evidence) is now resolved — build passes green with all routes generated.
- Six explicit follow-ups documented as non-silent carryover: AIPLAN-13 offline planner sync (Milestone 4), AIPLAN-14 grocery derivation consumption (Milestone 3), `manually_added` mixed-confirmation test gap (minor), Auth0 production wiring (inherited), `datetime.utcnow()` deprecation (inherited), dual lockfile warning (inherited).
- Decision recorded at `.squad/decisions/inbox/kirk-aiplan-12-milestone-review.md`.
- Running the evidence suite independently before signing off continues to prove essential — progress ledger claims alone are never sufficient for a milestone gate. The previously noted build failure being resolved by milestone-end validated that workspace-level issues should not block slice reviews but must clear before final acceptance.
- Milestone 2 completion means downstream milestones (Grocery Derivation M3, Offline Sync M4) can safely build on the confirmed-plan handoff contract without placeholder dependencies.
