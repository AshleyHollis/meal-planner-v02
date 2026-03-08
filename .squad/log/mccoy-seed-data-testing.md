# McCoy — Seed data posture for milestone-end smoke testing

**Date:** 2026-03-09  
**Requested by:** Ashley Hollis

## Issue

Manual functional and visual smoke testing is now a required milestone-end gate, but the current experience is too empty to explore honestly without first hand-entering a lot of data. That makes smoke testing slower, less repeatable, and more likely to miss real UX and trust issues.

## Assessment

The current product is only meaningfully testable by hand when four connected seams already have data:

1. **Inventory trust surface** — the tester needs real items, varied freshness states, and at least one readable adjustment history/correction chain, or the inventory screen becomes an empty CRUD shell instead of a trust review.
2. **Planner review surface** — the tester needs an already-populated household context plus a current-week confirmed plan and at least one draft/suggestion path, or planner smoke devolves into setup work instead of reviewing request/edit/confirm UX.
3. **Grocery derivation surface** — the tester needs a confirmed plan plus inventory offsets and at least one ad hoc/manual line, or grocery review cannot show whether derivation, overrides, and traceability are believable.
4. **Milestone 4 smoke surface** — the tester needs a confirmed grocery snapshot that can bootstrap trip/offline behavior, but conflict and stale-review cases should remain opt-in scenario seeds rather than polluting the default environment.

This lines up with the approved governance that smoke testing happens once at milestone end and should capture integrated user-journey evidence, not force the reviewer to build a household from scratch before every pass.

## Decision

Adopt a **single default smoke household** that is small but realistic, plus a **small set of opt-in edge scenario seeds** for stale/fallback/conflict review. Do not use a giant demo dataset as the default environment.

### Minimum realistic default smoke seed

Seed one household with:

- **1 authenticated owner user** and, if cheap to include, **1 second household member** so shared-household language and actor history look real.
- **5–7 inventory items** total, intentionally spread across pantry/fridge/freezer/leftovers.
  - Include mixed freshness basis states: one `known`, one `estimated`, one `unknown`.
  - Include at least one item with a short but believable mutation history, including a correction chain.
- **1 confirmed weekly meal plan for the current smoke week** with enough populated slots to make planner and grocery useful immediately.
  - Include a mix of `ai_suggested` and `manually_added` / user-edited style content so the planner does not look artificially perfect.
  - Every seeded meal reference used for grocery derivation must exist in the ingredient/catalog source the derivation engine trusts.
- **1 grocery draft derived from that confirmed plan** with:
  - at least one line partially offset by on-hand inventory,
  - at least one normal derived line with nothing on hand,
  - at least one ad hoc/manual line,
  - visible meal traceability,
  - and at least one incomplete/missing-data warning only if it is an honest, expected case rather than accidental fixture drift.
- **1 confirmed grocery snapshot** available for Milestone 4 trip/offline smoke bootstrap once that flow is live.

That is the smallest seed set that lets a human reviewer move through home/session bootstrap, inventory trust, planner review, grocery review, and milestone-end integrated smoke without spending the first ten minutes creating data.

### How it should support milestone-end smoke testing

The default smoke seed should support this reviewer path:

1. Open the app and confirm session/household bootstrap looks sane.
2. Inspect inventory and history quickly enough to judge trust, readability, and mutation UX.
3. Review planner state with enough real meals/context to exercise request/edit/confirm pathways or at minimum inspect believable current/confirmed content.
4. Review grocery derivation with visible offsets, manual additions, and traceability.
5. For Milestone 4 and later, bootstrap trip/offline from a confirmed snapshot without needing to fabricate a grocery list first.

The seed is successful if it supports a **10–15 minute integrated smoke pass** with honest coverage of the milestone's UX, matching the current milestone-end smoke policy.

### Edge scenarios that should be separate, not in the default seed

Keep these as **toggleable scenario seeds** or resettable alternate fixtures:

- stale planner draft requiring acknowledgment,
- planner fallback/manual-guidance state,
- slot regeneration failure,
- offline queued mutations waiting to sync,
- explicit sync conflict requiring `keep_mine` / `use_server`,
- trip already in progress,
- trip complete pending reconciliation.

These are valuable smoke paths, but they are too noisy and too stateful for the default environment. The default seed should stay clean and confidence-building; edge states should be intentional.

## Pitfalls to avoid

1. **Do not let the default seed become a giant demo world.** Too much data hides layout, traceability, and state bugs under clutter.
2. **Do not mix contradictory trust fields.** Freshness basis, expiry fields, inventory versions, correction links, and meal references must agree with the contracts or the smoke environment itself becomes misleading.
3. **Do not anchor default smoke to rare failure states.** A default stale draft or default conflict makes the app feel broken even when the happy-path UX is what the reviewer most needs to judge first.
4. **Do not let seeds drift with wall-clock time.** Use deterministic timestamps or a controlled “current smoke week” rule so the same environment remains believable and stable across repeated milestone reviews.
5. **Do not create seeds that mutate unpredictably between reviewers.** Confirmed snapshots and trust data should be resettable and reproducible; otherwise one smoke pass poisons the next.
6. **Do not hide empty-state coverage entirely.** Empty states still matter, but they should be a separate scenario, not the only thing a manual tester sees by default.

## Consequences

- McCoy can perform milestone-end smoke reviews against a stable, meaningful environment instead of spending review time manufacturing data.
- Kirk can consume smoke evidence that reflects integrated behavior, not ad hoc reviewer setup steps.
- Uhura and Scotty get a trustworthy manual-review target that mirrors the real cross-feature seams already verified in automated tests.
- Future Milestone 4/5 smoke work can layer trip/conflict/reconciliation scenarios on top of the same baseline household instead of inventing new one-off fixture worlds.

## Practical guidance

- Treat the default smoke seed as a **curated reviewer household**, not a test dump.
- Keep the baseline seed **small, realistic, deterministic, and resettable**.
- Add **named scenario seeds** for conflict/stale/fallback paths instead of overloading the baseline.
- Re-validate the seed whenever trusted contracts change (inventory history shape, planner slot provenance, grocery line identity, offline conflict model).
