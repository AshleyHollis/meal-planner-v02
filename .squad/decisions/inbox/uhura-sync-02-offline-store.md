# Uhura — SYNC-02 Offline Store Decision

Date: 2026-03-09
Requested by: Ashley Hollis
Related task: `SYNC-02`

## Decision

Milestone 4 web durability will use one client-owned offline runtime with separate IndexedDB record groups for confirmed-list snapshots, meal-plan context, inventory snapshot metadata, queued mutations, and preserved conflict records.

## Why

The locked SYNC-01 seam gives the frontend stable aggregate identity and conflict contracts, but trip mode still needs a browser store that can survive refresh, reconnect, and accidental tab closure without flattening everything into one opaque cache blob. Keeping snapshot, queue, and conflict records separate preserves auditability for reviewers and lets downstream trip/conflict UX load only the slice it needs on a phone-sized screen.

## Locked implications

1. **Confirmed-list snapshots remain the only offline trip baseline.**
   - The runtime may cache drafts for ordinary page rendering later if needed, but Milestone 4 trip execution must hydrate from the confirmed-list seam only.

2. **Queue durability stays intent-based.**
   - Queued records preserve `client_mutation_id`, aggregate scope, payload, retry state, and base version metadata. They do not overwrite whole grocery objects locally.

3. **Conflict records stay durable and separate from queue entries.**
   - A review-required conflict must remain reopenable after refresh/restart even if the queue item has already transitioned out of `queued_offline`.

4. **Frontend plumbing should stay honest about unfinished UX.**
   - SYNC-02 may expose browser runtime APIs and read-only confirmed-snapshot fallback, but trip-mode checkoff/quantity/ad-hoc workflows still belong to SYNC-03 / SYNC-07.

## Downstream guidance

- Uhura should build SYNC-03 and SYNC-07 on top of `OfflineSyncProvider` / `useOfflineSync()` instead of inventing another trip-local state silo.
- Scotty should assume the client can resend preserved queue/conflict metadata after reload and should keep the server contract append-only and resolution-command-driven.
