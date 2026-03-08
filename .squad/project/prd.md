# Product Requirements Document

## Project
- **Product:** AI-Assisted Household Meal Planner
- **Repository:** `meal-planner-v02`
- **Requested by:** Ashley Hollis
- **Status:** Draft for review
- **Last Updated:** 2026-03-07

## 1. Product Summary
The AI-Assisted Household Meal Planner helps a household decide what to cook, understand what ingredients they already have, generate a weekly plan, produce a grocery list, complete a shopping trip, and keep inventory trustworthy after shopping and cooking. The MVP combines a REST API, modern web UI, and editable AI-generated weekly meal-plan suggestions while honoring the constitution priorities of strong UX, mobile shopping first, offline support, reliability, shared-household thinking, food-waste reduction, and explainable AI.

## 2. Problem Statement
Household meal planning is fragmented across memory, handwritten notes, recipe ideas, and shopping apps that do not reflect real pantry, fridge, freezer, and leftovers state. This causes overbuying, forgotten ingredients, wasted food, and friction during shopping and cooking, especially when more than one household member may rely on the same plan and inventory.

Current alternatives often fail in one or more important ways:
- They treat shopping lists as separate from actual household inventory.
- They do not make expiry pressure or leftovers visible during planning.
- They make mobile shopping awkward or assume constant connectivity.
- They use AI as opaque automation rather than as an editable assistant.
- They do not help users confidently update inventory after real-world shopping and cooking.

## 3. Product Vision
Create a trustworthy household planning system that makes it easy to plan a week of meals, shop from a phone, use what is already on hand, and keep inventory accurate enough that the household can rely on it. AI should reduce planning effort, but users must remain in control of authoritative meal-plan, grocery, and inventory data.

## 4. Goals
### 4.1 Business and Product Goals
- Deliver a usable MVP focused on shared inventory, weekly meal planning, grocery/trip workflow, and post-shopping/post-cooking inventory updates.
- Make the product meaningfully helpful for everyday household use, not just recipe inspiration.
- Reduce food waste by bringing existing stock, leftovers, and expiry pressure into planning decisions.
- Establish a foundation for future household collaboration, store-specific workflows, and richer AI assistance without redesigning the core data model.

### 4.2 User Goals
- Know what ingredients are available across pantry, fridge, freezer, and leftovers.
- Build or accept an editable weekly meal plan faster than planning manually.
- Generate a grocery list that reflects the current plan and household inventory.
- Use the grocery/trip flow effectively on a phone, even with intermittent connectivity.
- Update inventory with confidence after shopping and after cooking.

### 4.3 Experience Goals
- Low-friction, high-clarity workflows with minimal typing on mobile.
- Strong user trust in quantities, item states, and shopping progress.
- Clear AI explanations and easy overrides.
- Graceful behavior during weak network conditions and sync delays.

## 5. Non-Goals
The following are explicitly out of MVP scope unless later approved:
- Store-specific product mapping and preferred-shop support.
- Rich multi-person collaboration workflows beyond a primary planner model.
- Advanced AI beyond editable weekly meal-plan suggestions.
- Opaque automation that directly mutates authoritative shopping or inventory state without explicit user action.

The following may be explored later but are not required to define MVP success:
- Deep recipe marketplace or content-library differentiation.
- Dynamic pricing, coupon optimization, or retailer integrations.
- Advanced nutrition coaching beyond basic dietary restriction and preference support.

## 6. Target Users and Jobs To Be Done
### 6.1 Primary Persona: Household Planner
The person primarily responsible for deciding meals, checking what is on hand, and preparing the weekly shopping trip.

**Jobs to be done**
- When I am planning the week, I want meal suggestions that account for inventory, leftovers, equipment, and household preferences so I can decide quickly.
- When I review a proposed plan, I want to edit it easily so I stay in control.
- When I generate groceries, I want confidence that the list reflects what I actually need.

### 6.2 Secondary Persona: In-Store Shopper
Often the same person as the planner, but in a different context: mobile, time-pressured, and possibly offline.

**Jobs to be done**
- When I am at the store, I want a mobile-first list and trip flow so I can shop quickly with one hand.
- When connectivity is poor, I still want to view the current plan, list, and recent inventory snapshot.
- When I purchase or skip items, I want the list state to remain trustworthy and sync safely later.

### 6.3 Secondary Persona: Household Cook
The person using the meal plan to prepare meals and update inventory afterward.

**Jobs to be done**
- When I cook a planned meal, I want to record what was used so inventory stays accurate.
- When I create leftovers, I want them represented clearly so they can be reused in future plans.
- When substitutions happen, I want to adjust the plan or consumption without breaking trust in the data.

## 7. Product Principles Applied to MVP
This PRD follows the constitution and assumes:
- Mobile shopping flows are first-class.
- Essential trip workflows require offline-capable behavior.
- Inventory and shopping data are trust data and must be auditable, reversible where practical, and conflict-safe.
- AI is advisory and editable, not authoritative.
- Food-waste reduction is a real optimization goal, especially through expiry and leftovers awareness.

## 8. MVP Scope
### 8.1 Included in MVP
1. **Shared household inventory**
   - Track pantry, fridge, freezer, and leftovers as distinct but related inventory areas.
   - Support quantity/state updates that remain understandable to users.
   - Surface expiry-aware information where available.

2. **Weekly meal planning**
   - Create and edit a weekly meal plan.
   - Support dietary restrictions and preferences in planning.
   - Consider cooking equipment and substitutions as planning inputs where needed.
   - Provide AI-generated weekly meal-plan suggestions that are explainable and editable.

3. **Grocery and trip workflow**
   - Generate grocery needs from the meal plan and current inventory.
   - Support grocery-list review and adjustment before the trip.
   - Support mobile-first trip execution with core offline-capable access to plan, list, and inventory snapshot.

4. **Post-shopping inventory updates**
   - Convert shopping outcomes into inventory updates with user-visible control.
   - Avoid silent duplicates or confusing stock changes.

5. **Post-cooking inventory updates**
   - Update inventory after planned meals are cooked.
   - Support leftovers as a first-class outcome.

### 8.2 MVP Boundaries
- MVP should start with one primary planner per household experience, but design choices should not block later expansion to richer collaboration.
- AI scope is limited to weekly meal-plan suggestions and accompanying reasoning.
- The MVP should prefer clear workflows and trustworthy state over broad automation.

## 9. First-Pass Feature List
This is an initial feature map intended to feed architecture and downstream feature specs.

### 9.1 Inventory Foundation
- Household inventory model for pantry, fridge, freezer, and leftovers
- Inventory item CRUD and quantity adjustments
- Expiry or freshness metadata capture where known
- Inventory activity/history suitable for audit and reversal

### 9.2 Meal Planning
- Weekly planner view
- Manual meal-slot editing
- Dietary restriction and preference inputs
- Equipment-aware planning inputs
- Substitution-aware planning support
- AI-generated weekly meal-plan suggestion flow with rationale and edit controls

### 9.3 Grocery Calculation and Review
- Grocery need calculation from meal plan + current inventory
- List review and manual adjustment
- Quantity/unit handling sufficient for household planning
- Distinction between suggested and user-confirmed grocery changes where needed

### 9.4 Trip Workflow
- Mobile-first shopping list view
- Check-off and quantity edits during the trip
- Add ad hoc items during shopping
- Offline-capable viewing and trip edits with later synchronization behavior to be specified

### 9.5 Inventory Reconciliation After Actions
- Apply purchased items to inventory after shopping
- Apply consumed ingredients to inventory after cooking
- Create/update leftovers after cooking
- Handle corrections when the user notices a mismatch

### 9.6 Cross-Cutting Product Requirements
- Explainability for AI plan suggestions
- Clear empty/loading/retry/conflict states
- Shared-household-safe state changes
- Observability and retry-safe background processing for non-immediate work

## 10. User Journey Overview
### 10.1 Weekly Planning Journey
1. User reviews current household inventory and expiry pressure.
2. User requests or receives an AI-generated weekly plan suggestion.
3. User reviews rationale, edits meals, substitutions, or constraints.
4. User confirms the week’s plan.
5. System derives grocery needs from the approved plan and current inventory.

### 10.2 Shopping Journey
1. User opens the grocery/trip flow on mobile.
2. User views current list, related meal-plan context, and latest inventory snapshot.
3. User shops with support for checking off, editing, and adding items even under poor connectivity.
4. User confirms or reviews shopping outcomes.
5. System prepares user-controlled inventory updates from the trip.

### 10.3 Cooking and Inventory Journey
1. User selects a planned meal during or after cooking.
2. User records what was actually used and whether leftovers were created.
3. System updates inventory in a clear, auditable way.
4. Future planning can reuse leftovers and updated stock levels.

## 11. Success Criteria
### 11.1 MVP Success Indicators
- Users can create or accept an editable weekly plan and produce a usable grocery list from it.
- Users can complete a shopping trip on mobile without desktop-only steps.
- Essential shopping interactions remain usable during intermittent connectivity.
- Inventory remains understandable and correct enough that users continue relying on it week to week.
- AI suggestions are adopted as a planning accelerator because they are editable and clearly explained.

### 11.2 Candidate Measurable Outcomes
The exact targets remain to be finalized, but likely measures include:
- Weekly plan completion rate
- Grocery-list generation completion rate
- Trip workflow completion rate on mobile
- Percentage of AI-suggested meal plans that are accepted with edits or without edits
- Reduction in manually reported food waste or unused expiring items
- Inventory correction rate after shopping/cooking, used as a proxy for trust and data quality

## 12. Major Risks
- **Inventory trust risk:** If quantities drift or updates feel opaque, users may abandon the product quickly.
- **Offline/sync risk:** Weak offline behavior or confusing conflict resolution can break the in-store experience.
- **AI trust risk:** If plan suggestions feel generic, unexplainable, or hard to edit, AI will be seen as noise.
- **Scope risk:** Meal planning, inventory, shopping, and reconciliation are tightly connected; MVP must stay focused on the approved core loop.
- **Data-model risk:** Important architecture choices are still open, including database, auth/identity, offline sync approach, and queue technology.

## 13. Assumptions
- The MVP serves a household workflow with a shared state but starts from a primary planner mental model.
- The product will be delivered as a web experience with a modern UI and REST API, consistent with the approved stack.
- AI planning suggestions will use household context such as inventory, preferences, and expiry pressure when that data is available.
- Users need manual override paths at every point where AI or automation influences planning outcomes.

## 14. Open Questions
These are intentionally unresolved and should feed architecture and feature-spec work:
- What database technology and state boundaries best support authoritative inventory, auditability, and sync needs?
- What authentication and household identity model should represent planner, shopper, and future multi-person roles?
- What client-side offline storage and synchronization approach should support mobile shopping and later reconciliation?
- Which queue technology will support background work in Aspire-based local development and Azure deployment?
- How should recipes, meal templates, and ingredient representations be modeled to balance speed of delivery with trustworthy grocery calculation?
- What level of expiry precision is realistic for MVP: date-only, freshness windows, or mixed confidence levels?
- What inventory update UX best balances speed and auditability after shopping and cooking?

## 15. Phase 2 Ideas
These are explicitly beyond MVP but compatible with the current direction:
- Store-specific product mapping and preferred-shop support
- Richer multi-person collaboration, permissions, and simultaneous coordination flows
- More advanced AI assistance such as smarter substitutions, trip optimization, or adaptive planning
- Deeper grocery intelligence such as retailer-aware flows or pricing support
- More advanced recipe and nutrition experiences

## 16. Recommended Next Specs
The following artifacts should follow this PRD:
1. Architecture outline for frontend, API, workers, offline-capable flows, and authoritative state boundaries
2. Dedicated AI technical architecture for MVP weekly meal-plan suggestions, including provider/runtime direction, grounding pipeline, prompt/result versioning, explainability contract, and fallback/testing posture
3. Feature spec for inventory model and inventory mutation rules
4. Feature spec for weekly meal planning, including AI explainability and override behavior
5. Feature spec for grocery calculation and trip workflow, including offline and sync behavior
6. Feature spec for post-shopping and post-cooking reconciliation flows
