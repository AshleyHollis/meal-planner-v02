from __future__ import annotations

import logging
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_REQUIRED_LOCAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("ai_suggestion_requests", "meal_plan_id"),
    ("ai_suggestion_requests", "meal_plan_slot_id"),
    ("meal_plan_slots", "slot_key"),
    ("grocery_lists", "confirmation_client_mutation_id"),
    ("grocery_list_items", "stable_line_id"),
)


def find_local_db_incompatibilities(db_path: Path) -> list[str]:
    if not db_path.exists():
        return []

    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        issues: list[str] = []
        for table_name, column_name in _REQUIRED_LOCAL_COLUMNS:
            if table_name not in tables:
                continue

            columns = {
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            }
            if column_name not in columns:
                issues.append(f"{table_name}.{column_name}")
        return issues
    finally:
        connection.close()


def backup_incompatible_local_db(db_path: Path) -> Path | None:
    issues = find_local_db_incompatibilities(db_path)
    if not issues:
        return None

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = db_path.with_name(
        f"{db_path.stem}.incompatible-{timestamp}{db_path.suffix}.bak"
    )
    db_path.replace(backup_path)
    logger.warning(
        "resetting incompatible local sqlite database",
        extra={
            "local_db_path": str(db_path),
            "local_db_backup_path": str(backup_path),
            "local_db_incompatibilities": issues,
        },
    )
    return backup_path


def resolve_local_db_path(db_path: Path) -> Path:
    issues = find_local_db_incompatibilities(db_path)
    if not issues:
        return db_path

    try:
        backup_incompatible_local_db(db_path)
        return db_path
    except PermissionError:
        fallback_path = db_path.with_name(
            f"{db_path.stem}.process-{os.getpid()}{db_path.suffix}"
        )
        logger.warning(
            "local sqlite database is locked; using isolated fallback database",
            extra={
                "local_db_path": str(db_path),
                "local_db_fallback_path": str(fallback_path),
                "local_db_incompatibilities": issues,
            },
        )
        return fallback_path
