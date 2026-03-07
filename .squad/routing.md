# Routing

| Signal | Route To | Notes |
| --- | --- | --- |
| Project principles, PRD, feature planning | Spec | Interview-first specification workflow |
| Architecture decisions, scope, review gates | Kirk | Lead and reviewer |
| Web UI, client flows, interaction design | Uhura | Frontend implementation |
| REST API, services, integrations | Scotty | Backend implementation |
| Personalization, recommendations, prompt logic | Spock | AI systems and prompt design |
| Inventory models, product mapping, store data flows | Sulu | Data design and pipelines |
| Verification, acceptance checks, edge cases | McCoy | Testing and review |
| Session logging, decisions merge, cross-agent updates | Scribe | Silent logging role |
| Backlog scanning, issue/PR monitoring, keep-alive | Ralph | Continuous work monitor |

## Default Behavior
- Route feature requests to Spec first unless the task is trivially small or the user explicitly says to skip spec.
- Route implementation tasks to the owning specialist plus McCoy for verification when parallel work is possible.
- Route ambiguous multi-domain work to Kirk for decomposition.
