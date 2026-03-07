# Uhura Decision — GROC-07 Grocery Review UX

Date: 2026-03-08  
Owner: Uhura  
Scope: Grocery review and confirmation UX

## Decision

Use an inline review surface for grocery lines, with:

- inline per-line detail disclosure for meal traceability and inventory-offset breakdown,
- inline quantity override editing and removal review while the list is still a draft,
- a separate removed-lines section so draft review remains honest about what changed,
- and a confirmation modal for the final list-locking step instead of a silent one-click confirm.

## Why

- The grocery review surface needs fast scanability on desktop without hiding traceability detail behind route changes or a secondary page.
- On phones, the same disclosure pattern stacks cleanly and keeps each line self-contained, which is simpler than trying to maintain a side panel.
- Separating removed lines from active lines keeps the draft trustworthy: users can see what they intentionally dismissed without polluting the main shopping list.
- Confirmation is the authority boundary for Milestone 3, so the final commit step needs a dedicated modal that restates warnings, overrides, and the "locked list version" consequence.

## Consequences

- The current web grocery slice now favors inline disclosure + modal confirmation over a dedicated detail page.
- McCoy's GROC-10 verification should treat this interaction model as the expected review flow on both desktop and phone-sized layouts.
