from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import app.models  # noqa: F401
from sqlalchemy import select

from app.models.ai_planning import AISuggestionRequest, AISuggestionResult
from app.models.base import Base
from app.models.household import Household
from app.models.inventory import InventoryItem
from app.models.meal_plan import MealPlan, MealPlanSlot
from app.schemas.enums import PlanSlotRegenStatus
from planner_fixtures import ExplodingProvider, HappyPathProvider, InvalidPayloadProvider
from worker_runtime import GenerationWorker, build_session_factory
from worker_runtime.runtime import CuratedMealTemplate


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _session_factory(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'worker-test.sqlite').as_posix()}"
    session_factory = build_session_factory(database_url)
    Base.metadata.create_all(session_factory.kw["bind"])
    return session_factory


def _seed_household(session, household_id: str = "hh-worker") -> Household:
    household = Household(id=household_id, name="Worker Household", created_at=_utcnow(), updated_at=_utcnow())
    session.add(household)
    session.flush()
    return household


def _seed_inventory(session, household_id: str) -> None:
    session.add_all(
        [
            InventoryItem(
                household_id=household_id,
                name="Broccoli",
                storage_location="fridge",
                quantity_on_hand=Decimal("2"),
                primary_unit="heads",
                freshness_basis="known",
                expiry_date=date(2026, 3, 10),
                created_at=_utcnow(),
                updated_at=_utcnow(),
            ),
            InventoryItem(
                household_id=household_id,
                name="Oats",
                storage_location="pantry",
                quantity_on_hand=Decimal("1"),
                primary_unit="bag",
                freshness_basis="unknown",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            ),
        ]
    )


def _seed_confirmed_plan(session, household_id: str) -> None:
    plan = MealPlan(
        household_id=household_id,
        period_start=date(2026, 3, 2),
        period_end=date(2026, 3, 8),
        status="confirmed",
        created_at=_utcnow(),
        updated_at=_utcnow(),
        confirmed_at=_utcnow(),
        confirmation_client_mutation_id="confirm-prev",
    )
    session.add(plan)
    session.flush()
    session.add(
        MealPlanSlot(
            meal_plan_id=plan.id,
            slot_key="0:dinner",
            day_of_week=0,
            meal_type="dinner",
            meal_title="Broccoli Pasta Toss",
            slot_origin="ai_suggested",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
    )


def _queued_request(**overrides) -> AISuggestionRequest:
    return AISuggestionRequest(
        household_id=overrides.pop("household_id", "hh-worker"),
        actor_id=overrides.pop("actor_id", "user-001"),
        plan_period_start=overrides.pop("plan_period_start", date(2026, 3, 9)),
        plan_period_end=overrides.pop("plan_period_end", date(2026, 3, 15)),
        status=overrides.pop("status", "queued"),
        request_idempotency_key=overrides.pop("request_idempotency_key", f"req-{_utcnow().timestamp()}"),
        created_at=overrides.pop("created_at", _utcnow()),
        **overrides,
    )


def test_generation_worker_processes_weekly_request_with_grounding_and_versions(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    with session_factory() as session:
        household = _seed_household(session)
        _seed_inventory(session, household.id)
        _seed_confirmed_plan(session, household.id)
        request = _queued_request(household_id=household.id, request_idempotency_key="weekly-001")
        session.add(request)
        session.commit()
        request_id = request.id

    worker = GenerationWorker(session_factory=session_factory)
    worker.process_request(request_id)

    with session_factory() as session:
        request = session.get(AISuggestionRequest, request_id)
        result = session.scalar(select(AISuggestionResult).where(AISuggestionResult.request_id == request_id))
        assert request is not None
        assert request.status == "completed"
        assert request.prompt_family == "weekly_meal_plan"
        assert request.prompt_version == "1.0.0"
        assert request.policy_version == "1.0.0"
        assert request.context_contract_version == "1.0.0"
        assert request.result_contract_version == "1.0.0"
        assert request.grounding_hash is not None
        assert len(request.grounding_hash) == 64
        assert result is not None
        assert result.fallback_mode == "none"
        assert len(result.slots) == 21
        first_slot = result.slots[0]
        assert "USES_ON_HAND" in first_slot.reason_codes
        assert first_slot.uses_on_hand is not None
        assert first_slot.missing_hints is not None


def test_generation_worker_reuses_equivalent_fresh_result(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    provider = HappyPathProvider()
    with session_factory() as session:
        household = _seed_household(session)
        _seed_inventory(session, household.id)
        first_request = _queued_request(household_id=household.id, request_idempotency_key="weekly-001")
        second_request = _queued_request(household_id=household.id, request_idempotency_key="weekly-002")
        session.add_all([first_request, second_request])
        session.commit()
        first_id = first_request.id
        second_id = second_request.id

    worker = GenerationWorker(session_factory=session_factory, provider=provider)
    worker.process_request(first_id)
    worker.process_request(second_id)

    with session_factory() as session:
        first_request = session.get(AISuggestionRequest, first_id)
        second_request = session.get(AISuggestionRequest, second_id)
        first_result = session.scalar(select(AISuggestionResult).where(AISuggestionResult.request_id == first_id))
        second_result = session.scalar(select(AISuggestionResult).where(AISuggestionResult.request_id == second_id))
        assert provider.calls == 1
        assert first_request is not None and second_request is not None
        assert first_request.grounding_hash == second_request.grounding_hash
        assert first_result is not None and second_result is not None
        first_titles = [slot.meal_title for slot in sorted(first_result.slots, key=lambda slot: slot.slot_key)]
        second_titles = [slot.meal_title for slot in sorted(second_result.slots, key=lambda slot: slot.slot_key)]
        assert first_titles == second_titles


def test_generation_worker_stops_reusing_result_when_grounding_changes(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    provider = HappyPathProvider()
    with session_factory() as session:
        household = _seed_household(session)
        household_id = household.id
        _seed_inventory(session, household_id)
        first_request = _queued_request(household_id=household_id, request_idempotency_key="weekly-001")
        session.add(first_request)
        session.commit()
        first_id = first_request.id

    worker = GenerationWorker(session_factory=session_factory, provider=provider)
    worker.process_request(first_id)

    with session_factory() as session:
        broccoli = session.scalar(
            select(InventoryItem)
            .where(InventoryItem.household_id == household_id)
            .where(InventoryItem.name == "Broccoli")
        )
        assert broccoli is not None
        broccoli.quantity_on_hand = Decimal("5")
        broccoli.updated_at = _utcnow()
        second_request = _queued_request(household_id=household_id, request_idempotency_key="weekly-002")
        session.add(second_request)
        session.commit()
        second_id = second_request.id

    worker.process_request(second_id)

    with session_factory() as session:
        first_request = session.get(AISuggestionRequest, first_id)
        second_request = session.get(AISuggestionRequest, second_id)
        assert first_request is not None and second_request is not None
        assert provider.calls == 2
        assert first_request.grounding_hash != second_request.grounding_hash


def test_generation_worker_uses_curated_fallback_when_provider_output_is_invalid(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    with session_factory() as session:
        household = _seed_household(session)
        _seed_inventory(session, household.id)
        request = _queued_request(household_id=household.id, request_idempotency_key="weekly-invalid")
        session.add(request)
        session.commit()
        request_id = request.id

    worker = GenerationWorker(session_factory=session_factory, provider=InvalidPayloadProvider())
    worker.process_request(request_id)

    with session_factory() as session:
        request = session.get(AISuggestionRequest, request_id)
        result = session.scalar(select(AISuggestionResult).where(AISuggestionResult.request_id == request_id))
        assert request is not None
        assert request.status == "completed_with_fallback"
        assert result is not None
        assert result.fallback_mode == "curated_fallback"
        assert all(slot.is_fallback for slot in result.slots)
        assert len(result.slots) == 21
        first_slot = result.slots[0]
        assert first_slot.reason_codes is not None
        assert "LOW_CONTEXT_FALLBACK" in first_slot.reason_codes
        assert first_slot.explanation_entries is not None
        assert "deterministic fallback" in first_slot.explanation_entries
        assert first_slot.uses_on_hand is not None
        assert first_slot.missing_hints is not None


def test_generation_worker_preserves_existing_slot_when_manual_guidance_is_needed(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    with session_factory() as session:
        household = _seed_household(session)
        plan = MealPlan(
            household_id=household.id,
            period_start=date(2026, 3, 9),
            period_end=date(2026, 3, 15),
            status="draft",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(plan)
        session.flush()
        slot = MealPlanSlot(
            meal_plan_id=plan.id,
            slot_key="0:breakfast",
            day_of_week=0,
            meal_type="breakfast",
            meal_title="Keep Existing Breakfast",
            slot_origin="user_edited",
            ai_suggestion_request_id="req-original",
            ai_suggestion_result_id="result-original",
            regen_status="pending_regen",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(slot)
        session.flush()
        request = _queued_request(
            household_id=household.id,
            request_idempotency_key="regen-manual",
            target_slot_id=slot.id,
            meal_plan_id=plan.id,
            meal_plan_slot_id=slot.id,
        )
        session.add(request)
        session.commit()
        request_id = request.id
        slot_id = slot.id

    worker = GenerationWorker(
        session_factory=session_factory,
        provider=InvalidPayloadProvider(),
        curated_fallbacks=[
            CuratedMealTemplate(
                meal_type="dinner",
                title="Dinner Only Fallback",
                summary="Not applicable to breakfast.",
                uses_on_hand=("rice",),
                missing_key_ingredients=("greens",),
            )
        ],
    )
    worker.process_request(request_id)

    with session_factory() as session:
        request = session.get(AISuggestionRequest, request_id)
        result = session.scalar(select(AISuggestionResult).where(AISuggestionResult.request_id == request_id))
        slot = session.get(MealPlanSlot, slot_id)
        assert request is not None
        assert request.status == "completed_with_fallback"
        assert result is not None
        assert result.fallback_mode == "manual_guidance"
        assert slot is not None
        assert slot.meal_title == "Keep Existing Breakfast"
        assert slot.regen_status == PlanSlotRegenStatus.regen_failed.value
        assert slot.pending_regen_request_id is None


def test_generation_worker_applies_successful_slot_regeneration_metadata(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    provider = HappyPathProvider()
    with session_factory() as session:
        household = _seed_household(session)
        _seed_inventory(session, household.id)
        plan = MealPlan(
            household_id=household.id,
            period_start=date(2026, 3, 9),
            period_end=date(2026, 3, 15),
            status="draft",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(plan)
        session.flush()
        slot = MealPlanSlot(
            meal_plan_id=plan.id,
            slot_key="0:dinner",
            day_of_week=0,
            meal_type="dinner",
            meal_title="Keep Existing Dinner",
            slot_origin="user_edited",
            ai_suggestion_request_id="req-original",
            ai_suggestion_result_id="result-original",
            reason_codes='["OLD_REASON"]',
            explanation_entries='["Old explanation"]',
            prompt_family="weekly_meal_plan",
            prompt_version="0.9.0",
            fallback_mode="manual_guidance",
            regen_status="pending_regen",
            pending_regen_request_id="pending-old",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        sibling = MealPlanSlot(
            meal_plan_id=plan.id,
            slot_key="1:lunch",
            day_of_week=1,
            meal_type="lunch",
            meal_title="Leave Sibling Alone",
            slot_origin="user_edited",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add_all([slot, sibling])
        session.flush()
        request = _queued_request(
            household_id=household.id,
            request_idempotency_key="regen-success",
            target_slot_id=slot.id,
            meal_plan_id=plan.id,
            meal_plan_slot_id=slot.id,
        )
        session.add(request)
        session.commit()
        request_id = request.id
        slot_id = slot.id
        sibling_id = sibling.id

    worker = GenerationWorker(session_factory=session_factory, provider=provider)
    worker.process_request(request_id)

    with session_factory() as session:
        request = session.get(AISuggestionRequest, request_id)
        result = session.scalar(select(AISuggestionResult).where(AISuggestionResult.request_id == request_id))
        slot = session.get(MealPlanSlot, slot_id)
        sibling = session.get(MealPlanSlot, sibling_id)
        assert request is not None
        assert request.status == "completed"
        assert result is not None
        assert result.fallback_mode == "none"
        assert len(result.slots) == 1
        assert slot is not None
        assert slot.slot_origin == "ai_suggested"
        assert slot.ai_suggestion_request_id == request_id
        assert slot.ai_suggestion_result_id == result.id
        assert slot.prompt_family == "slot_regeneration"
        assert slot.prompt_version == "1.0.0"
        assert slot.fallback_mode == "none"
        assert slot.regen_status == PlanSlotRegenStatus.idle.value
        assert slot.pending_regen_request_id is None
        assert slot.meal_title == "Dinner Provider Meal 1"
        assert slot.reason_codes is not None
        assert "USES_ON_HAND" in slot.reason_codes
        assert sibling is not None
        assert sibling.meal_title == "Leave Sibling Alone"


def test_generation_worker_logs_correlation_id_for_completed_request(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="worker_runtime.runtime")
    session_factory = _session_factory(tmp_path)
    provider = HappyPathProvider()
    with session_factory() as session:
        household = _seed_household(session)
        _seed_inventory(session, household.id)
        request = _queued_request(household_id=household.id, request_idempotency_key="weekly-log")
        session.add(request)
        session.commit()
        request_id = request.id

    worker = GenerationWorker(session_factory=session_factory, provider=provider)
    worker.process_request(request_id)

    completed = next(
        record
        for record in caplog.records
        if getattr(record, "worker_outcome", None) == "completed"
    )
    assert completed.worker_correlation_id == request_id
    assert completed.worker_request_id == request_id
    assert completed.worker_household_id == "hh-worker"
    assert completed.worker_prompt_family == "weekly_meal_plan"


def test_generation_worker_marks_request_failed_and_logs_correlation_id_on_unhandled_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("ERROR", logger="worker_runtime.runtime")
    session_factory = _session_factory(tmp_path)
    with session_factory() as session:
        household = _seed_household(session)
        _seed_inventory(session, household.id)
        request = _queued_request(household_id=household.id, request_idempotency_key="weekly-failure")
        session.add(request)
        session.commit()
        request_id = request.id

    worker = GenerationWorker(session_factory=session_factory, provider=ExplodingProvider())
    worker.process_request(request_id)

    with session_factory() as session:
        request = session.get(AISuggestionRequest, request_id)
        result = session.scalar(select(AISuggestionResult).where(AISuggestionResult.request_id == request_id))
        assert request is not None
        assert request.status == "failed"
        assert request.completed_at is not None
        assert result is None

    failed = next(
        record
        for record in caplog.records
        if getattr(record, "worker_outcome", None) == "failed"
    )
    assert failed.worker_correlation_id == request_id
    assert failed.worker_request_id == request_id
    assert failed.worker_household_id == "hh-worker"
