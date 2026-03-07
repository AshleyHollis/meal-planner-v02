# Cooking Reconciliation Feature Spec

Date: 2026-03-07
Requested by: Ashley Hollis
Status: Draft for approval
Depends on:
- `.squad/specs/inventory-foundation/feature-spec.md`
- `.squad/specs/offline-sync-conflicts/feature-spec.md`
- Milestone 2 weekly planner contracts
- Milestone 5 reconciliation implementation foundations

## 1. Purpose
Define the MVP post-cooking reconciliation flow so a cook can confirm what was actually used and what leftovers were created before authoritative inventory changes are committed.

This spec turns the gathered discovery inputs into an implementation-ready contract for:
- separating “meal cooked” context from actual inventory consumption,
- defining the post-cooking review/apply behavior,
- clarifying what is confirmed before ingredient and leftover inventory changes occur,
- mapping reviewed cooking outcomes into inventory decrease/create commands,
- supporting practical substitutions and skipped planned ingredients without required variance reasons,
- defining later correction behavior through compensating inventory events.

## 2. Scope

### In scope
- Post-cooking review/apply flow for planned meals and equivalent cooking events.
- Confirmation of practical cooking outcomes: used, not used/skipped, substituted actual-use entries, and leftovers created.
- Explicit creation of leftovers as first-class inventory outcomes.
- Handoff from reviewed cooking outcomes into authoritative inventory mutations.
- Acceptance criteria and implementation-ready tasks.

### Out of scope
- Full recipe normalization or nutrition accounting.
- Required capture of why a planned ingredient was skipped or substituted.
- Advanced serving-size analytics, waste scoring, or cost accounting.
- Fully offline authoritative cooking apply in MVP.
- Automated recipe-based depletion without user confirmation.

## 3. User Outcome
After cooking, the household can confirm what actually got used and what leftovers now exist, so inventory reflects reality rather than assumptions from the original meal plan.

## 4. Constitution Alignment
- **2.3 Shared Household Coordination:** shared inventory mutations from cooking must be conflict-safe and auditable.
- **2.4 Trustworthy Planning and Inventory:** actual use and leftovers must be explicitly confirmed before stock changes are committed.
- **2.6 Food Waste Reduction:** leftovers are first-class outcomes that can feed future planning and reduce waste.
- **2.7 UX Quality and Reliability:** cooking review, apply, apply failure, and later correction states are part of the feature.
- **4.1 Spec-First Delivery:** this spec covers data-integrity, shared-state, and user-visible behavior before implementation.
- **5.1 / 5.2 Quality Gates:** cooking reconciliation requires automated verification across backend rules, frontend flows, and E2E outcomes.

## 5. Core MVP Decisions
- Marking a meal as cooked or opening a cooking event does **not** automatically mutate inventory.
- Inventory changes happen only after the cook explicitly confirms the reviewed actual-use and leftovers outcome.
- MVP review detail is intentionally practical:
  - what was used,
  - what planned ingredients were not actually used,
  - what substitute or ad hoc ingredients were actually used,
  - what leftovers were created.
- MVP does **not** require reasons for substitutions, skipped ingredients, or leftover amounts.
- If a mistake is discovered later, correction happens through a **later correction flow** that creates compensating inventory events rather than editing past cooking history invisibly.

## 6. Flow Summary

### 6.1 High-level sequence
1. User opens a planned meal or cooking event after or during cooking.
2. The app preloads the expected ingredients or planning context as a draft starting point.
3. The user reviews the actual outcome in practical terms.
4. The user confirms apply.
5. The API creates a cooking reconciliation or cooking event record and emits authoritative inventory mutations for consumed ingredients and leftovers.
6. Inventory/activity history preserves linkage back to the cooking source.

### 6.2 Principle
The meal plan is advisory context for cooking reconciliation. It must not be treated as proof of what was actually consumed.

## 7. Review and Apply Behavior

### 7.1 What the review screen shows
The post-cooking review should show, at minimum:
- meal or cooking-event reference,
- expected ingredient rows when known,
- actual used quantity per reviewed ingredient row,
- skipped/not-used status where applicable,
- ability to add an actual-used ingredient not present in the original expected list,
- leftovers rows with name, quantity, unit, and storage defaults needed for inventory creation,
- a clear final confirmation action before inventory is updated.

### 7.2 MVP practical outcome choices
Each ingredient or outcome row should support practical MVP choices such as:
1. **Used as expected**
2. **Used, but adjust quantity**
3. **Not used / skip this planned ingredient**
4. **Add actual-used ingredient** for substitution or ad hoc use
5. **Create leftovers** with quantity/unit/location details needed by inventory

### 7.3 What the user confirms before inventory changes
Before apply, the user must confirm:
- which ingredients were actually used,
- the actual used quantity for each used ingredient,
- which expected ingredients were not actually used and therefore should not reduce inventory,
- any substitute or ad hoc ingredients that should reduce inventory instead,
- any leftovers that should be created in inventory,
- any required identity or storage-location choices needed to satisfy inventory rules,
- that the reviewed cooking outcome is ready to apply now.

### 7.4 What is intentionally not required in MVP
The user is **not** required to provide:
- why an expected ingredient was skipped,
- why a substitute was used,
- why leftover quantity differs from expectation,
- detailed prep notes or recipe commentary.

## 8. Inventory Commit Boundary

### 8.1 No implicit inventory mutation from planning context
The following must not directly mutate inventory on their own:
- a planned meal existing on the calendar,
- opening a cooking event,
- marking a meal “cooked” before review,
- inferred ingredient use from recipe expectations alone.

### 8.2 Apply transaction expectation
When the user chooses apply:
- the API validates the reviewed cooking payload,
- persists a cooking event or cooking reconciliation record,
- emits explicit inventory decrease/create commands,
- links resulting inventory adjustments back to the cooking source,
- returns a clear applied or failed outcome.

### 8.3 Apply failure behavior
If apply fails:
- the app must not imply inventory was updated,
- the reviewed cooking draft should remain available for retry or amendment,
- retryable failure must be distinguished from duplicate apply and conflict/review-required outcomes.

## 9. Inventory Handoff Rules

### 9.1 Handoff ownership
Cooking reconciliation owns the reviewed actual-use and leftovers outcome. Inventory owns the authoritative consumption and leftover stock mutations emitted from that reviewed outcome.

### 9.2 Handoff rules by outcome
1. **Used existing inventory item**
   - emit `decrease_quantity` inventory mutation,
   - use reason code such as `cooking_consume`,
   - link back to the cooking event and reviewed row.

2. **Skipped planned ingredient**
   - emit no inventory decrease for that row,
   - preserve the reviewed outcome in cooking history so the difference remains understandable.

3. **Added actual-used substitute or ad hoc ingredient**
   - map to an existing inventory item and emit `decrease_quantity`,
   - if no safe item identity exists, require explicit user mapping before apply succeeds.

4. **Created leftovers**
   - emit `create_item` or `increase_quantity` against leftovers inventory location,
   - use reason code such as `leftovers_create`,
   - preserve linkage to the source cooking event.

### 9.3 Guardrails
- Cooking reconciliation must respect the inventory single-primary-unit rule.
- The client must not silently convert units during apply.
- The system must not guess consumption for an ambiguous ingredient identity; it should require explicit user selection.
- The system must not create leftovers implicitly from meal completion alone.

## 10. Leftovers Rules

### 10.1 Leftovers are first-class
Leftovers created during cooking should be represented as explicit inventory outcomes, not notes hidden inside a cooking event only.

### 10.2 Minimum leftovers capture
For each leftover row, MVP should capture:
- display name,
- quantity,
- primary unit,
- storage location defaulting to leftovers-appropriate location,
- optional freshness basis/details when later implementation is ready to collect them.

### 10.3 Leftovers identity posture
- A leftover can create a new leftovers inventory item when no existing leftover item is being continued.
- If the user intentionally adds to an existing leftovers item, the apply flow must make that target explicit rather than silently merging by name.

## 11. Offline and Shared-Household Behavior

### 11.1 Offline posture
- Cooking review drafts may be staged locally if implementation chooses to support draft resilience.
- Final authoritative apply should require server acknowledgment in MVP because it mutates trusted inventory state.
- If offline, the app must state clearly that reviewed cooking outcomes have not yet updated inventory.

### 11.2 Shared-household posture
- A cooking apply command must be idempotent so retry or reconnect does not double-consume ingredients or double-create leftovers.
- If targeted inventory items changed since the cooking draft was prepared in a way that makes apply unsafe, the server should return an explicit conflict/error outcome rather than guessing.
- Household members should be able to understand later from history that a stock change came from cooking reconciliation, not manual editing.

## 12. Correction Behavior

### 12.1 Later correction rule
If the cook later realizes the applied outcome was wrong, the system must use a later correction flow rather than editing the original cooking reconciliation in place.

### 12.2 Correction expectations
The correction flow should:
- reference the original cooking event and affected inventory events when known,
- create compensating inventory increases/decreases or leftover corrections,
- preserve the original cooking event as the previously confirmed outcome,
- make correction chains visible in inventory and activity history.

### 12.3 Examples
- User applied 500g of pasta used but later realizes only 300g was used. Correction creates an inventory increase of 200g linked to the mistaken cooking deduction.
- User forgot to record leftovers. Later correction creates a leftovers inventory event linked to the original cooking event rather than editing history invisibly.
- User recorded the wrong ingredient as consumed. Correction restores the mistaken deduction and applies the intended deduction with explicit linkage.

## 13. Data and API Direction

### 13.1 Minimum cooking reconciliation record
The authoritative cooking record should preserve at least:
- `cooking_event_id` or `cooking_reconciliation_id`
- household and actor
- source meal-plan slot or ad hoc cooking reference when available
- reviewed ingredient outcomes
- reviewed leftover outcomes
- status (`draft_review`, `applying`, `applied`, `failed`, or equivalent)
- apply timestamp
- linkage to resulting inventory adjustment IDs

### 13.2 Apply command shape direction
The cooking apply command should include:
- stable client/apply mutation ID,
- household ID,
- meal or cooking-event reference when applicable,
- reviewed actual-use rows,
- reviewed leftovers rows,
- any explicit inventory identity mappings needed for substitutes or leftovers continuation,
- optional concurrency/version tokens where available.

### 13.3 Read-model expectations
The client should be able to fetch:
- cooking reconciliation summary,
- ingredient-use and leftovers review rows,
- apply result state,
- linked inventory-activity summary after success,
- later correction linkage where applicable.

## 14. User-Visible States
The UX should make these states understandable:
- `cooking_draft`
- `ready_to_apply`
- `apply_pending_online`
- `applying`
- `applied`
- `apply_failed_retryable`
- `apply_failed_review_required`
- `corrected_later`

Final labels can be friendlier, but the behavioral states must be explicit.

## 15. Observability Expectations
- Log cooking apply attempts with correlation IDs and source meal/cooking references.
- Distinguish apply accepted, duplicate apply replay, validation failure, and conflict/review-required outcomes.
- Preserve linkage between cooking rows, leftovers creation, and resulting inventory adjustments.
- Emit metrics later for cooking apply success, leftovers creation rate, skipped-ingredient rate, and correction-after-cooking rate where telemetry exists.

## 16. Risks and Guardrails
- **Risk: meal-plan assumptions silently consume stock.** Guardrail: explicit review/apply confirmation before authoritative inventory mutation.
- **Risk: leftover handling becomes a note instead of stock.** Guardrail: leftovers are explicit inventory outcomes.
- **Risk: retries double-consume ingredients.** Guardrail: idempotent apply command and inventory mutation receipts.
- **Risk: substitution handling becomes opaque.** Guardrail: actual-used ingredients are reviewed explicitly, without forcing narrative reasons.
- **Risk: later mistakes tempt destructive edits.** Guardrail: correction flow uses compensating events.

## 17. Acceptance Criteria
1. Meal-plan context or “meal cooked” status does not directly mutate authoritative inventory.
2. After cooking, the user is presented with a review/apply step before ingredient consumption and leftovers changes are committed.
3. The review/apply step supports practical MVP outcomes only: used, adjusted used quantity, skipped/not used, added actual-used ingredient, and leftovers created.
4. The review/apply step does not require variance reasons in MVP.
5. Inventory changes are committed only after explicit user confirmation of the reviewed cooking outcome.
6. Used ingredients decrease inventory only for the confirmed actual-used quantities.
7. Planned ingredients marked not used create no inventory decrease.
8. Substitute or ad hoc actual-used ingredients can be reviewed and applied through explicit inventory identity mapping rather than hidden inference.
9. Leftovers are created as explicit inventory outcomes linked back to the source cooking event.
10. Cooking apply commands are idempotent so retries or reconnect replay do not double-consume ingredients or double-create leftovers.
11. If connectivity is unavailable at review time, the app clearly indicates that inventory has not yet been updated and final apply remains pending until acknowledged by the server.
12. Later discovered mistakes are corrected through compensating correction flows rather than destructive edits to the original applied cooking record.
13. Inventory/activity history can show which stock changes came from the cooking reconciliation and which later corrections adjusted them.
14. Automated tests cover review/apply success, duplicate apply retry, skipped ingredient, substitute ingredient, leftovers creation, offline deferred apply messaging, and later correction linkage.

## 18. Approval Readiness
This spec is ready for Ashley’s review and approval as the MVP post-cooking reconciliation plan. It is implementation-ready at the behavior and contract level while leaving exact screen layout, endpoint naming, and recipe-detail polish to downstream implementation.
