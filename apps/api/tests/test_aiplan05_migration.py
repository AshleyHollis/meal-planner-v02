from sqlalchemy import create_engine, inspect, text

from migrations.versions import rev_20260308_03_aiplan05_planner_events as migration


def _create_pre_aiplan05_schema(connection) -> None:
    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plans (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            status VARCHAR(32) NOT NULL,
            version INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.execute(
        text(
            """
            INSERT INTO meal_plans (
                id, household_id, period_start, period_end, status, version, created_at, updated_at
            ) VALUES (
                'plan-001', 'hh-001', '2026-03-09', '2026-03-15', 'confirmed', 2,
                '2026-03-08T10:00:00', '2026-03-08T10:05:00'
            )
            """
        )
    )


def test_aiplan05_planner_events_migration_round_trips() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        _create_pre_aiplan05_schema(connection)

        migration.upgrade(connection)
        inspector = inspect(connection)
        assert "planner_events" in inspector.get_table_names()
        event_columns = {column["name"] for column in inspector.get_columns("planner_events")}
        assert {"event_type", "source_mutation_id", "payload", "occurred_at", "published_at"} <= event_columns

        connection.execute(
            text(
                """
                INSERT INTO planner_events (
                    id, household_id, meal_plan_id, event_type, source_mutation_id, payload, occurred_at
                ) VALUES (
                    'evt-001', 'hh-001', 'plan-001', 'plan_confirmed', 'confirm-001',
                    '{"event_type":"plan_confirmed"}', '2026-03-08T10:06:00'
                )
                """
            )
        )
        persisted = connection.execute(
            text("SELECT event_type, source_mutation_id FROM planner_events WHERE id = 'evt-001'")
        ).one()
        assert persisted.event_type == "plan_confirmed"
        assert persisted.source_mutation_id == "confirm-001"

        migration.downgrade(connection)
        assert "planner_events" not in inspect(connection).get_table_names()

    engine.dispose()
