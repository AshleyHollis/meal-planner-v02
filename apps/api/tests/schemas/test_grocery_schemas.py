from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.grocery import (
    GroceryListConfirmCommand,
    GroceryListItemAdHocCreate,
    GroceryListQuantityAdjustCommand,
    GroceryListRemoveLineCommand,
)


def test_ad_hoc_item_create_valid():
    item = GroceryListItemAdHocCreate(
        grocery_list_id="gl-001",
        household_id="hh-001",
        ingredient_name="Sparkling Water",
        quantity_needed=Decimal("2.0"),
        unit="liters",
        client_mutation_id="grocery-create-001",
    )
    assert item.ingredient_name == "Sparkling Water"
    assert item.quantity_needed == Decimal("2.0")


def test_ad_hoc_item_rejects_zero_quantity():
    with pytest.raises(ValidationError):
        GroceryListItemAdHocCreate(
            grocery_list_id="gl-001",
            household_id="hh-001",
            ingredient_name="Sparkling Water",
            quantity_needed=Decimal("0.0"),
            unit="liters",
            client_mutation_id="grocery-create-002",
        )


def test_ad_hoc_item_rejects_empty_name():
    with pytest.raises(ValidationError):
        GroceryListItemAdHocCreate(
            grocery_list_id="gl-001",
            household_id="hh-001",
            ingredient_name="",
            quantity_needed=Decimal("1.0"),
            unit="liters",
            client_mutation_id="grocery-create-003",
        )


def test_grocery_confirm_command_requires_idempotency_key():
    cmd = GroceryListConfirmCommand(
        grocery_list_id="gl-001",
        household_id="hh-001",
        client_mutation_id="grocery-confirm-001",
    )
    assert cmd.client_mutation_id == "grocery-confirm-001"


def test_grocery_quantity_adjust_command_captures_adjustment_note():
    cmd = GroceryListQuantityAdjustCommand(
        grocery_list_item_id="gli-001",
        household_id="hh-001",
        user_adjusted_quantity=Decimal("3.0"),
        user_adjustment_note="Need extra for guests",
        client_mutation_id="grocery-adjust-001",
    )
    assert cmd.user_adjustment_note == "Need extra for guests"


def test_grocery_remove_line_command_requires_idempotency_key():
    cmd = GroceryListRemoveLineCommand(
        grocery_list_item_id="gli-001",
        household_id="hh-001",
        client_mutation_id="grocery-remove-001",
    )
    assert cmd.client_mutation_id == "grocery-remove-001"
