from __future__ import annotations

from sqlalchemy import inspect


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspect(connection).get_columns(table_name))


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
    if _column_exists(connection, "grocery_lists", "confirmation_client_mutation_id") and _table_exists(
        connection, "grocery_mutation_receipts"
    ):
        return

    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

    _drop_index_if_exists(connection, "ix_grocery_lists_household_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_lists_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            meal_plan_id VARCHAR(36) NULL,
            status VARCHAR(32) NOT NULL,
            current_version_number INTEGER NOT NULL,
            confirmed_at DATETIME NULL,
            confirmation_client_mutation_id VARCHAR(128) NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT ck_grocery_list_current_version_positive CHECK (current_version_number >= 1),
            CONSTRAINT ck_grocery_list_status CHECK (
                status IN (
                    'no_plan_confirmed',
                    'deriving',
                    'draft',
                    'stale_draft',
                    'confirming',
                    'confirmed',
                    'trip_in_progress',
                    'trip_complete_pending_reconciliation'
                )
            ),
            CONSTRAINT uq_grocery_list_confirmation_mutation
                UNIQUE (household_id, confirmation_client_mutation_id),
            FOREIGN KEY(household_id) REFERENCES households (id),
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO grocery_lists_new (
            id, household_id, meal_plan_id, status, current_version_number,
            confirmed_at, confirmation_client_mutation_id, created_at, updated_at
        )
        SELECT
            id, household_id, meal_plan_id, status, current_version_number,
            confirmed_at, NULL, created_at, updated_at
        FROM grocery_lists
        """
    )
    connection.exec_driver_sql("DROP TABLE grocery_lists")
    connection.exec_driver_sql("ALTER TABLE grocery_lists_new RENAME TO grocery_lists")
    connection.exec_driver_sql("CREATE INDEX ix_grocery_lists_household_id ON grocery_lists (household_id)")

    _drop_index_if_exists(connection, "ix_grocery_list_versions_grocery_list_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_versions_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            grocery_list_id VARCHAR(36) NOT NULL,
            version_number INTEGER NOT NULL,
            plan_period_reference VARCHAR(64) NULL,
            confirmed_plan_id VARCHAR(36) NULL,
            derived_at DATETIME NOT NULL,
            confirmed_plan_version INTEGER NULL,
            inventory_snapshot_reference VARCHAR(128) NULL,
            invalidated_at DATETIME NULL,
            incomplete_slot_warnings TEXT NULL,
            CONSTRAINT ck_grocery_list_version_positive CHECK (version_number >= 1),
            CONSTRAINT uq_grocery_list_version_number UNIQUE (grocery_list_id, version_number),
            FOREIGN KEY(grocery_list_id) REFERENCES grocery_lists (id),
            FOREIGN KEY(confirmed_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO grocery_list_versions_new (
            id, grocery_list_id, version_number, plan_period_reference,
            confirmed_plan_id, derived_at, confirmed_plan_version,
            inventory_snapshot_reference, invalidated_at, incomplete_slot_warnings
        )
        SELECT
            id, grocery_list_id, version_number, plan_period_reference,
            confirmed_plan_id, derived_at, source_plan_version,
            inventory_snapshot_reference, invalidated_at, NULL
        FROM grocery_list_versions
        """
    )
    connection.exec_driver_sql("DROP TABLE grocery_list_versions")
    connection.exec_driver_sql("ALTER TABLE grocery_list_versions_new RENAME TO grocery_list_versions")
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_list_versions_grocery_list_id ON grocery_list_versions (grocery_list_id)"
    )

    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_id")
    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_version_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_items_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            grocery_list_id VARCHAR(36) NOT NULL,
            grocery_list_version_id VARCHAR(36) NULL,
            ingredient_name VARCHAR(255) NOT NULL,
            ingredient_ref_id VARCHAR(36) NULL,
            required_quantity NUMERIC(14, 4) NOT NULL,
            unit VARCHAR(64) NOT NULL,
            offset_quantity NUMERIC(14, 4) NOT NULL,
            offset_inventory_item_id VARCHAR(36) NULL,
            offset_inventory_item_version INTEGER NULL,
            shopping_quantity NUMERIC(14, 4) NOT NULL,
            origin VARCHAR(32) NOT NULL,
            meal_sources TEXT NULL,
            user_adjusted_quantity NUMERIC(14, 4) NULL,
            user_adjustment_note TEXT NULL,
            user_adjustment_flagged BOOLEAN NOT NULL,
            ad_hoc_note TEXT NULL,
            active BOOLEAN NOT NULL,
            removed_at DATETIME NULL,
            is_purchased BOOLEAN NOT NULL,
            created_client_mutation_id VARCHAR(128) NULL,
            removed_client_mutation_id VARCHAR(128) NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT ck_grocery_list_item_required_positive CHECK (required_quantity > 0),
            CONSTRAINT ck_grocery_list_item_offset_non_negative CHECK (offset_quantity >= 0),
            CONSTRAINT ck_grocery_list_item_shopping_non_negative CHECK (shopping_quantity >= 0),
            CONSTRAINT ck_grocery_list_item_user_adjusted_positive CHECK (
                user_adjusted_quantity IS NULL OR user_adjusted_quantity > 0
            ),
            CONSTRAINT ck_grocery_list_item_origin CHECK (origin IN ('derived', 'ad_hoc')),
            CONSTRAINT ck_grocery_list_item_removed_requires_inactive CHECK (
                removed_at IS NULL OR active = 0
            ),
            FOREIGN KEY(grocery_list_id) REFERENCES grocery_lists (id),
            FOREIGN KEY(grocery_list_version_id) REFERENCES grocery_list_versions (id),
            FOREIGN KEY(offset_inventory_item_id) REFERENCES inventory_items (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO grocery_list_items_new (
            id, grocery_list_id, grocery_list_version_id, ingredient_name,
            ingredient_ref_id, required_quantity, unit, offset_quantity,
            offset_inventory_item_id, offset_inventory_item_version,
            shopping_quantity, origin, meal_sources, user_adjusted_quantity,
            user_adjustment_note, user_adjustment_flagged, ad_hoc_note,
            active, removed_at, is_purchased, created_client_mutation_id,
            removed_client_mutation_id, created_at, updated_at
        )
        SELECT
            id, grocery_list_id, grocery_list_version_id, ingredient_name,
            ingredient_ref_id, quantity_needed, unit, quantity_offset,
            offset_inventory_item_id, NULL,
            quantity_to_buy, origin, meal_sources, user_adjusted_quantity,
            user_adjustment_note, user_adjustment_flagged, ad_hoc_note,
            is_active, NULL, is_purchased, NULL,
            NULL, created_at, updated_at
        FROM grocery_list_items
        """
    )
    connection.exec_driver_sql("DROP TABLE grocery_list_items")
    connection.exec_driver_sql("ALTER TABLE grocery_list_items_new RENAME TO grocery_list_items")
    connection.exec_driver_sql("CREATE INDEX ix_grocery_list_items_grocery_list_id ON grocery_list_items (grocery_list_id)")
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_list_items_grocery_list_version_id ON grocery_list_items (grocery_list_version_id)"
    )

    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_mutation_receipts (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            grocery_list_id VARCHAR(36) NOT NULL,
            grocery_list_item_id VARCHAR(36) NULL,
            client_mutation_id VARCHAR(128) NOT NULL,
            mutation_kind VARCHAR(64) NOT NULL,
            accepted_at DATETIME NOT NULL,
            result_summary TEXT NULL,
            CONSTRAINT uq_grocery_mutation_receipt UNIQUE (household_id, client_mutation_id),
            FOREIGN KEY(household_id) REFERENCES households (id),
            FOREIGN KEY(grocery_list_id) REFERENCES grocery_lists (id),
            FOREIGN KEY(grocery_list_item_id) REFERENCES grocery_list_items (id)
        )
        """
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_mutation_receipts_household_id ON grocery_mutation_receipts (household_id)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_mutation_receipts_grocery_list_id ON grocery_mutation_receipts (grocery_list_id)"
    )

    connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade(connection) -> None:
    if not _column_exists(connection, "grocery_lists", "confirmation_client_mutation_id"):
        return

    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

    _drop_index_if_exists(connection, "ix_grocery_mutation_receipts_household_id")
    _drop_index_if_exists(connection, "ix_grocery_mutation_receipts_grocery_list_id")
    if _table_exists(connection, "grocery_mutation_receipts"):
        connection.exec_driver_sql("DROP TABLE grocery_mutation_receipts")

    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_id")
    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_version_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_items_old (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            grocery_list_id VARCHAR(36) NOT NULL,
            grocery_list_version_id VARCHAR(36) NULL,
            ingredient_name VARCHAR(255) NOT NULL,
            ingredient_ref_id VARCHAR(36) NULL,
            quantity_needed NUMERIC(14, 4) NOT NULL,
            unit VARCHAR(64) NOT NULL,
            quantity_offset NUMERIC(14, 4) NOT NULL,
            offset_inventory_item_id VARCHAR(36) NULL,
            quantity_to_buy NUMERIC(14, 4) NOT NULL,
            origin VARCHAR(32) NOT NULL,
            meal_sources TEXT NULL,
            user_adjusted_quantity NUMERIC(14, 4) NULL,
            user_adjustment_note TEXT NULL,
            user_adjustment_flagged BOOLEAN NOT NULL,
            ad_hoc_note TEXT NULL,
            is_active BOOLEAN NOT NULL,
            is_purchased BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(grocery_list_id) REFERENCES grocery_lists (id),
            FOREIGN KEY(grocery_list_version_id) REFERENCES grocery_list_versions (id),
            FOREIGN KEY(offset_inventory_item_id) REFERENCES inventory_items (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO grocery_list_items_old (
            id, grocery_list_id, grocery_list_version_id, ingredient_name,
            ingredient_ref_id, quantity_needed, unit, quantity_offset,
            offset_inventory_item_id, quantity_to_buy, origin, meal_sources,
            user_adjusted_quantity, user_adjustment_note, user_adjustment_flagged,
            ad_hoc_note, is_active, is_purchased, created_at, updated_at
        )
        SELECT
            id, grocery_list_id, grocery_list_version_id, ingredient_name,
            ingredient_ref_id, required_quantity, unit, offset_quantity,
            offset_inventory_item_id, shopping_quantity, origin, meal_sources,
            user_adjusted_quantity, user_adjustment_note, user_adjustment_flagged,
            ad_hoc_note, active, is_purchased, created_at, updated_at
        FROM grocery_list_items
        """
    )
    connection.exec_driver_sql("DROP TABLE grocery_list_items")
    connection.exec_driver_sql("ALTER TABLE grocery_list_items_old RENAME TO grocery_list_items")
    connection.exec_driver_sql("CREATE INDEX ix_grocery_list_items_grocery_list_id ON grocery_list_items (grocery_list_id)")

    _drop_index_if_exists(connection, "ix_grocery_list_versions_grocery_list_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_versions_old (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            grocery_list_id VARCHAR(36) NOT NULL,
            version_number INTEGER NOT NULL,
            plan_period_reference VARCHAR(64) NULL,
            confirmed_plan_id VARCHAR(36) NULL,
            derived_at DATETIME NOT NULL,
            source_plan_version INTEGER NULL,
            inventory_snapshot_reference VARCHAR(128) NULL,
            invalidated_at DATETIME NULL,
            FOREIGN KEY(grocery_list_id) REFERENCES grocery_lists (id),
            FOREIGN KEY(confirmed_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO grocery_list_versions_old (
            id, grocery_list_id, version_number, plan_period_reference,
            confirmed_plan_id, derived_at, source_plan_version,
            inventory_snapshot_reference, invalidated_at
        )
        SELECT
            id, grocery_list_id, version_number, plan_period_reference,
            confirmed_plan_id, derived_at, confirmed_plan_version,
            inventory_snapshot_reference, invalidated_at
        FROM grocery_list_versions
        """
    )
    connection.exec_driver_sql("DROP TABLE grocery_list_versions")
    connection.exec_driver_sql("ALTER TABLE grocery_list_versions_old RENAME TO grocery_list_versions")
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_list_versions_grocery_list_id ON grocery_list_versions (grocery_list_id)"
    )

    _drop_index_if_exists(connection, "ix_grocery_lists_household_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_lists_old (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            household_id VARCHAR(36) NOT NULL,
            meal_plan_id VARCHAR(36) NULL,
            status VARCHAR(32) NOT NULL,
            current_version_number INTEGER NOT NULL,
            confirmed_at DATETIME NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans (id)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO grocery_lists_old (
            id, household_id, meal_plan_id, status, current_version_number,
            confirmed_at, created_at, updated_at
        )
        SELECT
            id, household_id, meal_plan_id, status, current_version_number,
            confirmed_at, created_at, updated_at
        FROM grocery_lists
        """
    )
    connection.exec_driver_sql("DROP TABLE grocery_lists")
    connection.exec_driver_sql("ALTER TABLE grocery_lists_old RENAME TO grocery_lists")
    connection.exec_driver_sql("CREATE INDEX ix_grocery_lists_household_id ON grocery_lists (household_id)")

    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
