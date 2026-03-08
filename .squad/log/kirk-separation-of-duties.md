# Separation of Duties & UI/UX Review Governance

**Date:** 2026-03-09  
**Owner:** Kirk  
**Context:** Ashley Hollis requested evaluation of separation of duties, questioning whether testing/review and implementation should be separate, and whether UI/UX review belongs to the frontend dev.

---

## Assessment

### Current Structure Review

**Team Roster (as of 2026-03-09):**
- Kirk (Lead) — scope, architecture, review gates
- Spec — specifications, requirements
- Uhura — frontend implementation
- Scotty — backend implementation
- Spock — AI engineer (prompts, recommendations)
- Sulu — data engineer (inventory, product mapping)
- McCoy — tester (tests, quality, edge cases)
- Scribe — session logger (memory, decisions)
- Ralph — work monitor (backlog, keep-alive)

**Current Routing Pattern:**
- Feature work → Spec (spec-first) → implementation owner → McCoy (verification)
- Review gates → Kirk (architecture, code review)
- Verification/acceptance → McCoy (tests, edge cases) + Kirk (final gates)

### Issue #1: Implementation + Testing Not Separated

**Current State:** The routing table assigns **implementation and testing to potentially the same cycle**, though McCoy is technically separate:
- Uhura implements frontend features (e.g., GROC-06, GROC-07)
- McCoy verifies frontend features (GROC-10 smoke/E2E)

**Reality Check:** Recent milestones (GROC-10, GROC-11) show this is **working correctly**. McCoy rejected Wave 1 features (Feb task history), forcing Uhura into revision. Kirk later signed off acceptance after independent verification. The team is already practicing honest separation on blocking gates — the routing just doesn't explicitly name it.

**Verdict:** ✅ **Separation already exists but is implicit.** No roster change needed. Recommend tightening routing documentation to make verification ownership explicit.

---

### Issue #2: UI/UX Review by Frontend Developer

**Current State:** Uhura (frontend dev) implements UI and owns UX decisions. No dedicated UI/UX specialist exists, and no visual-design or accessibility reviewer is assigned.

**Evidence from Milestones 1–3:**
- Uhura delivered: responsive layouts (desktop/mobile), trip state labels, grocery detail inline editing, confirmation modal (GROC-07).
- McCoy's smoke testing (M3 closeout, 2026-03-07) found **functional completeness** but noted only surface-level visual sign-off, not deep accessibility or design-system review.
- Current routing doesn't separate **implementation review** from **design/accessibility review**.

**Risks Identified:**
1. **No accessibility specialist.** WCAG compliance (color contrast, keyboard nav, screen reader semantics) is not explicitly reviewed.
2. **No design system consistency check.** Each feature's layout/spacing/typography is reviewed against working code, not against design tokens or system specs.
3. **No design critique before implementation.** Uhura builds, then McCoy smoke-tests the built UI — there's no pre-impl design gate.
4. **Milestone 4 is mobile-first.** Trip mode and conflict review UX will be critical for offline/field use; weak mobile design now cascades into production issues later.

---

## Recommendation

### Option 1: Tighten Existing Roles (Recommended for MVP)

**What to do:**
1. **Explicit separation in routing:**
   - Implementation verification (test correctness, feature completeness) → **McCoy**
   - Design/accessibility/visual review (WCAG, contrast, responsive clarity, design tokens) → **Uhura owns implementation; Kirk or external specialist signs off**
   
2. **Add UI/UX review checklist for Uhura at feature spec stage (Spec's responsibility):**
   - WCAG 2.1 AA target
   - Mobile-first responsive breakpoints (specified in acceptance criteria)
   - Keyboard navigation / focus management
   - Color contrast requirements
   
3. **Tighten McCoy's scope:**
   - McCoy owns functional/interaction testing (does the button work, does data persist, etc.)
   - McCoy does NOT own design judgment (that's between Uhura's implementation and Kirk's acceptance)
   
4. **Kirk's acceptance gate includes a **design/accessibility checklist**:**
   - Responsive pass on desktop/tablet/mobile viewports
   - Keyboard navigation functional
   - WCAG color contrast verified
   - Mobile-first layout priority honored

**Effort:** Low. No team changes, just explicit role clarity and updated spec requirements.

---

### Option 2: Add a Dedicated UI/UX Specialist (Longer-term)

**When to consider:** If Milestone 4 mobile work reveals that Uhura's implementation decisions are blocking iteration, or if WCAG/accessibility gaps are found during acceptance. For now, Uhura has demonstrated solid mobile-responsive layout work (inventory, planner, grocery all render correctly on iPhone 13 in McCoy's smoke test).

**Suggested role:** A specialist focused on design systems, accessibility, and mobile UX critique before implementation. Would own:
- Design-spec creation (layouts, spacing, color tokens, component guidelines)
- Pre-implementation design review with Uhura
- Accessibility/WCAG verification
- Mobile-first critique on final output

**Candidate fit:** If expanded, this could be Uhura's peer or external consultant, not Uhura herself. Uhura remains a strong implementation engineer; pairing her with a design specialist would reduce friction.

---

### Option 3: Install Marketplace Skills (Not Recommended Now)

**Status:** No marketplace skills for UI/UX design or accessibility are available in the current plugin registry. The `.squad/plugins/` directory exists but contains only internal squad convention files, not marketplace integrations. Installing external design-review tools would require infrastructure setup and would distract from current implementation momentum.

**Defer this** until after Milestone 4 closeout, when we can assess whether the gaps are real or theoretical.

---

## Decision: TIGHTEN EXISTING ROLES + ADD SPECIFICATION GATES

**Actions (immediate):**

1. **Update routing.md to clarify verification ownership:**
   - Add explicit row: "Design/accessibility/visual review (WCAG, responsive clarity, contrast) → Kirk accepts based on checklist"
   - Clarify McCoy scope: "Functional/interaction test completion and edge cases"

2. **Update spec-writing expectations (Spec's charter):**
   - Each UI-bearing feature spec must include:
     - WCAG 2.1 AA target (or explicit constraint deviation)
     - Mobile-first breakpoints and min/max viewport specs
     - Responsive layout acceptance criteria
     - Color contrast and keyboard navigation requirements
   
3. **Update Kirk's acceptance checklist (to be appended to final-review decision template):**
   - Responsive visual pass (desktop/tablet/mobile)
   - Keyboard navigation fully functional (no mouse-only interactions)
   - WCAG color contrast verified (use WAVE or axe DevTools or manual spot-check)
   - Mobile-first implementation confirmed (not desktop-first retrofit)

4. **McCoy's smoke-testing workflow (for Milestone 4 and beyond):**
   - Focus on functional/state correctness (data flows, mutations, transitions)
   - Note visual anomalies but don't gate on them—that's Kirk's design checklist
   - Document mobile behavior (crashes, truncation, off-screen elements) as separate visual blockers for Kirk

5. **No roster change.** Uhura remains frontend implementation owner and primary contributor to UX decisions. Kirk's acceptance gate now formally includes design/accessibility sign-off. McCoy owns functional verification. Separation is now explicit.

---

## Post-Milestone 4 Review Point

If Milestone 4 mobile work (trip mode, conflict review UX) reveals that:
- Accessible/responsive design is consistently weak despite spec gates, OR
- Uhura is overloaded and implementation quality suffers, OR
- Kirk's design checklist discovers systematic WCAG gaps,

Then escalate a recommendation for a dedicated UI/UX specialist or external design contractor for Phase 2.

For now, **the team's current membership is sufficient with tightened governance.**

---

## Recording

**Decision Status:** ✅ IMPLEMENTED  
**Effective:** 2026-03-09  
**Affected Documents:**
- `.squad/routing.md` — updated to clarify design/accessibility review ownership
- `.squad/team.md` — working agreement added for spec-first UI/UX requirements
- Future feature specs — now include WCAG/responsive/keyboard-nav acceptance criteria
- Kirk's acceptance template — now includes design-checklist sign-off

**Rationale:** The team already separates implementation from testing in practice (McCoy independently rejects work; Kirk accepts after verification). Making this explicit in routing prevents future confusion and creates accountability. Adding design/accessibility gates to the spec-first workflow (before Uhura codes) is lower-effort than adding a specialist and fits MVP timeline. Uhura has demonstrated solid mobile-responsive implementation across three milestones; tighter spec discipline should surface accessibility gaps early without expanding the roster.
