from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from migrations.versions import rev_20260308_04_groc01_grocery_schema_seams as migration


def _create_legacy_schema(connection) -> None:
    connection.exec_driver_sql("CREATE TABLE households (id VARCHAR(36) NOT NULL PRIMARY KEY, name VARCHAR(255) NOT NULL)")
    connection.exec_driver_sql("CREATE TABLE meal_plans (id VARCHAR(36) NOT NULL PRIMARY KEY)")
    connection.exec_driver_sql("CREATE TABLE inventory_items (id VARCHAR(36) NOT NULL PRIMARY KEY)")

    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_lists (
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
    connection.exec_driver_sql("CREATE INDEX ix_grocery_lists_household_id ON grocery_lists (household_id)")
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_versions (
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
        "CREATE INDEX ix_grocery_list_versions_grocery_list_id ON grocery_list_versions (grocery_list_id)"
    )
    connection.exec_driver_sql(
        """
        CREATE TABLE grocery_list_items (
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
    connection.exec_driver_sql("CREATE INDEX ix_grocery_list_items_grocery_list_id ON grocery_list_items (grocery_list_id)")

    connection.execute(text("INSERT INTO households (id, name) VALUES ('hh-001', 'Alpha Household')"))
    connection.execute(text("INSERT INTO meal_plans (id) VALUES ('plan-001')"))
    connection.execute(text("INSERT INTO inventory_items (id) VALUES ('inv-001')"))
    connection.execute(
        text(
            """
            INSERT INTO grocery_lists (
                id, household_id, meal_plan_id, status, current_version_number,
                confirmed_at, created_at, updated_at
            ) VALUES (
                'gl-001', 'hh-001', 'plan-001', 'draft', 1,
                NULL, '2025-01-01T12:00:00', '2025-01-01T12:05:00'
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO grocery_list_versions (
                id, grocery_list_id, version_number, plan_period_reference,
                confirmed_plan_id, derived_at, source_plan_version,
                inventory_snapshot_reference, invalidated_at
            ) VALUES (
                'glv-001', 'gl-001', 1, '2025-01-06/2025-01-12',
                'plan-001', '2025-01-01T12:00:00', 3,
                'inventory-v4', NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO grocery_list_items (
                id, grocery_list_id, grocery_list_version_id, ingredient_name,
                ingredient_ref_id, quantity_needed, unit, quantity_offset,
                offset_inventory_item_id, quantity_to_buy, origin, meal_sources,
                user_adjusted_quantity, user_adjustment_note, user_adjustment_flagged,
                ad_hoc_note, is_active, is_purchased, created_at, updated_at
            ) VALUES (
                'gli-001', 'gl-001', 'glv-001', 'Pasta',
                NULL, 500.0, 'grams', 200.0,
                'inv-001', 300.0, 'derived', '[{"meal_plan_slot_id": "slot-001", "quantity": 500.0}]',
                NULL, NULL, 0,
                NULL, 1, 0, '2025-01-01T12:00:00', '2025-01-01T12:05:00'
            )
            """
        )
    )


def test_groc01_migration_upgrade_and_downgrade():
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as connection:
        _create_legacy_schema(connection)
        migration.upgrade(connection)

        inspector = inspect(connection)
        grocery_list_columns = {column["name"] for column in inspector.get_columns("grocery_lists")}
        version_columns = {column["name"] for column in inspector.get_columns("grocery_list_versions")}
        item_columns = {column["name"] for column in inspector.get_columns("grocery_list_items")}

        assert "confirmation_client_mutation_id" in grocery_list_columns
        assert {"confirmed_plan_version", "incomplete_slot_warnings"} <= version_columns
        assert {
            "required_quantity",
            "offset_inventory_item_version",
            "shopping_quantity",
            "active",
            "removed_at",
            "created_client_mutation_id",
            "removed_client_mutation_id",
        } <= item_columns
        assert "grocery_mutation_receipts" in inspector.get_table_names()

        upgraded_item = connection.execute(
            text(
                "SELECT required_quantity, offset_quantity, shopping_quantity, active FROM grocery_list_items WHERE id = 'gli-001'"
            )
        ).one()
        assert float(upgraded_item.required_quantity) == 500.0
        assert float(upgraded_item.offset_quantity) == 200.0
        assert float(upgraded_item.shopping_quantity) == 300.0
        assert upgraded_item.active == 1

        upgraded_version = connection.execute(
            text(
                "SELECT confirmed_plan_version, incomplete_slot_warnings FROM grocery_list_versions WHERE id = 'glv-001'"
            )
        ).one()
        assert upgraded_version.confirmed_plan_version == 3
        assert upgraded_version.incomplete_slot_warnings is None

        migration.downgrade(connection)

        inspector = inspect(connection)
        reverted_grocery_list_columns = {column["name"] for column in inspector.get_columns("grocery_lists")}
        reverted_version_columns = {column["name"] for column in inspector.get_columns("grocery_list_versions")}
        reverted_item_columns = {column["name"] for column in inspector.get_columns("grocery_list_items")}

        assert "confirmation_client_mutation_id" not in reverted_grocery_list_columns
        assert "confirmed_plan_version" not in reverted_version_columns
        assert "required_quantity" not in reverted_item_columns
        assert "quantity_needed" in reverted_item_columns
        assert "grocery_mutation_receipts" not in inspector.get_table_names()

    engine.dispose()
