from datetime import datetime
from decimal import Decimal

from app.models.grocery import GroceryList, GroceryListVersion, GroceryListItem

HOUSEHOLD = "hh-001"


def make_list(**kwargs) -> GroceryList:
    return GroceryList(
        household_id=HOUSEHOLD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        **kwargs,
    )


def test_grocery_list_defaults(db_session):
    gl = make_list()
    db_session.add(gl)
    db_session.commit()
    db_session.refresh(gl)

    assert gl.id is not None
    assert gl.status == "deriving"
    assert gl.current_version_number == 1
    assert gl.confirmed_at is None


def test_grocery_list_version_links_to_list(db_session):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()

    version = GroceryListVersion(
        grocery_list_id=gl.id,
        version_number=1,
        plan_period_reference="2025-01-06/2025-01-12",
        derived_at=datetime.utcnow(),
        inventory_snapshot_reference="inventory-v12",
        source_plan_version=1,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(gl)

    assert len(gl.versions) == 1


def test_grocery_list_item_meal_derived_defaults(db_session):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        ingredient_name="Pasta",
        quantity_needed=Decimal("400.0"),
        unit="grams",
        quantity_offset=Decimal("0.0"),
        quantity_to_buy=Decimal("400.0"),
        meal_sources='[{"meal_plan_slot_id": "slot-001", "quantity": 400.0}]',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.origin == "derived"
    assert item.is_purchased is False
    assert item.is_active is True
    assert item.user_adjustment_flagged is False


def test_grocery_list_item_ad_hoc(db_session):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        ingredient_name="Sparkling Water",
        quantity_needed=Decimal("2.0"),
        unit="liters",
        quantity_offset=Decimal("0.0"),
        quantity_to_buy=Decimal("2.0"),
        origin="ad_hoc",
        ad_hoc_note="Grab the club soda for brunch",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.origin == "ad_hoc"
    assert item.ad_hoc_note == "Grab the club soda for brunch"


def test_grocery_list_partial_inventory_offset(db_session):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        ingredient_name="Pasta",
        quantity_needed=Decimal("500.0"),
        unit="grams",
        quantity_offset=Decimal("200.0"),
        quantity_to_buy=Decimal("300.0"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.quantity_offset == Decimal("200.0")
    assert item.quantity_to_buy == Decimal("300.0")


def test_grocery_list_item_tracks_user_adjustment_note_and_active_state(db_session):
    gl = make_list()
    db_session.add(gl)
    db_session.flush()

    item = GroceryListItem(
        grocery_list_id=gl.id,
        ingredient_name="Tomatoes",
        quantity_needed=Decimal("4.0"),
        unit="count",
        quantity_offset=Decimal("0.0"),
        quantity_to_buy=Decimal("5.0"),
        user_adjusted_quantity=Decimal("5.0"),
        user_adjustment_note="Need an extra one for salsa",
        is_active=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(item)
    db_session.commit()

    assert item.user_adjustment_note == "Need an extra one for salsa"
    assert item.is_active is False
