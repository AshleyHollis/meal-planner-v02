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

## Learnings — AIPLAN-07 Planner Wiring (2026-03-08)

- The planner page must use `activeHouseholdId` from the API-owned session bootstrap, not the legacy compatibility alias, when calling household-scoped planner routes.
- Planner request lifecycles are authoritative in the backend now: frontend suggestion and slot-regeneration flows should poll `GET /api/v1/households/{household_id}/plans/requests/{request_id}` instead of simulating local completion.
- Local-only planner drafts and manual slot mutations create misleading authority boundaries. Once Scotty's draft endpoints exist, the UI should persist slot edits/restores immediately or not offer the action.
- `apps/web/app/_lib/planner-api.test.ts` now covers the planner API seam, and `npm --prefix apps\web run test` includes planner contract mapping alongside session and inventory checks.

## Learnings — AIPLAN-08 Planner UX Completion (2026-03-08)

- The planner review flow needs all three states visible in context: confirmed plan, suggestion preview, and editable draft are separate user promises, and hiding the confirmed plan while a replacement draft is open makes the replacement boundary too easy to miss.
- Confirmed-plan presentation should suppress AI provenance details entirely. Keep badges, fallback notes, reason codes, and explanation copy in suggestion/draft review only so the confirmed plan still reads as the household's plan.
- Per-slot regeneration failures need slot-local recovery copy, not just a global error state. The safest UX is to keep the user's last saved slot choice or original AI suggestion visible and explain that AI could not find a better replacement from the current context.
- `apps/web/app/_lib/planner-ui.test.ts` now covers planner UX copy decisions, and `npm --prefix apps\web run test` remains the frontend regression command for planner contract plus UX helper coverage.

## Learnings — GROC-06 Grocery API Wiring (2026-03-08)

- Grocery web calls should use `activeHouseholdId` from the API-owned session bootstrap, not the legacy compatibility alias, so the grocery page follows the same backend-owned household-context rule as planner and inventory.
- The backend grocery contract is authoritative on lifecycle and mutability: real statuses are `draft`, `stale_draft`, `confirmed`, and trip states, while ad hoc add/confirm/re-derive are valid only where the router allows them. The old purchased-line checkbox was a false promise because Milestone 3 exposes grocery review, not trip execution.
- `apps/web/app/_lib/grocery-api.test.ts` now guards grocery read-model mapping plus derive/re-derive/confirm/ad-hoc commands, and `npm --prefix apps\web run test` covers grocery alongside the existing session, inventory, and planner seams.

## Learnings — GROC-07 Grocery Review UX (2026-03-08)

- Grocery review works best as one page with inline line disclosure: keep the list scannable first, then let each line expand to show meal traceability, inventory offsets, and derived-vs-override quantity math where the decision is happening.
- Draft review must distinguish active lines from removed lines. Hiding removed lines entirely makes refresh behavior feel untrustworthy, while a separate removed section preserves user intent without cluttering the shopping list.
- Quantity overrides need two layers of visibility: show the effective shopping quantity in the main row, then keep the original derived quantity and review note in the expanded detail so the user can see both the current choice and why it changed.
- Confirmation should not be a silent button press. A modal summary that restates warning counts, override counts, and list-locking consequences gives the grocery flow a clear authority boundary before the list becomes the stable shopping version.
- `apps/web/tests/e2e/grocery-acceptance.spec.ts` now verifies the grocery review journey with mocked API responses on desktop and phone-sized viewports, while `npm --prefix apps\\web run test` covers the new grocery review helper and mutation seam logic.
