# Offline Sync Conflicts Feature Spec

Date: 2026-03-07
Requested by: Ashley Hollis
Status: Approved
Depends on:
- `.squad/specs/inventory-foundation/feature-spec.md`
- Milestone 3 grocery/list confirmation contracts
- Milestone 4 mobile trip mode and sync queue implementation

## 1. Purpose
Define the MVP contract for offline sync conflict handling so mobile trip and related household mutations remain trustworthy under reconnects, duplicate retries, and concurrent edits by other household members.

This spec turns the gathered discovery inputs into an implementation-ready plan for:
- detecting stale and conflicting offline mutations,
- classifying safe replay versus review-required conflict outcomes,
- limiting auto-merge to clearly safe cases,
- surfacing user-visible sync and conflict states,
- defining explicit review choices,
- stopping unsafe replay loops,
- handling stale mutations without silent overwrite.

## 2. Scope

### In scope
- Offline replay of client mutation intents from the IndexedDB-backed sync queue.
- Conflict detection for household mutations that can be queued during MVP trip/offline flows.
- MVP classification rules for duplicate retry, safe auto-merge, and review-required conflicts.
- User-visible sync state and conflict-review UX requirements.
- Retry, replay, and stale-mutation handling rules.
- API/read-model expectations for conflict records, resolution actions, and queue outcomes.
- Automated acceptance criteria and implementation-ready tasks.

### Out of scope
- Real-time collaboration presence or live cursors.
- Phase 2 collaboration policies beyond the MVP primary-planner/shared-household posture.
- Fully automatic semantic merges for overlapping quantity or metadata changes.
- AI-specific conflict handling; AI generation remains online-only for MVP.
- Final visual design polish beyond the required state/flow behavior.

## 3. User Outcome
When a shopper reconnects after working offline, their changes replay safely. Clearly safe retries resolve automatically, but any ambiguous or trust-sensitive merge stops and asks the user to decide instead of silently damaging shared household data.

## 4. Constitution Alignment
- **2.1 Mobile Shopping First:** conflict handling must work clearly on a phone-sized trip flow.
- **2.2 Offline Is Required:** queued offline mutations must define retry, replay, reconciliation, and user-visible recovery.
- **2.3 Shared Household Coordination:** shared-state conflicts must be detected explicitly; silent destructive overwrite is prohibited.
- **2.4 Trustworthy Planning and Inventory:** sync must preserve auditability, idempotency, and recovery paths.
- **2.7 UX Quality and Reliability:** queued, retrying, failed, and conflict states are part of the feature, not deferred polish.
- **4.1 Spec-First Delivery:** this spec covers mobile, offline, shared-state, and data-integrity behavior before implementation.
- **5.1 / 5.2 / 5.3 Quality Gates:** conflict logic requires automated coverage, E2E reconnect scenarios, and diagnosable logs.

## 5. Core MVP Decisions
- The browser queue stores **intent-based mutations**, not whole-record overwrites.
- The API remains the authority for dedupe, stale detection, safe-merge decisions, and conflict creation.
- If the system cannot prove a stale local mutation merges safely with newer server state, it must **stop automatic replay and require explicit user review**.
- MVP auto-merge is intentionally narrow. Only **duplicate retries** and **clearly non-overlapping updates** may auto-merge.
- The conflict review choices for MVP are:
  1. **Keep mine**
  2. **Use server**
  3. **Review details** before choosing
- The following conflict classes always force review in MVP:
  - quantity conflicts,
  - item deletion/archive conflicts,
  - freshness/location conflicts.

## 6. Context and Aggregate Boundaries

### 6.1 Authoritative rule
The server owns authoritative household state. The offline client owns:
- latest cached read-model snapshots,
- pending mutation intents,
- per-mutation local sync status,
- enough local detail to explain conflicts back to the user.

### 6.2 Aggregates this spec covers
This spec applies to queued MVP household mutations in:
- grocery/trip item state,
- trip ad hoc item creation/edit flows,
- inventory-affecting commands that may be queued or replayed through the shared sync pathway,
- related trust-sensitive metadata changes such as archive, freshness, and location changes.

### 6.3 Aggregate rule
Conflicts must be detected and resolved against the authoritative aggregate the mutation targets. Cross-aggregate reasoning may inform the explanation, but resolution is attached to a specific authoritative target and mutation intent.

## 7. Conflict Detection Contract

### 7.1 Required mutation metadata
Every replayable queued mutation should carry at least:
- `client_mutation_id`
- `household_id`
- `actor_id`
- `aggregate_type`
- `aggregate_id` or client-side provisional reference
- `mutation_type`
- mutation payload
- `base_server_version` or sync token if known
- device timestamp
- local queue status

### 7.2 Required server-side comparison inputs
The API should evaluate each uploaded mutation against:
- persisted mutation receipt state,
- the current authoritative aggregate version,
- the last-known base version from the client,
- the specific fields or semantic areas touched by the mutation,
- whether the target aggregate still exists and remains active,
- whether the requested mutation would produce the same authoritative outcome as an already-accepted request.

### 7.3 Detection flow
For each uploaded mutation:
1. Check for an existing mutation receipt keyed to the same dedupe identity.
2. If a matching accepted receipt exists, return the original outcome as a duplicate retry.
3. If the base version is current, validate and apply normally.
4. If the base version is stale, compare the local intent with changes since the client's base version.
5. If the server can prove the stale change is clearly safe, auto-merge and record why.
6. Otherwise create a conflict record, freeze automatic replay for that mutation, and return a review-required outcome.

### 7.4 Conflict record expectations
The system should persist a conflict record or equivalent durable review artifact containing at least:
- `conflict_id`
- `household_id`
- `aggregate_type`
- `aggregate_id`
- `local_mutation_id`
- `mutation_type`
- `base_server_version`
- `current_server_version`
- `conflict_class`
- `requires_review`
- summary of local intent
- summary of base state
- summary of current server state
- created timestamp
- resolution status and resolved-by metadata when completed

## 8. Conflict Classification

### 8.1 MVP classification outcomes
Every stale or replayed mutation must land in exactly one of these outcome classes:

1. **duplicate_retry**
   - Meaning: the same accepted mutation was replayed again.
   - Result: return the original accepted outcome; do not create a new authoritative mutation.

2. **auto_merged_non_overlapping**
   - Meaning: the client's base version is stale, but the newer server changes do not overlap the same semantic field or intent boundary touched by the local mutation.
   - Result: apply the local mutation against the latest server version and record auto-merge metadata.

3. **review_required_quantity**
   - Meaning: the local change and newer server state both affect the same quantity or completion semantics in a way that is not clearly safe.
   - Result: create conflict, stop automatic replay, require user review.

4. **review_required_deleted_or_archived**
   - Meaning: the client mutated an item that the server deleted, archived, or otherwise removed from active state after the client's base version.
   - Result: create conflict, stop automatic replay, require user review.

5. **review_required_freshness_or_location**
   - Meaning: the client mutated freshness or storage-location data on an item whose freshness/location basis changed on the server since the base version.
   - Result: create conflict, stop automatic replay, require user review.

6. **review_required_other_unsafe**
   - Meaning: stale change exists, but the system cannot prove a safe merge under MVP rules.
   - Result: create conflict, stop automatic replay, require user review.

### 8.2 What “clearly safe” means in MVP
A change is only clearly safe when all of the following are true:
- the replay is not already a duplicate receipt case,
- the server can deterministically identify the semantic area touched by the local mutation,
- newer server changes do not touch that same semantic area,
- applying the local mutation on top of current server state will not hide another actor's change,
- the result remains auditable and understandable later.

### 8.3 Classification priority
When multiple checks could apply, use this order:
1. duplicate retry
2. apply normally with current version
3. safe non-overlapping auto-merge
4. review-required conflict

The system should prefer review over cleverness when classification is ambiguous.

## 9. Auto-Merge Boundaries

### 9.1 Allowed auto-merge cases in MVP
MVP auto-merge is limited to clearly safe cases such as:
- duplicate retries already protected by mutation receipts,
- non-overlapping updates to different records,
- non-overlapping updates to different semantic fields of the same record when the server can prove independence,
- independent ad hoc additions that do not collide on the same authoritative item identity.

### 9.2 Forbidden auto-merge cases in MVP
The system must not auto-merge when the stale local mutation touches:
- the same item quantity or shopping completion quantity changed by newer server state,
- an item that was deleted or archived on the server,
- freshness basis, freshness date, or storage location also changed on the server,
- any case where the server cannot explain a deterministic merge in product terms,
- any case where merge would require hidden arithmetic reconciliation or guess user intent.

### 9.3 Audit expectation for auto-merge
When auto-merge occurs, the system should preserve:
- the original client mutation ID,
- the stale base version,
- the current server version used for merge,
- the reason the merge was considered safe.

Auto-merge is allowed only when the resulting audit trail remains understandable.

## 10. Review-Required Conflict Types

### 10.1 Quantity conflicts
Always require review in MVP when the same authoritative quantity meaning changed on both sides after the client's base version, including:
- inventory quantity adjustments on the same item,
- shopping/trip quantity edits on the same item,
- purchase/check-off state changes that imply quantity or completion differences.

### 10.2 Item deletion or archive conflicts
Always require review in MVP when:
- the local mutation targets an item that no longer exists in active server state,
- the server archived the item after the client went offline,
- the local mutation would effectively resurrect or mutate a removed item without user confirmation.

### 10.3 Freshness or location conflicts
Always require review in MVP when:
- the local mutation changes freshness basis or freshness date and the server did too,
- the local mutation changes storage location and the server changed location or freshness,
- the server state makes it unclear whether the local action still applies to the same real-world item condition.

### 10.4 Other ambiguous conflicts
If a stale mutation does not fit a known safe rule and the server cannot explain a safe merge, classify it as review required rather than inventing a merge.

## 11. User-Visible States and Review UX

### 11.1 Required user-visible mutation states
The client should expose per-mutation or per-item state using at least:
- `queued_offline`
- `syncing`
- `synced`
- `retrying`
- `failed_retryable`
- `review_required`
- `resolving`
- `resolved_keep_mine`
- `resolved_use_server`

These names are contract direction; final UI copy can be more human-friendly.

### 11.2 Required review summary behavior
When a review-required conflict exists, the app must show:
- which item or mutation needs review,
- a short label for the conflict class,
- that automatic sync has stopped for this mutation,
- the available next actions.

### 11.3 Required detail behavior
The detailed conflict view should show:
- what the user changed locally,
- what the server changed since the local base version,
- the relevant base snapshot or before-state summary,
- the current server version summary,
- the effect of choosing keep mine versus use server when that can be explained.

### 11.4 Review choices
MVP review flow must offer:
1. **Keep mine**
   - preserves the user's intent by creating a new resolution command against the latest server state,
   - must use a new mutation ID linked back to the conflict record,
   - must not silently discard the server-side audit history.

2. **Use server**
   - accepts the current authoritative server state,
   - marks the local queued mutation as resolved/discarded,
   - refreshes the local snapshot from the server.

3. **Review details**
   - opens the detailed comparison,
   - is not itself a final resolution.

### 11.5 UX guardrails
- The app must not hide a conflict behind a generic “sync failed” message when the server knows review is required.
- The app must preserve the user's local intent long enough for review rather than dropping it.
- Conflict UX must be usable on mobile and must not require desktop-only detail panels.

## 12. Retry, Replay, and Queue Rules

### 12.1 Retryable failure vs review-required conflict
The sync engine must distinguish:
- transient retryable failures, which may keep auto-retrying,
- duplicate retries, which resolve immediately,
- review-required conflicts, which must stop automatic retry until the user resolves them.

### 12.2 Replay rules
- Replay mutations in original intent form.
- Preserve per-aggregate ordering where ordering matters.
- Treat each mutation in a batch as independently dedupable and classifiable.
- Do not re-send already accepted sibling mutations just because one later mutation conflicted.

### 12.3 Retry behavior
- Retry transient network or service failures with bounded backoff and jitter.
- Persist retry count and last error summary locally.
- Stop automatic retries once a mutation becomes `review_required`.
- Surface a user-visible retry state instead of silently spinning forever.

### 12.4 Duplicate receipt behavior
When a duplicate retry is detected:
- return the original authoritative outcome,
- mark the local mutation as applied/synced,
- do not emit a new adjustment/event or second side effect.

### 12.5 Resolution replay behavior
If the user chooses **keep mine**:
- create a new resolution mutation or command,
- link it to the original conflict,
- evaluate it against the latest server version,
- mark the original stale mutation as superseded, not silently erased.

## 13. Stale Mutation Handling

### 13.1 Definition
A mutation is stale when it was prepared against an older server version than the one currently authoritative for the targeted aggregate.

### 13.2 Required stale-mutation outcomes
When a mutation is stale, the system must do one of the following:
- auto-merge only if the stale change is clearly safe,
- create a review-required conflict,
- return duplicate-retry outcome if the stale replay is actually an already-accepted mutation.

### 13.3 What the system must not do
The system must not:
- silently drop the stale local change,
- silently overwrite newer server state,
- keep infinite retry loops going after the server has already classified the mutation as needing review,
- disguise a review-required conflict as a generic validation error.

### 13.4 Local preservation rule
Until the user resolves a stale conflict, the client should preserve:
- the local queued mutation payload,
- local timestamps and status,
- enough comparison data or identifiers to reopen the review screen after refresh/restart.

## 14. API and Read-Model Direction

### 14.1 Upload outcome shape expectations
Sync upload results should make the server outcome explicit per mutation, including:
- mutation identifier,
- outcome class,
- authoritative version after apply when applicable,
- conflict ID when review is required,
- retry guidance when retryable,
- duplicate-retry metadata when deduped.

### 14.2 Conflict read-model expectations
The API should provide a conflict read model containing:
- conflict summary for lists,
- detailed local/base/server comparison,
- allowed resolution actions,
- current resolution status,
- timestamps and actor metadata where safe/useful.

### 14.3 Resolution command expectations
The API should expose explicit resolution commands rather than magical retry semantics, for example:
- resolve conflict with keep mine,
- resolve conflict with use server.

Final endpoint naming stays implementation-level, but the behavior must remain explicit.

## 15. Observability Expectations
- Log duplicate retries, auto-merges, review-required conflicts, and manual resolutions with correlation IDs.
- Measure conflict rate by class, auto-merge rate, and retry exhaustion rate when telemetry exists.
- Preserve enough metadata to diagnose why a stale mutation auto-merged versus stopped for review.
- Include conflict and resolution outcomes in E2E evidence for affected flows.

## 16. Risks and Guardrails
- **Risk: silent shared-state damage on reconnect.** Guardrail: explicit review whenever safe merge cannot be proven.
- **Risk: too much automation hides intent.** Guardrail: narrow MVP auto-merge boundaries.
- **Risk: users lose offline work during conflicts.** Guardrail: preserve local intent and offer keep-mine resolution.
- **Risk: endless retry loops degrade trust.** Guardrail: stop automatic replay for review-required conflicts.
- **Risk: mobile conflict UX becomes unusable.** Guardrail: define concise summary states plus detail drill-down, both phone-friendly.

## 17. Acceptance Criteria
1. Replayable offline mutations carry client mutation ID, base version when known, and enough metadata for stale detection.
2. The server distinguishes duplicate retry from stale conflict and returns the original accepted result for duplicates without duplicating side effects.
3. The server classifies stale mutations into explicit outcomes including duplicate retry, safe auto-merge, and review-required conflict.
4. MVP auto-merge is limited to duplicate retries and clearly non-overlapping updates; overlapping or ambiguous merges are not auto-resolved.
5. Quantity conflicts always produce a review-required outcome in MVP.
6. Item deletion/archive conflicts always produce a review-required outcome in MVP.
7. Freshness/location conflicts always produce a review-required outcome in MVP.
8. When review is required, automatic retries stop for that mutation and the client preserves the local intent for later review.
9. The conflict review flow offers keep mine, use server, and review details before final resolution.
10. Choosing keep mine creates an explicit follow-up resolution command linked to the original conflict instead of mutating history invisibly.
11. Choosing use server discards the stale local mutation, refreshes local state, and preserves the conflict audit trail.
12. The client exposes queued, syncing, retrying, review-required, and resolved states clearly on mobile trip flows.
13. Batch replay supports partial success without duplicating already accepted sibling mutations when one mutation conflicts.
14. Automated tests cover duplicate replay, non-overlapping auto-merge, quantity conflict, deletion/archive conflict, freshness/location conflict, review resolution choices, and reconnect behavior.

## 18. Approval Readiness
This spec is ready for Ashley’s review and approval as the MVP offline sync conflict-handling plan. It is implementation-ready at the behavior and contract level while leaving exact endpoint names and final UI styling to downstream implementation.
