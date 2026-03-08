# McCoy Decision: Visual Smoke Acceptance Gate

Date: 2026-03-07
Requested by: Ashley Hollis
Owner: McCoy

## Decision

Before any non-trivial milestone is accepted as complete, the team must run one manual visual smoke pass in the supported local app flow at both:

- a desktop viewport, and
- a phone-sized/mobile viewport.

That smoke pass must capture screenshots/evidence in `test-results\` for the key available flows under review and record any blocked/broken journeys in the relevant spec progress log during the milestone's final user-journey verification gate. Final acceptance should consume that recorded evidence instead of rerunning the smoke pass at every intermediate verify or approval sub-step.

## Why

This local review found failures that automated checks alone did not surface honestly:

1. stale local SQLite schema could crash planner/grocery routes with 500s,
2. shared Next build output could make the local app appear broken during review, and
3. mobile-specific usability quality still needs explicit human review even when desktop flows render.

If we do not perform a real browser smoke pass before sign-off, we risk approving specs whose “green” state exists only in tests, not in the actual local product experience Ashley sees.

## Required evidence pattern

- Start or verify the repo’s supported local flow.
- Review the relevant flows in a real browser.
- Capture desktop + mobile screenshots for the routes/journeys that matter to the spec.
- Note the exact brokenness found: functionality, layout, usability, polish.
- Do not mark the milestone accepted until that evidence is recorded in the spec progress/history trail and referenced by the final milestone reviewer.
