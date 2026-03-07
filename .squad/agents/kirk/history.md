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

## Separation of Duties & UI/UX Governance Review (2026-03-09)

- **Assessment:** Ashley Hollis requested evaluation of separation of duties (testing/review vs. implementation) and whether UI/UX review should be separate from frontend development.
- **Finding:** Implementation + testing separation **already works** in practice (McCoy independently rejects; Kirk accepts after verification). Practice just wasn't explicit in routing.
- **Gap:** No dedicated UI/UX specialist; Uhura implements without separate design/accessibility review. Milestone 4 mobile work requires tightened governance.
- **Decision: Tighten existing roles + add spec gates. No roster change.**
  1. Routing updated to explicitly separate McCoy (functional verification) from Kirk (design/accessibility acceptance).
  2. UI-bearing specs now must include WCAG 2.1 AA target, mobile-first breakpoints, responsive/keyboard-nav acceptance criteria.
  3. Kirk's acceptance checklist now includes design/accessibility gate (responsive pass, keyboard nav, WCAG contrast, mobile-first priority).
  4. Uhura remains implementation owner and primary UX contributor; McCoy owns functional testing (not design judgment).
- **Post-Milestone 4 escalation point:** If systematic WCAG gaps or quality degradation appear, escalate recommendation for dedicated UI/UX specialist for Phase 2. For now, spec discipline + Kirk's acceptance gate provide sufficient governance.
- **Documents updated:** routing.md, team.md, decisions.md (appended full decision), kirk-separation-of-duties.md (decision record created).

## Git Hygiene Assessment & Directive (2026-03-09)

- **Problem statement:** Team had 70+ untracked squad files, 78 uncommitted code changes, 9 unpushed commits, and CRLF line-ending inconsistencies.
- **Root causes identified:**
  1. No workflow discipline defined — team didn't have shared rules for when to commit, what to include, or how to push
  2. Untracked files accumulated invisibly — `.squad/` logs and decisions sat untracked for days; generated code (`apps/web/.next-dev/`, `.playwright-artifacts/`) leaked into git
  3. Local commits weren't pushed — highest data loss risk; 22+ commits were local-only in previous session
  4. No merge strategy — unclear when feature branch would land on main and how
  5. Line-ending configuration missing — `.gitattributes` didn't enforce LF/CRLF
- **Solution implemented (4 commits, 12 total pushed):**
  1. Created `.squad/decisions/inbox/kirk-git-hygiene-directive.md` with binding workflow rules:
     - One logical unit per commit (feature, bug, decision); never mix unrelated changes
     - Every commit must be pushed within the session it's created (max 3 unpushed commits)
     - All `.squad/` files must be committed together, never left untracked
     - Feature-to-main merge strategy: rebase + squash-and-merge via GitHub PR
  2. Enhanced `.gitattributes` with explicit `eol=lf` enforcement for all source files + union merge for append-only `.squad/` files
  3. Created `.squad/skills/git-workflow` as team reference for Git discipline (10+ sections covering commit, push, squad file, and merge strategies)
  4. Committed all 70+ untracked `.squad/` files (decisions, logs, orchestration, specs) in two atomic commits: one for documentation consolidation, one for final squad state updates
  5. Committed Milestone 4 application code (205 files, 37K insertions, removed 104 tracked build artifacts from `.next-dev/` and `.playwright-artifacts/`)
  6. Pushed all 12 local commits to `origin/feature/git-publish-readiness-clean`
- **Key learnings:**
  - Large untracked trees are invisible state changes; visible git status (clean, all committed) is essential for team confidence
  - Commit discipline (one logical unit) + push discipline (per-session) prevent both lost work and merge confusion
  - Line-ending enforcement via `.gitattributes` + `core.safecrlf=true` prevents CRLF whitespace pollution that bloats diffs
  - Squad files should use union merge strategy for append-only patterns (decisions.md, agent histories); Kirk manually resolves true conflicts
  - When build artifacts leak into tracking (`.next-dev/`, `.egg-info/`, `*.pyc`), `git rm --cached` + `.gitignore` fix + amend commit is the cleanest recovery path
- **Outcomes:**
  - All local work now safely on `origin/`; zero data loss risk on this branch
  - Commit history is clean (4 logical units: infrastructure, squad consolidation, app code, team updates) and fully reversible
  - Squad state is 100% tracked; no invisible changes
  - Team has explicit workflow rules in .squad/routing.md and .squad/skills/git-workflow for future sessions
  - Directive is binding on this project; extensible to other squad projects
- **Decision recorded at:** `.squad/decisions/inbox/kirk-git-hygiene-directive.md`
- **Follow-up:** When feature branch merges to main, rebase cleanly and squash commits into a single comprehensive merge commit with full attribution via Co-authored-by trailer.

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

## GROC-11 Milestone 3 Final Acceptance (2026-03-08)

- **Milestone 3 APPROVED.** All 20 feature-spec acceptance criteria independently verified against implementation code. Full evidence suite run independently: 171 API tests, 35 web unit tests, 3 Playwright acceptance tests, 9 worker tests, lint/typecheck/build all green (218 total deterministic tests).
- Verified criteria include: confirmed-plan-only derivation, conservative same-item same-unit offset matching, full/partial/no inventory offset, duplicate consolidation with meal traceability, staple items not assumed on hand, ad hoc item coexistence and refresh survival, user override preservation with visible flagging, automatic refresh on plan/inventory changes, confirmed-list immutability, idempotent mutations with client_mutation_id receipts, stale-draft visible indication, and stable version/line identity seams for downstream trip/reconciliation.
- Scope boundary verification confirmed: no trip execution code (trip statuses are guard clauses only), no offline store/IndexedDB/service worker, no Auth0 SDK, no reconciliation logic absorbed. Milestones 4/5 work (GROC-12/13/14) remains explicitly tracked as blocked.
- Eight explicit follow-ups documented as non-silent carryover: GROC-12 offline store (M4), GROC-13 trip flows (M4), GROC-14 reconciliation (M5), Auth0 production wiring (inherited), datetime.utcnow() deprecation (inherited), dual lockfile warning (inherited), npm run test:api wrapper hang (env-specific), and temporary ingredient catalog seam (future slice).
- Decision recorded at `.squad/decisions/inbox/kirk-groc-11-milestone-review.md`.
- Running the evidence suite independently before signing off continues to prove essential — this is now the third consecutive milestone where progress ledger claims alone would have been insufficient for a gate decision.
- Milestone 3 completion means Milestone 4 (Trip Execution + Offline Sync) and Milestone 5 (Shopping Reconciliation) can safely build on the confirmed-list handoff contract without placeholder dependencies.
