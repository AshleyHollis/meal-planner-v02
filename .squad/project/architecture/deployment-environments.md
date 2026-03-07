# Deployment and Environments

Last Updated: 2026-03-07
Status: Draft for review

## 1. Environment Strategy
The platform should support a consistent path across:
- **local development** via Aspire,
- **preview** as fully automated per-PR environments,
- **production** for live household usage.

The environment design should keep frontend, API, worker, SQL, queue, and identity wiring explicit.
It must also keep infrastructure ownership, Terraform boundaries, and secret-management rules explicit so there is no ambiguity between shared platform responsibilities and app responsibilities.

## 2. Local Development
### Local runtime defaults
- **Orchestration:** .NET Aspire AppHost
- **Frontend:** Next.js dev server or container
- **API:** FastAPI service
- **Worker:** Python queue worker
- **Database:** local SQL Server instance/container
- **Queue emulator:** Azurite for Azure Storage Queue compatibility
- **Secrets:** Azure Key Vault remains the source of truth, accessed through Azure-authenticated developer workflows

### Local goals
- one-command startup of full stack,
- realistic end-to-end sync and queue behavior,
- inspectable logs for frontend, API, and worker,
- local identity integration path compatible with Auth0 API configuration (Auth0 is backend-only; the local frontend dev server has no Auth0 SDK dependency),
- rebuildable local environments without hand-maintained secret files.

### Local secret strategy
- **Source of truth:** Azure Key Vault stores environment secrets for local development as well as preview and production.
- **Preferred access path:** developers authenticate with Azure (for example via `az login`) and local tooling resolves secrets from Key Vault at startup.
- **Preferred credential posture:** use Azure identity-based access where possible instead of inventing local copies of secrets.
- **Bootstrap fallback:** when a tool cannot read Key Vault directly, a bootstrap step may materialize a minimal, user-scoped local secret cache or user-secrets entry outside the repo, but that cache must be disposable and refreshable from Key Vault.
- **Non-goal:** checked-in `.env` secrets or manually curated per-developer secret files.

## 3. Cloud Topology

| Concern | Hosting choice | Notes |
| --- | --- | --- |
| Web client | Azure Static Web Apps | Edge-hosted frontend delivery |
| API | AKS | Containerized FastAPI deployment |
| Worker | AKS | Queue-consuming Python deployment |
| Database | Azure SQL Serverless | Authoritative cloud operational store |
| Queue | Azure Storage Queues | Background work backbone |
| Secrets | Azure Key Vault | Central secret authority consumed by workloads and local development |
| Identity | Auth0 | External identity provider |

## 4. Environment Differences

| Area | Local | Preview | Production |
| --- | --- | --- | --- |
| SQL | SQL Server local | Per-PR Azure SQL database | Azure SQL |
| Queue | Azurite | Azure Storage Queues | Azure Storage Queues |
| Secrets | Azure-authenticated Key Vault access or disposable bootstrap cache | Azure Key Vault | Azure Key Vault |
| Auth | Auth0 dev tenant or equivalent dev app | Auth0 preview app | Auth0 prod app |
| API/worker scale | single instance acceptable | low-scale but production-like | autoscaled by demand |
| Data | disposable developer data | isolated per-PR preview data | protected production data |

## 5. Infrastructure Ownership Split

| Responsibility | `shared-infra` repo (`C:\Users\ashle\Source\GitHub\AshleyHollis\shared-infra`) | This repo |
| --- | --- | --- |
| Shared Azure/Kubernetes platform | Terraform for shared Azure resources, AKS platform primitives, shared networking, cluster bootstrap, and cluster-level controllers/components | Consume the platform; do not recreate shared platform primitives here |
| OIDC/federated auth plumbing | GitHub OIDC setup, federated credentials, reusable workload identity patterns | Use those identities from app deployment workflows and runtime workloads |
| DNS and edge routing foundations | Gateway API controllers, shared gateway layer, ExternalDNS integration, and Cloudflare automation | Declare app-specific hostnames/routes through repo-owned app configuration |
| TLS foundations | cert-manager operations and shared wildcard certificate posture at the gateway layer | Consume the shared wildcard-TLS ingress path; do not model per-PR certificates here |
| Shared delivery building blocks | Shared GitHub Actions/workflows and reusable Terraform modules | App-specific deployment workflows that call shared actions and apply app-owned Terraform/manifests |
| Secrets platform enablement | Key Vault foundation, access models, External Secrets/workload identity plumbing | App-owned secret definitions/references and namespace-level secret consumption wiring |
| App deployment intent | Not the owner | App-specific Terraform, Kubernetes manifests/overlays, ArgoCD application definitions, release sequencing, and preview cleanup triggers |

## 6. Deployment Packaging
- Web client deploys independently from API/worker.
- API and worker should be built as container workloads for AKS.
- Keep API and worker versioned together unless later operational pressure justifies independent release trains.
- Database schema migration must be part of the release process, not an ad hoc manual step.
- Terraform plans/applies should happen in the repository that owns the relevant infrastructure change.
- ArgoCD application definitions and namespace-scoped Kubernetes overlays for this app belong in this repo, even when they target shared clusters.

## 7. Preview Environment Architecture
### Preview scope
- Every pull request should produce its own end-to-end preview environment automatically.
- The preview unit for this repository is:
  - one Azure Static Web Apps preview environment for the frontend,
  - one AKS namespace for API and worker workloads,
  - one ArgoCD application and overlay set pointing at that namespace,
  - one preview DNS hostname,
  - one meal-planner-specific Azure SQL database for that PR,
  - one Key Vault secret set or secret versioning entry that lets preview workloads resolve the per-PR database connection.

### Ownership and flow
1. GitHub Actions in this repo orchestrates the meal-planner preview deployment using shared OIDC-enabled workflow building blocks.
2. This repo provisions or updates app-owned preview resources and manifests: SWA preview wiring, app Terraform, ArgoCD app/overlay, namespace-scoped settings, and meal-planner-specific database/secret references.
3. `shared-infra` provides and operates the shared AKS entry path: Gateway API controllers, shared gateway, ExternalDNS, Cloudflare integration, cert-manager, and wildcard TLS posture.
4. Preview traffic resolves through shared DNS automation and terminates on the shared wildcard certificate at the gateway layer before routing to the app's preview namespace.

### Limits and cleanup
- Azure Static Web Apps has a hard limit of three concurrent preview environments, so preview lifecycle control is an architectural requirement rather than optional housekeeping.
- Closing a PR should trigger immediate teardown of that PR's SWA preview environment, AKS namespace, ArgoCD app/overlay, preview hostname, meal-planner Azure SQL database, and no-longer-needed Key Vault secret material.
- A scheduled sweep should also run to find and remove orphaned preview resources that survive due to workflow interruption or drift, following the same general cleanup pattern used in `yt-summarizer`.
- Preview naming and ownership metadata should stay consistent across SWA, namespace, ArgoCD, DNS, database, and secret resources so cleanup can act deterministically.

## 8. CI/CD Direction
GitHub Actions remains the delivery backbone.

Recommended stages:
1. lint, type-check, unit tests, integration tests,
2. build web and Python artifacts,
3. Terraform validation/plan for app-owned infrastructure,
4. contract and E2E validation for impacted flows,
5. deploy or update the PR-scoped preview environment,
6. gated production promotion after review.

The current repository workflows are placeholders and do not yet define product build/test commands.
Shared workflow primitives and Azure OIDC plumbing should be provided from `shared-infra`; this repo should compose them into meal-planner-specific delivery workflows.

## 9. Configuration and Secrets
Environment variables should be grouped by deployment unit:
- **web:** public API base URL, telemetry keys as appropriate. No Auth0 client settings — the Next.js frontend must not include the Auth0 SDK (it breaks SWA startup); auth is handled entirely by the API.
- **api:** SQL connection string, Auth0 domain/audience/secret, queue connection settings, AI provider configuration,
- **worker:** SQL connection string, queue connection settings, AI provider configuration,
- **shared:** correlation, logging, environment name, feature-flag sources.

- Azure Key Vault is the authoritative store for secrets in every environment, including local development.
- GitHub Actions should use federated identity/OIDC rather than stored cloud credentials.
- AKS workloads should prefer workload identity plus External Secrets or equivalent Key Vault-backed secret delivery instead of handwritten Kubernetes secrets.
- Public web configuration can remain non-secret configuration, but any server-side or build-time secret must still originate from Key Vault.
- Secrets should not be committed, manually duplicated between repos, or hand-edited separately per developer machine.
- For previews, meal-planner-specific Key Vault entries must support per-PR database isolation rather than sharing one preview database secret across all PRs.

## 10. Likely Shared-Infra Updates Required
- Add or verify GitHub federated credentials for this repository's preview and production deployment workflows.
- Ensure shared AKS clusters have workload identity and External Secrets integration available for app namespaces.
- Provide or version reusable Terraform modules for namespace provisioning, Key Vault access wiring, and common app-on-cluster resources.
- Provide reusable shared workflow/actions patterns for Terraform, container publishing, and deployment handoff.
- Keep ExternalDNS plus Cloudflare automation and the shared gateway wildcard-TLS posture available for preview and production hostnames.

## 11. Observability
- Centralize structured logs from API and worker.
- Preserve correlation identifiers from web request through backend work where feasible.
- Capture health, readiness, and queue-processing metrics.
- Treat offline sync failures and dead-letter conditions as first-class operational signals.

## 12. Reliability and Recovery Expectations
- Preview and production environments must support safe rollback of application versions.
- Database migrations require rollback or forward-fix guidance.
- Worker retries must be bounded and diagnosable.
- Client-visible outages should degrade to cached/offline behavior where possible for trip-critical flows.

## 13. Known Unresolved Items
- Exact network topology, ingress, and private connectivity requirements.
- Exact observability stack choice beyond the requirement for actionable logs and correlation.
