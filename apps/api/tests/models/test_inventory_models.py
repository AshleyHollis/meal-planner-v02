from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.household import Household
from app.models.inventory import InventoryAdjustment, InventoryItem, MutationReceipt


HOUSEHOLD = "hh-001"
HOUSEHOLD_BETA_ID = "00000000-0000-0000-0000-0000000000b2"


def add_household(db_session, household_id: str = HOUSEHOLD, name: str = "Primary Household") -> Household:
    household = db_session.get(Household, household_id)
    if household is None:
        household = Household(
            id=household_id,
            name=name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(household)
        db_session.flush()
    return household


def make_item(name: str = "Milk", **kwargs) -> InventoryItem:
    payload = {
        "household_id": HOUSEHOLD,
        "name": name,
        "storage_location": "fridge",
        "quantity_on_hand": Decimal("2.0"),
        "primary_unit": "liters",
        "freshness_basis": "known",
        "expiry_date": date(2025, 12, 31),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    payload.update(kwargs)
    return InventoryItem(**payload)


def test_inventory_item_can_be_created(db_session):
    add_household(db_session)
    item = make_item()
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id is not None
    assert item.household_id == HOUSEHOLD
    assert item.name == "Milk"
    assert item.storage_location == "fridge"
    assert item.quantity_on_hand == Decimal("2.0")
    assert item.primary_unit == "liters"
    assert item.freshness_basis == "known"
    assert item.is_active is True
    assert item.version == 1


def test_inventory_item_defaults_unknown_freshness(db_session):
    add_household(db_session)
    item = InventoryItem(
        household_id=HOUSEHOLD,
        name="Mystery Jar",
        storage_location="pantry",
        quantity_on_hand=Decimal("1.0"),
        primary_unit="count",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()
    assert item.freshness_basis == "unknown"


def test_inventory_item_requires_existing_household(db_session):
    item = make_item(household_id="missing-household")
    db_session.add(item)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_inventory_item_enforces_known_freshness_date(db_session):
    add_household(db_session)
    item = make_item(freshness_basis="known", expiry_date=None)
    db_session.add(item)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_inventory_adjustment_creates_with_correction_link(db_session):
    add_household(db_session)
    item = make_item()
    db_session.add(item)
    db_session.flush()

    original = InventoryAdjustment(
        inventory_item_id=item.id,
        household_id=HOUSEHOLD,
        mutation_type="increase_quantity",
        delta_quantity=Decimal("4.0"),
        quantity_before=Decimal("0.0"),
        quantity_after=Decimal("4.0"),
        reason_code="shopping_apply",
        created_at=datetime.utcnow(),
    )
    db_session.add(original)
    db_session.flush()

    correction = InventoryAdjustment(
        inventory_item_id=item.id,
        household_id=HOUSEHOLD,
        mutation_type="correction",
        delta_quantity=Decimal("-2.0"),
        quantity_before=Decimal("4.0"),
        quantity_after=Decimal("2.0"),
        reason_code="correction",
        corrects_adjustment_id=original.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(correction)
    db_session.commit()

    assert correction.corrects_adjustment_id == original.id
    assert original.corrected_by_adjustments[0].id == correction.id


def test_inventory_adjustment_stores_location_and_freshness_history(db_session):
    add_household(db_session)
    item = make_item()
    db_session.add(item)
    db_session.flush()

    adj = InventoryAdjustment(
        inventory_item_id=item.id,
        household_id=HOUSEHOLD,
        mutation_type="set_metadata",
        quantity_before=Decimal("2.0"),
        quantity_after=Decimal("2.0"),
        storage_location_before="fridge",
        storage_location_after="freezer",
        freshness_basis_before="estimated",
        estimated_expiry_date_before=date(2025, 12, 30),
        freshness_basis_after="known",
        expiry_date_after=date(2025, 12, 31),
        reason_code="manual_edit",
        created_at=datetime.utcnow(),
    )
    db_session.add(adj)
    db_session.commit()

    assert adj.storage_location_before == "fridge"
    assert adj.storage_location_after == "freezer"
    assert adj.freshness_basis_before == "estimated"
    assert adj.expiry_date_after == date(2025, 12, 31)


def test_mutation_receipt_unique_per_household_and_client_id(db_session):
    add_household(db_session)
    receipt = MutationReceipt(
        household_id=HOUSEHOLD,
        client_mutation_id="client-abc-123",
        accepted_at=datetime.utcnow(),
    )
    db_session.add(receipt)
    db_session.commit()

    duplicate = MutationReceipt(
        household_id=HOUSEHOLD,
        client_mutation_id="client-abc-123",
        accepted_at=datetime.utcnow(),
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_mutation_receipt_allows_same_client_id_for_other_household(db_session):
    add_household(db_session)
    add_household(db_session, household_id=HOUSEHOLD_BETA_ID, name="Secondary Household")

    first = MutationReceipt(
        household_id=HOUSEHOLD,
        client_mutation_id="client-abc-123",
        accepted_at=datetime.utcnow(),
    )
    second = MutationReceipt(
        household_id=HOUSEHOLD_BETA_ID,
        client_mutation_id="client-abc-123",
        accepted_at=datetime.utcnow(),
    )
    db_session.add_all([first, second])
    db_session.commit()

    assert first.id is not None
    assert second.id is not None


def test_inventory_item_adjustments_relationship(db_session):
    add_household(db_session)
    item = make_item("Eggs")
    db_session.add(item)
    db_session.flush()

    adj = InventoryAdjustment(
        inventory_item_id=item.id,
        household_id=HOUSEHOLD,
        mutation_type="decrease_quantity",
        delta_quantity=Decimal("2.0"),
        reason_code="cooking_consume",
        created_at=datetime.utcnow(),
    )
    db_session.add(adj)
    db_session.commit()
    db_session.refresh(item)

    assert len(item.adjustments) == 1
    assert item.adjustments[0].reason_code == "cooking_consume"
