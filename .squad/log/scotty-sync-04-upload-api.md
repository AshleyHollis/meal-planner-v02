# Scotty SYNC-04 upload API decision

Date: 2026-03-09
Owner: Scotty
Requested by: Ashley Hollis

## Decision

For SYNC-04, grocery sync uploads advance the authoritative confirmed/trip snapshot by cloning the current `GroceryListVersion` into a new version per accepted sync mutation, and stale/review-required uploads persist in a dedicated `grocery_sync_conflicts` store keyed by `(household_id, local_mutation_id)`.

## Why

- The Milestone 3 confirmed-list seam already gives us durable grocery-list versions, stable line identity, and household-scoped mutation receipts. Extending that seam keeps `base_server_version` comparisons integer-based and trustworthy without inventing a parallel version model just for offline replay.
- Using a dedicated conflict store lets duplicate accepted replays keep using the proven grocery mutation receipt path while still preserving unresolved stale uploads as durable review artifacts with local/base/server summaries for later SYNC-05/SYNC-06 work.
- Per-mutation version advancement keeps sync replay auditable and supports partial-batch processing: one stale mutation can stop replay for its affected list while independent mutations on other lists in the same batch still apply.

## Follow-on impact

- SYNC-05 should refine the conservative stale outcomes emitted by this foundation into the approved conflict-matrix classes and safe auto-merge cases.
- SYNC-06 should attach keep-mine/use-server resolution commands to the persisted `grocery_sync_conflicts` records instead of creating a second review store.
