from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.household import Household, HouseholdMembership
from app.models.inventory import InventoryAdjustment, InventoryItem, MutationReceipt


HOUSEHOLD_ALPHA_ID = "00000000-0000-0000-0000-0000000000a1"
HOUSEHOLD_BETA_ID = "00000000-0000-0000-0000-0000000000b2"
SHARED_MUTATION_ID = "seeded-client-mutation"


def test_household_membership_is_unique_per_household_user(db_session):
    household = Household(
        id=HOUSEHOLD_ALPHA_ID,
        name="Alpha Household",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(household)
    db_session.flush()

    membership = HouseholdMembership(
        household_id=household.id,
        user_id="user-alpha-owner",
        role="owner",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()

    duplicate = HouseholdMembership(
        household_id=household.id,
        user_id="user-alpha-owner",
        role="member",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_seeded_households_keep_inventory_isolated(db_session, seeded_households):
    alpha_items = db_session.scalars(
        select(InventoryItem).where(InventoryItem.household_id == HOUSEHOLD_ALPHA_ID)
    ).all()
    beta_items = db_session.scalars(
        select(InventoryItem).where(InventoryItem.household_id == HOUSEHOLD_BETA_ID)
    ).all()

    assert [item.name for item in alpha_items] == ["Alpha Milk"]
    assert [item.name for item in beta_items] == ["Beta Rice"]
    assert alpha_items[0].household.name == "Alpha Household"
    assert beta_items[0].household.name == "Beta Household"


def test_seeded_households_keep_audit_trails_isolated(db_session, seeded_households):
    alpha_adjustments = db_session.scalars(
        select(InventoryAdjustment).where(InventoryAdjustment.household_id == HOUSEHOLD_ALPHA_ID)
    ).all()
    beta_adjustments = db_session.scalars(
        select(InventoryAdjustment).where(InventoryAdjustment.household_id == HOUSEHOLD_BETA_ID)
    ).all()
    alpha_receipts = db_session.scalars(
        select(MutationReceipt).where(MutationReceipt.household_id == HOUSEHOLD_ALPHA_ID)
    ).all()
    beta_receipts = db_session.scalars(
        select(MutationReceipt).where(MutationReceipt.household_id == HOUSEHOLD_BETA_ID)
    ).all()

    assert len(alpha_adjustments) == 1
    assert len(beta_adjustments) == 1
    assert len(alpha_receipts) == 1
    assert len(beta_receipts) == 1
    assert alpha_receipts[0].client_mutation_id == SHARED_MUTATION_ID
    assert beta_receipts[0].client_mutation_id == SHARED_MUTATION_ID
    assert alpha_receipts[0].inventory_adjustment_id != beta_receipts[0].inventory_adjustment_id
