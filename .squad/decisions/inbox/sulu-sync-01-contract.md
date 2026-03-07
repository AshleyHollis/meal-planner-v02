# Sulu — SYNC-01 Contract Decision

Date: 2026-03-08
Requested by: Ashley Hollis
Related task: `SYNC-01`

## Decision

Milestone 4 trip/offline work will use an explicit `trip_state` + sync-contract seam rather than relying only on `GroceryListStatus` labels.

## Why

The grocery lifecycle status already contains trip-ready values from Milestone 3, but those values alone are too easy to misread as “the trip UI is already implemented.” Milestone 4 needs a sharper seam for:

- confirmed-list bootstrap payloads,
- queueable mutation aggregate identity,
- per-mutation sync outcomes,
- durable conflict read models,
- explicit keep-mine / use-server resolution commands.

Separating `trip_state` from generic grocery review wording keeps the confirmed snapshot contract honest while preserving the existing grocery list lifecycle values.

## Locked implications

1. **Confirmed-list bootstrap must carry explicit trip bootstrap state.**
   - `confirmed_list_ready` is the honest bootstrap state for a confirmed grocery list that has not yet entered active trip replay.
   - `trip_in_progress` and `trip_complete_pending_reconciliation` remain valid downstream states.

2. **Conflict scope must be attached to an explicit aggregate reference.**
   - Use `SyncAggregateRef` (`aggregate_type`, `aggregate_id`, version, optional provisional ID) instead of ad hoc field guessing.

3. **Resolution remains command-driven.**
   - `keep_mine` and `use_server` are explicit commands with their own mutation identity; they are not hidden retry semantics.

4. **Web copy must not imply completed trip execution where only snapshot/contract work exists.**
   - Grocery review surfaces can describe confirmed snapshot and downstream trip/reconciliation semantics, but must not claim the screen already is the Milestone 4 trip workflow.

## Downstream guidance

- Scotty should use the new conflict/read-model contracts as the API spine for SYNC-04 through SYNC-06.
- Uhura should use `trip_state`, `QueueableSyncMutation`, and the sync/conflict enums as the client-store and mobile UX contract for SYNC-02 / SYNC-03 / SYNC-07.
