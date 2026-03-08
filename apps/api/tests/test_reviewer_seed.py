from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL

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
from app.seeds import (
    REVIEWER_HOUSEHOLD_ID,
    REVIEWER_HOUSEHOLD_NAME,
    REVIEWER_USER_EMAIL,
    REVIEWER_USER_ID,
    REVIEWER_USER_NAME,
    SECONDARY_HOUSEHOLD_ID,
    SECONDARY_HOUSEHOLD_NAME,
    REVIEWER_PLAN_PERIOD_START,
    seed_reviewer_data,
)
from app.services.grocery_service import GroceryService, get_grocery_service
from app.services.inventory_store import InventoryStore, get_inventory_store
from app.services.planner_service import PlannerService, get_planner_service


def _session_headers() -> dict[str, str]:
    return {
        DEV_USER_ID_HEADER: REVIEWER_USER_ID,
        DEV_USER_EMAIL_HEADER: REVIEWER_USER_EMAIL,
        DEV_USER_NAME_HEADER: REVIEWER_USER_NAME,
        DEV_ACTIVE_HOUSEHOLD_ID_HEADER: REVIEWER_HOUSEHOLD_ID,
        DEV_ACTIVE_HOUSEHOLD_NAME_HEADER: REVIEWER_HOUSEHOLD_NAME,
        DEV_ACTIVE_HOUSEHOLD_ROLE_HEADER: "owner",
        DEV_HOUSEHOLDS_HEADER: (
            f'[{{"household_id":"{REVIEWER_HOUSEHOLD_ID}","household_name":"{REVIEWER_HOUSEHOLD_NAME}","role":"owner"}},'
            f'{{"household_id":"{SECONDARY_HOUSEHOLD_ID}","household_name":"{SECONDARY_HOUSEHOLD_NAME}","role":"owner"}}]'
        ),
    }


def _build_client(database_url: URL) -> tuple[TestClient, PlannerService, InventoryStore, GroceryService]:
    planner = PlannerService(database_url=database_url)
    inventory = InventoryStore(database_url=database_url)
    grocery = GroceryService(database_url=database_url)
    app.dependency_overrides[get_planner_service] = lambda: planner
    app.dependency_overrides[get_inventory_store] = lambda: inventory
    app.dependency_overrides[get_grocery_service] = lambda: grocery
    client = TestClient(app)
    client.headers.update(_session_headers())
    return client, planner, inventory, grocery


def _dispose_services(planner: PlannerService, inventory: InventoryStore, grocery: GroceryService) -> None:
    app.dependency_overrides.pop(get_planner_service, None)
    app.dependency_overrides.pop(get_inventory_store, None)
    app.dependency_overrides.pop(get_grocery_service, None)
    planner.dispose()
    inventory.dispose()
    grocery.dispose()


def test_reviewer_seed_is_resettable_and_stable(tmp_path: Path) -> None:
    database_url = URL.create("sqlite+pysqlite", database=str((tmp_path / "reviewer-seed.sqlite").resolve()))

    first = seed_reviewer_data(database_url=database_url)
    second = seed_reviewer_data(database_url=database_url)

    assert first.household_id == second.household_id
    assert first.confirmed_plan_id == second.confirmed_plan_id
    assert first.grocery_list_id == second.grocery_list_id
    assert first.grocery_list_version_id == second.grocery_list_version_id
    assert first.inventory_item_ids == second.inventory_item_ids


def test_reviewer_seed_supports_inventory_planner_and_grocery_review(tmp_path: Path) -> None:
    database_url = URL.create("sqlite+pysqlite", database=str((tmp_path / "reviewer-review.sqlite").resolve()))
    seed_reviewer_data(database_url=database_url)

    client, planner, inventory, grocery = _build_client(database_url)
    try:
        inventory_response = client.get("/api/v1/inventory")
        assert inventory_response.status_code == 200
        inventory_body = inventory_response.json()
        assert inventory_body["total"] >= 10
        assert {item["storage_location"] for item in inventory_body["items"]} == {
            "fridge",
            "freezer",
            "leftovers",
            "pantry",
        }

        history_response = client.get(
            "/api/v1/inventory/66666666-6666-6666-6666-666666666604/history"
        )
        assert history_response.status_code == 200
        history_body = history_response.json()
        assert history_body["summary"]["correction_count"] == 1
        assert history_body["entries"][0]["mutation_type"] == "correction"

        confirmed_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/plans/confirmed",
            params={"period": REVIEWER_PLAN_PERIOD_START.isoformat()},
        )
        assert confirmed_response.status_code == 200
        confirmed_body = confirmed_response.json()
        assert len(confirmed_body["slots"]) == 21
        assert {slot["slot_origin"] for slot in confirmed_body["slots"]} == {"ai_suggested", "manually_added"}

        grocery_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery",
            params={"period": REVIEWER_PLAN_PERIOD_START.isoformat()},
        )
        assert grocery_response.status_code == 200
        grocery_body = grocery_response.json()
        assert grocery_body["status"] == "confirmed"
        assert grocery_body["trip_state"] == "confirmed_list_ready"
        assert any(line["origin"] == "ad_hoc" for line in grocery_body["lines"])
        assert any(line["offset_inventory_item_id"] for line in grocery_body["lines"])
        assert any(line["user_adjusted_quantity"] for line in grocery_body["lines"])

        conflict_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery/sync/conflicts"
        )
        assert conflict_response.status_code == 200
        assert conflict_response.json() == []
    finally:
        client.close()
        _dispose_services(planner, inventory, grocery)


def test_reviewer_seed_conflict_scenario_is_opt_in(tmp_path: Path) -> None:
    database_url = URL.create("sqlite+pysqlite", database=str((tmp_path / "reviewer-conflict.sqlite").resolve()))
    seed_reviewer_data(database_url=database_url, scenario_names=["sync-conflict-review"])

    client, planner, inventory, grocery = _build_client(database_url)
    try:
        grocery_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery",
            params={"period": REVIEWER_PLAN_PERIOD_START.isoformat()},
        )
        assert grocery_response.status_code == 200
        assert grocery_response.json()["trip_state"] == "trip_in_progress"
        assert grocery_response.json()["current_version_number"] == 2

        conflicts_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery/sync/conflicts"
        )
        assert conflicts_response.status_code == 200
        conflicts = conflicts_response.json()
        assert len(conflicts) == 1
        assert conflicts[0]["outcome"] == "review_required_quantity"
        assert conflicts[0]["resolution_status"] == "pending"
        assert conflicts[0]["allowed_resolution_actions"] == ["keep_mine", "use_server"]

        detail_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery/sync/conflicts/{conflicts[0]['conflict_id']}"
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["local_intent_summary"]["payload"]["quantity_to_buy"] == "2.5000"
    finally:
        client.close()
        _dispose_services(planner, inventory, grocery)


def test_reviewer_seed_baseline_sync_upload_uses_stable_line_identifier_contract(tmp_path: Path) -> None:
    database_url = URL.create("sqlite+pysqlite", database=str((tmp_path / "reviewer-sync-upload.sqlite").resolve()))
    seed_reviewer_data(database_url=database_url)

    client, planner, inventory, grocery = _build_client(database_url)
    try:
        grocery_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery",
            params={"period": REVIEWER_PLAN_PERIOD_START.isoformat()},
        )
        assert grocery_response.status_code == 200
        grocery_body = grocery_response.json()
        milk_line = next(line for line in grocery_body["lines"] if line["ingredient_name"] == "Milk")
        payload = {
            "household_id": REVIEWER_HOUSEHOLD_ID,
            "grocery_list_id": grocery_body["id"],
            "grocery_line_id": milk_line["grocery_line_id"],
            "grocery_list_item_id": milk_line["id"],
            "client_mutation_id": "seeded-offline-remove-milk-stable-line-id",
        }

        upload_response = client.post(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery/sync/upload",
            json=[
                {
                    "client_mutation_id": "seeded-offline-remove-milk-stable-line-id",
                    "household_id": REVIEWER_HOUSEHOLD_ID,
                    "actor_id": REVIEWER_USER_ID,
                    "aggregate_type": "grocery_line",
                    "aggregate_id": milk_line["grocery_line_id"],
                    "mutation_type": "remove_line",
                    "payload": payload,
                    "base_server_version": grocery_body["current_version_number"],
                    "device_timestamp": "2026-03-09T10:30:00",
                    "local_queue_status": "queued_offline",
                }
            ],
        )
        assert upload_response.status_code == 200, upload_response.text
        outcomes = upload_response.json()
        assert outcomes[0]["outcome"] == "applied"
        assert outcomes[0]["aggregate"]["aggregate_id"] == milk_line["grocery_line_id"]
        assert outcomes[0]["authoritative_server_version"] == grocery_body["current_version_number"] + 1

        refreshed_response = client.get(
            f"/api/v1/households/{REVIEWER_HOUSEHOLD_ID}/grocery",
            params={"period": REVIEWER_PLAN_PERIOD_START.isoformat()},
        )
        assert refreshed_response.status_code == 200
        refreshed_body = refreshed_response.json()
        assert refreshed_body["status"] == "trip_in_progress"
        assert all(line["ingredient_name"] != "Milk" for line in refreshed_body["lines"])
    finally:
        client.close()
        _dispose_services(planner, inventory, grocery)
