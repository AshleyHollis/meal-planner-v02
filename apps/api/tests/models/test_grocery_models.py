from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.grocery import (
    GroceryList,
    GroceryListItem,
    GroceryListVersion,
    GroceryMutationReceipt,
    GrocerySyncConflict,
)

from .conftest import HOUSEHOLD_ALPHA_ID, HOUSEHOLD_ALPHA_ITEM_ID, HOUSEHOLD_BETA_ID

HOUSEHOLD = HOUSEHOLD_ALPHA_ID


def make_list(**kwargs) -> GroceryList:
    return GroceryList(
        household_id=HOUSEHOLD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        **kwargs,
    )


def make_version(grocery_list_id: str, **kwargs) -> GroceryListVersion:
    return GroceryListVersion(
        grocery_list_id=grocery_list_id,
        version_number=1,
        derived_at=datetime.utcnow(),
        **kwargs,
    )


def test_grocery_list_defaults(db_session, seeded_households):
    gl = make_list()
    db_session.add(gl)
    db_session.commit()
    db_session.refresh(gl)

    assert gl.id is not None
    assert gl.status == "deriving"
    assert gl.current_version_number == 1
    assert gl.confirmed_at is None
    assert gl.confirmation_client_mutation_id is None
    assert gl.current_version is None


def test_grocery_list_version_links_to_list_and_surfaces_warning_metadata(db_session, seeded_households):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()

    version = make_version(
        gl.id,
        plan_period_reference="2025-01-06/2025-01-12",
        inventory_snapshot_reference="inventory-v12",
        confirmed_plan_version=1,
        incomplete_slot_warnings='[{"meal_plan_slot_id": "slot-001", "meal_name": "Friday Pasta"}]',
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(gl)

    assert len(gl.versions) == 1
    assert gl.current_version_id == version.id
    assert gl.last_derived_at == version.derived_at
    assert gl.incomplete_slot_warnings == [{"meal_plan_slot_id": "slot-001", "meal_name": "Friday Pasta"}]


def test_grocery_list_item_meal_derived_defaults(db_session, seeded_households):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()
    version = make_version(gl.id)
    db_session.add(version)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        grocery_list_version_id=version.id,
        ingredient_name="Pasta",
        required_quantity=Decimal("400.0"),
        unit="grams",
        offset_quantity=Decimal("0.0"),
        shopping_quantity=Decimal("400.0"),
        meal_sources='[{"meal_plan_slot_id": "slot-001", "quantity": 400.0}]',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.stable_line_id is not None
    assert item.origin == "derived"
    assert item.is_purchased is False
    assert item.active is True
    assert item.user_adjustment_flagged is False


def test_grocery_list_item_ad_hoc(db_session, seeded_households):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()
    version = make_version(gl.id)
    db_session.add(version)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        grocery_list_version_id=version.id,
        ingredient_name="Sparkling Water",
        required_quantity=Decimal("2.0"),
        unit="liters",
        offset_quantity=Decimal("0.0"),
        shopping_quantity=Decimal("2.0"),
        origin="ad_hoc",
        ad_hoc_note="Grab the club soda for brunch",
        created_client_mutation_id="grocery-create-001",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.stable_line_id is not None
    assert item.origin == "ad_hoc"
    assert item.ad_hoc_note == "Grab the club soda for brunch"
    assert item.created_client_mutation_id == "grocery-create-001"


def test_grocery_list_partial_inventory_offset(db_session, seeded_households):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()
    version = make_version(gl.id)
    db_session.add(version)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        grocery_list_version_id=version.id,
        ingredient_name="Pasta",
        required_quantity=Decimal("500.0"),
        unit="grams",
        offset_quantity=Decimal("200.0"),
        offset_inventory_item_id=HOUSEHOLD_ALPHA_ITEM_ID,
        offset_inventory_item_version=4,
        shopping_quantity=Decimal("300.0"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.offset_quantity == Decimal("200.0")
    assert item.offset_inventory_item_id == HOUSEHOLD_ALPHA_ITEM_ID
    assert item.offset_inventory_item_version == 4
    assert item.shopping_quantity == Decimal("300.0")


def test_grocery_list_item_tracks_user_adjustment_note_and_removed_state(db_session, seeded_households):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()
    version = make_version(gl.id)
    db_session.add(version)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        grocery_list_version_id=version.id,
        ingredient_name="Tomatoes",
        required_quantity=Decimal("4.0"),
        unit="count",
        offset_quantity=Decimal("0.0"),
        shopping_quantity=Decimal("5.0"),
        user_adjusted_quantity=Decimal("5.0"),
        user_adjustment_note="Need an extra one for salsa",
        active=False,
        removed_at=datetime.utcnow(),
        removed_client_mutation_id="grocery-remove-001",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.user_adjustment_note == "Need an extra one for salsa"
    assert item.active is False
    assert item.removed_client_mutation_id == "grocery-remove-001"


def test_grocery_list_version_number_unique_per_list(db_session, seeded_households):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()
    db_session.add_all([make_version(gl.id), make_version(gl.id)])

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_grocery_mutation_receipts_are_household_scoped(db_session, seeded_households):
    alpha_list = make_list()
    beta_list = GroceryList(
        household_id=HOUSEHOLD_BETA_ID,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add_all([alpha_list, beta_list])
    db_session.flush()

    alpha_receipt = GroceryMutationReceipt(
        household_id=HOUSEHOLD_ALPHA_ID,
        grocery_list_id=alpha_list.id,
        client_mutation_id="shared-grocery-mutation",
        mutation_kind="add_ad_hoc",
        result_summary="alpha add",
    )
    beta_receipt = GroceryMutationReceipt(
        household_id=HOUSEHOLD_BETA_ID,
        grocery_list_id=beta_list.id,
        client_mutation_id="shared-grocery-mutation",
        mutation_kind="add_ad_hoc",
        result_summary="beta add",
    )
    db_session.add_all([alpha_receipt, beta_receipt])
    db_session.commit()

    duplicate_alpha = GroceryMutationReceipt(
        household_id=HOUSEHOLD_ALPHA_ID,
        grocery_list_id=alpha_list.id,
        client_mutation_id="shared-grocery-mutation",
        mutation_kind="confirm",
    )
    db_session.add(duplicate_alpha)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_grocery_sync_conflicts_are_household_scoped(db_session, seeded_households):
    alpha_list = make_list()
    beta_list = GroceryList(
        household_id=HOUSEHOLD_BETA_ID,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add_all([alpha_list, beta_list])
    db_session.flush()

    alpha_conflict = GrocerySyncConflict(
        household_id=HOUSEHOLD_ALPHA_ID,
        grocery_list_id=alpha_list.id,
        aggregate_type="grocery_line",
        aggregate_id="line-001",
        local_mutation_id="shared-sync-mutation",
        mutation_type="adjust_line",
        outcome="review_required_other_unsafe",
        base_server_version=1,
        current_server_version=2,
        requires_review=True,
        summary="Alpha needs review.",
        local_queue_status="review_required",
        allowed_resolution_actions='["keep_mine","use_server"]',
        resolution_status="pending",
        created_at=datetime.utcnow(),
    )
    beta_conflict = GrocerySyncConflict(
        household_id=HOUSEHOLD_BETA_ID,
        grocery_list_id=beta_list.id,
        aggregate_type="grocery_line",
        aggregate_id="line-001",
        local_mutation_id="shared-sync-mutation",
        mutation_type="adjust_line",
        outcome="review_required_other_unsafe",
        base_server_version=1,
        current_server_version=2,
        requires_review=True,
        summary="Beta needs review.",
        local_queue_status="review_required",
        allowed_resolution_actions='["keep_mine","use_server"]',
        resolution_status="pending",
        created_at=datetime.utcnow(),
    )
    db_session.add_all([alpha_conflict, beta_conflict])
    db_session.commit()

    duplicate_alpha = GrocerySyncConflict(
        household_id=HOUSEHOLD_ALPHA_ID,
        grocery_list_id=alpha_list.id,
        aggregate_type="grocery_line",
        aggregate_id="line-001",
        local_mutation_id="shared-sync-mutation",
        mutation_type="remove_line",
        outcome="review_required_deleted_or_archived",
        current_server_version=3,
        requires_review=True,
        summary="Duplicate alpha conflict.",
        local_queue_status="review_required",
        resolution_status="pending",
        created_at=datetime.utcnow(),
    )
    db_session.add(duplicate_alpha)

    with pytest.raises(IntegrityError):
        db_session.commit()
