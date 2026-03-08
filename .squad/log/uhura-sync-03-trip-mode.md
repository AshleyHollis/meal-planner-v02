# Uhura — SYNC-03 trip mode decision

Date: 2026-03-09
Requested by: Ashley Hollis
Scope: Milestone 4 mobile trip mode over the confirmed-list snapshot

## Decision

Trip mode now treats the confirmed grocery-list snapshot as the shopper's durable local working copy and applies only intent-based trip edits on top of it:

- quantity updates queue as `adjust_quantity`,
- done/check-off actions queue as `remove_line`,
- trip add-ons queue as `add_ad_hoc` with provisional local line ids until the server returns the refreshed authoritative list.

The web client immediately updates the saved local snapshot for phone usability, then attempts replay through `POST /grocery/sync/upload` whenever the device is online. If replay stops for review, the UI preserves the local intent and surfaces the pending review state instead of pretending to resolve the conflict inline.

## Why

This keeps Milestone 4 aligned with the approved contract and constitution:

- confirmed-list snapshot remains the authority seam for trip mode,
- offline work stays durable across reloads/reconnects,
- sync remains intent-based and conflict-safe,
- reviewer-separation still holds because conflict resolution itself is explicitly deferred to SYNC-07 / SYNC-06 follow-on work.

## Consequences

- Grocery trip UI can now be used honestly on a phone even without connectivity.
- The current screen intentionally stops at local sync status + review-needed summaries; keep-mine/use-server resolution is still downstream work, not hidden in this slice.
