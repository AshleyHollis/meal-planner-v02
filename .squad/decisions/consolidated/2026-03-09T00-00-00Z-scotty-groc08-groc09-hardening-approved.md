# Scotty — GROC-08 / GROC-09 Hardening Decision

Date: 2026-03-08
Requested by: Ashley Hollis
Scope: Grocery derivation Milestone 3 backend handoff seam hardening

## Decision

Treat the grocery list version, not the mutable grocery list row alone, as the downstream trip/reconciliation snapshot seam, and expose it explicitly in the read model as `grocery_list_version_id`. Expose stable per-line identifiers separately as `grocery_line_id`, backed by a persisted `stable_line_id` that survives logical carry-forward across re-derives for the same line.

## Why

- Milestone 4 trip mode needs a snapshot identity it can cache and execute against even after a later online re-derive produces a newer draft.
- Milestone 5 reconciliation needs stable line references that are not coupled to whatever per-version row primary key happened to be written for one refresh cycle.
- Keeping the mutable row `id` for backend persistence while adding explicit downstream-facing snapshot identifiers avoids breaking existing API consumers and makes the seam honest before offline/trip work lands.

## Consequences

- Confirmed-list payloads now carry an explicit version identity (`grocery_list_version_id`) and stable line identity (`grocery_line_id`) for downstream consumers.
- Existing persisted grocery rows need a migration so pre-hardening data gets a stable line identity; the upgrade seeds `stable_line_id` from the existing row `id`.
- Future trip-mode and reconciliation work should consume `grocery_list_version_id` + `grocery_line_id` instead of depending on `current_version_id` or raw line row IDs by convention alone.
