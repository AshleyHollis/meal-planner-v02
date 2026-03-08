# Decision: Git Workflow Binding Directive Finalized (2026-03-09 — Kirk)

**Date:** 2026-03-09  
**Owner:** Kirk (Lead)  
**Status:** ✅ COMPLETE — Binding Directive Now Live  
**Scope:** All contributors; enforced at review and merge gates

## What Was Done

1. **Merged binding directive into decisions.md** — Git workflow and hygiene directive now published in the main team decision record (not left in inbox).
2. **Verified squad file tracking** — All untracked `.squad/` files committed in atomic batch; union merge strategy enforced in `.gitattributes`.
3. **Confirmed .gitattributes enforcement** — Line-ending control (eol=lf) and append-only merge strategy already in place and functional.
4. **Confirmed .gitignore hardening** — Build artifacts (bin/, obj/, .next/, *.egg-info, .aspire/) and generated files now properly ignored.
5. **Verified feature branch cleanliness** — `feature/git-publish-readiness-clean` branch pushed to origin; zero unpushed commits; zero untracked files.
6. **Created reusable squad skill** — `.squad/skills/git-workflow` published as team reference for commit/push/squad-file discipline.
7. **Recorded verification gates activation** — Log file committed: SYNC-09 and SYNC-10 (verification gates) now active; SYNC-11 ready to follow.

## Why This Matters

**Invisible state → visible state:** Team decisions/logs no longer left untracked.  
**Merge safety:** One logical unit per commit enables clean reverts; union merge strategy handles append-only squad files.  
**Data loss prevention:** Push discipline ensures all work lives on `origin/`; no local-only single points of failure.  
**CI/CD cleanliness:** `.gitattributes` enforcement prevents CRLF whitespace pollution; no build artifacts leak into tracking.  

## Implementation Evidence

| Artifact | Status |
| --- | --- |
| Binding directive in decisions.md | ✅ Published (96 lines, full coverage) |
| Reusable skill at .squad/skills/git-workflow | ✅ Complete (78 lines, 6 sections + references) |
| .gitattributes line-ending enforcement | ✅ Enforced (eol=lf on all source files) |
| .gitattributes union merge for append-only | ✅ Enforced (decisions.md, histories, logs) |
| .gitignore hardened for build artifacts | ✅ Complete (bin/, obj/, .next/, *.egg-info, .aspire/) |
| feature/git-publish-readiness-clean clean | ✅ All 12 commits pushed to origin; clean worktree |
| Squad file tracking complete | ✅ 70+ files committed; zero invisible state |
| Verification gates recorded | ✅ Log file 2026-03-09T07-00-00Z committed |

## Downstream Usage

**All contributors must follow:**
1. One logical unit per commit (feature, bug, decision)
2. Push every commit within the session it's created (max 3 unpushed)
3. All `.squad/` files committed together (never left untracked)
4. Rebase-before-merge; squash-and-merge to main via GitHub PR
5. Full test suite green before merge (npm run build:web && npm run test:api && npm run test:worker && npm run lint:web && npm run typecheck:web)

**Review gates apply at:**
- **Pull request review:** Kirk or designated reviewer verifies commit discipline and message format
- **Merge gate:** Full test suite must pass; feature branch must be rebased on main
- **Squad file merge:** Kirk manually resolves any true conflicts (union merge catches append-only issues)

## Next Steps

- **Immediate:** Continue Milestone 4 execution with verified Git hygiene discipline.
- **SYNC-09:** McCoy executes backend sync/conflict verification (independent reviewer).
- **SYNC-10:** McCoy executes mobile trip/offline E2E with mandatory visual smoke test.
- **SYNC-11:** Kirk final Milestone 4 acceptance review.
- **Merge window:** After SYNC-11 approval, rebase feature branch on main and prepare squash-and-merge to main via GitHub PR.

## Binding Status

**This directive is now binding on all workflow.** Extensible to other squad projects with identical Git discipline framework.

---

**Decision recorded by Kirk on Ashley Hollis authorization: "Yes and then continue build all of the app. We need to ensure that we are using Git well so it's easy to revert and merge changes."**

**Commit: 32b0af8b** — docs: Merge Git workflow binding directive into decisions.md; record verification gate activation
