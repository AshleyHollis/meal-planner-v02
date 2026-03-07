# Cooking Reconciliation Tasks

Date: 2026-03-07
Status: Proposed after spec draft
Depends on:
- Milestone 1 inventory foundation contracts
- Milestone 2 planner/meal context contracts
- Milestone 5 reconciliation implementation foundations

## 1. Goal
Turn the approved cooking reconciliation spec into implementation slices that preserve a clear review/apply boundary between meal context and authoritative inventory consumption/leftovers updates.

## 2. Implementation Task Breakdown

### Task 1 — Define cooking reconciliation data contracts
**Outcome:** client and server share explicit shapes for reviewed actual-use and leftovers outcomes.

**Work**
- Define reviewed ingredient outcome shapes for used, adjusted quantity, skipped, and added actual-used ingredient rows.
- Define leftovers outcome shapes including quantity, unit, location, and target identity when continuing an existing leftovers item.
- Define apply-command payloads including stable mutation identity, source meal/cooking reference, reviewed ingredient rows, and leftovers rows.
- Define apply-result shapes for success, duplicate retry, retryable failure, and review-required failure.

**Constitution alignment**
- 2.4 Trustworthy Planning and Inventory
- 6.2 Data Standards

### Task 2 — Build review/apply UX for actual use and leftovers
**Outcome:** cooks can confirm real-world outcomes without being forced into heavy bookkeeping.

**Work**
- Preload expected ingredient context from the meal plan or cooking draft when available.
- Add review rows for used, adjusted quantity, skipped, added actual-used ingredient, and leftovers creation.
- Keep the flow clear about what will and will not change in inventory before apply.
- Ensure the UX works on typical web and mobile-sized cooking contexts even if cooking is not as phone-centric as trip mode.

**Constitution alignment**
- 2.4 Trustworthy Planning and Inventory
- 2.7 UX Quality and Reliability
- 6.1 UX and Interaction Standards

### Task 3 — Implement ingredient consumption handoff rules
**Outcome:** reviewed actual-used outcomes map into explicit inventory decrease commands safely.

**Work**
- Map confirmed ingredient usage to inventory decrease commands with source linkage.
- Treat skipped planned ingredients as no-op inventory rows while preserving cooking history.
- Require explicit item mapping for substitute/ad hoc actual-used ingredients when identity is ambiguous.
- Enforce inventory unit and non-negative balance rules during apply.

**Constitution alignment**
- 2.3 Shared Household Coordination
- 2.4 Trustworthy Planning and Inventory

### Task 4 — Implement leftovers creation rules
**Outcome:** leftovers become first-class inventory records instead of hidden notes.

**Work**
- Support leftovers create-item and increase-existing-leftovers behaviors with explicit target choice.
- Capture location and any freshness metadata supported by current inventory contracts.
- Link leftovers inventory events back to the source cooking event.
- Prevent silent name-based merging when the user has not confirmed the target leftover identity.

**Constitution alignment**
- 2.4 Trustworthy Planning and Inventory
- 2.6 Food Waste Reduction

### Task 5 — Implement idempotent apply behavior
**Outcome:** retries and reconnect replay do not duplicate consumption or leftovers creation.

**Work**
- Require stable client/apply mutation IDs.
- Persist apply receipts transactionally with resulting authoritative records.
- Return duplicate-safe responses for repeated apply attempts.
- Distinguish duplicate replay from validation/conflict failure.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.4 Trustworthy Planning and Inventory

### Task 6 — Support offline draft resilience with deferred apply
**Outcome:** reviewed cooking drafts can survive network interruption without falsely implying inventory already changed.

**Work**
- Preserve local cooking review drafts if implementation supports draft durability.
- Mark apply as pending-online until server acknowledgment succeeds.
- Refresh inventory and cooking read models after successful apply.
- Ensure deferred apply aligns with shared sync/conflict rules for trusted inventory mutations.

**Constitution alignment**
- 2.2 Offline Is Required
- 2.7 UX Quality and Reliability

### Task 7 — Add correction entry points and history linkage
**Outcome:** later mistakes are fixable without rewriting cooking or inventory history.

**Work**
- Add entry points from cooking history or inventory history into later correction flow.
- Link corrections back to the original cooking event and inventory events where known.
- Surface corrected-later indicators in cooking and inventory read models.
- Preserve the original applied cooking record as historical truth of the earlier confirmation.

**Constitution alignment**
- 2.4 Trustworthy Planning and Inventory
- 5.3 Reliability and Observability

### Task 8 — Add automated coverage for cooking reconciliation
**Outcome:** actual-use and leftovers rules are provably safe before release.

**Backend/unit**
- mapping used, skipped, substitute, and leftovers rows into inventory commands
- apply idempotency behavior
- correction linkage rules

**Integration**
- cooking apply transaction behavior
- duplicate apply replay
- inventory adjustment linkage to cooking rows
- leftovers create/increase behavior

**Frontend/component or flow**
- review/apply rendering for ingredient rows and leftovers
- inventory-not-updated-yet messaging
- apply pending, success, and failure states

**E2E priority**
- review actual use before inventory update
- apply used and skipped ingredient outcomes successfully
- create leftovers and verify future inventory visibility
- retry the same apply without duplicate consumption or leftovers
- later correct a mistaken applied cooking outcome

**Constitution alignment**
- 5.1 Test Expectations
- 5.2 Release Gates

## 3. Suggested Delivery Order
1. Task 1 — cooking reconciliation data contracts
2. Task 2 — review/apply UX
3. Task 3 — ingredient consumption handoff
4. Task 4 — leftovers creation rules
5. Task 5 — idempotent apply behavior
6. Task 6 — offline draft resilience with deferred apply
7. Task 7 — correction entry points and history linkage
8. Task 8 — automated coverage and hardening

## 4. Exit Criteria
- Meal context stays separate from authoritative inventory mutation.
- Users confirm actual ingredient use and leftovers before inventory changes are committed.
- Cooking apply is idempotent, auditable, and linked to resulting inventory history.
- Leftovers are first-class inventory outcomes with clear lineage.
- Later mistakes can be corrected through compensating events rather than history rewrites.
