from __future__ import annotations

from sqlalchemy import inspect


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspect(connection).get_columns(table_name))


def _drop_index_if_exists(connection, index_name: str) -> None:
    indexes = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    ).fetchall()
    if indexes:
        connection.exec_driver_sql(f"DROP INDEX {index_name}")


def upgrade(connection) -> None:
    if _column_exists(connection, "grocery_list_items", "stable_line_id"):
        return

    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_id")
    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_version_id")
    _drop_index_if_exists(connection, "ix_grocery_list_items_stable_line_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_items_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            stable_line_id VARCHAR(36) NOT NULL,
            grocery_list_id VARCHAR(36) NOT NULL,
            grocery_list_version_id VARCHAR(36) NOT NULL,
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
            id, stable_line_id, grocery_list_id, grocery_list_version_id, ingredient_name,
            ingredient_ref_id, required_quantity, unit, offset_quantity,
            offset_inventory_item_id, offset_inventory_item_version,
            shopping_quantity, origin, meal_sources, user_adjusted_quantity,
            user_adjustment_note, user_adjustment_flagged, ad_hoc_note,
            active, removed_at, is_purchased, created_client_mutation_id,
            removed_client_mutation_id, created_at, updated_at
        )
        SELECT
            id, id, grocery_list_id, grocery_list_version_id, ingredient_name,
            ingredient_ref_id, required_quantity, unit, offset_quantity,
            offset_inventory_item_id, offset_inventory_item_version,
            shopping_quantity, origin, meal_sources, user_adjusted_quantity,
            user_adjustment_note, user_adjustment_flagged, ad_hoc_note,
            active, removed_at, is_purchased, created_client_mutation_id,
            removed_client_mutation_id, created_at, updated_at
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
        "CREATE INDEX ix_grocery_list_items_stable_line_id ON grocery_list_items (stable_line_id)"
    )

    connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade(connection) -> None:
    if not _column_exists(connection, "grocery_list_items", "stable_line_id"):
        return

    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_id")
    _drop_index_if_exists(connection, "ix_grocery_list_items_grocery_list_version_id")
    _drop_index_if_exists(connection, "ix_grocery_list_items_stable_line_id")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_items_old (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            grocery_list_id VARCHAR(36) NOT NULL,
            grocery_list_version_id VARCHAR(36) NOT NULL,
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
        INSERT INTO grocery_list_items_old (
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
            ingredient_ref_id, required_quantity, unit, offset_quantity,
            offset_inventory_item_id, offset_inventory_item_version,
            shopping_quantity, origin, meal_sources, user_adjusted_quantity,
            user_adjustment_note, user_adjustment_flagged, ad_hoc_note,
            active, removed_at, is_purchased, created_client_mutation_id,
            removed_client_mutation_id, created_at, updated_at
        FROM grocery_list_items
        """
    )
    connection.exec_driver_sql("DROP TABLE grocery_list_items")
    connection.exec_driver_sql("ALTER TABLE grocery_list_items_old RENAME TO grocery_list_items")
    connection.exec_driver_sql("CREATE INDEX ix_grocery_list_items_grocery_list_id ON grocery_list_items (grocery_list_id)")
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_list_items_grocery_list_version_id ON grocery_list_items (grocery_list_version_id)"
    )

    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
