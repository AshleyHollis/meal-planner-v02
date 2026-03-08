from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import URL

from app.seeds.reviewer import (
    REVIEWER_HOUSEHOLD_ID,
    SECONDARY_HOUSEHOLD_ID,
    SeedSafetyError,
    bootstrap_from_environment,
    current_smoke_week,
    seed_dataset,
)
from app.services.grocery_service import GroceryService
from app.services.inventory_store import InventoryStore
from app.services.planner_service import PlannerService

PRIMARY_HOUSEHOLD_ID = REVIEWER_HOUSEHOLD_ID


def _database_url(tmp_path: Path) -> URL:
    return URL.create("sqlite+pysqlite", database=str((tmp_path / "reviewer-seed.sqlite").resolve()))


def test_reviewer_seed_builds_baseline_dataset(tmp_path: Path):
    database_url = _database_url(tmp_path)

    result = seed_dataset(environment="test", scenario="baseline", reset=True, database_url=database_url)

    inventory = InventoryStore(database_url=database_url)
    planner = PlannerService(database_url=database_url)
    grocery = GroceryService(database_url=database_url)
    try:
        assert result.period_start == current_smoke_week()
        assert len(inventory.list_items(PRIMARY_HOUSEHOLD_ID)) == 11
        assert len(inventory.list_items(SECONDARY_HOUSEHOLD_ID)) == 1

        confirmed_plan = planner.get_confirmed_plan(PRIMARY_HOUSEHOLD_ID, result.period_start)
        assert confirmed_plan is not None
        assert len(confirmed_plan.slots) == 21
        assert {slot.slot_origin for slot in confirmed_plan.slots} == {"ai_suggested", "manually_added"}
        assert any(slot.meal_reference_id is not None for slot in confirmed_plan.slots)

        grocery_list = grocery.get_current_list(PRIMARY_HOUSEHOLD_ID, result.period_start)
        assert grocery_list is not None
        assert grocery_list.status == "confirmed"
        assert grocery_list.trip_state == "confirmed_list_ready"
        assert any(line.origin == "ad_hoc" and line.active for line in grocery_list.lines)
        assert any(line.user_adjusted_quantity is not None for line in grocery_list.lines)
    finally:
        inventory.dispose()
        planner.dispose()
        grocery.dispose()


def test_reviewer_seed_trip_scenario_bootstraps_trip_state(tmp_path: Path):
    database_url = _database_url(tmp_path)

    result = seed_dataset(
        environment="test",
        scenario="trip-in-progress",
        reset=True,
        database_url=database_url,
    )

    grocery = GroceryService(database_url=database_url)
    try:
        grocery_list = grocery.get_current_list(PRIMARY_HOUSEHOLD_ID, result.period_start)
        assert grocery_list is not None
        assert grocery_list.status == "trip_in_progress"
        assert grocery_list.trip_state == "trip_in_progress"
    finally:
        grocery.dispose()


def test_reviewer_seed_blocks_production_environment(tmp_path: Path):
    database_url = _database_url(tmp_path)

    with pytest.raises(SeedSafetyError):
        seed_dataset(environment="production", reset=True, database_url=database_url)


def test_reviewer_seed_blocks_unknown_environment(tmp_path: Path):
    database_url = _database_url(tmp_path)

    with pytest.raises(SeedSafetyError):
        seed_dataset(environment="staging", reset=True, database_url=database_url)


def test_bootstrap_from_environment_only_applies_on_empty_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("MEAL_PLANNER_BOOTSTRAP_DATASET", "reviewer-baseline")
    monkeypatch.setenv("MEAL_PLANNER_BOOTSTRAP_ENV", "test")
    monkeypatch.setenv("MEAL_PLANNER_BOOTSTRAP_IF_EMPTY", "1")

    first = bootstrap_from_environment(database_url=database_url)
    second = bootstrap_from_environment(database_url=database_url)

    assert first is not None
    assert second is None


def test_reviewer_seed_alias_is_safe_empty_bootstrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_url = _database_url(tmp_path)
    monkeypatch.delenv("MEAL_PLANNER_BOOTSTRAP_DATASET", raising=False)
    monkeypatch.setenv("MEAL_PLANNER_REVIEWER_SEED", "1")
    monkeypatch.setenv("MEAL_PLANNER_BOOTSTRAP_ENV", "preview")
    monkeypatch.setenv("MEAL_PLANNER_REVIEWER_SEED_SCENARIO", "sync-conflict-review")

    first = bootstrap_from_environment(database_url=database_url)
    second = bootstrap_from_environment(database_url=database_url)

    assert first is not None
    assert first.environment == "preview"
    assert first.scenario == "sync-conflict-review"
    assert second is None
