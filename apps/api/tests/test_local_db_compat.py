from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import URL, create_engine

import app.models  # noqa: F401
from app.models.base import Base
from app.services.local_db_compat import (
    backup_incompatible_local_db,
    find_local_db_incompatibilities,
    resolve_local_db_path,
)


def _create_stale_schema(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(
            """
            CREATE TABLE ai_suggestion_requests (
                id TEXT PRIMARY KEY,
                household_id TEXT NOT NULL,
                actor_id TEXT NULL,
                plan_period_start TEXT NOT NULL,
                plan_period_end TEXT NOT NULL,
                target_slot_id TEXT NULL,
                status TEXT NOT NULL,
                request_idempotency_key TEXT NOT NULL,
                prompt_family TEXT NULL,
                prompt_version TEXT NULL,
                policy_version TEXT NULL,
                context_contract_version TEXT NULL,
                result_contract_version TEXT NULL,
                grounding_hash TEXT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT NULL
            );

            CREATE TABLE meal_plan_slots (
                id TEXT PRIMARY KEY,
                meal_plan_id TEXT NOT NULL,
                day_of_week INTEGER NOT NULL,
                meal_type TEXT NOT NULL,
                meal_title TEXT NULL,
                meal_reference_id TEXT NULL,
                slot_origin TEXT NOT NULL,
                is_user_locked INTEGER NOT NULL DEFAULT 0,
                notes TEXT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE grocery_lists (
                id TEXT PRIMARY KEY,
                household_id TEXT NOT NULL,
                meal_plan_id TEXT NULL,
                status TEXT NOT NULL,
                current_version_number INTEGER NOT NULL,
                confirmed_at TEXT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE grocery_list_items (
                id TEXT PRIMARY KEY,
                grocery_list_id TEXT NOT NULL,
                grocery_list_version_id TEXT NULL,
                ingredient_name TEXT NOT NULL,
                ingredient_ref_id TEXT NULL,
                quantity_needed NUMERIC NOT NULL,
                unit TEXT NOT NULL,
                quantity_offset NUMERIC NOT NULL,
                offset_inventory_item_id TEXT NULL,
                quantity_to_buy NUMERIC NOT NULL,
                origin TEXT NOT NULL,
                meal_sources TEXT NULL,
                user_adjusted_quantity NUMERIC NULL,
                user_adjustment_note TEXT NULL,
                user_adjustment_flagged INTEGER NOT NULL DEFAULT 0,
                ad_hoc_note TEXT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_purchased INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_find_local_db_incompatibilities_detects_stale_planner_and_grocery_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "inventory.sqlite"
    _create_stale_schema(db_path)

    assert find_local_db_incompatibilities(db_path) == [
        "ai_suggestion_requests.meal_plan_id",
        "ai_suggestion_requests.meal_plan_slot_id",
        "meal_plan_slots.slot_key",
        "grocery_lists.confirmation_client_mutation_id",
        "grocery_list_items.stable_line_id",
    ]


def test_find_local_db_incompatibilities_is_empty_for_current_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "inventory.sqlite"
    test_engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(db_path)),
        future=True,
    )
    try:
        Base.metadata.create_all(test_engine)
    finally:
        test_engine.dispose()

    assert find_local_db_incompatibilities(db_path) == []


def test_backup_incompatible_local_db_renames_stale_database(tmp_path: Path) -> None:
    db_path = tmp_path / "inventory.sqlite"
    _create_stale_schema(db_path)

    backup_path = backup_incompatible_local_db(db_path)

    assert backup_path is not None
    assert backup_path.exists()
    assert not db_path.exists()


def test_resolve_local_db_path_falls_back_when_stale_db_is_locked(tmp_path: Path) -> None:
    db_path = tmp_path / "inventory.sqlite"
    _create_stale_schema(db_path)

    connection = sqlite3.connect(db_path)
    try:
        fallback_path = resolve_local_db_path(db_path)
    finally:
        connection.close()

    if fallback_path == db_path:
        backup_paths = list(tmp_path.glob("inventory.incompatible-*.sqlite.bak"))
        assert len(backup_paths) == 1
        assert not db_path.exists()
    else:
        assert fallback_path.name.startswith("inventory.process-")
        assert db_path.exists()
