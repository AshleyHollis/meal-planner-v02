from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from migrations.versions import rev_20260308_02_aiplan04_fallback_modes as migration


def _create_pre_aiplan04_schema(connection) -> None:
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
    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slots (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            meal_plan_id VARCHAR(36) NOT NULL,
            slot_key VARCHAR(64) NOT NULL,
            day_of_week INTEGER NOT NULL,
            meal_type VARCHAR(32) NOT NULL,
            meal_title VARCHAR(255) NULL,
            meal_summary TEXT NULL,
            meal_reference_id VARCHAR(36) NULL,
            slot_origin VARCHAR(32) NOT NULL,
            ai_suggestion_request_id VARCHAR(36) NULL,
            ai_suggestion_result_id VARCHAR(36) NULL,
            reason_codes TEXT NULL,
            explanation_entries TEXT NULL,
            prompt_family VARCHAR(128) NULL,
            prompt_version VARCHAR(64) NULL,
            fallback_mode BOOLEAN NULL,
            regen_status VARCHAR(32) NOT NULL DEFAULT 'idle',
            pending_regen_request_id VARCHAR(36) NULL,
            is_user_locked BOOLEAN NOT NULL DEFAULT 0,
            notes TEXT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_meal_plan_slots_meal_plan_id ON meal_plan_slots (meal_plan_id)")
    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slot_history (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            meal_plan_slot_id VARCHAR(36) NOT NULL,
            meal_plan_id VARCHAR(36) NOT NULL,
            slot_key VARCHAR(64) NOT NULL,
            slot_origin VARCHAR(32) NOT NULL,
            ai_suggestion_request_id VARCHAR(36) NULL,
            ai_suggestion_result_id VARCHAR(36) NULL,
            reason_codes TEXT NULL,
            explanation_entries TEXT NULL,
            prompt_family VARCHAR(128) NULL,
            prompt_version VARCHAR(64) NULL,
            fallback_mode BOOLEAN NULL,
            stale_warning_present_at_confirmation BOOLEAN NOT NULL DEFAULT 0,
            confirmed_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_meal_plan_slot_history_meal_plan_slot_id ON meal_plan_slot_history (meal_plan_slot_id)"
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_results (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            request_id VARCHAR(36) NOT NULL UNIQUE,
            meal_plan_id VARCHAR(36) NULL,
            fallback_mode BOOLEAN NOT NULL DEFAULT 0,
            stale_flag BOOLEAN NOT NULL DEFAULT 0,
            result_contract_version VARCHAR(64) NULL,
            created_at DATETIME NOT NULL
        )
        """
    )
    connection.execute(
        text(
            """
            INSERT INTO meal_plans (id, household_id, period_start, period_end, status, version, created_at, updated_at)
            VALUES ('plan-001', 'hh-001', '2026-03-09', '2026-03-15', 'draft', 1, '2026-03-01T12:00:00', '2026-03-01T12:00:00')
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO meal_plan_slots (
                id, meal_plan_id, slot_key, day_of_week, meal_type, meal_title, meal_summary, slot_origin,
                fallback_mode, regen_status, created_at, updated_at
            ) VALUES (
                'slot-001', 'plan-001', '0:dinner', 0, 'dinner', 'Fallback Dinner', 'Summary',
                'ai_suggested', 1, 'idle', '2026-03-01T12:00:00', '2026-03-01T12:00:00'
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO meal_plan_slot_history (
                id, meal_plan_slot_id, meal_plan_id, slot_key, slot_origin, fallback_mode,
                stale_warning_present_at_confirmation, confirmed_at, created_at
            ) VALUES (
                'hist-001', 'slot-001', 'plan-001', '0:dinner', 'ai_suggested', 1, 0,
                '2026-03-01T12:05:00', '2026-03-01T12:05:00'
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO ai_suggestion_results (id, request_id, meal_plan_id, fallback_mode, stale_flag, result_contract_version, created_at)
            VALUES ('result-001', 'req-001', 'plan-001', 1, 0, '1.0.0', '2026-03-01T12:00:00')
            """
        )
    )


def test_aiplan04_fallback_mode_migration_round_trips() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        _create_pre_aiplan04_schema(connection)

        migration.upgrade(connection)
        inspector = inspect(connection)
        result_column = next(
            column for column in inspector.get_columns("ai_suggestion_results") if column["name"] == "fallback_mode"
        )
        assert "VARCHAR" in str(result_column["type"]).upper()
        upgraded = connection.execute(
            text(
                """
                SELECT
                    (SELECT fallback_mode FROM ai_suggestion_results WHERE id = 'result-001') AS result_mode,
                    (SELECT fallback_mode FROM meal_plan_slots WHERE id = 'slot-001') AS slot_mode,
                    (SELECT fallback_mode FROM meal_plan_slot_history WHERE id = 'hist-001') AS history_mode
                """
            )
        ).one()
        assert upgraded.result_mode == "curated_fallback"
        assert upgraded.slot_mode == "curated_fallback"
        assert upgraded.history_mode == "curated_fallback"

        migration.downgrade(connection)
        reverted = connection.execute(
            text(
                """
                SELECT
                    (SELECT fallback_mode FROM ai_suggestion_results WHERE id = 'result-001') AS result_mode,
                    (SELECT fallback_mode FROM meal_plan_slots WHERE id = 'slot-001') AS slot_mode,
                    (SELECT fallback_mode FROM meal_plan_slot_history WHERE id = 'hist-001') AS history_mode
                """
            )
        ).one()
        assert reverted.result_mode == 1
        assert reverted.slot_mode == 1
        assert reverted.history_mode == 1

    engine.dispose()
