# Milestone 2 Phase 3: Grocery Handoff & Observability Parallel Path

**Timestamp:** 2026-03-08T17-00-00Z  
**Authorized by:** Ashley Hollis  
**Owner:** Scotty (AIPLAN-09/10), McCoy & Kirk (standby for AIPLAN-11/12)  
**Recorded by:** Scribe

## Handoff Event: Parallel Grocery & Observability Work Launched

With AIPLAN-06 (backend/worker contract gate) and AIPLAN-08 (planner UI) both closed, the critical path now flows through parallel grocery/observability work (AIPLAN-09/10) before final E2E verification (AIPLAN-11).

### AIPLAN-09: Emit and Contract-Test Grocery Handoff Seam
**Owner:** Scotty  
**Unlocks:** AIPLAN-12 (Kirk, final Milestone 2 review)  
**Dependency:** AIPLAN-05 (complete), AIPLAN-06 (complete)

**Scope:**
- Validate that `plan_confirmed` events flow correctly from planner API to grocery derivation boundary.
- Wire up the handoff contract: confirmed weekly plan → grocery list derivation (Milestone 3 responsibility).
- Add deterministic contract tests proving the boundary behaves correctly under test fixtures.

**Success Criteria:**
- `plan_confirmed` events emit with correct household/slot/confirmation/AI-origin payload.
- Grocery derivation receives and parses events correctly (dry-run against mock).
- No regression in planner API or worker tests.

### AIPLAN-10: Build Observability & Deterministic Fixtures for E2E Coverage
**Owner:** Scotty  
**Unlocks:** AIPLAN-11 (McCoy, UI/E2E verification)  
**Dependency:** AIPLAN-05 (complete), AIPLAN-06 (complete)

**Scope:**
- Implement event publishing infrastructure for end-to-end trace visibility.
- Build deterministic test fixtures that enable repeatable E2E scenarios across planner → grocery boundary.
- Add observability hooks into worker generation, slot confirmation, and stale detection flows.

**Success Criteria:**
- Event logs can be captured and replayed in deterministic order.
- E2E tests can assert full trace from plan submission through grocery derivation without flakiness.
- All worker, API, and frontend deterministic tests remain green.

### Ready-Now Queue Status
- **Scotty (AIPLAN-09 & AIPLAN-10):** Both tasks ready to execute in parallel. No inter-blocking dependency between them.
- **McCoy (AIPLAN-11):** Blocked. Will transition to ready-now upon AIPLAN-09/10 completion.
- **Kirk (AIPLAN-12):** Blocked. Will transition to ready-now upon AIPLAN-11 completion.

---

## Why This Phase Is Critical
The grocery handoff seam (AIPLAN-09) and observability foundation (AIPLAN-10) are the final engineering dependencies before Milestone 2 closure:
1. Without grocery handoff validation (AIPLAN-09), the planner → grocery pipeline remains unproven.
2. Without observability (AIPLAN-10), McCoy cannot build repeatable E2E tests (AIPLAN-11).
3. Without AIPLAN-11, Kirk cannot complete final Milestone 2 acceptance (AIPLAN-12).

Ashley's directive to complete and verify the app requires this full chain to execute and succeed.

---

## Command Verification (upon completion)
Scotty will run before transitioning to McCoy:
```
cd apps\api && python -m pytest tests
cd apps\worker && python -m pytest tests
npm run lint
npm run typecheck
npm run build
```
