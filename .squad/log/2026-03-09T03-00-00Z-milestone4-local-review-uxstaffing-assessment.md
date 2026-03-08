# Session: Milestone 4 Local App Review & UI/UX Staffing Assessment

**Date:** 2026-03-09T03-00-00Z  
**Attendee:** Ashley Hollis  
**Context:** Milestone 3 is complete and approved. Milestone 4 (offline sync, trip mode, conflict review) planning is now active. SYNC-01 (Sulu) is ready_now. Before full Milestone 4 execution, the local app UI/UX posture and team staffing gaps must be assessed.

## Purpose

1. Start local Aspire app and visually inspect Milestones 1–3 feature delivery.
2. Identify UX gaps, quality concerns, accessibility issues, or mobile-readiness gaps.
3. Assess team UI/UX expertise (Kirk, Scotty, Uhura, Sulu, McCoy) and any skills needed for Milestone 4 mobile trip mode and conflict-resolution UX.
4. Determine UI/UX staffing strategy: in-house capability vs. specialist hiring/consulting.

## New Governance: Mandatory Visual Smoke Testing

As of 2026-03-09, **each milestone completion must include one manual local Aspire app review before the milestone is closed.**

- **When:** Once at the milestone end, inside the last user-journey verification gate (for example GROC-10 or SYNC-10), after the milestone's automated verification is green and before final acceptance.
- **How:** Run the local app, visually validate the milestone journeys against the spec on desktop and phone-sized viewports, and identify UX gaps or concerns.
- **Recording:** Smoke test findings are captured in the milestone progress/acceptance logs so the final approver can consume the same evidence, not rerun the smoke test by default.
- **Owner Responsibility:** The owner of the milestone's final user-journey verification gate performs the review; the final milestone approver checks that evidence before closure.

**Rationale:**
- Constitution 2.1 (Mobile Shopping First) and 2.3 (Shared Household Coordination) require high-quality user-facing UX.
- Milestone 4 conflict resolution is explicitly in-trip, mobile-first, and cannot be validated by code review or automated tests alone.
- Team staffing clarity (whether current team has UX depth or specialist is needed) is now visible only through hands-on local inspection.

## Session Plan

### Phase 1: Local App Start & Feature Walkthrough (5–10 min)
1. Run Aspire orchestration (`dotnet run` or `dapr run` equivalent).
2. Verify all services start cleanly: web, API, SQL, Azurite, worker (if applicable).
3. Access web app on localhost and confirm load time, initial UI state, mobile-responsive design.

### Phase 2: Milestone 1 Inspection (5 min)
- Inventory creation, editing, and deletion.
- Freshness/basis handling (known, estimated, unknown).
- Mobile form usability: touch targets, label clarity, error feedback.
- Accessibility: tab order, screen reader hints (if implemented).

### Phase 3: Milestone 2 Inspection (5 min)
- Weekly meal plan view and planner slots.
- AI suggestion display, explainability payload rendering.
- Pinned/excluded meal state and re-shuffle interaction.
- Mobile responsiveness: multi-week calendar on phone-sized screen.

### Phase 4: Milestone 3 Inspection (5 min)
- Grocery derivation and review flow.
- Quantity override editing and confirmation.
- Removed-lines tracking and inline detail expansion.
- Desktop vs. mobile layout quality, touch targets.

### Phase 5: Gap & Capability Assessment (5 min)
- Issues found: note any UI gaps, accessibility concerns, mobile friction, unexpected behavior.
- Team capability: Do Kirk, Scotty, Uhura have the UX judgment to design and implement Milestone 4 conflict-review flow?
- Specialist need: Would a dedicated mobile UX or interaction designer speed up Milestone 4 conflict resolution and mobile trip mode?

## Decision Points

After walkthrough:
1. **UX Gaps:** Are there showstoppers or rework needs in Milestones 1–3 before Milestone 4 starts?
2. **Staffing:** Can current team (Kirk lead + Scotty backend + Uhura web) handle Milestone 4 conflict UX, or is a specialist necessary?
3. **Milestone 4 Scope:** Should any UX work be pulled forward or deferred based on team capacity?

## Expected Outcome

- Smoke test findings (gap list) recorded in this session log.
- UI/UX staffing decision documented in squad decisions.
- Any Milestone 4 scope adjustments made and communicated to Sulu (SYNC-01 owner) and team.
- Session plan (`plan.md`) updated to reflect current focus.

---

## Walkthrough & Findings

_(To be filled in during session.)_

### Phase 1: Local App Start
- [ ] Aspire start status
- [ ] Web service load time and initial state
- [ ] Mobile viewport check

### Phase 2: Milestone 1 (Inventory)
- [ ] Feature completeness
- [ ] UX quality issues (if any)
- [ ] Mobile usability assessment

### Phase 3: Milestone 2 (Planning & AI)
- [ ] Feature completeness
- [ ] UX quality issues (if any)
- [ ] Mobile layout quality

### Phase 4: Milestone 3 (Grocery)
- [ ] Feature completeness
- [ ] UX quality issues (if any)
- [ ] Mobile/desktop layout consistency

### Phase 5: Staffing & Gaps
- UX gaps identified:
- Team capability assessment:
- Specialist hiring recommendation:

---

## Decision & Closure

**Scribe update:** Record team staffing decision and any Milestone 4 scope adjustments in `.squad/decisions.md`. Update `.squad/identity/now.md` and session plan with findings.

**Deadline:** Smoke test complete by 2026-03-09T04-00-00Z. SYNC-01 (Sulu) execution can proceed once staffing clarity is reached.
