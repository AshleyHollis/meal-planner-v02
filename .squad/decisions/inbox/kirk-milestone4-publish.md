# Kirk: Milestone 4 Publish Classification Decision (2026-03-09)

**Requested by:** Ashley Hollis  
**Author:** Kirk  
**Status:** Draft for current publish session

## Decision

Treat the current pending reviewer-seed integration changes and squad-state consolidation as intentional Milestone 4 publish content, and delete only disposable local residue before the milestone PR is created.

## Intentional to commit

- `apps/api/app/seeds/` reviewer seed package
- `apps/api/tests/test_seeds.py`
- `apps/api/tests/test_reviewer_seed.py`
- Root repo discoverability updates in `package.json` and `README.md`
- Current `.squad/` consolidation changes already staged for Milestone 4 closure, including canonical decisions/history updates and the tracked archive/removal of `kirk-squad-directory-audit.md`

## Safe to delete

- `.squad/decisions/inbox/copilot-directive-20260308T030721Z-pr-per-milestone.md` (already merged into `.squad/decisions.md`)
- Generated `apps/api/app/seeds/__pycache__/` contents

## Publish gate

Run only existing repo checks relevant to this delta:

1. Reviewer reset command from repo root: `npm run seed:api:reviewer-reset`
2. Seed-focused API regressions: `python -m pytest tests/test_seeds.py tests/test_reviewer_seed.py -q`
3. Standard repo lint/typecheck/build/test commands required by the branch merge rule before PR merge

## Rationale

The reviewer seed package is deliberate infrastructure supporting Milestone 4 review and smoke workflows, not transient experimentation. Conversely, merged inbox marker files and generated Python caches have no long-term value and create avoidable noise at the milestone PR boundary.
