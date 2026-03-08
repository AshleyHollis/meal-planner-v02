from datetime import date, datetime
from decimal import Decimal

from app.models.household import Household
from app.models.inventory import InventoryAdjustment, InventoryItem
from app.models.reconciliation import (
    ShoppingReconciliation,
    ShoppingReconciliationRow,
    CookingEvent,
    CookingIngredientRow,
    LeftoverRow,
)

HOUSEHOLD = "hh-001"


def add_household(db_session, household_id: str = HOUSEHOLD) -> Household:
    household = db_session.get(Household, household_id)
    if household is None:
        household = Household(
            id=household_id,
            name="Primary Household",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(household)
        db_session.flush()
    return household


def test_shopping_reconciliation_default_status(db_session):
    rec = ShoppingReconciliation(
        household_id=HOUSEHOLD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(rec)
    db_session.commit()

    assert rec.id is not None
    assert rec.status == "review_draft"
    assert rec.applied_at is None


def test_shopping_reconciliation_row_skipped_outcome(db_session):
    rec = ShoppingReconciliation(
        household_id=HOUSEHOLD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(rec)
    db_session.flush()

    row = ShoppingReconciliationRow(
        reconciliation_id=rec.id,
        item_name="Milk",
        planned_quantity=Decimal("2.0"),
        planned_unit="liters",
        outcome="skipped",
        created_at=datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()

    assert row.outcome == "skipped"
    assert row.actual_quantity is None
    assert row.inventory_adjustment_id is None


def test_shopping_reconciliation_supports_not_purchased_and_review_required(db_session):
    rec = ShoppingReconciliation(
        household_id=HOUSEHOLD,
        status="apply_failed_review_required",
        review_required_reason="Inventory target is ambiguous.",
        source_grocery_list_version_number=4,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(rec)
    db_session.flush()

    row = ShoppingReconciliationRow(
        reconciliation_id=rec.id,
        item_name="Greek Yogurt",
        outcome="not_purchased",
        inventory_item_version=3,
        created_at=datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()

    assert rec.review_required_reason == "Inventory target is ambiguous."
    assert rec.source_grocery_list_version_number == 4
    assert row.outcome == "not_purchased"
    assert row.inventory_item_version == 3


def test_cooking_event_default_status(db_session):
    event = CookingEvent(
        household_id=HOUSEHOLD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(event)
    db_session.commit()

    assert event.status == "cooking_draft"
    assert event.applied_at is None


def test_cooking_ingredient_row_substitute(db_session):
    event = CookingEvent(
        household_id=HOUSEHOLD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(event)
    db_session.flush()

    row = CookingIngredientRow(
        cooking_event_id=event.id,
        ingredient_name="Chicken Breast",
        planned_quantity=Decimal("300.0"),
        planned_unit="grams",
        outcome="substitute",
        actual_quantity=Decimal("250.0"),
        actual_unit="grams",
        created_at=datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()

    assert row.outcome == "substitute"


def test_leftover_row_is_first_class_inventory_outcome(db_session):
    add_household(db_session)
    event = CookingEvent(
        household_id=HOUSEHOLD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(event)
    db_session.flush()

    inventory_item = InventoryItem(
        id="inv-leftover-001",
        household_id=HOUSEHOLD,
        name="Leftover Chili",
        storage_location="leftovers",
        quantity_on_hand=Decimal("3.0"),
        primary_unit="servings",
        freshness_basis="estimated",
        estimated_expiry_date=date(2026, 3, 8),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(inventory_item)
    db_session.flush()

    adjustment = InventoryAdjustment(
        id="adj-leftover-001",
        inventory_item_id=inventory_item.id,
        household_id=HOUSEHOLD,
        mutation_type="create_item",
        delta_quantity=Decimal("3.0"),
        quantity_before=Decimal("0.0"),
        quantity_after=Decimal("3.0"),
        storage_location_after="leftovers",
        freshness_basis_after="estimated",
        reason_code="leftovers_create",
        created_at=datetime.utcnow(),
    )
    db_session.add(adjustment)
    db_session.flush()

    leftover = LeftoverRow(
        cooking_event_id=event.id,
        display_name="Leftover Chili",
        quantity=Decimal("3.0"),
        unit="servings",
        storage_location="fridge",
        target_inventory_item_id="inv-leftover-001",
        target_inventory_item_version=2,
        inventory_adjustment_id="adj-leftover-001",
        freshness_basis="estimated",
        created_at=datetime.utcnow(),
    )
    db_session.add(leftover)
    db_session.commit()
    db_session.refresh(event)

    assert len(event.leftover_rows) == 1
    assert event.leftover_rows[0].display_name == "Leftover Chili"
    assert event.leftover_rows[0].storage_location == "fridge"
    assert event.leftover_rows[0].target_inventory_item_id == "inv-leftover-001"
    assert event.leftover_rows[0].inventory_adjustment_id == "adj-leftover-001"
