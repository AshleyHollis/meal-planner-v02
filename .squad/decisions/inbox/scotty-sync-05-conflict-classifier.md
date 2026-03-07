# Scotty SYNC-05 conflict classifier decision

Date: 2026-03-09
Owner: Scotty
Requested by: Ashley Hollis

## Decision

For SYNC-05, stale grocery sync uploads only auto-merge when the backend can prove the local mutation is non-overlapping with newer authoritative server changes, and the safe-merge rationale is carried in the sync outcome/log seam rather than introducing a new persistence schema just for successful auto-merges.

## Why

- Milestone 4 explicitly locks MVP auto-merge to duplicate retries and clearly non-overlapping updates. The safest backend posture is therefore to classify same-line quantity/completion drift as `review_required_quantity`, deleted/archived targets as `review_required_deleted_or_archived`, and everything ambiguous as review-required instead of guessing user intent.
- The existing receipt/conflict model already cleanly separates accepted mutations from durable review artifacts. Successful auto-merges do not need a second durable conflict row; they need an immediate explanation the client can trust plus structured logs that later observability work can build on.
- Keeping replay-stop list-scoped after the first review-required conflict preserves batch isolation: independent lists can still sync, while a conflicted list freezes until SYNC-06 resolution commands arrive.

## Follow-on impact

- SYNC-06 should treat the classifier outcome on persisted conflicts as authoritative and keep manual resolutions explicit rather than trying to reinterpret stale batches.
- SYNC-07 can surface `auto_merge_reason` directly from upload outcomes for trust messaging, while continuing to block review-required items until the user chooses keep-mine or use-server.
- SYNC-08 should extend the current auto-merge reason logging seam if we need richer audit/telemetry, instead of backfilling a new success-only database artifact.
