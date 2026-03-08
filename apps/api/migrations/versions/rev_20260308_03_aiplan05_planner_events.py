from __future__ import annotations

from sqlalchemy import Connection, inspect


revision = "20260308_03_aiplan05"
down_revision = "20260308_02_aiplan04"


def _has_table(connection: Connection, table_name: str) -> bool:
    inspector = inspect(connection)
    return table_name in inspector.get_table_names()


def _drop_index_if_exists(connection: Connection, index_name: str) -> None:
    connection.exec_driver_sql(f"DROP INDEX IF EXISTS {index_name}")


def upgrade(connection: Connection) -> None:
    if _has_table(connection, "planner_events"):
        return

    connection.exec_driver_sql(
        """
        CREATE TABLE planner_events (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            meal_plan_id VARCHAR(36) NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            source_mutation_id VARCHAR(128) NOT NULL,
            payload TEXT NOT NULL,
            occurred_at DATETIME NOT NULL,
            published_at DATETIME NULL,
            CONSTRAINT uq_planner_events_household_type_mutation
                UNIQUE (household_id, event_type, source_mutation_id),
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_planner_events_household_id ON planner_events (household_id)")
    connection.exec_driver_sql("CREATE INDEX ix_planner_events_meal_plan_id ON planner_events (meal_plan_id)")


def downgrade(connection: Connection) -> None:
    if not _has_table(connection, "planner_events"):
        return

    _drop_index_if_exists(connection, "ix_planner_events_household_id")
    _drop_index_if_exists(connection, "ix_planner_events_meal_plan_id")
    connection.exec_driver_sql("DROP TABLE planner_events")
