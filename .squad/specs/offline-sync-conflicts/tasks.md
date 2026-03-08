# Offline Sync Conflicts — Implementation Tasks

Date: 2026-03-08
Milestone: 4 (Mobile trip mode, offline queueing, and conflict-safe sync)
Status: Execution-ready planning refresh
Spec: `.squad/specs/offline-sync-conflicts/feature-spec.md`

This task plan turns the approved Milestone 4 offline-sync-conflicts spec into an execution queue grounded in the current repo. It is aligned with the constitution, PRD, roadmap, the approved offline-sync decisions in `.squad/decisions.md`, and the now-complete Milestone 3 confirmed grocery-list handoff seam.

## 1. Planning cut line

### Milestone 4 outcome
Deliver a trustworthy mobile trip flow where a shopper can:
- open a **confirmed** grocery list on a phone-sized layout,
- keep working through poor connectivity using a durable local trip snapshot and intent queue,
- queue check-off, quantity-edit, and ad hoc item mutations offline,
- reconnect safely with explicit sync outcomes, narrow auto-merge, and review-required conflict handling,
- preserve a clean handoff into Milestone 5 shopping reconciliation without silently mutating inventory during trip mode.

### Locked implementation rules
- **Confirmed-list bootstrap only:** trip mode starts from the confirmed grocery list version delivered by Milestone 3. Draft grocery state is never the authoritative trip input.
- **Intent queue only:** offline storage persists intent-based mutations plus comparison metadata, not whole-record overwrites.
- **Server-classified conflicts:** the API owns duplicate detection, stale detection, safe auto-merge decisions, conflict creation, and resolution commands. The client must not invent its own merge rules.
- **Unsafe replay stops:** if the system cannot prove a safe merge, replay halts for that mutation and requires explicit user review.
- **MVP auto-merge remains narrow:** only duplicate retries and clearly non-overlapping updates may auto-merge.
- **Mobile-first UX is mandatory:** trip progress, sync state, retry state, and conflict review must stay usable on a phone with large touch targets and minimal typing.
- **No silent inventory mutation:** trip mode updates grocery/trip state only. Authoritative inventory changes remain Milestone 5 reconciliation work.
- **Backend-owned session/auth only:** Milestone 4 continues using API-owned session bootstrap via `GET /api/v1/me`; no Auth0 SDK or Auth0 runtime config may be added to `apps/web`.

## 2. Current codebase starting point

- Milestone 3 is approved. The grocery contract already exposes stable `grocery_list_version_id`, `grocery_line_id`, and `confirmed_at` seams in backend and web read models.
- `apps/api/app/routers/grocery.py` and `apps/api/app/services/grocery_service.py` already enforce confirmed-list stability, grocery mutation receipts, and trip-state-ready lifecycle enums, but they do **not** yet implement trip mutation upload, offline replay outcomes, conflict records, or resolution commands.
- `apps/web/app/grocery/_components/GroceryView.tsx` and `apps/web/app/_components/SyncStatusBadge.tsx` already expose basic sync/trip status labels, but the current web flow is still online-only and treats trip states as read-only placeholders.
- The repo already has trustworthy household-scoped idempotency patterns in inventory and grocery slices (`client_mutation_id`, durable mutation receipts, scoped 404/403 rules). Milestone 4 should reuse those patterns rather than inventing a separate sync identity model.
- The repo does **not** yet have the full Milestone 4 client offline store, replay queue, conflict list/detail views, or explicit keep-mine / use-server resolution API contract.

## 3. Ready-now implementation queue

| ID | Task | Agent | Depends on | Parallel | Notes |
| --- | --- | --- | --- | --- | --- |
| SYNC-00 | Keep Milestone 4 progress ledger current | Scribe | — | [P] | Update `progress.md` on every start, finish, blocker, and verification result. |
| SYNC-01 | Lock the trip/offline contract seam across API and web types | Sulu | GROC-11 |  | Finalize Milestone 4 contract fields for confirmed-list bootstrap payloads, queueable mutation metadata (`client_mutation_id`, `base_server_version`, aggregate identity), sync outcome enums, conflict read models, and explicit resolution commands. Remove any placeholder trip semantics that could mislead implementation. |
| SYNC-02 | Build the durable client offline store and queue foundation | Uhura | SYNC-01 |  | Add the IndexedDB-class storage layer for confirmed grocery list snapshot, related meal-plan context, latest inventory snapshot, queued trip mutations, retry counters, and local conflict preservation so app restarts do not lose in-store work. |
| SYNC-03 | Implement mobile trip mode over the confirmed-list snapshot | Uhura | SYNC-01, SYNC-02 |  | Deliver the phone-first trip UI: large touch targets, one-handed list interaction, low-typing quantity adjustments, ad hoc item creation, local sync status surfaces, and honest read-only handling when the confirmed-list seam is absent or stale. |
| SYNC-04 | Add sync upload API and stale-detection foundations | Scotty | SYNC-01 |  | ✅ Done 2026-03-09. Implemented per-mutation upload handling, durable mutation/conflict persistence, current-version comparison, confirmed-list version advancement, conflict read endpoints, and partial-batch processing on top of the existing household-scoped grocery patterns. |
| SYNC-05 | Implement the MVP conflict classifier and replay rules | Scotty | SYNC-04 |  | Encode `duplicate_retry`, `auto_merged_non_overlapping`, and the locked `review_required_*` classes from the approved spec and conflict matrix. Stop automatic replay for review-required conflicts and preserve safe-merge rationale when auto-merge occurs. |
| SYNC-06 | Implement explicit resolution commands and read-model refresh | Scotty | SYNC-05 | [P] | Add keep-mine and use-server resolution commands, supersede the original stale mutation without erasing it, refresh affected snapshots/read models, and link resolutions back to the durable conflict record. |
| SYNC-07 | Wire the mobile conflict-review UX and resolution flow | Uhura | SYNC-03, SYNC-05, SYNC-06 |  | Add mobile-friendly conflict summary/detail views, distinguish review-required from retryable failures, preserve local intent for later review, and let shoppers choose keep mine or use server from a phone-sized screen. |
| SYNC-08 | Add observability, diagnostics, and deterministic sync fixtures | Scotty | SYNC-05 | [P] | Emit correlation-aware logs for duplicate retries, auto-merges, review-required conflicts, retry exhaustion, and manual resolutions. Add deterministic fixtures that frontend and backend tests can share for reconnect/conflict scenarios. |
| SYNC-09 | Verify the backend sync/conflict slice | McCoy | SYNC-04, SYNC-05, SYNC-06, SYNC-08 | [VERIFY] | Add unit/integration coverage for duplicate replay, non-overlapping auto-merge, quantity/deletion/freshness conflicts, partial batch success, durable conflict records, and resolution command behavior against SQL-backed state. The person closing this gate must not be one of the implementation owners for the backend sync/conflict slice. |
| SYNC-10 | Verify mobile trip/offline behavior end to end | McCoy | SYNC-02, SYNC-03, SYNC-07, SYNC-08 | [VERIFY] | Add frontend and Playwright coverage for confirmed-list offline load, queued trip edits during connectivity loss, reconnect duplicate replay, reconnect review-required conflict, and user-visible resolution back to a trustworthy final state. This is also the single Milestone 4 manual visual smoke gate: run the local app once on desktop + phone-sized viewports and record the evidence for milestone closure. The person closing SYNC-10 must not be one of the implementation owners for the trip UI or conflict UX slice being verified. |
| SYNC-11 | Final Milestone 4 acceptance review | Kirk | SYNC-09, SYNC-10 | [VERIFY] | Review implementation against the approved spec, constitution rules, roadmap cut line, the Milestone 3 confirmed-list seam, and the single milestone-end smoke evidence from SYNC-10 before Milestone 4 is claimed complete. Final acceptance must be owned by a reviewer who did not implement the Milestone 4 slice being approved. |

## 4. Blocked or cross-milestone follow-on work

These items remain real requirements, but the roadmap intentionally sequences them outside the core Milestone 4 cut line. Keep them explicit instead of quietly absorbing them into trip/offline work.

| ID | Task | Agent | Status | Blocked by | Why it stays tracked |
| --- | --- | --- | --- | --- | --- |
| SYNC-12 | Convert confirmed trip outcomes into authoritative inventory updates | Scotty + Sulu | blocked | Milestone 5 shopping reconciliation | Milestone 4 must preserve version/line/conflict traceability for downstream apply flows, but authoritative inventory mutation still belongs to the explicit post-shopping review/apply milestone. |
| SYNC-13 | Add richer simultaneous multi-shopper coordination and live presence | Uhura + Scotty | blocked | Phase 2 collaboration scope | MVP requires conflict-safe shared state, not presence indicators, cursors, or real-time co-editing UI. |
| SYNC-14 | Expand auto-merge beyond the locked MVP-safe classes | Scotty | blocked | Phase 2 merge policy approval | Semantic overlap resolution, hidden arithmetic reconciliation, and broader conflict automation remain intentionally out of MVP. |

## 5. Execution notes for downstream implementers

- Start from the approved grocery seam, not from a fresh trip model: `grocery_list_version_id`, stable `grocery_line_id`, and confirmed-list immutability are already the authoritative Milestone 3 handoff.
- Reuse Milestone 1 and Milestone 3 trust patterns: backend-owned household scope, durable mutation receipts, SQL-backed authoritative state, explicit status enums, and append-only provenance.
- Keep the client queue intent-based and auditable. Queue entries should preserve enough local/base/server comparison context to reopen conflict review after refresh or browser restart.
- Let the server prefer review over cleverness. If a replay case does not match a proven safe rule, it should produce a review-required conflict, not a guessed merge.
- Distinguish retryable transport/service failures from review-required conflicts everywhere in UI and logging. “Sync failed” is not an honest conflict experience.
- Do not hide Milestone 5 reconciliation inside trip completion. Trip mode prepares trustworthy outcomes; reconciliation remains a separate explicit review/apply step.
- Testing and review ownership must stay separate from implementation ownership. If one human covered multiple named squad roles during delivery, reassign SYNC-09, SYNC-10, and SYNC-11 to another existing reviewer before marking Milestone 4 verified or approved.

## 6. Suggested implementation order

1. **Contract spine:** SYNC-01.
2. **Client durability foundation:** SYNC-02.
3. **Server replay/conflict spine:** SYNC-04 → SYNC-05 → SYNC-06.
4. **Phone-first trip UX:** SYNC-03 → SYNC-07.
5. **Observability and deterministic fixtures:** SYNC-08.
6. **Acceptance evidence:** SYNC-09 → SYNC-10 (automated + single milestone-end smoke evidence) → SYNC-11.

This sequence keeps the confirmed-list seam, replay safety rules, and mobile usability ahead of polish and prevents reconciliation scope from bleeding into Milestone 4.
