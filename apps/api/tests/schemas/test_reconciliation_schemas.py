from decimal import Decimal

from app.schemas.reconciliation import ShoppingApplyCommand, CookingApplyCommand
from app.schemas.enums import ShoppingOutcome, CookingOutcome, StorageLocation


def test_shopping_apply_command_with_mixed_outcomes():
    cmd = ShoppingApplyCommand(
        household_id="hh-001",
        trip_session_id="trip-001",
        grocery_list_version_id="glv-001",
        source_grocery_list_version_number=3,
        client_apply_mutation_id="apply-001",
        rows=[
            {
                "item_name": "Milk",
                "planned_quantity": Decimal("2.0"),
                "planned_unit": "liters",
                "outcome": ShoppingOutcome.bought,
                "actual_quantity": Decimal("2.0"),
                "actual_unit": "liters",
                "inventory_item_version": 4,
            },
            {
                "item_name": "Bread",
                "planned_quantity": Decimal("1.0"),
                "planned_unit": "loaf",
                "outcome": ShoppingOutcome.not_purchased,
            },
            {
                "item_name": "Sparkling Water",
                "outcome": ShoppingOutcome.ad_hoc,
                "actual_quantity": Decimal("1.5"),
                "actual_unit": "liters",
                "storage_location": StorageLocation.pantry,
            },
        ],
    )
    assert len(cmd.rows) == 3
    assert cmd.source_grocery_list_version_number == 3
    assert cmd.rows[1].outcome == ShoppingOutcome.not_purchased
    assert cmd.rows[2].outcome == ShoppingOutcome.ad_hoc


def test_cooking_apply_command_with_leftovers():
    cmd = CookingApplyCommand(
        household_id="hh-001",
        meal_plan_slot_id="slot-001",
        expected_meal_plan_version=7,
        client_apply_mutation_id="cook-apply-001",
        ingredient_rows=[
            {
                "ingredient_name": "Pasta",
                "planned_quantity": Decimal("400.0"),
                "planned_unit": "grams",
                "outcome": CookingOutcome.used_adjusted,
                "actual_quantity": Decimal("350.0"),
                "actual_unit": "grams",
                "inventory_item_version": 2,
            },
            {
                "ingredient_name": "Sauce",
                "planned_quantity": Decimal("1.0"),
                "planned_unit": "jar",
                "outcome": CookingOutcome.skipped,
            },
        ],
        leftover_rows=[
            {
                "display_name": "Leftover Pasta",
                "quantity": Decimal("2.0"),
                "unit": "servings",
                "storage_location": StorageLocation.fridge,
                "target_inventory_item_id": "inv-leftovers-001",
                "target_inventory_item_version": 5,
            }
        ],
    )
    assert len(cmd.ingredient_rows) == 2
    assert len(cmd.leftover_rows) == 1
    assert cmd.expected_meal_plan_version == 7
    assert cmd.leftover_rows[0].display_name == "Leftover Pasta"
    assert cmd.leftover_rows[0].target_inventory_item_id == "inv-leftovers-001"
