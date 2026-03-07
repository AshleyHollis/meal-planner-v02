# Orchestration Log: Spec Agent – Architecture Revision

**Timestamp:** 2026-03-07T08:57:01Z  
**Requested by:** Ashley Hollis  
**Topic:** Architecture revision and approval for the AI-assisted household meal planning platform

## Outcome
- ✅ Revised architecture to include modular full-stack design with Next.js frontend, FastAPI backend, and Python workers
- ✅ Established Terraform/shared-infra boundaries for infrastructure-as-code and shared platform ownership
- ✅ Locked Key Vault strategy for local development with Azure-authenticated access
- ✅ Designed fully automated per-PR preview environments with SWA, AKS namespace, DNS, and TLS awareness
- ✅ Captured all architecture decisions into `.squad/decisions/inbox/` for consolidation
- ✅ Ashley Hollis reviewed and approved the complete architecture direction

## Deliverables
1. **Core Architecture Decisions** (`.squad/decisions/inbox/spec-architecture.md`):
   - Modular full-stack: one Next.js client, one FastAPI API, Python workers
   - SQL-backed household data as authoritative; browser offline as working copy with sync queue
   - Auth0 for identity proofing; household membership in app domain
   - Azure Storage Queues in cloud, Azurite in local Aspire
   - SWA for web client, AKS for API/workers
   - Intent-based sync with idempotent mutation IDs
   - Synchronous API for user-visible mutations; workers for async/heavy work

2. **Infrastructure & Shared-Infra Decisions** (`.squad/decisions/inbox/spec-architecture-revision.md`):
   - Terraform is infrastructure-as-code standard
   - Shared-infra owns shared Azure, Kubernetes, identity, and workflow primitives
   - meal-planner-v02 owns app-specific Terraform, manifests, ArgoCD, and workflows
   - Key Vault is source of truth for secrets (local, preview, production)
   - Prefer Azure-authenticated access to Key Vault; minimal bootstrap cache
   - OIDC/federated identity and workload identity patterns for GitHub Actions and AKS runtime

3. **Preview Environment Architecture** (`.squad/decisions/inbox/spec-preview-architecture.md`):
   - Per-PR preview environments: fully automated end-to-end creation and updates
   - Preview isolation: dedicated SWA preview, AKS namespace, ArgoCD app, DNS hostname, SQL database, Key Vault secrets
   - Shared-infra owns shared preview platform (OIDC, gateway, ExternalDNS, Cloudflare DNS, cert-manager, wildcard TLS)
   - meal-planner-v02 owns app-specific preview workflows, Terraform, manifests, ArgoCD, naming conventions
   - Shared wildcard TLS at gateway layer (not per-PR certificate issuance)
   - PR close triggers immediate preview teardown; scheduled sweep removes orphaned resources
   - Resource naming aligns across SWA, namespace, ArgoCD, DNS, database, and Key Vault for deterministic cleanup

## Status
Complete and approved. Architecture ready for implementation planning and feature specialization.
