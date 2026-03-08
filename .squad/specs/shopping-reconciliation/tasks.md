# Shopping Reconciliation Tasks

Date: 2026-03-07
Status: Proposed after spec draft
Depends on:
- Milestone 1 inventory foundation contracts
- Milestone 3 grocery/list confirmation contracts
- Milestone 4 trip execution and offline sync foundations

## 1. Goal
Turn the approved shopping reconciliation spec into implementation slices that preserve a clean review/apply boundary between trip progress and authoritative inventory updates.

## 2. Implementation Task Breakdown

### Task 1 — Define shopping reconciliation data contracts
**Outcome:** client and server share explicit shapes for reviewed shopping outcomes and apply results.

**Work**
- Define shopping reconciliation summary and row-level reviewed outcome shapes.
- Define apply-command payloads including stable mutation identity, source trip reference, reviewed item outcomes, and any inventory mapping/location choices.
- Define apply-result shapes for success, duplicate retry, retryable failure, and review-required failure.
- Define read-models for review screen, applied summary, and linked inventory activity.

**Constitution alignment**
- 2.4 Trustworthy Planning and Inventory
- 6.2 Data Standards

### Task 2 — Persist trip outcome to reconciliation draft boundary
**Outcome:** trip state can feed reconciliation without directly mutating inventory.

**Work**
- Define how checked-off, skipped, edited, and ad hoc trip outcomes are materialized into a reconciliation draft.
- Ensure trip progress remains separate from authoritative inventory transactions.
- Preserve source grocery-list/trip references for later audit and debugging.
- Handle incomplete or ambiguous trip rows so review can surface them clearly.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.4 Trustworthy Planning and Inventory

### Task 3 — Build mobile-friendly review/apply UX
**Outcome:** shoppers can quickly confirm real-world outcomes after the trip.

**Work**
- Add review rows for bought, adjusted quantity, skipped, and ad hoc outcomes.
- Keep the screen phone-friendly with low typing and clear final-action affordance.
- Show whether each row will increase an existing item or create a new inventory item.
- Show clear “inventory not updated yet” messaging until apply succeeds.

**Constitution alignment**
- 2.1 Mobile Shopping First
- 2.7 UX Quality and Reliability
- 6.1 UX and Interaction Standards

### Task 4 — Implement inventory handoff rules
**Outcome:** reviewed shopping outcomes turn into explicit inventory commands safely.

**Work**
- Map bought outcomes to inventory increase or create commands.
- Map skipped outcomes to no-op inventory effect while preserving reconciliation history.
- Enforce inventory unit/location/identity requirements before apply succeeds.
- Link resulting inventory adjustments back to reconciliation and source rows.

**Constitution alignment**
- 2.3 Shared Household Coordination
- 2.4 Trustworthy Planning and Inventory

### Task 5 — Implement idempotent apply behavior
**Outcome:** apply retries and reconnect replay do not duplicate purchased stock.

**Work**
- Require stable client/apply mutation IDs.
- Persist apply receipts transactionally with resulting authoritative records.
- Return duplicate-safe responses for repeated apply attempts.
- Distinguish duplicate replay from validation/conflict failure.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.4 Trustworthy Planning and Inventory

### Task 6 — Support offline review with deferred server apply
**Outcome:** users can inspect and prepare reconciliation while offline without being misled about inventory state.

**Work**
- Allow locally cached trip outcomes to populate the review screen offline.
- Mark apply as pending-online until server acknowledgment succeeds.
- Refresh local state and inventory read models after successful apply.
- Ensure deferred apply interacts correctly with sync/conflict contracts.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.7 UX Quality and Reliability

### Task 7 — Add correction entry points and history linkage
**Outcome:** later mistakes are fixable without rewriting history.

**Work**
- Add entry points from shopping reconciliation or inventory history into later correction flow.
- Link corrections back to the original reconciliation and inventory events where known.
- Surface corrected-later indicators in relevant history/read models.
- Preserve original reconciliation outcome as historical truth of the earlier confirmation.

**Constitution alignment**
- 2.4 Trustworthy Planning and Inventory
- 5.3 Reliability and Observability

### Task 8 — Add automated coverage for shopping reconciliation
**Outcome:** the review/apply contract is provably safe before release.

**Backend/unit**
- mapping bought, partial, skipped, and ad hoc rows into inventory commands
- apply idempotency behavior
- correction linkage rules

**Integration**
- reconciliation apply transaction behavior
- duplicate apply replay
- inventory adjustment linkage to reconciliation rows
- offline-to-online deferred apply path

**Frontend/component or flow**
- mobile review/apply rendering
- inventory-not-updated-yet state
- apply pending, success, and failure states

**E2E priority**
- complete trip and review purchases before inventory update
- apply bought and skipped outcomes successfully
- retry the same apply without duplicate stock changes
- review while offline, reconnect, and apply successfully
- later correct a mistaken applied shopping outcome

**Constitution alignment**
- 5.1 Test Expectations
- 5.2 Release Gates

## 3. Suggested Delivery Order
1. Task 1 — reconciliation data contracts
2. Task 2 — trip-to-review boundary
3. Task 3 — review/apply UX
4. Task 4 — inventory handoff rules
5. Task 5 — idempotent apply behavior
6. Task 6 — offline review with deferred apply
7. Task 7 — correction entry points and history linkage
8. Task 8 — automated coverage and hardening

## 4. Exit Criteria
- Trip progress stays separate from authoritative inventory mutation.
- Users confirm real-world shopping outcomes before inventory changes are committed.
- Shopping apply is idempotent, auditable, and linked to resulting inventory history.
- Offline review makes deferred apply clear without falsely implying inventory already changed.
- Later mistakes can be corrected through compensating events rather than history rewrites.
