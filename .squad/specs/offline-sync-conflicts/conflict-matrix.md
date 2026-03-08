# Offline Sync Conflict Matrix

Date: 2026-03-07
Status: Supporting reference for implementation planning

This matrix is a supporting artifact for `.squad/specs/offline-sync-conflicts/feature-spec.md`. It makes the MVP classification posture concrete so API and frontend work can implement the same decision table.

| Local mutation | Newer server change since base version | MVP default outcome | Why |
| --- | --- | --- | --- |
| Exact same accepted mutation replayed with same receipt identity | Already accepted server result exists | `duplicate_retry` | Safe idempotent replay; no new side effect |
| Add independent ad hoc item A | Another actor added independent item B | `auto_merged_non_overlapping` | Different authoritative records |
| Edit non-overlapping metadata field | Server changed a different non-overlapping metadata field and merge is deterministic | `auto_merged_non_overlapping` | Safe only if independence is provable |
| Change item quantity | Server also changed same item quantity or completion quantity | `review_required_quantity` | Arithmetic intent is ambiguous in MVP |
| Check off or edit purchase quantity for list item | Server also changed same list item's completion/quantity meaning | `review_required_quantity` | Completion semantics overlap |
| Update item that server archived | Server archived or removed target item | `review_required_deleted_or_archived` | Must not resurrect or mutate silently |
| Update item that server deleted | Server no longer has active target item | `review_required_deleted_or_archived` | Identity/liveness changed |
| Change freshness basis/date | Server changed freshness or location on same item | `review_required_freshness_or_location` | Real-world item condition is ambiguous |
| Move location | Server changed location or freshness on same item | `review_required_freshness_or_location` | Cannot safely assume both apply |
| Any stale mutation not covered by explicit safe rule | Any ambiguous newer server change | `review_required_other_unsafe` | Conservative trust-first posture |

## Resolution Expectations
- `duplicate_retry` returns the original accepted result and marks the local queue item applied.
- `auto_merged_non_overlapping` applies once and records why the merge was considered safe.
- Any `review_required_*` outcome freezes automatic replay until the user chooses **keep mine** or **use server**.

## Keep-Mine vs Use-Server Guidance
- **Keep mine:** send a new resolution command against the latest server state and link it to the original conflict.
- **Use server:** discard the stale local mutation, refresh local snapshots, and preserve the conflict record for auditability.
