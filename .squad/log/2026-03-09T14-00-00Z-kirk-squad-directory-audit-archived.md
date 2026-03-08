# Kirk: .squad Directory Audit & Cleanup Decision (2026-03-09T14-00-00Z)

**Requested by:** Ashley Hollis  
**Audited by:** Kirk  
**Date:** 2026-03-09T14-00-00Z  
**Status:** ✅ AUDIT COMPLETE — Critical action items below

---

## Executive Summary

The `.squad/` directory is **substantially in good order** but has one **critical blocking issue** that must be resolved immediately:

1. ⚠️ **BLOCKING:** Decision files are duplicated across `.squad/decisions/` root and `.squad/decisions/consolidated/` subdirectory. The consolidated/ directory must be removed and root files staged.

2. ✅ **Decisions framework is otherwise clean:** `.squad/decisions.md` is canonical; `.squad/decisions/inbox/` will be empty after this audit.

3. ✅ **Log structure is sound:** Chronological organization, clear naming convention, no stale files detected.

---

## Detailed Audit Findings

### `.squad/decisions/` Directory

**Status:** ⚠️ **CRITICAL DUPLICATION ISSUE**

**Problem identified:**
- **Canonical layer (root):** 11 decision files exist at `.squad/decisions/` root (untracked):
  - `2026-03-09T07-00-00Z-git-hygiene-process.md` (under Kirk review)
  - `2026-03-09T09-30-00Z-seed-data-required.md` (approved)
  - 8 milestone-decision files (2026-03-08 GROC/approval records)
  - 1 scotty-groc-02-04-backend.md

- **Duplicate layer (consolidated/ subdirectory):** Same 11 files also exist in `.squad/decisions/consolidated/` (tracked in git)

- **Result:** Git state is confused; root files are untracked (new), consolidated versions are tracked (old). This creates merge hazards and confuses future reviewers about which is authoritative.

**Root cause:** A prior session created the consolidated/ subdirectory, then root copies appeared. No cleanup happened; both exist simultaneously.

**Verdict:** **This must be fixed before merging to main.** Consolidated/ directory should not exist per the audit policy.

### `.squad/decisions/inbox/` Directory

**Status:** ✅ **WILL BE CLEAN AFTER AUDIT**

- Directory currently contains 26 files from prior cleanup + this audit decision file.
- All 26 files in inbox are stale (should have been archived in prior 2026-03-09T13-00-00Z cleanup).
- **After this audit:** Inbox should contain only `kirk-squad-directory-audit.md` (this file).

**Action:** All other inbox files should be moved to `.squad/log/` as historical record if not already archived.

### `.squad/log/` Directory

**Status:** ✅ **CLEAN AND WELL-ORGANIZED**

- 81+ chronologically-named logs (2026-03-07 through 2026-03-09).
- Clear naming convention: `YYYY-MM-DDTHH-MM-SSZ-description.md`
- No stale or orphaned entries detected.
- Untracked files from 2026-03-09 afternoon (2026-03-09T10-00-00Z through 2026-03-09T13-00-00Z) need staging to preserve audit trail.

**Verdict:** Log directory is healthy. Untracked entries should be staged.

### `.squad/orchestration-log/` Directory

**Status:** ✅ **CLEAN**

- 58 chronologically-named orchestration records.
- One untracked file: `2026-03-09T12-30-00Z-milestone-end-decision-merge.md` (consolidation handoff).
- No stale or duplicates detected.

---

## Policy Decision: `.squad/decisions/` vs `.squad/decisions/inbox/` vs `.squad/log/`

### Canonical Policy (Binding)

**`.squad/decisions/` (Canonical Layer — ROOT LEVEL)**
- **Purpose:** Active, approved decisions that remain binding for current or upcoming milestones.
- **Location:** Files live at the root of `.squad/decisions/` (NOT in subdirectories like consolidated/).
- **Lifecycle:** A decision file stays here as long as it is:
  - Freshly approved (within current milestone), OR
  - A standing governance rule (e.g., Git workflow directives), OR
  - Under active review (e.g., git-hygiene-process)
- **No subdirectories:** Do not create subdirectories within decisions/. If organizational structure is needed in the future, discuss with team first.

**`.squad/decisions/inbox/` (Processing Queue)**
- **Purpose:** Transient queue for incoming decisions awaiting consolidation or review.
- **Lifecycle:** Items spend ~1-24 hours here; processed by Scribe or Kirk to either:
  - Merge into canonical `.squad/decisions.md` (governance rules), OR
  - Assign as active file in `.squad/decisions/` (approval-gate item), OR
  - Archive to `.squad/log/` (evidence trail preserved)
- **Target state:** Empty or ≤2 items max between sessions.

**`.squad/log/` (Historical Archive — Append-Only)**
- **Purpose:** Complete audit trail of all past decisions, approvals, task completions, and governance evolution.
- **Lifecycle:** Permanent record. Files go here after:
  - A milestone ends (task decisions moved from inbox), OR
  - A governance rule is superseded or archived, OR
  - Evidence trails from completed feature work
- **Naming:** Chronological + descriptive (e.g., `2026-03-09T13-00-00Z-inbox-cleanup-complete.md`)
- **Searchability:** Future reviewers find past context via filename search

---

## Cleanup Actions Required (IMMEDIATE — BLOCKING)

### 1. 🚨 **Resolve decision file duplication** (P0 — BLOCKING)

**Issue:** Files in both root and consolidated/subdirectory.

**Correct action:** Delete the consolidated/ subdirectory. Keep all files at root of `.squad/decisions/`.

```powershell
# Remove the duplicated consolidated subdirectory
Remove-Item ".squad\decisions\consolidated" -Recurse -Force

# All decision files should now live in .squad/decisions/ root (not in subdirectories)
```

**Why:** Subdirectories create merge hazards and confuse git tracking. The inbox exists for the queue function; canonical decisions live at root.

### 2. ⚠️ **Stage all decision files** (P0)

After removing consolidated/, stage all root decision files:

```powershell
git add ".squad\decisions\2026-03-09T07-00-00Z-git-hygiene-process.md"
git add ".squad\decisions\2026-03-09T09-30-00Z-seed-data-required.md"
git add ".squad\decisions\2026-03-08T20-00-00Z-sulu-groc01-schema-approved.md"
git add ".squad\decisions\2026-03-08T21-00-00Z-groc03-refresh-decision.md"
git add ".squad\decisions\2026-03-08T21-00-00Z-groc06-api-wiring-decision.md"
git add ".squad\decisions\2026-03-08T21-15-00Z-mccoy-groc05-verification-approved.md"
git add ".squad\decisions\2026-03-08T21-15-00Z-uhura-groc07-review-ux-decision.md"
git add ".squad\decisions\2026-03-09T00-00-00Z-mccoy-groc10-ui-e2e-approved.md"
git add ".squad\decisions\2026-03-09T00-00-00Z-scotty-groc08-groc09-hardening-approved.md"
git add ".squad\decisions\2026-03-09T01-00-00Z-kirk-groc11-milestone-acceptance.md"
git add ".squad\decisions\scotty-groc-02-04-backend.md"
```

### 3. ✅ **Stage agent histories and identity updates** (P0)

```powershell
git add ".squad\agents\kirk\history.md"
git add ".squad\agents\mccoy\history.md"
git add ".squad\agents\scotty\history.md"
git add ".squad\agents\scribe\history.md"
git add ".squad\agents\uhura\history.md"
git add ".squad\identity\now.md"
git add ".squad\decisions.md"
```

### 4. ✅ **Stage recent log entries** (P0)

```powershell
git add ".squad\log\2026-03-09T10-00-00Z-seed-data-files-found-scotty-mccoy-active.md"
git add ".squad\log\2026-03-09T11-13-36Z-uhura-sync10-grocery-stability.md"
git add ".squad\log\2026-03-09T12-45-00Z-scotty-repo-cleanup-status.md"
git add ".squad\log\2026-03-09T13-00-00Z-inbox-cleanup-complete.md"
git add ".squad\orchestration-log\2026-03-09T12-30-00Z-milestone-end-decision-merge.md"
```

### 5. ✅ **Verify inbox cleanup** (P0)

After archiving inbox stragglers to log, inbox should contain only this audit decision.

---

## Deferred or Non-Issues

### ✅ Not a problem: Milestone 4 app source changes

Git status shows untracked app source files (`apps/api/app/seeds/`, test files). These are **intentional Milestone 4 deliverables** (seed data required for SYNC-11). They should be staged and committed as part of the integration commit, not deleted. This is a P0 merge task, not a cleanup issue.

### ✅ Not a problem: Stale log entries

All 81 log entries are part of the Milestone 1-4 execution record and remain valuable for future audit. None are duplicates or orphaned. Untracked recent entries should be staged (Action 4 above).

---

## Recommendations Going Forward

1. **Keep inbox empty as default state.** Process incoming decisions within the same session (consolidate or assign). Max queue time: <24 hours.

2. **Never create subdirectories in `.squad/decisions/`.** If organizational structure is needed, discuss with team first and document in policy.

3. **Continue chronological log naming.** Current convention is clear and searchable. Maintain `YYYY-MM-DDTHH-MM-SSZ-description.md` pattern.

4. **Quarterly audit pass.** Every 3 months (or at major release points), run this audit to catch any inconsistencies early.

---

## Final Verdict

⚠️ **`.squad/` directory has one critical blocking issue that must be fixed before main merge.**

**Blocking Issue:** Duplicated decision files in root and consolidated/ subdirectory — requires removal of consolidated/ directory and staging of root files.

**Audit Status:** Clean with 5 action items required (1 critical, 4 standard staging).

**Effort:** ~10 minutes to execute cleanup actions and commit.

**Ready for:** Merge to main after consolidated/ directory cleanup and file staging.

---

*Recorded by Kirk on Ashley Hollis authorization (2026-03-09T14-00-00Z).*  
*Audit scope: Full directory inventory, consistency, lifecycle policy, and blocking issues.*
