# Milestone 4 Kickoff — SYNC-01 Handoff to Sulu (2026-03-09T02-00-00Z)

**Recorded by:** Scribe  
**On behalf of:** Ashley Hollis (full app build request, Milestone 4 execution)

---

## Summary

Milestone 3 (Grocery Derivation) is now **COMPLETE AND APPROVED** as of 2026-03-09T01-00-00Z. GROC-11 final acceptance review closed. Milestone 4 (Mobile trip mode, offline queueing, and conflict-safe sync) planning is now **ACTIVE**, with execution-ready task queue prepared from approved spec and confirmed Milestone 3 grocery handoff seam.

**Immediate action:** SYNC-01 (Lock the trip/offline contract seam across API and web types) is now **ready_now** and handed off to **Sulu** for execution.

---

## Current State Transition

### Milestone 3 Closure
- ✅ **GROC-11 (Kirk final acceptance):** Executed, approved
- ✅ **All 11 GROC tasks delivered:** GROC-01 through GROC-11 complete
- ✅ **Full test suite verified:** 171 API + 33 web + 9 worker tests passing
- ✅ **Confirmed-list seam stable:** `grocery_list_version_id`, `grocery_line_id`, `confirmed_at` ready for Milestone 4 consumption
- ✅ **Scope boundaries clean:** No trip-execution, offline-store, or reconciliation code absorbed into Milestone 3

### Milestone 4 Activation
- 🚀 **Status:** PLANNING ACTIVE (2026-03-09T01-00-00Z)
- 🚀 **Ready-now queue established:** SYNC-00 (Scribe progress ledger) and SYNC-01 (Sulu contract seam) active
- 🚀 **Execution-ready task breakdown:** SYNC-02 through SYNC-11 queued with clear dependencies, verified against approved offline-sync spec
- 🚀 **All prerequisites satisfied:** Milestone 1 ✅, Milestone 3 ✅, Milestone 0 sync scaffolding ✅

---

## SYNC-01 Handoff Details

**Task:** Lock the trip/offline contract seam across API and web types  
**Owner:** Sulu  
**Status:** ready_now (assigned 2026-03-09T02-00-00Z)

### Scope
Finalize Milestone 4 contract fields required for:
- Confirmed-list bootstrap payloads (source list version, available lines, latest inventory snapshot)
- Queueable mutation metadata (`client_mutation_id`, `base_server_version`, aggregate identity for deduplication)
- Sync outcome enums (duplicate retry, auto-merged non-overlapping, review-required classes)
- Conflict read models (conflict record schema, conflict class, local/base/server snapshot comparison)
- Explicit resolution commands (keep-mine, use-server, with rationale preservation)
- Removal of any placeholder trip semantics that could mislead downstream implementation

### Inputs
- Approved offline-sync-conflicts spec at `.squad/specs/offline-sync-conflicts/feature-spec.md`
- Approved conflict-matrix at `.squad/specs/offline-sync-conflicts/conflict-matrix.md`
- Milestone 3 confirmed-list handoff seams already live in:
  - `apps/api/app/models/grocery.py`
  - `apps/api/app/schemas/grocery.py`
  - `apps/web/app/grocery/_components/GroceryView.tsx`

### Dependent Tasks
- **SYNC-02** (Uhura, offline store) — waits for SYNC-01 to lock IndexedDB schema and mutation intent model
- **SYNC-03** (Uhura, mobile trip UX) — waits for SYNC-01 to finalize confirmed-list bootstrap and trip state enums
- **SYNC-04** (Scotty, upload API) — waits for SYNC-01 to lock mutation metadata and sync outcome classes
- **SYNC-05** (Scotty, conflict classifier) — waits for SYNC-01 to finalize conflict record fields and decision logic

### Success Criteria
- ✅ Confirmed-list bootstrap payload contract finalized (list version, lines, inventory snapshot)
- ✅ Queueable mutation metadata schema locked (`client_mutation_id`, `base_server_version`, aggregate identity)
- ✅ Sync outcome enums and conflict classes defined and verified against approved conflict matrix
- ✅ Conflict read-model schema established (conflict record, resolution commands)
- ✅ Resolution command contracts finalized (keep-mine and use-server with rationale)
- ✅ API type stubs and web type definitions updated to reflect finalized contract
- ✅ Zero placeholder trip semantics remaining in backend or web code

---

## Progress Ledger Update

**Milestone 4 Progress Log:** `.squad/specs/offline-sync-conflicts/progress.md`

| ID | Task | Agent | Status | Notes |
| --- | --- | --- | --- | --- |
| SYNC-00 | Keep Milestone 4 progress ledger current | Scribe | in_progress | Ledger activated; will update on every transition, blocker, and verification result. |
| SYNC-01 | Lock the trip/offline contract seam across API and web types | Sulu | ready_now | Assigned 2026-03-09T02-00-00Z. First contract gate before queue, upload, and conflict work begins. |
| SYNC-02 through SYNC-11 | Implementation and verification tasks | [assigned] | pending | Blocked until SYNC-01 locks contract seam. Execution order: SYNC-02/SYNC-03/SYNC-04 in parallel after SYNC-01; follow with SYNC-05/SYNC-06; then SYNC-07/SYNC-08; finally SYNC-09/SYNC-10/SYNC-11 verification gates. |

---

## Roadmap and Dependency Status

**Constitution alignment:** Milestone 4 delivery aligns with approved constitution principles:
- 2.1 Mobile Shopping First: trip mode operates on phone-sized touch targets
- 2.2 Offline Is Required: app must work through connectivity loss
- 2.3 Shared Household Coordination: safe conflict resolution enables shared grocery/trip state
- 2.7 UX Quality and Reliability: mobile trip is a first-class feature, not read-only fallback

**Dependency verification:**
- ✅ Milestone 1 (Household + Inventory Foundation): Complete 2026-03-08
- ✅ Milestone 3 (Grocery Calculation + Review): Complete 2026-03-09
- ✅ Milestone 0 Sync Scaffolding (Aspire, queue foundations, auth seam): Complete 2026-03-08

**Ready for execution:** All prerequisites satisfied. SYNC-01 handoff is the first implementation gate.

---

## Decision Consolidation

**Inbox status:** 1 item queued for consolidation
- `kirk-groc-11-milestone-review.md` (GROC-11 final acceptance review) — to be merged to `.squad/decisions/consolidated/` after this session log

**Impact:** Kirk's GROC-11 decision consolidation finalizes Milestone 3 approval record and unblocks Milestone 4 execution.

---

## Full Application Verification Status at Milestone 4 Activation

**Test results from Milestone 3 completion (2026-03-09T01-00-00Z):**
- ✅ API tests: 171 passed
- ✅ Web tests: 33 passed
- ✅ Worker tests: 9 passed
- ✅ Web build: Complete and green
- ✅ Web lint: Clean
- ✅ Web typecheck: Clean
- ✅ E2E acceptance tests (Playwright): All green

**Build status:** Full app buildable, testable, and verifiable through Milestone 3. Ready for Milestone 4 execution.

---

## Watchpoints for SYNC-01 and Downstream Execution

**Contract seam integrity:**
- Trip mode must consume confirmed list via locked `grocery_list_version_id`, `grocery_line_id`, and `confirmed_at` from Milestone 3 seam
- No re-derivation or auto-refresh of grocery list during trip execution
- Confirmed list version and line IDs immutable during trip

**Mutation intent model:**
- Client-supplied `client_mutation_id` tied to household scope (reuse Milestone 1/3 patterns)
- Queue entry must preserve local/base/server comparison metadata for post-reconnect conflict review
- Mutation intent types: check-off, quantity-edit, ad-hoc item creation (trip-mode mutations only; no inventory mutations)

**Sync outcome classifications:**
- Duplicate retry: same `client_mutation_id` sent again (idempotent receipt replay)
- Auto-merged non-overlapping: server verifies mutation doesn't overlap with concurrent edits
- Review-required conflicts: quantity conflict, deletion/archive conflict, freshness/location conflict (per approved matrix)

**Conflict record schema:**
- Stable conflict identity for resolution tracking (conflict ID, resolution status, keep-mine/use-server decision)
- Preserve local intent, base version, current server version for review UX
- Audit trail: conflict creation timestamp, classification reason, resolution command and timestamp

---

## Session Artifact Status

**Files updated/created for Milestone 4 activation:**
- ✅ Session log: `.squad/log/2026-03-09T02-00-00Z-milestone4-kickoff-sync01-handoff.md` (this file)
- ✅ Orchestration log: `.squad/orchestration-log/2026-03-09T02-00-00Z-milestone4-kickoff-sync01-handoff.md`
- 📋 Pending: Consolidate Kirk GROC-11 decision from inbox to `.squad/decisions/consolidated/`
- 📋 Pending: Append Scribe history with Milestone 4 activation record

---

## Next Immediate Actions

1. **Sulu executes SYNC-01** (contract seam lock) — target completion 2026-03-09T06-00-00Z
2. **Scribe consolidates Kirk GROC-11 decision** — move from inbox to consolidated decisions
3. **Scribe appends history** — update `.squad/agents/scribe/history.md` with Milestone 4 activation record
4. **Progress ledger remains active** — SYNC-00 updates on every state transition

---

## Status

✅ **MILESTONE 3 FULLY COMPLETE AND APPROVED. MILESTONE 4 PLANNING ACTIVATED. SYNC-01 READY_NOW AND HANDED TO SULU. ZERO BLOCKING ISSUES. FULL APP BUILDABLE, TESTABLE, AND VERIFIABLE.**
