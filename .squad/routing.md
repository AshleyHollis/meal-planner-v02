# Routing

| Signal | Route To | Notes |
| --- | --- | --- |
| Project principles, PRD, feature planning | Spec | Interview-first specification workflow |
| Architecture decisions, scope, review gates | Kirk | Lead and reviewer |
| Web UI, client flows, interaction design | Uhura | Frontend implementation |
| REST API, services, integrations | Scotty | Backend implementation |
| Personalization, recommendations, prompt logic | Spock | AI systems and prompt design |
| Inventory models, product mapping, store data flows | Sulu | Data design and pipelines |
| Functional test completion, edge cases, acceptance behavior | McCoy | Testing and review (implementation verification) |
| Design/accessibility/visual review (WCAG, responsive, contrast) | Kirk | Design acceptance gate; gated on spec requirements |
| Session logging, decisions merge, cross-agent updates | Scribe | Silent logging role |
| Backlog scanning, issue/PR monitoring, keep-alive | Ralph | Continuous work monitor |

## Default Behavior
- Route feature requests to Spec first unless the task is trivially small or the user explicitly says to skip spec.
- Route implementation tasks to the owning specialist plus McCoy for **functional verification** when parallel work is possible.
- Route ambiguous multi-domain work to Kirk for decomposition.
- **Separation of Duties:** McCoy verifies implementation correctness; Kirk verifies design/accessibility requirements against spec before final acceptance. Uhura remains implementation owner and primary UX contributor.

## Spec Requirements for UI-Bearing Features
- Include WCAG 2.1 AA accessibility target (or explicit constraint deviation with rationale)
- Specify mobile-first breakpoints and min/max viewport acceptance criteria
- Specify responsive layout, keyboard navigation, and color contrast acceptance criteria
- Identify any design-system or component-library dependencies before implementation starts
