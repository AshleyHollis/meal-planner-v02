from datetime import date, datetime

import pytest

from app.models.meal_plan import MealPlan, MealPlanSlot, MealPlanSlotHistory

HOUSEHOLD = "hh-001"


def make_plan(**kwargs) -> MealPlan:
    return MealPlan(
        household_id=HOUSEHOLD,
        period_start=date(2025, 1, 6),
        period_end=date(2025, 1, 12),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        **kwargs,
    )


def test_meal_plan_defaults_to_draft(db_session):
    plan = make_plan()
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    assert plan.id is not None
    assert plan.status == "draft"
    assert plan.version == 1
    assert plan.confirmed_at is None


def test_meal_plan_slot_origin_defaults_to_manually_added(db_session):
    plan = make_plan()
    db_session.add(plan)
    db_session.flush()

    slot = MealPlanSlot(
        meal_plan_id=plan.id,
        slot_key="0:dinner",
        day_of_week=0,
        meal_type="dinner",
        meal_title="Pasta",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(slot)
    db_session.commit()

    assert slot.slot_origin == "manually_added"
    assert slot.is_user_locked is False


def test_meal_plan_slots_relationship(db_session):
    plan = make_plan()
    db_session.add(plan)
    db_session.flush()

    for day in range(7):
        slot = MealPlanSlot(
            meal_plan_id=plan.id,
            slot_key=f"{day}:dinner",
            day_of_week=day,
            meal_type="dinner",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(slot)

    db_session.commit()
    db_session.refresh(plan)
    assert len(plan.slots) == 7


def test_meal_plan_slot_history_stores_ai_metadata(db_session):
    plan = make_plan()
    db_session.add(plan)
    db_session.flush()

    slot = MealPlanSlot(
        meal_plan_id=plan.id,
        slot_key="1:dinner",
        day_of_week=1,
        meal_type="dinner",
        slot_origin="ai_suggested",
        ai_suggestion_request_id="req-001",
        ai_suggestion_result_id="result-001",
        reason_codes='["expiry_pressure", "preference_match"]',
        explanation_entries='["Uses expiring broccoli", "Avoids recent pasta"]',
        prompt_family="weekly-v1",
        prompt_version="v1.0",
        fallback_mode=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(slot)
    db_session.flush()

    history = MealPlanSlotHistory(
        meal_plan_slot_id=slot.id,
        meal_plan_id=plan.id,
        slot_key="1:dinner",
        slot_origin="ai_suggested",
        ai_suggestion_request_id="req-001",
        ai_suggestion_result_id="result-001",
        reason_codes='["expiry_pressure", "preference_match"]',
        explanation_entries='["Uses expiring broccoli", "Avoids recent pasta"]',
        prompt_family="weekly-v1",
        prompt_version="v1.0",
        fallback_mode=False,
        stale_warning_present_at_confirmation=True,
        confirmed_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db_session.add(history)
    db_session.commit()

    assert history.ai_suggestion_request_id == "req-001"
    assert history.ai_suggestion_result_id == "result-001"
    assert history.slot_key == "1:dinner"
    assert history.explanation_entries == '["Uses expiring broccoli", "Avoids recent pasta"]'
    assert history.stale_warning_present_at_confirmation is True


def test_meal_plan_confirmation_client_mutation_id_is_unique_per_household(db_session):
    first = make_plan(confirmation_client_mutation_id="confirm-001")
    db_session.add(first)
    db_session.commit()

    duplicate = make_plan(confirmation_client_mutation_id="confirm-001")
    db_session.add(duplicate)

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_active_draft_is_unique_per_household_and_period(db_session):
    db_session.add(make_plan())
    db_session.commit()

    duplicate_draft = make_plan()
    db_session.add(duplicate_draft)

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_confirmed_plan_and_draft_can_coexist_for_same_household_period(db_session):
    confirmed = make_plan(
        status="confirmed",
        confirmed_at=datetime.utcnow(),
        confirmation_client_mutation_id="confirm-100",
    )
    draft = make_plan(
        confirmation_client_mutation_id="confirm-101",
    )
    db_session.add_all([confirmed, draft])
    db_session.commit()

    assert confirmed.status == "confirmed"
    assert draft.status == "draft"


def test_same_active_draft_period_allowed_for_different_households(db_session):
    alpha = make_plan()
    beta = MealPlan(
        household_id="hh-002",
        period_start=date(2025, 1, 6),
        period_end=date(2025, 1, 12),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add_all([alpha, beta])
    db_session.commit()

    assert alpha.household_id != beta.household_id


def test_meal_plan_slot_persists_ai_lineage_and_regen_fields(db_session):
    plan = make_plan(ai_suggestion_request_id="req-plan-001", ai_suggestion_result_id="result-plan-001")
    db_session.add(plan)
    db_session.flush()

    slot = MealPlanSlot(
        meal_plan_id=plan.id,
        slot_key="2:lunch",
        day_of_week=2,
        meal_type="lunch",
        meal_title="Soup",
        meal_summary="Uses leftover roast vegetables.",
        slot_origin="user_edited",
        ai_suggestion_request_id="req-slot-001",
        ai_suggestion_result_id="result-slot-001",
        reason_codes='["uses_on_hand"]',
        explanation_entries="[\"Reuses yesterday's vegetables\"]",
        prompt_family="weekly-v2",
        prompt_version="v2.0",
        fallback_mode=True,
        regen_status="pending_regen",
        pending_regen_request_id="req-regen-001",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)

    assert slot.slot_key == "2:lunch"
    assert slot.meal_summary == "Uses leftover roast vegetables."
    assert slot.ai_suggestion_result_id == "result-slot-001"
    assert slot.explanation_entries == "[\"Reuses yesterday's vegetables\"]"
    assert slot.regen_status == "pending_regen"
    assert slot.pending_regen_request_id == "req-regen-001"


def test_meal_plan_slot_key_is_unique_within_plan(db_session):
    plan = make_plan()
    db_session.add(plan)
    db_session.flush()

    db_session.add(
        MealPlanSlot(
            meal_plan_id=plan.id,
            slot_key="3:dinner",
            day_of_week=3,
            meal_type="dinner",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    db_session.flush()

    db_session.add(
        MealPlanSlot(
            meal_plan_id=plan.id,
            slot_key="3:dinner",
            day_of_week=3,
            meal_type="dinner",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()
