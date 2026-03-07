from __future__ import annotations


def _drop_index_if_exists(connection, index_name: str) -> None:
    indexes = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    ).fetchall()
    if indexes:
        connection.exec_driver_sql(f"DROP INDEX {index_name}")


def upgrade(connection) -> None:
    _drop_index_if_exists(connection, "ix_meal_plan_slots_meal_plan_id")
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
            fallback_mode VARCHAR(32) NULL,
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
        INSERT INTO meal_plan_slots_new
        SELECT
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
            CASE
                WHEN fallback_mode IS NULL THEN NULL
                WHEN fallback_mode = 1 THEN 'curated_fallback'
                ELSE 'none'
            END,
            regen_status,
            pending_regen_request_id,
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

    _drop_index_if_exists(connection, "ix_meal_plan_slot_history_meal_plan_slot_id")
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
            fallback_mode VARCHAR(32) NULL,
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
        INSERT INTO meal_plan_slot_history_new
        SELECT
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
            CASE
                WHEN fallback_mode IS NULL THEN NULL
                WHEN fallback_mode = 1 THEN 'curated_fallback'
                ELSE 'none'
            END,
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
        CREATE TABLE ai_suggestion_results_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            request_id VARCHAR(36) NOT NULL UNIQUE,
            meal_plan_id VARCHAR(36) NULL,
            fallback_mode VARCHAR(32) NOT NULL DEFAULT 'none',
            stale_flag BOOLEAN NOT NULL DEFAULT 0,
            result_contract_version VARCHAR(64) NULL,
            created_at DATETIME NOT NULL
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO ai_suggestion_results_new
        SELECT
            id,
            request_id,
            meal_plan_id,
            CASE
                WHEN fallback_mode = 1 THEN 'curated_fallback'
                ELSE 'none'
            END,
            stale_flag,
            result_contract_version,
            created_at
        FROM ai_suggestion_results
        """
    )
    connection.exec_driver_sql("DROP TABLE ai_suggestion_results")
    connection.exec_driver_sql("ALTER TABLE ai_suggestion_results_new RENAME TO ai_suggestion_results")


def downgrade(connection) -> None:
    _drop_index_if_exists(connection, "ix_meal_plan_slots_meal_plan_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE meal_plan_slots_old (
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
        INSERT INTO meal_plan_slots_old
        SELECT
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
            CASE
                WHEN fallback_mode IS NULL THEN NULL
                WHEN fallback_mode = 'none' THEN 0
                ELSE 1
            END,
            regen_status,
            pending_regen_request_id,
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
        INSERT INTO meal_plan_slot_history_old
        SELECT
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
            CASE
                WHEN fallback_mode IS NULL THEN NULL
                WHEN fallback_mode = 'none' THEN 0
                ELSE 1
            END,
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

    connection.exec_driver_sql(
        """
        CREATE TABLE ai_suggestion_results_old (
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
        INSERT INTO ai_suggestion_results_old
        SELECT
            id,
            request_id,
            meal_plan_id,
            CASE
                WHEN fallback_mode = 'none' THEN 0
                ELSE 1
            END,
            stale_flag,
            result_contract_version,
            created_at
        FROM ai_suggestion_results
        """
    )
    connection.exec_driver_sql("DROP TABLE ai_suggestion_results")
    connection.exec_driver_sql("ALTER TABLE ai_suggestion_results_old RENAME TO ai_suggestion_results")
