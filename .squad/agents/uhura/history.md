# Uhura History

## Project Context
- **User:** Ashley Hollis
- **Project:** AI-Assisted Household Meal Planner
- **Stack:** REST API, modern web UI, AI assistance, inventory/product mapping workflows
- **Description:** Build a connected household meal planning platform spanning inventory, meal plans, substitutions, store mapping, shopping trips, and inventory updates after shopping or cooking.
- **Team casting:** Star Trek TOS first.

## Learnings
- Team initialized on 2026-03-07 for Ashley Hollis.
- Current focus is spec-first setup for the AI-assisted household meal planning platform.

## Learnings — Wave 1 Frontend (2026-03-07)

- Completed the Wave 1 frontend implementation: app shell, session bootstrap seam, and feature surfaces for inventory, planner, and grocery.
- The Next.js app shell uses a client-side SessionProvider that calls GET /api/v1/me on mount; no Auth0 SDK is installed.
- All three feature routes (/inventory, /planner, /grocery) build successfully and pass TypeScript and ESLint checks.
- Used CSS Modules for all component styles (no Tailwind added); co-located .module.css files with each component.
- Client mutation IDs use crypto.randomUUID() with a plain-JS fallback; idempotency keys flow through all inventory mutations.
- AI suggestion states (generating, eady, allback_used, insufficient_context, ailed) are rendered in AISuggestionBanner per the spec.
- Stale draft warning is rendered but non-blocking per the spec: user can still confirm over it.
- Grocery list supports optimistic check-off and ad hoc item addition alongside derived lines.
- Wrote team-facing decisions to .squad/decisions/inbox/uhura-wave1-frontend.md covering session contract, CSS approach, API base URL env var, and open questions for Scotty.
- IndexedDB offline sync layer is intentionally deferred to a dedicated offline wave; the API seam is in place to support it.

## Team Updates (2026-03-07)

**Scribe consolidation:**
- Five frontend decisions merged into `.squad/decisions.md` from inbox.
- Orchestration log created at `.squad/orchestration-log/2026-03-07T21-34-42Z-uhura.md`.
- Session log summarizing Wave 1 frontend + backend review outcomes written to `.squad/log/2026-03-07T21-34-42Z-frontend-wave1-review.md`.
- Three open questions pending team input: session expiry UX, IndexedDB offline timeline, Aspire NEXT_PUBLIC_API_BASE_URL injection.
- Backend review (McCoy) identified 3 blocking gaps in Scotty's inventory implementation; next revision assigned to Bones or Kirk.

## Learnings — INF-05 Web Session (2026-03-08)

- Updated the frontend session bootstrap to consume the backend-owned `/api/v1/me` contract with `active_household_id` and household memberships, while preserving compatibility aliases for existing planner and grocery callers.
- Added explicit session UX states for retrying, unauthenticated, unauthorized, and transport failure so inventory bootstrap problems are visible and recoverable instead of collapsing into a generic empty view.
- Inventory list and existing-item mutations now rely on backend-resolved household scope by default; only create still sends the active household ID because the current backend command schema requires it.
- Relevant existing web validation for this slice is currently lint, typecheck, and production build; there are no pre-existing `apps/web` automated test scripts yet.

## Learnings — INF-09 Trust Review UX (2026-03-08)

- The new inventory trust surface works best as a selected-item review panel: keep the location-filtered list simple, then load Scotty's detail/history read models only for the item the user is inspecting.
- Freshness trust language needs to stay explicit everywhere. Rendering "Known freshness", "Estimated freshness", and "Unknown freshness" in both current state and history avoids treating estimated dates as fact.
- Metadata edits that reduce freshness precision need an explicit confirmation step, while correction flows should force the user to pick a prior event and record a balancing delta plus note so the UI never implies history deletion.
- `mutateInventory()` must choose the correct HTTP verb per mutation type; `set_metadata` is PATCH while the other inventory mutations remain POST.
- `npm --prefix apps\web run test` is now a real frontend check for this slice, covering session bootstrap, inventory API mapping, and freshness/trust formatting helpers.
