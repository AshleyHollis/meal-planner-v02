# AI Plan Acceptance Feature Spec

Date: 2026-03-07
Requested by: Ashley Hollis
Status: Draft for approval
Milestone: 2 (Weekly planner and explainable AI suggestions)
Depends on:
- `.squad/specs/inventory-foundation/feature-spec.md`
- `.squad/specs/offline-sync-conflicts/feature-spec.md`
- `.squad/project/architecture/ai-architecture.md`
- `.squad/specs/grocery-derivation/feature-spec.md`

## 1. Purpose

Define how a household planner reviews an AI-generated weekly meal-plan suggestion, edits individual slots, mixes AI and manual choices, and confirms the final plan so it becomes the authoritative input for grocery derivation and downstream workflows.

This spec turns the captured user decisions and the approved AI architecture into an implementation-ready contract for:
- the three distinct plan states: AI suggestion result, editable draft, and confirmed authoritative plan,
- slot-level editing and per-slot regeneration within a draft,
- mixed drafts combining AI-suggested and manually chosen slots,
- stale-draft detection and user warnings,
- protection of an existing confirmed plan when a new AI suggestion is requested,
- confirmation as the authoritative handoff into deterministic meal-plan state,
- what AI origin metadata is retained after confirmation,
- non-goals and out-of-scope items,
- offline and shared-household implications,
- acceptance criteria that align with grocery derivation depending only on confirmed plan state.

## 2. Scope

### In scope
- Reviewing an AI suggestion result (read-only, polling-complete state from the worker).
- Opening a draft plan pre-populated from an AI suggestion result.
- Editing individual meal slots within the draft.
- Replacing an AI-suggested slot with a manual choice, keeping other slots unchanged.
- Requesting per-slot AI regeneration within an existing draft without regenerating the full week.
- Mixed drafts where some slots are AI-suggested and others are manually chosen.
- Stale-draft detection and the user-visible warning when a draft may no longer reflect current preferences, inventory, or meals.
- Protecting an existing confirmed plan when the user requests a new AI suggestion.
- Confirming the draft, which promotes it to the authoritative confirmed plan and hands off to grocery derivation.
- Storing AI origin metadata (per-slot) in a background history record after confirmation.
- Offline and shared-household implications for the review, draft, and confirmation steps.

### Out of scope
- AI generating the suggestion (covered in `.squad/project/architecture/ai-architecture.md`).
- Grocery derivation logic after confirmation (covered in `.squad/specs/grocery-derivation/feature-spec.md`).
- Recipe content, ingredient data management, or meal catalog administration.
- Multi-user simultaneous draft editing beyond one active draft per household + period.
- Autonomous plan confirmation without an explicit user action.
- Rich collaborative drafting workflows (post-MVP).
- Feedback or rating flows beyond AI origin metadata retention (post-MVP).
- Nutritional scoring, cost estimation, or meal-quality ranking.

## 3. User Outcome

The household planner gets a proposed weekly meal plan from AI as a starting point, can review and adjust individual meals until the plan fits the household's needs, and can confirm the final plan with confidence — knowing the AI suggestion was a helpful draft, not an authoritative decision made without them.

## 4. Constitution Alignment

- **2.4 Trustworthy Planning and Inventory:** the confirmed plan is the only authoritative input to grocery derivation; AI suggestions are advisory and never silently promote to plan state.
- **2.5 Explainable AI, Never Opaque Automation:** each AI-suggested slot must surface reason codes and explanations from the existing AI result contract; AI origin is never hidden during the review and drafting phase.
- **2.3 Shared Household Coordination:** a draft belongs to a household + plan period; confirmation must never silently overwrite a co-existing confirmed plan for the same period.
- **2.2 Offline Is Required:** an in-progress draft should be readable offline; draft edits queue safely and sync when connectivity returns.
- **2.7 UX Quality and Reliability:** stale draft warning, per-slot regeneration state, confirmation success/failure, and AI-unavailable fallback are part of the feature, not deferred polish.
- **4.1 Spec-First Delivery:** this spec covers all state transitions, boundaries, offline behavior, and acceptance criteria before implementation begins.
- **5.1 / 5.2 / 5.3 Quality Gates:** the acceptance/rejection flow requires automated tests for state transitions, stale detection, protected confirmed plan, and grocery derivation handoff.

## 5. Core MVP Decisions

These decisions are authoritative and not subject to reinterpretation in implementation.

1. **Edit-then-confirm acceptance flow.** Users may edit individual slots in a draft before confirming the whole plan. There is no forced slot-by-slot confirmation wizard; the user works through the draft at their own pace and confirms when ready.

2. **Stale-draft warning, not stale-draft block.** If preferences, inventory, or meals change after the draft was opened, the app warns the user that the draft may be stale, but does not prevent confirmation. The warning must be visible and honest; suppressing it is not acceptable. The user's explicit confirmation is still valid even over a stale warning.

3. **User-edited slot loses AI advisory state; plan model stays simple.** Once a user edits a slot (replaces the AI suggestion with their own choice), that slot is treated as a user-chosen slot. No hidden scoring, re-ranking, or AI re-advisory step is applied to the edited slot. The model remains: AI-suggested (from the current suggestion result), user-edited (user has replaced the AI choice), or manually added (user filled a slot with no AI suggestion present).

4. **New AI suggestion is always a separate draft; existing confirmed plan is never auto-overwritten.** If a confirmed weekly plan already exists for a household + period, and the user requests a new AI suggestion, the resulting suggestion must open as a separate draft. The confirmed plan persists untouched until the user explicitly confirms a new plan over it. This protection is unconditional in MVP.

5. **Per-slot regeneration without full-week regeneration.** A user may request AI regeneration for a single slot within an existing draft. The regeneration follows the same async worker/request-result flow as full-week generation, scoped to the target slot. Other slots in the draft are not affected. The slot shows a pending/generating state while regeneration runs; on completion it shows the new suggestion for that slot.

6. **AI origin stored in background history after confirmation; not emphasized in the confirmed-plan main UI.** After confirmation, the confirmed plan looks like any other confirmed plan in the main UI. Per-slot AI origin metadata (suggestion request ID, reason codes, prompt version, fallback mode) is stored in a history/audit record for supportability and future telemetry, but the main confirmed-plan UI does not render AI badges or provenance labels.

7. **Mixed drafts are valid.** A draft may contain any combination of AI-suggested and manually chosen slots before confirmation. No rule requires all slots to be AI-suggested or all manually chosen. A user may accept all AI suggestions, accept none, or accept any subset.

## 6. Three Distinct Plan States

The implementation must maintain a clear distinction between these three states. They must not be conflated in storage, API shape, or UX.

### 6.1 AI suggestion result
- Produced by the worker after a successful generation run.
- Read-only from the plan-management perspective.
- Stored in `ai_suggestion_results` per the AI architecture contract.
- Contains: per-slot meal titles, summaries, reason codes, explanations, uses-on-hand lists, missing ingredients hints, fallback mode, stale flag, and prompt/result version fields.
- The suggestion result is the source material for opening a draft, not a draft itself.
- A suggestion result may be `stale` before a draft is opened from it; the draft must inherit that stale status and warn immediately.
- A suggestion result is never the authoritative plan.

### 6.2 Editable draft plan
- Created when the user opens an AI suggestion result for review, or when the user starts a manual plan from scratch.
- Mutable: the user may edit, reorder, clear, or replace slots.
- Scoped to a household + plan period; only one active draft per household + period.
- Contains per-slot state: `ai_suggested` (from the current suggestion result, not yet edited by user), `user_edited` (user replaced the AI suggestion), or `manually_added` (no AI suggestion was involved).
- The draft is not authoritative for grocery derivation. Grocery derivation must not read from draft state.
- A draft carries a `stale_warning` flag that is set true when preferences, inventory, or meals change materially after the draft was created or last refreshed.
- A draft carries a reference to the suggestion request ID(s) it was created from, for history linkage.
- A draft may contain per-slot `pending_regen` or `regenerating` state when a per-slot regeneration is in flight.
- The draft is disposable if the user abandons it; it does not affect confirmed plan state.

### 6.3 Confirmed authoritative plan
- Produced by an explicit user confirmation action on a draft.
- Immutable once confirmed (a later confirmation of a new draft creates a new confirmed plan version; prior versions are retained as history).
- Stored in the meal-plan authoritative table with status `confirmed`.
- The only plan state that grocery derivation may read.
- Does not carry AI advisory labels in its primary representation. AI origin is captured in a separate history record.
- Cannot be overwritten by a new AI suggestion result or by opening a new draft alone; only a new explicit user confirmation may replace it.

## 7. Review and Draft Workflow Rules

### 7.1 Opening a draft from an AI suggestion result
- The user takes an explicit action to open or "use" the AI suggestion.
- The system creates a new draft pre-populated with the AI suggestion slots.
- Each slot is marked `ai_suggested` and carries the full slot-level explanation payload from the suggestion result.
- If the suggestion result is already `stale` at draft-open time, the stale warning must be shown immediately and the draft must carry the warning flag.
- If an active draft already exists for the same household + period, the system must prompt before replacing it. Silent replacement of an in-progress draft is not allowed.

### 7.2 Editing individual slots
- Any slot in the draft may be replaced with a user-chosen meal at any time before confirmation.
- Once replaced, the slot state transitions to `user_edited`. The previous AI suggestion for that slot is no longer active in the draft.
- The prior AI suggestion payload for the edited slot must be retained in the draft's history record (not shown in the main draft UI, but available for history/audit).
- The user may also clear a slot (leaving it empty) or restore it to the original AI suggestion if they want to revert an edit.

### 7.3 Per-slot regeneration
- Available for any slot in the draft that has not been confirmed.
- The user requests regeneration for a specific slot. The other slots in the draft are unchanged.
- The system posts a scoped AI suggestion request for that slot, following the same async worker/request-result flow.
- While regeneration runs, the slot shows a pending/generating indicator; the rest of the draft remains interactive.
- On completion, the slot shows the new AI suggestion with updated explanations and reason codes. Slot state returns to `ai_suggested`.
- On failure, the slot shows an error state and the user may retry or edit manually.
- Regeneration for a slot uses a fresh grounding snapshot. If the new result differs materially from the original (different meal title or substantially different inventory basis), the stale warning on other draft slots is not automatically reset — only the regenerated slot reflects the updated advice.

### 7.4 Mixed drafts
- No rule requires all slots to share the same origin.
- The draft may have some `ai_suggested`, some `user_edited`, and some `manually_added` slots simultaneously.
- Confirmation of a mixed draft is a valid, supported outcome.
- The per-slot origin state is captured in history records after confirmation so the provenance of each slot is auditable.

### 7.5 Stale-draft detection and warning
- A draft becomes stale when any of the following occur after the draft was created or last refreshed:
  - The household dietary restrictions or hard exclusions change.
  - The inventory basis changes materially in a way that affects meals or ingredients the suggestion relied on.
  - A meal that the AI suggestion depends on is removed, archived, or otherwise unavailable.
  - The plan period or slot set changes.
- Stale detection relies on the grounding metadata already defined in the AI architecture, but MVP should only warn when the change affects meals or ingredients the suggestion actually relied on rather than any unrelated inventory movement.
- The stale warning must be visible in the draft UI. It must not be dismissible permanently before confirmation without the user acknowledging it.
- The stale warning must be plain language: it should explain that the plan may not reflect current inventory or preferences and invite the user to review or regenerate before confirming.
- Stale status does not block confirmation. The user may confirm over a stale warning. The warning is their last opportunity to know.
- After confirming over a stale warning, the history record should capture that the plan was confirmed with a known stale warning present.

### 7.6 Protection of an existing confirmed plan
- If a confirmed plan already exists for the household + period, requesting a new AI suggestion or opening a new draft must not affect it.
- The new AI suggestion result lands in `ai_suggestion_results` as a new result row.
- Any new draft opened from that result is a separate draft state, not a replacement for the confirmed plan.
- The confirmed plan remains authoritative for grocery derivation until a new explicit confirmation replaces it.
- The UI must clearly distinguish: "you have a confirmed plan for this week" from "you are reviewing a new draft/suggestion." These are not the same screen.

### 7.7 Confirmation as authoritative handoff
- Confirmation is an explicit user action (e.g., "Confirm this plan" button with no ambiguity about finality).
- Before confirmation, if a stale warning is present, the user must acknowledge it (not dismiss it permanently — they must at least see it clearly on the confirmation path).
- On confirmation, the system:
  1. Writes the confirmed plan record with status `confirmed` and all confirmed slot states.
  2. Writes a per-slot AI origin history record capturing: suggestion request ID, slot state at confirmation (`ai_suggested`, `user_edited`, `manually_added`), reason codes, prompt version, fallback mode, and stale warning flag.
  3. Marks the draft as `confirmed` (no longer editable).
  4. Emits a plan-confirmed event that grocery derivation can react to (per grocery derivation spec).
- Confirmation must be idempotent: if the same confirmation is retried after a transient failure, the confirmed plan record must not be duplicated.
- The confirmation response confirms success. A failed confirmation must leave the draft in its pre-confirmation state and surface an actionable error.

## 8. AI Origin Metadata After Confirmation

### 8.1 What is stored
For each confirmed slot, a history/audit record must store at minimum:
- `confirmed_plan_id`
- `slot_key`
- `slot_origin` (`ai_suggested`, `user_edited`, `manually_added`)
- `ai_suggestion_request_id` (null if `manually_added`)
- `ai_suggestion_result_id` (null if `manually_added`)
- `reason_codes` at the time the slot was AI-suggested (null if not AI-suggested)
- `prompt_family` and `prompt_version` (null if not AI-suggested)
- `fallback_mode` (null if not AI-suggested)
- `stale_warning_present_at_confirmation` (boolean)
- `confirmed_at`

### 8.2 What is not shown in the main confirmed-plan UI
- The confirmed plan detail and weekly plan view must not render AI origin badges, confidence labels, or AI attribution per slot as primary UI elements.
- AI origin is available through a history or audit view for supportability and future telemetry, not as primary planning UI affordance.
- This rule supports the principle that the confirmed plan is the user's plan, not the AI's plan with a rubber stamp.

### 8.3 Retention posture
- AI origin history records are retained as long as the associated confirmed plan record is retained.
- They are operational trust data, not disposable.

## 9. Offline and Shared-Household Implications

### 9.1 Draft editing offline
- The in-progress draft must be readable offline (stored locally using the IndexedDB-backed client storage).
- Slot edits made offline are queued as draft mutation intents and applied when connectivity returns.
- Per-slot regeneration requests require connectivity and must surface a clear "requires connection" state rather than silently failing.
- If the user confirms while offline, the confirmation intent is queued and applied on reconnect; the local UI optimistically shows the plan as confirmed but must not emit the grocery derivation trigger until the server confirmation succeeds.

### 9.2 Shared household considerations
- Only one active draft per household + period is supported in MVP.
- If two household members open or edit the same draft, last-write-wins with conflict surfacing is acceptable in MVP following the offline-sync-conflicts spec.
- The confirmed plan protection rule applies regardless of which household member triggers the new AI request; the confirmed plan is never auto-overwritten by any member's AI session.

### 9.3 AI suggestion requests are per-household, per-period
- An AI suggestion request is scoped to the household, not to the individual user within the household.
- Any household member may open a suggestion result as a draft.
- Draft state is household-scoped; if one member creates a draft from a suggestion, a second member opening the same suggestion should see a "draft already in progress" state.

## 10. Error and Confidence Posture

- AI is advisory only. Error states in AI generation (provider failure, fallback used, sparse data) must not prevent manual planning.
- If the AI suggestion result has `fallback_mode` set to `curated_fallback` or `manual_guidance`, this must be visible in the review UI before the user opens a draft from it.
- Reason codes and explanations must remain visible on AI-suggested slots throughout the draft phase, not just at initial review.
- If a per-slot regeneration fails, the slot falls back to the user's last manual choice or the original AI suggestion for that slot, not to an empty/broken state.
- The system must not expose pseudo-precise numeric confidence scores. Reason codes, stale warnings, fallback modes, and data-completeness notes are the confidence surface.

## 11. Non-Goals / Out of Scope for MVP

- **Autonomous confirmation:** AI may never confirm a plan without an explicit user action. This is unconditional.
- **AI origin emphasis in the confirmed-plan UI:** the main confirmed-plan view does not show AI provenance labels per slot.
- **Multi-draft comparison:** comparing two AI-generated drafts side-by-side is post-MVP.
- **AI feedback / rating flows:** users cannot rate individual AI suggestions in MVP. Origin metadata is captured for telemetry, not for a feedback product loop.
- **Smart slot reordering:** AI does not automatically re-sort or re-optimize the draft after user edits.
- **Undo beyond slot-level revert:** the only undo in MVP is reverting an individual edited slot back to its original AI suggestion.
- **Cross-period plan borrowing:** borrowing confirmed meals from a prior period into a new AI suggestion prompt is a future grounding enhancement.
- **AI-driven grocery impact optimization:** the AI suggestion is not yet aware of final grocery cost or pack-size considerations. This is post-MVP.

## 12. Acceptance Criteria

These are testable conditions that must pass before the feature is considered complete.

1. A user can request an AI suggestion, wait for the async result, and open a draft pre-populated with the AI-suggested slots.
2. Each AI-suggested slot in the draft displays the meal title, summary, reason codes, and at least one explanation tied to household data or fallback state.
3. A user can replace any individual slot in the draft with a manually chosen meal; the replaced slot is marked `user_edited` and the original AI suggestion for that slot is retained in the draft history.
4. A user can request per-slot AI regeneration; only the targeted slot enters a generating state while the rest of the draft remains interactive.
5. A draft may be confirmed with any mix of `ai_suggested`, `user_edited`, and `manually_added` slots.
6. If preferences, inventory, or meals change materially after the draft was created, the stale warning is visible in the draft UI before confirmation.
7. The stale warning does not block confirmation, but must be visible and acknowledged on the confirmation path.
8. If a confirmed weekly plan exists for the same household and period, requesting a new AI suggestion and opening a new draft does not modify or overwrite the confirmed plan.
9. Confirmation is an idempotent operation: retrying a confirmation after a transient failure does not create duplicate confirmed plan records.
10. After confirmation, the confirmed plan record exists with status `confirmed` and a per-slot AI origin history record is written.
11. The main confirmed-plan UI does not render AI origin badges or provenance labels per slot.
12. Grocery derivation uses only confirmed plan state; draft or AI suggestion result state is not visible to the derivation pipeline.
13. Test coverage exists for: draft-open from suggestion result, slot edit transition, per-slot regen lifecycle, stale warning trigger, confirmed plan protection, confirmation idempotency, mixed draft confirmation, and history record creation.
14. The stale warning at confirmation captures `stale_warning_present_at_confirmation: true` in the history record when applicable.

## 13. Risks and Guardrails

- **Risk: AI suggestion result is treated as a confirmed plan.** Guardrail: clear three-state model; derivation pipeline may only read `confirmed` state.
- **Risk: new AI draft silently replaces an existing confirmed plan.** Guardrail: confirmed plan protection is unconditional; any code path that auto-confirms or auto-replaces is a defect.
- **Risk: stale warning is dismissible or invisible.** Guardrail: stale warning must be present on the confirmation path, not just on the draft overview screen.
- **Risk: per-slot regeneration contaminates other draft slots.** Guardrail: regeneration is scoped; other slots must not change state while a per-slot regen is in flight.
- **Risk: AI origin metadata is lost after confirmation.** Guardrail: history record write is part of the confirmation transaction; failure to write history must fail the confirmation rather than silently drop the record.
- **Risk: offline confirmation triggers grocery derivation prematurely.** Guardrail: grocery derivation trigger fires only on server-confirmed plan; local optimistic state is clearly provisional.

## 14. Open Follow-On Questions

- Should the stale warning threshold be configurable (e.g., only trigger if a specific number of inventory items changed, or any change at all)? The spec assumes "any material grounding-relevant change" for MVP; the exact threshold can be tuned during implementation with preview evidence.
- Should a household member be able to explicitly "lock" a draft slot (pin it) to prevent it from being affected by the other household member's edits? This is likely a post-MVP feature but the data model should not preclude it.
- Should the per-slot AI origin history record be surfaced in any user-facing "plan history" view in Milestone 2, or only in support/admin tooling? The spec defers this choice to implementation while requiring the record be written.

## 15. Approval Readiness

This spec is ready for Ashley's review and approval as the AI plan acceptance implementation contract for Milestone 2. It is decision-complete at the rule/contract/state-machine level, while leaving schema naming, endpoint paths, and component file structure to downstream implementation.
