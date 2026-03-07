# Kirk Decision: Local and Preview/Test Environment Seed Data Strategy

**Date:** 2026-03-09  
**Requested by:** Ashley Hollis  
**Owner:** Kirk (Lead)  

## Decision

**The answer is: YES, with conditional scope differences between local and preview/test.**

The product **MUST** have seeded test data for both local and preview/test environments to enable manual functional and visual smoke testing without friction. This is a formal team/product decision.

### What Kinds of Data Should Be Seeded

Seed data must cover the full MVP critical path with realistic scenarios:

1. **Household Foundation** (required for all flows)
   - One active household with a primary-planner user assigned
   - One secondary household to verify household-scoping boundaries
   - One user with membership across both households to verify isolation

2. **Inventory Foundation** (enables planner and grocery flows)
   - Pantry items (non-perishables): oil, flour, pasta, canned goods
   - Fridge items (short-lived): milk, eggs, vegetables, leftovers example
   - Freezer items (long-lived): meats, pre-made items
   - Items with mixed freshness bases (known exact date, estimated, unknown)
   - At least one item with expiry risk (within 3 days) to test expiry visibility
   - At least one item marked as leftovers to test reuse scenarios
   - Total: ~15–20 items across locations with realistic quantities and freshness metadata

3. **Weekly Meal Plan** (enables grocery derivation and trip flows)
   - One confirmed meal plan for the next 7 days with varied meal types
   - Meals using ingredients from seeded inventory to test derivation accuracy
   - At least one meal with dietary-restriction notes (vegetarian, allergy-free, etc.)
   - Include at least one ad hoc meal adjustment to show plan editability

4. **Grocery List** (enables trip and reconciliation flows)
   - One confirmed grocery list derived from the seeded plan and inventory
   - Items both in-stock (shown as 0 quantity need) and out-of-stock (shown with need)
   - At least one user-adjusted item to show override preservation
   - At least one ad hoc item added during trip to test stale-list behavior
   - Status: confirmed and ready for trip execution

5. **Trip Execution Artifact** (optional, if offline sync is under review)
   - One completed or in-progress shopping trip with check-offs and quantity edits
   - Offline-sync test state if Milestone 4 is under active verification

6. **Reconciliation Trail** (optional, if post-shopping/post-cooking is under review)
   - One example post-shopping inventory reconciliation
   - One example post-cooking reconciliation with leftovers created

### Local vs. Preview/Test Environment Differences

| Aspect | Local | Preview/Test |
| --- | --- | --- |
| **Scope** | Full seed dataset (all 6 categories) | Same scope as local |
| **Data Reset** | Manual, via CLI or db reset command | Automatic on preview build/deploy |
| **Persistence** | Preserved across local dev sessions unless explicitly reset | Fresh seed on each PR/preview creation |
| **AI State** | Seeded with mock/deterministic fallback (no live Azure OpenAI calls) | Same as local during testing; live AI in production preview if needed |
| **Auth Context** | Seeded primary user via `X-Dev-*` header or hardcoded session | Real Auth0 flow or seeded JWT for preview |
| **Refresh Cadence** | Developer keeps seed data fresh manually as MVP evolves | Infrastructure code ensures seed schema matches migrations |

**Key principle:** The **schema must always match** the current database migrations. If a migration changes inventory fields, the seed script must be updated synchronously so the seed data remains valid.

### Reset and Reseed Expectations

1. **Local Development Reset**
   - Provide a CLI command or npm script (e.g., `npm run seed:reset`) that drops and recreates all tables, then repopulates with the seed dataset.
   - Make the seed script idempotent: running it twice produces the same state.
   - Document the reset flow prominently in the local dev README.
   - Seed data should be kept in version-controlled seed scripts, not exported SQLite files.

2. **Preview Environment Seeding**
   - Seed data is part of the infrastructure-as-code pipeline: migrations run, then seed scripts execute automatically.
   - Each preview deployment creates a fresh database with seeded data from scratch.
   - No manual reseed needed; the seed is deterministic and version-controlled.

3. **Production Environment (Out of Scope for Now)**
   - Production databases do NOT receive seeded test data.
   - Production uses real user-created data only.
   - Any seed-like data (e.g., default staple items) will be handled in a future feature spec, not through this seeding mechanism.

### Risks to Avoid

1. **Schema Drift**: If migrations change inventory fields but seed scripts are not updated, the seed will fail silently or produce incomplete data. **Mitigation:** Add a migration-lint rule that checks seed scripts after schema changes. Attach seed maintenance to every milestone's migration checklist.

2. **Test Data Leakage into Production**: A misconfigured deployment could seed production with test data. **Mitigation:** Make seeding conditional on environment variables (e.g., `ASPIRE_ENV=local` or `PREVIEW_ENV=true`). Never ship seed code with production binaries.

3. **Seed Data Too Simple or Narrow**: If the seed dataset doesn't cover trip conflicts, offline sync edge cases, or multi-user scenarios, developers and reviewers will hit untested flows during smoke testing. **Mitigation:** Expand seed scenarios alongside each MVP milestone; McCoy's smoke-test evidence should flag missing seed scenarios.

4. **Seed Scripts Become Hard to Maintain**: As the schema grows (Milestones 4, 5), seed scripts can become complex. **Mitigation:** Keep seed data separate from test fixtures. Store seed in `apps/api/app/seeds/` with SQL or ORM-backed scripts. Test fixtures (used by pytest) remain in `tests/`.

5. **Local Dev Seed Conflicts with Personal Data**: A developer working on local changes might seed the same database instance and lose personal test data. **Mitigation:** Default to a separate `__seed__` database file or SQLite memory instance for seeding. Document the reseed flow clearly so developers know when to reset.

### Formal Team/Product Implications

This decision is **formally recorded as a team commitment** because:

1. **Milestone End Gates Depend on It**: McCoy's visual smoke-test gate requires realistic data to validate desktop and mobile flows. Without seed data, smoke testing becomes guesswork about what state the app should be in.

2. **Product Trust Requires It**: The constitution prioritizes manual functional and visual testing (section 5.2 Release Gates, 2.1 Mobile Shopping First, 2.7 UX Quality and Reliability). Seed data is essential infrastructure for that gate.

3. **It Affects Local Startup Guidance**: The Milestone 0 foundation work must include a `seed` CLI command and documentation so new developers can start productive work immediately without manual data entry.

4. **It Becomes a Schema Maintenance Burden**: Seed scripts must be kept in sync with migrations. Future implementation must include this as an explicit task (e.g., "update seed scripts for migration ABC").

5. **It Unblocks Offline/Sync Verification**: Milestone 4 (mobile trip mode, offline queueing, sync) cannot be verified reliably without a pre-populated grocery list and trip state. Seeding is prerequisite.

## Recommended Next Steps

1. **Immediate (Milestone 4 planning)**
   - Create `apps/api/app/seeds/` directory with modular seed scripts for households, inventory, plans, groceries.
   - Add a `python -m app.seeds --reset` command to the API startup flow.
   - Document in `.squad/project/architecture/local-development-guide.md`.
   - Add seed maintenance to the Milestone 4 task plan (Uhura and Scotty confirm seed is valid for their offline/sync work).

2. **Integration (as Milestones 4 and 5 ship)**
   - Expand seed data to cover trip states, offline mutations, and reconciliation artifacts.
   - Add a seed-validation test (e.g., "seed is reproducible, schema-valid, and covers all critical paths").
   - Include seed maintenance in the final verification gate before each milestone acceptance.

3. **Documentation**
   - Add seed reset instructions to the local dev README.
   - Create a seed data contract document (`apps/api/app/seeds/SEED_SCHEMA.md`) that lists what data is seeded and why.
   - Include seed assumptions in the Milestone 4 offline sync spec and Milestone 5 reconciliation spec.

4. **Operational (if Preview Automation Happens)**
   - Ensure the preview-deploy workflow automatically runs migrations and seed scripts in order.
   - Add environment check (fail loudly if ASPIRE_ENV or preview flag is not set) before seeding production.

## Acceptance Criteria for This Decision

- Seed data exists and is version-controlled in the repository.
- Seed data covers all critical MVP flows (planning through reconciliation).
- Seed reset command is documented and easy to run locally.
- Seed data remains valid after every schema migration.
- No test data appears in production by accident.
- McCoy's smoke-test gate confirms that realistic seed data enabled confident manual testing.
- Team members report that seed data reduced friction in local development and review cycles.

## Decision Closure

This decision establishes seed data as a formal, budgeted part of MVP delivery. It is **not optional** and **not deferred to Phase 2**. Seed data must be in place before the Milestone 4 final verification gate so manual trip/sync testing can proceed confidently.
