# Sulu — GROC-01 Grocery Schema Decision

Date: 2026-03-08
Requested by: Ashley Hollis
Task: GROC-01 — tighten grocery schema, lifecycle enums, and migration seams

## Decision

Use a **household-scoped grocery mutation receipt table** plus **version-level incomplete-slot warning payloads** as the Milestone 3 contract seam.

## Why

- Grocery mutations (`add ad hoc`, `adjust quantity`, `remove line`, `confirm list`) all require `client_mutation_id`, so the backend needs a durable replay boundary just like inventory already has. A generic receipt table keyed by `(household_id, client_mutation_id)` keeps retries safe without forcing the line/list tables themselves to become the replay store.
- Incomplete ingredient data is a derivation-run outcome, not a line attribute. Storing incomplete-slot warnings on `grocery_list_versions` keeps the warning attached to the exact plan+inventory snapshot that produced the draft and avoids pretending a missing slot is just another grocery line.

## Implementation impact

- `apps/api/app/models/grocery.py` now includes `GroceryMutationReceipt`, list confirmation mutation IDs, version-level warning storage, offset inventory version references, and active/removed line metadata.
- `apps/api/app/schemas/grocery.py` now exposes parsed incomplete-slot warnings and meal-source traceability so Scotty and Uhura can build the derivation/router/UI layers on the approved contract instead of the placeholder scaffold.
- `apps/api/migrations/versions/rev_20260308_04_groc01_grocery_schema_seams.py` makes the seam reversible for current SQLite-backed development and future migration hardening.

## Cross-team guidance

- Scotty should treat `grocery_mutation_receipts` as the authoritative idempotency seam when implementing GROC-03/GROC-04 mutation handlers.
- Uhura should consume the warning payload from the current grocery list version and present it as list-level derivation honesty, not as a per-line error badge.
- Spec/McCoy can verify GROC-05 against the new contract names: `confirmed_plan_version`, `required_quantity`, `offset_quantity`, `shopping_quantity`, `active`, and version-level `incomplete_slot_warnings`.
