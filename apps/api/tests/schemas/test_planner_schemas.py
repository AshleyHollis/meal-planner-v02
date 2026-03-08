from datetime import date, datetime

from app.schemas.planner import DraftConfirmRequest, PlanConfirmedEvent


def test_draft_confirm_request_accepts_camel_case_stale_ack_flag() -> None:
    command = DraftConfirmRequest(
        clientMutationId="confirm-001",
        staleWarningAcknowledged=True,
    )

    assert command.client_mutation_id == "confirm-001"
    assert command.stale_warning_acknowledged is True


def test_plan_confirmed_event_captures_handoff_payload() -> None:
    event = PlanConfirmedEvent(
        household_id="hh-001",
        meal_plan_id="plan-001",
        plan_period_start=date(2026, 3, 9),
        plan_period_end=date(2026, 3, 15),
        confirmed_at=datetime(2026, 3, 8, 12, 0, 0),
        source_plan_status="confirmed",
        stale_warning_acknowledged=True,
        confirmation_client_mutation_id="confirm-001",
        actor_id="user-001",
        slot_count=21,
        plan_version=3,
        correlation_id="req-001",
        grocery_refresh_trigger={
            "household_id": "hh-001",
            "confirmed_plan_id": "plan-001",
            "plan_period_start": date(2026, 3, 9),
            "plan_period_end": date(2026, 3, 15),
            "source_plan_version": 3,
            "correlation_id": "req-001",
        },
    )

    assert event.event_type == "plan_confirmed"
    assert event.source_plan_status == "confirmed"
    assert event.slot_count == 21
    assert event.plan_version == 3
    assert event.correlation_id == "req-001"
    assert event.grocery_refresh_trigger.trigger_type == "grocery_refresh_requested"
    assert event.grocery_refresh_trigger.source_plan_status == "confirmed"
