# Spock History

## Project Context
- **User:** Ashley Hollis
- **Project:** AI-Assisted Household Meal Planner
- **Stack:** REST API, modern web UI, AI assistance, inventory/product mapping workflows
- **Description:** Build a connected household meal planning platform spanning inventory, meal plans, substitutions, store mapping, shopping trips, and inventory updates after shopping or cooking.
- **Team casting:** Star Trek TOS first.

## Learnings
- Team initialized on 2026-03-07 for Ashley Hollis.
- Current focus is spec-first setup for the AI-assisted household meal planning platform.
- MVP AI scope is advisory weekly meal-plan suggestion generation only; deterministic services still own inventory truth, grocery derivation, sync, and authoritative meal-plan persistence.
- AI planning docs now assume worker-based generation with grounded household/product inputs, structured explanation payloads, visible fallback states, and deterministic testing fixtures rather than routine live-provider dependence.
- Reference-repo review reinforced three patterns worth carrying forward: Azure/OpenAI-compatible provider wrappers, queue-backed worker execution with persisted request status, and OpenTelemetry-style AI observability from the start.
- Unlike `yt-summarizer`, meal-planner AI outputs should default to normalized SQL records instead of blob-first storage because the result is small, user-reviewed, and needs queryable explainability fields.
- Unlike the current reference repos, this project should add lightweight prompt/policy/result version tags from MVP so Ashley can compare preview/prod behavior and support can reproduce suggestion runs.
