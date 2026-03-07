from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import app.models  # noqa: F401
from sqlalchemy import URL, Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.household import Household
from app.models.ai_planning import AISuggestionRequest, AISuggestionResult, AISuggestionSlot
from app.models.meal_plan import MealPlan, MealPlanSlot, MealPlanSlotHistory
from app.models.planner_event import PlannerEvent
from app.schemas.enums import AISuggestionStatus, MealPlanStatus, PlanSlotRegenStatus, SlotOrigin
from app.schemas.planner import (
    ConfirmedPlanView,
    DraftConfirmRequest,
    DraftCreateCommand,
    DraftPlanView,
    DraftSlotUpdateCommand,
    GroceryRefreshTrigger,
    PlanConfirmedEvent,
    PlannerSlotSuggestionSnapshot,
    PlannerSlotView,
    SlotRegenerateCommand,
    SuggestionEnvelope,
    SuggestionRequestCommand,
)
from app.services.local_db_compat import resolve_local_db_path

WORKER_ROOT = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from worker_runtime import GenerationWorker

MEAL_TYPES = ("breakfast", "lunch", "dinner")
ACTIVE_REQUEST_STATUSES = {"queued", "pending", "generating"}
VISIBLE_REQUEST_STATUSES = {"queued", "pending", "generating", "completed", "completed_with_fallback", "failed", "stale"}
TERMINAL_SUGGESTION_STATUSES = {
    AISuggestionStatus.completed.value,
    AISuggestionStatus.completed_with_fallback.value,
    AISuggestionStatus.stale.value,
}
logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PlannerDomainError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int = 422) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class PlannerService:
    def __init__(self, database_url: str | URL | None = None) -> None:
        self._engine = self._create_engine(database_url)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @classmethod
    def for_default_app(cls) -> "PlannerService":
        build_dir = Path(__file__).resolve().parents[2] / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        db_path = resolve_local_db_path((build_dir / "inventory.sqlite").resolve())
        db_url = URL.create(
            "sqlite+pysqlite",
            database=str(db_path),
        )
        return cls(database_url=db_url)

    @staticmethod
    def _create_engine(database_url: str | URL | None) -> Engine:
        engine_kwargs: dict[str, Any] = {"future": True}

        if database_url is None:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
            engine = create_engine("sqlite+pysqlite:///:memory:", **engine_kwargs)
        else:
            db_url = database_url
            if str(db_url).startswith("sqlite"):
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine = create_engine(db_url, **engine_kwargs)

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    def dispose(self) -> None:
        self._engine.dispose()

    def request_suggestion(
        self,
        household_id: str,
        *,
        actor_id: str,
        command: SuggestionRequestCommand,
    ) -> SuggestionEnvelope:
        period_end = self._period_end(command.plan_period_start)
        with self._session_factory() as session:
            self._ensure_household_exists(session, household_id)
            existing = self._get_request_by_idempotency(
                session,
                household_id,
                command.request_idempotency_key,
            )
            if existing is not None:
                self._log_planner_lifecycle(
                    action="request_suggestion",
                    outcome="duplicate",
                    household_id=household_id,
                    correlation_id=existing.id,
                    actor_id=actor_id,
                    request_id=existing.id,
                    client_mutation_id=command.request_idempotency_key,
                    plan_period_start=existing.plan_period_start,
                    plan_period_end=existing.plan_period_end,
                )
                return self._request_to_envelope(session, existing)

            active = self._find_active_request(
                session,
                household_id=household_id,
                plan_period_start=command.plan_period_start,
                plan_period_end=period_end,
                target_slot_id=None,
            )
            if active is not None:
                self._log_planner_lifecycle(
                    action="request_suggestion",
                    outcome="deduped_active",
                    household_id=household_id,
                    correlation_id=active.id,
                    actor_id=actor_id,
                    request_id=active.id,
                    client_mutation_id=command.request_idempotency_key,
                    plan_period_start=active.plan_period_start,
                    plan_period_end=active.plan_period_end,
                )
                return self._request_to_envelope(session, active)

            self._supersede_visible_requests(
                session,
                household_id=household_id,
                plan_period_start=command.plan_period_start,
                plan_period_end=period_end,
                target_slot_id=None,
            )
            request = AISuggestionRequest(
                household_id=household_id,
                actor_id=actor_id,
                plan_period_start=command.plan_period_start,
                plan_period_end=period_end,
                target_slot_id=None,
                status=AISuggestionStatus.queued.value,
                request_idempotency_key=command.request_idempotency_key,
                prompt_family="weekly_meal_plan",
                prompt_version="1.0.0",
                policy_version="1.0.0",
                context_contract_version="1.0.0",
                result_contract_version="1.0.0",
                grounding_hash=self._grounding_hash(
                    household_id=household_id,
                    period_start=command.plan_period_start,
                    period_end=period_end,
                    target_slot_id=None,
                ),
                created_at=_utcnow(),
            )
            session.add(request)
            session.commit()
            session.refresh(request)
            self._log_planner_lifecycle(
                action="request_suggestion",
                outcome="accepted",
                household_id=household_id,
                correlation_id=request.id,
                actor_id=actor_id,
                request_id=request.id,
                client_mutation_id=command.request_idempotency_key,
                plan_period_start=request.plan_period_start,
                plan_period_end=request.plan_period_end,
            )
            return self._request_to_envelope(session, request)

    def get_request(self, household_id: str, request_id: str) -> SuggestionEnvelope | None:
        with self._session_factory() as session:
            request = self._get_request(session, household_id, request_id)
            if request is None:
                return None
            return self._request_to_envelope(session, request)

    def get_latest_suggestion(self, household_id: str, plan_period_start: date) -> SuggestionEnvelope | None:
        period_end = self._period_end(plan_period_start)
        with self._session_factory() as session:
            stmt = (
                select(AISuggestionRequest)
                .where(AISuggestionRequest.household_id == household_id)
                .where(AISuggestionRequest.plan_period_start == plan_period_start)
                .where(AISuggestionRequest.plan_period_end == period_end)
                .where(AISuggestionRequest.target_slot_id.is_(None))
                .order_by(AISuggestionRequest.created_at.desc(), AISuggestionRequest.id.desc())
            )
            request = session.scalar(stmt)
            if request is None:
                return None
            return self._request_to_envelope(session, request)

    def open_draft_from_suggestion(
        self,
        household_id: str,
        *,
        command: DraftCreateCommand,
    ) -> DraftPlanView:
        with self._session_factory() as session:
            result = session.get(AISuggestionResult, command.suggestion_id)
            if result is None:
                raise PlannerDomainError(
                    code="suggestion_not_found",
                    message="AI suggestion result not found.",
                    status_code=404,
                )
            request = session.get(AISuggestionRequest, result.request_id)
            if request is None or request.household_id != household_id:
                raise PlannerDomainError(
                    code="suggestion_not_found",
                    message="AI suggestion result not found.",
                    status_code=404,
                )
            if request.target_slot_id is not None:
                raise PlannerDomainError(
                    code="suggestion_not_openable",
                    message="Slot regeneration results cannot be opened as a weekly draft.",
                    status_code=409,
                )

            existing = self._get_active_draft(
                session,
                household_id=household_id,
                plan_period_start=request.plan_period_start,
                plan_period_end=request.plan_period_end,
            )
            if existing is not None and existing.ai_suggestion_result_id == result.id:
                self._log_planner_lifecycle(
                    action="open_draft",
                    outcome="duplicate",
                    household_id=household_id,
                    correlation_id=self._plan_correlation_id(existing),
                    request_id=request.id,
                    plan_id=existing.id,
                    suggestion_id=result.id,
                    plan_period_start=existing.period_start,
                    plan_period_end=existing.period_end,
                )
                return self._plan_to_draft_view(session, existing)
            if existing is not None and not command.replace_existing:
                raise PlannerDomainError(
                    code="draft_already_exists",
                    message="A draft already exists for this household and week.",
                    status_code=409,
                )
            if existing is not None and command.replace_existing:
                session.delete(existing)
                session.flush()

            plan = MealPlan(
                household_id=household_id,
                period_start=request.plan_period_start,
                period_end=request.plan_period_end,
                status=MealPlanStatus.draft.value,
                ai_suggestion_request_id=request.id,
                ai_suggestion_result_id=result.id,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            session.add(plan)
            session.flush()
            for suggestion_slot in sorted(result.slots, key=lambda slot: (slot.day_of_week, slot.meal_type)):
                slot = MealPlanSlot(
                    meal_plan_id=plan.id,
                    slot_key=suggestion_slot.slot_key,
                    day_of_week=suggestion_slot.day_of_week,
                    meal_type=suggestion_slot.meal_type,
                    meal_title=suggestion_slot.meal_title,
                    meal_summary=suggestion_slot.meal_summary,
                    slot_origin=SlotOrigin.ai_suggested.value,
                    ai_suggestion_request_id=request.id,
                    ai_suggestion_result_id=result.id,
                    reason_codes=self._dump_string_list(self._parse_string_list(suggestion_slot.reason_codes)),
                    explanation_entries=self._dump_string_list(
                        self._parse_string_list(suggestion_slot.explanation_entries)
                    ),
                    prompt_family=request.prompt_family,
                    prompt_version=request.prompt_version,
                    fallback_mode=result.fallback_mode,
                    regen_status=PlanSlotRegenStatus.idle.value,
                    pending_regen_request_id=None,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                session.add(slot)

            session.commit()
            session.refresh(plan)
            self._log_planner_lifecycle(
                action="open_draft",
                outcome="accepted",
                household_id=household_id,
                correlation_id=self._plan_correlation_id(plan),
                request_id=request.id,
                plan_id=plan.id,
                suggestion_id=result.id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
                replaces_existing=command.replace_existing,
            )
            return self._plan_to_draft_view(session, plan)

    def get_draft(self, household_id: str, plan_period_start: date) -> DraftPlanView | None:
        period_end = self._period_end(plan_period_start)
        with self._session_factory() as session:
            draft = self._get_active_draft(
                session,
                household_id=household_id,
                plan_period_start=plan_period_start,
                plan_period_end=period_end,
            )
            if draft is None:
                return None
            return self._plan_to_draft_view(session, draft)

    def update_draft_slot(
        self,
        household_id: str,
        *,
        draft_id: str,
        slot_id: str,
        command: DraftSlotUpdateCommand,
    ) -> PlannerSlotView:
        with self._session_factory() as session:
            plan, slot = self._load_draft_slot(session, household_id, draft_id, slot_id)
            title = self._normalized_text(command.meal_title)
            summary = self._normalized_text(command.meal_summary)
            slot.meal_title = title
            slot.meal_summary = summary
            slot.meal_reference_id = self._normalized_text(command.meal_reference_id)
            slot.slot_origin = (
                SlotOrigin.user_edited.value
                if slot.ai_suggestion_result_id is not None
                else SlotOrigin.manually_added.value
            )
            slot.regen_status = PlanSlotRegenStatus.idle.value
            slot.pending_regen_request_id = None
            slot.updated_at = _utcnow()
            plan.updated_at = _utcnow()
            session.commit()
            session.refresh(slot)
            return self._slot_to_view(session, slot)

    def revert_draft_slot(self, household_id: str, *, draft_id: str, slot_id: str) -> PlannerSlotView:
        with self._session_factory() as session:
            plan, slot = self._load_draft_slot(session, household_id, draft_id, slot_id)
            suggestion_slot = self._find_original_suggestion_slot(session, slot)
            if suggestion_slot is None:
                raise PlannerDomainError(
                    code="original_suggestion_not_found",
                    message="This slot does not have an AI suggestion to restore.",
                    status_code=409,
                )
            result = session.get(AISuggestionResult, slot.ai_suggestion_result_id)
            if result is None:
                raise PlannerDomainError(
                    code="original_suggestion_not_found",
                    message="This slot does not have an AI suggestion to restore.",
                    status_code=409,
                )
            request = session.get(AISuggestionRequest, result.request_id)
            if request is None:
                raise PlannerDomainError(
                    code="original_suggestion_not_found",
                    message="This slot does not have an AI suggestion to restore.",
                    status_code=409,
                )
            self._apply_suggestion_to_slot(slot, request, result, suggestion_slot)
            plan.updated_at = _utcnow()
            session.commit()
            session.refresh(slot)
            return self._slot_to_view(session, slot)

    def request_slot_regeneration(
        self,
        household_id: str,
        *,
        draft_id: str,
        slot_id: str,
        actor_id: str,
        command: SlotRegenerateCommand,
    ) -> SuggestionEnvelope:
        with self._session_factory() as session:
            plan, slot = self._load_draft_slot(session, household_id, draft_id, slot_id)
            existing = self._get_request_by_idempotency(
                session,
                household_id,
                command.client_mutation_id,
            )
            if existing is not None:
                self._log_planner_lifecycle(
                    action="request_regeneration",
                    outcome="duplicate",
                    household_id=household_id,
                    correlation_id=existing.id,
                    actor_id=actor_id,
                    request_id=existing.id,
                    plan_id=plan.id,
                    slot_id=slot.id,
                    client_mutation_id=command.client_mutation_id,
                    plan_period_start=plan.period_start,
                    plan_period_end=plan.period_end,
                )
                return self._request_to_envelope(session, existing)

            active = self._find_active_request(
                session,
                household_id=household_id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
                target_slot_id=slot.id,
            )
            if active is not None:
                self._log_planner_lifecycle(
                    action="request_regeneration",
                    outcome="deduped_active",
                    household_id=household_id,
                    correlation_id=active.id,
                    actor_id=actor_id,
                    request_id=active.id,
                    plan_id=plan.id,
                    slot_id=slot.id,
                    client_mutation_id=command.client_mutation_id,
                    plan_period_start=plan.period_start,
                    plan_period_end=plan.period_end,
                )
                return self._request_to_envelope(session, active)

            self._supersede_visible_requests(
                session,
                household_id=household_id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
                target_slot_id=slot.id,
            )
            request = AISuggestionRequest(
                household_id=household_id,
                actor_id=actor_id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
                target_slot_id=slot.id,
                meal_plan_id=plan.id,
                meal_plan_slot_id=slot.id,
                status=AISuggestionStatus.queued.value,
                request_idempotency_key=command.client_mutation_id,
                prompt_family="slot_regeneration",
                prompt_version="1.0.0",
                policy_version="1.0.0",
                context_contract_version="1.0.0",
                result_contract_version="1.0.0",
                grounding_hash=self._grounding_hash(
                    household_id=household_id,
                    period_start=plan.period_start,
                    period_end=plan.period_end,
                    target_slot_id=slot.id,
                ),
                created_at=_utcnow(),
            )
            session.add(request)
            session.flush()
            slot.regen_status = PlanSlotRegenStatus.pending_regen.value
            slot.pending_regen_request_id = request.id
            slot.updated_at = _utcnow()
            plan.updated_at = _utcnow()
            session.commit()
            session.refresh(request)
            self._log_planner_lifecycle(
                action="request_regeneration",
                outcome="accepted",
                household_id=household_id,
                correlation_id=request.id,
                actor_id=actor_id,
                request_id=request.id,
                plan_id=plan.id,
                slot_id=slot.id,
                client_mutation_id=command.client_mutation_id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
            )
            return self._request_to_envelope(session, request)

    def confirm_draft(
        self,
        household_id: str,
        *,
        draft_id: str,
        actor_id: str,
        command: DraftConfirmRequest,
    ) -> ConfirmedPlanView:
        with self._session_factory() as session:
            existing = self._get_confirmed_by_mutation(
                session,
                household_id=household_id,
                client_mutation_id=command.client_mutation_id,
            )
            if existing is not None:
                self._log_planner_lifecycle(
                    action="confirm_draft",
                    outcome="duplicate",
                    household_id=household_id,
                    correlation_id=self._plan_correlation_id(existing),
                    actor_id=actor_id,
                    plan_id=existing.id,
                    client_mutation_id=command.client_mutation_id,
                    plan_period_start=existing.period_start,
                    plan_period_end=existing.period_end,
                    grocery_refresh_triggered=True,
                )
                return self._plan_to_confirmed_view(session, existing)

            plan = self._get_plan(session, household_id, draft_id, status=MealPlanStatus.draft.value)
            if plan is None:
                raise PlannerDomainError(
                    code="draft_not_found",
                    message="Draft plan not found.",
                    status_code=404,
                )
            stale_warning = self._plan_is_stale(session, plan)
            if stale_warning and not command.stale_warning_acknowledged:
                self._log_planner_lifecycle(
                    action="confirm_draft",
                    outcome="blocked_stale",
                    household_id=household_id,
                    correlation_id=self._plan_correlation_id(plan),
                    actor_id=actor_id,
                    plan_id=plan.id,
                    client_mutation_id=command.client_mutation_id,
                    plan_period_start=plan.period_start,
                    plan_period_end=plan.period_end,
                )
                raise PlannerDomainError(
                    code="stale_warning_ack_required",
                    message="Acknowledge the stale-draft warning before confirming this plan.",
                    status_code=409,
                )

            confirmation_time = _utcnow()
            prior_confirmed = self._get_latest_confirmed_plan(
                session,
                household_id=household_id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
            )
            plan.status = MealPlanStatus.confirmed.value
            plan.confirmed_at = confirmation_time
            plan.confirmation_client_mutation_id = command.client_mutation_id
            plan.stale_warning_acknowledged = stale_warning and command.stale_warning_acknowledged
            prior_version = prior_confirmed.version if prior_confirmed is not None else 0
            plan.version = max(plan.version + 1, prior_version + 1)
            plan.updated_at = confirmation_time

            existing_history_stmt = select(MealPlanSlotHistory).where(MealPlanSlotHistory.meal_plan_id == plan.id)
            if session.scalars(existing_history_stmt).first() is None:
                for slot in plan.slots:
                    history = MealPlanSlotHistory(
                        meal_plan_slot_id=slot.id,
                        meal_plan_id=plan.id,
                        slot_key=slot.slot_key,
                        slot_origin=slot.slot_origin,
                        ai_suggestion_request_id=slot.ai_suggestion_request_id,
                        ai_suggestion_result_id=slot.ai_suggestion_result_id,
                        reason_codes=slot.reason_codes,
                        explanation_entries=slot.explanation_entries,
                        prompt_family=slot.prompt_family,
                        prompt_version=slot.prompt_version,
                        fallback_mode=slot.fallback_mode,
                        stale_warning_present_at_confirmation=stale_warning,
                        confirmed_at=confirmation_time,
                        created_at=confirmation_time,
                    )
                    session.add(history)

            event_payload = self._build_plan_confirmed_event(
                plan,
                actor_id=actor_id,
                confirmation_client_mutation_id=command.client_mutation_id,
            )
            session.add(
                PlannerEvent(
                    household_id=plan.household_id,
                    meal_plan_id=plan.id,
                    event_type=event_payload.event_type,
                    source_mutation_id=command.client_mutation_id,
                    payload=event_payload.model_dump_json(),
                    occurred_at=confirmation_time,
                )
            )

            session.commit()
            session.refresh(plan)
            self._log_planner_lifecycle(
                action="confirm_draft",
                outcome="accepted",
                household_id=household_id,
                correlation_id=event_payload.correlation_id,
                actor_id=actor_id,
                plan_id=plan.id,
                client_mutation_id=command.client_mutation_id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
                grocery_refresh_triggered=True,
            )
            return self._plan_to_confirmed_view(session, plan)

    def get_confirmed_plan(
        self,
        household_id: str,
        plan_period_start: date,
    ) -> ConfirmedPlanView | None:
        period_end = self._period_end(plan_period_start)
        with self._session_factory() as session:
            stmt = (
                select(MealPlan)
                .where(MealPlan.household_id == household_id)
                .where(MealPlan.period_start == plan_period_start)
                .where(MealPlan.period_end == period_end)
                .where(MealPlan.status == MealPlanStatus.confirmed.value)
                .order_by(MealPlan.confirmed_at.desc(), MealPlan.updated_at.desc(), MealPlan.id.desc())
            )
            plan = session.scalar(stmt)
            if plan is None:
                return None
            return self._plan_to_confirmed_view(session, plan)

    def update_request_status(self, household_id: str, request_id: str, status: AISuggestionStatus) -> SuggestionEnvelope:
        with self._session_factory() as session:
            request = self._get_request(session, household_id, request_id)
            if request is None:
                raise PlannerDomainError(
                    code="request_not_found",
                    message="AI request not found.",
                    status_code=404,
                )
            request.status = status.value
            if status in {
                AISuggestionStatus.completed,
                AISuggestionStatus.completed_with_fallback,
                AISuggestionStatus.failed,
                AISuggestionStatus.stale,
                AISuggestionStatus.superseded,
            }:
                request.completed_at = _utcnow()
            session.commit()
            session.refresh(request)
            return self._request_to_envelope(session, request)

    def complete_request(self, request_id: str) -> None:
        GenerationWorker(session_factory=self._session_factory).process_request(request_id)

    def _materialize_weekly_result(self, session: Session, request: AISuggestionRequest) -> AISuggestionResult:
        result = AISuggestionResult(
            request_id=request.id,
            meal_plan_id=None,
            fallback_mode="none",
            stale_flag=False,
            result_contract_version=request.result_contract_version,
            created_at=_utcnow(),
        )
        session.add(result)
        session.flush()
        for day_of_week in range(7):
            for meal_type in MEAL_TYPES:
                title = self._generated_title(
                    day_of_week=day_of_week,
                    meal_type=meal_type,
                    request=request,
                    regeneration=False,
                )
                slot = AISuggestionSlot(
                    result_id=result.id,
                    slot_key=self._slot_key(day_of_week, meal_type),
                    day_of_week=day_of_week,
                    meal_type=meal_type,
                    meal_title=title,
                    meal_summary=f"{title} built for household week planning.",
                    reason_codes=self._dump_string_list(
                        ["uses_on_hand", "balanced_rotation" if meal_type == "dinner" else "household_rhythm"]
                    ),
                    explanation_entries=self._dump_string_list(
                        [
                            f"Planned for {meal_type} on day {day_of_week + 1}.",
                            "Keeps draft suggestions explainable and editable.",
                        ]
                    ),
                    uses_on_hand=self._dump_string_list(["pantry staples"]),
                    missing_hints=self._dump_string_list(["fresh herbs"]),
                    is_fallback=False,
                    created_at=_utcnow(),
                )
                session.add(slot)
        session.flush()
        return result

    def _materialize_regenerated_slot(self, session: Session, request: AISuggestionRequest) -> AISuggestionResult:
        plan = session.get(MealPlan, request.meal_plan_id)
        slot = session.get(MealPlanSlot, request.meal_plan_slot_id)
        if plan is None or slot is None or plan.household_id != request.household_id:
            request.status = AISuggestionStatus.failed.value
            request.completed_at = _utcnow()
            return AISuggestionResult(
                request_id=request.id,
                meal_plan_id=request.meal_plan_id,
                fallback_mode="manual_guidance",
                stale_flag=False,
                result_contract_version=request.result_contract_version,
                created_at=_utcnow(),
            )

        result = AISuggestionResult(
            request_id=request.id,
            meal_plan_id=plan.id,
            fallback_mode="none",
            stale_flag=False,
            result_contract_version=request.result_contract_version,
            created_at=_utcnow(),
        )
        session.add(result)
        session.flush()

        title = self._generated_title(
            day_of_week=slot.day_of_week,
            meal_type=slot.meal_type,
            request=request,
            regeneration=True,
        )
        suggestion_slot = AISuggestionSlot(
            result_id=result.id,
            slot_key=slot.slot_key,
            day_of_week=slot.day_of_week,
            meal_type=slot.meal_type,
            meal_title=title,
            meal_summary=f"{title} refreshed for this single slot.",
            reason_codes=self._dump_string_list(["fresh_regeneration", "household_fit"]),
            explanation_entries=self._dump_string_list(
                [
                    "Generated from the latest household planner context.",
                    "Only this slot changed; the rest of the draft stayed intact.",
                ]
            ),
            uses_on_hand=self._dump_string_list(["updated pantry context"]),
            missing_hints=self._dump_string_list(["optional garnish"]),
            is_fallback=False,
            created_at=_utcnow(),
        )
        session.add(suggestion_slot)
        session.flush()

        self._apply_suggestion_to_slot(slot, request, result, suggestion_slot)
        plan.updated_at = _utcnow()
        return result

    def _load_draft_slot(
        self,
        session: Session,
        household_id: str,
        draft_id: str,
        slot_id: str,
    ) -> tuple[MealPlan, MealPlanSlot]:
        plan = self._get_plan(session, household_id, draft_id, status=MealPlanStatus.draft.value)
        if plan is None:
            raise PlannerDomainError(
                code="draft_not_found",
                message="Draft plan not found.",
                status_code=404,
            )
        slot = session.get(MealPlanSlot, slot_id)
        if slot is None or slot.meal_plan_id != plan.id:
            raise PlannerDomainError(
                code="slot_not_found",
                message="Draft slot not found.",
                status_code=404,
            )
        return plan, slot

    def _get_plan(
        self,
        session: Session,
        household_id: str,
        plan_id: str,
        *,
        status: str | None = None,
    ) -> MealPlan | None:
        stmt = select(MealPlan).where(MealPlan.id == plan_id).where(MealPlan.household_id == household_id)
        if status is not None:
            stmt = stmt.where(MealPlan.status == status)
        return session.scalar(stmt)

    def _get_request(self, session: Session, household_id: str, request_id: str) -> AISuggestionRequest | None:
        stmt = (
            select(AISuggestionRequest)
            .where(AISuggestionRequest.id == request_id)
            .where(AISuggestionRequest.household_id == household_id)
        )
        return session.scalar(stmt)

    def _get_request_by_idempotency(
        self,
        session: Session,
        household_id: str,
        request_idempotency_key: str,
    ) -> AISuggestionRequest | None:
        stmt = (
            select(AISuggestionRequest)
            .where(AISuggestionRequest.household_id == household_id)
            .where(AISuggestionRequest.request_idempotency_key == request_idempotency_key)
        )
        return session.scalar(stmt)

    def _find_active_request(
        self,
        session: Session,
        *,
        household_id: str,
        plan_period_start: date,
        plan_period_end: date,
        target_slot_id: str | None,
    ) -> AISuggestionRequest | None:
        stmt = (
            select(AISuggestionRequest)
            .where(AISuggestionRequest.household_id == household_id)
            .where(AISuggestionRequest.plan_period_start == plan_period_start)
            .where(AISuggestionRequest.plan_period_end == plan_period_end)
            .where(AISuggestionRequest.status.in_(ACTIVE_REQUEST_STATUSES))
        )
        if target_slot_id is None:
            stmt = stmt.where(AISuggestionRequest.target_slot_id.is_(None))
        else:
            stmt = stmt.where(AISuggestionRequest.target_slot_id == target_slot_id)
        stmt = stmt.order_by(AISuggestionRequest.created_at.desc(), AISuggestionRequest.id.desc())
        return session.scalar(stmt)

    def _supersede_visible_requests(
        self,
        session: Session,
        *,
        household_id: str,
        plan_period_start: date,
        plan_period_end: date,
        target_slot_id: str | None,
    ) -> None:
        stmt = (
            select(AISuggestionRequest)
            .where(AISuggestionRequest.household_id == household_id)
            .where(AISuggestionRequest.plan_period_start == plan_period_start)
            .where(AISuggestionRequest.plan_period_end == plan_period_end)
            .where(AISuggestionRequest.status.in_(VISIBLE_REQUEST_STATUSES))
        )
        if target_slot_id is None:
            stmt = stmt.where(AISuggestionRequest.target_slot_id.is_(None))
        else:
            stmt = stmt.where(AISuggestionRequest.target_slot_id == target_slot_id)
        for request in session.scalars(stmt).all():
            if request.status not in ACTIVE_REQUEST_STATUSES:
                request.status = AISuggestionStatus.superseded.value
                request.completed_at = request.completed_at or _utcnow()

    def _get_active_draft(
        self,
        session: Session,
        *,
        household_id: str,
        plan_period_start: date,
        plan_period_end: date,
    ) -> MealPlan | None:
        stmt = (
            select(MealPlan)
            .where(MealPlan.household_id == household_id)
            .where(MealPlan.period_start == plan_period_start)
            .where(MealPlan.period_end == plan_period_end)
            .where(MealPlan.status == MealPlanStatus.draft.value)
            .order_by(MealPlan.updated_at.desc(), MealPlan.id.desc())
        )
        return session.scalar(stmt)

    def _get_confirmed_by_mutation(
        self,
        session: Session,
        *,
        household_id: str,
        client_mutation_id: str,
    ) -> MealPlan | None:
        stmt = (
            select(MealPlan)
            .where(MealPlan.household_id == household_id)
            .where(MealPlan.confirmation_client_mutation_id == client_mutation_id)
            .where(MealPlan.status == MealPlanStatus.confirmed.value)
        )
        return session.scalar(stmt)

    def _get_latest_confirmed_plan(
        self,
        session: Session,
        *,
        household_id: str,
        plan_period_start: date,
        plan_period_end: date,
    ) -> MealPlan | None:
        stmt = (
            select(MealPlan)
            .where(MealPlan.household_id == household_id)
            .where(MealPlan.period_start == plan_period_start)
            .where(MealPlan.period_end == plan_period_end)
            .where(MealPlan.status == MealPlanStatus.confirmed.value)
            .order_by(MealPlan.version.desc(), MealPlan.confirmed_at.desc(), MealPlan.updated_at.desc(), MealPlan.id.desc())
        )
        return session.scalar(stmt)

    def _plan_to_draft_view(self, session: Session, plan: MealPlan) -> DraftPlanView:
        return DraftPlanView(
            id=plan.id,
            household_id=plan.household_id,
            period_start=plan.period_start,
            period_end=plan.period_end,
            status=MealPlanStatus(plan.status),
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            stale_warning=self._plan_is_stale(session, plan),
            stale_warning_acknowledged=plan.stale_warning_acknowledged,
            ai_suggestion_request_id=plan.ai_suggestion_request_id,
            ai_suggestion_result_id=plan.ai_suggestion_result_id,
            slots=[self._slot_to_view(session, slot) for slot in self._ordered_slots(plan.slots)],
        )

    def _plan_to_confirmed_view(self, session: Session, plan: MealPlan) -> ConfirmedPlanView:
        confirmed_at = plan.confirmed_at or plan.updated_at
        return ConfirmedPlanView(
            id=plan.id,
            household_id=plan.household_id,
            period_start=plan.period_start,
            period_end=plan.period_end,
            status=MealPlanStatus(plan.status),
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            confirmed_at=confirmed_at,
            stale_warning_acknowledged=plan.stale_warning_acknowledged,
            ai_suggestion_request_id=plan.ai_suggestion_request_id,
            ai_suggestion_result_id=plan.ai_suggestion_result_id,
            slots=[self._slot_to_view(session, slot) for slot in self._ordered_slots(plan.slots)],
        )

    def _request_to_envelope(self, session: Session, request: AISuggestionRequest) -> SuggestionEnvelope:
        result = self._get_result_for_request(session, request.id)
        slots: list[PlannerSlotView] = []
        suggestion_id: str | None = None
        fallback_mode = "none"
        is_stale = request.status == AISuggestionStatus.stale.value or self._request_has_stale_grounding(session, request)
        if result is not None:
            suggestion_id = result.id
            slots = [self._suggestion_slot_to_view(slot) for slot in self._ordered_slots(result.slots)]
            fallback_mode = result.fallback_mode
            is_stale = is_stale or result.stale_flag
        response_status = (
            AISuggestionStatus.stale
            if is_stale and request.status in TERMINAL_SUGGESTION_STATUSES
            else AISuggestionStatus(request.status)
        )

        return SuggestionEnvelope(
            request_id=request.id,
            household_id=request.household_id,
            plan_period_start=request.plan_period_start,
            plan_period_end=request.plan_period_end,
            status=response_status,
            created_at=request.created_at,
            completed_at=request.completed_at,
            suggestion_id=suggestion_id,
            meal_plan_id=request.meal_plan_id,
            slots=slots,
            is_stale=is_stale,
            fallback_mode=fallback_mode,
            prompt_family=request.prompt_family,
            prompt_version=request.prompt_version,
            policy_version=request.policy_version,
            context_contract_version=request.context_contract_version,
            result_contract_version=result.result_contract_version if result is not None else request.result_contract_version,
        )

    def _slot_to_view(self, session: Session, slot: MealPlanSlot) -> PlannerSlotView:
        original = self._original_snapshot(session, slot)
        is_ai_active = slot.slot_origin == SlotOrigin.ai_suggested.value
        return PlannerSlotView(
            id=slot.id,
            slot_key=slot.slot_key,
            day_of_week=slot.day_of_week,
            meal_type=slot.meal_type,
            meal_title=slot.meal_title,
            meal_summary=slot.meal_summary,
            meal_reference_id=slot.meal_reference_id,
            slot_origin=SlotOrigin(slot.slot_origin),
            reason_codes=self._parse_string_list(slot.reason_codes) if is_ai_active else [],
            explanation_entries=self._parse_string_list(slot.explanation_entries) if is_ai_active else [],
            regen_status=PlanSlotRegenStatus(slot.regen_status),
            pending_regen_request_id=slot.pending_regen_request_id,
            is_user_locked=slot.is_user_locked,
            prompt_family=slot.prompt_family,
            prompt_version=slot.prompt_version,
            fallback_mode=slot.fallback_mode,
            slot_message=self._slot_message(slot),
            original_suggestion=original,
            uses_on_hand=original.uses_on_hand if original is not None and is_ai_active else [],
            missing_hints=original.missing_hints if original is not None and is_ai_active else [],
        )

    def _suggestion_slot_to_view(self, slot: AISuggestionSlot) -> PlannerSlotView:
        snapshot = PlannerSlotSuggestionSnapshot(
            meal_title=slot.meal_title,
            meal_summary=slot.meal_summary,
            reason_codes=self._parse_string_list(slot.reason_codes),
            explanation_entries=self._parse_string_list(slot.explanation_entries),
            uses_on_hand=self._parse_string_list(slot.uses_on_hand),
            missing_hints=self._parse_string_list(slot.missing_hints),
        )
        return PlannerSlotView(
            id=slot.id,
            slot_key=slot.slot_key,
            day_of_week=slot.day_of_week,
            meal_type=slot.meal_type,
            meal_title=slot.meal_title,
            meal_summary=slot.meal_summary,
            meal_reference_id=None,
            slot_origin=SlotOrigin.ai_suggested,
            reason_codes=snapshot.reason_codes,
            explanation_entries=snapshot.explanation_entries,
            regen_status=PlanSlotRegenStatus.idle,
            pending_regen_request_id=None,
            is_user_locked=False,
            prompt_family=None,
            prompt_version=None,
            fallback_mode="curated_fallback" if slot.is_fallback else "none",
            original_suggestion=snapshot,
            uses_on_hand=snapshot.uses_on_hand,
            missing_hints=snapshot.missing_hints,
        )

    def _original_snapshot(
        self,
        session: Session,
        slot: MealPlanSlot,
    ) -> PlannerSlotSuggestionSnapshot | None:
        suggestion_slot = self._find_original_suggestion_slot(session, slot)
        if suggestion_slot is None:
            return None
        return PlannerSlotSuggestionSnapshot(
            meal_title=suggestion_slot.meal_title,
            meal_summary=suggestion_slot.meal_summary,
            reason_codes=self._parse_string_list(suggestion_slot.reason_codes),
            explanation_entries=self._parse_string_list(suggestion_slot.explanation_entries),
            uses_on_hand=self._parse_string_list(suggestion_slot.uses_on_hand),
            missing_hints=self._parse_string_list(suggestion_slot.missing_hints),
        )

    def _find_original_suggestion_slot(
        self,
        session: Session,
        slot: MealPlanSlot,
    ) -> AISuggestionSlot | None:
        if slot.ai_suggestion_result_id is None:
            return None
        stmt = (
            select(AISuggestionSlot)
            .where(AISuggestionSlot.result_id == slot.ai_suggestion_result_id)
            .where(AISuggestionSlot.slot_key == slot.slot_key)
        )
        return session.scalar(stmt)

    def _apply_suggestion_to_slot(
        self,
        slot: MealPlanSlot,
        request: AISuggestionRequest,
        result: AISuggestionResult,
        suggestion_slot: AISuggestionSlot,
    ) -> None:
        slot.meal_title = suggestion_slot.meal_title
        slot.meal_summary = suggestion_slot.meal_summary
        slot.slot_origin = SlotOrigin.ai_suggested.value
        slot.ai_suggestion_request_id = request.id
        slot.ai_suggestion_result_id = result.id
        slot.reason_codes = suggestion_slot.reason_codes
        slot.explanation_entries = suggestion_slot.explanation_entries
        slot.prompt_family = request.prompt_family
        slot.prompt_version = request.prompt_version
        slot.fallback_mode = result.fallback_mode
        slot.regen_status = PlanSlotRegenStatus.idle.value
        slot.pending_regen_request_id = None
        slot.updated_at = _utcnow()

    def _get_result_for_request(self, session: Session, request_id: str) -> AISuggestionResult | None:
        stmt = select(AISuggestionResult).where(AISuggestionResult.request_id == request_id)
        return session.scalar(stmt)

    def _plan_is_stale(self, session: Session, plan: MealPlan) -> bool:
        request_ids = {
            request_id
            for request_id in [plan.ai_suggestion_request_id, *[slot.ai_suggestion_request_id for slot in plan.slots]]
            if request_id is not None
        }
        for request_id in request_ids:
            request = session.get(AISuggestionRequest, request_id)
            if request is not None and (
                request.status == AISuggestionStatus.stale.value or self._request_has_stale_grounding(session, request)
            ):
                return True
        result_ids = {
            result_id
            for result_id in [plan.ai_suggestion_result_id, *[slot.ai_suggestion_result_id for slot in plan.slots]]
            if result_id is not None
        }
        for result_id in result_ids:
            result = session.get(AISuggestionResult, result_id)
            if result is not None and result.stale_flag:
                return True
        return False

    def _request_has_stale_grounding(self, session: Session, request: AISuggestionRequest) -> bool:
        if request.grounding_hash is None or request.status not in TERMINAL_SUGGESTION_STATUSES:
            return False

        plan = session.get(MealPlan, request.meal_plan_id) if request.meal_plan_id else None
        target_slot = session.get(MealPlanSlot, request.meal_plan_slot_id) if request.meal_plan_slot_id else None
        current_hash = GenerationWorker(session_factory=self._session_factory).compute_grounding_hash(
            session,
            request,
            plan=plan,
            target_slot=target_slot,
        )
        return current_hash != request.grounding_hash

    @staticmethod
    def _build_plan_confirmed_event(
        plan: MealPlan,
        *,
        actor_id: str,
        confirmation_client_mutation_id: str,
    ) -> PlanConfirmedEvent:
        correlation_id = PlannerService._plan_correlation_id(plan)
        return PlanConfirmedEvent(
            household_id=plan.household_id,
            meal_plan_id=plan.id,
            plan_period_start=plan.period_start,
            plan_period_end=plan.period_end,
            confirmed_at=plan.confirmed_at or plan.updated_at,
            source_plan_status=MealPlanStatus.confirmed.value,
            stale_warning_acknowledged=plan.stale_warning_acknowledged,
            confirmation_client_mutation_id=confirmation_client_mutation_id,
            actor_id=actor_id,
            slot_count=len(plan.slots),
            plan_version=plan.version,
            correlation_id=correlation_id,
            grocery_refresh_trigger=GroceryRefreshTrigger(
                household_id=plan.household_id,
                confirmed_plan_id=plan.id,
                plan_period_start=plan.period_start,
                plan_period_end=plan.period_end,
                source_plan_version=plan.version,
                correlation_id=correlation_id,
            ),
        )

    @staticmethod
    def _plan_correlation_id(plan: MealPlan) -> str:
        return (
            plan.ai_suggestion_request_id
            or plan.confirmation_client_mutation_id
            or plan.id
        )

    def _log_planner_lifecycle(
        self,
        *,
        action: str,
        outcome: str,
        household_id: str,
        correlation_id: str,
        actor_id: str | None = None,
        request_id: str | None = None,
        plan_id: str | None = None,
        slot_id: str | None = None,
        suggestion_id: str | None = None,
        client_mutation_id: str | None = None,
        plan_period_start: date | None = None,
        plan_period_end: date | None = None,
        replaces_existing: bool | None = None,
        grocery_refresh_triggered: bool = False,
    ) -> None:
        level = logging.INFO if outcome in {"accepted", "duplicate", "deduped_active"} else logging.WARNING
        logger.log(
            level,
            "planner lifecycle %s",
            action,
            extra={
                "planner_action": action,
                "planner_outcome": outcome,
                "planner_household_id": household_id,
                "planner_actor_id": actor_id,
                "planner_request_id": request_id,
                "planner_plan_id": plan_id,
                "planner_slot_id": slot_id,
                "planner_suggestion_id": suggestion_id,
                "planner_client_mutation_id": client_mutation_id,
                "planner_plan_period_start": plan_period_start.isoformat() if plan_period_start else None,
                "planner_plan_period_end": plan_period_end.isoformat() if plan_period_end else None,
                "planner_replaces_existing": replaces_existing,
                "planner_correlation_id": correlation_id,
                "planner_grocery_refresh_triggered": grocery_refresh_triggered,
            },
        )

    def _slot_message(self, slot: MealPlanSlot) -> str | None:
        if slot.regen_status == PlanSlotRegenStatus.pending_regen.value:
            return "Waiting for a refreshed suggestion for this slot."
        if slot.regen_status == PlanSlotRegenStatus.regenerating.value:
            return "Generating a refreshed suggestion for this slot."
        if slot.regen_status == PlanSlotRegenStatus.regen_failed.value:
            return "Could not regenerate this slot. Retry or edit it manually."
        return None

    def _ensure_household_exists(self, session: Session, household_id: str) -> None:
        household = session.get(Household, household_id)
        if household is None:
            now = _utcnow()
            session.add(Household(id=household_id, name="Household", created_at=now, updated_at=now))
            session.flush()

    @staticmethod
    def _period_end(period_start: date) -> date:
        return period_start + timedelta(days=6)

    @staticmethod
    def _slot_key(day_of_week: int, meal_type: str) -> str:
        return f"{day_of_week}:{meal_type}"

    @staticmethod
    def _grounding_hash(
        *,
        household_id: str,
        period_start: date,
        period_end: date,
        target_slot_id: str | None,
    ) -> str:
        return f"{household_id}:{period_start.isoformat()}:{period_end.isoformat()}:{target_slot_id or 'full-week'}"

    @staticmethod
    def _generated_title(
        *,
        day_of_week: int,
        meal_type: str,
        request: AISuggestionRequest,
        regeneration: bool,
    ) -> str:
        prefix = "Refreshed" if regeneration else "Suggested"
        return f"{prefix} {meal_type.title()} {day_of_week + 1}"

    @staticmethod
    def _normalized_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _parse_string_list(value: str | None) -> list[str]:
        if value is None or value == "":
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
        return [str(parsed)]

    @staticmethod
    def _dump_string_list(values: Iterable[str]) -> str:
        return json.dumps([value for value in values if value])

    @staticmethod
    def _ordered_slots(slots: Iterable[Any]) -> list[Any]:
        return sorted(slots, key=lambda slot: (slot.day_of_week, slot.meal_type, slot.id))


_default_service = PlannerService.for_default_app()


def get_planner_service() -> PlannerService:
    return _default_service
