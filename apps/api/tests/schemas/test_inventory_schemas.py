from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.inventory import InventoryItemCreate, InventoryAdjustmentCreate
from app.schemas.enums import FreshnessBasis, MutationType, ReasonCode, StorageLocation


def test_inventory_item_create_valid():
    item = InventoryItemCreate(
        household_id="hh-001",
        name="Milk",
        storage_location=StorageLocation.fridge,
        quantity_on_hand=Decimal("2.0"),
        primary_unit="liters",
        freshness_basis=FreshnessBasis.known,
        expiry_date=date(2025, 12, 31),
    )
    assert item.name == "Milk"
    assert item.storage_location == StorageLocation.fridge
    assert item.freshness_basis == FreshnessBasis.known


def test_inventory_item_create_defaults_unknown_freshness():
    item = InventoryItemCreate(
        household_id="hh-001",
        name="Salt",
        storage_location=StorageLocation.pantry,
        quantity_on_hand=Decimal("500.0"),
        primary_unit="grams",
    )
    assert item.freshness_basis == FreshnessBasis.unknown
    assert item.expiry_date is None


def test_inventory_item_create_requires_known_expiry_date():
    with pytest.raises(ValidationError):
        InventoryItemCreate(
            household_id="hh-001",
            name="Milk",
            storage_location=StorageLocation.fridge,
            quantity_on_hand=Decimal("2.0"),
            primary_unit="liters",
            freshness_basis=FreshnessBasis.known,
        )


def test_inventory_item_create_requires_estimated_expiry_date():
    with pytest.raises(ValidationError):
        InventoryItemCreate(
            household_id="hh-001",
            name="Lettuce",
            storage_location=StorageLocation.fridge,
            quantity_on_hand=Decimal("1.0"),
            primary_unit="head",
            freshness_basis=FreshnessBasis.estimated,
        )


def test_inventory_item_create_rejects_dates_for_unknown_basis():
    with pytest.raises(ValidationError):
        InventoryItemCreate(
            household_id="hh-001",
            name="Mystery Sauce",
            storage_location=StorageLocation.pantry,
            quantity_on_hand=Decimal("1.0"),
            primary_unit="jar",
            freshness_basis=FreshnessBasis.unknown,
            expiry_date=date(2025, 12, 31),
        )


def test_inventory_item_create_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        InventoryItemCreate(
            household_id="hh-001",
            name="Milk",
            storage_location=StorageLocation.fridge,
            quantity_on_hand=Decimal("-1.0"),
            primary_unit="liters",
        )


def test_inventory_item_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        InventoryItemCreate(
            household_id="hh-001",
            name="",
            storage_location=StorageLocation.fridge,
            quantity_on_hand=Decimal("1.0"),
            primary_unit="liters",
        )


def test_inventory_adjustment_create_valid():
    adj = InventoryAdjustmentCreate(
        inventory_item_id="item-001",
        household_id="hh-001",
        mutation_type=MutationType.increase_quantity,
        delta_quantity=Decimal("2.0"),
        quantity_before=Decimal("0.0"),
        quantity_after=Decimal("2.0"),
        reason_code=ReasonCode.shopping_apply,
        client_mutation_id="client-abc",
    )
    assert adj.mutation_type == MutationType.increase_quantity
    assert adj.reason_code == ReasonCode.shopping_apply


def test_inventory_adjustment_accepts_correction_link():
    adj = InventoryAdjustmentCreate(
        inventory_item_id="item-001",
        household_id="hh-001",
        mutation_type=MutationType.correction,
        delta_quantity=Decimal("-2.0"),
        reason_code=ReasonCode.correction,
        corrects_adjustment_id="adj-original-001",
    )
    assert adj.corrects_adjustment_id == "adj-original-001"


def test_inventory_adjustment_accepts_freshness_and_location_history():
    adj = InventoryAdjustmentCreate(
        inventory_item_id="item-001",
        household_id="hh-001",
        mutation_type=MutationType.set_metadata,
        quantity_before=Decimal("2.0"),
        quantity_after=Decimal("2.0"),
        storage_location_before=StorageLocation.fridge,
        storage_location_after=StorageLocation.freezer,
        freshness_basis_before=FreshnessBasis.estimated,
        estimated_expiry_date_before=date(2025, 12, 30),
        freshness_basis_after=FreshnessBasis.known,
        expiry_date_after=date(2025, 12, 31),
        reason_code=ReasonCode.manual_edit,
    )
    assert adj.storage_location_after == StorageLocation.freezer
    assert adj.freshness_basis_after == FreshnessBasis.known
