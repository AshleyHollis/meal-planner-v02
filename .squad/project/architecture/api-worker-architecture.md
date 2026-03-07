# API and Worker Architecture

Last Updated: 2026-03-07
Status: Draft for review

## 1. Service Roles
### FastAPI service
The API is the single authority for validating commands and persisting household state. It should expose explicit REST endpoints for:
- household and membership context,
- inventory,
- meal planning,
- grocery list generation/review,
- trip execution,
- reconciliation after shopping and cooking,
- AI suggestion request/review,
- sync/conflict handling.

### Python workers
Workers handle asynchronous or retryable workloads that should not block user-facing request latency:
- AI meal-plan suggestion generation,
- heavier grocery recalculation and projection work,
- derived read-model refresh tasks,
- retry workflows and dead-letter inspection tooling,
- operational cleanup or backfill tasks.

## 2. API Design Direction
- **Style:** REST over JSON.
- **Versioning:** URL versioning from day one, e.g. `/api/v1/...`.
- **Validation:** FastAPI request/response models define contract boundaries.
- **Idempotency:** command endpoints that may be retried from offline flows must accept idempotency keys or client mutation IDs.

## 3. Auth and Authorization
- **Identity provider:** Auth0.
- **Auth0 integration ownership:** Auth0 is integrated exclusively in the backend API. The Next.js frontend on Azure Static Web Apps must not install or embed the Auth0 SDK or runtime — the Auth0 Next.js package breaks SWA startup. All Auth0 interaction (OIDC login initiation, callback handling, token validation) is owned by the API.
- **Frontend authentication path:** the frontend authenticates by calling API endpoints such as `GET /api/v1/me`. Login redirects and session bootstrap are orchestrated by the API. The frontend consumes session state returned by the API rather than managing Auth0 tokens directly.
- **API auth:** bearer JWT validation against Auth0 is performed by the API on every authenticated request.
- **Authorization model:** application authorization is household-aware and not delegated entirely to Auth0.

### Application authorization responsibilities
- map authenticated user identity to one or more household memberships,
- enforce household-scoped access to plans, lists, inventory, and activity history,
- preserve room for later role expansion beyond MVP.

For MVP, a practical role model is:
- household owner,
- household member,
- optional read-only/admin distinctions deferred unless needed.

## 4. Runtime Identity and Secret Access
- **Infrastructure auth:** deployment workflows and AKS workloads should use Azure federated identity/workload identity patterns rather than stored cloud credentials.
- **Secret source:** API and worker secrets originate in Azure Key Vault in every environment, including local development.
- **Cluster delivery:** preview and production secret delivery should use shared platform capabilities such as workload identity and External Secrets or equivalent Key Vault-backed mechanisms.
- **Local development:** local API and worker processes should prefer Azure-authenticated Key Vault access directly; if a bootstrap cache is needed, it must be disposable and regenerated from Key Vault.

## 5. API Domain Modules
- **Identity/household module**
- **Inventory module**
- **Meal-planning module**
- **Grocery/trip module**
- **Reconciliation module**
- **Sync/conflict module**
- **AI planning module**

These should remain modular in code even if initially deployed as one API application.

## 6. Request Path vs Background Path

| Work type | Where it runs | Reason |
| --- | --- | --- |
| CRUD reads and small writes | API | Immediate user response |
| Inventory adjustments with validation | API | Authoritative and user-visible |
| Meal-plan approval and list confirmation | API | Core business transaction |
| AI suggestion generation | Worker via queue | Slower, retryable, external-dependency prone |
| Rebuild projections/read models | Worker via queue | Can be retried without blocking UI |
| Notifications/follow-up automation | Worker via queue | Non-blocking side effects |

### 6.1 AI planning generation flow
#### Request and grounding boundary
- The API should accept an AI suggestion request as a **job request**, not as a synchronous full generation call.
- The authoritative API request records:
  - household and actor,
  - plan period or slots to fill,
  - request status,
  - whether an existing request/result can be reused.
- Workers assemble the grounding context from deterministic sources at execution time so prompt construction stays tied to current server data rather than trusting raw client-provided context.

#### Grounding inputs for MVP
Workers should build AI context from:
- current inventory snapshot and expiry pressure,
- household dietary restrictions and preferences,
- equipment constraints,
- recent accepted or completed meals where available,
- pinned, excluded, or manually preserved meal slots,
- household size and any other product-owned planning constraints already available in the domain.

#### Result contract expectations
Persisted AI suggestion results should be structured enough for the client and later grocery derivation review. Each result should include:
- suggestion status (`queued`, `generating`, `completed`, `completed_with_fallback`, `failed`),
- meals proposed for each requested slot,
- short per-meal explanation fields tied to grounding data when possible,
- optional substitution or grocery-impact notes,
- data-completeness/fallback notes,
- provider-agnostic diagnostics such as generation timestamp and bounded execution metadata.

#### Lifecycle
1. Client requests suggestion generation.
2. API persists the request record and enqueues `meal_plan_generate_requested` after commit.
3. Worker hydrates current household context and constructs provider-neutral prompt/context input.
4. Worker calls the configured provider behind an abstraction boundary.
5. Worker validates and normalizes the result into the app-owned contract.
6. Worker persists the advisory result.
7. Client polls or refreshes the request endpoint to review, edit, accept, reject, or regenerate.

#### Failure and retry behavior
- Transient provider errors, network failures, and rate limits should be retried with bounded worker policies.
- Terminal failure should produce a visible failed request state, not an implicit silent disappearance.
- When feasible for MVP, provider failure or low-context generation may return a deterministic fallback suggestion set or a clear manual-planning prompt.
- Duplicate queue delivery must be safe; repeated processing of the same request should not create duplicate advisory records.

## 7. Queue Usage
- **Queue platform:** Azure Storage Queues in cloud, Azurite in local Aspire development.
- **Publishing rule:** the API publishes queue messages only after the authoritative transaction is committed.
- **Processing rule:** workers must be retry-safe and safe under duplicate delivery.
- **Failure rule:** terminal failures must land in a diagnosable state with correlation data.

### Recommended message types
- `meal_plan_generate_requested`
- `grocery_projection_refresh_requested`
- `inventory_projection_refresh_requested`
- `sync_reconciliation_followup_requested`
- `audit_compaction_requested`

These are logical event names, not a locked transport schema.

### 7.1 AI queue policy notes
- AI generation should use request IDs or equivalent idempotency markers so API retries and duplicate queue delivery are safe.
- Household-level throttling and worker concurrency controls should protect the provider boundary without changing user-facing contracts.
- Dead-letter handling should preserve enough context to diagnose prompt assembly, provider failure, or normalization issues without exposing secrets.

## 8. Consistency and Transaction Rules
- Core mutations should use SQL transactions at the API boundary.
- API writes should record audit/activity entries in the same transaction where practical.
- Queue handoff should follow a transactional-outbox-friendly pattern if simple direct enqueue is insufficient.
- Worker side effects must tolerate replay and duplicate messages.

## 9. Suggested Endpoint Families

| Area | Example endpoints |
| --- | --- |
| Auth/session bootstrap | `GET /api/v1/me`, `GET /api/v1/households/{id}` |
| Inventory | `GET /api/v1/households/{id}/inventory`, `POST /api/v1/households/{id}/inventory/adjustments` |
| Meal planning | `GET /api/v1/households/{id}/meal-plans/current`, `POST /api/v1/households/{id}/meal-plans/current/slots` |
| AI planning | `POST /api/v1/households/{id}/meal-plan-suggestions`, `GET /api/v1/households/{id}/meal-plan-suggestions/{requestId}` |
| Grocery/trip | `POST /api/v1/households/{id}/grocery-lists/current/generate`, `POST /api/v1/households/{id}/trips/current/mutations` |
| Reconciliation | `POST /api/v1/households/{id}/shopping-reconciliations`, `POST /api/v1/households/{id}/cooking-events` |
| Sync/conflicts | `POST /api/v1/households/{id}/sync/mutations:batch`, `GET /api/v1/households/{id}/sync/conflicts` |

Endpoint names are directional defaults for planning, not final contract approval.

### 9.1 AI endpoint expectations
- `POST /meal-plan-suggestions` should create or reuse a generation request and return an accepted/queued response with a request identifier.
- `GET /meal-plan-suggestions/{requestId}` should expose request status, freshness, fallback state, and structured suggestion results when ready.
- Accepting AI output into the authoritative meal plan should happen through normal meal-plan commands, not through a magical AI-specific auto-apply endpoint.

## 10. Observability Responsibilities
- Attach correlation IDs across frontend request, API transaction, queue publish, and worker execution where possible.
- Emit structured logs for sync failures, worker retries, inventory corrections, and conflict outcomes.
- Expose health endpoints for API and worker readiness/liveness.

### 10.1 AI-specific observability
- Log request lifecycle transitions for AI suggestions: queued, started, completed, fallback-used, failed.
- Capture provider-neutral latency, retry count, timeout, and rate-limit occurrences for operational visibility.
- Preserve enough execution metadata to explain why a result is stale, sparse, or fallback-derived.

## 11. Known Unresolved Items
- Whether to separate worker process types by domain or start with a single multi-queue worker.
- Whether to implement an explicit outbox table in v1 or begin with simpler enqueue-after-commit behavior.
- Exact prompt asset storage/layout and prompt versioning approach.
- Exact rate-limiting numbers, abuse controls, and whether manual fallback suggestions should be generated server-side or from curated templates.
