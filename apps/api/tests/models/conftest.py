from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.base import Base
import app.models  # noqa: F401
from app.models.household import Household, HouseholdMembership
from app.models.inventory import InventoryAdjustment, InventoryItem, MutationReceipt

HOUSEHOLD_ALPHA_ID = "00000000-0000-0000-0000-0000000000a1"
HOUSEHOLD_BETA_ID = "00000000-0000-0000-0000-0000000000b2"
HOUSEHOLD_ALPHA_ITEM_ID = "10000000-0000-0000-0000-0000000000a1"
HOUSEHOLD_BETA_ITEM_ID = "20000000-0000-0000-0000-0000000000b2"
HOUSEHOLD_ALPHA_ADJUSTMENT_ID = "30000000-0000-0000-0000-0000000000a1"
HOUSEHOLD_BETA_ADJUSTMENT_ID = "40000000-0000-0000-0000-0000000000b2"
HOUSEHOLD_ALPHA_RECEIPT_ID = "50000000-0000-0000-0000-0000000000a1"
HOUSEHOLD_BETA_RECEIPT_ID = "60000000-0000-0000-0000-0000000000b2"
SHARED_MUTATION_ID = "seeded-client-mutation"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture(scope="function")
def seeded_households(db_session):
    now = datetime.utcnow()
    households = [
        Household(
            id=HOUSEHOLD_ALPHA_ID,
            name="Alpha Household",
            created_at=now,
            updated_at=now,
        ),
        Household(
            id=HOUSEHOLD_BETA_ID,
            name="Beta Household",
            created_at=now,
            updated_at=now,
        ),
    ]
    db_session.add_all(households)
    db_session.flush()

    memberships = [
        HouseholdMembership(
            household_id=HOUSEHOLD_ALPHA_ID,
            user_id="user-alpha-owner",
            user_email="alpha-owner@example.com",
            user_display_name="Alpha Owner",
            role="owner",
            created_at=now,
            updated_at=now,
        ),
        HouseholdMembership(
            household_id=HOUSEHOLD_BETA_ID,
            user_id="user-beta-member",
            user_email="beta-member@example.com",
            user_display_name="Beta Member",
            role="member",
            created_at=now,
            updated_at=now,
        ),
    ]
    db_session.add_all(memberships)
    db_session.flush()

    items = [
        InventoryItem(
            id=HOUSEHOLD_ALPHA_ITEM_ID,
            household_id=HOUSEHOLD_ALPHA_ID,
            name="Alpha Milk",
            storage_location="fridge",
            quantity_on_hand=Decimal("2.0000"),
            primary_unit="liters",
            freshness_basis="known",
            expiry_date=date(2026, 3, 12),
            freshness_updated_at=now,
            created_at=now,
            updated_at=now,
        ),
        InventoryItem(
            id=HOUSEHOLD_BETA_ITEM_ID,
            household_id=HOUSEHOLD_BETA_ID,
            name="Beta Rice",
            storage_location="pantry",
            quantity_on_hand=Decimal("500.0000"),
            primary_unit="grams",
            freshness_basis="estimated",
            estimated_expiry_date=date(2026, 4, 5),
            freshness_note="Estimated from purchase week.",
            freshness_updated_at=now,
            created_at=now,
            updated_at=now,
        ),
    ]
    db_session.add_all(items)
    db_session.flush()

    adjustments = [
        InventoryAdjustment(
            id=HOUSEHOLD_ALPHA_ADJUSTMENT_ID,
            inventory_item_id=HOUSEHOLD_ALPHA_ITEM_ID,
            household_id=HOUSEHOLD_ALPHA_ID,
            mutation_type="create_item",
            delta_quantity=Decimal("2.0000"),
            quantity_before=Decimal("0.0000"),
            quantity_after=Decimal("2.0000"),
            storage_location_after="fridge",
            freshness_basis_after="known",
            expiry_date_after=date(2026, 3, 12),
            reason_code="manual_create",
            actor_id="user-alpha-owner",
            client_mutation_id=SHARED_MUTATION_ID,
            created_at=now,
        ),
        InventoryAdjustment(
            id=HOUSEHOLD_BETA_ADJUSTMENT_ID,
            inventory_item_id=HOUSEHOLD_BETA_ITEM_ID,
            household_id=HOUSEHOLD_BETA_ID,
            mutation_type="create_item",
            delta_quantity=Decimal("500.0000"),
            quantity_before=Decimal("0.0000"),
            quantity_after=Decimal("500.0000"),
            storage_location_after="pantry",
            freshness_basis_after="estimated",
            estimated_expiry_date_after=date(2026, 4, 5),
            reason_code="manual_create",
            actor_id="user-beta-member",
            client_mutation_id=SHARED_MUTATION_ID,
            created_at=now,
        ),
    ]
    db_session.add_all(adjustments)
    db_session.flush()

    receipts = [
        MutationReceipt(
            id=HOUSEHOLD_ALPHA_RECEIPT_ID,
            household_id=HOUSEHOLD_ALPHA_ID,
            client_mutation_id=SHARED_MUTATION_ID,
            accepted_at=now,
            result_summary="alpha seed create",
            inventory_adjustment_id=HOUSEHOLD_ALPHA_ADJUSTMENT_ID,
        ),
        MutationReceipt(
            id=HOUSEHOLD_BETA_RECEIPT_ID,
            household_id=HOUSEHOLD_BETA_ID,
            client_mutation_id=SHARED_MUTATION_ID,
            accepted_at=now,
            result_summary="beta seed create",
            inventory_adjustment_id=HOUSEHOLD_BETA_ADJUSTMENT_ID,
        ),
    ]
    db_session.add_all(receipts)
    db_session.commit()

    return {
        "households": households,
        "memberships": memberships,
        "items": items,
        "adjustments": adjustments,
        "receipts": receipts,
    }
