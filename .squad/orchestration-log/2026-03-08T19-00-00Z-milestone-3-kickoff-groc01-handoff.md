# Orchestration: Milestone 3 Kickoff / GROC-01 Handoff to Sulu

**Timestamp:** 2026-03-08T19-00-00Z  
**Orchestrator:** Scribe  
**Requested by:** Ashley Hollis  
**Directive:** Team, please build the full app and don't stop until it's complete and verified.

---

## Event: Milestone 3 Planning Conclusion and Execution Kickoff

**Status:** 🚀 **MILESTONE 3 EXECUTION READY**

### Predecessor State

- ✅ **Milestone 2 Complete:** All 12 AIPLAN tasks approved; full app buildable, testable, verified through weekly planner + AI
- ✅ **Milestone 3 Planning Complete:** Feature spec, task plan, and progress ledger finalized in `.squad/specs/grocery-derivation/`
- ✅ **Zero Blocking Dependencies:** Confirmed-plan handoff contract verified; inventory foundation stable; household session/auth trustworthy

### Milestone 3 Scope (Locked from Roadmap)

1. Grocery derivation rules from confirmed meal plan plus current inventory
2. Grocery list versions, item adjustments, quantity/unit handling, review/confirmation
3. Distinction between derived suggestions and user-confirmed list state
4. Read models for desktop review and later mobile trip use
5. Test coverage for correctness, duplicate avoidance, and list confirmation behavior

### Constitution Alignment

- **2.1** Mobile Shopping First
- **2.4** Trustworthy Planning and Inventory
- **2.6** Food Waste Reduction

### Handoff Contract from Milestone 2

**Confirmed-Plan Event:**
- Event Type: `plan_confirmed`
- Payload: `household_id`, `plan_id`, `plan_version`, `period`, `slot_count`, `stale_warning_acknowledged`, `correlation_id`
- Persistence: Durable `planner_events` table
- Consumption: Exclusive trigger for grocery derivation work (suggestion and draft states emit no grocery-handoff signal)

---

## Event: GROC-01 Assignment and Handoff to Sulu

**Task:** GROC-01 — Tighten grocery schema, lifecycle enums, and migration seams  
**Owner:** Sulu  
**Status:** 🚀 **IN_PROGRESS**

### Task Directive

The current grocery models and schema (`.apps/api/app/models/grocery.py`) are a useful stub, but they still need to align fully to the approved Milestone 3 contract before implementation of GROC-02 (derivation engine) can begin with confidence.

### Acceptance Criteria

1. ✅ Grocery models reflect the approved lifecycle contract from `.squad/specs/grocery-derivation/feature-spec.md`
2. ✅ List, version, and item database tables exist with explicit version semantics and idempotency contract
3. ✅ Lifecycle enums (derived, draft, confirmed) are explicit and distinct from planner states
4. ✅ Quantity/unit handling follows inventory precedent: one primary unit per item, explicit prohibition on silent cross-unit conversion
5. ✅ Line-item adjustments support user override semantics without silently losing offset traceability
6. ✅ Line items carry per-unit cost and availability indicators for later trip use
7. ✅ Migration seams exist (alembic DDL) to evolve schema without breaking running instances
8. ✅ Deterministic test fixtures prove household isolation, idempotency, and schema correctness at SQL layer
9. ✅ Backend validation passes: lint, typecheck, test suite clean (no new noise)

### Dependencies Satisfied

- ✅ Inventory foundation (Milestone 1) — schema precedent and idempotency patterns
- ✅ Planner confirmation (Milestone 2) — `plan_confirmed` event contract finalized
- ✅ Constitution constraints — household-scoped, SQL-backed, append-only mutations with audit trail

### Blockers to GROC-02

This task unblocks GROC-02 (Implement derivation engine and authoritative persistence by Scotty). Sulu's schema work is a critical-path dependency; derivation cannot build from confident household inventory match without trustworthy schema under it.

### Supervision

- **Acceptance gate:** McCoy (per GROC-05 backend verification plan)
- **Scope boundary:** Schema and model only; no routing, no service logic, no UI wiring
- **Scope out:** Full grocery API routing (GROC-04), reconciliation pipeline (Milestone 5)

---

## Event: Milestone 3 Ready-Now Queue Initialization

| ID | Task | Agent | Status | Unlocks |
| --- | --- | --- | --- | --- |
| GROC-00 | Keep Milestone 3 progress ledger current | Scribe | in_progress | All transitions and blockers |
| GROC-01 | Tighten grocery schema, lifecycle enums, and migration seams | Sulu | **in_progress** | GROC-02 derivation engine |

### Planned Queue (Blocked Until Dependencies)

| ID | Task | Agent | Status | Blocked By |
| --- | --- | --- | --- | --- |
| GROC-02 | Implement derivation engine and authoritative persistence | Scotty | pending | GROC-01 schema |
| GROC-03 | Implement refresh and stale-draft orchestration | Scotty | pending | GROC-02 derivation |
| GROC-04 | Implement grocery API router and mutation contracts | Scotty | pending | GROC-02 derivation |
| GROC-05 | Verify backend derivation and contract slice | McCoy | pending | GROC-02, GROC-04 |
| GROC-06 | Rewire the web grocery client to the real API contracts | Uhura | pending | GROC-04 API router |
| GROC-07 | Complete grocery review and confirmation UX | Uhura | pending | GROC-04 API router |
| GROC-08 | Land confirmed-list handoff seams for trip mode and reconciliation | Scotty | pending | GROC-07 confirmation |
| GROC-09 | Add grocery observability and deterministic fixtures | Scotty | pending | GROC-04 router, GROC-05 acceptance |
| GROC-10 | Verify grocery UI and end-to-end flows | McCoy | pending | GROC-06, GROC-07 UI completion |
| GROC-11 | Final Milestone 3 acceptance review | Kirk | pending | GROC-10 E2E verification |

### Cross-Milestone Blocked Work (Explicit Deferred)

| ID | Task | Agent | Status | Blocked By |
| --- | --- | --- | --- | --- |
| GROC-12 | Persist confirmed grocery list into the real offline client store | Uhura + Scotty | blocked | Milestone 4 offline-sync foundation |
| GROC-13 | Execute active trip flows against the confirmed grocery list with conflict review | Uhura + Scotty | blocked | Milestone 4 trip mode + conflict UX |
| GROC-14 | Convert confirmed grocery outcomes into authoritative inventory updates | Scotty + Sulu | blocked | Milestone 5 shopping reconciliation |

### Risks and Watchpoints

1. **Contract drift risk:** Current frontend scaffold uses placeholder status names (`current`, `shopping`, `completed`) that do not match the approved lifecycle contract. Backend and frontend must be realigned before UI work continues.
2. **Scope bleed risk:** It will be tempting to solve trip execution, offline queueing, or reconciliation inside grocery work. The roadmap explicitly forbids that cut-line blur.
3. **Trust risk:** Any derivation shortcut that applies fuzzy matching, cross-unit conversion, or silent override loss would violate constitution §§2.4 and 6.2.
4. **Confirmed-list stability risk:** Refresh behavior must distinguish draft refresh from confirmed-list immutability, especially now that planner handoff events are real.
5. **Auth boundary risk:** Grocery work must keep using API-owned session/bootstrap rules and must not reintroduce frontend-owned auth assumptions.

---

## Event: Scribe Progress Ledger Activated

**File:** `.squad/specs/grocery-derivation/progress.md`

### Status: 🚀 Milestone 3 Execution Kickoff (2026-03-08T19-00-00Z)

- ✅ Milestone 1 complete and approved; foundational household and inventory work trustworthy
- ✅ Milestone 2 complete and approved; confirmed weekly plans and `plan_confirmed` handoff seam ready for consumption
- 🚀 Milestone 3 planning complete and execution-ready; all tasks decomposed and dependency chain mapped
- 🚀 GROC-01 assigned to Sulu and marked in_progress

---

## Event: Inbox Check and Decision Consolidation

**File:** `.squad/decisions.md`

### Status: Inbox Empty

- Previous session (Milestone 2 closure) merged 8 inbox decisions into main decisions file
- No pending decision inbox items from Milestone 2 closure require further consolidation
- Milestone 3 planning did not generate new decision boxes; all planning work is recorded in spec files and orchestration logs

---

## Compliance Checklist

- ✅ Milestone 3 kickoff orchestration log created (this file)
- ✅ GROC-01 handoff to Sulu recorded and assigned
- ✅ Milestone 3 ready-now and planned task queues mapped
- ✅ Cross-milestone blocked work explicitly listed (no silent carryover)
- ✅ Scribe progress ledger status verified active
- ✅ Inbox check confirms no pending decision consolidation needed
- ✅ Team notifications ready (orchestration log available)

---

## Status Summary

**Milestone 3:** 🚀 **EXECUTION KICKOFF (2026-03-08T19-00-00Z forward)**

- Scope locked in roadmap and feature spec
- Handoff contracts verified from Milestone 2
- Zero blocking dependencies remaining
- Critical-path task (GROC-01 schema tightening) assigned to Sulu and in-progress
- Full task decomposition complete with dependencies mapped
- Progress ledger active for transition tracking

**Ashley Hollis Directive:** "Team, please build the full app and don't stop until it's complete and verified."

**Current Status:** ✅ **MILESTONE 2 COMPLETE AND VERIFIED** → 🚀 **MILESTONE 3 EXECUTION ACTIVE**
