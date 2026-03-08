from __future__ import annotations

from sqlalchemy import Connection, inspect


revision = "20260308_01_aiplan01"
down_revision = None


def _has_column(connection: Connection, table_name: str, column_name: str) -> bool:
    inspector = inspect(connection)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _drop_index_if_exists(connection: Connection, index_name: str) -> None:
    connection.exec_driver_sql(f"DROP INDEX IF EXISTS {index_name}")


def upgrade(connection: Connection) -> None:
    if _has_column(connection, "meal_plans", "ai_suggestion_result_id"):
        return

    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plans_new (
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
            ai_suggestion_result_id VARCHAR(36) NULL,
            stale_warning_acknowledged BOOLEAN NOT NULL DEFAULT 0,
            CONSTRAINT uq_meal_plan_confirmation_mutation
                UNIQUE (household_id, confirmation_client_mutation_id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO meal_plans_new (
            id,
            household_id,
            period_start,
            period_end,
            status,
            version,
            created_at,
            updated_at,
            confirmed_at,
            confirmation_client_mutation_id,
            ai_suggestion_request_id,
            ai_suggestion_result_id,
            stale_warning_acknowledged
        )
        SELECT
            id,
            household_id,
            period_start,
            period_end,
            status,
            version,
            created_at,
            updated_at,
            confirmed_at,
            confirmation_client_mutation_id,
            ai_suggestion_request_id,
            NULL,
            stale_warning_acknowledged
        FROM meal_plans
        """
    )
    connection.exec_driver_sql("DROP TABLE meal_plans")
    connection.exec_driver_sql("ALTER TABLE meal_plans_new RENAME TO meal_plans")
    connection.exec_driver_sql(
        "CREATE UNIQUE INDEX ix_meal_plans_active_draft_household_period "
        "ON meal_plans (household_id, period_start, period_end) WHERE status = 'draft'"
    )
    connection.exec_driver_sql("CREATE INDEX ix_meal_plans_household_id ON meal_plans (household_id)")

    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slots_new (
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
            updated_at DATETIME NOT NULL,
            CONSTRAINT uq_meal_plan_slot_key UNIQUE (meal_plan_id, slot_key),
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO meal_plan_slots_new (
            id,
            meal_plan_id,
            slot_key,
            day_of_week,
            meal_type,
            meal_title,
            meal_summary,
            meal_reference_id,
            slot_origin,
            ai_suggestion_request_id,
            ai_suggestion_result_id,
            reason_codes,
            explanation_entries,
            prompt_family,
            prompt_version,
            fallback_mode,
            regen_status,
            pending_regen_request_id,
            is_user_locked,
            notes,
            created_at,
            updated_at
        )
        SELECT
            id,
            meal_plan_id,
            printf('%d:%s', day_of_week, meal_type),
            day_of_week,
            meal_type,
            meal_title,
            NULL,
            meal_reference_id,
            slot_origin,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            'idle',
            NULL,
            is_user_locked,
            notes,
            created_at,
            updated_at
        FROM meal_plan_slots
        """
    )
    connection.exec_driver_sql("DROP TABLE meal_plan_slots")
    connection.exec_driver_sql("ALTER TABLE meal_plan_slots_new RENAME TO meal_plan_slots")
    connection.exec_driver_sql("CREATE INDEX ix_meal_plan_slots_meal_plan_id ON meal_plan_slots (meal_plan_id)")

    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slot_history_new (
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
            created_at DATETIME NOT NULL,
            FOREIGN KEY(meal_plan_slot_id) REFERENCES meal_plan_slots (id),
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO meal_plan_slot_history_new (
            id,
            meal_plan_slot_id,
            meal_plan_id,
            slot_key,
            slot_origin,
            ai_suggestion_request_id,
            ai_suggestion_result_id,
            reason_codes,
            explanation_entries,
            prompt_family,
            prompt_version,
            fallback_mode,
            stale_warning_present_at_confirmation,
            confirmed_at,
            created_at
        )
        SELECT
            id,
            meal_plan_slot_id,
            meal_plan_id,
            slot_key,
            slot_origin,
            ai_suggestion_request_id,
            ai_suggestion_result_id,
            reason_codes,
            NULL,
            prompt_family,
            prompt_version,
            fallback_mode,
            stale_warning_present_at_confirmation,
            confirmed_at,
            created_at
        FROM meal_plan_slot_history
        """
    )
    connection.exec_driver_sql("DROP TABLE meal_plan_slot_history")
    connection.exec_driver_sql("ALTER TABLE meal_plan_slot_history_new RENAME TO meal_plan_slot_history")
    connection.exec_driver_sql(
        "CREATE INDEX ix_meal_plan_slot_history_meal_plan_slot_id ON meal_plan_slot_history (meal_plan_slot_id)"
    )

    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_requests_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            actor_id VARCHAR(36) NULL,
            plan_period_start DATE NOT NULL,
            plan_period_end DATE NOT NULL,
            target_slot_id VARCHAR(36) NULL,
            meal_plan_id VARCHAR(36) NULL,
            meal_plan_slot_id VARCHAR(36) NULL,
            status VARCHAR(32) NOT NULL,
            request_idempotency_key VARCHAR(128) NOT NULL,
            prompt_family VARCHAR(128) NULL,
            prompt_version VARCHAR(64) NULL,
            policy_version VARCHAR(64) NULL,
            context_contract_version VARCHAR(64) NULL,
            result_contract_version VARCHAR(64) NULL,
            grounding_hash VARCHAR(128) NULL,
            created_at DATETIME NOT NULL,
            completed_at DATETIME NULL,
            CONSTRAINT uq_ai_request_household_idempotency
                UNIQUE (household_id, request_idempotency_key),
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id),
            FOREIGN KEY(meal_plan_slot_id) REFERENCES meal_plan_slots (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO ai_suggestion_requests_new (
            id,
            household_id,
            actor_id,
            plan_period_start,
            plan_period_end,
            target_slot_id,
            meal_plan_id,
            meal_plan_slot_id,
            status,
            request_idempotency_key,
            prompt_family,
            prompt_version,
            policy_version,
            context_contract_version,
            result_contract_version,
            grounding_hash,
            created_at,
            completed_at
        )
        SELECT
            id,
            household_id,
            actor_id,
            plan_period_start,
            plan_period_end,
            target_slot_id,
            NULL,
            NULL,
            status,
            request_idempotency_key,
            prompt_family,
            prompt_version,
            policy_version,
            context_contract_version,
            result_contract_version,
            grounding_hash,
            created_at,
            completed_at
        FROM ai_suggestion_requests
        """
    )
    connection.exec_driver_sql("DROP TABLE ai_suggestion_requests")
    connection.exec_driver_sql("ALTER TABLE ai_suggestion_requests_new RENAME TO ai_suggestion_requests")
    connection.exec_driver_sql(
        "CREATE INDEX ix_ai_suggestion_requests_household_id ON ai_suggestion_requests (household_id)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_ai_suggestion_requests_meal_plan_id ON ai_suggestion_requests (meal_plan_id)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_ai_suggestion_requests_meal_plan_slot_id ON ai_suggestion_requests (meal_plan_slot_id)"
    )

    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_slots_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            result_id VARCHAR(36) NOT NULL,
            slot_key VARCHAR(64) NOT NULL,
            day_of_week INTEGER NOT NULL,
            meal_type VARCHAR(32) NOT NULL,
            meal_title VARCHAR(255) NOT NULL,
            meal_summary TEXT NULL,
            reason_codes TEXT NULL,
            explanation_entries TEXT NULL,
            uses_on_hand TEXT NULL,
            missing_hints TEXT NULL,
            is_fallback BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            CONSTRAINT uq_ai_suggestion_slot_result_key UNIQUE (result_id, slot_key),
            FOREIGN KEY(result_id) REFERENCES ai_suggestion_results (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO ai_suggestion_slots_new (
            id,
            result_id,
            slot_key,
            day_of_week,
            meal_type,
            meal_title,
            meal_summary,
            reason_codes,
            explanation_entries,
            uses_on_hand,
            missing_hints,
            is_fallback,
            created_at
        )
        SELECT
            id,
            result_id,
            printf('%d:%s', day_of_week, meal_type),
            day_of_week,
            meal_type,
            meal_title,
            NULL,
            reason_codes,
            explanation_entries,
            uses_on_hand,
            missing_hints,
            is_fallback,
            created_at
        FROM ai_suggestion_slots
        """
    )
    connection.exec_driver_sql("DROP TABLE ai_suggestion_slots")
    connection.exec_driver_sql("ALTER TABLE ai_suggestion_slots_new RENAME TO ai_suggestion_slots")
    connection.exec_driver_sql("CREATE INDEX ix_ai_suggestion_slots_result_id ON ai_suggestion_slots (result_id)")

    connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade(connection: Connection) -> None:
    if not _has_column(connection, "meal_plans", "ai_suggestion_result_id"):
        return

    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

    _drop_index_if_exists(connection, "ix_meal_plans_active_draft_household_period")
    _drop_index_if_exists(connection, "ix_meal_plans_household_id")

    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plans_old (
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
    connection.exec_driver_sql(
        """
        INSERT INTO meal_plans_old (
            id,
            household_id,
            period_start,
            period_end,
            status,
            version,
            created_at,
            updated_at,
            confirmed_at,
            confirmation_client_mutation_id,
            ai_suggestion_request_id,
            stale_warning_acknowledged
        )
        SELECT
            id,
            household_id,
            period_start,
            period_end,
            status,
            version,
            created_at,
            updated_at,
            confirmed_at,
            confirmation_client_mutation_id,
            ai_suggestion_request_id,
            stale_warning_acknowledged
        FROM meal_plans
        """
    )
    connection.exec_driver_sql("DROP TABLE meal_plans")
    connection.exec_driver_sql("ALTER TABLE meal_plans_old RENAME TO meal_plans")
    connection.exec_driver_sql("CREATE INDEX ix_meal_plans_household_id ON meal_plans (household_id)")

    _drop_index_if_exists(connection, "ix_meal_plan_slots_meal_plan_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slots_old (
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
    connection.exec_driver_sql(
        """
        INSERT INTO meal_plan_slots_old (
            id,
            meal_plan_id,
            day_of_week,
            meal_type,
            meal_title,
            meal_reference_id,
            slot_origin,
            is_user_locked,
            notes,
            created_at,
            updated_at
        )
        SELECT
            id,
            meal_plan_id,
            day_of_week,
            meal_type,
            meal_title,
            meal_reference_id,
            slot_origin,
            is_user_locked,
            notes,
            created_at,
            updated_at
        FROM meal_plan_slots
        """
    )
    connection.exec_driver_sql("DROP TABLE meal_plan_slots")
    connection.exec_driver_sql("ALTER TABLE meal_plan_slots_old RENAME TO meal_plan_slots")
    connection.exec_driver_sql("CREATE INDEX ix_meal_plan_slots_meal_plan_id ON meal_plan_slots (meal_plan_id)")

    _drop_index_if_exists(connection, "ix_meal_plan_slot_history_meal_plan_slot_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slot_history_old (
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
        """
        INSERT INTO meal_plan_slot_history_old (
            id,
            meal_plan_slot_id,
            meal_plan_id,
            slot_key,
            slot_origin,
            ai_suggestion_request_id,
            ai_suggestion_result_id,
            reason_codes,
            prompt_family,
            prompt_version,
            fallback_mode,
            stale_warning_present_at_confirmation,
            confirmed_at,
            created_at
        )
        SELECT
            id,
            meal_plan_slot_id,
            meal_plan_id,
            slot_key,
            slot_origin,
            ai_suggestion_request_id,
            ai_suggestion_result_id,
            reason_codes,
            prompt_family,
            prompt_version,
            fallback_mode,
            stale_warning_present_at_confirmation,
            confirmed_at,
            created_at
        FROM meal_plan_slot_history
        """
    )
    connection.exec_driver_sql("DROP TABLE meal_plan_slot_history")
    connection.exec_driver_sql("ALTER TABLE meal_plan_slot_history_old RENAME TO meal_plan_slot_history")
    connection.exec_driver_sql(
        "CREATE INDEX ix_meal_plan_slot_history_meal_plan_slot_id ON meal_plan_slot_history (meal_plan_slot_id)"
    )

    _drop_index_if_exists(connection, "ix_ai_suggestion_requests_household_id")
    _drop_index_if_exists(connection, "ix_ai_suggestion_requests_meal_plan_id")
    _drop_index_if_exists(connection, "ix_ai_suggestion_requests_meal_plan_slot_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_requests_old (
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
    connection.exec_driver_sql(
        """
        INSERT INTO ai_suggestion_requests_old (
            id,
            household_id,
            actor_id,
            plan_period_start,
            plan_period_end,
            target_slot_id,
            status,
            request_idempotency_key,
            prompt_family,
            prompt_version,
            policy_version,
            context_contract_version,
            result_contract_version,
            grounding_hash,
            created_at,
            completed_at
        )
        SELECT
            id,
            household_id,
            actor_id,
            plan_period_start,
            plan_period_end,
            target_slot_id,
            status,
            request_idempotency_key,
            prompt_family,
            prompt_version,
            policy_version,
            context_contract_version,
            result_contract_version,
            grounding_hash,
            created_at,
            completed_at
        FROM ai_suggestion_requests
        """
    )
    connection.exec_driver_sql("DROP TABLE ai_suggestion_requests")
    connection.exec_driver_sql("ALTER TABLE ai_suggestion_requests_old RENAME TO ai_suggestion_requests")
    connection.exec_driver_sql(
        "CREATE INDEX ix_ai_suggestion_requests_household_id ON ai_suggestion_requests (household_id)"
    )

    _drop_index_if_exists(connection, "ix_ai_suggestion_slots_result_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_slots_old (
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
    connection.exec_driver_sql(
        """
        INSERT INTO ai_suggestion_slots_old (
            id,
            result_id,
            day_of_week,
            meal_type,
            meal_title,
            reason_codes,
            explanation_entries,
            uses_on_hand,
            missing_hints,
            is_fallback,
            created_at
        )
        SELECT
            id,
            result_id,
            day_of_week,
            meal_type,
            meal_title,
            reason_codes,
            explanation_entries,
            uses_on_hand,
            missing_hints,
            is_fallback,
            created_at
        FROM ai_suggestion_slots
        """
    )
    connection.exec_driver_sql("DROP TABLE ai_suggestion_slots")
    connection.exec_driver_sql("ALTER TABLE ai_suggestion_slots_old RENAME TO ai_suggestion_slots")
    connection.exec_driver_sql("CREATE INDEX ix_ai_suggestion_slots_result_id ON ai_suggestion_slots (result_id)")

    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
