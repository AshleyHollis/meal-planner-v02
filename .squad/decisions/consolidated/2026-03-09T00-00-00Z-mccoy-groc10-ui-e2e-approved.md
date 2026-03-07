# McCoy Review — GROC-10 Grocery UI and End-to-End Verification

Date: 2026-03-08
Reviewer: McCoy
Requested by: Ashley Hollis
Scope: Milestone 3 grocery UI / end-to-end verification gate (`GROC-10`)

## Verdict

**APPROVE**

The grocery review slice now satisfies the GROC-10 chartered acceptance seam. Frontend helper coverage and Playwright acceptance coverage prove the user can derive a draft from the confirmed-plan seam, review traceability, preserve ad hoc and override intent across stale refresh, adjust quantities, and confirm a stable shopping version without silent mutation.

## Evidence reviewed

- Frontend regression additions:
  - `apps/web/app/_lib/grocery-ui.ts`
  - `apps/web/app/_lib/grocery-ui.test.ts`
  - `apps/web/tests/e2e/grocery-acceptance.spec.ts`
  - `apps/web/playwright.config.ts`
- Validation evidence:
  - `npm run lint:web`
  - `npm run typecheck:web`
  - `npm run build:web`
  - `npm --prefix apps\web run test`
  - `set PLAYWRIGHT_PORT=3101 && npm --prefix apps\web run test:e2e -- tests/e2e/grocery-acceptance.spec.ts`
  - `python -m pytest apps\api\tests -q`
  - `npm run test:worker`

## What changed in verification

- Added helper-level regression coverage for visible meal trace labels so duplicate meal names collapse correctly and unnamed sources fall back to meal-slot IDs.
- Added Playwright acceptance coverage for:
  - derive → review → adjust → confirm from a no-list state,
  - stale refresh preserving existing override + ad hoc intent,
  - visible traceability details including meal-source quantities and inventory snapshot linkage,
  - and phone-sized confirmation usability.
- Hardened Playwright config to honor `PLAYWRIGHT_PORT`, which is necessary in this shared Windows workspace because port 3000 may already be occupied by an unrelated process.

## Rationale

The previous grocery acceptance coverage proved only a subset of the review flow and did not explicitly demonstrate derive-from-empty, preserved user intent after refresh, or traceability detail persistence. Those seams are now covered by deterministic tests and the cross-stack regression evidence remained green, so there is no remaining blocker within the GROC-10 slice.

## Immediate next step

Route to **Kirk** for `GROC-11` final Milestone 3 acceptance review. Kirk should confirm the approved grocery implementation still respects the roadmap cut line and did not quietly absorb Milestone 4 trip-mode or Milestone 5 reconciliation scope.
