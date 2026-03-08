from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, select

from app.dependencies.session import (
    DEV_ACTIVE_HOUSEHOLD_ID_HEADER,
    DEV_ACTIVE_HOUSEHOLD_NAME_HEADER,
    DEV_ACTIVE_HOUSEHOLD_ROLE_HEADER,
    DEV_HOUSEHOLDS_HEADER,
    DEV_USER_EMAIL_HEADER,
    DEV_USER_ID_HEADER,
    DEV_USER_NAME_HEADER,
)
from app.main import app
from app.models.grocery import GroceryList
from app.models.household import Household
from app.models.inventory import InventoryItem
from app.models.meal_plan import MealPlan, MealPlanSlot
from app.models.planner_event import PlannerEvent
from app.schemas.enums import FreshnessBasis, MealPlanStatus, StorageLocation
from app.schemas.inventory import CreateItemCommand, FreshnessInfo
from app.schemas.planner import GroceryRefreshTrigger, PlanConfirmedEvent
from app.services.grocery_service import (
    GroceryService,
    MealIngredient,
    MealIngredientCatalog,
    get_grocery_service,
)
from app.services.inventory_store import InventoryStore, get_inventory_store
from app.services.planner_service import PlannerService, get_planner_service
from grocery_fixtures import (
    CONFIRMATION_DIAGNOSTIC_FIXTURE,
    DERIVATION_DIAGNOSTIC_FIXTURE,
    STALE_DETECTION_FIXTURE,
    SYNC_AUTO_MERGE_FIXTURE,
    SYNC_DUPLICATE_RETRY_FIXTURE,
    SYNC_KEEP_MINE_RESOLUTION_FIXTURE,
    SYNC_REVIEW_REQUIRED_FIXTURE,
    SYNC_USE_SERVER_RESOLUTION_FIXTURE,
    build_sync_add_ad_hoc_mutation,
    build_sync_adjust_line_mutation,
)

HOUSEHOLD = "household-grocery-alpha"
OTHER_HOUSEHOLD = "household-grocery-beta"
PERIOD_START = date(2026, 3, 9)


@pytest.fixture()
def shared_services(tmp_path) -> tuple[PlannerService, InventoryStore, GroceryService]:
    db_url = URL.create("sqlite+pysqlite", database=str((tmp_path / "grocery-test.sqlite").resolve()))
    catalog = MealIngredientCatalog(
        {
            "meal-pasta-bake": [
                MealIngredient("Pasta", Decimal("500"), "grams", ingredient_ref_id="ingredient-pasta"),
                MealIngredient("Tomatoes", Decimal("4"), "count", ingredient_ref_id="ingredient-tomatoes"),
                MealIngredient("Olive Oil", Decimal("100"), "milliliters", ingredient_ref_id="ingredient-olive-oil"),
            ],
            "meal-pesto-pasta": [
                MealIngredient("Pasta", Decimal("300"), "grams", ingredient_ref_id="ingredient-pasta"),
                MealIngredient("Basil", Decimal("1"), "bunch", ingredient_ref_id="ingredient-basil"),
                MealIngredient("Olive Oil", Decimal("50"), "milliliters", ingredient_ref_id="ingredient-olive-oil"),
            ],
            "meal-oil-bottle": [
                MealIngredient("Olive Oil", Decimal("1"), "bottle", ingredient_ref_id="ingredient-olive-oil"),
            ],
            "meal-oil-ml": [
                MealIngredient("Olive Oil", Decimal("25"), "milliliters", ingredient_ref_id="ingredient-olive-oil"),
            ],
            "meal-staples-toast": [
                MealIngredient("Olive Oil", Decimal("2"), "tablespoons", ingredient_ref_id="ingredient-olive-oil"),
                MealIngredient("Salt", Decimal("1"), "teaspoon", ingredient_ref_id="ingredient-salt"),
            ],
        }
    )
    planner = PlannerService(database_url=db_url)
    inventory = InventoryStore(database_url=db_url)
    grocery = GroceryService(database_url=db_url, ingredient_catalog=catalog)
    yield planner, inventory, grocery
    planner.dispose()
    inventory.dispose()
    grocery.dispose()


@pytest.fixture()
def client(shared_services: tuple[PlannerService, InventoryStore, GroceryService]) -> TestClient:
    planner, inventory, grocery = shared_services
    app.dependency_overrides[get_planner_service] = lambda: planner
    app.dependency_overrides[get_inventory_store] = lambda: inventory
    app.dependency_overrides[get_grocery_service] = lambda: grocery
    with TestClient(app) as test_client:
        test_client.headers.update(_session_headers(HOUSEHOLD))
        yield test_client
    app.dependency_overrides.pop(get_planner_service, None)
    app.dependency_overrides.pop(get_inventory_store, None)
    app.dependency_overrides.pop(get_grocery_service, None)


def _session_headers(household_id: str) -> dict[str, str]:
    return {
        DEV_USER_ID_HEADER: f"user-{household_id}",
        DEV_USER_EMAIL_HEADER: f"{household_id}@example.com",
        DEV_USER_NAME_HEADER: household_id,
        DEV_ACTIVE_HOUSEHOLD_ID_HEADER: household_id,
        DEV_ACTIVE_HOUSEHOLD_NAME_HEADER: f"{household_id} home",
        DEV_ACTIVE_HOUSEHOLD_ROLE_HEADER: "owner",
        DEV_HOUSEHOLDS_HEADER: json.dumps(
            [
                {
                    "household_id": household_id,
                    "household_name": f"{household_id} home",
                    "role": "owner",
                }
            ]
        ),
    }


def _actor_id(household_id: str = HOUSEHOLD) -> str:
    return f"user-{household_id}"


def _seed_confirmed_plan(
    grocery: GroceryService,
    *,
    household_id: str = HOUSEHOLD,
    period_start: date = PERIOD_START,
    slot_refs: list[tuple[str, str | None]] | None = None,
    version: int = 3,
    plan_id: str | None = None,
) -> str:
    slot_refs = slot_refs or [
        ("Pasta Bake", "meal-pasta-bake"),
        ("Pesto Pasta", "meal-pesto-pasta"),
        ("Mystery Night", None),
    ]
    now = datetime.now(UTC).replace(tzinfo=None)
    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        if session.get(Household, household_id) is None:
            session.add(Household(id=household_id, name=f"{household_id} home", created_at=now, updated_at=now))
            session.flush()
        plan = MealPlan(
            id=plan_id or f"plan-{household_id}-{period_start.isoformat()}-v{version}",
            household_id=household_id,
            period_start=period_start,
            period_end=period_start + timedelta(days=6),
            status=MealPlanStatus.confirmed.value,
            version=version,
            confirmed_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(plan)
        session.flush()
        meal_types = ["breakfast", "lunch", "dinner"]
        for index, (title, meal_reference_id) in enumerate(slot_refs):
            session.add(
                MealPlanSlot(
                    id=f"slot-{household_id}-v{version}-{index}",
                    meal_plan_id=plan.id,
                    slot_key=f"day-{index}-{meal_types[index % len(meal_types)]}",
                    day_of_week=index,
                    meal_type=meal_types[index % len(meal_types)],
                    meal_title=title,
                    meal_summary=f"{title} summary",
                    meal_reference_id=meal_reference_id,
                    slot_origin="manually_added",
                    regen_status="idle",
                    is_user_locked=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()
        return plan.id


def _enqueue_plan_confirmed_event(
    grocery: GroceryService,
    *,
    household_id: str = HOUSEHOLD,
    plan_id: str,
    period_start: date = PERIOD_START,
    version: int,
    mutation_id: str,
) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    event = PlanConfirmedEvent(
        household_id=household_id,
        meal_plan_id=plan_id,
        plan_period_start=period_start,
        plan_period_end=period_start + timedelta(days=6),
        confirmed_at=now,
        stale_warning_acknowledged=False,
        confirmation_client_mutation_id=mutation_id,
        actor_id=f"user-{household_id}",
        slot_count=3,
        plan_version=version,
        correlation_id=f"corr-{mutation_id}",
        grocery_refresh_trigger=GroceryRefreshTrigger(
            household_id=household_id,
            confirmed_plan_id=plan_id,
            plan_period_start=period_start,
            plan_period_end=period_start + timedelta(days=6),
            source_plan_version=version,
            correlation_id=f"corr-{mutation_id}",
        ),
    )
    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        session.add(
            PlannerEvent(
                household_id=household_id,
                meal_plan_id=plan_id,
                event_type="plan_confirmed",
                source_mutation_id=mutation_id,
                payload=event.model_dump_json(),
                occurred_at=now,
            )
        )
        session.commit()


def _create_inventory_item(
    inventory: InventoryStore,
    *,
    household_id: str,
    name: str,
    quantity: str,
    unit: str,
    mutation_id: str,
) -> None:
    inventory.create_item(
        CreateItemCommand(
            household_id=household_id,
            name=name,
            storage_location=StorageLocation.pantry,
            initial_quantity=float(Decimal(quantity)),
            primary_unit=unit,
            freshness=FreshnessInfo(basis=FreshnessBasis.known, best_before="2026-03-20"),
            client_mutation_id=mutation_id,
        ),
        actor_user_id=f"user-{household_id}",
    )


def _derive(client: TestClient, mutation_id: str, *, household_id: str = HOUSEHOLD) -> dict:
    response = client.post(
        f"/api/v1/households/{household_id}/grocery/derive",
        json={
            "household_id": household_id,
            "planPeriodStart": PERIOD_START.isoformat(),
            "clientMutationId": mutation_id,
        },
        headers=_session_headers(household_id),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _confirm_list(
    client: TestClient,
    grocery_list_id: str,
    *,
    household_id: str = HOUSEHOLD,
    mutation_id: str,
) -> dict:
    response = client.post(
        f"/api/v1/households/{household_id}/grocery/{grocery_list_id}/confirm",
        json={
            "groceryListId": grocery_list_id,
            "household_id": household_id,
            "clientMutationId": mutation_id,
        },
        headers=_session_headers(household_id),
    )
    assert response.status_code == 200, response.text
    return response.json()["grocery_list"]


def _upload_sync_mutations(
    client: TestClient,
    mutations: list[dict],
    *,
    household_id: str = HOUSEHOLD,
) -> list[dict]:
    response = client.post(
        f"/api/v1/households/{household_id}/grocery/sync/upload",
        json=mutations,
        headers=_session_headers(household_id),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_derive_grocery_list_consolidates_duplicates_offsets_and_warnings(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Pasta", quantity="200", unit="grams", mutation_id="inv-pasta")
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Tomatoes", quantity="4", unit="count", mutation_id="inv-tomatoes")
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Olive Oil", quantity="20", unit="milliliters", mutation_id="inv-oil")

    body = _derive(client, "derive-001")

    assert body["mutation_kind"] == "derive"
    assert body["is_duplicate"] is False
    grocery_list = body["grocery_list"]
    assert grocery_list["status"] == "draft"
    assert grocery_list["confirmed_plan_version"] == 3
    assert len(grocery_list["incomplete_slot_warnings"]) == 1
    assert grocery_list["incomplete_slot_warnings"][0]["meal_slot_id"] == f"slot-{HOUSEHOLD}-v3-2"

    lines = {line["ingredient_name"]: line for line in grocery_list["lines"]}
    assert set(lines) == {"Basil", "Olive Oil", "Pasta"}
    assert lines["Pasta"]["required_quantity"] == "800.0000"
    assert lines["Pasta"]["offset_quantity"] == "200.0000"
    assert lines["Pasta"]["shopping_quantity"] == "600.0000"
    assert len(lines["Pasta"]["meal_sources"]) == 2
    assert lines["Olive Oil"]["shopping_quantity"] == "130.0000"
    assert lines["Basil"]["shopping_quantity"] == "1.0000"

    current = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery?period={PERIOD_START.isoformat()}")
    assert current.status_code == 200
    assert current.json()["id"] == grocery_list["id"]


def test_derive_keeps_same_name_different_units_as_separate_lines(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, _, grocery = shared_services
    _seed_confirmed_plan(
        grocery,
        slot_refs=[("Oil Bottle", "meal-oil-bottle"), ("Oil Splash", "meal-oil-ml")],
    )

    body = _derive(client, "derive-002")
    oil_lines = [line for line in body["grocery_list"]["lines"] if line["ingredient_name"] == "Olive Oil"]

    assert len(oil_lines) == 2
    assert {line["unit"] for line in oil_lines} == {"bottle", "milliliters"}


def test_derive_uses_only_confirmed_plan_slots_for_the_period(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, _, grocery = shared_services
    _seed_confirmed_plan(grocery, slot_refs=[("Confirmed Pasta", "meal-pasta-bake")])

    now = datetime.now(UTC).replace(tzinfo=None)
    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        draft_plan = MealPlan(
            id=f"draft-plan-{HOUSEHOLD}-{PERIOD_START.isoformat()}",
            household_id=HOUSEHOLD,
            period_start=PERIOD_START,
            period_end=PERIOD_START + timedelta(days=6),
            status=MealPlanStatus.draft.value,
            version=99,
            created_at=now,
            updated_at=now,
        )
        session.add(draft_plan)
        session.flush()
        session.add(
            MealPlanSlot(
                id=f"draft-slot-{HOUSEHOLD}-{PERIOD_START.isoformat()}",
                meal_plan_id=draft_plan.id,
                slot_key="day-0-dinner",
                day_of_week=0,
                meal_type="dinner",
                meal_title="Draft Oil Bottle",
                meal_summary="Draft-only meal",
                meal_reference_id="meal-oil-bottle",
                slot_origin="manually_added",
                regen_status="idle",
                is_user_locked=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    body = _derive(client, "derive-confirmed-only-001")
    grocery_list = body["grocery_list"]
    line_units = {(line["ingredient_name"], line["unit"]) for line in grocery_list["lines"]}

    assert grocery_list["confirmed_plan_version"] == 3
    assert ("Pasta", "grams") in line_units
    assert ("Tomatoes", "count") in line_units
    assert ("Olive Oil", "milliliters") in line_units
    assert ("Olive Oil", "bottle") not in line_units


def test_derive_does_not_assume_staples_are_on_hand(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, _, grocery = shared_services
    _seed_confirmed_plan(grocery, slot_refs=[("Staples Toast", "meal-staples-toast")])

    body = _derive(client, "derive-staples-001")
    lines = {line["ingredient_name"]: line for line in body["grocery_list"]["lines"]}

    assert set(lines) == {"Olive Oil", "Salt"}
    assert lines["Olive Oil"]["offset_quantity"] == "0.0000"
    assert lines["Olive Oil"]["shopping_quantity"] == "2.0000"
    assert lines["Salt"]["offset_quantity"] == "0.0000"
    assert lines["Salt"]["shopping_quantity"] == "1.0000"


def test_read_current_list_marks_stale_after_inventory_change(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Pasta", quantity="200", unit="grams", mutation_id="inv-stale-pasta")
    _derive(client, "derive-stale-001")

    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        pasta = session.scalar(select(InventoryItem).where(InventoryItem.household_id == HOUSEHOLD, InventoryItem.name == "Pasta"))
        assert pasta is not None
        pasta.quantity_on_hand = Decimal("50.0000")
        pasta.version += 1
        pasta.updated_at = datetime.now(UTC).replace(tzinfo=None)
        session.commit()

    current = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery?period={PERIOD_START.isoformat()}")
    assert current.status_code == 200
    assert current.json()["status"] == "stale_draft"
    assert current.json()["is_stale"] is True


def test_plan_confirmed_event_auto_derives_when_no_list_exists(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    plan_id = _seed_confirmed_plan(grocery)
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Pasta", quantity="200", unit="grams", mutation_id="inv-auto-plan")
    _enqueue_plan_confirmed_event(
        grocery,
        plan_id=plan_id,
        version=3,
        mutation_id="plan-confirmed-auto-001",
    )

    processed = grocery.process_pending_plan_confirmed_events(HOUSEHOLD, actor_id="worker-grocery")

    assert processed == 1
    current = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery?period={PERIOD_START.isoformat()}")
    assert current.status_code == 200
    assert current.json()["status"] == "draft"
    assert {line["ingredient_name"] for line in current.json()["lines"]} == {
        "Basil",
        "Olive Oil",
        "Pasta",
        "Tomatoes",
    }

    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        published = session.scalar(
            select(PlannerEvent.published_at).where(PlannerEvent.source_mutation_id == "plan-confirmed-auto-001")
        )
        assert published is not None


def test_plan_confirmed_refresh_preserves_ad_hoc_lines_and_overrides(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Pasta", quantity="200", unit="grams", mutation_id="inv-plan-refresh-pasta")
    original = _derive(client, "derive-plan-refresh-001")["grocery_list"]
    pasta_line = next(line for line in original["lines"] if line["ingredient_name"] == "Pasta")

    add_response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{original['id']}/lines",
        json={
            "groceryListId": original["id"],
            "household_id": HOUSEHOLD,
            "ingredient_name": "Sparkling Water",
            "shopping_quantity": "2",
            "unit": "liters",
            "clientMutationId": "add-water-plan-refresh-001",
        },
    )
    assert add_response.status_code == 201

    adjust_response = client.patch(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{original['id']}/lines/{pasta_line['id']}",
        json={
            "groceryListItemId": pasta_line["id"],
            "household_id": HOUSEHOLD,
            "userAdjustedQuantity": "700",
            "userAdjustmentNote": "Need extra for guests",
            "clientMutationId": "adjust-pasta-plan-refresh-001",
        },
    )
    assert adjust_response.status_code == 200

    new_plan_id = _seed_confirmed_plan(
        grocery,
        version=4,
        slot_refs=[("Pasta Bake", "meal-pasta-bake"), ("Second Pasta Bake", "meal-pasta-bake")],
    )
    _enqueue_plan_confirmed_event(
        grocery,
        plan_id=new_plan_id,
        version=4,
        mutation_id="plan-confirmed-refresh-001",
    )

    processed = grocery.process_pending_plan_confirmed_events(HOUSEHOLD, actor_id="worker-grocery")

    assert processed == 1
    refreshed = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery?period={PERIOD_START.isoformat()}")
    assert refreshed.status_code == 200
    assert refreshed.json()["id"] == original["id"]
    assert refreshed.json()["current_version_number"] == 2
    lines = {line["ingredient_name"]: line for line in refreshed.json()["lines"]}
    assert "Sparkling Water" in lines
    assert lines["Sparkling Water"]["origin"] == "ad_hoc"
    assert lines["Pasta"]["user_adjusted_quantity"] == "700.0000"
    assert lines["Pasta"]["user_adjustment_flagged"] is True
    assert refreshed.json()["confirmed_plan_version"] == 4


def test_rederive_preserves_ad_hoc_lines_and_user_overrides(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Pasta", quantity="200", unit="grams", mutation_id="inv-rederive-pasta")
    original = _derive(client, "derive-refresh-001")["grocery_list"]
    pasta_line = next(line for line in original["lines"] if line["ingredient_name"] == "Pasta")

    add_response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{original['id']}/lines",
        json={
            "groceryListId": original["id"],
            "household_id": HOUSEHOLD,
            "ingredient_name": "Sparkling Water",
            "shopping_quantity": "2",
            "unit": "liters",
            "clientMutationId": "add-water-001",
        },
    )
    assert add_response.status_code == 201

    adjust_response = client.patch(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{original['id']}/lines/{pasta_line['id']}",
        json={
            "groceryListItemId": pasta_line["id"],
            "household_id": HOUSEHOLD,
            "userAdjustedQuantity": "700",
            "userAdjustmentNote": "Need extra for guests",
            "clientMutationId": "adjust-pasta-001",
        },
    )
    assert adjust_response.status_code == 200

    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        pasta = session.scalar(select(InventoryItem).where(InventoryItem.household_id == HOUSEHOLD, InventoryItem.name == "Pasta"))
        assert pasta is not None
        pasta.quantity_on_hand = Decimal("0.0000")
        pasta.version += 1
        pasta.updated_at = datetime.now(UTC).replace(tzinfo=None)
        session.commit()

    rederived = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{original['id']}/rederive",
        json={
            "household_id": HOUSEHOLD,
            "planPeriodStart": PERIOD_START.isoformat(),
            "clientMutationId": "rederive-001",
        },
    )
    assert rederived.status_code == 200
    lines = {line["ingredient_name"]: line for line in rederived.json()["grocery_list"]["lines"]}

    assert "Sparkling Water" in lines
    assert lines["Sparkling Water"]["origin"] == "ad_hoc"
    assert lines["Pasta"]["shopping_quantity"] == "800.0000"
    assert lines["Pasta"]["user_adjusted_quantity"] == "700.0000"
    assert lines["Pasta"]["user_adjustment_flagged"] is True


def test_plan_confirmed_refresh_creates_new_draft_from_confirmed_list(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Pasta", quantity="200", unit="grams", mutation_id="inv-plan-confirmed-pasta")
    derived = _derive(client, "derive-plan-confirmed-001")["grocery_list"]

    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}/confirm",
        json={
            "groceryListId": derived["id"],
            "household_id": HOUSEHOLD,
            "clientMutationId": "confirm-plan-confirmed-001",
        },
    )
    assert confirmed.status_code == 200

    new_plan_id = _seed_confirmed_plan(
        grocery,
        version=4,
        slot_refs=[("Pasta Bake", "meal-pasta-bake"), ("Second Pasta Bake", "meal-pasta-bake")],
    )
    _enqueue_plan_confirmed_event(
        grocery,
        plan_id=new_plan_id,
        version=4,
        mutation_id="plan-confirmed-new-draft-001",
    )

    processed = grocery.process_pending_plan_confirmed_events(HOUSEHOLD, actor_id="worker-grocery")

    assert processed == 1
    current = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery?period={PERIOD_START.isoformat()}")
    assert current.status_code == 200
    assert current.json()["id"] != derived["id"]
    assert current.json()["status"] == "draft"

    original_detail = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}")
    assert original_detail.status_code == 200
    assert original_detail.json()["status"] == "confirmed"


def test_confirmed_list_remains_stable_when_rederived(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(inventory, household_id=HOUSEHOLD, name="Pasta", quantity="200", unit="grams", mutation_id="inv-confirm-pasta")
    derived = _derive(client, "derive-confirm-001")["grocery_list"]

    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}/confirm",
        json={
            "groceryListId": derived["id"],
            "household_id": HOUSEHOLD,
            "clientMutationId": "confirm-001",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["grocery_list"]["status"] == "confirmed"

    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        pasta = session.scalar(select(InventoryItem).where(InventoryItem.household_id == HOUSEHOLD, InventoryItem.name == "Pasta"))
        assert pasta is not None
        pasta.quantity_on_hand = Decimal("0.0000")
        pasta.version += 1
        pasta.updated_at = datetime.now(UTC).replace(tzinfo=None)
        session.commit()

    refreshed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}/rederive",
        json={
            "household_id": HOUSEHOLD,
            "planPeriodStart": PERIOD_START.isoformat(),
            "clientMutationId": "rederive-after-confirm-001",
        },
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["grocery_list"]["id"] != derived["id"]
    assert refreshed.json()["grocery_list"]["status"] == "draft"

    original_detail = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}")
    assert original_detail.status_code == 200
    assert original_detail.json()["status"] == "confirmed"


def test_inventory_orchestration_only_marks_relevant_drafts_stale(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    pasta_id = inventory.create_item(
        CreateItemCommand(
            household_id=HOUSEHOLD,
            name="Pasta",
            storage_location=StorageLocation.pantry,
            initial_quantity=200,
            primary_unit="grams",
            freshness=FreshnessInfo(basis=FreshnessBasis.known, best_before="2026-03-20"),
            client_mutation_id="inv-relevant-create-pasta",
        ),
        actor_user_id=f"user-{HOUSEHOLD}",
    ).inventory_item_id
    _derive(client, "derive-relevant-stale-001")

    unrelated = client.post(
        "/api/v1/inventory",
        json={
            "household_id": HOUSEHOLD,
            "name": "Dish Soap",
            "storage_location": "pantry",
            "initial_quantity": 1,
            "primary_unit": "bottle",
            "freshness": {"basis": "known", "best_before": "2026-03-20"},
            "client_mutation_id": "inv-unrelated-create-001",
        },
    )
    assert unrelated.status_code == 201

    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        list_model = session.scalar(select(GroceryList).where(GroceryList.household_id == HOUSEHOLD))
        assert list_model is not None
        assert list_model.status == "draft"

    relevant = client.post(
        f"/api/v1/inventory/{pasta_id}/adjustments",
        json={
            "mutation_type": "set_quantity",
            "delta_quantity": 0,
            "reason_code": "correction",
            "client_mutation_id": "inv-relevant-adjust-001",
            "version": 1,
        },
    )
    assert relevant.status_code == 201

    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        list_model = session.scalar(select(GroceryList).where(GroceryList.household_id == HOUSEHOLD))
        assert list_model is not None
        assert list_model.status == "stale_draft"


def test_grocery_mutations_are_idempotent_and_household_scoped(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, _, grocery = shared_services
    _seed_confirmed_plan(grocery, household_id=HOUSEHOLD)
    _seed_confirmed_plan(grocery, household_id=OTHER_HOUSEHOLD)

    alpha_list = _derive(client, "derive-alpha-001")["grocery_list"]
    duplicate = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{alpha_list['id']}/lines",
        json={
            "groceryListId": alpha_list["id"],
            "household_id": HOUSEHOLD,
            "ingredient_name": "Coffee Beans",
            "shopping_quantity": "1",
            "unit": "bag",
            "clientMutationId": "shared-grocery-line-mutation",
        },
    )
    replay = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{alpha_list['id']}/lines",
        json={
            "groceryListId": alpha_list["id"],
            "household_id": HOUSEHOLD,
            "ingredient_name": "Coffee Beans",
            "shopping_quantity": "1",
            "unit": "bag",
            "clientMutationId": "shared-grocery-line-mutation",
        },
    )

    beta_headers = _session_headers(OTHER_HOUSEHOLD)
    beta_list = client.post(
        f"/api/v1/households/{OTHER_HOUSEHOLD}/grocery/derive",
        json={
            "household_id": OTHER_HOUSEHOLD,
            "planPeriodStart": PERIOD_START.isoformat(),
            "clientMutationId": "derive-beta-001",
        },
        headers=beta_headers,
    ).json()["grocery_list"]
    beta_add = client.post(
        f"/api/v1/households/{OTHER_HOUSEHOLD}/grocery/{beta_list['id']}/lines",
        json={
            "groceryListId": beta_list["id"],
            "household_id": OTHER_HOUSEHOLD,
            "ingredient_name": "Coffee Beans",
            "shopping_quantity": "1",
            "unit": "bag",
            "clientMutationId": "shared-grocery-line-mutation",
        },
        headers=beta_headers,
    )

    assert duplicate.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["is_duplicate"] is True
    assert duplicate.json()["item"]["id"] == replay.json()["item"]["id"]
    assert beta_add.status_code == 201
    assert beta_add.json()["is_duplicate"] is False
    assert beta_add.json()["item"]["id"] != duplicate.json()["item"]["id"]


def test_sync_upload_applies_confirmed_list_mutations_and_advances_server_version(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-apply-pasta",
    )
    derived = _derive(client, "derive-sync-apply-001")["grocery_list"]
    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}/confirm",
        json={
            "groceryListId": derived["id"],
            "household_id": HOUSEHOLD,
            "clientMutationId": "confirm-sync-apply-001",
        },
    )
    assert confirmed.status_code == 200
    confirmed_list = confirmed.json()["grocery_list"]
    pasta_line = next(line for line in confirmed_list["lines"] if line["ingredient_name"] == "Pasta")

    upload = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-add-water-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_list",
                "aggregate_id": confirmed_list["id"],
                "provisional_aggregate_id": "local-water-line-001",
                "mutation_type": "add_ad_hoc",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "ingredient_name": "Sparkling Water",
                    "shopping_quantity": "2",
                    "unit": "liters",
                    "ad_hoc_note": "Trip pickup",
                },
                "base_server_version": confirmed_list["current_version_number"],
                "device_timestamp": "2026-03-09T12:00:00Z",
                "local_queue_status": "queued_offline",
            },
            {
                "client_mutation_id": "sync-adjust-pasta-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "900",
                    "user_adjustment_note": "Need extra for guests",
                },
                "base_server_version": confirmed_list["current_version_number"],
                "device_timestamp": "2026-03-09T12:05:00Z",
                "local_queue_status": "queued_offline",
            },
        ],
    )

    assert upload.status_code == 200, upload.text
    outcomes = upload.json()
    assert [outcome["outcome"] for outcome in outcomes] == ["applied", "applied"]
    assert [outcome["authoritative_server_version"] for outcome in outcomes] == [2, 3]
    assert outcomes[0]["aggregate"]["aggregate_type"] == "grocery_line"
    assert outcomes[0]["aggregate"]["provisional_aggregate_id"] == "local-water-line-001"

    current = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/{confirmed_list['id']}")
    assert current.status_code == 200
    payload = current.json()
    assert payload["status"] == "trip_in_progress"
    assert payload["trip_state"] == "trip_in_progress"
    assert payload["current_version_number"] == 3
    lines = {line["ingredient_name"]: line for line in payload["lines"]}
    assert lines["Sparkling Water"]["origin"] == "ad_hoc"
    assert lines["Sparkling Water"]["ad_hoc_note"] == "Trip pickup"
    assert lines["Pasta"]["user_adjusted_quantity"] == "900.0000"
    assert lines["Pasta"]["user_adjustment_flagged"] is True


def test_sync_upload_replays_duplicate_receipts_and_keeps_household_scope(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery, household_id=HOUSEHOLD)
    _seed_confirmed_plan(grocery, household_id=OTHER_HOUSEHOLD)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-dup-alpha",
    )
    _create_inventory_item(
        inventory,
        household_id=OTHER_HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-dup-beta",
    )
    alpha_list = _derive(client, "derive-sync-dup-alpha")["grocery_list"]
    beta_headers = _session_headers(OTHER_HOUSEHOLD)
    beta_list = client.post(
        f"/api/v1/households/{OTHER_HOUSEHOLD}/grocery/derive",
        json={
            "household_id": OTHER_HOUSEHOLD,
            "planPeriodStart": PERIOD_START.isoformat(),
            "clientMutationId": "derive-sync-dup-beta",
        },
        headers=beta_headers,
    ).json()["grocery_list"]
    for household_id, grocery_list_id, headers, mutation_id in (
        (HOUSEHOLD, alpha_list["id"], None, "confirm-sync-dup-alpha"),
        (OTHER_HOUSEHOLD, beta_list["id"], beta_headers, "confirm-sync-dup-beta"),
    ):
        response = client.post(
            f"/api/v1/households/{household_id}/grocery/{grocery_list_id}/confirm",
            json={
                "groceryListId": grocery_list_id,
                "household_id": household_id,
                "clientMutationId": mutation_id,
            },
            headers=headers,
        )
        assert response.status_code == 200

    alpha_sync_payload = [
        {
            "client_mutation_id": "shared-sync-upload-id",
            "household_id": HOUSEHOLD,
            "actor_id": f"user-{HOUSEHOLD}",
            "aggregate_type": "grocery_list",
            "aggregate_id": alpha_list["id"],
            "provisional_aggregate_id": "local-alpha-water",
            "mutation_type": "add_ad_hoc",
            "payload": {
                "grocery_list_id": alpha_list["id"],
                "ingredient_name": "Coffee Beans",
                "shopping_quantity": "1",
                "unit": "bag",
            },
            "base_server_version": 1,
            "device_timestamp": "2026-03-09T12:10:00Z",
            "local_queue_status": "queued_offline",
        }
    ]
    alpha_first = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=alpha_sync_payload,
    )
    alpha_second = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=alpha_sync_payload,
    )
    beta_sync = client.post(
        f"/api/v1/households/{OTHER_HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                **alpha_sync_payload[0],
                "household_id": OTHER_HOUSEHOLD,
                "aggregate_id": beta_list["id"],
                "payload": {
                    "grocery_list_id": beta_list["id"],
                    "ingredient_name": "Coffee Beans",
                    "shopping_quantity": "1",
                    "unit": "bag",
                },
            }
        ],
        headers=beta_headers,
    )

    assert alpha_first.status_code == 200
    assert alpha_second.status_code == 200
    assert beta_sync.status_code == 200
    assert alpha_first.json()[0]["outcome"] == "applied"
    assert alpha_second.json()[0]["outcome"] == "duplicate_retry"
    assert alpha_second.json()[0]["duplicate_of_client_mutation_id"] == "shared-sync-upload-id"
    assert beta_sync.json()[0]["outcome"] == "applied"
    assert beta_sync.json()[0]["aggregate"]["aggregate_id"] != alpha_first.json()[0]["aggregate"]["aggregate_id"]


def test_sync_upload_auto_merges_stale_non_overlapping_adds(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-auto-merge-pasta",
    )
    derived = _derive(client, "derive-sync-auto-merge-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id="confirm-sync-auto-merge-001",
    )

    accepted = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-auto-merge-server-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_list",
                "aggregate_id": confirmed_list["id"],
                "provisional_aggregate_id": "local-server-snack-001",
                "mutation_type": "add_ad_hoc",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "ingredient_name": "Trail Mix",
                    "shopping_quantity": "1",
                    "unit": "bag",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:15:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()[0]["outcome"] == "applied"

    stale_upload = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-auto-merge-local-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_list",
                "aggregate_id": confirmed_list["id"],
                "provisional_aggregate_id": "local-water-line-002",
                "mutation_type": "add_ad_hoc",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "ingredient_name": "Sparkling Water",
                    "shopping_quantity": "2",
                    "unit": "liters",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:16:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )

    assert stale_upload.status_code == 200, stale_upload.text
    outcome = stale_upload.json()[0]
    assert outcome["outcome"] == "auto_merged_non_overlapping"
    assert outcome["authoritative_server_version"] == 3
    assert outcome["auto_merge_reason"] is not None
    assert "new ad hoc line" in outcome["auto_merge_reason"]

    current = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/{confirmed_list['id']}")
    assert current.status_code == 200
    lines = {line["ingredient_name"]: line for line in current.json()["lines"]}
    assert "Trail Mix" in lines
    assert "Sparkling Water" in lines


def test_sync_upload_classifies_deleted_lines_as_review_required_deleted_or_archived(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-delete-pasta",
    )
    derived = _derive(client, "derive-sync-delete-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id="confirm-sync-delete-001",
    )
    pasta_line = next(line for line in confirmed_list["lines"] if line["ingredient_name"] == "Pasta")

    remove_line = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-remove-pasta-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "remove_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:30:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert remove_line.status_code == 200, remove_line.text
    assert remove_line.json()[0]["outcome"] == "applied"

    stale_adjust = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-stale-adjust-pasta-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "900",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:31:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )

    assert stale_adjust.status_code == 200, stale_adjust.text
    outcome = stale_adjust.json()[0]
    assert outcome["outcome"] == "review_required_deleted_or_archived"
    assert outcome["conflict_id"] is not None


def test_sync_upload_creates_conflict_and_still_applies_other_list_mutations_in_same_batch(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    second_period = date(2026, 3, 16)
    _seed_confirmed_plan(grocery, period_start=PERIOD_START, plan_id="plan-sync-conflict-1")
    _seed_confirmed_plan(grocery, period_start=second_period, plan_id="plan-sync-conflict-2", version=4)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-conflict-pasta",
    )
    first_list = _derive(client, "derive-sync-conflict-001")["grocery_list"]
    second_list_response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/derive",
        json={
            "household_id": HOUSEHOLD,
            "planPeriodStart": second_period.isoformat(),
            "clientMutationId": "derive-sync-conflict-002",
        },
    )
    assert second_list_response.status_code == 201
    second_list = second_list_response.json()["grocery_list"]
    for grocery_list_id, mutation_id in (
        (first_list["id"], "confirm-sync-conflict-001"),
        (second_list["id"], "confirm-sync-conflict-002"),
    ):
        response = client.post(
            f"/api/v1/households/{HOUSEHOLD}/grocery/{grocery_list_id}/confirm",
            json={
                "groceryListId": grocery_list_id,
                "household_id": HOUSEHOLD,
                "clientMutationId": mutation_id,
            },
        )
        assert response.status_code == 200

    first_detail = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/{first_list['id']}").json()
    pasta_line = next(line for line in first_detail["lines"] if line["ingredient_name"] == "Pasta")
    advance = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-conflict-advance-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": first_list["id"],
                    "quantity_to_buy": "850",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:20:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert advance.status_code == 200
    assert advance.json()[0]["outcome"] == "applied"

    stale_batch = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-conflict-stale-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": first_list["id"],
                    "quantity_to_buy": "900",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:25:00Z",
                "local_queue_status": "queued_offline",
            },
            {
                "client_mutation_id": "sync-conflict-stop-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_list",
                "aggregate_id": first_list["id"],
                "provisional_aggregate_id": "local-stop-line-001",
                "mutation_type": "add_ad_hoc",
                "payload": {
                    "grocery_list_id": first_list["id"],
                    "ingredient_name": "Soda",
                    "shopping_quantity": "2",
                    "unit": "cans",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:25:30Z",
                "local_queue_status": "queued_offline",
            },
            {
                "client_mutation_id": "sync-conflict-other-list-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_list",
                "aggregate_id": second_list["id"],
                "provisional_aggregate_id": "local-snack-line-001",
                "mutation_type": "add_ad_hoc",
                "payload": {
                    "grocery_list_id": second_list["id"],
                    "ingredient_name": "Trail Mix",
                    "shopping_quantity": "1",
                    "unit": "bag",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:26:00Z",
                "local_queue_status": "queued_offline",
            },
        ],
    )

    assert stale_batch.status_code == 200, stale_batch.text
    outcomes = stale_batch.json()
    assert outcomes[0]["outcome"] == "review_required_quantity"
    assert outcomes[0]["conflict_id"] is not None
    assert outcomes[1]["outcome"] == "review_required_other_unsafe"
    assert outcomes[1]["conflict_id"] is not None
    assert outcomes[2]["outcome"] == "applied"

    conflicts = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts")
    assert conflicts.status_code == 200
    conflict = next(entry for entry in conflicts.json() if entry["conflict_id"] == outcomes[0]["conflict_id"])
    assert conflict["local_mutation_id"] == "sync-conflict-stale-001"
    assert conflict["allowed_resolution_actions"] == ["keep_mine", "use_server"]
    assert conflict["current_server_version"] == 2
    stopped = next(entry for entry in conflicts.json() if entry["conflict_id"] == outcomes[1]["conflict_id"])
    assert stopped["local_mutation_id"] == "sync-conflict-stop-001"
    assert "already needs review" in stopped["summary"]

    conflict_detail = client.get(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{outcomes[0]['conflict_id']}"
    )
    assert conflict_detail.status_code == 200
    detail = conflict_detail.json()
    assert detail["local_intent_summary"]["payload"]["quantity_to_buy"] == "900"
    assert detail["base_state_summary"]["grocery_line_id"] == pasta_line["grocery_line_id"]
    assert detail["server_state_summary"]["user_adjusted_quantity"] == "850.0000"

    refreshed_second_list = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/{second_list['id']}")
    assert refreshed_second_list.status_code == 200
    assert any(
        line["ingredient_name"] == "Trail Mix" for line in refreshed_second_list.json()["lines"]
    )


def test_sync_conflict_keep_mine_replays_latest_intent_and_marks_conflict_resolved(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-resolve-keep-pasta",
    )
    derived = _derive(client, "derive-sync-resolve-keep-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id="confirm-sync-resolve-keep-001",
    )
    pasta_line = next(line for line in confirmed_list["lines"] if line["ingredient_name"] == "Pasta")

    advance = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-resolve-keep-advance-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "850",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:40:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert advance.status_code == 200
    assert advance.json()[0]["outcome"] == "applied"

    stale = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-resolve-keep-stale-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "900",
                    "user_adjustment_note": "Need extra for guests",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:41:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert stale.status_code == 200, stale.text
    conflict_id = stale.json()[0]["conflict_id"]
    assert stale.json()[0]["outcome"] == "review_required_quantity"

    resolved = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}/resolve-keep-mine",
        json={
            "conflict_id": conflict_id,
            "household_id": HOUSEHOLD,
            "client_mutation_id": "sync-resolve-keep-command-001",
            "base_server_version": 2,
        },
    )
    assert resolved.status_code == 200, resolved.text
    resolved_payload = resolved.json()["grocery_list"]
    assert resolved.json()["mutation_kind"] == "resolve_keep_mine"
    assert resolved_payload["current_version_number"] == 3
    pasta = next(line for line in resolved_payload["lines"] if line["ingredient_name"] == "Pasta")
    assert pasta["user_adjusted_quantity"] == "900.0000"
    assert pasta["user_adjustment_note"] == "Need extra for guests"

    detail = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}")
    assert detail.status_code == 200
    assert detail.json()["resolution_status"] == "resolved_keep_mine"
    assert detail.json()["local_queue_status"] == "resolved_keep_mine"
    assert detail.json()["allowed_resolution_actions"] == []
    assert detail.json()["resolved_at"] is not None
    assert detail.json()["resolved_by_actor_id"] is not None
    assert detail.json()["local_intent_summary"]["resolution"]["action"] == "keep_mine"
    assert (
        detail.json()["local_intent_summary"]["resolution"]["client_mutation_id"]
        == "sync-resolve-keep-command-001"
    )


def test_sync_conflict_keep_mine_can_restore_deleted_line_when_user_reaffirms_intent(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-resolve-restore-pasta",
    )
    derived = _derive(client, "derive-sync-resolve-restore-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id="confirm-sync-resolve-restore-001",
    )
    pasta_line = next(line for line in confirmed_list["lines"] if line["ingredient_name"] == "Pasta")

    remove_line = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-resolve-restore-remove-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "remove_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:50:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert remove_line.status_code == 200
    assert remove_line.json()[0]["outcome"] == "applied"

    stale_adjust = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-resolve-restore-stale-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "925",
                    "user_adjustment_note": "Still need pasta",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T12:51:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert stale_adjust.status_code == 200, stale_adjust.text
    conflict_id = stale_adjust.json()[0]["conflict_id"]
    assert stale_adjust.json()[0]["outcome"] == "review_required_deleted_or_archived"

    resolved = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}/resolve-keep-mine",
        json={
            "conflict_id": conflict_id,
            "household_id": HOUSEHOLD,
            "client_mutation_id": "sync-resolve-restore-command-001",
        },
    )
    assert resolved.status_code == 200, resolved.text
    restored_lines = {line["ingredient_name"]: line for line in resolved.json()["grocery_list"]["lines"]}
    assert restored_lines["Pasta"]["user_adjusted_quantity"] == "925.0000"
    assert restored_lines["Pasta"]["active"] is True

    detail = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}")
    assert detail.status_code == 200
    assert detail.json()["resolution_status"] == "resolved_keep_mine"
    assert detail.json()["server_state_summary"]["user_adjusted_quantity"] == "925.0000"


def test_sync_conflict_use_server_refreshes_latest_read_model_and_is_idempotent(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-resolve-server-pasta",
    )
    derived = _derive(client, "derive-sync-resolve-server-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id="confirm-sync-resolve-server-001",
    )
    pasta_line = next(line for line in confirmed_list["lines"] if line["ingredient_name"] == "Pasta")

    advance = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-resolve-server-advance-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "850",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T13:00:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert advance.status_code == 200

    stale = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-resolve-server-stale-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "900",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T13:01:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert stale.status_code == 200, stale.text
    conflict_id = stale.json()[0]["conflict_id"]

    latest_change = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/upload",
        json=[
            {
                "client_mutation_id": "sync-resolve-server-latest-001",
                "household_id": HOUSEHOLD,
                "actor_id": f"user-{HOUSEHOLD}",
                "aggregate_type": "grocery_list",
                "aggregate_id": confirmed_list["id"],
                "provisional_aggregate_id": "local-water-latest-001",
                "mutation_type": "add_ad_hoc",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "ingredient_name": "Sparkling Water",
                    "shopping_quantity": "2",
                    "unit": "liters",
                },
                "base_server_version": 2,
                "device_timestamp": "2026-03-09T13:02:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    assert latest_change.status_code == 200, latest_change.text
    assert latest_change.json()[0]["authoritative_server_version"] == 3

    detail = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}")
    assert detail.status_code == 200
    assert detail.json()["current_server_version"] == 3

    resolved = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}/resolve-use-server",
        json={
            "conflict_id": conflict_id,
            "household_id": HOUSEHOLD,
            "client_mutation_id": "sync-resolve-server-command-001",
        },
    )
    replay = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}/resolve-use-server",
        json={
            "conflict_id": conflict_id,
            "household_id": HOUSEHOLD,
            "client_mutation_id": "sync-resolve-server-command-001",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert replay.status_code == 200, replay.text
    assert resolved.json()["mutation_kind"] == "resolve_use_server"
    assert replay.json()["grocery_list"]["current_version_number"] == 3
    assert any(
        line["ingredient_name"] == "Sparkling Water"
        for line in resolved.json()["grocery_list"]["lines"]
    )

    refreshed_conflict = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_id}")
    assert refreshed_conflict.status_code == 200
    assert refreshed_conflict.json()["resolution_status"] == "resolved_use_server"
    assert refreshed_conflict.json()["local_queue_status"] == "resolved_use_server"
    assert refreshed_conflict.json()["current_server_version"] == 3
    assert refreshed_conflict.json()["allowed_resolution_actions"] == []


def test_confirmed_list_exposes_stable_version_identity_and_line_ids(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
) -> None:
    _, inventory, grocery = shared_services
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-confirmed-handoff-pasta",
    )
    derived = _derive(client, "derive-confirmed-handoff-001")["grocery_list"]
    original_version_id = derived["grocery_list_version_id"]
    original_line_ids = {
        line["ingredient_name"]: line["grocery_line_id"]
        for line in derived["lines"]
    }

    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}/confirm",
        json={
            "groceryListId": derived["id"],
            "household_id": HOUSEHOLD,
            "clientMutationId": "confirm-confirmed-handoff-001",
        },
    )

    assert confirmed.status_code == 200
    confirmed_list = confirmed.json()["grocery_list"]
    assert confirmed_list["status"] == "confirmed"
    assert confirmed_list["confirmed_at"] is not None
    assert confirmed_list["grocery_list_version_id"] == original_version_id
    assert confirmed_list["current_version_id"] == original_version_id

    with grocery._session_factory() as session:  # noqa: SLF001 - shared test seam
        pasta = session.scalar(
            select(InventoryItem).where(
                InventoryItem.household_id == HOUSEHOLD,
                InventoryItem.name == "Pasta",
            )
        )
        assert pasta is not None
        pasta.quantity_on_hand = Decimal("0.0000")
        pasta.version += 1
        pasta.updated_at = datetime.now(UTC).replace(tzinfo=None)
        session.commit()

    refreshed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}/rederive",
        json={
            "household_id": HOUSEHOLD,
            "planPeriodStart": PERIOD_START.isoformat(),
            "clientMutationId": "rederive-confirmed-handoff-001",
        },
    )

    assert refreshed.status_code == 200
    assert refreshed.json()["grocery_list"]["id"] != derived["id"]

    original_detail = client.get(f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}")
    assert original_detail.status_code == 200
    original_payload = original_detail.json()
    assert original_payload["status"] == "confirmed"
    assert original_payload["grocery_list_version_id"] == original_version_id
    assert {
        line["ingredient_name"]: line["grocery_line_id"]
        for line in original_payload["lines"]
    } == original_line_ids


def test_derive_logs_correlation_and_incomplete_slot_diagnostics(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, inventory, grocery = shared_services
    caplog.set_level("INFO", logger="app.services.grocery_service")
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-derive-diagnostics-pasta",
    )

    body = _derive(client, DERIVATION_DIAGNOSTIC_FIXTURE.client_mutation_id)

    accepted = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_action", None) == "derive"
        and getattr(record, "grocery_outcome", None) == "accepted"
    )
    assert accepted.grocery_correlation_id == DERIVATION_DIAGNOSTIC_FIXTURE.correlation_id
    assert accepted.grocery_list_id == body["grocery_list"]["id"]
    assert accepted.grocery_list_version_id == body["grocery_list"]["grocery_list_version_id"]
    assert accepted.grocery_raw_need_count == 6
    assert accepted.grocery_incomplete_slot_count == 1
    assert accepted.grocery_unmatched_need_count >= 1

    incomplete = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_action", None) == "derivation_incomplete_slots"
    )
    assert incomplete.grocery_correlation_id == DERIVATION_DIAGNOSTIC_FIXTURE.correlation_id
    assert incomplete.grocery_list_version_id == body["grocery_list"]["grocery_list_version_id"]
    assert incomplete.grocery_incomplete_slot_count == 1
    assert incomplete.grocery_incomplete_slot_ids == [f"slot-{HOUSEHOLD}-v3-2"]


def test_inventory_stale_detection_logs_correlation_and_reason(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, inventory, grocery = shared_services
    caplog.set_level("INFO", logger="app.services.grocery_service")
    _seed_confirmed_plan(grocery)
    pasta_id = inventory.create_item(
        CreateItemCommand(
            household_id=HOUSEHOLD,
            name="Pasta",
            storage_location=StorageLocation.pantry,
            initial_quantity=200,
            primary_unit="grams",
            freshness=FreshnessInfo(basis=FreshnessBasis.known, best_before="2026-03-20"),
            client_mutation_id="inv-stale-log-create-pasta",
        ),
        actor_user_id=f"user-{HOUSEHOLD}",
    ).inventory_item_id
    derived = _derive(client, "derive-stale-log-001")["grocery_list"]

    response = client.post(
        f"/api/v1/inventory/{pasta_id}/adjustments",
        json={
            "mutation_type": "set_quantity",
            "delta_quantity": 0,
            "reason_code": "correction",
            "client_mutation_id": STALE_DETECTION_FIXTURE.client_mutation_id,
            "version": 1,
        },
    )

    assert response.status_code == 201
    detected = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_action", None) == "stale_detection"
        and getattr(record, "grocery_outcome", None) == "detected"
    )
    assert detected.grocery_correlation_id == STALE_DETECTION_FIXTURE.correlation_id
    assert detected.grocery_list_id == derived["id"]
    assert detected.grocery_list_version_id == derived["grocery_list_version_id"]
    assert detected.grocery_stale_reason == "inventory_snapshot_changed"


def test_confirm_list_logs_correlation_and_version_diagnostics(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, inventory, grocery = shared_services
    caplog.set_level("INFO", logger="app.services.grocery_service")
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-confirm-diagnostics-pasta",
    )
    derived = _derive(client, "derive-confirm-diagnostics-001")["grocery_list"]

    response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/{derived['id']}/confirm",
        json={
            "groceryListId": derived["id"],
            "household_id": HOUSEHOLD,
            "clientMutationId": CONFIRMATION_DIAGNOSTIC_FIXTURE.client_mutation_id,
        },
    )

    assert response.status_code == 200
    confirmed = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_action", None) == "confirm_list"
        and getattr(record, "grocery_outcome", None) == "accepted"
    )
    assert confirmed.grocery_correlation_id == CONFIRMATION_DIAGNOSTIC_FIXTURE.correlation_id
    assert confirmed.grocery_list_id == derived["id"]
    assert confirmed.grocery_list_version_id == derived["grocery_list_version_id"]
    assert confirmed.grocery_confirmed_at == response.json()["grocery_list"]["confirmed_at"]


def test_sync_upload_logs_duplicate_retry_diagnostics(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, inventory, grocery = shared_services
    caplog.set_level("INFO", logger="app.services.grocery_service")
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-duplicate-log-pasta",
    )
    derived = _derive(client, "derive-sync-duplicate-log-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id="confirm-sync-duplicate-log-001",
    )

    duplicate_payload = build_sync_add_ad_hoc_mutation(
        SYNC_DUPLICATE_RETRY_FIXTURE,
        household_id=HOUSEHOLD,
        actor_id=_actor_id(),
        grocery_list_id=confirmed_list["id"],
        ingredient_name="Sparkling Water",
        shopping_quantity="2",
        unit="liters",
        ad_hoc_note="Reconnect retry",
    )

    first_outcome = _upload_sync_mutations(client, [duplicate_payload])[0]
    second_outcome = _upload_sync_mutations(client, [duplicate_payload])[0]

    assert first_outcome["outcome"] == "applied"
    assert second_outcome["outcome"] == "duplicate_retry"

    duplicate = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_outcome", None) == "duplicate_retry"
        and getattr(record, "grocery_client_mutation_id", None)
        == SYNC_DUPLICATE_RETRY_FIXTURE.client_mutation_id
    )
    assert duplicate.grocery_action == "sync_add_ad_hoc"
    assert duplicate.grocery_correlation_id == SYNC_DUPLICATE_RETRY_FIXTURE.correlation_id
    assert duplicate.grocery_aggregate_type == "grocery_line"
    assert duplicate.grocery_aggregate_id == first_outcome["aggregate"]["aggregate_id"]
    assert duplicate.grocery_aggregate_version == second_outcome["authoritative_server_version"]
    assert duplicate.grocery_provisional_aggregate_id == SYNC_DUPLICATE_RETRY_FIXTURE.provisional_aggregate_id


def test_sync_upload_logs_auto_merge_and_review_required_conflict_diagnostics(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, inventory, grocery = shared_services
    caplog.set_level("INFO", logger="app.services.grocery_service")
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id="inv-sync-observability-pasta",
    )
    derived = _derive(client, "derive-sync-observability-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id="confirm-sync-observability-001",
    )
    pasta_line = next(line for line in confirmed_list["lines"] if line["ingredient_name"] == "Pasta")

    _upload_sync_mutations(
        client,
        [
            {
                "client_mutation_id": "sync-observability-advance-001",
                "household_id": HOUSEHOLD,
                "actor_id": _actor_id(),
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "850",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T14:02:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )

    auto_merged = _upload_sync_mutations(
        client,
        [
            build_sync_add_ad_hoc_mutation(
                SYNC_AUTO_MERGE_FIXTURE,
                household_id=HOUSEHOLD,
                actor_id=_actor_id(),
                grocery_list_id=confirmed_list["id"],
                ingredient_name="Trail Mix",
                shopping_quantity="1",
                unit="bag",
                ad_hoc_note="Safe reconnect add",
            )
        ],
    )[0]
    conflicted = _upload_sync_mutations(
        client,
        [
            build_sync_adjust_line_mutation(
                SYNC_REVIEW_REQUIRED_FIXTURE,
                household_id=HOUSEHOLD,
                actor_id=_actor_id(),
                grocery_list_id=confirmed_list["id"],
                grocery_line_id=pasta_line["grocery_line_id"],
                quantity_to_buy="900",
                user_adjustment_note="Need extra for guests",
            )
        ],
    )[0]

    assert auto_merged["outcome"] == "auto_merged_non_overlapping"
    assert conflicted["outcome"] == "review_required_quantity"

    auto_merge_log = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_outcome", None) == "auto_merged_non_overlapping"
        and getattr(record, "grocery_client_mutation_id", None) == SYNC_AUTO_MERGE_FIXTURE.client_mutation_id
    )
    assert auto_merge_log.grocery_correlation_id == SYNC_AUTO_MERGE_FIXTURE.correlation_id
    assert auto_merge_log.grocery_provisional_aggregate_id == SYNC_AUTO_MERGE_FIXTURE.provisional_aggregate_id
    assert auto_merge_log.grocery_base_server_version == SYNC_AUTO_MERGE_FIXTURE.base_server_version
    assert auto_merge_log.grocery_current_server_version == auto_merged["authoritative_server_version"]
    assert "new ad hoc line" in auto_merge_log.grocery_auto_merge_reason

    conflict_log = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_outcome", None) == "review_required_quantity"
        and getattr(record, "grocery_client_mutation_id", None)
        == SYNC_REVIEW_REQUIRED_FIXTURE.client_mutation_id
    )
    assert conflict_log.grocery_correlation_id == SYNC_REVIEW_REQUIRED_FIXTURE.correlation_id
    assert conflict_log.grocery_conflict_id == conflicted["conflict_id"]
    assert conflict_log.grocery_aggregate_type == "grocery_line"
    assert conflict_log.grocery_aggregate_id == pasta_line["grocery_line_id"]
    assert conflict_log.grocery_base_server_version == SYNC_REVIEW_REQUIRED_FIXTURE.base_server_version
    assert conflict_log.grocery_current_server_version == conflicted["authoritative_server_version"]
    assert "changed quantity" in conflict_log.grocery_sync_summary


@pytest.mark.parametrize(
    ("endpoint", "fixture", "expected_outcome", "expected_action"),
    [
        (
            "resolve-keep-mine",
            SYNC_KEEP_MINE_RESOLUTION_FIXTURE,
            "resolved_keep_mine",
            "keep_mine",
        ),
        (
            "resolve-use-server",
            SYNC_USE_SERVER_RESOLUTION_FIXTURE,
            "resolved_use_server",
            "use_server",
        ),
    ],
)
def test_sync_conflict_resolution_logs_manual_resolution_diagnostics(
    client: TestClient,
    shared_services: tuple[PlannerService, InventoryStore, GroceryService],
    caplog: pytest.LogCaptureFixture,
    endpoint: str,
    fixture,
    expected_outcome: str,
    expected_action: str,
) -> None:
    _, inventory, grocery = shared_services
    caplog.set_level("INFO", logger="app.services.grocery_service")
    _seed_confirmed_plan(grocery)
    _create_inventory_item(
        inventory,
        household_id=HOUSEHOLD,
        name="Pasta",
        quantity="200",
        unit="grams",
        mutation_id=f"inv-{expected_action}-resolution-log-pasta",
    )
    derived = _derive(client, f"derive-{expected_action}-resolution-log-001")["grocery_list"]
    confirmed_list = _confirm_list(
        client,
        derived["id"],
        mutation_id=f"confirm-{expected_action}-resolution-log-001",
    )
    pasta_line = next(line for line in confirmed_list["lines"] if line["ingredient_name"] == "Pasta")

    _upload_sync_mutations(
        client,
        [
            {
                "client_mutation_id": f"sync-{expected_action}-resolution-advance-001",
                "household_id": HOUSEHOLD,
                "actor_id": _actor_id(),
                "aggregate_type": "grocery_line",
                "aggregate_id": pasta_line["grocery_line_id"],
                "mutation_type": "adjust_line",
                "payload": {
                    "grocery_list_id": confirmed_list["id"],
                    "quantity_to_buy": "850",
                },
                "base_server_version": 1,
                "device_timestamp": "2026-03-09T14:15:00Z",
                "local_queue_status": "queued_offline",
            }
        ],
    )
    conflict_outcome = _upload_sync_mutations(
        client,
        [
            build_sync_adjust_line_mutation(
                SYNC_REVIEW_REQUIRED_FIXTURE,
                household_id=HOUSEHOLD,
                actor_id=_actor_id(),
                grocery_list_id=confirmed_list["id"],
                grocery_line_id=pasta_line["grocery_line_id"],
                quantity_to_buy="900",
                user_adjustment_note="Need extra for guests",
            )
        ],
    )[0]
    assert conflict_outcome["outcome"] == "review_required_quantity"

    command: dict[str, object] = {
        "conflict_id": conflict_outcome["conflict_id"],
        "household_id": HOUSEHOLD,
        "client_mutation_id": fixture.client_mutation_id,
    }
    if endpoint == "resolve-keep-mine":
        command["base_server_version"] = 2

    response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/sync/conflicts/{conflict_outcome['conflict_id']}/{endpoint}",
        json=command,
        headers=_session_headers(HOUSEHOLD),
    )

    assert response.status_code == 200, response.text

    resolution_log = next(
        record
        for record in caplog.records
        if getattr(record, "grocery_outcome", None) == expected_outcome
        and getattr(record, "grocery_client_mutation_id", None) == fixture.client_mutation_id
    )
    assert resolution_log.grocery_action == f"sync_resolution_{expected_action}"
    assert resolution_log.grocery_correlation_id == fixture.correlation_id
    assert resolution_log.grocery_conflict_id == conflict_outcome["conflict_id"]
    assert resolution_log.grocery_resolution_action == expected_action
    assert resolution_log.grocery_aggregate_type == "grocery_line"
    assert resolution_log.grocery_aggregate_id == pasta_line["grocery_line_id"]
    assert resolution_log.grocery_base_server_version == 2
    assert resolution_log.grocery_current_server_version >= 2


def test_derive_requires_confirmed_plan(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/grocery/derive",
        json={
            "household_id": HOUSEHOLD,
            "planPeriodStart": PERIOD_START.isoformat(),
            "clientMutationId": "derive-without-plan",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "confirmed_plan_not_found"
