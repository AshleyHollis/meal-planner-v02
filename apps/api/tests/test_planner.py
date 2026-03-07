from __future__ import annotations

import json
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

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
from app.models.ai_planning import AISuggestionRequest, AISuggestionResult
from app.models.inventory import InventoryItem
from app.models.meal_plan import MealPlan, MealPlanSlot, MealPlanSlotHistory
from app.models.planner_event import PlannerEvent
from app.schemas.enums import AISuggestionStatus, PlanSlotRegenStatus
from app.schemas.planner import DraftConfirmRequest, DraftCreateCommand, SlotRegenerateCommand, SuggestionRequestCommand
from app.services.planner_service import PlannerService, get_planner_service

HOUSEHOLD = "household-abc"
OTHER_HOUSEHOLD = "household-xyz"
PERIOD_START = "2026-03-09"


@pytest.fixture()
def planner() -> PlannerService:
    return PlannerService()


@pytest.fixture()
def client(planner: PlannerService) -> TestClient:
    app.dependency_overrides[get_planner_service] = lambda: planner
    with TestClient(app) as test_client:
        test_client.headers.update(_session_headers())
        yield test_client
    app.dependency_overrides.pop(get_planner_service, None)
    planner.dispose()


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


def _request_suggestion(client: TestClient, mutation_id: str | None = None) -> dict:
    response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/suggestion",
        json={
            "planPeriodStart": PERIOD_START,
            "requestIdempotencyKey": mutation_id or str(uuid.uuid4()),
        },
    )
    assert response.status_code == 202
    return response.json()


def _await_completed_suggestion(client: TestClient, request_id: str) -> dict:
    response = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/requests/{request_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["suggestion_id"]
    return body


def _open_draft(client: TestClient, suggestion_id: str, *, replace_existing: bool = False) -> dict:
    response = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft",
        json={"suggestionId": suggestion_id, "replaceExisting": replace_existing},
    )
    assert response.status_code == 201
    return response.json()


def test_request_poll_and_open_draft_flow(client: TestClient) -> None:
    requested = _request_suggestion(client)
    assert requested["request_id"]
    assert requested["status"] in {"queued", "completed"}

    completed = _await_completed_suggestion(client, requested["request_id"])
    assert completed["household_id"] == HOUSEHOLD
    assert completed["prompt_family"] == "weekly_meal_plan"
    assert completed["prompt_version"] == "1.0.0"
    assert completed["policy_version"] == "1.0.0"
    assert completed["context_contract_version"] == "1.0.0"
    assert completed["result_contract_version"] == "1.0.0"
    assert len(completed["slots"]) == 21
    assert "uses_on_hand" in completed["slots"][0]
    assert "missing_hints" in completed["slots"][0]

    by_period = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/suggestion?period={PERIOD_START}")
    assert by_period.status_code == 200
    assert by_period.json()["suggestion_id"] == completed["suggestion_id"]

    draft = _open_draft(client, completed["suggestion_id"])
    assert draft["household_id"] == HOUSEHOLD
    assert draft["status"] == "draft"
    assert draft["stale_warning"] is False
    assert len(draft["slots"]) == 21
    assert draft["slots"][0]["slot_origin"] == "ai_suggested"
    assert draft["slots"][0]["prompt_family"] == "weekly_meal_plan"
    assert "uses_on_hand" in draft["slots"][0]


def test_request_and_confirm_log_planner_correlation_ids(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="app.services.planner_service")

    requested = _request_suggestion(client, "planner-log-001")
    completed = _await_completed_suggestion(client, requested["request_id"])
    draft = _open_draft(client, completed["suggestion_id"])
    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json={"clientMutationId": "confirm-log-001", "staleWarningAcknowledged": False},
    )

    assert confirmed.status_code == 200
    request_log = next(
        record
        for record in caplog.records
        if getattr(record, "planner_action", None) == "request_suggestion"
        and getattr(record, "planner_outcome", None) == "accepted"
    )
    assert request_log.planner_correlation_id == requested["request_id"]
    assert request_log.planner_request_id == requested["request_id"]

    confirm_log = next(
        record
        for record in caplog.records
        if getattr(record, "planner_action", None) == "confirm_draft"
        and getattr(record, "planner_outcome", None) == "accepted"
    )
    assert confirm_log.planner_correlation_id == requested["request_id"]
    assert confirm_log.planner_plan_id == confirmed.json()["id"]
    assert confirm_log.planner_grocery_refresh_triggered is True


def test_request_idempotency_is_household_scoped(planner: PlannerService) -> None:
    first = planner.request_suggestion(
        HOUSEHOLD,
        actor_id="user-alpha",
        command=SuggestionRequestCommand(
            planPeriodStart=PERIOD_START,
            requestIdempotencyKey="shared-mutation-id",
        ),
    )
    second = planner.request_suggestion(
        OTHER_HOUSEHOLD,
        actor_id="user-beta",
        command=SuggestionRequestCommand(
            planPeriodStart=PERIOD_START,
            requestIdempotencyKey="shared-mutation-id",
        ),
    )
    assert first.request_id != second.request_id


def test_edit_and_revert_slot_preserves_original_suggestion(client: TestClient) -> None:
    completed = _await_completed_suggestion(client, _request_suggestion(client)["request_id"])
    draft = _open_draft(client, completed["suggestion_id"])
    slot = draft["slots"][0]
    original_title = slot["meal_title"]

    edited = client.patch(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/slots/{slot['id']}",
        json={"mealTitle": "Manual Stir Fry", "mealSummary": "Using the last fresh greens first."},
    )
    assert edited.status_code == 200
    edited_body = edited.json()
    assert edited_body["slot_origin"] == "user_edited"
    assert edited_body["meal_title"] == "Manual Stir Fry"
    assert edited_body["reason_codes"] == []
    assert edited_body["original_suggestion"]["meal_title"] == original_title

    reverted = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/slots/{slot['id']}/revert"
    )
    assert reverted.status_code == 200
    reverted_body = reverted.json()
    assert reverted_body["slot_origin"] == "ai_suggested"
    assert reverted_body["meal_title"] == original_title


def test_slot_regeneration_updates_only_targeted_slot(client: TestClient) -> None:
    completed = _await_completed_suggestion(client, _request_suggestion(client)["request_id"])
    draft = _open_draft(client, completed["suggestion_id"])
    first_slot = draft["slots"][0]
    second_slot = draft["slots"][1]

    regen = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/slots/{first_slot['id']}/regenerate",
        json={"clientMutationId": str(uuid.uuid4())},
    )
    assert regen.status_code == 202
    regen_request = regen.json()
    assert regen_request["request_id"]

    refreshed = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/draft?period={PERIOD_START}")
    assert refreshed.status_code == 200
    refreshed_body = refreshed.json()
    refreshed_first = next(slot for slot in refreshed_body["slots"] if slot["id"] == first_slot["id"])
    refreshed_second = next(slot for slot in refreshed_body["slots"] if slot["id"] == second_slot["id"])

    assert refreshed_first["meal_title"] != first_slot["meal_title"]
    assert refreshed_first["slot_origin"] == "ai_suggested"
    assert refreshed_second["meal_title"] == second_slot["meal_title"]


def test_slot_regeneration_tracks_pending_state_and_refreshes_slot_provenance(planner: PlannerService) -> None:
    requested = planner.request_suggestion(
        HOUSEHOLD,
        actor_id="user-alpha",
        command=SuggestionRequestCommand(
            planPeriodStart=PERIOD_START,
            requestIdempotencyKey="planner-regen-weekly",
        ),
    )
    planner.complete_request(requested.request_id)
    completed = planner.get_request(HOUSEHOLD, requested.request_id)
    assert completed is not None and completed.suggestion_id is not None

    draft = planner.open_draft_from_suggestion(
        HOUSEHOLD,
        command=DraftCreateCommand(suggestionId=completed.suggestion_id),
    )
    target_slot = draft.slots[0]

    regen = planner.request_slot_regeneration(
        HOUSEHOLD,
        draft_id=draft.id,
        slot_id=target_slot.id,
        actor_id="user-alpha",
        command=SlotRegenerateCommand(clientMutationId="regen-verify-001"),
    )
    duplicate = planner.request_slot_regeneration(
        HOUSEHOLD,
        draft_id=draft.id,
        slot_id=target_slot.id,
        actor_id="user-alpha",
        command=SlotRegenerateCommand(clientMutationId="regen-verify-001"),
    )
    assert duplicate.request_id == regen.request_id

    pending_draft = planner.get_draft(HOUSEHOLD, date.fromisoformat(PERIOD_START))
    assert pending_draft is not None
    pending_slot = next(slot for slot in pending_draft.slots if slot.id == target_slot.id)
    assert pending_slot.regen_status is PlanSlotRegenStatus.pending_regen
    assert pending_slot.pending_regen_request_id == regen.request_id
    assert pending_slot.slot_message == "Waiting for a refreshed suggestion for this slot."

    planner.complete_request(regen.request_id)

    refreshed_draft = planner.get_draft(HOUSEHOLD, date.fromisoformat(PERIOD_START))
    assert refreshed_draft is not None
    refreshed_slot = next(slot for slot in refreshed_draft.slots if slot.id == target_slot.id)
    assert refreshed_slot.regen_status is PlanSlotRegenStatus.idle
    assert refreshed_slot.pending_regen_request_id is None
    assert refreshed_slot.slot_origin.value == "ai_suggested"
    assert refreshed_slot.prompt_family == "slot_regeneration"
    assert refreshed_slot.prompt_version == "1.0.0"
    assert refreshed_slot.original_suggestion is not None

    with planner._session_factory() as session:
        persisted_slot = session.get(MealPlanSlot, target_slot.id)
        persisted_request = session.get(AISuggestionRequest, regen.request_id)
        persisted_result = session.scalar(
            select(AISuggestionResult).where(AISuggestionResult.request_id == regen.request_id)
        )
        assert persisted_slot is not None
        assert persisted_request is not None
        assert persisted_result is not None
        assert persisted_slot.ai_suggestion_request_id == regen.request_id
        assert persisted_slot.ai_suggestion_result_id == persisted_result.id
        assert persisted_slot.prompt_family == "slot_regeneration"
        assert persisted_slot.prompt_version == "1.0.0"
        assert persisted_slot.fallback_mode == persisted_result.fallback_mode
        assert persisted_slot.regen_status == PlanSlotRegenStatus.idle.value
        assert persisted_slot.pending_regen_request_id is None


def test_confirm_draft_is_idempotent_and_confirmed_read_is_separate(client: TestClient) -> None:
    completed = _await_completed_suggestion(client, _request_suggestion(client)["request_id"])
    draft = _open_draft(client, completed["suggestion_id"])

    confirm_payload = {
        "clientMutationId": "confirm-001",
        "staleWarningAcknowledged": False,
    }
    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json=confirm_payload,
    )
    assert confirmed.status_code == 200
    confirmed_body = confirmed.json()
    assert confirmed_body["status"] == "confirmed"
    assert confirmed_body["confirmed_at"] is not None

    duplicate = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json=confirm_payload,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == confirmed_body["id"]

    confirmed_read = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/confirmed?period={PERIOD_START}")
    assert confirmed_read.status_code == 200
    assert confirmed_read.json()["id"] == confirmed_body["id"]

    no_active_draft = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/draft?period={PERIOD_START}")
    assert no_active_draft.status_code == 404


def test_confirm_requires_stale_warning_acknowledgement(client: TestClient, planner: PlannerService) -> None:
    requested = _request_suggestion(client)
    planner.update_request_status(HOUSEHOLD, requested["request_id"], AISuggestionStatus.stale)
    completed = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/requests/{requested['request_id']}")
    assert completed.status_code == 200

    draft = _open_draft(client, completed.json()["suggestion_id"])
    assert draft["stale_warning"] is True

    blocked = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json={"clientMutationId": "confirm-stale-001", "staleWarningAcknowledged": False},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "stale_warning_ack_required"

    allowed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json={"clientMutationId": "confirm-stale-001", "staleWarningAcknowledged": True},
    )
    assert allowed.status_code == 200
    assert allowed.json()["stale_warning_acknowledged"] is True


def test_inventory_change_marks_existing_draft_stale(client: TestClient, planner: PlannerService) -> None:
    completed = _await_completed_suggestion(client, _request_suggestion(client)["request_id"])
    draft = _open_draft(client, completed["suggestion_id"])

    with planner._session_factory() as session:
        session.add(
            InventoryItem(
                household_id=HOUSEHOLD,
                name="Fresh Spinach",
                storage_location="fridge",
                quantity_on_hand=1,
                primary_unit="bag",
                freshness_basis="known",
                expiry_date=date.fromisoformat("2026-03-10"),
            )
        )
        session.commit()

    refreshed = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/draft?period={PERIOD_START}")
    assert refreshed.status_code == 200
    assert refreshed.json()["stale_warning"] is True

    blocked = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json={"clientMutationId": "confirm-after-inventory-change", "staleWarningAcknowledged": False},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "stale_warning_ack_required"


def test_confirming_stale_draft_persists_acknowledged_provenance(planner: PlannerService) -> None:
    requested = planner.request_suggestion(
        HOUSEHOLD,
        actor_id="user-alpha",
        command=SuggestionRequestCommand(
            planPeriodStart=PERIOD_START,
            requestIdempotencyKey="planner-stale-confirm",
        ),
    )
    planner.complete_request(requested.request_id)
    completed = planner.get_request(HOUSEHOLD, requested.request_id)
    assert completed is not None and completed.suggestion_id is not None
    draft = planner.open_draft_from_suggestion(
        HOUSEHOLD,
        command=DraftCreateCommand(suggestionId=completed.suggestion_id),
    )

    with planner._session_factory() as session:
        session.add(
            InventoryItem(
                household_id=HOUSEHOLD,
                name="Fresh Herbs",
                storage_location="fridge",
                quantity_on_hand=1,
                primary_unit="bunch",
                freshness_basis="known",
                expiry_date=date.fromisoformat("2026-03-09"),
            )
        )
        session.commit()

    refreshed = planner.get_draft(HOUSEHOLD, date.fromisoformat(PERIOD_START))
    assert refreshed is not None
    assert refreshed.stale_warning is True

    confirmed = planner.confirm_draft(
        HOUSEHOLD,
        draft_id=draft.id,
        actor_id="user-alpha",
        command=DraftConfirmRequest(
            clientMutationId="confirm-stale-ack-001",
            staleWarningAcknowledged=True,
        ),
    )
    duplicate = planner.confirm_draft(
        HOUSEHOLD,
        draft_id=draft.id,
        actor_id="user-alpha",
        command=DraftConfirmRequest(
            clientMutationId="confirm-stale-ack-001",
            staleWarningAcknowledged=True,
        ),
    )
    assert duplicate.id == confirmed.id
    assert duplicate.stale_warning_acknowledged is True

    with planner._session_factory() as session:
        plan = session.get(MealPlan, confirmed.id)
        history_rows = session.scalars(
            select(MealPlanSlotHistory).where(MealPlanSlotHistory.meal_plan_id == confirmed.id)
        ).all()
        event_rows = session.scalars(
            select(PlannerEvent).where(PlannerEvent.meal_plan_id == confirmed.id)
        ).all()

        assert plan is not None
        assert plan.stale_warning_acknowledged is True
        assert history_rows
        assert all(row.stale_warning_present_at_confirmation for row in history_rows)
        assert len(event_rows) == 1
        event_payload = json.loads(event_rows[0].payload)
        assert event_payload["stale_warning_acknowledged"] is True
        assert event_payload["confirmation_client_mutation_id"] == "confirm-stale-ack-001"
        assert event_payload["plan_version"] == plan.version


def test_new_suggestion_and_draft_do_not_overwrite_existing_confirmed_plan(client: TestClient) -> None:
    first = _await_completed_suggestion(client, _request_suggestion(client, "suggest-confirmed")["request_id"])
    first_draft = _open_draft(client, first["suggestion_id"])
    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{first_draft['id']}/confirm",
        json={"clientMutationId": "confirm-protected", "staleWarningAcknowledged": False},
    )
    assert confirmed.status_code == 200
    confirmed_id = confirmed.json()["id"]

    second = _await_completed_suggestion(client, _request_suggestion(client, "suggest-new-draft")["request_id"])
    replacement_draft = _open_draft(client, second["suggestion_id"])
    assert replacement_draft["id"] != first_draft["id"]

    confirmed_read = client.get(f"/api/v1/households/{HOUSEHOLD}/plans/confirmed?period={PERIOD_START}")
    assert confirmed_read.status_code == 200
    confirmed_body = confirmed_read.json()
    assert confirmed_body["id"] == confirmed_id
    assert confirmed_body["status"] == "confirmed"


def test_confirm_writes_slot_history_and_plan_confirmed_event_once(client: TestClient, planner: PlannerService) -> None:
    completed = _await_completed_suggestion(client, _request_suggestion(client)["request_id"])
    draft = _open_draft(client, completed["suggestion_id"])
    first_slot = draft["slots"][0]
    client.patch(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/slots/{first_slot['id']}",
        json={"mealTitle": "Manual Tacos", "mealSummary": "Manual choice."},
    )

    confirm_payload = {
        "clientMutationId": "confirm-history-001",
        "staleWarningAcknowledged": False,
    }
    confirmed = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json=confirm_payload,
    )
    assert confirmed.status_code == 200
    confirmed_body = confirmed.json()

    duplicate = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft/{draft['id']}/confirm",
        json=confirm_payload,
    )
    assert duplicate.status_code == 200

    with planner._session_factory() as session:
        plan = session.get(MealPlan, confirmed_body["id"])
        assert plan is not None
        history_rows = session.scalars(
            select(MealPlanSlotHistory).where(MealPlanSlotHistory.meal_plan_id == confirmed_body["id"])
        ).all()
        event_rows = session.scalars(
            select(PlannerEvent).where(PlannerEvent.meal_plan_id == confirmed_body["id"])
        ).all()

        assert len(history_rows) == len(confirmed_body["slots"])
        edited_history = next(row for row in history_rows if row.slot_key == first_slot["slot_key"])
        assert edited_history.slot_origin == "user_edited"
        assert edited_history.stale_warning_present_at_confirmation is False

        assert len(event_rows) == 1
        event = event_rows[0]
        event_payload = json.loads(event.payload)
        assert event.event_type == "plan_confirmed"
        assert event.source_mutation_id == "confirm-history-001"
        assert event_payload["slot_count"] == 21
        assert event_payload["meal_plan_id"] == confirmed_body["id"]
        assert event_payload["source_plan_status"] == "confirmed"
        assert event_payload["correlation_id"] == completed["request_id"]
        assert event_payload["grocery_refresh_trigger"]["trigger_type"] == "grocery_refresh_requested"
        assert event_payload["grocery_refresh_trigger"]["source_plan_status"] == "confirmed"
        assert event_payload["grocery_refresh_trigger"]["confirmed_plan_id"] == confirmed_body["id"]
        assert event_payload["grocery_refresh_trigger"]["source_plan_version"] == plan.version
        assert plan.version >= 2


def test_suggestion_and_draft_states_do_not_emit_grocery_refresh_trigger(
    client: TestClient, planner: PlannerService
) -> None:
    requested = _request_suggestion(client, "planner-no-grocery-001")

    with planner._session_factory() as session:
        assert session.scalars(select(PlannerEvent)).all() == []

    completed = _await_completed_suggestion(client, requested["request_id"])
    draft = _open_draft(client, completed["suggestion_id"])
    assert draft["status"] == "draft"

    with planner._session_factory() as session:
        assert session.scalars(select(PlannerEvent)).all() == []


def test_open_draft_requires_replace_flag_when_active_draft_exists(client: TestClient) -> None:
    first = _await_completed_suggestion(client, _request_suggestion(client, "suggest-1")["request_id"])
    second = _await_completed_suggestion(client, _request_suggestion(client, "suggest-2")["request_id"])
    original_draft = _open_draft(client, first["suggestion_id"])

    rejected = client.post(
        f"/api/v1/households/{HOUSEHOLD}/plans/draft",
        json={"suggestionId": second["suggestion_id"]},
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "draft_already_exists"

    replaced = _open_draft(client, second["suggestion_id"], replace_existing=True)
    assert replaced["id"] != original_draft["id"]


def test_household_path_must_match_request_session(client: TestClient) -> None:
    response = client.get(f"/api/v1/households/{OTHER_HOUSEHOLD}/plans/suggestion?period={PERIOD_START}")
    assert response.status_code == 403
