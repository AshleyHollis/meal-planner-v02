from datetime import date, datetime

import pytest

from app.models.ai_planning import AISuggestionRequest, AISuggestionResult, AISuggestionSlot
from app.models.meal_plan import MealPlan, MealPlanSlot

HOUSEHOLD = "hh-001"


def make_request(**kwargs) -> AISuggestionRequest:
    request_idempotency_key = kwargs.pop("request_idempotency_key", "idem-key-001")
    return AISuggestionRequest(
        household_id=HOUSEHOLD,
        plan_period_start=date(2025, 1, 6),
        plan_period_end=date(2025, 1, 12),
        request_idempotency_key=request_idempotency_key,
        created_at=datetime.utcnow(),
        **kwargs,
    )


def test_ai_suggestion_request_defaults_pending(db_session):
    req = make_request()
    db_session.add(req)
    db_session.commit()

    assert req.id is not None
    assert req.status == "pending"
    assert req.completed_at is None


def test_ai_suggestion_request_idempotency_key_unique_per_household(db_session):
    req1 = make_request()
    db_session.add(req1)
    db_session.commit()

    req2 = make_request(request_idempotency_key="idem-key-001")
    db_session.add(req2)
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_ai_suggestion_request_idempotency_key_can_repeat_in_other_household(db_session):
    alpha = make_request(request_idempotency_key="idem-key-shared")
    beta = AISuggestionRequest(
        household_id="hh-002",
        plan_period_start=date(2025, 1, 6),
        plan_period_end=date(2025, 1, 12),
        request_idempotency_key="idem-key-shared",
        created_at=datetime.utcnow(),
    )
    db_session.add_all([alpha, beta])
    db_session.commit()

    assert alpha.household_id != beta.household_id


def test_ai_suggestion_request_can_link_to_parent_draft_and_slot(db_session):
    plan = MealPlan(
        household_id=HOUSEHOLD,
        period_start=date(2025, 1, 6),
        period_end=date(2025, 1, 12),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(plan)
    db_session.flush()

    slot = MealPlanSlot(
        meal_plan_id=plan.id,
        slot_key="1:dinner",
        day_of_week=1,
        meal_type="dinner",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(slot)
    db_session.flush()

    req = make_request(
        request_idempotency_key="idem-key-003",
        target_slot_id=slot.id,
        meal_plan_id=plan.id,
        meal_plan_slot_id=slot.id,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    assert req.meal_plan_id == plan.id
    assert req.meal_plan_slot_id == slot.id
    assert req.target_slot_id == slot.id


def test_ai_suggestion_result_with_slots(db_session):
    req = make_request(request_idempotency_key="idem-key-002")
    db_session.add(req)
    db_session.flush()

    result = AISuggestionResult(
        request_id=req.id,
        fallback_mode="none",
        stale_flag=False,
        result_contract_version="v1.0",
        created_at=datetime.utcnow(),
    )
    db_session.add(result)
    db_session.flush()

    for day in range(7):
        slot = AISuggestionSlot(
            result_id=result.id,
            slot_key=f"{day}:dinner",
            day_of_week=day,
            meal_type="dinner",
            meal_title=f"Suggested Meal Day {day}",
            meal_summary=f"Summary for day {day}",
            reason_codes='["expiry_pressure"]',
            explanation_entries='["Uses items expiring soon"]',
            is_fallback=False,
            created_at=datetime.utcnow(),
        )
        db_session.add(slot)

    db_session.commit()
    db_session.refresh(result)

    assert len(result.slots) == 7
    assert result.request.status == "pending"


def test_ai_suggestion_slot_key_is_unique_per_result(db_session):
    req = make_request(request_idempotency_key="idem-key-004")
    db_session.add(req)
    db_session.flush()

    result = AISuggestionResult(
        request_id=req.id,
        fallback_mode="none",
        stale_flag=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(result)
    db_session.flush()

    db_session.add(
        AISuggestionSlot(
            result_id=result.id,
            slot_key="0:breakfast",
            day_of_week=0,
            meal_type="breakfast",
            meal_title="Oats",
            created_at=datetime.utcnow(),
        )
    )
    db_session.flush()

    db_session.add(
        AISuggestionSlot(
            result_id=result.id,
            slot_key="0:breakfast",
            day_of_week=0,
            meal_type="breakfast",
            meal_title="Toast",
            created_at=datetime.utcnow(),
        )
    )

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()
