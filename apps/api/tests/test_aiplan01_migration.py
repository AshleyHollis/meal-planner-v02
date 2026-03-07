from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from migrations.versions import rev_20260308_01_aiplan01_planner_seams as migration


def _create_legacy_schema(connection) -> None:
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
            updated_at DATETIME NOT NULL,
            confirmed_at DATETIME NULL,
            confirmation_client_mutation_id VARCHAR(128) NULL,
            ai_suggestion_request_id VARCHAR(36) NULL,
            stale_warning_acknowledged BOOLEAN NOT NULL DEFAULT 0,
            CONSTRAINT uq_meal_plan_confirmation_mutation
                UNIQUE (household_id, confirmation_client_mutation_id)
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_meal_plans_household_id ON meal_plans (household_id)")
    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slots (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            meal_plan_id VARCHAR(36) NOT NULL,
            day_of_week INTEGER NOT NULL,
            meal_type VARCHAR(32) NOT NULL,
            meal_title VARCHAR(255) NULL,
            meal_reference_id VARCHAR(36) NULL,
            slot_origin VARCHAR(32) NOT NULL,
            is_user_locked BOOLEAN NOT NULL DEFAULT 0,
            notes TEXT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id)
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
            prompt_family VARCHAR(128) NULL,
            prompt_version VARCHAR(64) NULL,
            fallback_mode BOOLEAN NULL,
            stale_warning_present_at_confirmation BOOLEAN NOT NULL DEFAULT 0,
            confirmed_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(meal_plan_slot_id) REFERENCES meal_plan_slots (id),
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_meal_plan_slot_history_meal_plan_slot_id ON meal_plan_slot_history (meal_plan_slot_id)"
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_requests (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            actor_id VARCHAR(36) NULL,
            plan_period_start DATE NOT NULL,
            plan_period_end DATE NOT NULL,
            target_slot_id VARCHAR(36) NULL,
            status VARCHAR(32) NOT NULL,
            request_idempotency_key VARCHAR(128) NOT NULL UNIQUE,
            prompt_family VARCHAR(128) NULL,
            prompt_version VARCHAR(64) NULL,
            policy_version VARCHAR(64) NULL,
            context_contract_version VARCHAR(64) NULL,
            result_contract_version VARCHAR(64) NULL,
            grounding_hash VARCHAR(128) NULL,
            created_at DATETIME NOT NULL,
            completed_at DATETIME NULL
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_ai_suggestion_requests_household_id ON ai_suggestion_requests (household_id)")
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
    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_slots (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            result_id VARCHAR(36) NOT NULL,
            day_of_week INTEGER NOT NULL,
            meal_type VARCHAR(32) NOT NULL,
            meal_title VARCHAR(255) NOT NULL,
            reason_codes TEXT NULL,
            explanation_entries TEXT NULL,
            uses_on_hand TEXT NULL,
            missing_hints TEXT NULL,
            is_fallback BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(result_id) REFERENCES ai_suggestion_results (id)
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_ai_suggestion_slots_result_id ON ai_suggestion_slots (result_id)")

    connection.execute(
        text(
            """
            INSERT INTO meal_plans (
                id, household_id, period_start, period_end, status, version,
                created_at, updated_at, confirmed_at, confirmation_client_mutation_id,
                ai_suggestion_request_id, stale_warning_acknowledged
            ) VALUES (
                'plan-001', 'hh-001', '2025-01-06', '2025-01-12', 'draft', 1,
                '2025-01-01T12:00:00', '2025-01-01T12:00:00', NULL, NULL,
                'req-001', 0
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO meal_plan_slots (
                id, meal_plan_id, day_of_week, meal_type, meal_title, meal_reference_id,
                slot_origin, is_user_locked, notes, created_at, updated_at
            ) VALUES (
                'slot-001', 'plan-001', 1, 'dinner', 'Pasta', NULL,
                'ai_suggested', 0, NULL, '2025-01-01T12:00:00', '2025-01-01T12:00:00'
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO ai_suggestion_requests (
                id, household_id, actor_id, plan_period_start, plan_period_end, target_slot_id,
                status, request_idempotency_key, prompt_family, prompt_version, policy_version,
                context_contract_version, result_contract_version, grounding_hash, created_at, completed_at
            ) VALUES (
                'req-001', 'hh-001', 'user-001', '2025-01-06', '2025-01-12', 'slot-001',
                'pending', 'idem-001', 'weekly-v1', 'v1.0', 'policy-v1',
                'ctx-v1', 'result-v1', 'grounding-001', '2025-01-01T12:00:00', NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO ai_suggestion_results (
                id, request_id, meal_plan_id, fallback_mode, stale_flag, result_contract_version, created_at
            ) VALUES (
                'result-001', 'req-001', 'plan-001', 0, 0, 'result-v1', '2025-01-01T12:01:00'
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO ai_suggestion_slots (
                id, result_id, day_of_week, meal_type, meal_title, reason_codes,
                explanation_entries, uses_on_hand, missing_hints, is_fallback, created_at
            ) VALUES (
                'ai-slot-001', 'result-001', 1, 'dinner', 'Pasta', '["uses_on_hand"]',
                '["Uses pantry staples"]', '["pasta"]', '["parmesan"]', 0, '2025-01-01T12:01:00'
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO meal_plan_slot_history (
                id, meal_plan_slot_id, meal_plan_id, slot_key, slot_origin,
                ai_suggestion_request_id, ai_suggestion_result_id, reason_codes,
                prompt_family, prompt_version, fallback_mode,
                stale_warning_present_at_confirmation, confirmed_at, created_at
            ) VALUES (
                'hist-001', 'slot-001', 'plan-001', '1:dinner', 'ai_suggested',
                'req-001', 'result-001', '["uses_on_hand"]',
                'weekly-v1', 'v1.0', 0, 0, '2025-01-01T12:05:00', '2025-01-01T12:05:00'
            )
            """
        )
    )
def test_aiplan01_migration_upgrade_and_downgrade():
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as connection:
        _create_legacy_schema(connection)
        migration.upgrade(connection)

        inspector = inspect(connection)
        meal_plan_columns = {column["name"] for column in inspector.get_columns("meal_plans")}
        meal_plan_slot_columns = {column["name"] for column in inspector.get_columns("meal_plan_slots")}
        request_columns = {column["name"] for column in inspector.get_columns("ai_suggestion_requests")}
        ai_slot_columns = {column["name"] for column in inspector.get_columns("ai_suggestion_slots")}
        history_columns = {column["name"] for column in inspector.get_columns("meal_plan_slot_history")}

        assert "ai_suggestion_result_id" in meal_plan_columns
        assert {"slot_key", "meal_summary", "regen_status", "pending_regen_request_id"} <= meal_plan_slot_columns
        assert {"meal_plan_id", "meal_plan_slot_id"} <= request_columns
        assert {"slot_key", "meal_summary"} <= ai_slot_columns
        assert "explanation_entries" in history_columns

        active_draft_indexes = {
            index["name"] for index in inspector.get_indexes("meal_plans")
        }
        assert "ix_meal_plans_active_draft_household_period" in active_draft_indexes

        upgraded_slot = connection.execute(
            text(
                "SELECT slot_key, regen_status FROM meal_plan_slots WHERE id = 'slot-001'"
            )
        ).one()
        assert upgraded_slot.slot_key == "1:dinner"
        assert upgraded_slot.regen_status == "idle"

        upgraded_request = connection.execute(
            text(
                "SELECT meal_plan_id, meal_plan_slot_id FROM ai_suggestion_requests WHERE id = 'req-001'"
            )
        ).one()
        assert upgraded_request.meal_plan_id is None
        assert upgraded_request.meal_plan_slot_id is None

        migration.downgrade(connection)

        inspector = inspect(connection)
        reverted_meal_plan_columns = {column["name"] for column in inspector.get_columns("meal_plans")}
        reverted_slot_columns = {column["name"] for column in inspector.get_columns("meal_plan_slots")}
        reverted_request_columns = {column["name"] for column in inspector.get_columns("ai_suggestion_requests")}

        assert "ai_suggestion_result_id" not in reverted_meal_plan_columns
        assert "slot_key" not in reverted_slot_columns
        assert "meal_plan_id" not in reverted_request_columns
        assert "ix_meal_plans_active_draft_household_period" not in {
            index["name"] for index in inspector.get_indexes("meal_plans")
        }

    engine.dispose()
