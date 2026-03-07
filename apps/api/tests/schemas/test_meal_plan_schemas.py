from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.meal_plan import (
    MealPlanConfirmCommand,
    MealPlanCreate,
    MealPlanSlotCreate,
    MealPlanSlotHistoryRead,
)
from app.schemas.enums import SlotOrigin


def test_meal_plan_create_valid():
    plan = MealPlanCreate(
        household_id="hh-001",
        period_start=date(2025, 1, 6),
        period_end=date(2025, 1, 12),
    )
    assert plan.household_id == "hh-001"
    assert plan.is_valid_period is True


def test_meal_plan_create_with_ai_suggestion():
    plan = MealPlanCreate(
        household_id="hh-001",
        period_start=date(2025, 1, 6),
        period_end=date(2025, 1, 12),
        ai_suggestion_request_id="req-001",
        ai_suggestion_result_id="result-001",
    )
    assert plan.ai_suggestion_request_id == "req-001"
    assert plan.ai_suggestion_result_id == "result-001"


def test_meal_plan_slot_create_valid():
    slot = MealPlanSlotCreate(
        meal_plan_id="plan-001",
        slot_key="0:dinner",
        day_of_week=0,
        meal_type="dinner",
        meal_title="Chicken Stir Fry",
        meal_summary="Uses broccoli and chicken.",
        slot_origin=SlotOrigin.ai_suggested,
        ai_suggestion_request_id="req-001",
        ai_suggestion_result_id="result-001",
        reason_codes='["uses_on_hand"]',
        explanation_entries='["Uses broccoli already in the fridge"]',
        prompt_family="weekly-v1",
        prompt_version="v1.0",
        fallback_mode=False,
        regen_status="idle",
    )
    assert slot.slot_origin == SlotOrigin.ai_suggested
    assert slot.day_of_week == 0
    assert slot.slot_key == "0:dinner"


def test_meal_plan_slot_rejects_invalid_day_of_week():
    with pytest.raises(ValidationError):
        MealPlanSlotCreate(
            meal_plan_id="plan-001",
            slot_key="7:dinner",
            day_of_week=7,
            meal_type="dinner",
        )


def test_meal_plan_slot_defaults_manually_added():
    slot = MealPlanSlotCreate(
        meal_plan_id="plan-001",
        slot_key="3:lunch",
        day_of_week=3,
        meal_type="lunch",
    )
    assert slot.slot_origin == SlotOrigin.manually_added


def test_meal_plan_slot_create_requires_slot_key():
    with pytest.raises(ValidationError):
        MealPlanSlotCreate(
            meal_plan_id="plan-001",
            slot_key="",
            day_of_week=1,
            meal_type="breakfast",
        )


def test_meal_plan_confirm_command():
    cmd = MealPlanConfirmCommand(
        meal_plan_id="plan-001",
        household_id="hh-001",
        stale_warning_acknowledged=True,
        client_mutation_id="client-confirm-001",
    )
    assert cmd.stale_warning_acknowledged is True


def test_meal_plan_confirm_command_requires_client_mutation_id():
    with pytest.raises(ValidationError):
        MealPlanConfirmCommand(
            meal_plan_id="plan-001",
            household_id="hh-001",
            stale_warning_acknowledged=True,
        )


def test_meal_plan_slot_history_read_captures_confirmation_audit_fields():
    history = MealPlanSlotHistoryRead(
        id="hist-001",
        meal_plan_slot_id="slot-001",
        meal_plan_id="plan-001",
        slot_key="2:dinner",
        slot_origin=SlotOrigin.ai_suggested,
        ai_suggestion_request_id="req-001",
        ai_suggestion_result_id="result-001",
        reason_codes='["expiry_pressure"]',
        explanation_entries='["Uses expiring yogurt"]',
        prompt_family="weekly-v1",
        prompt_version="v1.0",
        fallback_mode=False,
        stale_warning_present_at_confirmation=True,
        confirmed_at="2025-01-01T12:00:00Z",
        created_at="2025-01-01T12:00:00Z",
    )
    assert history.slot_key == "2:dinner"
    assert history.explanation_entries == '["Uses expiring yogurt"]'
    assert history.stale_warning_present_at_confirmation is True
