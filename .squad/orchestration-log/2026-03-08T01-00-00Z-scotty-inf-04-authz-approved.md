# INF-04 Orchestration: Household-Scoped Authorization Enforcement

## Metadata
- **Date/Time:** 2026-03-08T01-00-00Z
- **Owner:** Scotty
- **Task:** INF-04 — Enforce household-scoped authorization in inventory APIs
- **Status:** ✅ APPROVED

## Summary

Scotty completed INF-04: inventory reads and mutations now consistently run inside the resolved request household scope on top of the SQL-backed store, with foreign household item IDs hidden behind scoped `404` results and explicit household mismatch attempts still rejected as `403`.

## Deliverable

Inventory authorization layer now proves:
- Household-scoped item reads return `404` for foreign items, never leaking cross-household inventory existence
- Inventory mutations enforce household scope on durable store writes
- History and adjustment lookups stay inside the active household scope
- Correction targets are validated inside the same household/item scope; invalid or foreign adjustment references stay `422` without leaking foreign adjustment existence
- Explicit wrong-household overrides still surface as `403 household_access_forbidden`, distinguishing auth failures from not-found lookups

## Evidence

Backend validation passed on the targeted inventory authorization slice:
- `python -m pytest tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api`
- All 47 tests green
- Cross-household read/history/mutation coverage added and passing
- Household-scoped correction-target validation confirmed

## Handoff

INF-05 (Uhura) can now consume the inventory API as backend-owned household context by default, without relying on client-selected household scope for normal inventory operations. Frontend integration with session-derived household scope is ready to begin.
