# Inventory Foundation Feature Spec

Date: 2026-03-07
Requested by: Ashley Hollis
Status: Draft for approval

## 1. Purpose
Define the MVP inventory foundation for `meal-planner-v02` so inventory state stays trustworthy across manual edits, shopping reconciliation, cooking reconciliation, offline retries, and later audit/debug workflows.

This spec turns the already gathered discovery inputs into an implementation-ready contract for:
- inventory mutation types,
- idempotent command handling,
- audit/history expectations,
- compensating corrections,
- freshness behavior,
- quantity and unit rules,
- downstream boundaries for grocery, planner, trip, and reconciliation features.

## 2. Scope

### In scope
- Authoritative household inventory records for pantry, fridge, freezer, and leftovers.
- Explicit mutation event model behind inventory edits.
- Idempotent mutation handling for online and offline-capable clients.
- Audit/history read requirements for household trust and supportability.
- Compensating correction behavior instead of history rewrites.
- MVP freshness model using known, estimated, and unknown freshness states.
- MVP quantity model with one primary stored unit per inventory item.
- Contracts other bounded contexts must use when reading or mutating inventory.

### Out of scope
- Grocery derivation rules beyond the inventory boundary they depend on.
- Detailed trip-mode conflict UX.
- Full recipe normalization or cross-unit conversion engine.
- Advanced waste forecasting, usage prediction, or automated restock logic.
- Phase 2 store-aware product mapping.

## 3. User Outcome
Households can trust that inventory changes are understandable, retry-safe, reviewable later, and correctable without losing the historical truth of what happened.

## 4. Constitution Alignment
- **2.3 Shared Household Coordination:** inventory mutations must be conflict-safe and never silently overwrite shared state.
- **2.4 Trustworthy Planning and Inventory:** mutations must be auditable, idempotent where possible, and reversible or correctable.
- **2.6 Food Waste Reduction:** freshness must be captured clearly enough to support expiry-aware planning and waste reduction.
- **4.1 Spec-First Delivery:** this spec explicitly covers mobile/offline/shared-state/data-integrity implications for downstream implementation.
- **5.1 / 5.2 / 5.3 Quality Gates:** inventory changes require automated verification, retry safety, observability, and conflict/replay coverage.

## 5. Core Decisions
- Inventory editing uses a **hybrid model**: user-facing CRUD/edit flows in the UI, but authoritative stock changes are persisted as **explicit inventory adjustment events**.
- Inventory history is append-only for trust-sensitive changes. Mistakes are fixed with **compensating correction events**, not destructive rewrites.
- Every retryable mutation uses a **client mutation ID / idempotency key** so offline replay and duplicate submissions remain safe.
- Freshness is modeled as **known**, **estimated**, or **unknown**, with exact expiry dates captured when known and explicit labeling when dates are inferred.
- Each inventory item stores exactly **one primary unit** in MVP. Cross-unit conversions are out of scope and must not be implied silently.

## 6. Inventory Domain Model

### 6.1 Authoritative inventory record
Each inventory item should have one current authoritative record containing at least:
- `inventory_item_id`
- `household_id`
- `name` or linked canonical item reference
- `storage_location` (`pantry`, `fridge`, `freezer`, `leftovers`)
- `quantity_on_hand`
- `primary_unit`
- freshness state fields
- active/inactive state
- current server version / concurrency token
- created/updated metadata

The current record is the latest authoritative balance and metadata summary. It is not the only history source.

### 6.2 Inventory adjustment event
Every stock-affecting or trust-relevant correction action should create an adjustment/event record containing at least:
- `inventory_adjustment_id`
- `inventory_item_id`
- `household_id`
- `mutation_type`
- `delta_quantity` when quantity changes
- resulting balance snapshot or before/after summary
- `reason_code`
- actor identity
- request correlation ID
- client mutation ID when applicable
- causal reference to upstream workflow when applicable
- timestamp
- optional note payload

This record is the long-lived audit source for “what happened.”

## 7. Mutation Types
The API should expose explicit mutation types rather than generic opaque overwrite operations.

### 7.1 Core inventory mutation types
1. **create_item**
   - Creates a new inventory item with starting quantity, unit, location, and freshness metadata.
   - Used for manual item entry, initial seeding, and ad hoc additions not yet coming from shopping reconciliation.

2. **set_metadata**
   - Updates non-quantity fields such as display name, storage location, notes, or freshness metadata.
   - Must still be auditable when it changes user-trust data such as freshness basis or location.

3. **increase_quantity**
   - Adds stock to an existing item.
   - Typical sources: manual restock entry, shopping reconciliation, correction after undercount.

4. **decrease_quantity**
   - Removes stock from an existing item.
   - Typical sources: manual adjustment, spoilage removal, partial use not captured through cooking flow, correction after overcount.

5. **set_quantity**
   - Directly sets current balance to a specific value when the user is performing a stock count or an authoritative reset.
   - Must record the before quantity, after quantity, and reason because it is higher risk than delta-based changes.

6. **move_location**
   - Changes storage location without changing identity, for example fridge to freezer.
   - May optionally carry freshness-impact metadata if the user changes freshness confidence at the same time.

7. **archive_item**
   - Marks an item inactive or removed from active inventory views.
   - Should not erase history.

8. **correction**
   - A compensating event that offsets or replaces the effect of an earlier incorrect action without deleting the original event.
   - Must reference the corrected event or corrected state decision when possible.

### 7.2 Workflow-origin reason codes
Mutation records should also capture a reason code so downstream systems can distinguish intent. MVP reason codes should include at least:
- `manual_create`
- `manual_edit`
- `manual_count_reset`
- `shopping_apply`
- `shopping_skip_or_reduce`
- `cooking_consume`
- `leftovers_create`
- `spoilage_or_discard`
- `location_move`
- `correction`
- `system_replay_duplicate` only for receipts/diagnostics, not as a user mutation

### 7.3 Mutation rules
- Prefer **delta mutations** for ordinary increases/decreases.
- Restrict **set_quantity** to explicit count-reset or reconciliation flows because it hides causal detail if overused.
- Location changes and freshness changes must never silently alter quantity.
- The client must not fabricate authoritative derived changes; it sends intent and the API decides the resulting authoritative event(s).

## 8. Idempotency and Concurrency

### 8.1 Idempotency contract
Any mutation that can be retried from the client, sync queue, or network layer must accept a stable `client_mutation_id`.

The server should:
- store a mutation receipt keyed by household plus client mutation ID,
- return the original accepted result for duplicate retries,
- avoid creating duplicate adjustment events or duplicate quantity changes,
- preserve correlation to the first successful authoritative write.

### 8.2 What idempotency must protect against
- mobile retries after temporary network failure,
- offline queue replay after reconnect,
- duplicate button taps,
- API gateway/client retry behavior,
- duplicate sync batch delivery.

### 8.3 Concurrency expectations
- Inventory items exposed to editing must carry a server version or equivalent concurrency token.
- Mutations should include the last-known version when available.
- The API may reject stale mutations with explicit conflict responses rather than guessing.
- Duplicate retry and stale-conflict are different outcomes and must be represented differently.

### 8.4 Batch behavior
If sync uploads send multiple inventory mutations in one batch:
- each mutation remains independently idempotent,
- partial success must be representable,
- one conflicting mutation must not force the server to duplicate already accepted sibling mutations on retry.

## 9. Audit and History Expectations

### 9.1 Required history behavior
Users and support tooling must be able to answer:
- what changed,
- when it changed,
- who changed it,
- why it changed,
- what workflow caused it,
- whether the event was later corrected.

### 9.2 Minimum history fields for UI/support read models
- item identity and household
- action label
- reason code
- actor display reference
- timestamp
- before/after quantity summary where relevant
- freshness before/after summary where relevant
- location before/after summary where relevant
- correction linkage if applicable
- source workflow reference such as shopping reconciliation or cooking event

### 9.3 History retention posture
- Inventory adjustment history is operational trust data and should remain queryable.
- Projection/read-model rebuilds may be disposable; inventory adjustments are not.
- History views may paginate or summarize, but authoritative audit records must remain available.

## 10. Compensating Corrections

### 10.1 Rule
Incorrect inventory actions must be corrected by appending new events, not by mutating or deleting historical records in place.

### 10.2 Correction behavior
A correction event should:
- reference the original event ID when known,
- explain why the correction was needed,
- apply the balancing quantity or metadata correction,
- mark the audit trail so history readers can understand the chain,
- leave the original event visible as corrected rather than pretending it never existed.

### 10.3 Examples
- A shopping reconciliation accidentally adds 4 cans instead of 2. The fix is a correction event decreasing quantity by 2 and linking to the original shopping apply event.
- A cooking event consumes the wrong ingredient item. The fix is one correction event restoring the mistaken deduction and a second intended event applying the correct deduction, or a compound correction flow that records both outcomes clearly.
- A user entered estimated expiry for an item but later confirms the exact date. The metadata correction updates freshness basis while preserving the earlier estimate in history.

### 10.4 Restrictions
- Do not permit silent hard-delete of quantity-changing events in normal product flows.
- Administrative repair tooling, if ever added, must remain exceptional and separately auditable.

## 11. Freshness Behavior

### 11.1 Freshness basis states
Every inventory item must declare one freshness basis:
- **known**: user knows the exact expiry or use-by/best-by date.
- **estimated**: the system or user estimated freshness from a heuristic or approximate knowledge.
- **unknown**: no reliable freshness date is available.

### 11.2 MVP freshness fields
An inventory item should support:
- `freshness_basis` = `known | estimated | unknown`
- `expiry_date` when known
- `estimated_expiry_date` when estimated
- optional `freshness_note`
- `freshness_updated_at`

Only one active date basis should be authoritative at a time:
- `known` items use `expiry_date`
- `estimated` items use `estimated_expiry_date`
- `unknown` items use neither required date

### 11.3 Freshness rules
- The UI and API must clearly label whether freshness is known, estimated, or unknown.
- Estimated freshness must never be rendered as if it were a confirmed date.
- Unknown freshness is valid and should not block inventory creation.
- Switching basis from estimated to known is allowed and should be recorded in history.
- Switching from known to unknown or estimated should require explicit user intent because it reduces precision.

### 11.4 Downstream freshness contract
Downstream consumers may use freshness to:
- show expiry pressure,
- sort inventory views,
- feed future planning/grocery recommendations,
- support later forecasting and waste-reduction features.

However, downstream systems must preserve the basis label and must not treat estimated dates as equivalent to known dates.

## 12. Quantity and Unit Rules

### 12.1 MVP quantity model
Each inventory item has exactly one stored primary unit in MVP.

Examples:
- eggs -> `count`
- milk -> `liters`
- rice -> `grams`
- leftovers chili -> `servings`

### 12.2 Rules
- All authoritative quantity mutations for an item must use that item’s primary unit.
- The system must not silently convert between incompatible units in MVP.
- If a user needs a different unit basis, they must change the item definition explicitly or create a separate item as needed.
- Quantity cannot be negative after a committed mutation unless a later explicit business rule introduces backorder-like semantics, which MVP does not.
- Decimal quantities are allowed only where the chosen unit makes them sensible; implementation should avoid floating-point drift by using a fixed-precision numeric type.

### 12.3 Implications
- Grocery and recipe features must respect the inventory unit boundary rather than assuming a general conversion system exists.
- Item setup UX should steer users toward a practical primary unit because later edits depend on it.
- Direct quantity reset flows must show the unit prominently.

## 13. Downstream Boundaries

### 13.1 Inventory owns
- authoritative quantity on hand,
- storage location,
- freshness basis and current freshness metadata,
- inventory adjustment history,
- correction linkage for trust and debugging.

### 13.2 Grocery/trip owns
- proposed or confirmed shopping intent,
- trip execution outcomes,
- ad hoc in-store list mutations.

Grocery/trip does **not** directly overwrite inventory balances. It hands off authoritative inventory changes through inventory/reconciliation commands.

### 13.3 Reconciliation owns
- converting shopping or cooking outcomes into one or more inventory mutations,
- preserving source-workflow linkage to the originating trip or cooking event,
- presenting review/apply behavior before committing authoritative inventory changes when required by the workflow.

### 13.4 Meal planning and AI own
- advisory or planning context about what may be needed or should be used soon,
- never direct authoritative inventory mutation.

### 13.5 Client boundary
- The client may stage local optimistic views and queue intent offline.
- The client does not compute authoritative final balances as the source of truth.
- The API remains responsible for validation, conflict handling, idempotency, and event persistence.

## 14. API and Read-Model Direction

### 14.1 Command shape expectations
Inventory-related commands should include:
- household ID
- target item ID when applicable
- mutation type
- payload
- actor context
- client mutation ID for retryable flows
- target version/concurrency token when available

### 14.2 Read-model expectations
The API should eventually provide read models for:
- inventory summary by location,
- item detail with freshness and quantity,
- item history/activity feed,
- correction chain visibility,
- conflict/error result surfaces for failed stale mutations.

## 15. Observability Expectations
- Log accepted, duplicate, conflicted, and failed inventory mutations with correlation IDs.
- Preserve source workflow references for shopping/cooking-originated adjustments.
- Make correction chains diagnosable in logs and support tooling.
- Emit metrics for duplicate replay rate, conflict rate, correction rate, and freshness-basis distribution when instrumentation exists.

## 16. Risks and Guardrails
- **Risk: generic overwrite APIs hide causality.** Guardrail: prefer explicit mutation types and reason codes.
- **Risk: stale/offline retries duplicate stock changes.** Guardrail: mandatory idempotency receipts.
- **Risk: estimated freshness is mistaken for fact.** Guardrail: basis label preserved everywhere.
- **Risk: quantity/unit ambiguity breaks grocery correctness later.** Guardrail: one primary stored unit per item and no silent conversions.
- **Risk: correction flows become history erasure.** Guardrail: append-only correction model.

## 17. Acceptance Criteria
1. Inventory item creation supports pantry, fridge, freezer, and leftovers with quantity, primary unit, and freshness basis.
2. The system supports explicit mutation types for create, metadata update, quantity increase, quantity decrease, direct quantity set, location move, archive, and correction.
3. Retryable inventory mutations accept a client mutation ID and duplicate retries do not create duplicate stock changes or duplicate audit events.
4. Stale mutations are distinguishable from duplicate retries and can surface an explicit conflict/error response.
5. Quantity-changing actions create audit/history records that capture actor, time, mutation type, reason code, and before/after or delta context.
6. Corrections append new events and reference the original mistaken action when available; normal flows do not rewrite or delete historical quantity-changing events.
7. Freshness can be stored as known, estimated, or unknown, with exact dates only treated as known when explicitly captured.
8. Estimated freshness remains visibly labeled as estimated in inventory read models and history.
9. Inventory quantity rules enforce one primary stored unit per item and prevent silent cross-unit conversion.
10. Grocery, trip, planner, and AI flows are documented to consume inventory through explicit boundaries rather than directly overwriting inventory balances.
11. Test plans cover idempotent replay, stale concurrency conflict, correction chaining, freshness basis transitions, and quantity/unit validation.

## 18. Open Follow-On Questions
- Should leftovers live in the same primary item table with a location discriminator, or need extra subtyping fields beyond MVP?
- What fixed-precision numeric convention should be standard for decimal quantities?
- Which read-model shape best supports mobile history review without overwhelming the UI?
- How much detail should shopping/cooking reconciliation expose before it emits final inventory mutation commands?

## 19. Approval Readiness
This spec is ready for Ashley’s review and approval as the inventory foundation plan for Milestone 1. It is implementation-ready at the rule/contract level, while leaving schema naming and UI-level polishing to downstream implementation.
