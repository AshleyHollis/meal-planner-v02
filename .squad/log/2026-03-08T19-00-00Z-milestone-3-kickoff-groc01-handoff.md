# Milestone 3 Kickoff / GROC-01 Handoff to Sulu

**Timestamp:** 2026-03-08T19-00-00Z  
**Authorized by:** Ashley Hollis  
**Directive:** Team, please build the full app and don't stop until it's complete and verified.  
**Recorded by:** Scribe

---

## Summary

Milestone 3 (Grocery Derivation) planning is complete and execution is now active. GROC-01 (tighten grocery schema and lifecycle) has been assigned to Sulu and marked in_progress as the critical-path task that unblocks all downstream grocery derivation work.

---

## Milestone 3 Execution Status

**Status:** 🚀 **IN PROGRESS (2026-03-08T19-00-00Z forward)**

### Scope Confirmed

From `.squad/project/roadmap.md` and `.squad/specs/grocery-derivation/feature-spec.md`:

1. Grocery derivation rules from confirmed meal plan plus current inventory
2. Grocery list versions, item adjustments, quantity/unit handling, review/confirmation
3. Distinction between derived suggestions and user-confirmed list state
4. Read models for desktop review and later mobile trip use
5. Test coverage for grocery correctness, duplicate avoidance, and list confirmation behavior

### Handoff Contract from Milestone 2

- **Event Type:** `plan_confirmed`
- **Trigger:** Only confirmed plans trigger grocery derivation (suggestion and draft states emit no signal)
- **Payload:** `household_id`, `plan_id`, `plan_version`, `period`, `slot_count`, `stale_warning_acknowledged`, `correlation_id`
- **Consumption:** Exclusive input to grocery derivation work

---

## GROC-01 Assigned to Sulu

**Task:** Tighten grocery schema, lifecycle enums, and migration seams  
**Owner:** Sulu  
**Status:** 🚀 **IN_PROGRESS**

### Directive

The current grocery models (`.apps/api/app/models/grocery.py`) are a useful stub but need to align fully with the approved Milestone 3 contract before derivation engine work (GROC-02) can begin.

### Acceptance Criteria

1. ✅ Grocery models reflect the approved lifecycle contract
2. ✅ List, version, and item tables with explicit version semantics and idempotency
3. ✅ Lifecycle enums (derived, draft, confirmed) distinct from planner states
4. ✅ Quantity/unit handling: one primary unit per item, explicit prohibition on silent cross-unit conversion
5. ✅ Line-item adjustments support user override without losing offset traceability
6. ✅ Line items carry per-unit cost and availability indicators for later trip use
7. ✅ Migration seams (alembic DDL) exist for schema evolution
8. ✅ Deterministic test fixtures prove household isolation, idempotency, and schema correctness
9. ✅ Backend validation passes: lint, typecheck, test suite clean

### Unlocks

- GROC-02 (Scotty): Implement derivation engine and authoritative persistence
- Critical-path dependency; derivation cannot build from confident inventory match without trustworthy schema

---

## Milestone 3 Ready-Now Queue

| ID | Task | Agent | Status |
| --- | --- | --- | --- |
| GROC-00 | Keep Milestone 3 progress ledger current | Scribe | in_progress |
| GROC-01 | Tighten grocery schema, lifecycle enums, and migration seams | Sulu | **in_progress** |

---

## Milestone 3 Planned Queue (Blocked Until Dependencies Clear)

| ID | Task | Agent | Blocked By |
| --- | --- | --- | --- |
| GROC-02 | Implement derivation engine | Scotty | GROC-01 schema |
| GROC-03 | Refresh and stale-draft orchestration | Scotty | GROC-02 |
| GROC-04 | Grocery API router | Scotty | GROC-02 |
| GROC-05 | Backend verification gate | McCoy | GROC-02, GROC-04 |
| GROC-06 | Web grocery client rewiring | Uhura | GROC-04 |
| GROC-07 | Grocery review and confirmation UX | Uhura | GROC-04 |
| GROC-08 | Trip/reconciliation handoff seams | Scotty | GROC-07 |
| GROC-09 | Observability and deterministic fixtures | Scotty | GROC-04, GROC-05 |
| GROC-10 | Grocery UI and E2E verification | McCoy | GROC-06, GROC-07 |
| GROC-11 | Final Milestone 3 acceptance review | Kirk | GROC-10 |

---

## Explicit Cross-Milestone Deferred Work

- **GROC-12:** Offline client store persistence (Milestone 4 offline-sync foundation)
- **GROC-13:** Active trip execution (Milestone 4 trip mode + conflict UX)
- **GROC-14:** Inventory reconciliation (Milestone 5 shopping reconciliation)

---

## Watchpoints

1. **Contract drift:** Frontend scaffold uses placeholder status names; backend and frontend must realign before UI work continues.
2. **Scope bleed:** Trip execution, offline queueing, or reconciliation must not be absorbed into Milestone 3 per roadmap.
3. **Trust risk:** No fuzzy matching, cross-unit conversion, or silent override loss (constitution §§2.4, 6.2).
4. **Confirmed-list stability:** Refresh must distinguish draft from confirmed immutability.
5. **Auth boundary:** API-owned session/bootstrap rules must remain; no frontend auth assumptions.

---

## Inbox Status

- ✅ Inbox empty (previous session merged 8 decision items into `.squad/decisions.md`)
- ✅ No pending decision consolidation needed for Milestone 3 planning
- ✅ All planning decisions recorded in spec and orchestration logs

---

## Next Transitions

1. Sulu completes GROC-01 schema work and handoff to Scotty (GROC-02)
2. Scotty begins derivation engine implementation with schema as foundational contract
3. Parallel tracks: API router (GROC-04), refresh orchestration (GROC-03)
4. McCoy verifies backend against acceptance gate (GROC-05)
5. Uhura rewires web client and completes confirmation UX (GROC-06, GROC-07)
6. Final verification gates (GROC-10, GROC-11) before Milestone 3 closure

---

## Ashley Hollis Directive Status

**Directive:** "Team, please build the full app and don't stop until it's complete and verified."

**Current Progress:**
- ✅ **Milestone 1 Complete:** Inventory foundation stable and verified
- ✅ **Milestone 2 Complete:** Weekly planner and AI suggestions production-ready and verified
- 🚀 **Milestone 3 Active:** Grocery derivation execution just kicked off with critical-path task assigned
- **Roadmap:** Milestone 4 (offline/mobile) and Milestone 5 (reconciliation) queued after Milestone 3

Full app remains buildable, testable, and verifiable through all completed milestones. Team continuous execution mode enabled.
