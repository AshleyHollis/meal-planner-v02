# Milestone 4 Kickoff & SYNC-01 Handoff Orchestration Log (2026-03-09T02-00-00Z)

**Timestamp:** 2026-03-09T02-00-00Z  
**Recorded by:** Scribe  
**Authorized by:** Ashley Hollis (full app build request)

---

## Entry

Milestone 3 (Grocery calculation and review before the trip) is **COMPLETE AND APPROVED** (Kirk final acceptance review GROC-11 executed 2026-03-09T01-00-00Z). Milestone 4 (Mobile trip mode, offline queueing, and conflict-safe sync) planning is **ACTIVATED**. Execution-ready task queue prepared from approved spec and confirmed Milestone 3 grocery handoff seam.

**Immediate action:** SYNC-01 (Lock the trip/offline contract seam across API and web types) is now **ready_now** and handed off to **Sulu** for contract-seam execution.

---

## Prior State

- **Milestone 3:** GROC-11 (Kirk final acceptance) ready_now (2026-03-09T00-00-00Z)
- **Milestone 4:** Planned / awaiting Milestone 3 completion

---

## Current State

### Milestone 3: Final Approval Recorded

**Owner:** Kirk  
**Task:** GROC-11 (Final Milestone 3 acceptance review)  
**Status:** ✅ **APPROVED** (2026-03-09T01-00-00Z)

**Final acceptance gate execution result:**
- ✅ Confirmed all 11 GROC tasks (GROC-01 through GROC-11) delivered against chartered scope
- ✅ Verified no scope bleed into Milestone 4 (trip-execution features)
- ✅ Verified no scope bleed into Milestone 5 (reconciliation features)
- ✅ Validated downstream handoff seams (trip/reconciliation) stable
- ✅ Full suite test/build/lint/typecheck passing (171 API + 33 web + 9 worker)
- ✅ Grocery derivation, review, and confirmation workflows fully functional
- ✅ Confirmed lists maintain version and line identity for downstream use

**Outcome verified:** Household can turn weekly plan plus inventory into trustworthy grocery list and review it before shopping. Confirmed lists are stable, version-locked, and ready for Milestone 4 trip execution and Milestone 5 reconciliation.

**Decisions archived:** Kirk GROC-11 milestone review decision (from `.squad/decisions/inbox/kirk-groc-11-milestone-review.md`) staged for consolidation to `.squad/decisions/consolidated/` after this orchestration entry.

---

### Milestone 4: Planning Activated

**Status:** 🚀 **PLANNING ACTIVE** (2026-03-09T01-00-00Z)

**Roadmap reference:** `.squad/project/roadmap.md` §4

**Scope:**
- Mobile-first trip mode with large touch targets, low-typing interactions, phone-sized layout validation
- Offline-capable access to confirmed shopping list, meal plan context, and latest inventory snapshot
- Offline check-off, quantity edits, and ad hoc item creation using explicit IndexedDB-backed mutation intents
- Sync engine for replay, retry, status visibility, deduplication, and user-visible conflict handling
- Conflict UX for stale quantities, concurrent list edits, and retry/recovery choices

**Why Milestone 4 after Milestone 3:**
- Constitution requires offline-capable essential shopping workflows in MVP, but sync model depends on stable grocery, inventory, and API command boundaries
- Confirmed grocery lists from Milestone 3 are the source of truth for trip execution
- Sync/conflict contracts from Milestone 0 provide scaffolding foundation

**Dependencies satisfied:**
- ✅ Milestone 1 (Household + inventory foundation): Complete 2026-03-08
- ✅ Milestone 3 (Grocery calculation + review): Complete 2026-03-09
- ✅ Milestone 0 (Sync/conflict contract support): Complete 2026-03-08

**Constitution alignment verified:**
- 2.1 Mobile Shopping First: trip mode operates on phone-sized touch targets
- 2.2 Offline Is Required: app must work through connectivity loss
- 2.3 Shared Household Coordination: safe conflict resolution enables shared state
- 2.7 UX Quality and Reliability: mobile trip is first-class feature, not fallback

---

## SYNC-01 Handoff Details

**Task:** Lock the trip/offline contract seam across API and web types  
**Owner:** Sulu  
**Status:** ready_now (assigned 2026-03-09T02-00-00Z)  
**Planned completion:** 2026-03-09T06-00-00Z

**Rationale:** SYNC-01 is the first implementation gate for Milestone 4. Contract-seam tightening must precede offline-store, upload-API, and conflict-classifier work. This task finalizes:
- Confirmed-list bootstrap payload contract (list version, lines, inventory snapshot)
- Queueable mutation metadata (`client_mutation_id`, `base_server_version`, aggregate identity)
- Sync outcome enums (duplicate retry, auto-merged non-overlapping, review-required classes per conflict matrix)
- Conflict read-model schema (conflict record, resolution commands)
- Removal of placeholder trip semantics

**Dependent tasks (unblocked after SYNC-01):**
- SYNC-02 (Uhura): Durable client offline store and queue foundation
- SYNC-03 (Uhura): Mobile trip mode over confirmed-list snapshot
- SYNC-04 (Scotty): Sync upload API and stale-detection foundations
- SYNC-05 (Scotty): MVP conflict classifier and replay rules
- SYNC-06 (Scotty): Explicit resolution commands and read-model refresh
- SYNC-07 (Uhura): Mobile conflict-review UX and resolution flow
- SYNC-08 (Scotty): Observability, diagnostics, and deterministic sync fixtures
- SYNC-09 (McCoy): Backend sync/conflict slice verification
- SYNC-10 (McCoy): Mobile trip/offline behavior end-to-end verification
- SYNC-11 (Kirk): Final Milestone 4 acceptance review

**Parallel execution model (post-SYNC-01):**
- Parallel 1: SYNC-02 (offline store) + SYNC-03 (trip UX) + SYNC-04 (upload API)
- Parallel 2: SYNC-05 (conflict classifier) + SYNC-06 (resolution commands)
- Parallel 3: SYNC-07 (conflict UX) + SYNC-08 (observability) [depends on SYNC-05/SYNC-06]
- Verification gates: SYNC-09 (backend) + SYNC-10 (E2E) [depends on SYNC-05/SYNC-06/SYNC-08]
- Final gate: SYNC-11 (Kirk acceptance) [depends on SYNC-09/SYNC-10]

---

## Milestone 4 Execution-Ready Task Queue

**Master task plan:** `.squad/specs/offline-sync-conflicts/tasks.md`  
**Progress ledger:** `.squad/specs/offline-sync-conflicts/progress.md`

| Task | Owner | Status | Depends on | Notes |
| --- | --- | --- | --- | --- |
| SYNC-00 | Scribe | in_progress | — | Keep progress ledger current on every transition, blocker, verification result |
| SYNC-01 | Sulu | ready_now | GROC-11 ✅ | Contract seam lock (trip/offline models, mutation metadata, sync outcomes, conflict record) |
| SYNC-02 | Uhura | pending | SYNC-01 | Durable client offline store and queue foundation (IndexedDB, snapshot, mutation queue) |
| SYNC-03 | Uhura | pending | SYNC-01, SYNC-02 | Mobile trip mode over confirmed-list snapshot (phone UX, check-off, quantity edit, ad hoc items) |
| SYNC-04 | Scotty | pending | SYNC-01 | Sync upload API and stale-detection foundations (per-mutation upload, receipts, conflict records) |
| SYNC-05 | Scotty | pending | SYNC-04 | MVP conflict classifier and replay rules (duplicate retry, auto-merge, review-required classes) |
| SYNC-06 | Scotty | pending | SYNC-05 | Explicit resolution commands and read-model refresh (keep-mine, use-server, rationale) |
| SYNC-07 | Uhura | pending | SYNC-03, SYNC-05, SYNC-06 | Mobile conflict-review UX and resolution flow (phone-sized conflict details, resolution interaction) |
| SYNC-08 | Scotty | pending | SYNC-05 | Observability, diagnostics, and deterministic sync fixtures (correlation logs, test fixtures) |
| SYNC-09 | McCoy | pending | SYNC-04, SYNC-05, SYNC-06, SYNC-08 | Backend sync/conflict slice verification (unit/integration coverage for replay, merge, conflict) |
| SYNC-10 | McCoy | pending | SYNC-02, SYNC-03, SYNC-07, SYNC-08 | Mobile trip/offline behavior end-to-end verification (offline load, edits, reconnect, resolution) |
| SYNC-11 | Kirk | pending | SYNC-09, SYNC-10 | Final Milestone 4 acceptance review (spec compliance, constitution alignment, roadmap cut line) |

**Blocked/cross-milestone follow-on:**

| Task | Owner | Status | Blocked by | Why scheduled after Milestone 4 |
| --- | --- | --- | --- | --- |
| SYNC-12 | Scotty + Sulu | blocked | Milestone 5 | Inventory mutation from trip outcomes (reconciliation workflow) |
| SYNC-13 | Uhura + Scotty | blocked | Phase 2 | Live presence and multi-shopper coordination |
| SYNC-14 | Scotty | blocked | Phase 2 | Semantic merge automation beyond MVP-safe classes |

---

## Locked Milestone 4 Rules

**Confirmed-list bootstrap only:** Trip mode starts from confirmed grocery list version delivered by Milestone 3. Draft grocery state is never the authoritative trip input.

**Intent queue only:** Offline storage persists intent-based mutations plus comparison metadata, not whole-record overwrites.

**Server-classified conflicts:** API owns duplicate detection, stale detection, safe auto-merge decisions, conflict creation, and resolution commands. Client must not invent merge rules.

**Unsafe replay stops:** If system cannot prove safe merge, replay halts for that mutation and requires explicit user review.

**MVP auto-merge remains narrow:** Only duplicate retries and clearly non-overlapping updates may auto-merge.

**Mobile-first UX is mandatory:** Trip progress, sync state, retry state, and conflict review must stay usable on a phone.

**No silent inventory mutation:** Trip mode updates grocery/trip state only. Authoritative inventory changes remain Milestone 5 reconciliation.

**Backend-owned session/auth only:** No Auth0 SDK or runtime config in `apps/web`. Continue using API-owned session bootstrap via `GET /api/v1/me`.

---

## Current Codebase Status for Milestone 4 Execution

**Baseline from Milestone 3:**
- `apps/api/app/models/grocery.py` and `apps/api/app/schemas/grocery.py` expose stable confirmed-list identity seam (`stable_line_id`/`grocery_line_id`, `grocery_list_version_id`, `confirmed_at`)
- `apps/api/app/routers/grocery.py` and `apps/api/app/services/grocery_service.py` enforce confirmed-list stability, grocery mutation receipts, trip-state enums
- `apps/web/app/grocery/_components/GroceryView.tsx` renders trip-related status labels and uses `SyncStatusBadge`
- `apps/web/app/_components/SyncStatusBadge.tsx` and shared `SyncStatus` type provide UI seam for `syncing`, `conflict`, `error`, `offline` states

**Gaps for Milestone 4 (to be filled):**
- No durable offline client store (IndexedDB) or replay queue
- No full trip mutation upload handling on API
- No conflict records, classification logic, or resolution commands
- No mobile trip mode UX (current trip states are read-only labels)
- No conflict-review flow or user-visible resolution affordances

**Reusable patterns (from Milestone 1/3):**
- Backend-owned household session and request scope
- Durable mutation receipts unique on (household_id, client_mutation_id)
- Household-scoped authorization and isolation
- Append-only adjustment/receipt history for audit trail
- SQL-backed authoritative state with transaction consistency

---

## Full Application Verification at Milestone 4 Activation

**Test results at Milestone 3 completion (2026-03-09T01-00-00Z):**
- ✅ API tests: 171 passed
- ✅ Web tests: 33 passed
- ✅ Worker tests: 9 passed
- ✅ Web build: Complete
- ✅ Web lint: Clean
- ✅ Web typecheck: Clean
- ✅ E2E acceptance tests (Playwright): Green

**Build status:** Full app buildable, testable, and verifiable through Milestone 3. No blockers for Milestone 4 execution.

---

## Watchpoints for Milestone 4 Execution

**Trip mode scope boundaries:**
- No reconciliation logic (Milestone 5)
- No advanced inventory mutations (offline store is read-only plus explicit mutation intents)
- Confirmed list version/line IDs immutable during trip

**Sync and conflict scope:**
- Replay logic must be deterministic and auditable
- User-visible conflict UX must present clear choice points
- Deduplication must prevent double-application of mutation intents

**Mobile-first validation:**
- All interactions must work on phone-sized touch screens
- Offline-first behavior: app must function with full connectivity loss
- Sync resume: reconnect must replay pending intents in deterministic order

**Placeholder trip-state risk:** Grocery status enums mention `trip_in_progress`, but current UI is read-only labels. SYNC-01 through SYNC-03 must replace labels with real trip execution.

**Durability gap risk:** Without SYNC-02 offline store and queue, product still lacks honest offline replay capability.

**Conflict-trust risk:** Without SYNC-05/SYNC-06, product still lacks conflict record and explicit resolution commands.

---

## Session Artifact Updates Recorded

- **Session log:** `.squad/log/2026-03-09T02-00-00Z-milestone4-kickoff-sync01-handoff.md` ✅
- **Orchestration log:** `.squad/orchestration-log/2026-03-09T02-00-00Z-milestone4-kickoff-sync01-handoff.md` (this file)
- **Decision consolidation:** Kirk GROC-11 decision staged for move from `.squad/decisions/inbox/` to `.squad/decisions/consolidated/`
- **Scribe history:** Staged for append with Milestone 4 activation record
- **Progress ledger:** `.squad/specs/offline-sync-conflicts/progress.md` remains active (SYNC-00 in_progress)

---

## Decision Consolidation Status

**Inbox:** 1 item staged for consolidation
- `kirk-groc-11-milestone-review.md` (GROC-11 final Milestone 3 acceptance review) — to move to `.squad/decisions/consolidated/`

**Impact:** Consolidation closes Milestone 3 decision tracking and formally records Kirk's final approval.

---

## Status

✅ **MILESTONE 3 FULLY APPROVED. MILESTONE 4 PLANNING ACTIVATED. SYNC-01 READY_NOW AND HANDED TO SULU. ZERO BLOCKING ISSUES. ROADMAP UPDATED. FULL APP BUILDABLE, TESTABLE, AND VERIFIABLE.**
