from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from migrations.versions import rev_20260308_05_groc08_groc09_confirmed_list_identity as migration


def _create_pre_groc08_schema(connection) -> None:
    connection.exec_driver_sql("CREATE TABLE households (id VARCHAR(36) NOT NULL PRIMARY KEY, name VARCHAR(255) NOT NULL)")
    connection.exec_driver_sql("CREATE TABLE grocery_lists (id VARCHAR(36) NOT NULL PRIMARY KEY)")
    connection.exec_driver_sql("CREATE TABLE grocery_list_versions (id VARCHAR(36) NOT NULL PRIMARY KEY)")
    connection.exec_driver_sql("CREATE TABLE inventory_items (id VARCHAR(36) NOT NULL PRIMARY KEY)")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_items (
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
            FOREIGN KEY(grocery_list_id) REFERENCES grocery_lists (id),
            FOREIGN KEY(grocery_list_version_id) REFERENCES grocery_list_versions (id),
            FOREIGN KEY(offset_inventory_item_id) REFERENCES inventory_items (id)
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_grocery_list_items_grocery_list_id ON grocery_list_items (grocery_list_id)")
    connection.exec_driver_sql(
        "CREATE INDEX ix_grocery_list_items_grocery_list_version_id ON grocery_list_items (grocery_list_version_id)"
    )
    connection.execute(text("INSERT INTO households (id, name) VALUES ('hh-001', 'Alpha Household')"))
    connection.execute(text("INSERT INTO grocery_lists (id) VALUES ('gl-001')"))
    connection.execute(text("INSERT INTO grocery_list_versions (id) VALUES ('glv-001')"))
    connection.execute(text("INSERT INTO inventory_items (id) VALUES ('inv-001')"))
    connection.execute(
        text(
            """
            INSERT INTO grocery_list_items (
                id, grocery_list_id, grocery_list_version_id, ingredient_name,
                ingredient_ref_id, required_quantity, unit, offset_quantity,
                offset_inventory_item_id, offset_inventory_item_version,
                shopping_quantity, origin, meal_sources, user_adjusted_quantity,
                user_adjustment_note, user_adjustment_flagged, ad_hoc_note,
                active, removed_at, is_purchased, created_client_mutation_id,
                removed_client_mutation_id, created_at, updated_at
            ) VALUES (
                'gli-001', 'gl-001', 'glv-001', 'Pasta',
                NULL, 500.0, 'grams', 200.0,
                'inv-001', 4, 300.0, 'derived', '[]', NULL,
                NULL, 0, NULL, 1, NULL, 0, NULL,
                NULL, '2025-01-01T12:00:00', '2025-01-01T12:05:00'
            )
            """
        )
    )


def test_groc08_groc09_identity_migration_upgrade_and_downgrade() -> None:
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as connection:
        _create_pre_groc08_schema(connection)
        migration.upgrade(connection)

        inspector = inspect(connection)
        item_columns = {column["name"] for column in inspector.get_columns("grocery_list_items")}
        assert "stable_line_id" in item_columns

        upgraded_item = connection.execute(
            text("SELECT id, stable_line_id FROM grocery_list_items WHERE id = 'gli-001'")
        ).one()
        assert upgraded_item.stable_line_id == upgraded_item.id

        index_names = {index["name"] for index in inspector.get_indexes("grocery_list_items")}
        assert "ix_grocery_list_items_stable_line_id" in index_names

        migration.downgrade(connection)

        inspector = inspect(connection)
        reverted_columns = {column["name"] for column in inspector.get_columns("grocery_list_items")}
        assert "stable_line_id" not in reverted_columns

    engine.dispose()
