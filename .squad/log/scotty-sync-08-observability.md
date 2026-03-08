# Scotty SYNC-08 — sync observability and deterministic reconnect fixtures

Date: 2026-03-09
Owner: Scotty
Requested by: Ashley Hollis
Related spec: `.squad/specs/offline-sync-conflicts/feature-spec.md`

## Decision

For SYNC-08, grocery sync observability will extend the existing structured mutation-log seam instead of introducing a second persistence artifact: duplicate replay, auto-merge, review-required conflict creation/re-encounter, and manual resolution paths now emit correlation-aware diagnostics with aggregate/version/conflict metadata, while deterministic reconnect/conflict fixtures live in test helpers rather than a runtime-only debug surface.

## Why

- SYNC-04 through SYNC-06 already established the trustworthy backend truth sources: household-scoped mutation receipts plus durable `grocery_sync_conflicts`. SYNC-08 should make those flows easier to trace, not split observability into a new database table or bespoke debug endpoint.
- The same `client_mutation_id` already anchors replay idempotency, safe auto-merge rationale, and manual resolution commands. Carrying that correlation thread through structured logs keeps support/debugging honest during reconnect sequences.
- Deterministic fixture helpers give SYNC-07 and SYNC-09 a stable way to recreate reconnect/conflict stories without duplicating raw payload literals across tests or drifting from the approved Milestone 4 sync contract.

## Consequences

- Reviewer-owned SYNC-09 can audit duplicate retry, auto-merge, review-required conflict, and manual resolution behavior from a single structured log vocabulary plus the durable receipt/conflict store.
- SYNC-07 should build conflict-review UI tests on the new named reconnect fixtures/helpers so frontend trust messaging stays aligned with backend outcome classes.
- Retry exhaustion remains a client/runtime concern for the offline queue; this decision keeps backend logging focused on authoritative replay/conflict outcomes rather than inventing server-only retry counters that do not own the queue lifecycle.
