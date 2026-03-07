# Testing and Quality Architecture

Last Updated: 2026-03-07
Status: Draft for review

## 1. Quality Goals
The quality strategy must prove the product is trustworthy in the places users will notice most:
- mobile shopping usability,
- offline and reconnect behavior,
- inventory correctness,
- shared-household safety,
- AI explainability without hidden mutation.

This follows the constitution rule that E2E coverage is required for critical user journeys before deployment.

## 2. Test Pyramid for This Project

| Layer | Purpose | Primary targets |
| --- | --- | --- |
| Unit tests | Fast feedback on domain logic | inventory rules, grocery calculations, sync reducers, conflict classifiers |
| Integration tests | Boundary correctness | API + SQL, worker + queue, auth mapping, migration behavior |
| Contract tests | Stable frontend/backend expectations | read models, mutation payloads, error shapes |
| Component/flow tests | Critical frontend state transitions | planner edits, trip actions, reconciliation screens, conflict states |
| E2E tests | User-critical proof | weekly plan flow, mobile trip flow, offline restore flow, shopping/cooking reconciliation |

## 3. Frontend Quality Expectations
- Component or flow tests should cover:
  - trip item check-off,
  - quantity edits,
  - local queue status rendering,
  - conflict and retry UI,
  - meal-plan suggestion review/edit/accept flow.
- Responsive validation should explicitly cover phone-sized layouts for trip mode.
- Offline-capable flows should be tested with network interruption scenarios, not only ideal online paths.

## 4. API and Worker Quality Expectations
- Unit tests for domain policies:
  - inventory mutation rules,
  - grocery derivation rules,
  - reconciliation logic,
  - idempotency handling,
  - conflict detection decisions.
- Integration tests for:
  - SQL persistence and concurrency handling,
  - API-side Auth0 JWT validation and household membership mapping (Auth0 integration is API-only; no Auth0 SDK in the Next.js frontend),
  - queue publish/consume flows,
  - retry behavior and duplicate delivery safety.

### 4.1 AI evaluation and test expectations
AI-related tests should prove contract quality and graceful degradation rather than subjective meal quality scoring alone.

#### Unit and contract expectations
- Grounding-context assembly should be testable from deterministic fixtures for inventory, preferences, constraints, and recent-meal inputs.
- Result normalization should verify required fields are present for each meal suggestion: slot, explanation, and any fallback or data-sparsity note required by the contract.
- Tests should verify the system never treats AI output as authoritative without an explicit meal-plan confirmation command.

#### Worker integration expectations
- Duplicate suggestion requests should be idempotent.
- Timeout, rate-limit, and provider-failure paths should produce the expected retry, fallback, or failed-visible lifecycle states.
- Sparse-data households should still return a valid, reviewable result or an explicit manual-planning message.

#### Fixture expectations
- Maintain deterministic household fixtures that cover:
  - rich inventory with expiry pressure,
  - empty or sparse inventory,
  - dietary restriction edge cases,
  - recent-meal repetition avoidance,
  - provider timeout/failure and fallback cases.
- Routine CI should use mocks/fakes or deterministic fallback providers, not live provider calls.

## 5. E2E Priority Journeys
The first required E2E suite should cover:
1. user signs in and opens current household context,
2. user creates or accepts an editable weekly plan,
3. system produces a grocery list from plan plus current inventory,
4. user shops on a phone-sized viewport,
5. user performs trip edits while offline,
6. connectivity returns and queued changes reconcile,
7. user applies shopping results to inventory,
8. user records cooking and leftovers,
9. updated inventory is visible and trustworthy afterward.

## 6. Test Data Strategy
- Use seedable household scenarios with realistic pantry/fridge/freezer/leftovers data.
- Include fixtures for:
  - expiring items,
  - missing ingredients,
  - substitutions,
  - concurrent shopper edits,
  - retry/duplicate mutation uploads.
- AI-related tests should prefer deterministic mocks over live provider dependency for routine CI.
- AI fixtures should include expected explanation snippets or structured reason codes so explainability regressions are detectable.

## 7. Release Gates
Before merge or deploy, the repository should eventually require:
- lint pass,
- type-check pass,
- backend unit/integration pass,
- frontend component/flow pass,
- critical E2E pass for impacted flows,
- build pass for deployable artifacts.

The current repository does not yet contain implementation-specific lint/test/build commands, so these gates are architectural targets rather than active automation.

## 8. Non-Functional Verification
- **Performance:** mobile trip screens should remain responsive under large lists.
- **Resilience:** retry and reconnect behavior should be tested intentionally.
- **Accessibility:** mobile controls, labels, focus order, and status messaging should be verifiable.
- **Observability:** failures must produce enough logs and IDs to diagnose issues across web, API, and worker.
- **AI reliability:** queued generation should surface latency, fallback use, and failure states clearly enough that support and product teams can diagnose poor AI outcomes.

## 9. Quality Ownership
- Frontend changes must prove UI state transitions and mobile behavior.
- Backend changes must prove domain and persistence correctness.
- Cross-cutting changes affecting sync, shopping, inventory, or meal planning must include E2E evidence.
- Architecture and feature specs must call out any required new automated coverage before implementation starts.

## 10. Known Unresolved Items
- Exact testing frameworks for Next.js, FastAPI, and E2E automation are not yet locked.
- Exact contract-testing approach between frontend and API is still open.
- Exact performance budgets and accessibility gates still need product-level thresholds.
