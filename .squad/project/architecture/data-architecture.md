# Data Architecture and State Boundaries

Last Updated: 2026-03-07
Status: Draft for review

## 1. Data Architecture Principles
- SQL-backed household state is authoritative.
- Inventory, shopping, and meal-plan transitions must be auditable and understandable.
- Derived views should be rebuildable from authoritative records.
- Offline client state is a durable working copy, not the source of truth.
- Shared-household concurrency must be handled explicitly through versioning and mutation identity.

## 2. Storage Roles

| Storage | Role | Authority level |
| --- | --- | --- |
| Browser IndexedDB | Offline snapshots and pending mutation intents | Non-authoritative |
| SQL Server / Azure SQL | Authoritative operational data | Authoritative |
| Azure Storage Queues | Asynchronous work transport | Non-authoritative |

## 3. Core Bounded Contexts
### 3.1 Identity and Household
Owns:
- user profile linkage to Auth0 subject,
- household records,
- household membership,
- future household roles/permissions.

### 3.2 Inventory
Owns:
- pantry, fridge, freezer, leftovers inventory records,
- quantity and unit tracking,
- freshness/expiry metadata,
- inventory adjustments and correction history.

### 3.3 Meal Planning
Owns:
- meal-plan periods,
- meal slots,
- plan status,
- linked recipes or meal templates,
- substitution notes and planning rationale references.

### 3.4 Grocery and Trip
Owns:
- grocery list versions,
- list items,
- user adjustments,
- trip execution state,
- purchased/skipped/ad hoc outcomes.

### 3.5 Reconciliation and Activity
Owns:
- post-shopping application records,
- cooking events,
- leftovers creation,
- audit/event history,
- reversal/correction metadata.

### 3.6 AI Planning
Owns:
- suggestion request metadata,
- suggestion outputs,
- explanation payloads,
- request/result status lifecycle,
- grounding snapshot references or normalized grounding summaries,
- data-completeness and fallback indicators,
- acceptance/rejection feedback.

AI outputs are advisory records and never replace authoritative meal-plan or inventory tables on their own.
Acceptance of a suggestion only becomes authoritative when the user confirms plan changes through normal meal-plan commands.

## 4. Authoritative vs Derived State

| Category | Examples | Rule |
| --- | --- | --- |
| Authoritative | Inventory balances, meal-plan commitments, household memberships, list confirmations | Only changed through validated API commands |
| Derived | Grocery projections, expiry pressure indicators, planning recommendations, mobile summary read models | Recomputable from authoritative inputs and may be rebuilt |
| Advisory | AI suggestions and explanations | Never authoritative until user confirms through explicit command |

## 5. Recommended Core Entities
- `users`
- `households`
- `household_memberships`
- `inventory_items`
- `inventory_adjustments`
- `meal_plans`
- `meal_plan_slots`
- `recipes_or_templates`
- `grocery_lists`
- `grocery_list_items`
- `trip_sessions`
- `trip_item_mutations`
- `shopping_reconciliations`
- `cooking_events`
- `leftover_records`
- `ai_suggestion_requests`
- `ai_suggestion_results`
- `ai_suggestion_feedback`
- `sync_mutation_receipts`
- `audit_events`

These are architectural anchors, not finalized schema names.

## 6. Concurrency and Versioning
- Every aggregate exposed to offline editing should carry a server version, ETag, or equivalent concurrency token.
- Offline mutations should include:
  - client mutation ID,
  - actor ID,
  - target version if known.
- The API should record mutation receipts so retried uploads can be identified and safely deduplicated.
- Conflict policy must distinguish:
  - duplicate retry,
  - safe concurrent change,
  - user-review conflict.
- AI suggestion requests should also carry a stable request identifier so duplicate clicks or retries do not create needless parallel generations.
- AI suggestion results should reference the meal-plan period and a freshness basis so the UI can mark results stale after relevant inventory or plan changes.

## 7. Auditability
The following operations must be auditable:
- inventory increases/decreases/corrections,
- grocery list confirmations and manual overrides,
- trip completion changes,
- application of purchased items to inventory,
- cooking consumption and leftovers creation,
- acceptance of AI suggestions into a meal plan.

Audit entries should capture:
- actor,
- household,
- action type,
- affected entity reference,
- before/after summary where practical,
- timestamp,
- correlation or causation ID.

## 8. Data Lifecycle Expectations
- Operational records remain queryable for household trust and supportability.
- Derived projections can be refreshed or rebuilt.
- Queue messages are ephemeral and not long-term history.
- AI requests and results should remain queryable long enough to explain what was suggested, what fallback path was used, and whether the user accepted or rejected it.
- Audit retention policy is not yet defined and should be set before production launch.

### 8.1 AI result shape expectations
AI result records should be structured for UI review and testing rather than stored only as opaque text blobs. At minimum they should preserve:
- proposed meals by slot,
- explanation snippets tied to grounding signals such as expiry pressure, preference match, or equipment fit,
- any substitution or grocery-impact notes the UI will surface,
- fallback/data-sparsity indicators,
- request/result timestamps and prompt or contract version references where useful.

## 9. State Boundary Rules
1. The client may cache snapshots, but only the API writes authoritative balances.
2. Workers may compute recommendations or projections, but they do not silently commit user-facing authoritative changes without an explicit domain command.
3. Auth0 proves user identity; the application database decides household access and records household relationships.
4. Grocery generation is derived from meal-plan plus inventory state, but user-reviewed grocery list state becomes authoritative once confirmed.
5. AI grounding data comes from deterministic household/product data sources; the provider never becomes the source of truth for inventory, meal-plan, or grocery state.
6. Acceptance/edit feedback may inform future product evaluation, but MVP does not assume automated online learning or model fine-tuning.

## 10. Known Unresolved Items
- Exact inventory unit model and conversion strategy.
- Exact recipe, ingredient, and substitution normalization level.
- Whether leftovers reuse the same base inventory table or a specialized sub-model.
- Exact expiry representation, including confidence levels and date precision.
- Exact retention, archival, and reporting strategy for audit history.
- Exact storage approach for prompt versions, normalized grounding snapshots, and provider diagnostics.
