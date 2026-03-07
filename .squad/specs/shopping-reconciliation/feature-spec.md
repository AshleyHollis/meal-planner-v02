# Shopping Reconciliation Feature Spec

Date: 2026-03-07
Requested by: Ashley Hollis
Status: Draft for approval
Depends on:
- `.squad/specs/inventory-foundation/feature-spec.md`
- `.squad/specs/offline-sync-conflicts/feature-spec.md`
- Milestone 3 grocery review/list confirmation contracts
- Milestone 4 trip execution and offline sync behavior

## 1. Purpose
Define the MVP post-shopping reconciliation flow so trip outcomes become trustworthy inventory updates only after the shopper explicitly reviews and confirms what was actually bought.

This spec turns the gathered discovery inputs into an implementation-ready contract for:
- separating in-trip progress tracking from authoritative inventory changes,
- defining the post-trip review/apply behavior,
- clarifying what must be confirmed before inventory is mutated,
- mapping reviewed shopping outcomes into inventory commands,
- handling skipped and partial outcomes without forcing variance reasons,
- defining later correction behavior when mistakes are noticed after apply.

## 2. Scope

### In scope
- Review/apply flow after a shopping trip or shopping session.
- Confirmation of practical shopping outcomes: bought, partially bought, skipped, and ad hoc purchases.
- User-visible rules for when inventory is and is not updated.
- Handoff from shopping reconciliation into authoritative inventory mutation commands.
- Shared-household and offline-aware expectations for the review/apply step.
- Acceptance criteria and implementation-ready tasks.

### Out of scope
- Grocery derivation rules before the trip.
- Detailed in-store trip interaction design beyond the inputs handed into reconciliation.
- Store-specific product mapping, receipts, pricing, or retailer integrations.
- Required reason capture for variances such as “why skipped” or “why bought less.”
- Later financial/accounting reporting beyond inventory trust needs.

## 3. User Outcome
After shopping, the household can review the real-world trip result in practical terms and apply only the confirmed outcomes to inventory, without silent stock changes caused by checkmarks made during the trip.

## 4. Constitution Alignment
- **2.1 Mobile Shopping First:** the review/apply flow must remain usable on a phone-sized screen after a trip.
- **2.2 Offline Is Required:** trip progress may be captured offline, but final authoritative inventory changes must define replay and recovery rules.
- **2.3 Shared Household Coordination:** shopping outcomes and resulting inventory changes must be conflict-safe and never silently overwrite shared state.
- **2.4 Trustworthy Planning and Inventory:** inventory changes must be auditable, idempotent, and correctable later.
- **2.7 UX Quality and Reliability:** trip-complete, ready-to-review, pending-apply, apply-success, and apply-failure states are part of the feature.
- **4.1 Spec-First Delivery:** this spec covers mobile, offline, shared-state, and data-integrity behavior before implementation.

## 5. Core MVP Decisions
- Trip mode records **shopping progress and outcomes**, not immediate inventory mutations.
- Inventory is updated only when the user completes the **post-shopping review/apply confirmation**.
- MVP review detail is intentionally practical and lightweight:
  - what was bought,
  - what was bought in a reduced quantity,
  - what was skipped,
  - which ad hoc items were bought.
- MVP does **not** require variance reasons for skipped or reduced items.
- If the user notices a mistake later, correction happens through a **later correction flow** that creates compensating inventory events rather than rewriting the original applied outcome.

## 6. Flow Summary

### 6.1 High-level sequence
1. User shops in trip mode and marks progress item by item.
2. Trip mode stores purchased/skipped/ad hoc outcomes as trip state.
3. At trip completion, the app offers a **review purchases before updating inventory** step.
4. The user reviews the practical outcome for each relevant item.
5. The user confirms apply.
6. The API creates a shopping reconciliation record and emits the authoritative inventory mutations in one explicit apply action.
7. Inventory history remains linked back to the shopping reconciliation source.

### 6.2 Critical separation of concerns
- **Trip execution** answers: “What happened while shopping?”
- **Shopping reconciliation** answers: “What inventory changes should be committed now?”
- **Inventory foundation** answers: “How are those committed changes persisted, deduped, audited, and corrected later?”

## 7. Review and Apply Behavior

### 7.1 When review is required
The system must require post-shopping review before inventory changes are committed for:
- checked-off grocery items,
- items with edited purchased quantity,
- items explicitly skipped,
- ad hoc purchased items added during the trip,
- any item whose current trip state is incomplete or ambiguous.

### 7.2 What the review screen shows
The shopping reconciliation review should show, at minimum:
- item name,
- grocery-list quantity or planned amount,
- actual bought outcome,
- skipped outcome where applicable,
- ad hoc status when the item was not on the original list,
- storage-location choice when needed for newly created inventory records,
- whether applying the row will increase an existing item or create a new inventory item.

### 7.3 MVP row outcome choices
Each reviewable row should support one of these practical outcomes:
1. **Bought as marked**
2. **Bought, but adjust quantity**
3. **Skipped**
4. **Not purchased / remove trip check-off mistake before apply**
5. **Ad hoc bought item** with quantity and unit compatible with inventory rules

These choices should use simple labels in the UI; exact copy is implementation-level.

### 7.4 What the user confirms before inventory changes
Before apply, the user must confirm:
- which items were actually bought,
- the final bought quantity for each bought item,
- which items were skipped and therefore should not affect inventory,
- any ad hoc purchased items that should be added to inventory,
- any required inventory target identity or storage-location choice for ambiguous cases,
- that the review is ready to apply to household inventory now.

### 7.5 What is intentionally not required in MVP
The user is **not** required to enter:
- why an item was skipped,
- why a quantity differed from plan,
- receipt totals or prices,
- brand/store details,
- per-item notes unless later implementation chooses to allow optional notes.

## 8. Inventory Commit Boundary

### 8.1 No implicit inventory mutation during the trip
The following trip actions must not directly mutate inventory:
- checking off a grocery item,
- marking an item skipped in-store,
- editing expected purchase quantity during the trip,
- adding an ad hoc trip item.

These are trip outcomes only until review/apply confirmation succeeds.

### 8.2 Apply transaction expectation
When the user chooses apply:
- the API should validate the reviewed payload,
- persist a `shopping_reconciliation` or equivalent authoritative record,
- create the required inventory commands/events,
- persist audit linkage between the reconciliation and resulting inventory adjustments,
- return an explicit applied or failed outcome.

### 8.3 If apply does not complete
If the apply attempt fails:
- no partial invisible inventory mutation should be presented as successful,
- the user must see whether the apply is retryable, already applied via idempotent receipt, or blocked by a review/conflict issue,
- the reviewed shopping outcome should remain available for retry or correction before any new apply attempt.

## 9. Inventory Handoff Rules

### 9.1 Handoff ownership
Shopping reconciliation owns the reviewed shopping-outcome record. Inventory owns the authoritative stock mutations created from that record.

### 9.2 Handoff rules by outcome
1. **Bought item mapped to existing inventory item**
   - emit `increase_quantity` inventory mutation,
   - preserve source reason code such as `shopping_apply`,
   - link the inventory event back to the shopping reconciliation and source row.

2. **Bought item with no existing inventory record**
   - emit `create_item` plus starting quantity, or equivalent inventory creation command,
   - require any missing location/unit choices needed by inventory rules before apply succeeds.

3. **Partially bought item**
   - apply only the confirmed bought quantity,
   - do not create a negative or compensating event for the unbought remainder,
   - preserve the grocery/trip outcome that the item was not fully fulfilled.

4. **Skipped item**
   - create no inventory quantity increase,
   - preserve the shopping reconciliation record so history can explain why the grocery item did not enter inventory.

5. **Ad hoc purchased item**
   - treat as a reviewed bought item,
   - either match to an existing inventory item or create a new one,
   - require enough data to satisfy inventory quantity/unit/location rules.

### 9.3 Unit and identity guardrails
- Shopping reconciliation must respect the inventory single-primary-unit rule.
- The client must not silently convert units during apply.
- If a bought item cannot be safely mapped to an authoritative inventory identity, apply must stop and ask for explicit user choice rather than guessing.

## 10. Offline and Shared-Household Behavior

### 10.1 Offline posture
- Trip progress may be captured offline using the trip/offline sync contracts.
- The reviewed shopping draft may be shown offline from local data.
- Final authoritative **apply to inventory** should require server acknowledgment in MVP because it creates authoritative stock changes and audit records.

### 10.2 Review while offline
If the user reaches the reconciliation step while offline:
- the app may let them inspect and locally stage review changes,
- the app must clearly show that inventory has **not** been updated yet,
- final apply remains pending until connectivity returns and the server accepts the command.

### 10.3 Shared-household coordination
- Other household members may see trip progress according to trip/list sync rules, but inventory remains unchanged until apply succeeds.
- The reconciliation apply flow must use idempotent command identity so retries do not double-add purchased stock.
- If authoritative inventory or referenced items changed in a way that makes apply ambiguous, the server should return an explicit conflict/error outcome rather than guessing.

## 11. Correction Behavior

### 11.1 Later correction rule
If a user later notices that the applied shopping result was wrong, the system must route them to a later correction flow rather than reopening and mutating the original reconciliation in place.

### 11.2 Correction expectations
The later correction flow should:
- reference the original shopping reconciliation and affected inventory events when known,
- create compensating inventory events that reverse or adjust the mistaken stock effect,
- preserve the original shopping reconciliation history as what was previously confirmed,
- make the correction chain visible in inventory/activity history.

### 11.3 Examples
- User applied 3 bottles of milk but only 2 were actually purchased. Correction creates an inventory decrease of 1 linked to the original shopping apply event.
- User mistakenly marked an ad hoc purchase as bought. Correction creates a compensating decrease or archive path as appropriate.
- User later realizes a skipped item was actually bought and manually added later. That becomes a new correction/addition event rather than editing the past reconciliation record invisibly.

## 12. Data and API Direction

### 12.1 Minimum shopping reconciliation record
The authoritative reconciliation record should preserve at least:
- `shopping_reconciliation_id`
- household and actor
- source trip or grocery-list version reference
- reconciliation status (`draft_review`, `applying`, `applied`, `failed`, or equivalent)
- reviewed item rows with practical outcome fields
- apply timestamp
- correlation to resulting inventory adjustment IDs

### 12.2 Apply command shape direction
The apply command should include:
- stable client/apply mutation ID,
- household ID,
- source trip/session reference,
- reviewed item outcomes,
- any mapping or location selections required for inventory creation,
- optional concurrency/version data for relevant source aggregates when available.

### 12.3 Read-model expectations
The client should be able to fetch:
- shopping reconciliation summary,
- row-level review state,
- apply result state,
- linked inventory-activity summary after success,
- correction linkage after later adjustments.

## 13. User-Visible States
The UX should make these states understandable:
- `trip_in_progress`
- `ready_for_review`
- `review_draft`
- `apply_pending_online`
- `applying`
- `applied`
- `apply_failed_retryable`
- `apply_failed_review_required`
- `corrected_later`

Final copy can be more human-friendly, but the behavior needs explicit states at this level.

## 14. Observability Expectations
- Log reconciliation create/apply attempts with correlation IDs.
- Distinguish apply accepted, duplicate apply replay, validation failure, and conflict/review-required outcomes.
- Preserve linkage from shopping reconciliation rows to resulting inventory adjustments.
- Emit metrics later for apply success rate, skipped-item rate, ad hoc item rate, and correction-after-shopping rate where telemetry exists.

## 15. Risks and Guardrails
- **Risk: trip checkmarks silently change inventory.** Guardrail: explicit review/apply boundary before authoritative mutation.
- **Risk: users are forced into heavy bookkeeping after shopping.** Guardrail: MVP captures only practical outcomes, not variance reasons.
- **Risk: retries duplicate purchased stock.** Guardrail: idempotent apply command and inventory mutation receipts.
- **Risk: ambiguous item mapping creates wrong inventory rows.** Guardrail: require explicit mapping/location input when the system cannot determine a safe target.
- **Risk: later mistakes tempt destructive history edits.** Guardrail: correction flow uses compensating events.

## 16. Acceptance Criteria
1. Trip progress and item check-off do not directly mutate authoritative inventory.
2. After shopping, the user is presented with a review/apply step before inventory changes are committed.
3. The review/apply step supports practical MVP outcomes only: bought, adjusted bought quantity, skipped, and ad hoc bought items.
4. The review/apply step does not require users to provide variance reasons in MVP.
5. Inventory changes are committed only after explicit user confirmation of the reviewed shopping outcome.
6. Bought items increase existing inventory or create new inventory records through explicit inventory commands/events linked back to the shopping reconciliation.
7. Skipped items produce no inventory quantity increase while still remaining visible in the reconciliation history.
8. Partial purchases apply only the confirmed bought quantity and do not invent stock for unbought remainder.
9. Ad hoc purchased items can be reviewed and applied into inventory subject to inventory unit/location rules.
10. Apply commands are idempotent so retries or reconnect replay do not duplicate stock changes.
11. If connectivity is unavailable at review time, the app clearly indicates that inventory has not yet been updated and final apply remains pending until acknowledged by the server.
12. Later discovered mistakes are corrected through a later compensating correction flow rather than destructive edits to the original applied reconciliation.
13. Inventory/activity history can show the source shopping reconciliation for resulting stock changes.
14. Automated tests cover review/apply success, duplicate apply retry, partial purchase, skipped item, ad hoc item, offline review with deferred apply, and later correction linkage.

## 17. Approval Readiness
This spec is ready for Ashley’s review and approval as the MVP post-shopping reconciliation plan. It is implementation-ready at the behavior and contract level while leaving exact screen layout, endpoint naming, and optional polish details to downstream implementation.
