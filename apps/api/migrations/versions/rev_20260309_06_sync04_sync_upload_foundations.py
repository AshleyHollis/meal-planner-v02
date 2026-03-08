from __future__ import annotations

from sqlalchemy import inspect


def _table_exists(connection, table_name: str) -> bool:
    return table_name in inspect(connection).get_table_names()


def _drop_index_if_exists(connection, index_name: str) -> None:
    indexes = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    ).fetchall()
    if indexes:
        connection.exec_driver_sql(f"DROP INDEX {index_name}")


def upgrade(connection) -> None:
    if _table_exists(connection, "grocery_sync_conflicts"):
        return

    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_sync_conflicts (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            grocery_list_id VARCHAR(36) NOT NULL,
            aggregate_type VARCHAR(32) NOT NULL,
            aggregate_id VARCHAR(128) NOT NULL,
            local_mutation_id VARCHAR(128) NOT NULL,
            mutation_type VARCHAR(128) NOT NULL,
            outcome VARCHAR(64) NOT NULL,
            base_server_version INTEGER NULL,
            current_server_version INTEGER NOT NULL,
            requires_review BOOLEAN NOT NULL,
            summary TEXT NOT NULL,
            local_queue_status VARCHAR(32) NOT NULL,
            allowed_resolution_actions TEXT NULL,
            resolution_status VARCHAR(32) NOT NULL,
            local_intent_summary TEXT NULL,
            base_state_summary TEXT NULL,
            server_state_summary TEXT NULL,
            created_at DATETIME NOT NULL,
            resolved_at DATETIME NULL,
            resolved_by_actor_id VARCHAR(128) NULL,
            CONSTRAINT uq_grocery_sync_conflict_local_mutation UNIQUE (household_id, local_mutation_id),
            CONSTRAINT ck_grocery_sync_conflict_aggregate_type CHECK (
                aggregate_type IN ('grocery_list', 'grocery_line', 'inventory_item')
            ),
            CONSTRAINT ck_grocery_sync_conflict_outcome CHECK (
                outcome IN (
                    'duplicate_retry',
                    'auto_merged_non_overlapping',
                    'failed_retryable',
                    'review_required_quantity',
                    'review_required_deleted_or_archived',
                    'review_required_freshness_or_location',
                    'review_required_other_unsafe'
                )
            ),
            CONSTRAINT ck_grocery_sync_conflict_local_queue_status CHECK (
                local_queue_status IN (
                    'queued_offline',
                    'syncing',
                    'synced',
                    'retrying',
                    'failed_retryable',
                    'review_required',
                    'resolving',
                    'resolved_keep_mine',
                    'resolved_use_server'
                )
            ),
            CONSTRAINT ck_grocery_sync_conflict_resolution_status CHECK (
                resolution_status IN ('pending', 'resolved_keep_mine', 'resolved_use_server')
            ),
            CONSTRAINT ck_grocery_sync_conflict_base_server_version_positive CHECK (
                base_server_version IS NULL OR base_server_version >= 1
            ),
            CONSTRAINT ck_grocery_sync_conflict_current_server_version_positive CHECK (
                current_server_version >= 1
            ),
            FOREIGN KEY(household_id) REFERENCES households (id),
            FOREIGN KEY(grocery_list_id) REFERENCES grocery_lists (id)
        )
        """
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_sync_conflicts_household_id ON grocery_sync_conflicts (household_id)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_sync_conflicts_grocery_list_id ON grocery_sync_conflicts (grocery_list_id)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_sync_conflicts_aggregate_id ON grocery_sync_conflicts (aggregate_id)"
    )


def downgrade(connection) -> None:
    if not _table_exists(connection, "grocery_sync_conflicts"):
        return

    _drop_index_if_exists(connection, "ix_grocery_sync_conflicts_household_id")
    _drop_index_if_exists(connection, "ix_grocery_sync_conflicts_grocery_list_id")
    _drop_index_if_exists(connection, "ix_grocery_sync_conflicts_aggregate_id")
    connection.exec_driver_sql("DROP TABLE grocery_sync_conflicts")
