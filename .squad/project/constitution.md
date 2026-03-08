# Meal Planner Constitution

Version: 1.0.0
Ratified: 2026-03-07
Last Updated: 2026-03-07

## 1. Project Identity

### 1.1 Name & Mission
- **Name**: AI-Assisted Household Meal Planner
- **Mission**: Help households plan meals, manage inventory, and shop with confidence across desktop and mobile without losing trust in their data.
- **Primary outcomes**:
  - Reduce food waste.
  - Keep inventory and shopping data accurate.
  - Make planning and shopping low-friction for shared households.
  - Keep AI suggestions helpful, explainable, and easy to override.

### 1.2 Product Context
This project serves everyday household planning, shopping, and inventory workflows. Mobile use during shopping is a first-class scenario, offline support is required, and reliability matters as much as feature breadth.

## 2. Non-Negotiable Product Principles

### 2.1 Mobile Shopping First
- The product MUST work well on both desktop and mobile, with mobile shopping flows treated as first-class rather than responsive afterthoughts.
- Any feature that affects shopping mode MUST be designed for one-handed use, large touch targets, readable information density, and minimal typing.
- No core shopping workflow may require a desktop-only interaction.

### 2.2 Offline Is Required
- The system MUST support offline or intermittent-connectivity use for essential household workflows.
- At minimum, the offline-capable experience MUST cover:
  - Viewing the current shopping list.
  - Checking off purchased items.
  - Adding or editing list items and quantities.
  - Viewing the current meal plan needed for the trip.
  - Viewing the latest available household inventory snapshot.
- Features that mutate data offline MUST define how changes are queued, retried, reconciled, and surfaced to the user.

### 2.3 Shared Household Coordination
- Shared visibility and low-friction coordination for multi-person households are core product requirements, not stretch goals.
- Changes to shopping, meal-plan, and inventory data MUST be conflict-safe.
- Silent destructive overwrites are prohibited for shared state. Feature specs MUST define conflict detection, reconciliation behavior, and user-visible recovery when concurrent edits occur.
- Shopping mode MUST assume more than one person may act on the same list around the same time.

### 2.4 Trustworthy Planning and Inventory
- Inventory, pantry, fridge, freezer, leftovers, and shopping data MUST be treated as user-trust data.
- Mutations that affect stock levels, shopping completion, or meal consumption MUST be auditable, idempotent where possible, and reversible when mistakes happen.
- The system SHOULD prefer preserving data integrity over clever automation.
- Features MUST explicitly explain how they avoid stale quantities, duplicate list entries, or accidental stock loss.

### 2.5 Explainable AI, Never Opaque Automation
- AI suggestions MUST explain the main reasons they were produced, especially when using inventory state, expiry pressure, preferences, or household context.
- Users MUST be able to reject, override, or edit AI-driven outputs without fighting the system.
- AI MUST NOT silently mutate authoritative shopping or inventory records without an explicit user action.
- When confidence is low or data is incomplete, the product MUST say so plainly.

### 2.6 Food Waste Reduction
- Features SHOULD help households use what they already have before recommending new purchases.
- Expiry risk, leftovers, and existing stock SHOULD be visible in planning decisions when relevant.
- If a feature introduces automation or ranking, minimizing waste MUST be one of the documented optimization goals.

### 2.7 UX Quality and Reliability
- Strong UX is a product requirement. New work MUST improve or preserve clarity, speed, and confidence.
- The system MUST degrade gracefully under slow networks, partial outages, cold starts, and sync delays.
- Empty states, loading states, retry states, and conflict states are part of the feature, not polish work to defer indefinitely.

## 3. Engineering Defaults

### 3.1 Approved Default Stack
- **Frontend**: Next.js web app, TypeScript by default.
- **Backend API**: Python 3.13 FastAPI service.
- **Background processing**: Python workers using queues.
- **Local development**: Aspire-first orchestration.
- **Cloud environments**: Azure preview and production environments.
- **Delivery**: GitHub CI/CD pipelines.
- **Verification strategy**: E2E-first verification before deployment.

### 3.2 Expected Architectural Direction
- Build a thin, user-focused web frontend over explicit API contracts rather than hiding business logic in the client.
- Keep API, worker, and UI responsibilities separate so offline sync, retries, and background work remain understandable and testable.
- Prefer event- or queue-driven processing for long-running or retryable work instead of blocking request/response paths.
- Treat offline synchronization, shared-state reconciliation, and authoritative inventory updates as first-class architecture concerns in every affected design.

### 3.3 Unknowns Requiring Explicit Design Choice
The following areas are intentionally not invented here and MUST be decided in architecture/spec artifacts before implementation that depends on them:
- Primary database technology and data model boundaries.
- Authentication and household identity model.
- Offline storage/sync implementation details in the client.
- Queue technology selection for local and Azure environments.

## 4. Squad Rules of Engagement

### 4.1 Spec-First Delivery
- Non-trivial work MUST begin with spec artifacts before implementation.
- Every feature spec MUST state:
  - User outcome.
  - Acceptance criteria.
  - Mobile behavior.
  - Offline behavior.
  - Shared-household coordination behavior.
  - Data integrity implications.
  - AI explainability/override behavior when AI is involved.

### 4.2 Constitution Alignment
- Plans and task breakdowns MUST reference the relevant constitution principles they satisfy.
- If a proposal trades off reliability, offline support, mobile UX, or data integrity, that trade-off MUST be made explicit and approved before implementation.
- “We will fix mobile/offline/shared behavior later” is not an acceptable default for core flows.

### 4.3 Reference Repo Alignment
- Reuse patterns and tooling from `yt-summarizer` and `meal-planner-005-grocery-enhancements` where they accelerate delivery without violating this constitution.
- Consistency with the approved stack and proven team practices is preferred over novelty.
- Differences from the reference repos MUST be justified in the relevant architecture or feature plan.

## 5. Quality Gates

### 5.1 Test Expectations
- No non-trivial feature is complete without automated tests.
- Backend work MUST include unit tests for business logic and integration tests for data/API boundaries.
- Frontend work MUST include component or flow coverage for critical state transitions.
- E2E coverage MUST validate critical user journeys before deployment, with special attention to:
  - Mobile shopping flow.
  - Offline/restore connectivity behavior.
  - Shared-household update visibility.
  - Inventory and shopping-list accuracy after user actions.

### 5.2 Release Gates
- Before merge or deploy, changes MUST pass the repository’s lint, type-check, test, and build steps that exist at that time.
- Preview or pre-production verification MUST include E2E evidence for impacted user journeys.
- Any change that affects shopping, inventory, meal-plan state, or sync logic MUST be verified against concurrent-update and retry scenarios appropriate to the change.

### 5.3 Reliability and Observability
- Services MUST emit actionable logs and errors suitable for diagnosing sync failures, worker retries, and household data conflicts.
- Correlation across frontend, API, and worker activity SHOULD be preserved where feasible.
- Background jobs MUST be retry-safe and MUST surface terminal failure states clearly enough for diagnosis and recovery.

### 5.4 Change Safety
- Schema or contract changes MUST be versioned, reviewable, and accompanied by migration or rollout guidance when applicable.
- Data-destructive changes require explicit justification and a recovery path.
- New dependencies, infrastructure choices, or architectural complexity require written rationale tied to product value.

## 6. Working Standards

### 6.1 UX and Interaction Standards
- The default assumption is that users need to understand what changed, why it changed, and what to do next.
- Prefer explicit state, clear labels, and reversible actions over hidden automation.
- If a flow matters in-store, it MUST be testable and readable on a phone-sized viewport.

### 6.2 Data Standards
- Inventory, meal-plan, and shopping state transitions MUST be deterministic and understandable.
- Duplicate or ambiguous representations of the same household state SHOULD be avoided.
- Any derived recommendation SHOULD preserve or reference the underlying authoritative records rather than replacing them opaquely.

### 6.3 Simplicity with Accountability
- Choose the simplest design that satisfies mobile, offline, reliability, and shared-household requirements.
- Premature abstraction is discouraged, but postponing known conflict, sync, or integrity requirements is also prohibited.

## 7. Governance

### 7.1 Amendment Process
- Amend this constitution through a dedicated change that explains the rationale, affected workflows, and any required downstream updates.
- Use semantic versioning:
  - **MAJOR**: Principle removal or incompatible governance change.
  - **MINOR**: New principle or materially expanded rule.
  - **PATCH**: Clarification without changing intent.

### 7.2 Compliance
- This constitution overrides conflicting local preferences and informal habits.
- Reviewers, planners, and implementers are all responsible for enforcing it.
- If work cannot comply yet, the gap MUST be documented explicitly as an open question, risk, or follow-up rather than ignored.

## 8. Open Questions
- Which database technology best supports authoritative household state, offline reconciliation, and Azure deployment for this project?
- What authentication/identity model will represent households, membership, and permissions?
- What client-side offline storage and sync approach will back required mobile shopping behavior?
- Which queue technology will be standard across local Aspire development and Azure deployment?

## Changelog

### 1.0.0 - 2026-03-07
- Initial project-specific constitution drafted for the meal planner repository.
- Captured approved stack, mobile-shopping priority, offline requirement, shared-household coordination rules, and E2E-first quality gates.
