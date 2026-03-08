# meal-planner-v02

AI-assisted household meal planning platform with a REST API, modern web UI, deterministic grocery derivation, and advisory AI planning workflows.

## Repository layout

- `apps\web` - Next.js web application scaffold
- `apps\api` - FastAPI API scaffold
- `apps\worker` - Python worker scaffold
- `apps\apphost` - Aspire AppHost for local orchestration
- `infra\deploy\terraform` - app-owned Terraform baseline
- `.squad\project` - approved planning and architecture corpus

## Milestone 0 status

This repository is now scaffolded for the implementation-readiness phase described in the planning corpus. The highest-risk feature specs are approved and should be treated as authoritative before feature work begins.

## Local development

This scaffold intentionally separates structure from dependency installation:

1. Install JavaScript dependencies for `apps\web` when registry access is available.
2. Create a Python environment and install `apps\api` and `apps\worker`.
3. Restore the Aspire AppHost project.
4. Run the individual services or wire them together through the AppHost as Milestone 0 continues.

### Reviewer smoke seed reset

The API includes an intentional deterministic reviewer seed for local smoke/review flows. Reset the API database to that baseline from the repo root with:

`npm run seed:api:reviewer-reset`

You can pass through existing seed CLI options when needed, for example:

`npm run seed:api:reviewer-reset -- --scenario sync-conflict-review`

The underlying entrypoint is `python -m app.seeds reviewer-reset` from `apps\api`.

## Planning references

- `.squad\project\constitution.md`
- `.squad\project\prd.md`
- `.squad\project\roadmap.md`
- `.squad\project\architecture\overview.md`
- `.squad\project\architecture\ai-architecture.md`
- `.squad\specs\inventory-foundation\feature-spec.md`
- `.squad\specs\grocery-derivation\feature-spec.md`
- `.squad\specs\ai-plan-acceptance\feature-spec.md`
