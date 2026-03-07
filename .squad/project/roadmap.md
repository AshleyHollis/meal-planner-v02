# Product Roadmap: AI-Assisted Household Meal Planner

Date: 2026-03-07
Requested by: Ashley Hollis
Status: Draft for review

## 1. Purpose
This roadmap turns the approved constitution, PRD, and architecture into a practical delivery sequence for `meal-planner-v02`. It prioritizes the smallest trustworthy MVP loop first: inventory-aware weekly planning, grocery review, mobile/offline trip execution, and clear inventory reconciliation after shopping and cooking.

## 2. Roadmap Planning Rules
- **MVP first:** work that enables the core weekly planning-to-shopping-to-reconciliation loop comes before expansion work.
- **Constitution first:** mobile shopping, offline support, shared-household safety, trustworthy inventory, and explainable AI are built into MVP milestones rather than deferred.
- **Thin client, explicit API:** the roadmap follows the approved architecture of a Next.js client over FastAPI contracts with Python workers for retryable or heavy work.
- **Quality is part of delivery:** testability, preview environments, observability, and conflict handling are treated as release-enabling work, not cleanup.
- **Independent verification is mandatory:** the person who implements a slice cannot be the one who closes its testing or final acceptance gate. Named squad roles help route ownership, but reviewer independence must be real human separation, not just a different label on the same implementation work.

## 3. Delivery Assumptions
- The approved working architecture is: Next.js + TypeScript web app, FastAPI API, Python workers, IndexedDB-class offline client storage, SQL Server/Azure SQL, Azure Storage Queues, Auth0, Aspire, Azure, Terraform, and GitHub Actions.
- AI technical defaults for MVP are now proposed in `.squad/project/architecture/ai-architecture.md`, including provider direction, async execution path, prompt versioning, grounding pipeline, explainability contract, and fallback posture.
- The repository is still planning-first, so early MVP work includes implementation scaffolding, app contracts, and environment wiring before feature depth.
- Open implementation-level choices that remain unresolved should be closed inside milestone specs without changing the approved product direction.

## 4. MVP Milestone Sequence

### Milestone 0 — MVP foundation and delivery spine **[MVP]**
**Outcome:** The repo can host the product architecture and safely deliver previewable vertical slices.

**Scope**
- Set up the monorepo/app structure for web, API, worker, infra, and tests.
- Establish local Aspire orchestration for web, API, worker, SQL Server, and Azurite.
- Implement baseline Auth0 integration in the backend API (JWT validation, OIDC callback, session bootstrap endpoints such as `GET /api/v1/me`). Auth0 must not be installed in the Next.js frontend — the Auth0 Next.js package breaks Azure Static Web Apps startup. The frontend authenticates via API endpoints only.
- Stand up app-owned Terraform, preview deployment wiring, and repo-owned CI/CD composition against shared-infra capabilities.
- Define seed/test data patterns, baseline observability, and initial contract-testing/E2E harness structure.
- Wire the AI provider/config seam early: Key Vault-backed AI config, provider wrapper, queue message contract, and fake-provider path for deterministic tests should be part of foundation work instead of Milestone 2 cleanup.

**Why it comes first**
- All downstream milestones depend on stable app structure, auth/session bootstrap, deployment flow, and test scaffolding.
- The approved architecture makes preview automation, Key Vault-backed secrets, and shared-infra integration explicit dependencies rather than optional later work.

**Key dependencies**
- Shared-infra support for GitHub OIDC, workload identity, External Secrets or equivalent, gateway/DNS/TLS path, and reusable Terraform/workflow patterns.

**Constitution alignment**
- 2.7 UX Quality and Reliability
- 3.1 Approved Default Stack
- 5.2 Release Gates
- 5.3 Reliability and Observability

---

### Milestone 1 — Household context and authoritative inventory foundation **[MVP]** ✅ COMPLETE
**Outcome:** A household can sign in, access the right household context, and trust core inventory records across pantry, fridge, freezer, and leftovers.

**Status:** ✅ Completed on 2026-03-08. All 11 feature-spec acceptance criteria verified and approved by Kirk. Household-scoped authoritative inventory with SQL-backed persistence, idempotent mutation handling, append-only audit history, correction chaining, freshness-basis preservation, and one-primary-unit enforcement now available.

**Scope**
- Household membership and authorization model for MVP primary-planner workflows.
- Inventory item model, CRUD flows, quantity adjustments, freshness/expiry metadata, and audit history.
- Clear inventory read models for web and mobile consumption.
- Deterministic mutation rules, idempotent receipts where needed, and reversible/correctable adjustment paths.

**Why it comes here**
- Inventory is the trust-data base for meal planning, grocery derivation, trip context, and post-action reconciliation.
- AI planning and grocery generation are low-value without reliable household and inventory state.

**Depends on**
- Milestone 0

**Constitution alignment**
- 2.3 Shared Household Coordination
- 2.4 Trustworthy Planning and Inventory
- 6.2 Data Standards

---

### Milestone 2 — Weekly planner and explainable AI suggestions **[MVP]** ✅ COMPLETE
**Outcome:** A user can build a weekly plan manually or start from editable AI suggestions grounded in household context, with clear fallback and explanation behavior.

**Status:** ✅ Completed on 2026-03-08. All 12 feature-spec acceptance criteria verified and approved by Kirk. Three-state plan model (suggestion → draft → confirmed), per-slot regeneration, stale detection, confirmed-plan protection, grocery handoff seam, worker-backed async generation with tiered fallback modes, and full observability instrumentation now available.

**Scope**
- Weekly planner UI and API contracts.
- Meal slots, manual editing, plan confirmation flow, and linked planning rationale.
- Dietary restrictions, household preferences, equipment constraints, and substitution notes.
- AI system boundary for MVP:
  - AI only proposes advisory weekly meal-plan suggestions and rationale.
  - Deterministic services remain authoritative for inventory, meal-plan persistence, grocery derivation, sync, and audit behavior.
  - No AI output silently mutates authoritative household state.
- Grounding pipeline for suggestion requests using product-owned data such as inventory/expiry snapshot, dietary preferences and restrictions, equipment constraints, pinned or excluded meals, and recent meal history where available.
- AI suggestion request/review flow with structured explanation payloads, user edits, acceptance/rejection tracking, stale-result indicators, and no silent authoritative mutation.
- Worker-backed async generation path for AI suggestions, including request status lifecycle, bounded retries, visible failure states, and provider-neutral integration boundaries.
- Fallback behavior for sparse data, provider timeout, rate-limit, or provider failure so users can continue with manual planning or review a deterministic fallback suggestion set.
- Evaluation coverage for AI contracts: fixture-driven grounding tests, result-shape tests, fallback-path tests, and E2E review/edit/accept journeys without routine live-provider dependence.
- Implement the explicit AI contract defined in `ai-architecture.md`: prompt/policy version fields, reason-code-based explainability, grounding-hash reuse rules, and tiered fallback behavior.

**Why it comes here**
- The meal plan is the source for grocery need calculation.
- Explainable, editable AI is in MVP scope, but it should land on top of authoritative household and inventory foundations.

**Depends on**
- Milestone 1
- Worker and queue foundations from Milestone 0

**Constitution alignment**
- 2.5 Explainable AI, Never Opaque Automation
- 2.6 Food Waste Reduction
- 4.1 Spec-First Delivery

---

### Milestone 3 — Grocery calculation and review before the trip **[MVP]** ✅ COMPLETE
**Outcome:** The household can turn the approved weekly plan plus inventory into a trustworthy grocery list and review it before shopping.

**Status:** ✅ Completed on 2026-03-09. All 11 GROC task acceptance criteria verified and approved by Kirk. Grocery derivation engine, deterministic offset rules, review/confirmation UX, confirmed-list handoff seams, observability instrumentation, and full test coverage (171 API + 33 web + 9 worker tests) now available.

**Scope**
- Grocery derivation rules from meal plan plus current inventory.
- Grocery list versions, item adjustments, quantity/unit handling, and review/confirmation flow.
- Distinction between derived suggestions and user-confirmed list state.
- Read models optimized for both desktop review and later mobile trip use.
- Test coverage for grocery correctness, duplicate avoidance, and list confirmation behavior.

**Why it comes here**
- Offline/mobile trip execution should operate on a confirmed grocery list, not an unstable planning draft.
- This milestone creates the authoritative list state that later sync and trip flows depend on.

**Depends on**
- Milestone 1
- Milestone 2

**Constitution alignment**
- 2.1 Mobile Shopping First
- 2.4 Trustworthy Planning and Inventory
- 2.6 Food Waste Reduction

---

### Milestone 4 — Mobile trip mode, offline queueing, and conflict-safe sync **[MVP]** 🚀 PLANNING ACTIVE
**Outcome:** A shopper can execute the trip on a phone, remain productive under poor connectivity, and recover safely when sync conflicts occur.

**Status:** 🚀 Now active for specification and planning (2026-03-09). Milestone 3 complete (confirmed-list handoff seam verified). Specification work should begin on mobile trip UI, offline store schema, mutation intent model, and sync/conflict detection logic before implementation begins.

**Scope**
- Mobile-first trip mode with large touch targets, low-typing interactions, and phone-sized layout validation.
- Offline-capable access to current shopping list, current meal plan context, and latest inventory snapshot.
- Offline check-off, quantity edits, and ad hoc item creation using explicit IndexedDB-backed mutation intents.
- Sync engine for replay, retry, status visibility, deduplication, and user-visible conflict handling.
- Conflict UX for stale quantities, concurrent list edits, and retry/recovery choices.

**Why it comes here**
- The constitution requires offline-capable essential shopping workflows in MVP, but the sync model depends on stable grocery, inventory, and API command boundaries.
- This is the highest-risk UX/reliability milestone, so it should follow earlier authoritative data modeling but precede release hardening.

**Depends on**
- Milestone 1
- Milestone 3
- Sync/conflict contract support from Milestone 0

**Constitution alignment**
- 2.1 Mobile Shopping First
- 2.2 Offline Is Required
- 2.3 Shared Household Coordination
- 2.7 UX Quality and Reliability

---

### Milestone 5 — Post-shopping and post-cooking reconciliation **[MVP]**
**Outcome:** Shopping outcomes and cooking events become clear, auditable inventory updates that preserve trust and support leftovers.

**Scope**
- Post-shopping review/apply flow that converts purchased or skipped outcomes into inventory updates with user-visible control.
- Cooking event flow to record consumption, substitutions, and leftovers creation.
- Reconciliation records, audit history, corrections, and reversal/correction affordances.
- Worker-assisted projection refresh where useful after committed state changes.
- E2E coverage that proves inventory remains understandable after shopping and cooking.

**Why it comes here**
- This closes the MVP loop and is required for the week-to-week trust model in the PRD.
- It should land after trip execution because reconciliation depends on confirmed trip outcomes and authoritative item identities.

**Depends on**
- Milestone 1
- Milestone 3
- Milestone 4

**Constitution alignment**
- 2.4 Trustworthy Planning and Inventory
- 2.6 Food Waste Reduction
- 5.1 Test Expectations

---

### Milestone 6 — MVP hardening, preview evidence, and launch readiness **[MVP]**
**Outcome:** The MVP is reliable enough for repeat household use and has the verification evidence required for merge/deploy.

**Scope**
- Complete critical-path automated coverage across unit, integration, component/flow, contract, and E2E layers.
- Finalize preview environment automation and cleanup discipline for the full stack.
- Add observability for sync failures, worker retries, conflict outcomes, and reconciliation issues.
- Validate release gates: lint/type/build/test commands, preview verification, and rollback/migration guidance.
- Run end-to-end MVP acceptance against planning, trip, offline restore, and reconciliation journeys.

**Why it closes MVP**
- The constitution makes release quality, observability, and E2E evidence part of the definition of done for non-trivial work.
- This milestone converts feature-complete slices into a releasable product.

**Depends on**
- Milestones 0 through 5

**Constitution alignment**
- 5.1 Test Expectations
- 5.2 Release Gates
- 5.3 Reliability and Observability
- 5.4 Change Safety

## 5. MVP Dependency View

| Milestone | Status | Depends on | Unlocks |
| --- | --- | --- | --- |
| 0. Foundation and delivery spine | ✅ complete | shared-infra prerequisites | all implementation work |
| 1. Household + inventory foundation | ✅ complete | 0 | planning, grocery, trip, reconciliation |
| 2. Weekly planner + AI suggestions | ✅ complete | 1, 0 worker setup | grocery derivation |
| 3. Grocery calculation + review | ✅ complete | 1, 2 | trip mode and reconciliation |
| 4. Mobile trip + offline sync | 🚀 planning active | 1, 3, 0 sync scaffolding | trustworthy in-store usage |
| 5. Shopping/cooking reconciliation | ⏳ planned | 1, 3, 4 | closed-loop inventory trust |
| 6. MVP hardening and launch readiness | ⏳ planned | 0-5 | releasable MVP |

## 6. Cross-Cutting Workstreams That Should Run Alongside MVP
- **Feature-spec track:** each non-trivial milestone should produce or refine feature specs before implementation, especially for inventory mutation rules, planner/AI behavior, grocery derivation, sync/conflict handling, and reconciliation UX.
- **Shared-infra coordination:** meal-planner delivery depends on shared-infra changes for OIDC, workload identity, External Secrets support, gateway/DNS/TLS posture, and reusable Terraform/workflow modules.
- **Quality track:** test harnesses and seed data should grow with each milestone instead of waiting until the end.
- **Operational visibility:** correlation IDs, retry diagnostics, provider-failure/rate-limit telemetry, and conflict telemetry should be added incrementally while features are implemented.
- **AI evaluation track:** prompt/context fixtures, explainability contract checks, fallback scenarios, and acceptance/rejection reporting should be defined early enough that AI behavior can be verified during Milestone 2 rather than deferred to launch hardening.
- **AI ops track:** preview/prod AI quotas, cost ceilings, prompt version tagging, and stale-result diagnostics should be treated as release-enabling concerns, not post-MVP instrumentation.

## 7. Phase 2 and Follow-On Ideas
These items are intentionally **not** part of MVP and should stay separate unless Ashley approves a scope change.

### Phase 2 candidate themes
1. **Richer household collaboration**
   - expanded household roles and permissions,
   - stronger simultaneous multi-person coordination flows,
   - richer notifications or presence-style collaboration aids.

2. **Store-aware shopping enhancements**
   - store-specific product mapping,
   - preferred-shop workflows,
   - retailer-aware list shaping or future pricing support.

3. **More advanced AI planning**
   - better substitution intelligence tied to recipe and pantry depth,
   - adaptive planning based on household behavior and explicit feedback patterns,
   - richer recipe adaptation and serving-size adjustment,
   - grocery/trip optimization once store-aware data exists,
   - deeper AI evaluation and ranking beyond MVP explanation contracts.

4. **Deeper recipe and nutrition systems**
   - stronger recipe/template modeling,
   - more advanced nutrition support,
   - richer meal content and reuse flows.

5. **Platform maturity beyond MVP**
   - stronger live-update patterns,
   - broader analytics and support tooling,
   - performance/accessibility targets beyond baseline MVP gates.

## 8. Recommended Next Planning Artifacts
- Technical architecture: MVP AI provider/runtime/prompt/result contract spec
- Feature spec: inventory model, mutation rules, audit/reversal behavior
- Feature spec: weekly planner and AI suggestion review/override flow
- Feature spec: AI grounding inputs, provider-neutral result contract, fallback behavior, and evaluation fixtures
- Feature spec: grocery derivation, list confirmation, and quantity/unit handling
- Feature spec: trip mode offline behavior, sync states, and conflict UX
- Feature spec: post-shopping and post-cooking reconciliation
- Delivery plan: Milestone 0 implementation order and shared-infra dependency tracking

## 9. Review Summary for Ashley
- This roadmap keeps MVP tightly focused on the approved core loop: trustworthy inventory -> weekly planning -> grocery review -> mobile/offline trip -> reconciliation.
- Mobile, offline, shared-state safety, and explainable AI are included inside MVP milestones rather than treated as later polish.
- Phase 2 remains clearly separated so store-aware workflows, richer collaboration, and deeper AI do not dilute the first releasable product.
