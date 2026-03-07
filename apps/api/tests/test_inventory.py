"""
Tests for inventory foundation routes.

Covers:
- Create item (including idempotency).
- List items (household-scoped).
- Get single item.
- Increase / decrease / set quantity adjustments.
- Set metadata (non-quantity changes).
- Move location (no quantity side-effect).
- Archive item (history preserved).
- Compensating correction.
- Adjustment history read.
- 401 / 403 / 404 auth and not-found behaviour.
"""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

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
from app.services.inventory_store import InventoryStore, get_inventory_store


@pytest.fixture()
def store() -> InventoryStore:
    return InventoryStore()


@pytest.fixture()
def client(store: InventoryStore) -> TestClient:
    app.dependency_overrides[get_inventory_store] = lambda: store
    with TestClient(app) as test_client:
        test_client.headers.update(_session_headers())
        yield test_client
    app.dependency_overrides.pop(get_inventory_store, None)
    store.dispose()


@pytest.fixture()
def unauthenticated_client(store: InventoryStore) -> TestClient:
    app.dependency_overrides[get_inventory_store] = lambda: store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_inventory_store, None)
    store.dispose()


HOUSEHOLD = "household-abc"
OTHER_HOUSEHOLD = "household-xyz"


def _session_headers(household_id: str = HOUSEHOLD) -> dict[str, str]:
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


def _create_payload(
    mutation_id: str | None = None,
    *,
    household_id: str = HOUSEHOLD,
    name: str = "Oat Milk",
) -> dict:
    return {
        "household_id": household_id,
        "name": name,
        "storage_location": "fridge",
        "initial_quantity": 2.0,
        "primary_unit": "litres",
        "freshness": {"basis": "unknown"},
        "client_mutation_id": mutation_id or str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# Create item
# ---------------------------------------------------------------------------


def test_create_item_returns_201(client: TestClient) -> None:
    resp = client.post("/api/v1/inventory", json=_create_payload())
    assert resp.status_code == 201


def test_create_item_receipt_shape(client: TestClient) -> None:
    data = client.post("/api/v1/inventory", json=_create_payload()).json()
    assert "inventory_adjustment_id" in data
    assert "inventory_item_id" in data
    assert data["mutation_type"] == "create_item"
    assert data["quantity_after"] == 2.0
    assert data["version_after"] == 1
    assert data["is_duplicate"] is False


def test_create_item_logs_accepted_mutation_diagnostics(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="app.services.inventory_store")

    response = client.post("/api/v1/inventory", json=_create_payload())

    assert response.status_code == 201
    accepted = next(
        record for record in caplog.records if getattr(record, "inventory_outcome", None) == "accepted"
    )
    assert accepted.message == "inventory mutation accepted"
    assert accepted.inventory_household_id == HOUSEHOLD
    assert accepted.inventory_mutation_type == "create_item"
    assert accepted.inventory_actor_user_id == f"user-{HOUSEHOLD}"
    assert accepted.inventory_client_mutation_id
    assert accepted.inventory_item_id == response.json()["inventory_item_id"]
    assert accepted.inventory_adjustment_id == response.json()["inventory_adjustment_id"]


def test_create_item_idempotent_replay(client: TestClient) -> None:
    mutation_id = str(uuid.uuid4())
    payload = _create_payload(mutation_id)
    first = client.post("/api/v1/inventory", json=payload).json()
    second = client.post("/api/v1/inventory", json=payload).json()
    assert first["inventory_item_id"] == second["inventory_item_id"]
    assert first["inventory_adjustment_id"] == second["inventory_adjustment_id"]
    assert second["is_duplicate"] is True


def test_create_item_logs_duplicate_replay_diagnostics(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="app.services.inventory_store")
    mutation_id = str(uuid.uuid4())
    payload = _create_payload(mutation_id)

    first = client.post("/api/v1/inventory", json=payload)
    second = client.post("/api/v1/inventory", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    duplicate = next(
        record for record in caplog.records if getattr(record, "inventory_outcome", None) == "duplicate"
    )
    assert duplicate.message == "inventory mutation duplicate"
    assert duplicate.inventory_household_id == HOUSEHOLD
    assert duplicate.inventory_mutation_type == "create_item"
    assert duplicate.inventory_client_mutation_id == mutation_id
    assert duplicate.inventory_item_id == first.json()["inventory_item_id"]
    assert duplicate.inventory_adjustment_id == first.json()["inventory_adjustment_id"]


def test_create_item_same_mutation_id_is_scoped_per_household(client: TestClient) -> None:
    mutation_id = str(uuid.uuid4())
    first = client.post(
        "/api/v1/inventory",
        json=_create_payload(mutation_id, household_id=HOUSEHOLD, name="Oat Milk"),
    )
    second = client.post(
        "/api/v1/inventory",
        json=_create_payload(mutation_id, household_id=OTHER_HOUSEHOLD, name="Soy Milk"),
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_data = first.json()
    second_data = second.json()
    assert first_data["inventory_item_id"] != second_data["inventory_item_id"]
    assert first_data["inventory_adjustment_id"] != second_data["inventory_adjustment_id"]

    first_household = client.get("/api/v1/inventory").json()
    second_household = client.get("/api/v1/inventory", headers=_session_headers(OTHER_HOUSEHOLD)).json()
    assert first_household["total"] == 1
    assert second_household["total"] == 1
    assert first_household["items"][0]["name"] == "Oat Milk"
    assert second_household["items"][0]["name"] == "Soy Milk"


# ---------------------------------------------------------------------------
# List and get
# ---------------------------------------------------------------------------


def test_list_returns_created_item(client: TestClient) -> None:
    client.post("/api/v1/inventory", json=_create_payload())
    data = client.get("/api/v1/inventory").json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Oat Milk"


def test_list_uses_active_household_scope(client: TestClient) -> None:
    client.post("/api/v1/inventory", json=_create_payload(name="Oat Milk"))
    client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=OTHER_HOUSEHOLD, name="Soy Milk"),
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    first_household = client.get("/api/v1/inventory").json()
    second_household = client.get("/api/v1/inventory", headers=_session_headers(OTHER_HOUSEHOLD)).json()

    assert [item["name"] for item in first_household["items"]] == ["Oat Milk"]
    assert [item["name"] for item in second_household["items"]] == ["Soy Milk"]


def test_list_requires_matching_active_household(client: TestClient) -> None:
    client.post("/api/v1/inventory", json=_create_payload())
    response = client.get("/api/v1/inventory?household_id=other-household")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "household_access_forbidden"


def test_get_item_returns_full_record(client: TestClient, store: InventoryStore) -> None:
    receipt = client.post("/api/v1/inventory", json=_create_payload()).json()
    item_id = receipt["inventory_item_id"]
    data = client.get(f"/api/v1/inventory/{item_id}").json()
    assert data["inventory_item_id"] == item_id
    assert data["primary_unit"] == "litres"
    assert data["history_summary"]["committed_adjustment_count"] == 1
    assert data["latest_adjustment"]["mutation_type"] == "create_item"
    assert data["latest_adjustment"]["actor_user_id"] == f"user-{HOUSEHOLD}"
    assert data["latest_adjustment"]["quantity_transition"] == {
        "before": 0.0,
        "after": 2.0,
        "delta": 2.0,
        "unit": "litres",
        "changed": True,
    }


def test_get_item_404_for_unknown(client: TestClient) -> None:
    resp = client.get(f"/api/v1/inventory/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_item_403_for_wrong_household(client: TestClient) -> None:
    receipt = client.post("/api/v1/inventory", json=_create_payload()).json()
    item_id = receipt["inventory_item_id"]
    resp = client.get(f"/api/v1/inventory/{item_id}?household_id=wrong")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "household_access_forbidden"


def test_get_item_404_for_other_households_item(client: TestClient) -> None:
    receipt = client.post("/api/v1/inventory", json=_create_payload()).json()
    item_id = receipt["inventory_item_id"]

    response = client.get(
        f"/api/v1/inventory/{item_id}",
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory item not found"


def test_inventory_routes_return_401_without_session(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.post("/api/v1/inventory", json=_create_payload())
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthenticated"


def test_create_item_rejects_client_owned_household_override(client: TestClient) -> None:
    response = client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=OTHER_HOUSEHOLD),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "household_access_forbidden"


def test_create_item_logs_forbidden_household_access(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("WARNING", logger="app.dependencies.session")

    response = client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=OTHER_HOUSEHOLD),
    )

    assert response.status_code == 403
    forbidden = next(
        record for record in caplog.records if record.message == "household access forbidden"
    )
    assert forbidden.session_user_id == f"user-{HOUSEHOLD}"
    assert forbidden.session_active_household_id == HOUSEHOLD
    assert forbidden.session_requested_household_id == OTHER_HOUSEHOLD


# ---------------------------------------------------------------------------
# Quantity adjustments
# ---------------------------------------------------------------------------


def _item_id(client: TestClient) -> str:
    return client.post("/api/v1/inventory", json=_create_payload()).json()["inventory_item_id"]


def test_increase_quantity(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["quantity_after"] == 3.0
    assert data["version_after"] == 2


def test_decrease_quantity(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "decrease_quantity",
            "delta_quantity": 1.5,
            "reason_code": "cooking_consume",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.json()["quantity_after"] == 0.5


def test_set_quantity(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "set_quantity",
            "delta_quantity": 5.0,
            "reason_code": "manual_count_reset",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.json()["quantity_after"] == 5.0


def test_adjustment_idempotency(client: TestClient) -> None:
    iid = _item_id(client)
    mid = str(uuid.uuid4())
    cmd = {
        "mutation_type": "increase_quantity",
        "delta_quantity": 1.0,
        "reason_code": "manual_edit",
        "client_mutation_id": mid,
    }
    url = f"/api/v1/inventory/{iid}/adjustments"
    first = client.post(url, json=cmd).json()
    second = client.post(url, json=cmd).json()
    assert second["inventory_adjustment_id"] == first["inventory_adjustment_id"]
    assert second["is_duplicate"] is True
    # Balance unchanged on duplicate
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["quantity_on_hand"] == 3.0


def test_adjustment_rejects_stale_version_conflict(client: TestClient) -> None:
    iid = _item_id(client)
    url = f"/api/v1/inventory/{iid}/adjustments"

    client.post(
        url,
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
            "version": 1,
        },
    )

    stale = client.post(
        url,
        json={
            "mutation_type": "decrease_quantity",
            "delta_quantity": 0.5,
            "reason_code": "cooking_consume",
            "client_mutation_id": str(uuid.uuid4()),
            "version": 1,
        },
    )

    assert stale.status_code == 409
    assert stale.json()["detail"] == {
        "code": "stale_inventory_version",
        "message": "The inventory item changed since the client last read it.",
        "expected_version": 1,
        "current_version": 2,
    }
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["quantity_on_hand"] == 3.0
    assert item["version"] == 2


def test_adjustment_logs_stale_version_conflict_diagnostics(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("WARNING", logger="app.services.inventory_store")
    iid = _item_id(client)
    url = f"/api/v1/inventory/{iid}/adjustments"

    first = client.post(
        url,
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
            "version": 1,
        },
    )
    stale_mutation_id = str(uuid.uuid4())
    stale = client.post(
        url,
        json={
            "mutation_type": "decrease_quantity",
            "delta_quantity": 0.5,
            "reason_code": "cooking_consume",
            "client_mutation_id": stale_mutation_id,
            "version": 1,
        },
    )

    assert first.status_code == 201
    assert stale.status_code == 409
    conflict = next(
        record for record in caplog.records if getattr(record, "inventory_outcome", None) == "conflict"
    )
    assert conflict.message == "inventory mutation conflict"
    assert conflict.inventory_household_id == HOUSEHOLD
    assert conflict.inventory_item_id == iid
    assert conflict.inventory_mutation_type == "decrease_quantity"
    assert conflict.inventory_client_mutation_id == stale_mutation_id
    assert conflict.inventory_expected_version == 1
    assert conflict.inventory_current_version == 2


def test_decrease_quantity_rejects_negative_result(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "decrease_quantity",
            "delta_quantity": 3.0,
            "reason_code": "cooking_consume",
            "client_mutation_id": str(uuid.uuid4()),
            "version": 1,
        },
    )

    assert resp.status_code == 422
    assert resp.json()["detail"] == {
        "code": "negative_quantity_not_allowed",
        "message": "decrease_quantity cannot commit a negative inventory quantity",
    }
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["quantity_on_hand"] == 2.0
    assert item["version"] == 1


def test_adjustment_rejects_invalid_mutation_type(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "archive_item",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 422


def test_adjustment_404_for_unknown_item(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/inventory/{uuid.uuid4()}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 404


def test_adjustment_404_for_other_households_item(client: TestClient) -> None:
    iid = _item_id(client)
    response = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory item not found"


def test_adjustment_403_for_wrong_household_query_override(client: TestClient) -> None:
    iid = _item_id(client)
    response = client.post(
        f"/api/v1/inventory/{iid}/adjustments?household_id={OTHER_HOUSEHOLD}",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "household_access_forbidden"


# ---------------------------------------------------------------------------
# Set metadata
# ---------------------------------------------------------------------------


def test_set_metadata_updates_name(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.patch(
        f"/api/v1/inventory/{iid}/metadata",
        json={
            "name": "Barista Oat Milk",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 200
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["name"] == "Barista Oat Milk"


def test_set_metadata_does_not_change_quantity(client: TestClient) -> None:
    iid = _item_id(client)
    client.patch(
        f"/api/v1/inventory/{iid}/metadata",
        json={"name": "New Name", "client_mutation_id": str(uuid.uuid4())},
    )
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["quantity_on_hand"] == 2.0


def test_set_metadata_supports_freshness_basis_transition(client: TestClient) -> None:
    iid = _item_id(client)
    metadata_url = f"/api/v1/inventory/{iid}/metadata"

    estimated = client.patch(
        metadata_url,
        json={
            "freshness": {
                "basis": "estimated",
                "best_before": "2026-03-10T00:00:00Z",
                "estimated_note": "Estimated from a typical unopened carton.",
            },
            "client_mutation_id": str(uuid.uuid4()),
            "version": 1,
        },
    )
    assert estimated.status_code == 200
    assert estimated.json()["version_after"] == 2

    known = client.patch(
        metadata_url,
        json={
            "freshness": {
                "basis": "known",
                "best_before": "2026-03-12T00:00:00Z",
            },
            "client_mutation_id": str(uuid.uuid4()),
            "version": 2,
        },
    )
    assert known.status_code == 200
    assert known.json()["version_after"] == 3

    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["freshness"]["basis"] == "known"
    assert item["freshness"]["best_before"].startswith("2026-03-12T00:00:00")
    assert item["freshness"]["estimated_note"] is None
    assert item["version"] == 3

    history = client.get(f"/api/v1/inventory/{iid}/history").json()
    metadata_events = [event for event in history["entries"] if event["mutation_type"] == "set_metadata"]
    assert metadata_events[0]["freshness_before"]["basis"] == "estimated"
    assert metadata_events[0]["freshness_after"]["basis"] == "known"
    assert metadata_events[1]["freshness_before"]["basis"] == "unknown"
    assert metadata_events[1]["freshness_after"]["basis"] == "estimated"
    assert metadata_events[0]["freshness_transition"]["changed"] is True
    assert metadata_events[1]["workflow_reference"] == {
        "correlation_id": None,
        "causal_workflow_id": None,
        "causal_workflow_type": None,
    }


def test_set_metadata_same_mutation_id_is_scoped_per_household(client: TestClient) -> None:
    first_item_id = client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=HOUSEHOLD, name="Oat Milk"),
    ).json()["inventory_item_id"]
    second_item_id = client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=OTHER_HOUSEHOLD, name="Soy Milk"),
        headers=_session_headers(OTHER_HOUSEHOLD),
    ).json()["inventory_item_id"]

    mutation_id = str(uuid.uuid4())
    first_response = client.patch(
        f"/api/v1/inventory/{first_item_id}/metadata",
        json={
            "name": "Barista Oat Milk",
            "client_mutation_id": mutation_id,
            "version": 1,
        },
    )
    second_response = client.patch(
        f"/api/v1/inventory/{second_item_id}/metadata",
        json={
            "name": "Unsweetened Soy Milk",
            "client_mutation_id": mutation_id,
            "version": 1,
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["inventory_adjustment_id"] != second_response.json()["inventory_adjustment_id"]

    first_item = client.get(
        f"/api/v1/inventory/{first_item_id}"
    ).json()
    second_item = client.get(
        f"/api/v1/inventory/{second_item_id}",
        headers=_session_headers(OTHER_HOUSEHOLD),
    ).json()
    assert first_item["name"] == "Barista Oat Milk"
    assert second_item["name"] == "Unsweetened Soy Milk"


def test_set_metadata_404_for_other_households_item(client: TestClient) -> None:
    iid = _item_id(client)
    response = client.patch(
        f"/api/v1/inventory/{iid}/metadata",
        json={
            "name": "Hidden Milk",
            "client_mutation_id": str(uuid.uuid4()),
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory item not found"


# ---------------------------------------------------------------------------
# Move location
# ---------------------------------------------------------------------------


def test_move_location(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.post(
        f"/api/v1/inventory/{iid}/move",
        json={
            "storage_location": "freezer",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 201
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["storage_location"] == "freezer"

    history = client.get(f"/api/v1/inventory/{iid}/history").json()
    move_event = next(event for event in history["entries"] if event["mutation_type"] == "move_location")
    assert move_event["storage_location_before"] == "fridge"
    assert move_event["storage_location_after"] == "freezer"
    assert move_event["location_transition"] == {
        "before": "fridge",
        "after": "freezer",
        "changed": True,
    }


def test_move_location_does_not_alter_quantity(client: TestClient) -> None:
    iid = _item_id(client)
    client.post(
        f"/api/v1/inventory/{iid}/move",
        json={"storage_location": "pantry", "client_mutation_id": str(uuid.uuid4())},
    )
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["quantity_on_hand"] == 2.0


def test_move_location_404_for_other_households_item(client: TestClient) -> None:
    iid = _item_id(client)
    response = client.post(
        f"/api/v1/inventory/{iid}/move",
        json={
            "storage_location": "pantry",
            "client_mutation_id": str(uuid.uuid4()),
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory item not found"


# ---------------------------------------------------------------------------
# Archive item
# ---------------------------------------------------------------------------


def test_archive_item(client: TestClient) -> None:
    iid = _item_id(client)
    resp = client.post(
        f"/api/v1/inventory/{iid}/archive",
        json={"client_mutation_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 201


def test_archived_item_excluded_from_default_list(client: TestClient) -> None:
    iid = _item_id(client)
    client.post(
        f"/api/v1/inventory/{iid}/archive",
        json={"client_mutation_id": str(uuid.uuid4())},
    )
    data = client.get("/api/v1/inventory").json()
    assert data["total"] == 0


def test_archived_item_included_with_flag(client: TestClient) -> None:
    iid = _item_id(client)
    client.post(
        f"/api/v1/inventory/{iid}/archive",
        json={"client_mutation_id": str(uuid.uuid4())},
    )
    data = client.get("/api/v1/inventory?include_archived=true").json()
    assert data["total"] == 1


def test_archive_history_preserved(client: TestClient) -> None:
    iid = _item_id(client)
    client.post(
        f"/api/v1/inventory/{iid}/archive",
        json={"client_mutation_id": str(uuid.uuid4())},
    )
    history = client.get(f"/api/v1/inventory/{iid}/history").json()
    types = [h["mutation_type"] for h in history["entries"]]
    assert "create_item" in types
    assert "archive_item" in types


def test_archive_item_404_for_other_households_item(client: TestClient) -> None:
    iid = _item_id(client)
    response = client.post(
        f"/api/v1/inventory/{iid}/archive",
        json={"client_mutation_id": str(uuid.uuid4())},
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory item not found"


# ---------------------------------------------------------------------------
# Compensating correction
# ---------------------------------------------------------------------------


def test_correction_adjusts_balance(client: TestClient) -> None:
    iid = _item_id(client)
    # First record an initial increase to get an adjustment ID to correct against.
    increase_resp = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 3.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    ).json()
    adj_id = increase_resp["inventory_adjustment_id"]

    # Apply compensating correction (-3 to undo the increase).
    resp = client.post(
        f"/api/v1/inventory/{iid}/corrections",
        json={
            "delta_quantity": -3.0,
            "corrects_adjustment_id": adj_id,
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 201
    item = client.get(f"/api/v1/inventory/{iid}").json()
    assert item["quantity_on_hand"] == 2.0  # back to original
    history = client.get(f"/api/v1/inventory/{iid}/history").json()
    correction = next(event for event in history["entries"] if event["mutation_type"] == "correction")
    assert correction["correction_links"]["is_correction"] is True
    assert correction["correction_links"]["corrects_adjustment_id"] == adj_id
    corrected_target = next(event for event in history["entries"] if event["inventory_adjustment_id"] == adj_id)
    assert correction["quantity_transition"] == {
        "before": 5.0,
        "after": 2.0,
        "delta": -3.0,
        "unit": "litres",
        "changed": True,
    }
    assert corrected_target["correction_links"]["is_corrected"] is True
    assert correction["inventory_adjustment_id"] in corrected_target["correction_links"]["corrected_by_adjustment_ids"]


def test_correction_same_mutation_id_is_scoped_per_household(client: TestClient) -> None:
    first_item_id = client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=HOUSEHOLD, name="Oat Milk"),
    ).json()["inventory_item_id"]
    second_item_id = client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=OTHER_HOUSEHOLD, name="Soy Milk"),
        headers=_session_headers(OTHER_HOUSEHOLD),
    ).json()["inventory_item_id"]

    first_adjustment_id = client.post(
        f"/api/v1/inventory/{first_item_id}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    ).json()["inventory_adjustment_id"]
    second_adjustment_id = client.post(
        f"/api/v1/inventory/{second_item_id}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 2.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    ).json()["inventory_adjustment_id"]

    mutation_id = str(uuid.uuid4())
    first_response = client.post(
        f"/api/v1/inventory/{first_item_id}/corrections",
        json={
            "delta_quantity": -1.0,
            "corrects_adjustment_id": first_adjustment_id,
            "client_mutation_id": mutation_id,
            "version": 2,
        },
    )
    second_response = client.post(
        f"/api/v1/inventory/{second_item_id}/corrections",
        json={
            "delta_quantity": -2.0,
            "corrects_adjustment_id": second_adjustment_id,
            "client_mutation_id": mutation_id,
            "version": 2,
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["inventory_adjustment_id"] != second_response.json()["inventory_adjustment_id"]

    first_item = client.get(
        f"/api/v1/inventory/{first_item_id}"
    ).json()
    second_item = client.get(
        f"/api/v1/inventory/{second_item_id}",
        headers=_session_headers(OTHER_HOUSEHOLD),
    ).json()
    assert first_item["quantity_on_hand"] == 2.0
    assert second_item["quantity_on_hand"] == 2.0


def test_correction_404_for_other_households_item(client: TestClient) -> None:
    iid = _item_id(client)
    adjustment_id = client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    ).json()["inventory_adjustment_id"]

    response = client.post(
        f"/api/v1/inventory/{iid}/corrections",
        json={
            "delta_quantity": -1.0,
            "corrects_adjustment_id": adjustment_id,
            "client_mutation_id": str(uuid.uuid4()),
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory item not found"


def test_correction_target_must_stay_household_scoped(client: TestClient) -> None:
    first_item_id = client.post("/api/v1/inventory", json=_create_payload(name="Oat Milk")).json()[
        "inventory_item_id"
    ]
    second_item_id = client.post(
        "/api/v1/inventory",
        json=_create_payload(household_id=OTHER_HOUSEHOLD, name="Soy Milk"),
        headers=_session_headers(OTHER_HOUSEHOLD),
    ).json()["inventory_item_id"]

    other_household_adjustment_id = client.post(
        f"/api/v1/inventory/{second_item_id}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 2.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
        headers=_session_headers(OTHER_HOUSEHOLD),
    ).json()["inventory_adjustment_id"]

    response = client.post(
        f"/api/v1/inventory/{first_item_id}/corrections",
        json={
            "delta_quantity": -1.0,
            "corrects_adjustment_id": other_household_adjustment_id,
            "client_mutation_id": str(uuid.uuid4()),
            "version": 1,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "correction_target_not_found",
        "message": "The correction must reference an existing adjustment on this household inventory item.",
    }


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_history_contains_all_adjustment_events(client: TestClient) -> None:
    iid = _item_id(client)
    client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    client.post(
        f"/api/v1/inventory/{iid}/adjustments",
        json={
            "mutation_type": "decrease_quantity",
            "delta_quantity": 0.5,
            "reason_code": "cooking_consume",
            "client_mutation_id": str(uuid.uuid4()),
        },
    )
    history = client.get(f"/api/v1/inventory/{iid}/history").json()
    assert history["total"] == 3  # create + increase + decrease
    assert len(history["entries"]) == 3
    assert history["has_more"] is False
    assert history["summary"]["committed_adjustment_count"] == 3
    assert history["summary"]["correction_count"] == 0
    assert history["summary"]["latest_mutation_type"] == "decrease_quantity"
    assert history["entries"][0]["mutation_type"] == "decrease_quantity"
    assert history["entries"][1]["mutation_type"] == "increase_quantity"
    assert history["entries"][2]["mutation_type"] == "create_item"


def test_history_supports_pagination(client: TestClient) -> None:
    iid = _item_id(client)
    for quantity in (1.0, 2.0, 3.0):
        client.post(
            f"/api/v1/inventory/{iid}/adjustments",
            json={
                "mutation_type": "increase_quantity",
                "delta_quantity": quantity,
                "reason_code": "manual_edit",
                "client_mutation_id": str(uuid.uuid4()),
            },
        )

    first_page = client.get(f"/api/v1/inventory/{iid}/history?limit=2").json()
    second_page = client.get(f"/api/v1/inventory/{iid}/history?limit=2&offset=2").json()

    assert first_page["total"] == 4
    assert first_page["limit"] == 2
    assert first_page["offset"] == 0
    assert first_page["has_more"] is True
    assert len(first_page["entries"]) == 2
    assert second_page["offset"] == 2
    assert second_page["has_more"] is False
    assert len(second_page["entries"]) == 2


def test_history_excludes_duplicate_replays_and_stale_conflicts(client: TestClient) -> None:
    iid = _item_id(client)
    mutation_id = str(uuid.uuid4())
    url = f"/api/v1/inventory/{iid}/adjustments"

    first = client.post(
        url,
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": mutation_id,
            "version": 1,
        },
    )
    duplicate = client.post(
        url,
        json={
            "mutation_type": "increase_quantity",
            "delta_quantity": 1.0,
            "reason_code": "manual_edit",
            "client_mutation_id": mutation_id,
            "version": 1,
        },
    )
    stale = client.post(
        url,
        json={
            "mutation_type": "decrease_quantity",
            "delta_quantity": 0.5,
            "reason_code": "cooking_consume",
            "client_mutation_id": str(uuid.uuid4()),
            "version": 1,
        },
    )
    history = client.get(f"/api/v1/inventory/{iid}/history").json()

    assert first.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["is_duplicate"] is True
    assert stale.status_code == 409
    assert history["total"] == 2
    assert history["summary"]["committed_adjustment_count"] == 2
    assert [entry["mutation_type"] for entry in history["entries"]] == [
        "increase_quantity",
        "create_item",
    ]


def test_history_404_for_unknown_item(client: TestClient) -> None:
    resp = client.get(f"/api/v1/inventory/{uuid.uuid4()}/history")
    assert resp.status_code == 404


def test_history_404_for_other_households_item(client: TestClient) -> None:
    iid = _item_id(client)
    response = client.get(
        f"/api/v1/inventory/{iid}/history",
        headers=_session_headers(OTHER_HOUSEHOLD),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory item not found"
