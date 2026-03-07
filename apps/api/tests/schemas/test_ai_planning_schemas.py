from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.ai_planning import (
    AISuggestionRequestCreate,
    AISuggestionRequestRead,
    AISuggestionResultRead,
    AISuggestionSlotRead,
)
from app.schemas.enums import AISuggestionStatus


def test_ai_suggestion_request_create_accepts_regen_linkage():
    request = AISuggestionRequestCreate(
        household_id="hh-001",
        actor_id="user-001",
        plan_period_start=date(2025, 1, 6),
        plan_period_end=date(2025, 1, 12),
        target_slot_id="slot-001",
        meal_plan_id="plan-001",
        meal_plan_slot_id="slot-001",
        request_idempotency_key="idem-key-001",
        prompt_family="weekly-v1",
        prompt_version="v1.0",
        policy_version="policy-v1",
        context_contract_version="ctx-v1",
        result_contract_version="result-v1",
    )

    assert request.meal_plan_id == "plan-001"
    assert request.meal_plan_slot_id == "slot-001"


def test_ai_suggestion_request_create_requires_non_empty_idempotency_key():
    with pytest.raises(ValidationError):
        AISuggestionRequestCreate(
            household_id="hh-001",
            plan_period_start=date(2025, 1, 6),
            plan_period_end=date(2025, 1, 12),
            request_idempotency_key="",
        )


def test_ai_suggestion_request_read_includes_extended_status_fields():
    request = AISuggestionRequestRead(
        id="req-001",
        household_id="hh-001",
        actor_id="user-001",
        plan_period_start="2025-01-06",
        plan_period_end="2025-01-12",
        target_slot_id="slot-001",
        meal_plan_id="plan-001",
        meal_plan_slot_id="slot-001",
        status=AISuggestionStatus.completed_with_fallback,
        request_idempotency_key="idem-key-001",
        prompt_family="weekly-v1",
        prompt_version="v1.0",
        policy_version="policy-v1",
        context_contract_version="ctx-v1",
        result_contract_version="result-v1",
        grounding_hash="grounding-001",
        created_at="2025-01-01T12:00:00Z",
        completed_at="2025-01-01T12:05:00Z",
    )

    assert request.status == AISuggestionStatus.completed_with_fallback
    assert request.result_contract_version == "result-v1"


def test_ai_suggestion_slot_and_result_reads_capture_slot_key_and_summary():
    slot = AISuggestionSlotRead(
        id="slot-001",
        result_id="result-001",
        slot_key="1:dinner",
        day_of_week=1,
        meal_type="dinner",
        meal_title="Veggie Curry",
        meal_summary="Uses potatoes and chickpeas on hand.",
        reason_codes='["uses_on_hand"]',
        explanation_entries='["Potatoes are already available"]',
        uses_on_hand='["potatoes", "chickpeas"]',
        missing_hints='["coconut milk"]',
        is_fallback=False,
    )
    result = AISuggestionResultRead(
        id="result-001",
        request_id="req-001",
        meal_plan_id="plan-001",
        fallback_mode=False,
        stale_flag=False,
        result_contract_version="result-v1",
        created_at="2025-01-01T12:00:00Z",
        slots=[slot],
    )

    assert result.slots[0].slot_key == "1:dinner"
    assert result.slots[0].meal_summary == "Uses potatoes and chickpeas on hand."
