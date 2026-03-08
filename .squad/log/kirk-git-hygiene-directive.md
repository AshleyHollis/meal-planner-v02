# Git Hygiene Directive
**Owner:** Kirk  
**Date:** 2026-03-09  
**Status:** Active Directive (binding on all workflow)  

## Problem Statement
- **Untracked files:** 70+ decision/log/spec files in `.squad/` and generated code/artifacts in `apps/`
- **Uncommitted changes:** 78 files with local edits; 6,035 insertions/deletions staged for commit but not committed
- **Outstanding pushes:** 9 commits local on `feature/git-publish-readiness-clean` not yet pushed to `origin/`
- **Line ending warnings:** CRLF inconsistency in working copy vs. committed LF
- **Risk:** Large committed trees with unrelated artifacts make reversions brittle; merge conflicts harder to reason about; lost commits if branch is accidentally garbage-collected

## Analysis

### What's Working
- **Commit messages** are excellent: atomic, descriptive, scoped to feature/task (e.g., "AIPLAN-12: Milestone 2 approved")
- **Feature branching** is in place: clean separation between `main`, `feature/git-publish-readiness-clean`, and local dev
- **Co-author trailer** is already adopted on milestone commits
- **History is traceable:** each commit clearly documents what changed and why

### What's Broken
1. **No workflow definition:** team doesn't have shared rules for when to commit, what to include, or how to push  
   → Result: Long gaps between commits; unrelated files staged together; unclear merge timelines
2. **Untracked files accumulate:** `.squad/` logs, decisions, and generated `apps/` code sit untracked for days  
   → Result: Invisible state changes; can't see what's "done" without manual inspection; lost work if `git clean` is run
3. **Local commits not pushed:** 9 commits (three Milestone completions + sessions work) still local  
   → Result: Single point of failure; if dev machine crashes, irreplaceable work is lost
4. **No merge strategy defined:** feature branch will eventually need to land on `main`; no rules for squash vs. merge-commit vs. rebase  
   → Result: History confusion; hard to bisect; unclear revision ownership
5. **Line-ending configuration missing:** `.gitattributes` doesn't enforce LF/CRLF policy  
   → Result: Warnings on every commit; diffs polluted by whitespace; merge conflicts on unrelated lines

---

## Directives

### 1. Commit Discipline (REQUIRED)
**All commits to tracked code must follow this discipline:**

- **One logical unit per commit:** one feature, one bug fix, one decision merge. Never mix unrelated changes.
- **Exclude generated files:** never commit `bin/`, `obj/`, `.next/`, `dist/`, `*.egg-info`, `.next-dev/`, `.playwright-artifacts/`, `apps/web/.next-dev/`, `apps/web/.playwright-artifacts/`
- **Exclude temp build outputs:** `.pytest_cache`, `__pycache__`, `*.pyc`, `.tsbuildinfo`
- **Commit message template:**
  ```
  [SCOPE]: Brief one-line summary
  
  - Detailed explanation of what changed and why
  - One change per bullet; minimal prose
  - Link to relevant decision, spec, or task ID if applicable
  
  Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
  ```
- **Before committing, run:**
  ```
  git status  # Verify no build artifacts are staged
  git diff --cached  # Review every line you're committing
  ```

### 2. Push Discipline (REQUIRED)
**Every commit must be pushed within the session it's created.**

- **Local commits are not safe.** They live on one machine and can be lost.
- **Push at natural break points:** after a spec approval, after a test-passing review, after a decision merge. Never accumulate more than 3 unpushed commits.
- **Push command:**
  ```
  git push origin <your-feature-branch>
  ```
- **If `origin` is behind your feature branch**, you must rebase, not merge:
  ```
  git fetch origin
  git rebase origin/main  # or whatever the target branch is
  git push origin --force-with-lease <your-feature-branch>
  ```

### 3. Squad File Discipline (REQUIRED for `.squad/` files)
**All `.squad/` files must be tracked and committed together.**

- **When you create or modify `.squad/` files:**
  - Create the file in the appropriate directory (e.g., `.squad/decisions/inbox/`, `.squad/log/`, `.squad/orchestration-log/`)
  - Add and commit it **before closing your session** with message pattern: `docs: [describe what the decision/log records]`
  - Append-only files (`.squad/decisions.md`, team member history files) use union merge strategy (already configured in `.gitattributes`)
- **Never leave `.squad/` files untracked for more than one session.**
  - Untracked decisions are invisible to the team.
  - Untracked logs make recovery and review audits impossible.

### 4. Feature Branch Merge Strategy (REQUIRED for landing on main)
**When a feature branch reaches readiness for merge to `main`:**

- **Verify:** Run full test/lint/typecheck suite locally first: `npm run build:web && npm run test:api && npm run test:worker && npm run lint:web && npm run typecheck:web`
- **Rebase to main:** Ensure feature branch is rebased on latest `main`
- **Merge strategy:** Squash-and-merge to `main` with a single comprehensive commit that traces back to the feature branch
  ```
  git rebase origin/main
  git push origin --force-with-lease <your-feature-branch>
  # Then via GitHub PR: squash-and-merge
  ```
- **Never merge with a merge commit** unless the feature is >100 commits and needs per-author attribution (rare)
- **Always preserve the feature branch as a tag or backup** before deleting it: `git tag feature/<name>-backup <branch-sha>`

### 5. .gitattributes Enforcement (REQUIRED)
**Create `.gitattributes` at repo root to enforce line endings and merge strategies:**

```gitattributes
# Line endings: LF everywhere
* text=auto
*.py text eol=lf
*.js text eol=lf
*.ts text eol=lf
*.tsx text eol=lf
*.json text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf

# Binary files
*.db binary
*.pyc binary
*.egg-info binary

# Squad files: union merge strategy for append-only memory
.squad/decisions.md merge=union
.squad/agents/*/history.md merge=union
.squad/log/*.md merge=union
.squad/orchestration-log/*.md merge=union
```

---

## Implementation Checklist

- [ ] Create `.gitattributes` in repo root (Kirk will commit)
- [ ] Run `git config core.safecrlf true` locally to catch line-ending violations
- [ ] For current branch (`feature/git-publish-readiness-clean`):
  - [ ] Stage all untracked `.squad/` files (70+ files) in atomic commit
  - [ ] Review and stage all tracked code changes in logical bundles
  - [ ] Push all local commits to `origin/`
- [ ] Update `.squad/routing.md` to add Git process owner (recommend Ralph as work monitor or delegate to each task owner)
- [ ] Add this directive to `.squad/skills/git-workflow` for reference

---

## What This Fixes

| Problem | Fix |
| --- | --- |
| Large untracked trees | Squad files auto-committed per-session; no invisible state |
| Unrelated files staged together | One logical unit per commit enforced |
| Lost local commits | Push discipline ensures all work is on `origin/` |
| Merge chaos | Squash-and-merge to main + per-author history on feature branch |
| Line-ending warnings | `.gitattributes` + `core.safecrlf=true` prevents CRLF leaks |
| Unclear merge authority | Rebase-before-merge ensures linear history; Kirk decides final merge window |

---

## When to Escalate

- **Branch diverges >50 commits from main:** Kirk must decompose feature into smaller merge windows
- **Merge conflict on `.squad/` file:** Kirk manually resolves (union merge catches only truly append-only conflicts)
- **Accidental tracked artifact discovered after merge:** Kirk branches back, removes artifact, fast-forwards main with clean history
- **Line-ending violations detected at CI:** Reject PR; require local `git reset --hard` and `git clean -fdx` before re-push

---

## References

- Current branches: `main`, `feature/git-publish-readiness-clean` (9 unpushed commits)
- Affected team: All (every contributor must follow discipline)
- Related decisions: `kirk-git-publish-readiness.md`, `kirk-local-startup-triage.md`
- Scope: Binding on this project; extensible to other squad projects with identical workflow
