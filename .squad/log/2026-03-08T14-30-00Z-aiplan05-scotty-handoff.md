# AIPLAN-05 Handoff to Scotty

**Date:** 2026-03-08T14-30-00Z  
**Assigned to:** Scotty  
**Task:** AIPLAN-05 — Implement stale detection, confirmation flow, and history writes

## Summary

Scribe recorded AIPLAN-04 and AIPLAN-07 task completions on Ashley Hollis authorization. All upstream dependencies for AIPLAN-05 are now satisfied. AIPLAN-05 (stale detection, confirmation flow, history writes) is assigned to Scotty with no blocking decisions remaining.

## Dependency Status

**All upstream dependencies now complete ✅:**
- AIPLAN-02 (planner API router/service) ✅ Scotty, done 2026-03-08
- AIPLAN-03 (AI request lifecycle contracts) ✅ Scotty, done 2026-03-08
- AIPLAN-04 (worker grounding, prompt, validation, fallback) ✅ Sulu, done 2026-03-08

## AIPLAN-05 Scope

Locked for confirmation flow implementation:

1. **Stale Detection**
   - Detect when preferences, inventory, or meals change after draft was opened.
   - Compare draft open timestamp vs. current preference/inventory/meal state.
   - Warning is visible on confirmation path; stale status does not block (per D2 from AI Plan Acceptance Decisions).

2. **Confirmation Flow**
   - POST `/api/v1/households/{household_id}/plans/draft/{draft_id}/confirm` endpoint.
   - Household-scoped request idempotency via `confirmation_client_mutation_id`.
   - Confirmed plan replaces any previous plan for same household + period only with explicit confirmation.
   - Per D4: New suggestion never auto-overwrites confirmed plan without user confirmation.

3. **History Writes**
   - Confirmed plan record written with AI origin metadata at confirmation time.
   - Per-slot origin (`ai_suggested`, `user_edited`, `manually_added`) preserved.
   - Per-slot AI metadata (request ID, reason codes, prompt version, fallback mode, stale warning flag) written to history/audit record.
   - Per D6: AI provenance labels in background history only, not primary UX.

## Unblocked Dependencies

AIPLAN-05 unblocks:
- **AIPLAN-09** (Scotty, grocery handoff seam contract/test)
- **AIPLAN-10** (Scotty, observability)

## No Blocking Decisions

- Confirmed-plan protection enforcement (per D4) is straightforward: check existing confirmed plan, require explicit user confirmation to replace.
- Stale-warning propagation from worker results already tested in AIPLAN-04 work.
- History persistence model matches Milestone 1 audit patterns (append-only with full context).

## Current Parallel Threads

With AIPLAN-05 now ready_now:
- Scotty: AIPLAN-05 (confirmation/stale/history)
- Uhura: AIPLAN-08 (planner UX) — ready_now
- McCoy: AIPLAN-06 (backend/worker acceptance gate) — can proceed when ready

No blocking decisions or architectural gaps detected.
