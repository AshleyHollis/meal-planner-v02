# UI/UX Staffing Decision for Meal Planner v02

**Date:** 2026-03-09  
**Lead:** Kirk  
**Status:** Executed decision  
**Issue:** Should we add a UI/UX specialist or expand existing team skill areas to meet the new manual visual smoke testing rule and the app's present UI/UX needs?

---

## Executive Summary

**Recommendation: Upgrade Uhura's explicit skill scope to include mobile-first design and visual accessibility ownership.** Do not add a new specialist role. The frontend work is appropriately concentrated with Uhura; the gap is in *declared* skill boundaries and *acceptance process* clarity, not in team composition. Formalize visual smoke testing ownership, accessibility review criteria, and design consistency as explicit Uhura responsibilities with McCoy verification checkpoints.

---

## Current Staffing Analysis

### Current Team Roster
- **Uhura** (Frontend Dev): Web UI, flows, components, modern UI stack
- **McCoy** (Tester): Tests, quality, edge cases, acceptance verification
- **Spec** (Spec Engineer): Specifications, requirements, design
- **Scotty** (Backend Dev): API, services, integrations
- **Sulu** (Data Engineer): Data, product mapping, inventory pipelines
- **Spock** (AI Engineer): AI/ML, prompts, personalization
- **Kirk** (Lead): Architecture, review gates, scope

---

## UI/UX Complexity Assessment

### Frontend Scope (Current)
1. **Component count:** 23 active TSX components across inventory, planner, grocery
2. **Page coverage:** Home, planner, inventory, grocery, (trip mode pending)
3. **Feature density:** 
   - Meal plan editing with AI suggestions (Milestone 2 ✅)
   - Inventory CRUD with locations and freshness (Milestone 1 ✅)
   - Grocery derivation + review (Milestone 3 ✅)
   - Mobile trip mode + offline queueing + conflict resolution (Milestone 4 🚀 active)
4. **Mobile requirements:** Constitution mandates mobile-first shopping; Milestone 4 requires phone-sized viewport validation, large touch targets, one-handed interaction
5. **Accessibility baseline:** Constitution requires "UX Quality and Reliability"; testing-quality.md explicitly lists accessibility as unresolved (focus order, labels, status messaging for conflict/retry states undefined)

### Design System & Consistency
- **Current state:** No design system document; components manually authored
- **Risk:** Visual drift across planner/inventory/grocery/trip pages
- **Viewport coverage:** Desktop, tablet, and mobile profiles must all be tested; Milestone 4 adds explicit offline/conflict UX that lacks accessibility acceptance criteria

---

## The Manual Visual Smoke Testing Rule

**Directive source:** `.squad/decisions/inbox/copilot-directive-20260307T200940Z.md`

> As part of completing each spec, perform manual visual smoke testing in a real browser, including Playwright screenshots for both web and mobile screen sizes/profiles, and review usability/UI-UX before accepting completion.

### Implications
1. **Acceptance gate:** Every feature completion now requires manual review of visual quality, mobile responsiveness, accessibility, and usability
2. **Playwright coverage:** Screenshots for web, tablet, and mobile profiles expected
3. **Ownership:** Currently unassigned — no role explicitly owns "visual acceptance" or "accessibility review"
4. **Effort:** This is not trivial. Reviewing visual consistency, accessibility, and mobile responsiveness across multiple viewports requires domain expertise, not just "looking at it"

### Who Should Own This?
- **Option A (Current gap):** Undefined — nobody officially reviews visual/accessibility acceptance
- **Option B (Add designer):** Hire a UI/UX specialist to own design system, accessibility, and visual acceptance gates
- **Option C (Expand Uhura):** Formalize Uhura's scope to include visual design, accessibility compliance, and visual acceptance ownership

---

## Skill Gap Analysis

### Uhura's Current Strengths
- Owns all web implementation (proven across 3 milestones)
- Delivered planner, inventory, and grocery UI slices
- Experienced with Playwright and component testing
- Familiar with Milestone 4 offline/conflict UX requirements
- No cognitive handoff needed to a new designer — she owns the code

### Uhura's Documented Skill Gaps
- No explicit "visual design" skill area (design system, consistency, accessibility)
- No documented "mobile-first design" expertise
- No accessibility compliance background documented
- No "design pattern review" or "visual smoke testing" responsibility assigned

### McCoy's Current Role
- Owns test coverage, verification, quality gates
- Proven strong on contract/acceptance criteria validation
- Does NOT own visual design, accessibility, or mobile UX expertise
- Is well-positioned as a **verification gate** for visual/accessibility acceptance, not as the **owner** of design decisions

### Spec's Role
- Owns specifications and requirements
- Could document accessibility and mobile-first criteria in feature specs (e.g., WCAG baseline, viewport breakpoints, touch target minimums)
- Should NOT own the live visual review — that's UX-specialist work

---

## Why Adding a Designer Is Not Justified Right Now

### Reasons to NOT Add a New UI/UX Specialist
1. **Cognitive concentration:** Uhura already owns all web implementation. Adding a separate designer creates a split-brain problem where implementation and design intent can diverge, and someone else is reviewing Uhura's code for visual quality.

2. **No implementation backlog waiting:** The app has one frontend engineer (Uhura) and she is actively building across Milestones 1–4. There is no separate "UX work queue" sitting idle waiting for a designer to start.

3. **Team lean-ness:** The current roster (Kirk, Spec, Uhura, Scotty, Spock, Sulu, McCoy, Scribe, Ralph) is already balanced. Adding a designer inflates the team without removing work from anyone's plate.

4. **Cost vs. Lift:** Adding a designer role, onboarding them to the project context, and managing the design-implementation handoff is higher overhead than formalizing Uhura's skill areas.

5. **Milestone 4 timing:** We are mid-Milestone 4 (SYNC-00–SYNC-11 in flight). Inserting a new designer now would require re-scoping offline/trip work that Uhura is already progressing.

### Why Adding a Narrowly-Scoped Specialist Could Be Needed (But Isn't Yet)
- **If** the app grows to require a separate visual-design or design-systems team in Phase 2 (store-aware enhancements, richer collaboration, advanced recipe UI)
- **If** accessibility compliance becomes a hard regulatory or platform requirement (Azure accessibility gates, WCAG AA mandate)
- Then a dedicated accessibility/design specialist becomes justified

---

## Recommended Action: Skill Area Expansion for Uhura

### Explicit New Skill Areas for Uhura
1. **Mobile-first design and responsive validation**
   - Ownership of phone-sized layout decisions, touch target sizing (48px minimum), one-handed interaction patterns
   - Explicit responsibility to verify trip/offline UI on actual mobile viewports (not just browser resize)
   - Linked to Milestone 4 SYNC-03 and SYNC-07 tasks

2. **Visual accessibility and WCAG baseline compliance**
   - Ownership of semantic HTML, focus order, ARIA labels, and screen-reader testing for trip/conflict UX
   - Establishment of accessibility acceptance criteria per feature (e.g., "all interactive elements ≥48px", "all inputs have labels", "conflict-state messaging is audible")
   - Coordination with Spec to document accessibility baseline in feature specs

3. **Manual visual smoke testing and visual consistency review**
   - Explicit acceptance gate: before any feature is marked complete, Uhura reviews Playwright screenshots across web/tablet/mobile profiles
   - Usability review: UI navigation, button clarity, error/state messaging, visual hierarchy
   - Design consistency: component reuse, color/spacing/typography consistency across pages
   - Escalate visual rework needs to Spec/Kirk if they conflict with approved spec

4. **Design system documentation (lightweight)**
   - Establish a basic design system / component guide documenting spacing, color, typography, touch target rules, accessibility conventions
   - Not a separate Figma design tool — just a `.squad/project/design-system.md` documenting decisions made in code
   - Prevents drift as mobile/offline/trip components are added in Milestone 4

### Verification Gate: McCoy as Visual/Accessibility Verifier
- McCoy's acceptance responsibility expands to include:
  - **Accessibility regression:** Feature specs include accessibility acceptance criteria; McCoy verifies them
  - **Smoke test evidence:** Uhura provides Playwright screenshot evidence and usability rationale; McCoy spot-checks for accessibility coverage
  - **Mobile viewport validation:** For Milestone 4, McCoy explicitly tests trip/conflict UI on mobile-sized viewport
- McCoy remains the gatekeeper for "is the feature truly done?" but Uhura is the owner of "is the visual/accessibility quality good?"

### Routing Change
- **Status quo:** Web UI requests → Uhura (implementation) → McCoy (test coverage) → Kirk (acceptance)
- **New posture:** Web UI requests → Uhura (implementation + visual/accessibility design) → McCoy (visual/accessibility verification + test coverage) → Kirk (acceptance)
- Spec continues to document accessibility and mobile-first criteria in feature specs upfront

---

## Implementation: Uhura's Updated Charter

**Current charter (from `.squad/agents/uhura/charter.md`):**
> Build and refine the web experience for planning meals, managing inventory, and supporting shopping workflows.
> 
> Owns: Client-side UX, accessibility, and component quality  
> Boundaries: Respect approved specs and shared design decisions

**Updated charter (proposed):**
> Build and refine the web experience for planning meals, managing inventory, and supporting shopping workflows with strong mobile-first design, visual consistency, and accessibility.
> 
> **Owns:**
> - Client-side UX, accessibility, and component quality
> - Mobile-first responsive design and viewport validation (phone, tablet, desktop)
> - Visual accessibility compliance (WCAG baseline, semantic HTML, focus/ARIA, screen-reader testing)
> - Manual visual smoke testing and design consistency review per feature completion
> - Lightweight design system documentation in code
>
> **Boundaries:**
> - Respect approved specs and shared design decisions (Spec owns spec accessibility criteria; Uhura owns implementation validation)
> - Coordinate with McCoy on accessibility verification before feature acceptance
> - Escalate visual/accessibility conflicts with specs to Kirk/Spec

---

## Process Change: Visual Smoke Testing Ownership

### New Acceptance Gate (Before Feature Marked Complete)
1. **Uhura's visual review checklist:**
   - [ ] Responsive layout valid on desktop, tablet, and mobile viewports
   - [ ] Touch targets ≥48px on mobile (trip, conflict, inventory edit screens)
   - [ ] Error/state messaging clear and accessible
   - [ ] Visual hierarchy and component consistency with design system
   - [ ] Playwright screenshots captured for web/mobile profiles
   - [ ] Accessibility basics verified: labels, focus order, ARIA where needed

2. **McCoy's accessibility spot-check (before test completion):**
   - [ ] Uhura provided smoke-test evidence and rationale
   - [ ] Accessibility criteria from spec are covered in acceptance tests
   - [ ] Mobile viewport tested (for mobile-critical features like trip mode)
   - [ ] Failure states and conflict/retry messaging are accessible

3. **Kirk's acceptance gate:**
   - Reviews implementation against spec, visual evidence, and accessibility coverage
   - Signs off when both Uhura's visual quality and McCoy's verification are green

---

## Skills/Processes That Need Explicit Documentation

1. **Design System / Component Guide** (lightweight)
   - Create `.squad/project/design-system.md` documenting:
     - Color palette and usage
     - Typography (font sizes, weights, line heights)
     - Spacing system (margins, padding increments)
     - Touch target and button sizing rules
     - Accessible interaction patterns (focus states, ARIA, labels)
   - Populated incrementally as Uhura makes design decisions across milestones

2. **Accessibility Baseline in Specs**
   - Spec to include WCAG baseline (at least A-level), mobile viewport assumptions, and touch-target minimums in each feature spec
   - Uhura to validate these during implementation review
   - McCoy to spot-check during acceptance

3. **Visual Smoke Testing Template**
   - Create `.squad/templates/visual-smoke-test-checklist.md` as a reusable checklist for Uhura to sign off on before each feature is marked complete

---

## Risk Mitigation

### If Uhura Becomes a Bottleneck
- **Monitor:** Track Uhura's task velocity across implementation + visual review
- **Action:** If she is overloaded, consider adding **accessibility specialist only** (narrowly scoped: WCAG compliance, screen-reader testing, focus order validation) — not a full designer
- **Decision point:** Post-Milestone 4; re-evaluate if Phase 2 scope expands

### If Accessibility Becomes a Hard Requirement
- **Trigger:** If Azure compliance gates or explicit WCAG AA mandate lands
- **Action:** Justify adding a dedicated accessibility specialist; restructure Uhura's scope to focus on UX/design, not compliance testing

### If Design Drift Becomes Visible
- **Monitor:** Every 2 milestones, review component consistency across pages
- **Action:** If 3+ visual inconsistencies found across 2 milestones, elevate to Kirk/Spec to consider design-systems specialist

---

## What This Decision Does NOT Do

1. **Does not add a new team member.** Uhura remains the only frontend engineer.
2. **Does not slow down Milestone 4.** SYNC-02, SYNC-03, SYNC-07 proceed as planned; visual review is added to the acceptance gate, not to the implementation path.
3. **Does not require Figma or external design tools.** Design system lives in code and markdown.
4. **Does not defer accessibility.** Makes it a first-class responsibility from day 1, not a "nice to have."

---

## What This Decision Requires

1. **Charter update:** Formalize Uhura's mobile-first, accessibility, and visual-design responsibilities in her charter
2. **Process update:** Add visual smoke testing checklist to feature completion criteria
3. **Documentation:** Create `.squad/project/design-system.md` and `.squad/templates/visual-smoke-test-checklist.md`
4. **Spec discipline:** Include accessibility and mobile-first criteria in every feature spec (Spec owner)
5. **McCoy coordination:** Add accessibility/mobile-viewport spot-checks to McCoy's acceptance verification (already in his charter; making it explicit)

---

## Recommendation Summary

| Aspect | Decision |
|--------|----------|
| Add UI/UX specialist? | **No** — Uhura alone is appropriate |
| Add accessibility specialist? | **No** — Uhura expands scope; monitor for overload post-M4 |
| Add mobile design specialist? | **No** — Uhura owns mobile-first |
| Expand Uhura's skill boundaries? | **Yes** — formalize mobile-first design, accessibility, visual smoke testing |
| Update acceptance gates? | **Yes** — add visual/accessibility checklist before feature completion |
| Create design system? | **Yes** — lightweight (Markdown) in `.squad/project/design-system.md` |
| Engage McCoy more on visual/a11y? | **Yes** — spot-check accessibility before Uhura marks complete |
| Cost of this change | Minimal — process/documentation only; no new salary, no team restructure |

---

## Next Steps

1. Update `.squad/agents/uhura/charter.md` with new skill areas
2. Create `.squad/project/design-system.md` (stub with color/spacing/typography rules)
3. Create `.squad/templates/visual-smoke-test-checklist.md` for reuse across milestones
4. In next spec work, add "accessibility baseline" and "mobile viewport assumptions" sections
5. Monitor Uhura's velocity post-Milestone 4; reassess if overloaded

---

**Approval:** Kirk  
**Date:** 2026-03-09
