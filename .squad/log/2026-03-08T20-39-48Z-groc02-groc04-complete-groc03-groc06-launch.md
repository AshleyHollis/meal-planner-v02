# GROC-02 / GROC-04 Complete → GROC-03 / GROC-06 Launch

**Timestamp:** 2026-03-08T20:39:48Z  
**Recorded by:** Scribe  
**Authorized by:** Ashley Hollis (full app build request)

## Entry

GROC-02 (backend derivation engine) and GROC-04 (grocery API router + mutations) are now complete and approved. Backend grocery derivation with SQL-backed list persistence, stale detection, idempotency receipts, and household-scoped mutation contracts is ready.

**Blocking dependencies satisfied:**
- GROC-02 ✅ SQL derivation engine complete, confirmed-plan-only, conservative offsets, stale detection, ad hoc preservation, version tracking
- GROC-04 ✅ Grocery router complete, derive/read/detail/re-derive/add-ad-hoc/adjust/remove/confirm endpoints active with household-scoped idempotent mutation receipts

**Ready to launch:**
- **GROC-03** (Scotty): Refresh and stale-draft orchestration. Must preserve user adjustments/ad hoc lines and never mutate a confirmed list silently.
- **GROC-06** (Uhura): Rewire the web grocery client to the real API contracts. Current `grocery-api.ts` and `GroceryView.tsx` still reflect pre-spec placeholder states.

**Evidence trail:**
- `.squad/specs/grocery-derivation/progress.md` §9 shows GROC-02 completion: 151 API tests passed, all validation green.
- `.squad/specs/grocery-derivation/progress.md` §9 shows GROC-04 completion: focused tests passed (7), schema tests passed (12), compileall passed.
- Both tasks evidence clean full API test suite pass and zero blocking issues.

**Context:**
- Milestone 2 (planner) is approved and stable; confirmed-plan handoff (`plan_confirmed` events) is live.
- Milestone 3 roadmap is locked: deliverable is trustworthy grocery derivation and review, not offline trip execution or reconciliation.
- GROC-05 (McCoy, backend verification) and GROC-10 (McCoy, E2E verification) remain mandatory acceptance gates before Milestone 3 closure.

**Next orchestration:**
- GROC-03 and GROC-06 now execute in parallel until either completes.
- GROC-05 unblocked immediately upon GROC-03 + GROC-04 completion.
- GROC-07 (Uhura, review/confirm UX) unblocked upon GROC-06 completion.
- GROC-10 (McCoy, E2E verification) unblocked upon GROC-06 + GROC-07 completion.
- GROC-11 (Kirk, final review) unblocked upon GROC-10 completion.
