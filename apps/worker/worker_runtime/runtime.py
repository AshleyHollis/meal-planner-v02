from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
import random
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy import URL, Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

API_ROOT = Path(__file__).resolve().parents[2] / "api"
WORKER_ROOT = Path(__file__).resolve().parents[1]


def _ensure_import_priority(path: Path) -> None:
    path_str = str(path)
    while path_str in sys.path:
        sys.path.remove(path_str)
    sys.path.insert(0, path_str)


def _loaded_module_is_under(module_name: str, root: Path) -> bool:
    module = sys.modules.get(module_name)
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return False
    return Path(module_file).resolve().is_relative_to(root.resolve())


_ensure_import_priority(API_ROOT)
if _loaded_module_is_under("app", WORKER_ROOT):
    sys.modules.pop("app", None)

importlib.import_module("app.models")
from app.models.ai_planning import AISuggestionRequest, AISuggestionResult, AISuggestionSlot
from app.models.household import Household
from app.models.inventory import InventoryItem
from app.models.meal_plan import MealPlan, MealPlanSlot
from app.schemas.enums import AISuggestionStatus, PlanSlotRegenStatus, SlotOrigin

MEAL_TYPES = ("breakfast", "lunch", "dinner")
SUPPORTED_MEAL_TYPES = frozenset(MEAL_TYPES)
FALLBACK_MODES = ("none", "curated_fallback", "manual_guidance")
PRIMARY_PROMPT_FAMILY = "weekly_meal_plan"
REGEN_PROMPT_FAMILY = "slot_regeneration"
PROMPT_VERSION = "1.0.0"
POLICY_VERSION = "1.0.0"
CONTEXT_CONTRACT_VERSION = "1.0.0"
RESULT_CONTRACT_VERSION = "1.0.0"
ACTIVE_REQUEST_STATUSES = {
    AISuggestionStatus.queued.value,
    AISuggestionStatus.pending.value,
    AISuggestionStatus.generating.value,
}
TERMINAL_REUSE_STATUSES = {
    AISuggestionStatus.completed.value,
    AISuggestionStatus.completed_with_fallback.value,
}
logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _json_dump(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _dump_list(values: Iterable[str]) -> str:
    return json.dumps([value for value in values if value])


def _parse_list(raw: str | None) -> list[str]:
    if raw is None or raw == "":
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return [str(parsed)]


@dataclass(frozen=True)
class WorkerSettings:
    queue_name: str
    database_url: str | None


def load_worker_settings() -> WorkerSettings:
    return WorkerSettings(
        queue_name=os.getenv("MEAL_PLANNER_QUEUE_NAME", "meal-planner-default"),
        database_url=os.getenv("MEAL_PLANNER_DATABASE_URL"),
    )


def build_session_factory(database_url: str | URL) -> sessionmaker[Session]:
    engine_kwargs: dict[str, object] = {"future": True}
    if str(database_url).startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **engine_kwargs)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return sessionmaker(bind=engine, expire_on_commit=False)


class SourceExplanation(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)


class SlotSuggestionContract(BaseModel):
    slot_key: str = Field(min_length=1)
    meal_title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1)
    uses_on_hand: list[str] = Field(default_factory=list)
    missing_key_ingredients: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(min_length=1, max_length=3)
    explanations: list[SourceExplanation] = Field(min_length=1, max_length=3)
    grocery_impact_hint: str | None = None

    @field_validator("reason_codes")
    @classmethod
    def _normalize_reason_codes(cls, value: list[str]) -> list[str]:
        normalized = [code.strip().upper() for code in value if code and code.strip()]
        if not normalized:
            raise ValueError("At least one reason code is required.")
        return normalized

    @model_validator(mode="after")
    def _validate_codes_and_explanations(self) -> "SlotSuggestionContract":
        explanation_codes = {entry.code.strip().upper() for entry in self.explanations}
        reason_codes = set(self.reason_codes)
        if not explanation_codes & reason_codes:
            raise ValueError("At least one explanation must reference a reason code.")
        return self


class SuggestionResultContract(BaseModel):
    fallback_mode: Literal["none", "curated_fallback", "manual_guidance"] = "none"
    warnings: list[str] = Field(default_factory=list)
    data_completeness_note: str | None = None
    slots: list[SlotSuggestionContract] = Field(default_factory=list)


@dataclass(frozen=True)
class RequestedSlot:
    slot_key: str
    day_of_week: int
    meal_type: str


class AIGenerationProvider(Protocol):
    def generate(self, *, prompt_bundle: dict[str, str], grounding: dict[str, object]) -> dict[str, object]:
        ...


class DeterministicGenerationProvider:
    _MEAL_BY_TYPE: dict[str, tuple[str, ...]] = {
        "breakfast": ("Skillet Eggs", "Yogurt Bowl", "Oatmeal Bowl", "Toast Plate"),
        "lunch": ("Grain Bowl", "Soup Lunch", "Wrap Plate", "Leftover Lunch"),
        "dinner": ("Tray Bake", "Rice Bowl", "Pasta Toss", "Skillet Supper"),
    }

    def generate(self, *, prompt_bundle: dict[str, str], grounding: dict[str, object]) -> dict[str, object]:
        requested_slots = grounding["slot_requirements"]
        priority_items = grounding["inventory_priority_items"]
        recent_titles = {title.lower() for title in grounding["recent_meals"]}
        warnings = list(grounding["context_warnings"])
        data_note = (
            "Inventory and meal history were both sparse, so suggestions lean on household-safe defaults."
            if "inventory_sparse" in warnings and "recent_meals_sparse" in warnings
            else "Recent meal history was sparse; suggestions prefer on-hand and expiring items when possible."
            if "recent_meals_sparse" in warnings
            else "Inventory context was sparse; suggestions rely more on stable household-safe defaults."
            if "inventory_sparse" in warnings
            else None
        )

        rendered_slots: list[dict[str, object]] = []
        for index, requested in enumerate(requested_slots):
            meal_type = requested["meal_type"]
            inventory_name = self._inventory_name(priority_items, index)
            title = self._title(meal_type, inventory_name, recent_titles, index)
            current_title = str(requested.get("current_title") or "").strip().lower()
            if current_title and title.lower() == current_title:
                title = f"{title} Refresh"
            uses_on_hand = [inventory_name] if inventory_name else []
            reason_codes = ["FITS_DIETARY_RULES"]
            explanations = [
                {
                    "code": "FITS_DIETARY_RULES",
                    "message": "Builds from current household context without changing authoritative plan state.",
                    "source_refs": [f"household:{grounding['household_id']}"],
                }
            ]

            if uses_on_hand:
                reason_codes.insert(0, "USES_ON_HAND")
                explanations.insert(
                    0,
                    {
                        "code": "USES_ON_HAND",
                        "message": f"Uses {inventory_name} already available in the household inventory.",
                        "source_refs": [f"inventory:{inventory_name.lower().replace(' ', '-')}"],
                    },
                )
            if self._is_expiring(priority_items, inventory_name):
                if "USES_EXPIRING_ITEM" not in reason_codes:
                    reason_codes.insert(1 if uses_on_hand else 0, "USES_EXPIRING_ITEM")
                    explanations.append(
                        {
                            "code": "USES_EXPIRING_ITEM",
                            "message": f"Prioritizes {inventory_name} because it is in the highest expiry-pressure bucket.",
                            "source_refs": [f"inventory:{inventory_name.lower().replace(' ', '-')}"],
                        }
                    )
            if meal_type == "dinner":
                reason_codes.append("AVOIDS_RECENT_REPEAT")
                explanations.append(
                    {
                        "code": "AVOIDS_RECENT_REPEAT",
                        "message": "Keeps dinner rotation from leaning too heavily on recent confirmed meals.",
                        "source_refs": ["recent_meals"],
                    }
                )
            else:
                reason_codes.append("MATCHES_PREFERENCE")
                explanations.append(
                    {
                        "code": "MATCHES_PREFERENCE",
                        "message": f"Fits the household's usual {meal_type} rhythm with an editable suggestion.",
                        "source_refs": ["household_summary"],
                    }
                )

            rendered_slots.append(
                {
                    "slot_key": requested["slot_key"],
                    "meal_title": title,
                    "summary": f"{title} keeps the slot editable while using current household context.",
                    "uses_on_hand": uses_on_hand,
                    "missing_key_ingredients": ["fresh herbs"] if uses_on_hand else ["seasonal produce"],
                    "reason_codes": reason_codes[:3],
                    "explanations": explanations[:3],
                    "grocery_impact_hint": "Mostly pantry-ready with one optional fresh add-on.",
                }
            )

        return {
            "fallback_mode": "none",
            "warnings": warnings,
            "data_completeness_note": data_note,
            "slots": rendered_slots,
        }

    def _inventory_name(self, priority_items: list[dict[str, object]], index: int) -> str | None:
        if not priority_items:
            return None
        item = priority_items[index % len(priority_items)]
        return str(item["name"])

    def _is_expiring(self, priority_items: list[dict[str, object]], inventory_name: str | None) -> bool:
        if inventory_name is None:
            return False
        for item in priority_items:
            if item["name"] == inventory_name:
                return item["expiry_bucket"] in {"use_now", "use_soon"}
        return False

    def _title(self, meal_type: str, inventory_name: str | None, recent_titles: set[str], index: int) -> str:
        templates = self._MEAL_BY_TYPE.get(meal_type, ("Meal Plan",))
        suffix = templates[index % len(templates)]
        prefix = inventory_name or meal_type.title()
        title = f"{prefix.title()} {suffix}"
        if title.lower() in recent_titles:
            return f"{title} Remix"
        return title


@dataclass(frozen=True)
class CuratedMealTemplate:
    meal_type: str
    title: str
    summary: str
    uses_on_hand: tuple[str, ...]
    missing_key_ingredients: tuple[str, ...]


DEFAULT_CURATED_FALLBACKS: tuple[CuratedMealTemplate, ...] = (
    CuratedMealTemplate(
        meal_type="breakfast",
        title="Pantry Oatmeal Bowl",
        summary="A dependable breakfast fallback using shelf-stable oats and fruit toppings.",
        uses_on_hand=("oats",),
        missing_key_ingredients=("fruit topping",),
    ),
    CuratedMealTemplate(
        meal_type="lunch",
        title="Flexible Sandwich Plate",
        summary="A configurable lunch fallback that works with pantry staples and simple add-ons.",
        uses_on_hand=("bread",),
        missing_key_ingredients=("protein filling",),
    ),
    CuratedMealTemplate(
        meal_type="dinner",
        title="Sheet Pan Sausage and Vegetables",
        summary="A simple fallback dinner built for common pantry and freezer ingredients.",
        uses_on_hand=("root vegetables",),
        missing_key_ingredients=("sausages",),
    ),
)


class GenerationWorkerError(Exception):
    pass


class GenerationWorker:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        provider: AIGenerationProvider | None = None,
        curated_fallbacks: Iterable[CuratedMealTemplate] | None = None,
        random_seed: int = 7,
    ) -> None:
        self._session_factory = session_factory
        self._provider = provider or DeterministicGenerationProvider()
        self._curated_fallbacks = tuple(curated_fallbacks or DEFAULT_CURATED_FALLBACKS)
        self._random = random.Random(random_seed)

    def process_request(self, request_id: str) -> None:
        with self._session_factory() as session:
            request = session.get(AISuggestionRequest, request_id)
            if request is None or request.status not in ACTIVE_REQUEST_STATUSES:
                return

            correlation_id = request.id
            self._log_worker_lifecycle(
                action="process_request",
                outcome="started",
                request=request,
                correlation_id=correlation_id,
            )

            try:
                request.status = AISuggestionStatus.generating.value
                request.completed_at = None

                plan = session.get(MealPlan, request.meal_plan_id) if request.meal_plan_id else None
                slot = session.get(MealPlanSlot, request.meal_plan_slot_id) if request.meal_plan_slot_id else None
                if slot is not None:
                    slot.regen_status = PlanSlotRegenStatus.regenerating.value
                    slot.updated_at = _utcnow()
                session.flush()

                grounding = self._build_grounding(session, request, plan=plan, target_slot=slot)
                request.grounding_hash = grounding["grounding_hash"]
                self._apply_request_versions(request)

                reused = self._reuse_equivalent_result(session, request, target_slot=slot)
                if reused is not None:
                    request.status = reused
                    request.completed_at = _utcnow()
                    session.commit()
                    self._log_worker_lifecycle(
                        action="process_request",
                        outcome="reused",
                        request=request,
                        correlation_id=correlation_id,
                    )
                    return

                validated, status = self._generate_validated_result(request=request, grounding=grounding)
                result = self._persist_result(
                    session,
                    request=request,
                    validated=validated,
                    plan=plan,
                )

                if slot is not None:
                    self._apply_regenerated_slot(
                        session,
                        request=request,
                        result=result,
                        validated=validated,
                        target_slot=slot,
                    )

                request.status = status
                request.completed_at = _utcnow()
                session.commit()
                self._log_worker_lifecycle(
                    action="process_request",
                    outcome=status,
                    request=request,
                    correlation_id=correlation_id,
                )
            except Exception:
                session.rollback()
                failed_request = session.get(AISuggestionRequest, request_id)
                if failed_request is None:
                    logger.exception(
                        "planner worker request missing after failure",
                        extra={"worker_correlation_id": correlation_id, "worker_request_id": request_id},
                    )
                    return
                failed_request.status = AISuggestionStatus.failed.value
                failed_request.completed_at = _utcnow()
                failed_slot = (
                    session.get(MealPlanSlot, failed_request.meal_plan_slot_id)
                    if failed_request.meal_plan_slot_id
                    else None
                )
                if failed_slot is not None:
                    failed_slot.regen_status = PlanSlotRegenStatus.regen_failed.value
                    failed_slot.pending_regen_request_id = None
                    failed_slot.updated_at = _utcnow()
                session.commit()
                logger.exception(
                    "planner worker request failed",
                    extra={
                        "worker_action": "process_request",
                        "worker_outcome": "failed",
                        "worker_correlation_id": correlation_id,
                        "worker_request_id": failed_request.id,
                        "worker_household_id": failed_request.household_id,
                        "worker_plan_id": failed_request.meal_plan_id,
                        "worker_slot_id": failed_request.meal_plan_slot_id,
                        "worker_prompt_family": failed_request.prompt_family,
                        "worker_status": failed_request.status,
                    },
                )

    def process_available_requests(self, *, limit: int | None = None) -> int:
        processed = 0
        with self._session_factory() as session:
            stmt = (
                select(AISuggestionRequest.id)
                .where(AISuggestionRequest.status.in_([AISuggestionStatus.queued.value, AISuggestionStatus.pending.value]))
                .order_by(AISuggestionRequest.created_at.asc(), AISuggestionRequest.id.asc())
            )
            if limit is not None:
                stmt = stmt.limit(limit)
            request_ids = [row for row in session.scalars(stmt).all()]
        for request_id in request_ids:
            self.process_request(request_id)
            processed += 1
        return processed

    def _log_worker_lifecycle(
        self,
        *,
        action: str,
        outcome: str,
        request: AISuggestionRequest,
        correlation_id: str,
    ) -> None:
        logger.info(
            "planner worker %s",
            action,
            extra={
                "worker_action": action,
                "worker_outcome": outcome,
                "worker_correlation_id": correlation_id,
                "worker_request_id": request.id,
                "worker_household_id": request.household_id,
                "worker_plan_id": request.meal_plan_id,
                "worker_slot_id": request.meal_plan_slot_id,
                "worker_prompt_family": request.prompt_family,
                "worker_status": request.status,
            },
        )

    def build_grounding_snapshot(
        self,
        session: Session,
        request: AISuggestionRequest,
        *,
        plan: MealPlan | None,
        target_slot: MealPlanSlot | None,
    ) -> dict[str, object]:
        return self._build_grounding(session, request, plan=plan, target_slot=target_slot)

    def compute_grounding_hash(
        self,
        session: Session,
        request: AISuggestionRequest,
        *,
        plan: MealPlan | None,
        target_slot: MealPlanSlot | None,
    ) -> str:
        grounding = self.build_grounding_snapshot(
            session,
            request,
            plan=plan,
            target_slot=target_slot,
        )
        return str(grounding["grounding_hash"])

    def _build_grounding(
        self,
        session: Session,
        request: AISuggestionRequest,
        *,
        plan: MealPlan | None,
        target_slot: MealPlanSlot | None,
    ) -> dict[str, object]:
        household = session.get(Household, request.household_id)
        inventory_items = session.scalars(
            select(InventoryItem)
            .where(InventoryItem.household_id == request.household_id)
            .where(InventoryItem.is_active.is_(True))
            .order_by(InventoryItem.updated_at.desc(), InventoryItem.name.asc())
        ).all()
        confirmed_meal_plans = session.scalars(
            select(MealPlan)
            .where(MealPlan.household_id == request.household_id)
            .where(MealPlan.status == "confirmed")
            .where(MealPlan.period_end < request.plan_period_start)
            .order_by(MealPlan.confirmed_at.desc(), MealPlan.updated_at.desc())
        ).all()

        recent_meals: list[str] = []
        for prior_plan in confirmed_meal_plans[:2]:
            for prior_slot in sorted(prior_plan.slots, key=lambda slot: (slot.day_of_week, slot.meal_type)):
                if prior_slot.meal_title:
                    recent_meals.append(prior_slot.meal_title)

        requested_slots = self._requested_slots(request, plan=plan, target_slot=target_slot)
        inventory_priority_items = self._inventory_priority_items(inventory_items, plan_period_start=request.plan_period_start)
        locked_slots = self._locked_slots(plan=plan, target_slot=target_slot)
        context_warnings: list[str] = []
        if not inventory_priority_items:
            context_warnings.append("inventory_sparse")
        if not recent_meals:
            context_warnings.append("recent_meals_sparse")

        grounding = {
            "household_id": request.household_id,
            "target_slot_id": request.target_slot_id,
            "plan_period_start": request.plan_period_start.isoformat(),
            "plan_period_end": request.plan_period_end.isoformat(),
            "hard_constraints": {
                "advisory_only": True,
                "locked_slot_keys": [slot_key for slot_key in locked_slots],
                "slot_scope": [slot.slot_key for slot in requested_slots],
            },
            "soft_preferences": [
                "use_on_hand_first",
                "surface_expiry_pressure",
                "avoid_recent_repetition_when_possible",
            ],
            "inventory_priority_items": inventory_priority_items,
            "equipment_constraints": [],
            "leftover_candidates": [],
            "recent_meals": recent_meals[:10],
            "slot_requirements": [
                {
                    "slot_key": slot.slot_key,
                    "day_of_week": slot.day_of_week,
                    "meal_type": slot.meal_type,
                    "current_title": target_slot.meal_title if target_slot is not None and slot.slot_key == target_slot.slot_key else None,
                }
                for slot in requested_slots
            ],
            "household_summary": {
                "household_name": household.name if household is not None else "Household",
                "inventory_item_count": len(inventory_priority_items),
                "recent_meal_count": len(recent_meals),
            },
            "context_warnings": context_warnings,
        }
        grounding["grounding_hash"] = hashlib.sha256(_json_dump(grounding).encode("utf-8")).hexdigest()
        grounding["request_id"] = request.id
        return grounding

    def _requested_slots(
        self,
        request: AISuggestionRequest,
        *,
        plan: MealPlan | None,
        target_slot: MealPlanSlot | None,
    ) -> list[RequestedSlot]:
        if target_slot is not None:
            return [
                RequestedSlot(
                    slot_key=target_slot.slot_key,
                    day_of_week=target_slot.day_of_week,
                    meal_type=target_slot.meal_type,
                )
            ]

        requested: list[RequestedSlot] = []
        for day_of_week in range(7):
            for meal_type in MEAL_TYPES:
                requested.append(
                    RequestedSlot(
                        slot_key=f"{day_of_week}:{meal_type}",
                        day_of_week=day_of_week,
                        meal_type=meal_type,
                    )
                )
        if plan is not None:
            plan_slot_map = {slot.slot_key: slot for slot in plan.slots}
            for key, slot in plan_slot_map.items():
                if slot.is_user_locked:
                    requested = [candidate for candidate in requested if candidate.slot_key != key]
        return requested

    def _inventory_priority_items(
        self,
        inventory_items: list[InventoryItem],
        *,
        plan_period_start: date,
    ) -> list[dict[str, object]]:
        prioritized: list[dict[str, object]] = []
        for item in inventory_items:
            expiry_date = item.expiry_date or item.estimated_expiry_date
            bucket = "stable"
            if expiry_date is not None:
                delta_days = (expiry_date - plan_period_start).days
                if delta_days <= 1:
                    bucket = "use_now"
                elif delta_days <= 4:
                    bucket = "use_soon"
            prioritized.append(
                {
                    "name": item.name,
                    "storage_location": item.storage_location,
                    "quantity": str(item.quantity_on_hand),
                    "unit": item.primary_unit,
                    "expiry_bucket": bucket,
                    "inventory_version": item.version,
                }
            )
        priority_order = {"use_now": 0, "use_soon": 1, "stable": 2}
        return sorted(prioritized, key=lambda item: (priority_order[item["expiry_bucket"]], item["name"].lower()))

    def _locked_slots(self, *, plan: MealPlan | None, target_slot: MealPlanSlot | None) -> list[str]:
        if plan is None:
            return []
        locked: list[str] = []
        for slot in plan.slots:
            if target_slot is not None and slot.id == target_slot.id:
                continue
            if slot.is_user_locked or slot.slot_origin in {SlotOrigin.user_edited.value, SlotOrigin.manually_added.value}:
                locked.append(slot.slot_key)
        return sorted(set(locked))

    def _apply_request_versions(self, request: AISuggestionRequest) -> None:
        if request.target_slot_id is None:
            request.prompt_family = PRIMARY_PROMPT_FAMILY
        else:
            request.prompt_family = REGEN_PROMPT_FAMILY
        request.prompt_version = PROMPT_VERSION
        request.policy_version = POLICY_VERSION
        request.context_contract_version = CONTEXT_CONTRACT_VERSION
        request.result_contract_version = RESULT_CONTRACT_VERSION

    def _reuse_equivalent_result(
        self,
        session: Session,
        request: AISuggestionRequest,
        *,
        target_slot: MealPlanSlot | None,
    ) -> str | None:
        stmt = (
            select(AISuggestionRequest)
            .where(AISuggestionRequest.id != request.id)
            .where(AISuggestionRequest.household_id == request.household_id)
            .where(AISuggestionRequest.grounding_hash == request.grounding_hash)
            .where(AISuggestionRequest.status.in_(TERMINAL_REUSE_STATUSES))
            .order_by(AISuggestionRequest.completed_at.desc(), AISuggestionRequest.created_at.desc())
        )
        if request.target_slot_id is None:
            stmt = stmt.where(AISuggestionRequest.target_slot_id.is_(None))
        else:
            stmt = stmt.where(AISuggestionRequest.target_slot_id == request.target_slot_id)

        prior_request = session.scalar(stmt)
        if prior_request is None or prior_request.completed_at is None:
            return None
        if prior_request.completed_at < (_utcnow() - timedelta(hours=12)):
            return None

        prior_result = session.scalar(
            select(AISuggestionResult).where(AISuggestionResult.request_id == prior_request.id)
        )
        if prior_result is None or prior_result.stale_flag:
            return None

        cloned = AISuggestionResult(
            request_id=request.id,
            meal_plan_id=request.meal_plan_id,
            fallback_mode=prior_result.fallback_mode,
            stale_flag=prior_result.stale_flag,
            result_contract_version=prior_result.result_contract_version,
            created_at=_utcnow(),
        )
        session.add(cloned)
        session.flush()
        cloned_slots: list[AISuggestionSlot] = []
        for prior_slot in sorted(prior_result.slots, key=lambda slot: (slot.day_of_week, slot.meal_type)):
            cloned_slot = AISuggestionSlot(
                result_id=cloned.id,
                slot_key=prior_slot.slot_key,
                day_of_week=prior_slot.day_of_week,
                meal_type=prior_slot.meal_type,
                meal_title=prior_slot.meal_title,
                meal_summary=prior_slot.meal_summary,
                reason_codes=prior_slot.reason_codes,
                explanation_entries=prior_slot.explanation_entries,
                uses_on_hand=prior_slot.uses_on_hand,
                missing_hints=prior_slot.missing_hints,
                is_fallback=prior_slot.is_fallback,
                created_at=_utcnow(),
            )
            session.add(cloned_slot)
            cloned_slots.append(cloned_slot)
        session.flush()

        if target_slot is not None:
            if cloned_slots:
                self._apply_slot_from_suggestion(
                    target_slot=target_slot,
                    request=request,
                    result=cloned,
                    suggestion_slot=cloned_slots[0],
                )
            else:
                target_slot.regen_status = PlanSlotRegenStatus.regen_failed.value
                target_slot.pending_regen_request_id = None
                target_slot.updated_at = _utcnow()

        return (
            AISuggestionStatus.completed_with_fallback.value
            if cloned.fallback_mode != "none"
            else AISuggestionStatus.completed.value
        )

    def _generate_validated_result(
        self,
        *,
        request: AISuggestionRequest,
        grounding: dict[str, object],
    ) -> tuple[SuggestionResultContract, str]:
        prompt_bundle = self._build_prompt_bundle(request=request, grounding=grounding)
        try:
            provider_payload = self._provider.generate(prompt_bundle=prompt_bundle, grounding=grounding)
            validated = self._validate_result_payload(
                request=request,
                payload=provider_payload,
                requested_slots=grounding["slot_requirements"],
            )
            status = (
                AISuggestionStatus.completed_with_fallback.value
                if validated.fallback_mode != "none"
                else AISuggestionStatus.completed.value
            )
            return validated, status
        except (ValidationError, ValueError, RuntimeError):
            fallback = self._build_fallback_result(grounding=grounding, request=request)
            return fallback, AISuggestionStatus.completed_with_fallback.value

    def _build_prompt_bundle(
        self,
        *,
        request: AISuggestionRequest,
        grounding: dict[str, object],
    ) -> dict[str, str]:
        slot_scope = ", ".join(slot["slot_key"] for slot in grounding["slot_requirements"])
        return {
            "system": (
                "You are generating advisory-only meal suggestions. Do not mutate authoritative state, "
                "honor hard restrictions, and admit sparse context plainly."
            ),
            "task": (
                f"Generate editable meal suggestions for household {request.household_id} "
                f"across slot scope [{slot_scope}] while using on-hand and expiring items where practical."
            ),
            "context": _json_dump(grounding),
            "result_schema": (
                "Return JSON with fallback_mode, warnings, data_completeness_note, and slots[]. "
                "Each slot must include slot_key, meal_title, summary, uses_on_hand, "
                "missing_key_ingredients, reason_codes, explanations, and grocery_impact_hint."
            ),
        }

    def _validate_result_payload(
        self,
        *,
        request: AISuggestionRequest,
        payload: dict[str, object],
        requested_slots: list[dict[str, object]],
    ) -> SuggestionResultContract:
        validated = SuggestionResultContract.model_validate(payload)
        requested_keys = {slot["slot_key"] for slot in requested_slots}
        returned_keys = {slot.slot_key for slot in validated.slots}
        if request.target_slot_id is None and returned_keys != requested_keys:
            raise ValueError("Weekly generation must return all requested slots.")
        if request.target_slot_id is not None and len(validated.slots) != 1:
            raise ValueError("Slot regeneration must return exactly one slot.")
        if returned_keys and not returned_keys <= requested_keys:
            raise ValueError("Provider returned an unexpected slot key.")
        return validated

    def _build_fallback_result(
        self,
        *,
        grounding: dict[str, object],
        request: AISuggestionRequest,
    ) -> SuggestionResultContract:
        requested_slots = grounding["slot_requirements"]
        curated_slots: list[SlotSuggestionContract] = []

        for requested_slot in requested_slots:
            template = self._pick_curated_template(requested_slot["meal_type"])
            if template is None:
                continue
            curated_slots.append(
                SlotSuggestionContract(
                    slot_key=requested_slot["slot_key"],
                    meal_title=template.title,
                    summary=template.summary,
                    uses_on_hand=list(template.uses_on_hand),
                    missing_key_ingredients=list(template.missing_key_ingredients),
                    reason_codes=["LOW_CONTEXT_FALLBACK", "FITS_DIETARY_RULES"],
                    explanations=[
                        SourceExplanation(
                            code="LOW_CONTEXT_FALLBACK",
                            message="Used a deterministic fallback because the AI provider path did not return a valid result.",
                            source_refs=["fallback_catalog"],
                        ),
                        SourceExplanation(
                            code="FITS_DIETARY_RULES",
                            message="Fallback suggestions still respect the current hard constraint posture.",
                            source_refs=[f"household:{request.household_id}"],
                        ),
                    ],
                    grocery_impact_hint="Review pantry staples and add missing ingredients if needed.",
                )
            )

        if curated_slots and (
            request.target_slot_id is None or len(curated_slots) == len(requested_slots)
        ):
            return SuggestionResultContract(
                fallback_mode="curated_fallback",
                warnings=["provider_unavailable"],
                data_completeness_note="A deterministic fallback was used because the AI provider path was unavailable or invalid.",
                slots=curated_slots,
            )

        manual_guidance_slots = [
            SlotSuggestionContract(
                slot_key=requested_slot["slot_key"],
                meal_title="Choose a meal manually",
                summary="AI guidance was unavailable for this slot. Keep the current choice or plan manually.",
                uses_on_hand=[],
                missing_key_ingredients=[],
                reason_codes=["LOW_CONTEXT_FALLBACK"],
                explanations=[
                    SourceExplanation(
                        code="LOW_CONTEXT_FALLBACK",
                        message="Manual planning guidance is shown because no safe curated fallback was available.",
                        source_refs=["fallback_catalog"],
                    )
                ],
                grocery_impact_hint="No automatic grocery hint is available for this slot.",
            )
            for requested_slot in requested_slots
        ]
        return SuggestionResultContract(
            fallback_mode="manual_guidance",
            warnings=["provider_unavailable", "manual_planning_required"],
            data_completeness_note="Manual planning guidance is shown because the AI path could not produce a safe structured suggestion.",
            slots=manual_guidance_slots,
        )

    def _pick_curated_template(self, meal_type: str) -> CuratedMealTemplate | None:
        candidates = [template for template in self._curated_fallbacks if template.meal_type == meal_type]
        if not candidates:
            return None
        return candidates[self._random.randrange(len(candidates))]

    def _persist_result(
        self,
        session: Session,
        *,
        request: AISuggestionRequest,
        validated: SuggestionResultContract,
        plan: MealPlan | None,
    ) -> AISuggestionResult:
        result = AISuggestionResult(
            request_id=request.id,
            meal_plan_id=plan.id if request.target_slot_id is not None and plan is not None else None,
            fallback_mode=validated.fallback_mode,
            stale_flag=False,
            result_contract_version=request.result_contract_version,
            created_at=_utcnow(),
        )
        session.add(result)
        session.flush()

        for requested_slot in validated.slots:
            slot_key = requested_slot.slot_key
            day_of_week, meal_type = self._slot_key_parts(slot_key)
            session.add(
                AISuggestionSlot(
                    result_id=result.id,
                    slot_key=slot_key,
                    day_of_week=day_of_week,
                    meal_type=meal_type,
                    meal_title=requested_slot.meal_title,
                    meal_summary=requested_slot.summary,
                    reason_codes=_dump_list(requested_slot.reason_codes),
                    explanation_entries=_dump_list(
                        explanation.message for explanation in requested_slot.explanations
                    ),
                    uses_on_hand=_dump_list(requested_slot.uses_on_hand),
                    missing_hints=_dump_list(requested_slot.missing_key_ingredients),
                    is_fallback=validated.fallback_mode != "none",
                    created_at=_utcnow(),
                )
            )
        session.flush()
        return result

    def _apply_regenerated_slot(
        self,
        session: Session,
        *,
        request: AISuggestionRequest,
        result: AISuggestionResult,
        validated: SuggestionResultContract,
        target_slot: MealPlanSlot,
    ) -> None:
        suggestion_slot = session.scalar(
            select(AISuggestionSlot)
            .where(AISuggestionSlot.result_id == result.id)
            .where(AISuggestionSlot.slot_key == target_slot.slot_key)
        )
        if suggestion_slot is None or validated.fallback_mode == "manual_guidance":
            target_slot.regen_status = PlanSlotRegenStatus.regen_failed.value
            target_slot.pending_regen_request_id = None
            target_slot.updated_at = _utcnow()
            return

        self._apply_slot_from_suggestion(
            target_slot=target_slot,
            request=request,
            result=result,
            suggestion_slot=suggestion_slot,
        )

    def _apply_slot_from_suggestion(
        self,
        *,
        target_slot: MealPlanSlot,
        request: AISuggestionRequest,
        result: AISuggestionResult,
        suggestion_slot: AISuggestionSlot,
    ) -> None:
        target_slot.meal_title = suggestion_slot.meal_title
        target_slot.meal_summary = suggestion_slot.meal_summary
        target_slot.slot_origin = SlotOrigin.ai_suggested.value
        target_slot.ai_suggestion_request_id = request.id
        target_slot.ai_suggestion_result_id = result.id
        target_slot.reason_codes = suggestion_slot.reason_codes
        target_slot.explanation_entries = suggestion_slot.explanation_entries
        target_slot.prompt_family = request.prompt_family
        target_slot.prompt_version = request.prompt_version
        target_slot.fallback_mode = result.fallback_mode
        target_slot.regen_status = PlanSlotRegenStatus.idle.value
        target_slot.pending_regen_request_id = None
        target_slot.updated_at = _utcnow()

    def _slot_key_parts(self, slot_key: str) -> tuple[int, str]:
        day_text, meal_type = slot_key.split(":", 1)
        if meal_type not in SUPPORTED_MEAL_TYPES:
            raise GenerationWorkerError(f"Unsupported meal type in slot key: {slot_key}")
        return int(day_text), meal_type

