# Spec Decision: Milestone-End Visual Smoke Testing

Date: 2026-03-09
Requested by: Ashley Hollis
Owner: Spec

## Decision

Manual visual smoke testing is required **once per milestone** at milestone end, not at every intermediate verify or final-acceptance sub-step.

- The smoke pass belongs in the milestone's **last user-journey verification gate** after automated verification is green.
- The pass must cover the milestone's key delivered flows on **desktop and phone-sized viewports** in the supported local app flow.
- The result must be recorded in the milestone progress/acceptance trail so the final approver can consume the same evidence when deciding milestone closure.
- Final acceptance should only require a rerun if the product changed materially after the recorded smoke pass or the earlier evidence is no longer trustworthy.

## Why

The milestone task plans already end with explicit verification and final acceptance steps. Requiring smoke testing at every internal verify/final-acceptance sub-step duplicates work, obscures where reviewers should look for UX evidence, and makes milestone closure harder to follow.

This refinement keeps the constitutional UX check intact while making the process concrete: one end-of-milestone smoke pass, one recorded evidence trail, one final approval decision.
