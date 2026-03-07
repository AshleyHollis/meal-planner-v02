# Milestone 3: GROC-05 Approval and GROC-07 Completion → GROC-08/GROC-09 Handoff

**Timestamp:** 2026-03-08T21-15-00Z  
**Recorded by:** Scribe  
**Authorized by:** Ashley Hollis (full app build request)

---

## Entry

GROC-05 (backend derivation and contract slice verification) is approved by McCoy. GROC-07 (grocery review and confirmation UX) is complete by Uhura. Both blocking dependencies satisfied. GROC-08 and GROC-09 are now unblocked and ready for immediate execution.

---

## Prior State

- **GROC-05:** in_progress (launched 2026-03-08T21-00-00Z)
- **GROC-07:** in_progress (launched 2026-03-08T21-00-00Z)
- **GROC-08:** pending (blocked by GROC-07)
- **GROC-09:** pending (blocked by GROC-04, GROC-05)

---

## Current State

### GROC-05 Approval Recorded

**Reviewer:** McCoy  
**Verdict:** ✅ APPROVED (2026-03-08T21-15-00Z)

**Coverage added:**
- Explicit confirmed-plan-only derivation regression (against coexisting draft)
- Explicit staples non-assumption regression (remain on list unless inventory clearly offsets)
- Conservative offset behavior: full/partial/no match handling
- Duplicate consolidation and unit-separation safety
- Stale-draft signaling after relevant inventory mutations
- Override and ad-hoc item preservation across refresh/re-derive
- Household-scoped idempotent mutations
- Confirmed-list immutability under refresh/re-derive pressure

**Evidence:**
- `apps\api :: test_grocery.py` → 13/13 passed
- `apps\api :: tests (full suite)` → 166 passed, 196 warnings (repo baseline noise)

**Reviewer conclusion:** Automated proof explicit for trust-sensitive gaps. No rejection or lockout required.

**Decision consolidated:** `.squad/decisions/consolidated/2026-03-08T21-15-00Z-mccoy-groc05-verification-approved.md`

### GROC-07 Completion Recorded

**Owner:** Uhura  
**Status:** ✅ COMPLETE (2026-03-08T21-15-00Z)

**UX delivered:**
- Inline per-line detail disclosure for meal traceability and offset breakdown
- Inline quantity override editing and removal review (draft-only)
- Separate removed-lines section for transparent change tracking
- Confirmation modal for explicit list-locking step (desktop + phone)

**Why this shape:**
- Desktop/phone scanability without secondary pages or hidden detail routes
- Removed-lines section keeps draft honest: users see intentional dismissals
- Confirmation modal as explicit authority boundary: restates warnings, overrides, locked-list consequence

**Frontend evidence:** Web tests green; grocery calls now use `activeHouseholdId`; placeholder statuses replaced with approved contract.

**Decision consolidated:** `.squad/decisions/consolidated/2026-03-08T21-15-00Z-uhura-groc07-review-ux-decision.md`

---

## Unblocked Tasks

### GROC-08: Land Confirmed-List Handoff Seams (Scotty)

**Status:** ready_now (2026-03-08T21-15-00Z)  
**Dependencies satisfied:** GROC-04 ✅, GROC-07 ✅

**Scope:**
- Stable list-version identity: confirmed-at timestamp, list version ID immutable after confirmation
- Line identifiers: traceable back to meal slot + inventory snapshot
- Offset references: preserved end-to-end for reconciliation audit trail
- Mutation ID idempotency: client mutation ID scope validated for trip/reconciliation use
- Contract for downstream: Milestone 4 trip mode (offline client store seam) + Milestone 5 reconciliation (post-trip inventory updates)

**Watchpoints:**
- Must preserve original meal-slot references for trip UI traceability
- Must carry inventory offset path (item → units → quantity) for reconciliation audit
- List version stability is immutable after confirmation; new derivations spawn separate draft

### GROC-09: Add Grocery Observability and Deterministic Fixtures (Scotty)

**Status:** ready_now (2026-03-08T21-15-00Z)  
**Dependencies satisfied:** GROC-03 ✅, GROC-04 ✅

**Scope:**
- Trace events: plan → derive → refresh → confirm lifecycle with correlation IDs
- Deterministic fixtures:
  - Complete derivation (all items found in inventory)
  - Partial-offset scenarios (some items partially available)
  - Stale-draft refresh (inventory changes between confirmation and refresh)
  - Incomplete-slot warnings (derivation unable to find ingredients)
- Correlation ID threading: `plan_confirmed` event header through derivation → refresh → confirmation phases

**Watchpoints:**
- Derive request should carry correlation ID from `plan_confirmed` event
- Refresh signals should include household + plan scope for diagnostics
- Confirmation events should log final override count and stale-refresh path taken

---

## Ready-Now Queue After Handoff

| Task | Agent | Scope | Unblocks |
| --- | --- | --- | --- |
| GROC-08 | Scotty | Trip/reconciliation seams | GROC-10 E2E |
| GROC-09 | Scotty | Observability + fixtures | GROC-10 E2E |

**Execution model:** Parallel execution. No mutual blocking. Both unblock **GROC-10** (McCoy, E2E verification gate).

---

## Decision Consolidation Completed

✅ **mccoy-groc-05-verification.md** → `.squad/decisions/consolidated/2026-03-08T21-15-00Z-mccoy-groc05-verification-approved.md`  
✅ **uhura-groc-07-review-ux.md** → `.squad/decisions/consolidated/2026-03-08T21-15-00Z-uhura-groc07-review-ux-decision.md`  
✅ Both decisions appended to `.squad/decisions.md`  
✅ Inbox cleared (0 items remaining)  

---

## Milestone 3 Progress

**Critical path summary:**

| Completed | Task |
| --- | --- |
| ✅ GROC-01 | Schema and lifecycle seams (Sulu) |
| ✅ GROC-02 | Derivation engine (Scotty) |
| ✅ GROC-03 | Refresh orchestration (Scotty) |
| ✅ GROC-04 | API router (Scotty) |
| ✅ GROC-05 | Backend verification (McCoy) |
| ✅ GROC-06 | Web API wiring (Uhura) |
| ✅ GROC-07 | Review UX (Uhura) |

**Now ready:**
- GROC-08 (Scotty, trip/reconciliation seams)
- GROC-09 (Scotty, observability)

**Remaining mandatory gates:**
- GROC-10 (McCoy, E2E verification) — depends on GROC-08/GROC-09 completion
- GROC-11 (Kirk, final Milestone 3 acceptance) — depends on GROC-10 completion

---

## Status

✅ **Handoff recorded. Decisions consolidated. GROC-08 and GROC-09 ready for Scotty parallel execution. Zero blocking dependencies.**

Full app remains buildable, testable, and verifiable. Continuous execution can proceed without interruption.
