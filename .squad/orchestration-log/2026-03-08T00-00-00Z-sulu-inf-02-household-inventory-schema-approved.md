# Sulu INF-02 Household-Scoped Inventory Persistence Foundation Approved

**Date:** 2026-03-08T00:00:00Z  
**Agent:** Sulu  
**Task:** INF-02 — Add SQL-backed household and inventory schema  
**Status:** Approved  

## Summary

Sulu has completed INF-02 by establishing `households` and `household_memberships` as first-class SQL tables and making `inventory_items`, `inventory_adjustments`, and `mutation_receipts` explicitly household-backed with foreign keys to `households`.

## What was delivered

- `households` and `household_memberships` now persisted in SQL
- `inventory_items`, `inventory_adjustments`, and `mutation_receipts` explicitly household-backed with foreign-key constraints
- Freshness-basis rules and non-negative quantity/version expectations enforced with database constraints
- Mutation receipts unique on `(household_id, client_mutation_id)` for household-scoped duplicate replay handling
- Deterministic two-household seed fixtures with intentional shared `client_mutation_id` across households proving isolation and idempotency scope

## Evidence

- Relevant backend validation passed: `python -m pytest tests\models tests\schemas tests\test_inventory.py tests\test_session.py tests\test_health.py` from `apps\api`
- Model coverage now includes deterministic two-household inventory fixtures, per-household replay receipt scope with shared mutation ID, DB-level freshness-basis enforcement, and SQLite foreign-key enforcement
- SQLAlchemy models and test metadata bootstrap confirm schema design
- No migration framework needed in current repo; schema source remains the SQLAlchemy models and test bootstrap

## Handoff

INF-03 (Scotty) is now ready to begin replacing the in-memory inventory store with SQL-backed persistence on top of this locked household and inventory schema. Concrete household and inventory tables eliminate the placeholder-schema uncertainty for downstream work.

## Cross-team impact

- Scotty can build INF-03 against concrete household and inventory tables without inventing new tenancy seams
- Spec and McCoy have durable evidence that one household cannot claim another household's receipts or inventory history at the schema layer
- Database constraints backstop the existing API contract for freshness semantics and append-only correction linkage, reducing trust-sensitive drift between model code and route validation
