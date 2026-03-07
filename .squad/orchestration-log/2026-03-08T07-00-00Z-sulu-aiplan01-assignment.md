# AIPLAN-01: Planner SQL Model Tightening — Assigned to Sulu

Date: 2026-03-08T07:00:00Z  
Assigned by: Scribe (on Ashley Hollis authorization)  
Task ID: AIPLAN-01  
Milestone: 2 (Weekly planner and explainable AI suggestions)  
Agent: Sulu

## Task scope

Tighten the planner SQL model and migration seams to close active-draft uniqueness and confirmation idempotency gaps. Finalize regen linkage fields, confirmation idempotency fields, and slot-origin history completeness. The implementation must honor constitution 2.4 (authoritative state boundaries) and 5.4 (explicit confirmation protection).

## Starting context

- Milestone 1 (household + inventory) is complete and approved; SQL-backed household-scoped persistence, idempotent mutation handling, and append-only audit history patterns are validated and in production code.
- Current planner/AI models in `apps/api/app/models/meal_plan.py` and `apps/api/app/models/ai_planning.py` contain substantial scaffolding but require finalization against locked constraints.
- Specification: `.squad/specs/ai-plan-acceptance/feature-spec.md` (§Planner state machine, §AI result handling, §Confirmed plan protection).
- Roadmap constraint: planner mutations and offline-sync conflict handling remain Milestone 4 scope; Milestone 2 must preserve seams without inventing sync shortcuts.

## Acceptance criteria

1. **Active-draft uniqueness:** There is exactly one active draft per (household_id, planned_week) pair at any time; attempting to create a new draft while one exists must return a 409 or yield the existing draft via idempotent POST.
2. **Confirmation idempotency:** Confirming a draft is idempotent on the client mutation ID; duplicate confirm requests for the same draft yield the same confirmed plan without mutation.
3. **Slot-origin history:** Every slot in a draft or confirmed plan carries sufficient metadata to reconstruct which AI result (request/response pair) it originated from, including fallback path and manual edit markers.
4. **Regen linkage:** Per-slot regeneration requests are linked to the parent draft and slot, with request status, response binding, and failure/fallback state persisted.
5. **Migration seams:** All new tables, indexes, and foreign-key constraints ship with explicit migration files ready for review. No implicit schema assumptions; migrations must be repeatable and reversible.

## Dependencies

- Depends on: INF-11 (Milestone 1 completion) — ✅ met
- Unblocks: AIPLAN-02 (planner service/API router) and AIPLAN-04 (worker grounding/validation) once landed

## Constraints

- Constitution 2.4: Drafts, suggestions, and confirmed plans are distinct entities in storage and API shape; no shortcuts that treat AI results as confirmed state.
- Constitution 5.4: Confirmed plan protection is unconditional; new suggestions or drafts must never overwrite an existing confirmed plan without explicit user confirmation.
- No offline sync logic; preserve contract and state boundaries for future Milestone 4 threading.
- Household-scoped uniqueness and authorization; all planner work remains inside the household scope locked by `GET /api/v1/me`.

## Suggested approach

1. Review current schema in `apps/api/app/models/meal_plan.py` and `apps/api/app/models/ai_planning.py`; identify gaps in active-draft, confirmation, and slot-origin fields.
2. Finalize the data model: (household, planned_week, active_draft), (household, planned_week, slots), (slot, ai_result_origin), (request, response, slot_regen_status).
3. Write explicit migration(s) in `apps/api/migrations/` that create/alter tables with all constraints (NOT NULL, UNIQUE, FK, CHECK where appropriate).
4. Add test fixtures or seeds in `apps/api/tests/conftest.py` that demonstrate active-draft uniqueness, confirmation idempotency, and slot-origin linkage.
5. Validate migrations are repeatable and reversible; include in the Milestone 2 test suite.

## Evidence expected at completion

- Finalized `.py` models with docstrings explaining each constraint.
- Migration files in `apps/api/migrations/` ready for schema application.
- Test seeds or fixtures proving active-draft uniqueness, confirmation idempotency, and regen linkage.
- Schema review: all tables, indexes, FKs, and constraints explicitly reviewed against feature-spec requirements.

## Handoff to AIPLAN-02 / AIPLAN-04

Once AIPLAN-01 is approved:
- Scotty can implement AIPLAN-02 (planner service/API router) using the finalized schema.
- Sulu can proceed in parallel to AIPLAN-04 (worker grounding, prompt building, validation) as both depend only on schema, not on the router.

## Sign-off trail

- Requested by: Ashley Hollis (Milestone 2 build authorization)
- Recorded by: Scribe
- Status: **ASSIGNED** to Sulu (2026-03-08T07:00:00Z)
