# Sulu History

## Project Context
- **User:** Ashley Hollis
- **Project:** AI-Assisted Household Meal Planner
- **Stack:** REST API, modern web UI, AI assistance, inventory/product mapping workflows
- **Description:** Build a connected household meal planning platform spanning inventory, meal plans, substitutions, store mapping, shopping trips, and inventory updates after shopping or cooking.
- **Team casting:** Star Trek TOS first.

## Learnings
- Team initialized on 2026-03-07 for Ashley Hollis.
- Current focus is spec-first setup for the AI-assisted household meal planning platform.
- Wave 1 backend idempotency receipts must be scoped by `(household_id, client_mutation_id)`; global mutation-ID replay caches cause cross-household write suppression.
- The relevant backend/API validation suite for the current inventory/session slice is `python -m pytest tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api`.
- INF-02 introduced `households` + `household_memberships` as the tenancy root for inventory persistence, and the SQLite model harness now enables foreign-key enforcement so invalid cross-table references fail in tests instead of hiding until production.
- Deterministic dual-household seed fixtures should reuse the same client mutation ID across households to prove idempotency scope without relying on random UUID collisions.

## Wave 1 — Data Model Foundation (2026-03-07)

### What was built
Implemented the full persistent model and schema contract layer for all approved MVP specs in one wave:

**SQLAlchemy ORM models** (`apps/api/app/models/`):
- `inventory.py` — `InventoryItem`, `InventoryAdjustment`, `MutationReceipt` with append-only correction chaining, idempotency unique constraint, Numeric(14,4) fixed-precision quantities.
- `meal_plan.py` — `MealPlan`, `MealPlanSlot`, `MealPlanSlotHistory` capturing draft/confirmed lifecycle, slot origin (ai_suggested/user_edited/manually_added), and AI audit metadata stored at confirmation time.
- `grocery.py` — `GroceryList`, `GroceryListVersion`, `GroceryListItem` with explicit version tracking, meal_sources JSON traceability, ad_hoc vs meal_derived origin, partial inventory offset fields.
- `reconciliation.py` — `ShoppingReconciliation`, `ShoppingReconciliationRow`, `CookingEvent`, `CookingIngredientRow`, `LeftoverRow` with idempotent apply mutation IDs and linkage back to inventory adjustments.
- `ai_planning.py` — `AISuggestionRequest`, `AISuggestionResult`, `AISuggestionSlot` with idempotency key uniqueness, versioning fields (prompt/policy/context/result contract), grounding hash, and fallback/stale flags.

**Pydantic v2 schemas** (`apps/api/app/schemas/`):
- `enums.py` — All domain enumerations as `str, Enum` for safe serialization: StorageLocation, FreshnessBasis, MutationType, ReasonCode, MealPlanStatus, SlotOrigin, GroceryListStatus, GroceryItemOrigin, ReconciliationStatus, ShoppingOutcome, CookingOutcome, AISuggestionStatus.
- `inventory.py`, `meal_plan.py`, `grocery.py`, `reconciliation.py`, `ai_planning.py` — Command/query contract shapes for all bounded contexts.

**Tests** (68 passing):
- `tests/models/` — SQLite in-memory integration tests for all ORM models, covering relationships, defaults, constraint enforcement (unique mutation receipts, unique AI idempotency keys), correction chaining, leftover creation.
- `tests/schemas/` — Pydantic validation tests covering required fields, enum coercion, negative-quantity rejection, empty-name rejection, and command shape composition.

### Decisions made with cross-team impact
- Wrote `sulu-wave1-data.md` to `.squad/decisions/inbox/` covering: SQLAlchemy as ORM choice, Numeric(14,4) as quantity precision standard, JSON string columns for array fields (meal_sources, reason_codes, etc.), and deferred FK wiring for cross-bounded-context references.

### What this enables
- Scotty can wire database session, Alembic migrations, and API router stubs directly against these models.
- Spec can verify traceability fields (meal_sources, causal_workflow_id, corrects_adjustment_id) are present at the schema layer before E2E tests are written.
- Kirk can plan endpoint work against confirmed schema shapes.

## INF-02 — Household-Scoped Inventory Schema (2026-03-08)

### What was built
- Added SQLAlchemy `Household` and `HouseholdMembership` models as the persistence root for household-scoped inventory.
- Wired `InventoryItem`, `InventoryAdjustment`, and `MutationReceipt` back to `households` with foreign keys plus DB-level constraints for non-negative quantity/version, freshness-basis date semantics, self-correction prevention, and per-household idempotency uniqueness.
- Added deterministic two-household seed fixtures and model tests that prove inventory, adjustments, and receipts stay isolated even when both households reuse the same `client_mutation_id`.
- Tightened the SQLite model harness to enforce foreign keys, then updated the leftover-row model test to create its referenced inventory rows explicitly.

### Validation
- `python -m pytest tests\models tests\schemas tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api` passed after the schema work.

### Decisions made with cross-team impact
- Logged `sulu-inf-02-schema.md` in `.squad/decisions/inbox/` so Scotty and Spec can treat household tables, per-household receipt uniqueness, and DB-enforced freshness semantics as approved implementation constraints.

## AIPLAN-01 — Planner Model Seams (2026-03-08)

### What was built
- Tightened `MealPlan` to enforce exactly one active draft per household + period while keeping confirmed plans distinct, plus added plan-level AI request/result linkage needed for draft-vs-suggestion-vs-confirmed separation.
- Extended `MealPlanSlot` with stable `slot_key`, summary, AI lineage fields, explanation storage, fallback flag, regen status, and pending regen request linkage so draft slots can preserve provenance through edits/regeneration.
- Tightened `AISuggestionRequest` and `AISuggestionSlot` with household-scoped idempotency, parent draft/slot linkage, and stable slot keys for regen/request-result binding.
- Added reversible planner seam migration files under `apps/api/migrations/versions/` and regression coverage for active-draft uniqueness, household-scoped AI idempotency, slot lineage completeness, and migration upgrade/downgrade behavior.

### Validation
- `python -m pytest tests\models\test_meal_plan_models.py tests\models\test_ai_planning_models.py tests\schemas\test_meal_plan_schemas.py tests\schemas\test_ai_planning_schemas.py tests\test_aiplan01_migration.py` passed.
- `python -m pytest tests` passed (125 tests).
- `python -m compileall app tests migrations` passed.

### Learnings
- Planner slot provenance needs a stable slot key separate from row IDs; using a canonical `<day_of_week>:<meal_type>` seam keeps AI suggestion slots, draft slots, confirmation history, and per-slot regeneration aligned.
- AI request idempotency must stay household-scoped just like inventory mutations; planner request keys that are globally unique would create the same cross-household replay hazard already eliminated in inventory work.
