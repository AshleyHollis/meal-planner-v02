# Scotty INF-01 Session Contract Approved

**Date:** 2026-03-07T23:45:00Z  
**Agent:** Scotty  
**Task:** INF-01 — Lock household session and request-scope contract  
**Status:** Approved  

## Summary

Scotty has completed INF-01 by replacing the stub session seam with a request-scoped household contract backed by explicit dev/test headers until production Auth0 integration.

## What was delivered

- `/api/v1/me` endpoint now resolves caller identity and active household request-scoped from backend dependency
- Inventory routes explicitly reject unauthenticated requests (401) and wrong-household access (403)
- Client-supplied `household_id` values in request bodies no longer trusted; backend-owned household scope is authoritative
- Dev/test header seam: `X-Dev-User-Id`, `X-Dev-User-Email`, `X-Dev-User-Name`, `X-Dev-Active-Household-Id`, `X-Dev-Active-Household-Name`, `X-Dev-Active-Household-Role`, optional `X-Dev-Households`

## Evidence

- Session bootstrap and inventory route tests cover authenticated success paths
- Tests verify 401 for missing auth, 403 for wrong household, 404 for missing items
- Full `apps/api/tests` suite passing
- No expansion of pre-existing deprecation warnings

## Handoff

INF-02 (Sulu) is now ready to begin SQL-backed household and inventory schema work on top of this locked request-scoped session contract. The backend-authoritative household dependency provides a stable foundation for persistence.

## Decision Records

- `.squad/decisions/inbox/scotty-inf-01-session-contract.md` (approved and ready for merge)

## Cross-team impact

- Frontend and API tests can now bootstrap known household context deterministically
- Backend-authorized session scope is the source of truth for household membership
- Clean swap point for later Auth0 integration: replace header resolver, keep request-scoped contract and route behavior
