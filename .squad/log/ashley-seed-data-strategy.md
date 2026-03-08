# Seed Data Strategy Review: Local and Preview/Test Environments

**Date:** 2026-03-09  
**Initiated by:** Ashley Hollis  
**Status:** Under Review

## Question
Should we be seeding test data into our local and preview/test environments?

## Context
- Milestone 4 execution active (SYNC-02, SYNC-04 in flight)
- Local Aspire environment running with multiple services (web, API, workers)
- Team relies on manual local testing and verification gates
- Manual visual smoke testing now mandatory at each milestone end

## Scope
- **Local development environment:** Should developers have seed data or start with empty state?
- **Preview/test environment:** Should CI/CD preview builds include pre-loaded test fixtures?
- **Data scale and coverage:** What test scenarios should seed data cover?
- **Maintenance overhead:** How to keep seeds synchronized with schema/contract changes?

## Related Decisions
- SYNC-01 contract seam locked (stable grocery_list_version_id, grocery_line_id, confirmed_at)
- GROC-08/GROC-09: Stable handoff seams and observability fixtures established
- Mandatory visual smoke testing requires running app with realistic data flow

## Decision Point
Team to evaluate:
1. Whether seed data improves developer experience and test reliability
2. Whether seed data helps validate Milestone 4 mobile/conflict scenarios in local testing
3. How to version and maintain seed fixtures alongside schema evolution
4. Whether preview builds (e.g., for stakeholder demo) need different seed strategy than developer local

## Expected Input
- Sulu (contract/schema perspective)
- Uhura (frontend/mobile testing perspective)
- Scotty (API/data pipeline perspective)
- McCoy (verification/test coverage perspective)
