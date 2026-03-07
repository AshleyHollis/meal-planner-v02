# Frontend, Offline, and Sync Architecture

Last Updated: 2026-03-07
Status: Draft for review

## 1. Frontend Role
The Next.js web app is the only user-facing client for MVP. It must support:
- desktop planning workflows,
- mobile-first shopping workflows,
- offline-capable access to the active trip context,
- explicit and trustworthy sync feedback.

The frontend should remain thin on business policy while still owning offline durability, optimistic UX, and conflict presentation.

## 2. Application Shape
- **Framework:** Next.js with TypeScript.
- **Rendering approach:** hybrid SSR/CSR.
  - SSR/streamed rendering for authenticated shell, planner entry points, and initial read-heavy views.
  - Client-side state management for active planning, trip execution, and offline mutation flows.
- **PWA posture:** installable experience, service worker for asset caching, and durable local data for trip-critical state.

## 3. Feature Areas in the Client
- **Authenticated shell:** household selection, navigation, account/session state.
- **Inventory views:** pantry, fridge, freezer, leftovers, activity history, and correction flows.
- **Meal planner:** weekly plan grid, suggestion review, explanation panels, edits, and approval.
- **Grocery review:** generated list review, manual adjustments, and confirmation before trip.
- **Trip mode:** large touch targets, one-handed interactions, low typing, and offline-first list operations.
- **Reconciliation flows:** post-shopping apply-to-inventory review and post-cooking inventory adjustments.

## 4. Client State Layers

| State type | Owner | Notes |
| --- | --- | --- |
| UI state | React client state | Filters, expanded sections, temporary form input |
| Server read cache | Client data-fetching layer | Refreshable copies of API read models |
| Offline durable data | IndexedDB | Latest household snapshot needed for essential offline workflows |
| Pending offline mutations | IndexedDB sync queue | Ordered mutation intents awaiting upload/retry |
| Auth session | API-managed session (cookie or token returned by API auth endpoints) | The Next.js frontend must not install the Auth0 SDK; session state comes from the API. Token lifecycle is owned by the API, not the browser client. |

## 5. Offline Scope for MVP
The offline-capable client must support the constitutional minimum:
- view the current shopping list,
- check off purchased items,
- add or edit list items and quantities,
- view the current meal plan needed for the trip,
- view the latest available inventory snapshot.

For MVP, offline support is intentionally strongest around **trip mode**. Planning-heavy AI features may degrade to read-only or unavailable when offline.

### 5.1 AI suggestion behavior in the client
- AI suggestion generation is **online-only** for MVP; the client should not queue AI generation requests while offline.
- The latest completed AI suggestion for the active plan may be cached for read-only review, but the UI must mark it stale when plan or inventory context has materially changed.
- Users must always have a clear manual-planning path when AI is unavailable, still generating, rate-limited, or failed.
- AI review UI should show explicit states such as `generating`, `ready`, `fallback used`, `insufficient context`, and `failed`.

## 6. Offline Storage Model
- Use **IndexedDB** as the durable browser store.
- Maintain separate local stores for:
  - household snapshot metadata,
  - active meal-plan snapshot,
  - active grocery list snapshot,
  - inventory snapshot summary,
  - pending mutation queue,
  - sync status and last-success timestamps.
- Store queue items as explicit mutation intents, not raw table replicas.

### Queue Item Shape
Each queued mutation should include:
- client mutation ID,
- household ID,
- actor ID,
- mutation type,
- target aggregate or record reference,
- payload,
- device timestamp,
- base server version or sync token if known,
- retry count,
- local status (`pending`, `syncing`, `failed-retryable`, `conflict`, `applied`).

## 7. Sync Model
### 7.1 Direction
- **Download:** the client hydrates from API read models and refreshes snapshots when online.
- **Upload:** offline-created mutations are replayed to the API in original intent form.

### 7.2 Principles
- Sync is **intent-based**, not full-record overwrite.
- Mutations must be **idempotent** using client mutation IDs.
- The API is allowed to reject stale or conflicting mutations rather than guessing.
- The client must show clear per-item sync states during and after connectivity restoration.

### 7.3 Recommended Sync Flow
1. User performs a local action.
2. Client validates basic input and applies a local optimistic view.
3. Mutation intent is written durably to the local sync queue.
4. If online, the sync engine attempts immediate upload.
5. API accepts, rejects, or flags conflict.
6. Client updates local queue state and refreshes the relevant read model slice.

## 8. Conflict Handling UX
- **Safe auto-merge:** allowed for independent actions with no semantic collision, such as adding separate ad hoc items.
- **Explicit conflict review:** required when the same item quantity, shopping completion state, or inventory adjustment has changed incompatibly.
- **Never silently overwrite:** if the client cannot prove the merge is safe, show the user:
  - what changed locally,
  - what changed elsewhere,
  - the recovery choice.

For MVP, conflict UX should prioritize clarity over elegance:
- reload server version,
- keep local draft for review,
- retry after user confirmation where appropriate.

## 9. Mobile-First Constraints
- Trip mode should target phone-sized viewports first.
- Default actions must be thumb-friendly and low-friction.
- Quantity edits should minimize free typing where possible.
- Sync indicators must be visible but not dominant.
- Empty/loading/retry/conflict states are part of the flow, not secondary polish.

## 10. Frontend-to-API Contract Boundaries
- Client sends **commands/mutations** for authoritative changes.
- Client consumes **read models** optimized for screens:
  - weekly planner view,
  - grocery list/trip view,
  - inventory summary/detail,
  - activity history,
  - sync status/conflict detail.
- Client must not calculate final authoritative inventory transitions on its own.
- Client may render AI explanations and staleness/fallback messaging, but it must not infer hidden AI confidence or invent reasoning that did not come from the server contract.

## 11. Security and Privacy Notes
- Do not store secrets in offline storage.
- Do not install the Auth0 SDK or any Auth0 runtime package in the Next.js app. The Auth0 Next.js package breaks Azure Static Web Apps startup and must not be added as a frontend dependency.
- The frontend authenticates by calling backend API endpoints (e.g. `GET /api/v1/me`). Session tokens or cookies are returned and managed by the API; the frontend stores only what the API explicitly returns for session continuity, not raw Auth0 tokens.
- Keep session state outside business data stores; do not mix auth session information into IndexedDB app stores.
- Minimize offline caching of sensitive profile data beyond what is required for household workflows.
- Any server-side/frontend build secrets used by the app must originate from Azure Key Vault rather than checked-in local env files.
- Local development should prefer Azure-authenticated resolution of secrets from Key Vault; if a disposable bootstrap cache is needed, it must remain outside the repo and be refreshable from Key Vault.

## 12. Known Unresolved Items
- Exact client state/data libraries are not yet locked.
- Exact service-worker strategy for asset and API response caching still needs implementation design.
- Exact offline conflict UI for concurrent shoppers on the same list still needs a feature-level spec.
- Push-driven live updates versus polling/SWR refresh is still open for MVP.
