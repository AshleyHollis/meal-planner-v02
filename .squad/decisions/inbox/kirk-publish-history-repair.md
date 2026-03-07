# Kirk Decision: Publish history repair via clean replay branch

- **Date:** 2026-03-08
- **Owner:** Kirk
- **Context:** GitHub rejected the feature-branch push because unpublished local history still contained tracked generated content under `apps/web/node_modules`, even though the current tree had already removed those artifacts.
- **Decision:** Preserve the verified source tree by creating a safety backup branch, cut a new feature branch from `origin/main`, and replay the current verified repository state as a clean snapshot commit instead of publishing the contaminated unpublished history.
- **Consequences:**
  - The publishable branch keeps the real application, spec, and infrastructure changes that exist at the verified feature head.
  - Generated/dependency artifacts remain excluded because the clean branch is rooted at `origin/main`, the repaired `.gitignore` is preserved, and local-only Claude settings are now ignored.
  - The original local history remains recoverable from backup branches if deeper forensic review is needed.
