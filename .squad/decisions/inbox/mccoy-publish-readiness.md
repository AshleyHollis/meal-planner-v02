# McCoy: Milestone 4 Publish Readiness Verification (2026-03-09)

**Requested by:** Ashley Hollis  
**Audited by:** McCoy  
**Scope:** Reviewer-readiness check for Milestone 4 publication; not a duplicate of release mechanics

---

## Verdict

**Current status: SHIP-READY from reviewer perspective once the publish commit is finalized.**

Milestone 4 product evidence remains strong and the newly dirty app changes look intentional. The only remaining gap is procedural, not product-risk:

1. `git status` is still dirty and the branch is `ahead 2` of `origin/feature/git-publish-readiness-clean`.
2. The branch is not yet in a post-publish state: local commits are still ahead of origin and the worktree is still dirty.
3. The previously missing archive now exists at `.squad/log/2026-03-09T14-00-00Z-kirk-squad-directory-audit-archived.md`, so the evidence trail is consistent again.

---

## Dirty-Set Classification

### Intentional milestone integration work

- `apps/api/app/seeds/__init__.py`
- `apps/api/app/seeds/__main__.py`
- `apps/api/app/seeds/reviewer.py`
- `apps/api/tests/test_seeds.py`
- `apps/api/tests/test_reviewer_seed.py`
- `package.json`
- `README.md`

These files form a coherent reviewer-seed slice:
- reusable API seed package
- CLI entrypoint (`python -m app.seeds reviewer-reset`)
- focused regression coverage
- repo-level script/docs for reviewer reset discoverability

Focused verification passed, so these should be treated as intentional infrastructure to either commit together or explicitly revert together.

### Intentional squad/memory integration work

- `.squad/agents/kirk/history.md`
- `.squad/agents/mccoy/history.md`
- `.squad/agents/scotty/history.md`
- `.squad/agents/scribe/history.md`
- `.squad/decisions.md`
- `.squad/identity/now.md`
- deletion of `.squad/decisions/inbox/kirk-squad-directory-audit.md`

These are consistent with milestone-close consolidation and publish-prep bookkeeping.

### Intentional but still-to-be-consolidated publish-session notes

- `?? .squad/decisions/inbox/kirk-milestone4-publish.md`
- `?? .squad/decisions/inbox/scribe-publish-handoff.md`
- `?? .squad/decisions/inbox/mccoy-publish-readiness.md`

These appear to be intentional publish-session handoff notes, not disposable runtime residue. They should be merged/archived consistently before the final publication commit so the inbox state matches the team’s cleanup posture.

### Evidence-trail note (resolved during audit window)

- `D .squad/decisions/inbox/kirk-squad-directory-audit.md`
- `?? .squad/log/2026-03-09T14-00-00Z-kirk-squad-directory-audit-archived.md`

This deletion/archival pair now lines up with the squad records, so it is no longer a blocker.

---

## Minimal Validation Set Warranted by Current Dirty Files

Because the app-facing dirty set is limited to API reviewer-seed infrastructure plus root script/docs wiring, the minimal pre-merge validation set is:

1. `python -m pytest apps\api\tests\test_seeds.py apps\api\tests\test_reviewer_seed.py -q`
2. `npm run seed:api:reviewer-reset -- --database-url sqlite+pysqlite:///<temp> --environment test --scenario sync-conflict-review`

### Validation results

- ✅ `python -m pytest apps\api\tests\test_seeds.py apps\api\tests\test_reviewer_seed.py -q` → `10 passed`
- ✅ `npm run seed:api:reviewer-reset -- --database-url sqlite+pysqlite:///<temp> --environment test --scenario sync-conflict-review` succeeded and produced the expected seeded summary

No additional web/worker build checks are minimally required by the current dirty set because no web/worker source files changed in this review window; broader milestone evidence is already recorded in prior McCoy/Kirk approvals.

---

## Post-Publish Sanity Check

**Kirk has not fully published this latest local state yet.** The branch is still ahead of origin and the worktree remains dirty, so there is no successful post-publish state to bless today.

If Kirk publishes successfully, the branch/worktree is only Milestone-5-ready when all of the following are true:

- `git status --short --branch` shows no modified/untracked files
- the feature branch is no longer ahead/behind its origin counterpart
- the reviewer-seed slice is either committed as one coherent unit or intentionally removed
- the draft inbox notes are consolidated appropriately

Until then, **Milestone 5 should not start from this worktree**. Once the publish commit lands and the branch/worktree is clean, I see no remaining reviewer blocker to starting Milestone 5.

---

## Ship Summary

**Ship-ready, pending final publish mechanics.** Product readiness looks good, the seed slice validates cleanly, and I do not see a remaining reviewer blocker; publication just is not complete until the current intentional dirty set is committed/pushed and the branch returns to a clean synced state.
