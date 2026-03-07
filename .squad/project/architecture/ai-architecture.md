# AI Technical Architecture: Weekly Meal-Plan Suggestions

Last Updated: 2026-03-07
Status: Draft for review

## 1. Purpose
This document turns the existing AI notes into a concrete technical architecture for MVP weekly meal-plan suggestions. It defines the proposed default provider/model path, runtime boundaries, prompt and policy structure, grounding pipeline, result contract, operational expectations, and what should be locked now versus deferred to later feature specs.

This doc is intentionally specific because Ashley asked for a reviewable AI plan, not generic AI aspirations.

## 2. Scope and Non-Goals
### 2.1 In scope for MVP
- advisory weekly meal-plan suggestion generation,
- household-context grounding from product-owned data,
- structured explanations and visible fallback states,
- async request lifecycle and worker execution,
- prompt/policy versioning,
- deterministic validation, evaluation, and operational controls.

### 2.2 Out of scope for MVP
- direct AI mutation of authoritative meal-plan, grocery, or inventory state,
- general chat/copilot UX,
- vector search, embeddings, and retrieval pipelines,
- online learning, fine-tuning, or autonomous ranking loops,
- advanced substitution engines, retailer optimization, or nutrition coaching.

## 3. Decision Summary

| Concern | Proposed default | Borrowed vs. new | Why |
| --- | --- | --- | --- |
| Primary provider for preview/prod | **Azure OpenAI** | New recommendation, informed by `yt-summarizer` dual-mode wrapper and this repo's Azure-first architecture | Matches Azure deployment posture, Key Vault, preview/prod ops, and keeps provider access inside the same cloud boundary |
| Local/dev fallback provider path | **OpenAI-compatible adapter that can target standard OpenAI when needed** | Borrowed from `yt-summarizer` | Reduces local friction and preserves provider portability without making MVP multi-LLM |
| MVP generation model | **Small, JSON-capable chat model**; proposed default deployment: `gpt-4o-mini` on Azure OpenAI | New recommendation; deployment style borrowed from `yt-summarizer` | Weekly planning suggestions need reliability and structure more than maximum creativity; small models keep latency and cost bounded |
| Execution model | `POST` request to API -> SQL request row -> queue message -> worker generation -> SQL result row | Borrowed from existing architecture and `yt-summarizer` worker pattern | Keeps UI responsive and makes retries, fallback, and failure states visible |
| Result validation | Pydantic schema validation plus deterministic post-validation | Borrowed from `yt-summarizer` and `meal-planner-005` plans | Prevents opaque or malformed AI output from entering product state |
| Prompt construction | Function-based prompt builders with explicit context formatters | Borrowed from `meal-planner-005-grocery-enhancements` | Easier to test, extend, and reason about than giant string templates |
| Prompt versioning | Lightweight repo-owned prompt bundle versioning from MVP day one | New recommendation | Reproducibility matters for acceptance telemetry, preview/prod drift, and support investigations |
| Storage for AI results | Normalized result contract in SQL; optional raw provider payload capture only for diagnostics | New recommendation | Meal-plan suggestions are small, user-reviewed, and queryable; blob-first storage from `yt-summarizer` is not the right default here |
| Fallback path | Reuse equivalent fresh result if possible; otherwise curated deterministic meal-template fallback; otherwise visible manual-planning guidance | New recommendation | Keeps planning usable without pretending provider failures did not happen |
| Observability | Correlation IDs + OpenTelemetry across API, queue, and worker | Borrowed from `yt-summarizer` | AI latency, failures, and stale-result behavior must be diagnosable |

## 4. Recommended MVP AI Infrastructure
### 4.1 Why the MVP stack should stay simple
MVP AI is a narrow advisory capability, so the infra should stay narrow too. The project does **not** need a vector database, embeddings pipeline, model router, agent framework, or multi-step planner before launch because those add operational complexity without directly improving the approved weekly suggestion workflow.

### 4.2 Recommended components

| Layer | Proposed default | Why this is enough for MVP |
| --- | --- | --- |
| AI request entry | FastAPI endpoint | Keeps auth, household authorization, and request dedupe in the authoritative API |
| Async transport | Azure Storage Queue / Azurite locally | Already aligned with project architecture and proven in `yt-summarizer` |
| Generation runtime | Python worker process | Central place for grounding, prompt rendering, provider calls, validation, retries, and normalization |
| Provider | Azure OpenAI in preview/prod | Simplest fit with Azure hosting and Key Vault-backed secrets |
| Config | Pydantic BaseSettings + environment variables from Key Vault/Aspire | Proven team pattern and easy to test |
| Operational storage | SQL request/result tables | Needed for polling, staleness, feedback, explainability, and support review |
| Optional diagnostics storage | Structured SQL fields first; raw payload capture only when debugging is enabled | Avoids blob-first complexity for small structured outputs |

### 4.3 What is explicitly not recommended for MVP
- No vector store or embeddings service.
- No retrieval over unstructured documents.
- No general-purpose agent/tool-calling loop.
- No model-per-feature sprawl.
- No runtime prompt editing from an admin UI.
- No fine-tuning pipeline.

Those can be reconsidered only if later feature specs justify them with product value.

## 5. Provider and Model Direction
### 5.1 Borrowed patterns from the reference repos
From `yt-summarizer`, this project should borrow:
- a provider wrapper that can speak to **Azure OpenAI or standard OpenAI** through one app-owned interface,
- Pydantic `BaseSettings` config resolution that tolerates Aspire-style `ConnectionStrings__*` inputs,
- queue-backed worker execution with persisted job state,
- OpenTelemetry instrumentation around provider calls.

From `meal-planner-005-grocery-enhancements`, this project should borrow:
- function-based prompt building,
- explicit hard versus soft constraint language,
- deterministic validators that run after generation,
- clear relaxation order for soft constraints.

### 5.2 Proposed default provider choice
**Proposed default for MVP:** use **Azure OpenAI** for preview and production, with a single small-model deployment dedicated to meal-plan suggestion generation.

Why:
1. The rest of the platform is already Azure-first.
2. Preview/prod secret management is already Key Vault-centric.
3. Worker-based generation benefits from stable quotas and cloud-local networking.
4. Keeping the first production provider inside the same cloud boundary reduces operational spread.

### 5.3 Proposed default model choice
**Proposed default model:** deploy `gpt-4o-mini` in Azure OpenAI for weekly suggestion generation, with JSON-style structured output enforced by the app contract.

Why this is the default:
- The feature needs structured, explainable output more than creative long-form prose.
- A small model is usually sufficient for 7-slot weekly planning with grounded household context.
- Cost and latency are materially better than using a larger flagship model for every request.

### 5.4 What remains recommendation-only, not yet ratified
- The exact Azure OpenAI deployment name can change if Ashley prefers a different Azure-supported small model at implementation time.
- A secondary standard OpenAI API key path is a **portability and local-dev convenience**, not a commitment to support multiple live providers in MVP.
- A larger fallback model for second-pass repair is **not** recommended for MVP unless structured output failure proves common in preview evidence.

## 6. Where AI Runs in the System
### 6.1 Runtime boundary
AI should run in the **worker**, not inline in the API request path.

#### API responsibilities
- authenticate the caller,
- authorize household access,
- validate the request payload,
- dedupe or reuse equivalent requests when appropriate,
- persist `ai_suggestion_request`,
- enqueue background work,
- expose request/result polling endpoints.

#### Worker responsibilities
- load the latest household grounding data from SQL,
- build the normalized context object,
- render prompt + policy bundle,
- call the provider,
- validate and normalize output,
- apply retries and fallbacks,
- persist structured result + execution metadata.

### 6.2 Queue and storage expectations
**Queue messages**
- logical message type: `meal_plan_generate_requested`,
- payload should contain request ID, household ID, plan period ID, actor ID, and correlation ID,
- duplicate delivery must be safe.

**SQL tables**
- `ai_suggestion_requests`,
- `ai_suggestion_results`,
- `ai_suggestion_feedback`,
- optional `ai_prompt_versions` only if the team later wants DB-backed prompt cataloging; not required for MVP.

**Recommended request row fields**
- request ID,
- household ID,
- plan period ID,
- requested slot scope,
- grounding hash,
- status,
- created by,
- correlation ID,
- prompt family/version,
- result contract version.

**Recommended result row fields**
- request ID,
- status,
- provider name,
- model/deployment name,
- fallback mode,
- generation started/completed timestamps,
- token counts if available,
- normalized structured result payload,
- warnings and validation notes,
- freshness basis metadata.

### 6.3 Preview versus production posture

| Area | Preview | Production |
| --- | --- | --- |
| Provider quota | Lower dedicated quota or lower concurrency cap | Higher quota, sized for household traffic |
| Secrets | Preview-specific Key Vault entries or versions | Production-specific Key Vault entries |
| Retry budget | Tighter to avoid runaway preview spend | Slightly broader but still bounded |
| Cost alerts | Per-preview guardrails and soft caps | Stronger dashboards and budget alerts |
| Diagnostics | More verbose structured execution metadata allowed | Production-safe metadata only, no raw prompts unless explicitly enabled |

### 6.4 Secrets and config needs
The worker and API both need the same AI-related configuration surface. Public web config does **not** need direct provider credentials.

**Non-secret configuration**
- `AI_PROVIDER=azure_openai`,
- `AI_REQUEST_TIMEOUT_SECONDS`,
- `AI_MAX_RETRIES`,
- `AI_MAX_INPUT_TOKENS`,
- `AI_MAX_OUTPUT_TOKENS`,
- `AI_PROMPT_FAMILY`,
- `AI_RESULT_CONTRACT_VERSION`.

**Secret configuration**
- `AZURE_OPENAI_ENDPOINT`,
- `AZURE_OPENAI_API_KEY`,
- `AZURE_OPENAI_API_VERSION`,
- `AZURE_OPENAI_CHAT_DEPLOYMENT`,
- optional `OPENAI_API_KEY` only for local fallback mode.

**Proposed default secret posture**
- store secrets in Azure Key Vault,
- inject them into API and worker through the existing Key Vault strategy,
- prefer a Key Vault-managed API key for MVP rather than adding Entra-ID provider auth complexity immediately.

## 7. Request Lifecycle and State Machine
### 7.1 Suggested lifecycle
1. Client requests a weekly suggestion.
2. API validates request and household access.
3. API checks for a reusable fresh result by plan period + grounding hash.
4. If reusable, API returns the existing request/result reference.
5. Otherwise API writes request row as `queued` and enqueues work.
6. Worker marks request `generating`.
7. Worker assembles grounding data from current SQL state.
8. Worker renders prompt bundle and calls provider.
9. Worker validates the response against the app schema.
10. Worker either:
   - writes `completed`,
   - writes `completed_with_fallback`, or
   - writes `failed`.
11. Client polls the request endpoint and renders the latest visible state.

### 7.2 Allowed request states
- `queued`
- `generating`
- `completed`
- `completed_with_fallback`
- `failed`
- `stale`
- `superseded`

### 7.3 Staleness rule
An AI suggestion should be marked `stale` when any of the following change after generation:
- the plan period or slot set,
- pinned/excluded meals,
- inventory basis version used for grounding,
- household dietary restrictions or hard exclusions,
- recent-meal window basis relevant to repetition avoidance.

The UI may still show the stale result for reference, but it must not present it as current advice.

## 8. Prompt and Policy Architecture
### 8.1 Prompt bundle structure
The worker should compose prompts from four layers:

1. **System policy layer**
   - advisory-only posture,
   - never mutate authoritative state,
   - obey hard restrictions,
   - admit missing context plainly.

2. **Planning task layer**
   - generate weekly meal-slot suggestions for the requested household and time period,
   - optimize for using on-hand and expiring items where practical,
   - avoid recent repetition,
   - keep suggestions editable and realistic.

3. **Grounding/context layer**
   - rendered from deterministic formatters,
   - inventory and expiry signals,
   - dietary restrictions and preferences,
   - equipment constraints,
   - household size,
   - pinned/excluded meals,
   - recent accepted/cooked meal history.

4. **Result schema layer**
   - exact JSON shape instructions,
   - explanation requirements,
   - reason-code expectations,
   - fallback/warning fields.

### 8.2 Policy separation
The policy layer should remain distinct from the context layer. Product policy such as "never violate allergy restrictions" must not be hidden inside ad hoc formatter text where it becomes harder to test or version.

### 8.3 Prompt versioning approach
This project should use **lightweight prompt versioning from MVP day one**.

#### Proposed default version fields
- `prompt_family` — e.g. `weekly_meal_plan`
- `prompt_version` — semantic version string, e.g. `1.0.0`
- `policy_version` — semantic version string for rules and safety language
- `context_contract_version` — shape of the grounding object
- `result_contract_version` — shape of the normalized result payload

#### Version bump rules
- **PATCH**: copy edits or wording changes expected to preserve behavior.
- **MINOR**: added optional context or explanation fields without breaking consumers.
- **MAJOR**: changed required output fields, changed hard/soft constraint semantics, or changed staleness/fallback behavior visible to clients.

#### Storage rule
Persist these version fields on every request and completed result. This makes preview/prod comparisons, bug triage, and human review reproducible without building a prompt CMS.

### 8.4 Where prompt assets should live
When implementation starts, prompt code should live in the worker codebase, not in environment variables and not in the database. A reasonable target structure is:

```text
apps/worker/.../ai/
  prompts.py
  policy.py
  context_renderers.py
  schemas.py
  validators.py
```

That is a target layout, not a claim that it already exists.

## 9. Grounding and Context Assembly Pipeline
### 9.1 Pipeline rule
Grounding must be assembled server-side from authoritative household data. The client may request generation, but it must not be trusted to supply the actual planning context.

### 9.2 Proposed pipeline steps
1. **Load request frame**
   - household ID,
   - plan period,
   - slots to fill,
   - actor ID,
   - pinned or locked slots.

2. **Load household planning context**
   - household size,
   - dietary restrictions and allergies,
   - explicit preferences and dislikes,
   - equipment constraints,
   - max prep-time preferences if the product has them by then.

3. **Load inventory context**
   - pantry, fridge, freezer, leftovers,
   - quantity and unit summaries suitable for planning,
   - expiry/freshness metadata,
   - derived expiry buckets such as `use_now`, `use_soon`, `stable`.

4. **Load repetition and continuity context**
   - recent accepted plans,
   - recent cooked meals,
   - leftover-linked meals already needing reuse,
   - excluded meals or cuisines.

5. **Normalize into a compact grounding object**
   - collapse duplicate ingredient mentions,
   - convert raw dates into planning-friendly expiry buckets,
   - separate hard constraints from soft preferences,
   - sort items deterministically.

6. **Apply token budget rules**
   - always keep hard restrictions,
   - keep high-expiry-pressure items,
   - keep pinned/excluded slot context,
   - trim low-priority long-tail inventory first,
   - trim verbose history before trimming hard rules.

7. **Compute grounding hash**
   - hash the normalized context object plus request scope,
   - use the hash for dedupe, reuse, and stale checks.

### 9.3 Proposed grounding object sections
- `hard_constraints`
- `soft_preferences`
- `inventory_priority_items`
- `leftover_candidates`
- `equipment_constraints`
- `recent_meals`
- `slot_requirements`
- `household_summary`
- `context_warnings`

### 9.4 Hard versus soft rule contract
**Hard constraints**
- allergies/intolerances treated as hard blocks,
- explicit excluded ingredients or meal types,
- slot locks and pinned meals,
- household membership/authorization boundaries.

**Soft constraints**
- preference matches,
- favorite patterns,
- repetition avoidance,
- prep-time desirability,
- food-waste reduction targets,
- cuisine leaning.

The relaxation order must be deterministic and visible:
1. keep hard constraints always,
2. relax repetition avoidance if necessary,
3. relax cuisine preference if necessary,
4. relax favorites/likes ordering,
5. never relax allergies or explicit exclusions.

## 10. Result Schema and Explainability Contract
### 10.1 Contract principles
- The app owns the result schema.
- The provider never defines the product contract.
- Every slot suggestion must be explainable in product terms, not generic model prose.
- The result must be valid even when context is sparse or fallback is used.

### 10.2 Proposed normalized result shape
```json
{
  "request_id": "uuid",
  "status": "completed",
  "fallback_mode": "none",
  "stale": false,
  "prompt_family": "weekly_meal_plan",
  "prompt_version": "1.0.0",
  "result_contract_version": "1.0.0",
  "warnings": [],
  "slots": [
    {
      "slot_key": "2026-03-09-dinner",
      "meal_title": "Lemon Chicken Tray Bake",
      "summary": "Sheet-pan dinner using chicken thighs and broccoli already on hand.",
      "uses_on_hand": ["chicken thighs", "broccoli", "potatoes"],
      "missing_key_ingredients": ["lemons"],
      "reason_codes": [
        "USES_ON_HAND",
        "USES_EXPIRING_ITEM",
        "FITS_EQUIPMENT"
      ],
      "explanations": [
        {
          "code": "USES_ON_HAND",
          "message": "Uses chicken thighs and potatoes already in the household inventory.",
          "source_refs": ["inventory:chicken-thighs", "inventory:potatoes"]
        }
      ],
      "grocery_impact_hint": "Need lemons and garlic if not substituted."
    }
  ],
  "data_completeness_note": "Recent meal history was available; prep-time preference was not set."
}
```

### 10.3 Required slot fields
- `slot_key`
- `meal_title`
- `summary`
- `uses_on_hand`
- `missing_key_ingredients`
- `reason_codes`
- `explanations`

### 10.4 Canonical reason codes for MVP
- `USES_ON_HAND`
- `USES_EXPIRING_ITEM`
- `USES_LEFTOVERS`
- `FITS_DIETARY_RULES`
- `FITS_EQUIPMENT`
- `AVOIDS_RECENT_REPEAT`
- `MATCHES_PREFERENCE`
- `LOW_PREP_EFFORT`
- `LOW_CONTEXT_FALLBACK`

The UI should render these through app-controlled labels. It should not infer hidden confidence scores.

### 10.5 Explainability rule
Each slot should include **1 to 3 explicit reasons** tied to actual household data or fallback state. Generic explanations like "this seems tasty" are not sufficient for MVP.

### 10.6 Confidence posture
Do **not** expose pseudo-precise numeric confidence scores in MVP. Use:
- explicit reason codes,
- data-completeness notes,
- fallback mode,
- stale indicator,
- warnings.

That is more honest and more actionable for the product than invented percentages.

## 11. Failure Modes, Fallbacks, Retries, and Limits
### 11.1 Failure-mode table

| Failure mode | Expected behavior | User-visible outcome |
| --- | --- | --- |
| Provider timeout | Retry with bounded backoff | `generating` then either `completed_with_fallback` or `failed` |
| Provider rate limit | Retry with jitter and respect provider hints when available | Manual planning remains available; result does not silently disappear |
| Malformed model output | Attempt one normalization/repair pass inside worker logic; if still invalid, use fallback or fail visibly | No invalid payload reaches the client contract |
| Sparse household data | Generate with lower-personalization mode | `data_completeness_note` and possibly `LOW_CONTEXT_FALLBACK` reason |
| Queue duplicate delivery | Idempotent processing keyed by request ID | Single visible result only |
| Inventory changed mid-generation | Persist completed result but mark stale basis if versions changed before client review | Result visible but flagged stale |
| Hard constraints over-constrained | Relax soft rules only; if still impossible, fail visibly or return curated safe fallback | User sees why suggestions were limited |

### 11.2 Retry policy
**Proposed default**
- max 3 worker attempts per request,
- backoff with jitter,
- first retry after 10 seconds,
- second retry after 30 seconds,
- third retry after 90 seconds,
- then terminal `failed`.

### 11.3 Request throttling and dedupe
**Proposed default**
- only one active generation per household + plan period + slot scope,
- if a second identical request arrives while one is running, return the same request ID,
- manual regenerate limited to once every 30 seconds per household,
- worker concurrency capped per replica so provider quota exhaustion does not cascade.

### 11.4 Latency expectations
These are design targets, not contractual SLAs:
- API `POST` request should return quickly with `202 Accepted`-style behavior,
- P50 end-to-end suggestion readiness target: **under 8 seconds**,
- P95 target: **under 25 seconds**,
- if generation exceeds **30 seconds**, the UI should clearly remain in async mode rather than implying instant AI.

### 11.5 Cost expectations
These are target budgets rather than provider price guarantees:
- keep the normalized context under roughly **6k input tokens**,
- keep the result under roughly **2.5k output tokens**,
- target median per-request provider cost in the **low cents** range,
- alert if production requests regularly exceed the agreed budget threshold,
- preview should have stricter concurrency and spend caps than production.

### 11.6 Fallback design
Fallback should be tiered:
1. **Reuse fresh equivalent result** if the same grounding hash already completed recently.
2. **Curated deterministic fallback** from app-owned meal templates tagged with dietary and equipment metadata.
3. **Visible manual-planning guidance** when even the curated fallback cannot safely satisfy hard constraints.

For MVP, the curated fallback catalog should be intentionally small and reviewable, not a hidden heuristic system.

## 12. Evaluation and Testing Strategy
### 12.1 What to test
AI testing should focus on **contract correctness, grounding correctness, and graceful degradation**, not on pretending CI can judge culinary taste.

### 12.2 Required automated layers
**Unit tests**
- context assembly and deterministic trimming,
- hard versus soft constraint classification,
- grounding hash generation,
- staleness detection,
- result normalization,
- reason-code generation.

**Integration tests**
- API request persistence + queue publish,
- worker processing with fake provider,
- retry behavior,
- duplicate queue delivery handling,
- fallback selection,
- SQL persistence of prompt/result metadata.

**Contract tests**
- request endpoint response shape,
- result endpoint response shape,
- required explanation fields,
- version fields present,
- stale/fallback state rendering payloads.

**E2E tests**
- user requests AI plan and reviews it,
- user edits and accepts selected meals,
- provider failure path shows manual option,
- stale result path after inventory or plan change,
- mobile render still exposes explanation and retry states cleanly.

### 12.3 Evaluation fixtures
Maintain deterministic household fixtures for:
- rich inventory + expiry pressure,
- sparse inventory,
- allergy-heavy household,
- repetition-avoidance household,
- pinned meals already filling part of the week,
- provider timeout,
- malformed provider output,
- fallback-triggered request.

### 12.4 Release evidence
Before merge on AI-affecting work, the repository should eventually require:
- passing unit and integration coverage for changed AI modules,
- contract validation for result schema changes,
- preview evidence that the request lifecycle and fallback states still work,
- no live-provider dependency in routine CI.

### 12.5 Human review rubric
Ashley should be able to review a preview build and answer:
1. Are the reasons clear and grounded in household data?
2. Are fallback and sparse-data states honest?
3. Does the result stay editable without hidden automation?
4. Do stale-result indicators appear when the plan basis changes?

## 13. Lessons Learned from the Reference Repos
### 13.1 `yt-summarizer`
Useful lessons to adopt:
- dual Azure/OpenAI config wrapper is practical,
- Pydantic settings and queue client patterns already fit Aspire,
- OpenTelemetry around AI calls is worth doing early,
- persisted job state makes async UX and retries understandable.

Useful lessons **not** to copy directly:
- inline unversioned prompts are acceptable for that repo, but this project should add lightweight version tags because meal-planner suggestions are directly user-reviewed and compared over time,
- blob-first storage for large summaries makes sense there, but here normalized SQL records are the better default because results are small and need structured explainability.

### 13.2 `meal-planner-005-grocery-enhancements`
Useful lessons to adopt:
- function-based prompt builders,
- explicit formatter helpers,
- validator functions that run after generation,
- hard/soft rule separation,
- deterministic relaxation order.

Useful lessons to tighten for this repo:
- move from implied prompt evolution to explicit prompt/version tracking,
- define explainability as a first-class contract, not just narrative rationale,
- make fallback and staleness states part of the persisted result model.

## 14. What Should Be Explicit Now vs. Deferred

| Explicit in architecture now | Defer to later feature specs |
| --- | --- |
| AI is advisory only | Detailed recipe schema depth |
| Azure OpenAI primary / OpenAI-compatible fallback wrapper | Full substitution engine behavior |
| API vs. worker boundary | Advanced ranking heuristics between candidate meals |
| Queue-backed async lifecycle | Personalized learning from acceptance/rejection feedback |
| Prompt/policy/context/result version fields | Multi-provider routing |
| Grounding pipeline sections and trimming order | Streaming status updates instead of polling |
| Result schema and reason codes | Rich nutrition optimization |
| Retry, throttle, and fallback posture | Fine-tuning or embeddings |
| Preview/prod secret and config posture | Long-term analytics dashboards |

## 15. Recommended Follow-On Specs
After this document, the next AI-adjacent specs should be:
1. weekly planner feature spec referencing this request/result contract,
2. recipe/template catalog spec for curated fallback and grocery-friendly ingredients,
3. inventory-to-planning context mapping spec,
4. acceptance/edit telemetry spec for AI evaluation,
5. implementation plan for worker/provider/config modules.

## 16. Review Summary for Ashley
- The recommended MVP AI path is deliberately narrow: one async suggestion workflow, one primary provider, one small structured-output model, and strong deterministic contracts around it.
- The biggest architectural shift from the current notes is adding lightweight prompt/result versioning and a concrete explainability contract now, instead of leaving them implicit.
- The result keeps AI useful but bounded: grounded in household data, visible when weak or stale, and never authoritative on its own.
