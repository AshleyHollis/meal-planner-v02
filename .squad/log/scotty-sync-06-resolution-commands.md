# Scotty SYNC-06 — resolution command response + audit linkage

Date: 2026-03-09
Owner: Scotty
Requested by: Ashley Hollis
Related spec: `.squad/specs/offline-sync-conflicts/feature-spec.md`

## Decision

For SYNC-06, the explicit `keep mine` and `use server` APIs will return the refreshed authoritative `grocery_list` mutation envelope immediately, while the durable conflict record carries the resolution audit link inside `local_intent_summary.resolution` plus the resolved status/timestamps.

## Why

- The mobile conflict-review flow needs one round trip that both resolves the conflict and gives the client the server-truth snapshot it should persist locally next.
- The existing durable grocery mutation receipt seam already stores `GroceryMutationResult` reliably by `(household_id, client_mutation_id)`, so reusing that envelope keeps resolution commands idempotent without inventing a second receipt store.
- The conflict record still has to preserve the original stale mutation instead of erasing it; storing explicit resolution metadata back onto the conflict keeps the supersession link auditable without forcing a schema expansion in the middle of Milestone 4.

## Consequences

- SYNC-07 can call the resolution endpoint, update local snapshot state directly from the response, and still fetch/read the conflict detail for audit/history screens.
- Pending conflict list/detail reads should refresh the server-side snapshot/version before rendering so the comparison stays honest if the authoritative list changes again before the user resolves it.
