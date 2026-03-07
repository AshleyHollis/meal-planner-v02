from __future__ import annotations

from sqlalchemy import create_engine, inspect

from migrations.versions import rev_20260309_06_sync04_sync_upload_foundations as migration


def _create_pre_sync04_schema(connection) -> None:
    connection.exec_driver_sql("CREATE TABLE households (id VARCHAR(36) NOT NULL PRIMARY KEY, name VARCHAR(255) NOT NULL)")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_lists (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            FOREIGN KEY(household_id) REFERENCES households (id)
        )
        """
    )


def test_sync04_migration_upgrade_and_downgrade() -> None:
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as connection:
        _create_pre_sync04_schema(connection)
        migration.upgrade(connection)

        inspector = inspect(connection)
        assert "grocery_sync_conflicts" in inspector.get_table_names()
        columns = {column["name"] for column in inspector.get_columns("grocery_sync_conflicts")}
        assert {
            "household_id",
            "grocery_list_id",
            "aggregate_type",
            "aggregate_id",
            "local_mutation_id",
            "mutation_type",
            "outcome",
            "base_server_version",
            "current_server_version",
            "summary",
            "local_intent_summary",
            "server_state_summary",
        } <= columns

        indexes = {index["name"] for index in inspector.get_indexes("grocery_sync_conflicts")}
        assert {
            "ix_grocery_sync_conflicts_household_id",
            "ix_grocery_sync_conflicts_grocery_list_id",
            "ix_grocery_sync_conflicts_aggregate_id",
        } <= indexes

        migration.downgrade(connection)
        inspector = inspect(connection)
        assert "grocery_sync_conflicts" not in inspector.get_table_names()

    engine.dispose()
