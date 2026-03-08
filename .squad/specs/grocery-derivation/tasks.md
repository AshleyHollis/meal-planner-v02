# Grocery Derivation — Implementation Tasks

Date: 2026-03-08
Milestone: 3 (Grocery calculation and review before the trip)
Status: Execution-ready planning refresh
Spec: `.squad/specs/grocery-derivation/feature-spec.md`

This task plan turns the approved Milestone 3 grocery-derivation spec into an execution queue grounded in the current repo. It is aligned with the constitution, PRD, roadmap, the approved grocery MVP decisions in `.squad/decisions.md`, and the now-complete Milestone 2 planner/confirmed-plan handoff.

## 1. Planning cut line

### Milestone 3 outcome
Deliver a trustworthy grocery-review flow where a household can:
- derive a grocery draft from the **confirmed** weekly plan plus authoritative inventory,
- review consolidated meal-derived lines with conservative inventory offsets and meal traceability,
- add ad hoc items and adjust quantities without losing those edits on refresh,
- confirm a stable grocery list version for the upcoming trip,
- preserve a versioned handoff seam for Milestone 4 trip mode and Milestone 5 reconciliation.

### Locked implementation rules
- **Confirmed plan only:** grocery derivation consumes confirmed planner state only. Suggestion, request, and draft planner states never feed grocery calculation.
- **Trust-first matching only:** inventory offsets apply only for obvious same-item, same-unit matches. No fuzzy name matching, synonym inference, or unit conversion in MVP.
- **Derived vs. authoritative boundary stays explicit:** grocery drafts are derived state; only a user-confirmed grocery list becomes the authoritative trip input.
- **Refresh cannot destroy user intent:** ad hoc lines and user quantity overrides survive refresh. If underlying derived quantities change, the UI must surface a visible review state instead of silently overwriting user edits.
- **Confirmed list stability is non-negotiable:** once a list is confirmed for a trip, later derivations may create a new draft but must not silently mutate the confirmed version.
- **Backend-owned session/auth only:** grocery work must keep using API-owned session bootstrap via `GET /api/v1/me`; no Auth0 SDK or Auth0 runtime config may be added to `apps/web`.
- **Roadmap honesty on offline scope:** full offline mutation queueing, replay, and trip conflict resolution remain Milestone 4 work. Milestone 3 must land the confirmed-list version contract and caching seam honestly, without inventing unsafe offline shortcuts.

## 2. Current codebase starting point

- `apps/api/app/models/grocery.py` and `apps/api/app/schemas/grocery.py` already contain grocery list/version/line primitives, but the active API does not yet expose a grocery router and the contract still needs to be tightened to the approved lifecycle/state model.
- `apps/api/app/services/planner_service.py` now emits durable `plan_confirmed` events; Milestone 3 should consume that handoff seam instead of re-deriving planner intent from draft state.
- `apps/web/app/_lib/grocery-api.ts` and `apps/web/app/grocery/_components/GroceryView.tsx` already provide a grocery UI scaffold, but they currently depend on placeholder status names and a backend contract that does not exist yet.
- `apps/api/app/main.py` only registers session, inventory, and planner routers today; grocery logic is not yet an active authoritative feature slice.

## 3. Ready-now implementation queue

| ID | Task | Agent | Depends on | Parallel | Notes |
| --- | --- | --- | --- | --- | --- |
| GROC-00 | Keep Milestone 3 progress ledger current | Scribe | — | [P] | Update `progress.md` on every start, finish, blocker, and verification result. |
| GROC-01 | Tighten grocery schema, lifecycle enums, and migration seams | Sulu | AIPLAN-12 |  | Finalize list/version/line fields to match the approved spec: draft/confirmed/stale/confirming/trip states, plan + inventory traceability, incomplete-slot warnings, offset references, active/removed line state, and client-mutation/idempotency seams. |
| GROC-02 | Implement derivation engine and authoritative persistence | Scotty | GROC-01 |  | Build ingredient expansion from confirmed plans, conservative inventory offset, duplicate consolidation, remaining-to-buy calculation, and persistence of derived lines plus warnings in one durable slice. |
| GROC-03 | Implement refresh and stale-draft orchestration | Scotty | GROC-02 | [P] | ✅ Completed 2026-03-08. `plan_confirmed` events now auto-refresh drafts, inventory mutations only stale relevant drafts, ad hoc/override state survives refresh, and confirmed lists remain immutable. |
| GROC-04 | Implement grocery API router and mutation contracts | Scotty | GROC-02 |  | Add household-scoped derive/read/detail/re-derive/add-ad-hoc/adjust/remove/confirm endpoints using backend-owned session context and idempotent client mutation IDs. |
| GROC-05 | Verify backend derivation and contract slice | McCoy | GROC-03, GROC-04 | [VERIFY] | Add API/integration coverage for confirmed-plan-only derivation, full/partial/no offset, duplicate consolidation, staples, stale-draft behavior, override preservation, idempotent mutations, and confirmed-list stability. This gate must be executed by someone other than the implementation owner(s) of the backend slice under review. |
| GROC-06 | Rewire the web grocery client to the real API contracts | Uhura | GROC-04 |  | Replace placeholder status mapping and optimistic assumptions in `grocery-api.ts` and shared types with the approved lifecycle/read-model contract. |
| GROC-07 | Complete grocery review and confirmation UX | Uhura | GROC-03, GROC-06 |  | Deliver the user journey for draft review, stale visibility, incomplete-slot warnings, traceability detail, ad hoc item management, quantity override review, and list confirmation on phone-sized and desktop layouts. |
| GROC-08 | Land confirmed-list handoff seams for trip mode and reconciliation | Scotty | GROC-04 | [P] | Define and test the stable list-version identity, confirmed-at metadata, and line identifiers that Milestone 4 trip mode and Milestone 5 shopping reconciliation will consume. |
| GROC-09 | Add grocery observability and deterministic fixtures | Scotty | GROC-03, GROC-04 | [P] | Emit derivation run, stale detection, and confirmation diagnostics with correlation IDs; add deterministic fixtures for complete, partial-offset, stale, and incomplete-slot scenarios. |
| GROC-10 | Verify grocery UI and end-to-end flows | McCoy | GROC-07, GROC-08, GROC-09 | [VERIFY] | Add frontend and Playwright coverage for plan→derive→review→adjust→confirm, stale refresh with preserved user intent, and traceability visibility. This is also the single Milestone 3 manual visual smoke gate: run the local app once on desktop + phone-sized viewports and record the evidence for milestone closure. The person closing GROC-10 must not be one of the implementation owners for the UI or seam work being verified. |
| GROC-11 | Final Milestone 3 acceptance review | Kirk | GROC-05, GROC-10 | [VERIFY] | Review implementation against the feature spec acceptance criteria, constitution rules, roadmap cut line, Milestone 2 handoff assumptions, and the single milestone-end smoke evidence from GROC-10 before Milestone 3 is claimed complete. Final acceptance must be owned by a reviewer who did not implement the milestone slice being approved. |

## 4. Blocked or cross-milestone follow-on work

These items remain real requirements, but the roadmap intentionally sequences their full implementation into later milestones. Keep them visible instead of quietly absorbing them into Milestone 3.

| ID | Task | Agent | Status | Blocked by | Why it stays tracked |
| --- | --- | --- | --- | --- | --- |
| GROC-12 | Persist confirmed grocery list into the real offline client store | Uhura + Scotty | blocked | Milestone 4 offline-sync foundation | The grocery spec requires an offline-accessible confirmed list snapshot, but the repo’s full IndexedDB/sync machinery is a Milestone 4 dependency. Milestone 3 must define the stable confirmed-list payload and version contract now. |
| GROC-13 | Execute active trip flows against the confirmed grocery list with conflict review | Uhura + Scotty | blocked | Milestone 4 trip mode + conflict UX | Milestone 3 must make confirmed list versions stable and consumable, but the actual in-store trip execution and reconnect conflict handling are still separate roadmap work. |
| GROC-14 | Convert confirmed grocery outcomes into authoritative inventory updates | Scotty + Sulu | blocked | Milestone 5 shopping reconciliation | Grocery derivation must preserve line/version/offset traceability for downstream reconciliation, but post-trip review/apply remains its own milestone and should not be hidden inside grocery delivery. |

## 5. Execution notes for downstream implementers

- Start from the existing planner seam, not from grocery UI guesses: `plan_confirmed` events and confirmed plan reads are the authoritative trigger/input.
- Reuse Milestone 1 and Milestone 2 trust patterns: backend-owned household scope, SQL-backed persistence, explicit state machines, append-only provenance, and idempotent client mutation contracts.
- Do not let the existing grocery UI scaffold freeze a wrong backend contract. Backend lifecycle and read models should lead; the web layer should conform afterward.
- Treat incomplete ingredient data as honest partial derivation, not a hard failure and not silent invention. The user should see what derived and what could not.
- Verification gates are mandatory. Do not claim Milestone 3 complete on unit tests alone; the roadmap and constitution require user-journey evidence on the grocery review flow.
- Testing and review ownership must stay separate from implementation ownership. If the same human covered multiple named squad roles while building a slice, route GROC-05, GROC-10, and GROC-11 to a different existing reviewer before calling the milestone verified or approved.

## 6. Suggested implementation order

1. **Backend contract spine:** GROC-01 → GROC-02 → GROC-04.
2. **Refresh and trust behavior:** GROC-03.
3. **Backend proof gate:** GROC-05.
4. **Frontend wiring and UX completion:** GROC-06 → GROC-07.
5. **Cross-milestone seam hardening:** GROC-08 + GROC-09.
6. **Acceptance evidence:** GROC-10 (automated + single milestone-end smoke evidence) → GROC-11.

This sequence keeps the confirmed-plan handoff, derivation correctness, and trustworthy list lifecycle ahead of UI polish and later trip-mode work.
