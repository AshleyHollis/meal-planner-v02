# Orchestration Log: Scotty AIPLAN-02/03 Completion → Sulu/Uhura Parallel Handoff

Date: 2026-03-08T13-00-00Z
Scribe Entry: Milestone 2 backend service/router and lifecycle contracts now stable; parallel frontend and worker execution unlocked.

## Handoff Summary

Scotty completed the two interdependent backend tasks that unblock all downstream Milestone 2 work:

1. **AIPLAN-02: Planner Service and API Router**
   - Household-scoped planner endpoints for suggestion, draft, and confirmation flows
   - Period-based suggestion read for planner page seam (`GET /api/v1/households/{household_id}/plans/suggestion?period=...`)
   - Draft management: open, read, edit, revert, regenerate
   - Confirmation flow with idempotency via `confirmation_client_mutation_id`
   - Confirmed plan reads with backend-owned session enforcement
   - All lifecycle contracts covered by API tests

2. **AIPLAN-03: AI Request Lifecycle Contracts**
   - Canonical request polling read (`GET /api/v1/households/{household_id}/plans/requests/{request_id}`)
   - Request status transitions: `queued` → `generating` → `completed`
   - Household-scoped request idempotency for suggestion generation
   - Active-request deduplication scoped by household + period + slot scope
   - Stale-warning inheritance from suggestions to draft warnings
   - Confirmation idempotency via mutation ID
   - All lifecycle transitions verified by API tests

## Critical Dependencies Now Unblocked

### AIPLAN-04: Worker Grounding, Prompt, Validation, Fallback (Sulu)
- **Blocked by:** AIPLAN-02/03 request/result contract stability
- **Status:** ✅ Unblocked — can begin immediate implementation
- **Contract seam:** Use `GET /api/v1/households/{household_id}/plans/requests/{request_id}` for polling; work on request state machine and worker callable interface
- **Expected outcome:** Worker scaffold replaced with real grounding, prompt building, validation, and fallback paths

### AIPLAN-07: Wire Web Planner Client to Real Endpoints (Uhura)
- **Blocked by:** AIPLAN-02/03 backend contract stability
- **Status:** ✅ Unblocked — can begin immediate implementation
- **Contract seam:** Switch from `planner-api.ts` mock scaffolding to real `/api/v1/households/{household_id}/plans/*` endpoints
- **Expected outcome:** Frontend suggestion, draft, and confirmation flows wired to backend API

## Parallel Execution Path

Both Sulu and Uhura can now proceed **in parallel** without inter-thread blocking:

```
AIPLAN-02/03 (Scotty) ✅ DONE
    ├─ AIPLAN-04 (Sulu) → AIPLAN-05 (Scotty confirmation/stale) → AIPLAN-06 (McCoy gate)
    └─ AIPLAN-07 (Uhura) → AIPLAN-08 (Uhura UX) → AIPLAN-11 (McCoy E2E)
```

AIPLAN-04 and AIPLAN-07 have no direct inter-dependencies; both depend only on the now-locked AIPLAN-02/03 contract.

AIPLAN-05 (confirmation/stale logic) depends on both AIPLAN-02/03 (backend seam) and AIPLAN-04 (worker execution path being callable), so Scotty follows Sulu.

## Decision Consolidation

**Inbox file merged:**
- `scotty-aiplan-02-03-backend.md` → merged into `.squad/decisions.md`
  - Rationale: Period-based suggestion read keeps planner page seam; request polling is canonical lifecycle contract; draft revert uses persisted AI lineage
  - Consequences: Separates suggestion/draft/confirmed states cleanly; enables AIPLAN-04/07 parallel work; avoids hidden draft-only snapshots

**Inbox status:** 1 file remaining (kirk-publish-history-repair.md — already in log; ready for later archival)

## Constraints Preserved

- ✅ Confirmed-plan-protection: new suggestions never mutate existing confirmed plans (API tested)
- ✅ Authoritative-state distinction: suggestion, draft, confirmed remain separate
- ✅ AI-advisory-only: suggestions are preview-only until confirmed
- ✅ Household scope: all endpoint enforcement verified
- ✅ Session-owned: backend owns scope decisions

## Verification Baseline

Latest approved checks from Milestone 1:
- `npm run lint:web` ✅
- `npm run typecheck:web` ✅
- `npm run build:web` ✅
- `npm --prefix apps\web run test` ✅ (16 tests)
- `python -m pytest apps\api\tests` ✅ (111+ tests covering AIPLAN-02/03)

## Next Team Actions

1. **Sulu (AIPLAN-04):** Begin worker implementation using locked request/result contract; replace scaffold with real grounding/prompt/validation/fallback
2. **Uhura (AIPLAN-07):** Begin frontend wiring to real API endpoints; switch planner-api.ts from mocks to live backend calls
3. **Scotty (AIPLAN-05 follow-up):** Prepare confirmation/stale/history logic once AIPLAN-04 worker is callable
4. **McCoy (AIPLAN-06):** Stage acceptance gate testing for backend/worker contract slice once AIPLAN-04 has runnable code
5. **Kirk (Milestone 2 tracking):** Maintain progress ledger as work advances

No blockers detected. Both threads ready to proceed.
