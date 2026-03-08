# Grocery Derivation Feature Spec

Date: 2026-03-07
Requested by: Ashley Hollis
Status: Approved
Depends on:
- `.squad/specs/inventory-foundation/feature-spec.md`
- `.squad/specs/offline-sync-conflicts/feature-spec.md`
- Milestone 2 weekly planner and plan-confirmation contracts
- Milestone 3 grocery list review and confirmation flow
- Milestone 4 trip execution read-model and offline sync

## 1. Purpose
Define the MVP grocery derivation rules so a confirmed weekly meal plan and trustworthy household inventory can automatically produce a clear, accurate grocery list that the household can rely on when shopping.

This spec turns the gathered discovery inputs and approved user decisions into an implementation-ready contract for:
- the authoritative inputs to derivation,
- conservative inventory-offset matching behavior,
- ingredient-to-grocery-line expansion and duplicate consolidation,
- remaining-to-buy calculation,
- ad hoc item coexistence alongside derived items,
- automatic refresh triggers,
- explicit non-goals and out-of-scope boundaries,
- offline and shared-household implications,
- downstream shopping-reconciliation alignment.

## 2. Scope

### In scope
- Grocery need calculation from a confirmed meal plan plus trusted household inventory.
- Conservative inventory offset: only obvious same-item, same-unit matches reduce a grocery need.
- Duplicate consolidation: multiple meals needing the same ingredient produce one shopping line with traceability back to all contributing meals.
- Remaining-to-buy calculation when partial inventory coverage exists.
- Grocery list automatic refresh when the trusted meal plan or trusted inventory changes.
- Ad hoc grocery item addition alongside meal-derived grocery lines.
- Meal traceability on consolidated grocery lines.
- Explicit non-goals and MVP scope boundaries.
- Acceptance criteria aligned with the shopping-reconciliation follow-on spec.

### Out of scope
- Fuzzy or semantic ingredient-name matching across different item representations.
- Aggressive cross-unit conversion or complex quantity normalization beyond the same unit boundary.
- Pack-size optimization (e.g., inferring how many 400 g cans cover a 750 g need).
- Store-product mapping, brand resolution, or price/coupon intelligence.
- Required variance reason capture for any grocery derivation decision.
- AI-driven grocery suggestions beyond what falls naturally from the deterministic derivation rules in this spec.
- Post-trip shopping reconciliation rules (covered in `.squad/specs/shopping-reconciliation/feature-spec.md`).

## 3. User Outcome
The household sees a grocery list that honestly reflects what the week's meals need, offset by what they clearly already have, so they can shop with confidence rather than guessing or overbooking.

## 4. Constitution Alignment
- **2.1 Mobile Shopping First:** the derived grocery list must be the source for the mobile trip list and therefore must be phone-readable and confirmation-ready before the trip begins.
- **2.2 Offline Is Required:** a confirmed grocery list snapshot must be available offline during the trip; derivation refresh is an online operation but the produced list is an offline-accessible artifact.
- **2.3 Shared Household Coordination:** when the plan or inventory changes and the grocery list refreshes, the update must not silently clobber ad hoc additions or user adjustments already on the list.
- **2.4 Trustworthy Planning and Inventory:** derivation must not invent offsets it cannot confirm. Unclear inventory matches remain on the grocery list rather than being guessed away.
- **2.6 Food Waste Reduction:** conservative inventory matching helps households buy only what they actually need and use stock they already have when it clearly covers a need.
- **4.1 Spec-First Delivery:** this spec explicitly covers mobile/offline/shared-state/data-integrity implications for downstream implementation.
- **5.1 / 5.2 / 5.3 Quality Gates:** grocery derivation correctness, refresh behavior, offline posture, and ad hoc item coexistence require automated verification, E2E coverage, and diagnosable observability.

## 5. Core MVP Decisions

These decisions are authoritative and not subject to reinterpretation in implementation.

1. **Conservative trust-first inventory matching.** Only obvious same-item, same-unit inventory matches auto-count against a grocery need. MVP should use a shared ingredient identity/link as the preferred safe match when available, with exact-name and exact-unit fallback. Any match that requires semantic inference, unit conversion beyond trivially identical units, or name normalization must not be applied silently; those uncertain needs remain on the grocery list for review.

2. **Duplicate consolidation with traceability.** When two or more meals require the same ingredient and it is clearly the same item and unit, the grocery list shows one consolidated line with the summed quantity. The consolidated line preserves a reference to all meals that contributed to it.

3. **No pack-size or store-product reasoning in MVP.** Grocery derivation stops at ingredient quantities needed. It does not attempt to map quantities to shelf units, pack counts, brands, or specific store products.

4. **Partial inventory coverage shows remaining amount only.** If inventory clearly covers part of a need, the grocery line shows only the remaining amount to buy. The amount covered by inventory is not added to the shopping line.

5. **No assumed pantry staples.** The system does not assume any ingredient is already on hand unless inventory clearly covers it. If a recipe calls for salt, olive oil, or any other common item and inventory does not clearly show sufficient stock, it appears on the grocery list.

6. **Automatic refresh on trusted-state changes.** The grocery list refreshes automatically whenever the confirmed meal plan changes or the trusted inventory changes in a way that affects a derived grocery need. Ad hoc items added by the user are preserved across refresh unless the user explicitly removes them.

7. **Ad hoc items coexist with derived items.** Users may add ad hoc grocery items that are not derived from any meal. These items live alongside meal-derived lines and survive automatic refresh. They are clearly distinguishable from meal-derived lines in read models.

## 6. Authoritative Inputs to Derivation

### 6.1 Confirmed meal plan
Grocery derivation draws from the meal plan in its **confirmed/accepted state only**. A draft or unconfirmed plan slot does not produce grocery needs.

The confirmed meal plan provides:
- meal-plan period (e.g., week reference),
- meal slots with their linked meal or recipe reference,
- per-meal ingredient list with quantities and units as specified in the recipe/meal definition.

If a meal slot has no linked ingredient data, it produces no grocery lines. The user must see empty or incomplete derivation clearly rather than having the system invent needs.

### 6.2 Trusted inventory state
Grocery derivation uses the current authoritative inventory balances. Freshness basis, quantity on hand, primary unit, and active/inactive state are all relevant inputs.

**Trust boundary for inventory matching:**
- Only inventory items with known or estimated freshness are usable for offset; unknown-freshness items may still offset if the user's inventory clearly names and quantities the item, but the system must not extend trust beyond what the inventory record explicitly asserts.
- Inventory items marked inactive or archived do not count toward offsets.
- The quantity used for offset is the committed authoritative balance, not a locally cached or optimistic estimate.

### 6.3 Manual ad hoc items
Users may add grocery items that are not derived from any meal. These are authoritative user intent on the grocery list and are treated as first-class list entries alongside derived items. See Section 11 for ad hoc item rules.

### 6.4 User adjustments to derived lines
Users may adjust the quantity on a derived grocery line (e.g., to add a buffer) or remove a derived line they believe is already covered. These adjustments are stored as explicit user overrides on the derived line, not by modifying the underlying recipe or inventory record. User overrides survive automatic refresh.

## 7. Derivation Rules

### 7.1 Meal ingredient expansion
For each confirmed meal slot in the plan period:
1. Retrieve the ingredient list for the linked meal or recipe.
2. For each ingredient, produce a **raw grocery need** entry with:
   - ingredient name reference,
   - required quantity,
   - required unit,
   - source meal slot reference.
3. If a meal slot has no linked ingredient data, produce no grocery needs for that slot and surface a visible indication that the slot could not contribute to derivation.

### 7.2 Conservative inventory offset
For each raw grocery need:
1. Search the active household inventory for an item that is an **obvious same-item, same-unit match**. This means:
   - the inventory item and the grocery need clearly refer to the same ingredient by shared ingredient identity/link (preferred) or exact name fallback, AND
   - the inventory item's primary unit exactly matches the grocery need's unit (no conversion required).
2. If a match is found with sufficient quantity to fully cover the need:
   - the grocery need is considered fully covered by inventory,
   - no grocery line is produced for that need,
   - the offset is recorded so the derivation result is traceable.
3. If a match is found but the inventory quantity partially covers the need:
   - produce a grocery line for the **remaining amount only** (needed quantity minus inventory quantity on hand),
   - record the offset amount and the inventory item reference in the derivation result.
4. If no match is found, or the match requires unit conversion or name inference:
   - produce a grocery line for the **full needed quantity**,
   - do not apply any partial or inferred offset,
   - if the system detected a probable but not certain match, it must not silently apply it; the grocery line appears at full quantity.

**What "obvious same-item, same-unit" means in practice:**
- Shared canonical ingredient identity present on both the recipe ingredient and the inventory item (preferred path).
- Exact case-insensitive name string match with exact unit match when no shared ingredient identity is available (acceptable fallback).
- Any other match—synonym, abbreviation, generic-to-specific, or different unit—does not qualify as obvious and must not reduce the grocery need.

### 7.3 Duplicate consolidation
After inventory offsets are applied:
1. Group all remaining grocery needs by ingredient identity and unit.
2. If two or more remaining needs refer to the same ingredient and same unit:
   - produce one consolidated grocery line with the summed remaining quantity,
   - attach a **meal traceability list** to the consolidated line, listing each meal slot that contributed a quantity to this line and how much each contributed,
   - the consolidated line is presented as a single shopping item.
3. If needs refer to the same ingredient but different units, they must **not** be consolidated. Each unit variant remains as a separate grocery line.

### 7.4 Remaining-to-buy calculation
The quantity shown on a grocery line is always the net amount still needed after confirmed inventory offsets. The derivation engine should preserve and expose:
- the original recipe-required amount,
- the amount already covered by inventory (if any),
- the remaining amount to buy (what appears as the shopping quantity),
- the inventory item reference used for the offset (if any).

This traceability data supports the shopping-reconciliation follow-on behavior and household transparency.

### 7.5 Staple handling
The system must not assume any ingredient is already available unless inventory explicitly covers it. Staples such as oil, salt, spices, flour, sugar, or other common pantry items are subject to the same conservative matching rules as any other ingredient. If the household inventory does not clearly show sufficient stock, the staple appears on the grocery list.

### 7.6 Meal traceability on consolidated lines
Every consolidated grocery line must expose, at minimum:
- the list of source meal names or slot references that contributed to this line,
- the per-meal contribution quantity when derivation detail is requested.

This traceability enables users to understand why an item is on the list and supports shopping reconciliation in attributing purchases back to planned meals.

### 7.7 Automatic refresh triggers
The grocery list derivation result should refresh automatically when any of the following occur:
- a meal slot in the active confirmed plan is added, changed, or removed,
- a confirmed meal plan is replaced by a new confirmed plan for the same period,
- an inventory item is created, updated, or corrected in a way that changes the authoritative quantity or unit for an item that appears in the current derivation,
- an inventory item used in the current derivation is archived or deactivated.

**Refresh behavior during a trip:** once a trip session begins, the grocery list should not silently re-derive and overwrite items the shopper has already marked. The refresh behavior during an active trip follows the trip execution and sync conflict rules in `.squad/specs/offline-sync-conflicts/feature-spec.md` and the trip mode contracts in Milestone 4. The grocery derivation spec does not define trip-mode refresh conflict behavior.

**Ad hoc items survive refresh.** Automatically refreshing the derived portion of the list must not remove ad hoc items the user added.

**User overrides survive refresh.** Quantity adjustments the user made to derived lines should be flagged after refresh (the underlying need may have changed) but must not be silently discarded. The system should inform the user that the derived quantity changed and let them decide whether to keep their adjusted quantity or adopt the refreshed need.

### 7.8 Ad hoc item coexistence
Ad hoc items:
- are added explicitly by the user, not derived from any meal,
- have a quantity, unit, and display name chosen by the user,
- may optionally have a note but do not require one,
- are clearly distinguished from meal-derived lines in list read models (e.g., via an `origin` field with values like `derived` or `ad_hoc`),
- are not subject to automatic inventory offset by the derivation engine,
- survive automatic refresh of derived content,
- can be removed only through explicit user action,
- are preserved through trip mode as first-class list items.

## 8. Derivation State and Versioning

### 8.1 Grocery list version identity
Each derivation result should be associated with a versioned grocery list. The list version captures:
- the plan period it was derived for,
- the meal-plan version or confirmed-plan identifier used,
- the inventory snapshot reference or approximate inventory-as-of timestamp,
- the derivation timestamp,
- the set of derived lines and ad hoc lines at that version.

This versioning supports:
- downstream mobile caching for offline trip access,
- shopping-reconciliation traceability back to the specific list version used during the trip,
- conflict detection when a refresh occurs while a trip is in progress.

### 8.2 Confirmed versus draft grocery list state
Derivation produces a **draft grocery list**. The user reviews the draft, makes optional adjustments, and confirms the list before a trip begins. The confirmed list becomes the authoritative input to the trip execution flow.

The distinction between draft and confirmed grocery list state is:
- **Draft:** subject to refresh when plan or inventory changes; not yet authoritative for trip execution.
- **Confirmed:** the user has reviewed and approved this list for the upcoming trip; this is the authoritative input handed to trip mode.

Automatic refresh may update a draft list. It must not silently replace a confirmed list without the user's awareness and re-confirmation.

### 8.3 Derivation result record
The system should persist a grocery derivation result record (or equivalent projection) so list state can be:
- fetched by the client without re-computing on every load,
- audited to understand what plan and inventory state produced the current list,
- passed to the trip execution flow with a stable identity,
- linked back from shopping reconciliation to the list version used during a trip.

## 9. Offline and Shared-Household Implications

### 9.1 Offline posture
- The confirmed grocery list must be available offline as a cached snapshot for use during the trip. This is a first-class offline requirement per constitution §2.2.
- Grocery derivation itself (computing the list from plan and inventory) is an online operation; it requires current authoritative inventory and plan state.
- The draft grocery list view may be available offline from a cached snapshot but must clearly indicate it may not reflect the latest plan or inventory.
- The confirmed grocery list snapshot must be stable enough to support independent offline trip execution even if the underlying plan or inventory subsequently changes while the shopper is offline.

### 9.2 Shared-household coordination
- If one household member is on a shopping trip and another member confirms a new meal plan or updates inventory, the derivation may re-run and produce a new draft list.
- The active trip is not interrupted by this re-derivation; the shopper continues against the confirmed list version they started with.
- On reconnect, the sync engine should surface any meaningful divergence between the trip's list version and the currently derived state without silently clobbering the shopper's in-progress work.
- Ad hoc items added by any household member prior to list confirmation should be merged and visible on the shared list, subject to the shared-state coordination rules from the offline sync conflict spec.

### 9.3 Derivation is a derived (not authoritative) state
Grocery derivation results are derived state. They are produced from authoritative inputs (confirmed plan and inventory balances) and can be recomputed when those inputs change. The list is not permanently authoritative until the user confirms it for a trip. Even after confirmation, the confirmed list version is preserved as-is; a new derivation does not retroactively alter the confirmed list a trip is operating against.

## 10. Error and Confidence Posture

### 10.1 When derivation cannot run cleanly
If the confirmed meal plan has incomplete ingredient data for one or more slots, the system should:
- derive what it can from the slots with complete ingredient data,
- surface a clear indication of which meal slots produced no grocery needs (e.g., "2 meals have no ingredient data and could not contribute to the grocery list"),
- not fail silently or block list display while incomplete slots exist.

### 10.2 When inventory data is uncertain
If an inventory item exists but its unit or quantity is ambiguous, the conservative rule applies: do not apply an offset that cannot be confirmed. The grocery line appears at the full needed quantity.

### 10.3 No confidence scoring in MVP
MVP does not expose a numerical confidence score on grocery lines or inventory offsets. The confidence model is binary: an offset either obviously applies (and is applied) or does not (and is not). If a future phase adds confidence scoring, this spec must be updated.

### 10.4 No silent list mutations
The derivation engine and its refresh logic must not silently remove user-added adjustments or ad hoc items. Any refresh that would affect a user adjustment must surface a visible notice.

## 11. Ad Hoc Item Rules

An ad hoc grocery item is one added by a user outside of any meal derivation.

### 11.1 Required fields
- display name (free text),
- quantity (numeric),
- unit (matching inventory unit conventions where practical),
- origin label: `ad_hoc`.

### 11.2 Optional fields
- note or reminder text,
- manual category/aisle tag if the household adds one.

### 11.3 Behavior
- Ad hoc items are not subject to inventory offset by the derivation engine; the user is making a deliberate choice to put them on the list regardless of what inventory shows.
- Ad hoc items are idempotent under the same creation/idempotency rules as other list mutations.
- Ad hoc items appear in the shopping list read model alongside derived items.
- After a trip, ad hoc items participate in the shopping reconciliation flow like any other purchased or skipped item.

## 12. Data and API Direction

### 12.1 Grocery derivation result shape
The persisted derivation result should preserve at minimum:
- `grocery_list_id`
- `grocery_list_version_id`
- `household_id`
- `plan_period_reference`
- `confirmed_plan_version_id` used as input
- `inventory_snapshot_reference` (timestamp or version indicator)
- `derived_at` timestamp
- list of grocery line records (see 12.2)
- list status: `draft` or `confirmed`
- `confirmed_at` timestamp when confirmed

### 12.2 Grocery line record
Each grocery line should preserve at minimum:
- `grocery_line_id`
- `grocery_list_version_id`
- `origin`: `derived` or `ad_hoc`
- `ingredient_name` and optional linked canonical ingredient reference
- `required_quantity` (total needed before offset, for derived lines)
- `offset_quantity` (amount covered by inventory; 0 for ad hoc)
- `shopping_quantity` (remaining to buy = required minus offset)
- `unit`
- `inventory_item_ref` used for offset (when applicable)
- `meal_sources`: list of `{ meal_slot_id, meal_name, contributed_quantity }` for derived lines
- `user_adjusted_quantity` if the user overrode the shopping quantity
- `user_adjustment_note` if provided
- `ad_hoc_note` if provided (for ad hoc lines)
- `active`: true/false for active or removed lines

### 12.3 API read-model expectations
The client should be able to fetch:
- current grocery list summary (derived lines + ad hoc lines, shopping quantities, status),
- line-level detail including meal traceability and offset breakdown,
- list confirmation status and confirmed-at timestamp,
- refresh history or last-derived-at indicator,
- any incomplete-slot warnings from the most recent derivation run.

### 12.4 API command expectations
The API should support at minimum:
- trigger or accept a derivation run for the current confirmed plan period,
- add an ad hoc grocery item,
- adjust the quantity on a derived or ad hoc line,
- remove a line (explicit user action),
- confirm the grocery list for a trip,
- re-derive / refresh the draft list.

All commands that mutate the grocery list must be idempotent and carry a client mutation ID for offline and retry safety.

## 13. User-Visible States
The UX should make these states understandable at list level:
- `no_plan_confirmed` — no confirmed plan to derive from; derivation cannot run
- `deriving` — derivation is in progress
- `draft` — derivation complete; list is ready for review and adjustment
- `stale_draft` — plan or inventory changed after the last derivation; list may be out of date
- `confirming` — user has triggered list confirmation
- `confirmed` — list is confirmed and ready for trip mode
- `trip_in_progress` — a trip session is operating against this confirmed list
- `trip_complete_pending_reconciliation` — trip is done; list is awaiting post-shopping review/apply

Final UI copy can be friendlier, but these states must be represented explicitly at the data and API level.

## 14. Observability Expectations
- Log each derivation run with: plan period, plan version used, inventory snapshot reference, number of raw needs, number of offset needs, number of consolidated lines, number of items not matched.
- Log incomplete-slot indicators separately so they are diagnosable without scanning line-level records.
- Log list confirmation events with actor, household, and list version.
- Emit metrics for: derivation run count, average offset rate (how many needs were reduced by inventory), incomplete-slot rate, ad hoc item addition rate, user adjustment rate, and stale-draft detection rate when telemetry exists.

## 15. Risks and Guardrails
- **Risk: silent over-deduction removes items the household still needs to buy.** Guardrail: conservative trust-first matching—only obvious same-item, same-unit matches apply offsets.
- **Risk: fuzzy name matching quietly removes pantry staples from the list.** Guardrail: explicit prohibition of semantic/fuzzy matching in MVP; non-obvious matches never reduce a grocery need.
- **Risk: duplicate entries confuse shoppers.** Guardrail: consolidation rules produce one line per ingredient-unit pair with meal traceability.
- **Risk: refresh silently removes user adjustments or ad hoc items.** Guardrail: refresh only updates derived lines; ad hoc items and user overrides survive and are flagged when the underlying derived quantity changed.
- **Risk: confirmed trip list is altered mid-trip by a refresh.** Guardrail: confirmed lists are version-stable; a re-derivation does not mutate the confirmed list version the trip is operating against.
- **Risk: pantry staples assumed on hand and missing from list.** Guardrail: no assumed-on-hand behavior in MVP; staples follow the same offset rules as any other ingredient.

## 16. Acceptance Criteria
1. Grocery derivation only runs against the confirmed meal plan. Draft or unconfirmed meal slots produce no grocery needs.
2. For each confirmed meal slot, all ingredients with a linked quantity and unit are expanded to raw grocery need entries.
3. Inventory offset is applied only when the inventory item is an obvious same-item, same-unit match with no conversion or name inference required.
4. When inventory quantity fully covers a grocery need, no grocery line is produced for that need.
5. When inventory quantity partially covers a grocery need, the grocery line shows only the remaining amount to buy.
6. Grocery needs with no inventory match appear at the full required quantity.
7. When two or more meal slots produce needs for the same ingredient and same unit, they are consolidated into one grocery line with the summed quantity and traceability to all contributing meals.
8. Grocery needs for the same ingredient but different units are not consolidated; each remains a separate line.
9. The grocery list includes ingredients from all confirmed meal slots, including common staples, unless inventory clearly and conservatively offsets them.
10. Users can add ad hoc grocery items alongside derived items; ad hoc items are labeled with `origin: ad_hoc` in read models.
11. Ad hoc items survive automatic refresh of the derived portion of the list.
12. User quantity adjustments on derived lines survive refresh; if the underlying derived quantity changed, the system surfaces a visible notice rather than silently discarding the user's value.
13. The grocery list refreshes automatically when the confirmed meal plan changes or when inventory changes affect a derived grocery need.
14. Refreshing the derived list does not silently replace a confirmed list that a trip is already operating against.
15. Grocery lines expose meal traceability: each consolidated line references the contributing meal names and their individual quantity contributions.
16. The derivation result records which inventory items were used for offsets and by how much, so shopping reconciliation can trace purchase outcomes back to the list version.
17. The confirmed grocery list is available as an offline-accessible snapshot for trip mode.
18. The draft grocery list clearly indicates whether it may be stale relative to the latest plan or inventory state.
19. All list-mutating commands are idempotent and accept a client mutation ID for offline retry safety.
20. Automated tests cover: full derivation from a complete plan, partial inventory offset, full inventory offset, no inventory match, consolidated duplicate needs, separate non-consolidated different-unit needs, staple items not assumed on hand, ad hoc item addition, user override survival across refresh, and stale-draft indicator behavior.

## 17. Follow-On Alignment with Shopping Reconciliation
This spec intentionally stops at the confirmed grocery list. The shopping reconciliation spec (`.squad/specs/shopping-reconciliation/feature-spec.md`) picks up from the confirmed list version and governs how trip outcomes become inventory changes. The grocery derivation spec must produce a list state that the reconciliation spec can reliably consume, specifically:
- stable grocery line IDs that the trip and reconciliation flows can reference,
- meal traceability preserved on each line so post-trip analysis can attribute purchases to meals,
- offset data preserved so reconciliation can understand which inventory items were assumed covered when the list was derived.

## 18. Open Follow-On Questions
- Should the derivation result surface per-meal sub-totals in the UI (e.g., "Pasta Bake needs 400 g pasta"), or is the consolidated single line with a traceability detail view sufficient for MVP?
- What is the expected behavior when the confirmed plan has some meals with full ingredient data and others with only a meal name and no ingredients? Should the no-ingredient slots produce a warning on the grocery list, or is the list simply derived from what is available?
- Should user adjustments carry any reason or note field in MVP, or is the adjusted quantity alone sufficient?

## 19. Approval Readiness
This spec is ready for Ashley's review and approval as the MVP grocery derivation plan for Milestone 3. It is implementation-ready at the rule and contract level while leaving exact endpoint naming, schema column names, and UI-level copy to downstream implementation.
