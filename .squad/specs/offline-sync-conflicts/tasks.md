# Offline Sync Conflicts Tasks

Date: 2026-03-07
Status: Proposed after spec draft
Depends on:
- Milestone 0 sync scaffolding and test harness setup
- Milestone 1 inventory foundation contracts
- Milestone 3 authoritative grocery/trip list contracts

## 1. Goal
Turn the approved offline sync conflicts spec into implementation slices that preserve trust during reconnect, keep mobile trip flows understandable, and stop unsafe replay from silently overwriting newer household state.

## 2. Implementation Task Breakdown

### Task 1 — Define sync outcome and conflict data contracts
**Outcome:** client and server share explicit shapes for replay outcomes, conflict records, and resolution commands.

**Work**
- Define per-mutation upload result shapes for duplicate retry, auto-merge, retryable failure, and review-required conflict.
- Define durable conflict record fields including local/base/server comparison summaries and resolution metadata.
- Define resolution command payloads for keep mine and use server.
- Define frontend read-model contracts for conflict list and conflict detail screens.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.3 Shared Household Coordination
- 6.2 Data Standards

### Task 2 — Implement mutation receipt and stale-detection foundations
**Outcome:** replayable mutations can be deduped and classified against newer server state.

**Work**
- Require client mutation IDs and base version metadata on replayable sync commands.
- Persist mutation receipts transactionally with authoritative writes where applicable.
- Load current aggregate version and relevant changed fields during replay.
- Distinguish duplicate retry from stale-but-unresolved mutation outcomes.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.4 Trustworthy Planning and Inventory

### Task 3 — Implement MVP conflict classifier
**Outcome:** the API produces deterministic conflict classifications consistent with the feature spec and matrix.

**Work**
- Implement outcome classes for duplicate retry, auto-merged non-overlapping updates, and review-required conflicts.
- Encode explicit always-review rules for quantity, deletion/archive, and freshness/location conflicts.
- Default ambiguous stale cases to review required instead of inferred merge.
- Persist safe-merge rationale when auto-merge occurs.

**Constitution alignment**
- 2.3 Shared Household Coordination
- 2.4 Trustworthy Planning and Inventory

### Task 4 — Freeze unsafe replay and preserve local intent
**Outcome:** review-required conflicts stop automatic sync loops without losing user work.

**Work**
- Mark conflicted mutations as review required in the local queue and server outcome.
- Stop retry scheduling for review-required items.
- Preserve the original local payload and identifiers for later review after app restart.
- Support partial batch success so accepted sibling mutations are not replayed unnecessarily.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.7 UX Quality and Reliability

### Task 5 — Build mobile-friendly conflict review UX
**Outcome:** shoppers can understand and resolve sync conflicts from a phone-sized screen.

**Work**
- Add conflict summary surfaces that identify the item, state, and next actions.
- Add detail view showing local change, base state, and current server state.
- Implement review actions for keep mine and use server.
- Ensure review-required states are distinguishable from generic retryable failures.

**Constitution alignment**
- 2.1 Mobile Shopping First
- 2.7 UX Quality and Reliability
- 6.1 UX and Interaction Standards

### Task 6 — Implement resolution commands and replay behavior
**Outcome:** user decisions create explicit, auditable follow-up outcomes.

**Work**
- Implement keep-mine resolution as a new mutation/command linked to the original conflict.
- Implement use-server resolution as a discard-local-and-refresh path.
- Mark original stale mutations as superseded or resolved rather than silently deleting them.
- Refresh relevant read models after resolution.

**Constitution alignment**
- 2.3 Shared Household Coordination
- 2.4 Trustworthy Planning and Inventory

### Task 7 — Add observability and support diagnostics
**Outcome:** the team can diagnose why conflicts happened and how they were resolved.

**Work**
- Log duplicate retries, safe auto-merges, review-required conflicts, and resolutions with correlation IDs.
- Add metrics for conflict counts by class, auto-merge rate, and retry exhaustion where telemetry exists.
- Expose enough structured detail to support debugging without leaking sensitive data into the client.
- Ensure preview evidence can demonstrate reconnect/conflict scenarios.

**Constitution alignment**
- 5.2 Release Gates
- 5.3 Reliability and Observability

### Task 8 — Add automated coverage for conflict behavior
**Outcome:** reconnect and shared-state safety rules are provably enforced before release.

**Backend/unit**
- duplicate-retry detection
- non-overlapping auto-merge classification
- quantity conflict classification
- deletion/archive conflict classification
- freshness/location conflict classification
- resolution command rules

**Integration**
- mutation receipt dedupe
- stale-version replay against SQL-backed state
- partial batch success behavior
- conflict record persistence and resolution updates

**Frontend/component or flow**
- queued/syncing/retrying/review-required state rendering
- mobile conflict summary and detail rendering
- keep mine and use server action flows

**E2E priority**
- offline mutation queued during trip mode
- reconnect with duplicate replay
- reconnect with safe non-overlapping auto-merge
- reconnect with quantity conflict that requires review
- resolve conflict and confirm final authoritative state

**Constitution alignment**
- 5.1 Test Expectations
- 5.2 Release Gates

## 3. Suggested Delivery Order
1. Task 1 — sync outcome and conflict contracts
2. Task 2 — receipt and stale-detection foundations
3. Task 3 — conflict classifier
4. Task 4 — freeze unsafe replay and local preservation
5. Task 5 — mobile conflict review UX
6. Task 6 — resolution commands and replay
7. Task 7 — observability
8. Task 8 — automated coverage and hardening

## 4. Exit Criteria
- Replayable offline mutations are deduped safely and classified explicitly.
- Unsafe stale mutations stop automatic replay and require user review.
- MVP auto-merge remains limited to duplicate retries and clearly non-overlapping updates.
- Conflict review offers keep mine, use server, and detail inspection on mobile.
- Test evidence covers reconnect, safe merge, always-review conflict types, and resolution flows.
