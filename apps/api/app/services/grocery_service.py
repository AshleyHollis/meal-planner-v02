from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import app.models  # noqa: F401
from sqlalchemy import URL, Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.grocery import (
    GroceryList,
    GroceryListItem,
    GrocerySyncConflict,
    GroceryListVersion,
    GroceryMutationReceipt,
)
from app.models.household import Household
from app.models.inventory import InventoryItem
from app.models.meal_plan import MealPlan, MealPlanSlot
from app.models.planner_event import PlannerEvent
from app.schemas.enums import (
    GroceryItemOrigin,
    GroceryListStatus,
    MealPlanStatus,
    SyncAggregateType,
    SyncMutationState,
    SyncOutcome,
    SyncResolutionAction,
    SyncResolutionStatus,
)
from app.schemas.grocery import (
    GroceryIncompleteSlotWarningRead,
    GroceryListConfirmCommand,
    GroceryListDeriveCommand,
    GroceryListItemAdHocCreate,
    GroceryListItemRead,
    GroceryListQuantityAdjustCommand,
    GroceryListRead,
    GroceryListRemoveLineCommand,
    GroceryMealSourceRead,
    GroceryMutationResult,
    QueueableSyncMutation,
    SyncAggregateRef,
    SyncConflictDetailRead,
    SyncConflictKeepMineCommand,
    SyncConflictSummaryRead,
    SyncConflictUseServerCommand,
    SyncMutationOutcomeRead,
)
from app.schemas.planner import PlanConfirmedEvent
from app.services.local_db_compat import resolve_local_db_path

logger = logging.getLogger(__name__)
_QUANTITY_SCALE = Decimal("0.0001")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_decimal(value: Decimal | str | float | int) -> Decimal:
    return Decimal(str(value)).quantize(_QUANTITY_SCALE)


def _period_end(period_start: date) -> date:
    return period_start + timedelta(days=6)


def _normalized_name(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _period_reference(period_start: date, period_end: date) -> str:
    return f"{period_start.isoformat()}/{period_end.isoformat()}"


class GroceryDomainError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int = 422) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class MealIngredient:
    ingredient_name: str
    quantity: Decimal
    unit: str
    ingredient_ref_id: str | None = None


@dataclass
class RawNeed:
    ingredient_name: str
    ingredient_ref_id: str | None
    required_quantity: Decimal
    unit: str
    meal_slot_id: str
    meal_name: str | None
    offset_quantity: Decimal = Decimal("0")
    offset_inventory_item_id: str | None = None
    offset_inventory_item_version: int | None = None

    @property
    def shopping_quantity(self) -> Decimal:
        remaining = self.required_quantity - self.offset_quantity
        if remaining < 0:
            return Decimal("0.0000")
        return remaining.quantize(_QUANTITY_SCALE)


@dataclass(frozen=True)
class SyncMutationContext:
    grocery_list: GroceryList
    current_version: GroceryListVersion
    current_item: GroceryListItem | None
    aggregate_type: SyncAggregateType
    aggregate_id: str
    provisional_aggregate_id: str | None = None


@dataclass(frozen=True)
class SyncReplayDecision:
    outcome: SyncOutcome
    summary: str | None = None
    auto_merge_reason: str | None = None


class MealIngredientCatalog:
    """
    Temporary backend-owned meal ingredient seam for grocery derivation.

    The repo does not yet have a durable recipe/meal-definition store. Grocery
    derivation therefore resolves ingredients from explicit `meal_reference_id`
    keys when present, or from a deterministic title slug fallback that tests
    can target without inventing fuzzy matching.
    """

    def __init__(self, catalog: dict[str, list[MealIngredient]] | None = None) -> None:
        self._catalog = catalog or self._default_catalog()

    def get_ingredients(self, slot: MealPlanSlot) -> list[MealIngredient] | None:
        keys = [slot.meal_reference_id, self._title_key(slot.meal_title)]
        for key in keys:
            if not key:
                continue
            ingredients = self._catalog.get(key)
            if ingredients is not None:
                return ingredients
        return None

    @staticmethod
    def _title_key(title: str | None) -> str | None:
        if title is None:
            return None
        slug = "-".join(part for part in _normalized_name(title).replace("/", " ").split(" ") if part)
        return slug or None

    @staticmethod
    def _default_catalog() -> dict[str, list[MealIngredient]]:
        return {
            "meal-pasta-bake": [
                MealIngredient("Pasta", Decimal("500"), "grams", ingredient_ref_id="ingredient-pasta"),
                MealIngredient("Tomatoes", Decimal("4"), "count", ingredient_ref_id="ingredient-tomatoes"),
                MealIngredient("Olive Oil", Decimal("100"), "milliliters", ingredient_ref_id="ingredient-olive-oil"),
            ],
            "meal-pesto-pasta": [
                MealIngredient("Pasta", Decimal("300"), "grams", ingredient_ref_id="ingredient-pasta"),
                MealIngredient("Basil", Decimal("1"), "bunch", ingredient_ref_id="ingredient-basil"),
                MealIngredient("Olive Oil", Decimal("50"), "milliliters", ingredient_ref_id="ingredient-olive-oil"),
            ],
            "meal-salad-night": [
                MealIngredient("Lettuce", Decimal("1"), "head", ingredient_ref_id="ingredient-lettuce"),
                MealIngredient("Tomatoes", Decimal("2"), "count", ingredient_ref_id="ingredient-tomatoes"),
                MealIngredient("Olive Oil", Decimal("30"), "milliliters", ingredient_ref_id="ingredient-olive-oil"),
            ],
            "meal-taco-night": [
                MealIngredient("Tortillas", Decimal("8"), "count", ingredient_ref_id="ingredient-tortillas"),
                MealIngredient("Salsa", Decimal("1"), "jar", ingredient_ref_id="ingredient-salsa"),
            ],
        }


class GroceryService:
    def __init__(
        self,
        database_url: str | URL | None = None,
        *,
        ingredient_catalog: MealIngredientCatalog | None = None,
    ) -> None:
        self._engine = self._create_engine(database_url)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._ingredient_catalog = ingredient_catalog or MealIngredientCatalog()

    @classmethod
    def for_default_app(cls) -> "GroceryService":
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
            if str(database_url).startswith("sqlite"):
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine = create_engine(database_url, **engine_kwargs)

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    def dispose(self) -> None:
        self._engine.dispose()

    def derive_list(
        self,
        household_id: str,
        *,
        actor_id: str,
        command: GroceryListDeriveCommand,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        mutation_kind="derive",
                        outcome="duplicate",
                        household_id=household_id,
                        actor_id=actor_id,
                        grocery_list_id=existing.grocery_list.id,
                        client_mutation_id=command.client_mutation_id,
                    )
                    return existing

                plan = self._get_confirmed_plan_for_period(
                    session,
                    household_id=household_id,
                    period_start=command.plan_period_start,
                )
                if plan is None:
                    raise GroceryDomainError(
                        code="confirmed_plan_not_found",
                        message="No confirmed meal plan exists for that period.",
                        status_code=409,
                    )

                list_model = self._choose_list_for_derivation(session, household_id, plan)
                result = self._derive_into_list(
                    session,
                    household_id=household_id,
                    actor_id=actor_id,
                    plan=plan,
                    grocery_list=list_model,
                    mutation_kind="derive",
                    client_mutation_id=command.client_mutation_id,
                )
                self._store_receipt(
                    session,
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_kind="derive",
                    result=result,
                    accepted_at=_utcnow(),
                )
                return result

    def rederive_list(
        self,
        household_id: str,
        grocery_list_id: str,
        *,
        actor_id: str,
        command: GroceryListDeriveCommand,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        mutation_kind="rederive",
                        outcome="duplicate",
                        household_id=household_id,
                        actor_id=actor_id,
                        grocery_list_id=existing.grocery_list.id,
                        client_mutation_id=command.client_mutation_id,
                    )
                    return existing

                target_list = self._get_list(session, household_id, grocery_list_id)
                if target_list is None:
                    raise GroceryDomainError(
                        code="grocery_list_not_found",
                        message="Grocery list not found.",
                        status_code=404,
                    )
                plan = self._list_plan(session, target_list)
                if plan is None:
                    raise GroceryDomainError(
                        code="confirmed_plan_not_found",
                        message="The grocery list is not linked to a confirmed plan.",
                        status_code=409,
                    )
                if command.plan_period_start != plan.period_start:
                    raise GroceryDomainError(
                        code="period_mismatch",
                        message="The requested derivation period does not match the list period.",
                        status_code=409,
                    )
                destination_list = (
                    self._create_grocery_list(session, household_id=household_id, meal_plan_id=plan.id)
                    if target_list.status
                    in {
                        GroceryListStatus.confirmed.value,
                        GroceryListStatus.trip_in_progress.value,
                        GroceryListStatus.trip_complete_pending_reconciliation.value,
                    }
                    else target_list
                )
                result = self._derive_into_list(
                    session,
                    household_id=household_id,
                    actor_id=actor_id,
                    plan=plan,
                    grocery_list=destination_list,
                    mutation_kind="rederive",
                    client_mutation_id=command.client_mutation_id,
                )
                self._store_receipt(
                    session,
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_kind="rederive",
                    result=result,
                    accepted_at=_utcnow(),
                )
                return result

    def get_current_list(self, household_id: str, period_start: date) -> GroceryListRead | None:
        with self._session_factory() as session:
            list_model = self._get_latest_list_for_period(session, household_id=household_id, period_start=period_start)
            if list_model is None:
                return None
            changed = self._refresh_stale_status(session, list_model)
            if changed:
                session.commit()
                session.refresh(list_model)
            return self._list_to_read(session, list_model)

    def get_list(self, household_id: str, grocery_list_id: str) -> GroceryListRead | None:
        with self._session_factory() as session:
            list_model = self._get_list(session, household_id, grocery_list_id)
            if list_model is None:
                return None
            changed = self._refresh_stale_status(session, list_model)
            if changed:
                session.commit()
                session.refresh(list_model)
            return self._list_to_read(session, list_model)

    def process_pending_plan_confirmed_events(self, household_id: str, *, actor_id: str | None = None) -> int:
        with self._session_factory() as session:
            with session.begin():
                events = self._pending_plan_confirmed_events(session, household_id)
                processed = 0
                for event_model in events:
                    payload = PlanConfirmedEvent.model_validate_json(event_model.payload)
                    self._apply_plan_confirmed_event(
                        session,
                        event_model=event_model,
                        payload=payload,
                        actor_id=actor_id or payload.actor_id,
                    )
                    processed += 1
                return processed

    def refresh_stale_drafts(
        self,
        household_id: str,
        *,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ) -> int:
        with self._session_factory() as session:
            with session.begin():
                refreshed = 0
                for grocery_list in self._draft_lists_for_household(session, household_id):
                    if self._refresh_stale_status(
                        session,
                        grocery_list,
                        actor_id=actor_id,
                        correlation_id=correlation_id,
                    ):
                        refreshed += 1
                if refreshed:
                    logger.info(
                        "grocery stale refresh accepted",
                        extra={
                            "grocery_action": "stale_refresh",
                            "grocery_outcome": "accepted",
                            "grocery_household_id": household_id,
                            "grocery_actor_id": actor_id,
                            "grocery_correlation_id": correlation_id,
                            "grocery_stale_list_count": refreshed,
                        },
                    )
                return refreshed

    def add_ad_hoc_item(
        self,
        household_id: str,
        grocery_list_id: str,
        *,
        actor_id: str,
        command: GroceryListItemAdHocCreate,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        mutation_kind="add_ad_hoc",
                        outcome="duplicate",
                        household_id=household_id,
                        actor_id=actor_id,
                        grocery_list_id=existing.grocery_list.id,
                        grocery_list_item_id=existing.item.id if existing.item is not None else None,
                        client_mutation_id=command.client_mutation_id,
                    )
                    return existing

                grocery_list = self._get_mutable_list(session, household_id, grocery_list_id)
                current_version = self._require_current_version(session, grocery_list)
                now = _utcnow()
                item = GroceryListItem(
                    stable_line_id=str(uuid.uuid4()),
                    grocery_list_id=grocery_list.id,
                    grocery_list_version_id=current_version.id,
                    ingredient_name=command.ingredient_name.strip(),
                    ingredient_ref_id=None,
                    required_quantity=command.shopping_quantity,
                    unit=command.unit.strip(),
                    offset_quantity=Decimal("0.0000"),
                    shopping_quantity=command.shopping_quantity,
                    origin=GroceryItemOrigin.ad_hoc.value,
                    meal_sources=None,
                    user_adjusted_quantity=None,
                    user_adjustment_note=None,
                    user_adjustment_flagged=False,
                    ad_hoc_note=command.ad_hoc_note,
                    active=True,
                    removed_at=None,
                    created_client_mutation_id=command.client_mutation_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(item)
                session.flush()
                grocery_list.updated_at = now
                result = GroceryMutationResult(
                    mutation_kind="add_ad_hoc",
                    grocery_list=self._list_to_read(session, grocery_list),
                    item=self._item_to_read(item),
                )
                self._store_receipt(
                    session,
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_kind="add_ad_hoc",
                    result=result,
                    accepted_at=now,
                )
                self._log_mutation(
                    mutation_kind="add_ad_hoc",
                    outcome="accepted",
                    household_id=household_id,
                    actor_id=actor_id,
                    grocery_list_id=grocery_list.id,
                    grocery_list_item_id=item.id,
                    client_mutation_id=command.client_mutation_id,
                )
                return result

    def adjust_line(
        self,
        household_id: str,
        grocery_list_id: str,
        grocery_list_item_id: str,
        *,
        actor_id: str,
        command: GroceryListQuantityAdjustCommand,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        mutation_kind="adjust_line",
                        outcome="duplicate",
                        household_id=household_id,
                        actor_id=actor_id,
                        grocery_list_id=existing.grocery_list.id,
                        grocery_list_item_id=existing.item.id if existing.item is not None else None,
                        client_mutation_id=command.client_mutation_id,
                    )
                    return existing

                grocery_list = self._get_mutable_list(session, household_id, grocery_list_id)
                item = self._get_current_line(session, grocery_list, grocery_list_item_id)
                if item is None:
                    raise GroceryDomainError(
                        code="grocery_line_not_found",
                        message="Grocery line not found.",
                        status_code=404,
                    )
                now = _utcnow()
                item.user_adjusted_quantity = command.user_adjusted_quantity
                item.user_adjustment_note = command.user_adjustment_note
                item.user_adjustment_flagged = command.user_adjusted_quantity != item.shopping_quantity
                item.updated_at = now
                grocery_list.updated_at = now
                result = GroceryMutationResult(
                    mutation_kind="adjust_line",
                    grocery_list=self._list_to_read(session, grocery_list),
                    item=self._item_to_read(item),
                )
                self._store_receipt(
                    session,
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_kind="adjust_line",
                    result=result,
                    accepted_at=now,
                )
                self._log_mutation(
                    mutation_kind="adjust_line",
                    outcome="accepted",
                    household_id=household_id,
                    actor_id=actor_id,
                    grocery_list_id=grocery_list.id,
                    grocery_list_item_id=item.id,
                    client_mutation_id=command.client_mutation_id,
                )
                return result

    def remove_line(
        self,
        household_id: str,
        grocery_list_id: str,
        grocery_list_item_id: str,
        *,
        actor_id: str,
        command: GroceryListRemoveLineCommand,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        mutation_kind="remove_line",
                        outcome="duplicate",
                        household_id=household_id,
                        actor_id=actor_id,
                        grocery_list_id=existing.grocery_list.id,
                        grocery_list_item_id=existing.item.id if existing.item is not None else None,
                        client_mutation_id=command.client_mutation_id,
                    )
                    return existing

                grocery_list = self._get_mutable_list(session, household_id, grocery_list_id)
                item = self._get_current_line(session, grocery_list, grocery_list_item_id)
                if item is None:
                    raise GroceryDomainError(
                        code="grocery_line_not_found",
                        message="Grocery line not found.",
                        status_code=404,
                    )
                now = _utcnow()
                item.active = False
                item.removed_at = now
                item.removed_client_mutation_id = command.client_mutation_id
                item.updated_at = now
                grocery_list.updated_at = now
                result = GroceryMutationResult(
                    mutation_kind="remove_line",
                    grocery_list=self._list_to_read(session, grocery_list),
                    item=self._item_to_read(item),
                )
                self._store_receipt(
                    session,
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_kind="remove_line",
                    result=result,
                    accepted_at=now,
                )
                self._log_mutation(
                    mutation_kind="remove_line",
                    outcome="accepted",
                    household_id=household_id,
                    actor_id=actor_id,
                    grocery_list_id=grocery_list.id,
                    grocery_list_item_id=item.id,
                    client_mutation_id=command.client_mutation_id,
                )
                return result

    def confirm_list(
        self,
        household_id: str,
        grocery_list_id: str,
        *,
        actor_id: str,
        command: GroceryListConfirmCommand,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        mutation_kind="confirm_list",
                        outcome="duplicate",
                        household_id=household_id,
                        actor_id=actor_id,
                        grocery_list_id=existing.grocery_list.id,
                        client_mutation_id=command.client_mutation_id,
                    )
                    return existing

                grocery_list = self._get_list(session, household_id, grocery_list_id)
                if grocery_list is None:
                    raise GroceryDomainError(
                        code="grocery_list_not_found",
                        message="Grocery list not found.",
                        status_code=404,
                    )
                if grocery_list.status in {
                    GroceryListStatus.trip_in_progress.value,
                    GroceryListStatus.trip_complete_pending_reconciliation.value,
                }:
                    raise GroceryDomainError(
                        code="grocery_list_not_confirmable",
                        message="The grocery list cannot be confirmed in its current state.",
                        status_code=409,
                    )
                now = _utcnow()
                grocery_list.status = GroceryListStatus.confirmed.value
                grocery_list.confirmed_at = now
                grocery_list.confirmation_client_mutation_id = command.client_mutation_id
                grocery_list.updated_at = now
                current_version = self._require_current_version(session, grocery_list)
                result = GroceryMutationResult(
                    mutation_kind="confirm_list",
                    grocery_list=self._list_to_read(session, grocery_list),
                    item=None,
                )
                self._store_receipt(
                    session,
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_kind="confirm_list",
                    result=result,
                    accepted_at=now,
                )
                self._log_confirmation(
                    household_id=household_id,
                    actor_id=actor_id,
                    grocery_list_id=grocery_list.id,
                    grocery_list_version_id=current_version.id,
                    client_mutation_id=command.client_mutation_id,
                    confirmed_at=now,
                )
                return result

    def upload_sync_mutations(
        self,
        household_id: str,
        *,
        actor_id: str,
        mutations: list[QueueableSyncMutation],
    ) -> list[SyncMutationOutcomeRead]:
        if not mutations:
            return []

        with self._session_factory() as session:
            with session.begin():
                outcomes: list[SyncMutationOutcomeRead] = []
                initial_server_versions: dict[str, int] = {}
                blocked_lists: set[str] = set()

                for mutation in mutations:
                    if existing_conflict := self._get_sync_conflict_by_local_mutation(
                        session, household_id, mutation.client_mutation_id
                    ):
                        self._log_mutation(
                            mutation_kind=f"sync_{existing_conflict.mutation_type}",
                            outcome=existing_conflict.outcome,
                            household_id=household_id,
                            actor_id=actor_id,
                            grocery_list_id=existing_conflict.grocery_list_id,
                            client_mutation_id=mutation.client_mutation_id,
                            aggregate_type=existing_conflict.aggregate_type,
                            aggregate_id=existing_conflict.aggregate_id,
                            aggregate_version=existing_conflict.current_server_version,
                            provisional_aggregate_id=mutation.provisional_aggregate_id,
                            conflict_id=existing_conflict.id,
                            base_server_version=existing_conflict.base_server_version,
                            current_server_version=existing_conflict.current_server_version,
                            summary=existing_conflict.summary,
                        )
                        blocked_lists.add(existing_conflict.grocery_list_id)
                        outcomes.append(self._sync_conflict_to_outcome(existing_conflict))
                        continue

                    if self._has_applied_receipt(session, household_id, mutation.client_mutation_id):
                        outcomes.append(
                            self._build_duplicate_sync_outcome(
                                session,
                                household_id,
                                actor_id,
                                mutation.client_mutation_id,
                                provisional_aggregate_id=mutation.provisional_aggregate_id,
                            )
                        )
                        continue

                    context = self._resolve_sync_mutation_context(session, household_id, mutation)
                    initial_server_versions.setdefault(
                        context.grocery_list.id,
                        context.current_version.version_number,
                    )

                    if context.grocery_list.id in blocked_lists:
                        conflict = self._create_sync_conflict(
                            session,
                            household_id=household_id,
                            grocery_list=context.grocery_list,
                            mutation=mutation,
                            context=context,
                            outcome=SyncOutcome.review_required_other_unsafe,
                            summary=(
                                "Automatic replay stopped because an earlier offline change for this grocery list "
                                "already needs review."
                            ),
                        )
                        outcomes.append(self._sync_conflict_to_outcome(conflict))
                        continue

                    if (
                        mutation.base_server_version is not None
                        and mutation.base_server_version > context.current_version.version_number
                    ):
                        raise GroceryDomainError(
                            code="sync_base_server_version_invalid",
                            message="The uploaded base server version is newer than the authoritative server state.",
                            status_code=409,
                        )

                    if (
                        mutation.base_server_version is not None
                        and mutation.base_server_version < initial_server_versions[context.grocery_list.id]
                    ):
                        decision = self._classify_stale_sync_mutation(
                            session,
                            mutation=mutation,
                            context=context,
                        )
                        if decision.outcome == SyncOutcome.auto_merged_non_overlapping:
                            outcomes.append(
                                self._apply_sync_mutation(
                                    session,
                                    household_id=household_id,
                                    actor_id=actor_id,
                                    mutation=mutation,
                                    context=context,
                                    outcome=decision.outcome,
                                    auto_merge_reason=decision.auto_merge_reason,
                                )
                            )
                            continue
                        conflict = self._create_sync_conflict(
                            session,
                            household_id=household_id,
                            grocery_list=context.grocery_list,
                            mutation=mutation,
                            context=context,
                            outcome=decision.outcome,
                            summary=decision.summary or self._stale_sync_summary_for_context(context),
                        )
                        blocked_lists.add(context.grocery_list.id)
                        outcomes.append(self._sync_conflict_to_outcome(conflict))
                        continue

                    outcome = self._apply_sync_mutation(
                        session,
                        household_id=household_id,
                        actor_id=actor_id,
                        mutation=mutation,
                        context=context,
                    )
                    outcomes.append(outcome)

                return outcomes

    def list_sync_conflicts(self, household_id: str) -> list[SyncConflictSummaryRead]:
        with self._session_factory() as session:
            with session.begin():
                stmt = (
                    select(GrocerySyncConflict)
                    .where(GrocerySyncConflict.household_id == household_id)
                    .order_by(GrocerySyncConflict.created_at.desc(), GrocerySyncConflict.id.desc())
                )
                conflicts = session.scalars(stmt).all()
                for conflict in conflicts:
                    self._refresh_sync_conflict_read_model(session, conflict)
                return [self._sync_conflict_to_summary(conflict) for conflict in conflicts]

    def get_sync_conflict(self, household_id: str, conflict_id: str) -> SyncConflictDetailRead | None:
        with self._session_factory() as session:
            with session.begin():
                conflict = self._get_sync_conflict(session, household_id, conflict_id)
                if conflict is None:
                    return None
                self._refresh_sync_conflict_read_model(session, conflict)
                return self._sync_conflict_to_detail(conflict)

    def resolve_sync_conflict_keep_mine(
        self,
        household_id: str,
        conflict_id: str,
        *,
        actor_id: str,
        command: SyncConflictKeepMineCommand,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    return self._resolution_result(existing, mutation_kind="resolve_keep_mine")

                conflict = self._get_sync_conflict(session, household_id, conflict_id)
                if conflict is None:
                    raise GroceryDomainError(
                        code="sync_conflict_not_found",
                        message="Sync conflict not found.",
                        status_code=404,
                    )
                self._ensure_sync_conflict_pending(conflict)

                context = self._sync_conflict_context(session, conflict)
                self._refresh_sync_conflict_read_model(session, conflict, context=context)
                if (
                    command.base_server_version is not None
                    and command.base_server_version != conflict.current_server_version
                ):
                    raise GroceryDomainError(
                        code="sync_conflict_resolution_stale",
                        message="The conflict changed on the server. Refresh the conflict detail before keeping your change.",
                        status_code=409,
                    )

                now = _utcnow()
                conflict.local_queue_status = SyncMutationState.resolving.value
                session.flush()

                resolution_mutation = self._sync_resolution_mutation(
                    conflict,
                    actor_id=actor_id,
                    client_mutation_id=command.client_mutation_id,
                    base_server_version=conflict.current_server_version,
                )
                mutation_kind = self._sync_mutation_kind(resolution_mutation.mutation_type)

                if mutation_kind == "remove_line" and context.current_item is not None and not context.current_item.active:
                    result = GroceryMutationResult(
                        mutation_kind="resolve_keep_mine",
                        grocery_list=self._list_to_read(session, context.grocery_list),
                        item=None,
                    )
                    self._store_receipt(
                        session,
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_kind="resolve_keep_mine",
                        result=result,
                        accepted_at=now,
                    )
                else:
                    resolution_context = self._resolve_sync_mutation_context(
                        session,
                        household_id,
                        resolution_mutation,
                    )
                    self._apply_sync_mutation(
                        session,
                        household_id=household_id,
                        actor_id=actor_id,
                        mutation=resolution_mutation,
                        context=resolution_context,
                        allow_inactive_resolution=True,
                    )
                    stored_result = self._get_receipt(session, household_id, command.client_mutation_id)
                    if stored_result is None:
                        raise GroceryDomainError(
                            code="sync_resolution_receipt_missing",
                            message="Unable to load the keep-mine resolution receipt.",
                            status_code=409,
                        )
                    result = self._resolution_result(stored_result, mutation_kind="resolve_keep_mine")

                final_context = self._sync_conflict_context(session, conflict)
                self._mark_sync_conflict_resolved(
                    conflict,
                    action=SyncResolutionAction.keep_mine,
                    actor_id=actor_id,
                    resolution_client_mutation_id=command.client_mutation_id,
                    resolved_at=now,
                    context=final_context,
                    base_server_version=conflict.current_server_version,
                )
                return result

    def resolve_sync_conflict_use_server(
        self,
        household_id: str,
        conflict_id: str,
        *,
        actor_id: str,
        command: SyncConflictUseServerCommand,
    ) -> GroceryMutationResult:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    return self._resolution_result(existing, mutation_kind="resolve_use_server")

                conflict = self._get_sync_conflict(session, household_id, conflict_id)
                if conflict is None:
                    raise GroceryDomainError(
                        code="sync_conflict_not_found",
                        message="Sync conflict not found.",
                        status_code=404,
                    )
                self._ensure_sync_conflict_pending(conflict)

                context = self._sync_conflict_context(session, conflict)
                self._refresh_sync_conflict_read_model(session, conflict, context=context)
                now = _utcnow()
                result = GroceryMutationResult(
                    mutation_kind="resolve_use_server",
                    grocery_list=self._list_to_read(session, context.grocery_list),
                    item=None,
                )
                self._store_receipt(
                    session,
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_kind="resolve_use_server",
                    result=result,
                    accepted_at=now,
                )
                self._mark_sync_conflict_resolved(
                    conflict,
                    action=SyncResolutionAction.use_server,
                    actor_id=actor_id,
                    resolution_client_mutation_id=command.client_mutation_id,
                    resolved_at=now,
                    context=context,
                    base_server_version=conflict.current_server_version,
                )
                return result

    def _derive_into_list(
        self,
        session: Session,
        *,
        household_id: str,
        actor_id: str,
        plan: MealPlan,
        grocery_list: GroceryList,
        mutation_kind: str,
        client_mutation_id: str,
        correlation_id: str | None = None,
    ) -> GroceryMutationResult:
        self._ensure_household_exists(session, household_id)
        prior_version = self._current_version(session, grocery_list)
        previous_items = self._get_version_items(session, prior_version.id) if prior_version is not None else []
        now = _utcnow()

        raw_needs, warnings = self._build_raw_needs(session, household_id=household_id, plan=plan)
        derived_items = self._consolidate_needs(raw_needs)

        next_version_number = (grocery_list.current_version_number + 1) if prior_version is not None else 1
        if prior_version is not None:
            prior_version.invalidated_at = now

        current_inventory_ref = self._inventory_snapshot_reference(
            session,
            household_id,
            relevant_keys=self._plan_inventory_relevance_keys(plan),
        )
        version = GroceryListVersion(
            grocery_list_id=grocery_list.id,
            version_number=next_version_number,
            plan_period_reference=_period_reference(plan.period_start, plan.period_end),
            confirmed_plan_id=plan.id,
            derived_at=now,
            confirmed_plan_version=plan.version,
            inventory_snapshot_reference=current_inventory_ref,
            invalidated_at=None,
            incomplete_slot_warnings=json.dumps([warning.model_dump(mode="json") for warning in warnings]),
        )
        session.add(version)
        session.flush()

        for item in derived_items:
            session.add(self._derived_item_model(grocery_list.id, version.id, item, previous_items, now))
        for item in previous_items:
            if item.origin == GroceryItemOrigin.ad_hoc.value:
                session.add(self._copy_item_to_version(item, grocery_list.id, version.id, now))
        session.flush()

        grocery_list.meal_plan_id = plan.id
        grocery_list.current_version_number = version.version_number
        grocery_list.status = GroceryListStatus.draft.value
        grocery_list.updated_at = now
        session.flush()

        self._log_derivation(
            household_id=household_id,
            actor_id=actor_id,
            grocery_list_id=grocery_list.id,
            grocery_list_version_id=version.id,
            plan_id=plan.id,
            mutation_kind=mutation_kind,
            client_mutation_id=client_mutation_id,
            correlation_id=correlation_id or client_mutation_id,
            raw_need_count=len(raw_needs),
            offset_need_count=sum(1 for need in raw_needs if need.offset_quantity > 0),
            consolidated_line_count=len(derived_items),
            incomplete_slot_count=len(warnings),
            unmatched_need_count=sum(1 for need in raw_needs if need.offset_inventory_item_id is None),
            inventory_snapshot_reference=current_inventory_ref,
            confirmed_plan_version=plan.version,
        )
        self._log_incomplete_slots(
            household_id=household_id,
            actor_id=actor_id,
            grocery_list_id=grocery_list.id,
            grocery_list_version_id=version.id,
            client_mutation_id=client_mutation_id,
            correlation_id=correlation_id or client_mutation_id,
            warnings=warnings,
        )
        return GroceryMutationResult(
            mutation_kind=mutation_kind,
            grocery_list=self._list_to_read(session, grocery_list),
            item=None,
        )

    def _build_raw_needs(
        self,
        session: Session,
        *,
        household_id: str,
        plan: MealPlan,
    ) -> tuple[list[RawNeed], list[GroceryIncompleteSlotWarningRead]]:
        inventory_items = self._inventory_items(session, household_id)
        inventory_remaining = {item.id: item.quantity_on_hand for item in inventory_items}
        warnings: list[GroceryIncompleteSlotWarningRead] = []
        raw_needs: list[RawNeed] = []

        for slot in self._ordered_slots(plan.slots):
            ingredients = self._ingredient_catalog.get_ingredients(slot)
            if not ingredients:
                warnings.append(
                    GroceryIncompleteSlotWarningRead(
                        meal_slot_id=slot.id,
                        meal_name=slot.meal_title,
                        message="No authoritative ingredient data is available for this meal slot.",
                    )
                )
                continue

            for ingredient in ingredients:
                need = RawNeed(
                    ingredient_name=ingredient.ingredient_name,
                    ingredient_ref_id=ingredient.ingredient_ref_id,
                    required_quantity=_normalize_decimal(ingredient.quantity),
                    unit=ingredient.unit,
                    meal_slot_id=slot.id,
                    meal_name=slot.meal_title,
                )
                match = self._match_inventory_item(inventory_items, need)
                if match is not None:
                    remaining = inventory_remaining.get(match.id, Decimal("0.0000"))
                    offset = min(need.required_quantity, remaining)
                    if offset > 0:
                        need.offset_quantity = offset.quantize(_QUANTITY_SCALE)
                        need.offset_inventory_item_id = match.id
                        need.offset_inventory_item_version = match.version
                        inventory_remaining[match.id] = (remaining - offset).quantize(_QUANTITY_SCALE)
                raw_needs.append(need)
        return raw_needs, warnings

    def _consolidate_needs(self, raw_needs: list[RawNeed]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str | None, str, str], dict[str, Any]] = {}
        for need in raw_needs:
            if need.shopping_quantity <= 0:
                continue
            key = (need.ingredient_ref_id, _normalized_name(need.ingredient_name), need.unit)
            entry = grouped.setdefault(
                key,
                {
                    "ingredient_name": need.ingredient_name,
                    "ingredient_ref_id": need.ingredient_ref_id,
                    "required_quantity": Decimal("0.0000"),
                    "offset_quantity": Decimal("0.0000"),
                    "shopping_quantity": Decimal("0.0000"),
                    "unit": need.unit,
                    "meal_sources": [],
                    "offset_inventory_item_id": need.offset_inventory_item_id,
                    "offset_inventory_item_version": need.offset_inventory_item_version,
                },
            )
            entry["required_quantity"] += need.required_quantity
            entry["offset_quantity"] += need.offset_quantity
            entry["shopping_quantity"] += need.shopping_quantity
            entry["meal_sources"].append(
                GroceryMealSourceRead(
                    meal_slot_id=need.meal_slot_id,
                    meal_name=need.meal_name,
                    contributed_quantity=need.shopping_quantity,
                )
            )
            if (
                entry["offset_inventory_item_id"] != need.offset_inventory_item_id
                or entry["offset_inventory_item_version"] != need.offset_inventory_item_version
            ):
                entry["offset_inventory_item_id"] = None
                entry["offset_inventory_item_version"] = None

        consolidated = list(grouped.values())
        for entry in consolidated:
            entry["required_quantity"] = entry["required_quantity"].quantize(_QUANTITY_SCALE)
            entry["offset_quantity"] = entry["offset_quantity"].quantize(_QUANTITY_SCALE)
            entry["shopping_quantity"] = entry["shopping_quantity"].quantize(_QUANTITY_SCALE)
            entry["meal_sources"].sort(key=lambda source: (source.meal_name or "", source.meal_slot_id))
        consolidated.sort(
            key=lambda item: (_normalized_name(item["ingredient_name"]), item["unit"], item["ingredient_ref_id"] or "")
        )
        return consolidated

    def _derived_item_model(
        self,
        grocery_list_id: str,
        grocery_list_version_id: str,
        derived: dict[str, Any],
        previous_items: list[GroceryListItem],
        now: datetime,
    ) -> GroceryListItem:
        previous = self._find_previous_item(previous_items, derived["ingredient_ref_id"], derived["ingredient_name"], derived["unit"])
        active = True
        removed_at: datetime | None = None
        removed_client_mutation_id: str | None = None
        user_adjusted_quantity: Decimal | None = None
        user_adjustment_note: str | None = None
        user_adjustment_flagged = False

        if previous is not None:
            if not previous.active:
                active = False
                removed_at = previous.removed_at
                removed_client_mutation_id = previous.removed_client_mutation_id
            if previous.user_adjusted_quantity is not None:
                user_adjusted_quantity = previous.user_adjusted_quantity
                user_adjustment_note = previous.user_adjustment_note
                user_adjustment_flagged = any(
                    [
                        previous.required_quantity != derived["required_quantity"],
                        previous.offset_quantity != derived["offset_quantity"],
                        previous.shopping_quantity != derived["shopping_quantity"],
                    ]
                )

        return GroceryListItem(
            stable_line_id=previous.stable_line_id if previous is not None else str(uuid.uuid4()),
            grocery_list_id=grocery_list_id,
            grocery_list_version_id=grocery_list_version_id,
            ingredient_name=derived["ingredient_name"],
            ingredient_ref_id=derived["ingredient_ref_id"],
            required_quantity=derived["required_quantity"],
            unit=derived["unit"],
            offset_quantity=derived["offset_quantity"],
            offset_inventory_item_id=derived["offset_inventory_item_id"],
            offset_inventory_item_version=derived["offset_inventory_item_version"],
            shopping_quantity=derived["shopping_quantity"],
            origin=GroceryItemOrigin.derived.value,
            meal_sources=json.dumps([source.model_dump(mode="json") for source in derived["meal_sources"]]),
            user_adjusted_quantity=user_adjusted_quantity,
            user_adjustment_note=user_adjustment_note,
            user_adjustment_flagged=user_adjustment_flagged,
            ad_hoc_note=None,
            active=active,
            removed_at=removed_at,
            removed_client_mutation_id=removed_client_mutation_id,
            created_at=now,
            updated_at=now,
        )

    def _copy_item_to_version(
        self,
        item: GroceryListItem,
        grocery_list_id: str,
        grocery_list_version_id: str,
        now: datetime,
    ) -> GroceryListItem:
        return GroceryListItem(
            stable_line_id=item.stable_line_id,
            grocery_list_id=grocery_list_id,
            grocery_list_version_id=grocery_list_version_id,
            ingredient_name=item.ingredient_name,
            ingredient_ref_id=item.ingredient_ref_id,
            required_quantity=item.required_quantity,
            unit=item.unit,
            offset_quantity=item.offset_quantity,
            offset_inventory_item_id=item.offset_inventory_item_id,
            offset_inventory_item_version=item.offset_inventory_item_version,
            shopping_quantity=item.shopping_quantity,
            origin=item.origin,
            meal_sources=item.meal_sources,
            user_adjusted_quantity=item.user_adjusted_quantity,
            user_adjustment_note=item.user_adjustment_note,
            user_adjustment_flagged=item.user_adjustment_flagged,
            ad_hoc_note=item.ad_hoc_note,
            active=item.active,
            removed_at=item.removed_at,
            created_client_mutation_id=item.created_client_mutation_id,
            removed_client_mutation_id=item.removed_client_mutation_id,
            created_at=item.created_at,
            updated_at=now,
        )

    def _find_previous_item(
        self,
        previous_items: list[GroceryListItem],
        ingredient_ref_id: str | None,
        ingredient_name: str,
        unit: str,
    ) -> GroceryListItem | None:
        normalized = _normalized_name(ingredient_name)
        for item in previous_items:
            if item.origin != GroceryItemOrigin.derived.value:
                continue
            same_ref = item.ingredient_ref_id == ingredient_ref_id
            same_name = _normalized_name(item.ingredient_name) == normalized
            if item.unit == unit and (same_ref or (ingredient_ref_id is None and same_name)):
                return item
        return None

    def _match_inventory_item(self, inventory_items: list[InventoryItem], need: RawNeed) -> InventoryItem | None:
        normalized_need_name = _normalized_name(need.ingredient_name)
        for item in inventory_items:
            if item.primary_unit != need.unit:
                continue
            if _normalized_name(item.name) == normalized_need_name:
                return item
        return None

    def _refresh_stale_status(
        self,
        session: Session,
        grocery_list: GroceryList,
        *,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ) -> bool:
        stale_reason = self._stale_reason(session, grocery_list)
        stale = stale_reason is not None
        target_status = (
            GroceryListStatus.stale_draft.value
            if stale
            else GroceryListStatus.draft.value
        )
        if grocery_list.status not in {
            GroceryListStatus.draft.value,
            GroceryListStatus.stale_draft.value,
        }:
            return False
        if grocery_list.status == target_status:
            return False
        current_version = self._current_version(session, grocery_list)
        previous_status = grocery_list.status
        grocery_list.status = target_status
        grocery_list.updated_at = _utcnow()
        self._log_stale_transition(
            household_id=grocery_list.household_id,
            actor_id=actor_id,
            grocery_list_id=grocery_list.id,
            grocery_list_version_id=current_version.id if current_version is not None else None,
            previous_status=previous_status,
            current_status=target_status,
            stale_reason=stale_reason,
            correlation_id=correlation_id,
        )
        return True

    def _is_list_stale(self, session: Session, grocery_list: GroceryList) -> bool:
        return self._stale_reason(session, grocery_list) is not None

    def _stale_reason(self, session: Session, grocery_list: GroceryList) -> str | None:
        if grocery_list.status not in {
            GroceryListStatus.draft.value,
            GroceryListStatus.stale_draft.value,
        }:
            return None
        plan = self._list_plan(session, grocery_list)
        current_version = self._current_version(session, grocery_list)
        if plan is None or current_version is None:
            return None
        latest_plan = self._get_confirmed_plan_for_period(session, household_id=grocery_list.household_id, period_start=plan.period_start)
        if latest_plan is None:
            return None
        if latest_plan.id != plan.id or latest_plan.version != (current_version.confirmed_plan_version or 0):
            return "confirmed_plan_changed"
        current_inventory_ref = self._inventory_snapshot_reference(
            session,
            grocery_list.household_id,
            relevant_keys=self._plan_inventory_relevance_keys(latest_plan),
        )
        if current_version.inventory_snapshot_reference != current_inventory_ref:
            return "inventory_snapshot_changed"
        return None

    def _list_to_read(self, session: Session, grocery_list: GroceryList) -> GroceryListRead:
        current_version = self._current_version(session, grocery_list)
        plan = self._list_plan(session, grocery_list)
        lines = (
            [
                self._item_to_read(item)
                for item in self._get_version_items(session, current_version.id, active_only=True)
            ]
            if current_version is not None
            else []
        )
        return GroceryListRead(
            id=grocery_list.id,
            household_id=grocery_list.household_id,
            meal_plan_id=grocery_list.meal_plan_id,
            status=GroceryListStatus(grocery_list.status),
            current_version_number=grocery_list.current_version_number,
            grocery_list_version_id=current_version.id if current_version is not None else None,
            current_version_id=current_version.id if current_version is not None else None,
            confirmed_at=grocery_list.confirmed_at,
            confirmation_client_mutation_id=grocery_list.confirmation_client_mutation_id,
            trip_state=grocery_list.trip_state,
            last_derived_at=current_version.derived_at if current_version is not None else None,
            plan_period_start=plan.period_start if plan is not None else None,
            plan_period_end=plan.period_end if plan is not None else None,
            confirmed_plan_version=current_version.confirmed_plan_version if current_version is not None else None,
            inventory_snapshot_reference=(
                current_version.inventory_snapshot_reference if current_version is not None else None
            ),
            is_stale=self._is_list_stale(session, grocery_list),
            incomplete_slot_warnings=self._warning_reads(current_version.incomplete_slot_warnings if current_version is not None else None),
            lines=lines,
            created_at=grocery_list.created_at,
            updated_at=grocery_list.updated_at,
        )

    def _item_to_read(self, item: GroceryListItem) -> GroceryListItemRead:
        return GroceryListItemRead.model_validate(item)

    def _get_list(self, session: Session, household_id: str, grocery_list_id: str) -> GroceryList | None:
        stmt = select(GroceryList).where(
            GroceryList.id == grocery_list_id,
            GroceryList.household_id == household_id,
        )
        return session.scalar(stmt)

    def _get_latest_list_for_period(
        self,
        session: Session,
        *,
        household_id: str,
        period_start: date,
    ) -> GroceryList | None:
        stmt = (
            select(GroceryList)
            .join(MealPlan, GroceryList.meal_plan_id == MealPlan.id)
            .where(GroceryList.household_id == household_id)
            .where(MealPlan.period_start == period_start)
            .where(MealPlan.period_end == _period_end(period_start))
            .order_by(GroceryList.updated_at.desc(), GroceryList.id.desc())
        )
        return session.scalars(stmt).first()

    def _get_confirmed_plan_for_period(
        self,
        session: Session,
        *,
        household_id: str,
        period_start: date,
    ) -> MealPlan | None:
        stmt = (
            select(MealPlan)
            .where(MealPlan.household_id == household_id)
            .where(MealPlan.period_start == period_start)
            .where(MealPlan.period_end == _period_end(period_start))
            .where(MealPlan.status == MealPlanStatus.confirmed.value)
            .order_by(MealPlan.confirmed_at.desc(), MealPlan.version.desc(), MealPlan.id.desc())
        )
        return session.scalars(stmt).first()

    def _get_mutable_list(self, session: Session, household_id: str, grocery_list_id: str) -> GroceryList:
        grocery_list = self._get_list(session, household_id, grocery_list_id)
        if grocery_list is None:
            raise GroceryDomainError(
                code="grocery_list_not_found",
                message="Grocery list not found.",
                status_code=404,
            )
        if grocery_list.status not in {
            GroceryListStatus.draft.value,
            GroceryListStatus.stale_draft.value,
        }:
            raise GroceryDomainError(
                code="grocery_list_not_mutable",
                message="Only draft grocery lists can be changed.",
                status_code=409,
            )
        return grocery_list

    def _require_current_version(self, session: Session, grocery_list: GroceryList) -> GroceryListVersion:
        current_version = self._current_version(session, grocery_list)
        if current_version is None:
            raise GroceryDomainError(
                code="grocery_list_version_missing",
                message="The grocery list has no current version.",
                status_code=409,
            )
        return current_version

    def _get_current_line(
        self,
        session: Session,
        grocery_list: GroceryList,
        grocery_list_item_id: str,
    ) -> GroceryListItem | None:
        current_version = self._current_version(session, grocery_list)
        if current_version is None:
            raise GroceryDomainError(
                code="grocery_list_version_missing",
                message="The grocery list has no current version.",
                status_code=409,
            )
        stmt = select(GroceryListItem).where(
            GroceryListItem.id == grocery_list_item_id,
            GroceryListItem.grocery_list_id == grocery_list.id,
            GroceryListItem.grocery_list_version_id == current_version.id,
        )
        return session.scalar(stmt)

    def _current_version(self, session: Session, grocery_list: GroceryList) -> GroceryListVersion | None:
        stmt = select(GroceryListVersion).where(
            GroceryListVersion.grocery_list_id == grocery_list.id,
            GroceryListVersion.version_number == grocery_list.current_version_number,
        )
        return session.scalar(stmt)

    def _get_syncable_list(self, session: Session, household_id: str, grocery_list_id: str) -> GroceryList:
        grocery_list = self._get_list(session, household_id, grocery_list_id)
        if grocery_list is None:
            raise GroceryDomainError(
                code="grocery_list_not_found",
                message="Grocery list not found.",
                status_code=404,
            )
        if grocery_list.status not in {
            GroceryListStatus.confirmed.value,
            GroceryListStatus.trip_in_progress.value,
            GroceryListStatus.trip_complete_pending_reconciliation.value,
        }:
            raise GroceryDomainError(
                code="grocery_list_not_syncable",
                message="Only confirmed or in-progress grocery lists can accept sync uploads.",
                status_code=409,
            )
        return grocery_list

    def _get_current_line_by_stable_id(
        self,
        session: Session,
        grocery_list: GroceryList,
        stable_line_id: str,
    ) -> GroceryListItem | None:
        current_version = self._current_version(session, grocery_list)
        if current_version is None:
            return None
        stmt = select(GroceryListItem).where(
            GroceryListItem.grocery_list_id == grocery_list.id,
            GroceryListItem.grocery_list_version_id == current_version.id,
            GroceryListItem.stable_line_id == stable_line_id,
        )
        return session.scalar(stmt)

    def _find_syncable_list_by_stable_line_id(
        self,
        session: Session,
        household_id: str,
        stable_line_id: str,
    ) -> GroceryList | None:
        stmt = (
            select(GroceryList)
            .join(
                GroceryListVersion,
                (GroceryListVersion.grocery_list_id == GroceryList.id)
                & (GroceryListVersion.version_number == GroceryList.current_version_number),
            )
            .join(
                GroceryListItem,
                (GroceryListItem.grocery_list_id == GroceryList.id)
                & (GroceryListItem.grocery_list_version_id == GroceryListVersion.id),
            )
            .where(GroceryList.household_id == household_id)
            .where(
                GroceryList.status.in_(
                    [
                        GroceryListStatus.confirmed.value,
                        GroceryListStatus.trip_in_progress.value,
                        GroceryListStatus.trip_complete_pending_reconciliation.value,
                    ]
                )
            )
            .where(GroceryListItem.stable_line_id == stable_line_id)
            .order_by(GroceryList.updated_at.desc(), GroceryList.id.desc())
        )
        return session.scalars(stmt).first()

    def _resolve_sync_mutation_context(
        self,
        session: Session,
        household_id: str,
        mutation: QueueableSyncMutation,
    ) -> SyncMutationContext:
        aggregate_type = SyncAggregateType(mutation.aggregate_type)
        mutation_kind = self._sync_mutation_kind(mutation.mutation_type)
        payload = mutation.payload

        if mutation_kind == "add_ad_hoc":
            grocery_list_id = self._required_sync_string(
                payload.get("grocery_list_id") or payload.get("groceryListId") or mutation.aggregate_id,
                field_name="grocery_list_id",
            )
            grocery_list = self._get_syncable_list(session, household_id, grocery_list_id)
            current_version = self._require_current_version(session, grocery_list)
            return SyncMutationContext(
                grocery_list=grocery_list,
                current_version=current_version,
                current_item=None,
                aggregate_type=aggregate_type,
                aggregate_id=grocery_list.id,
                provisional_aggregate_id=mutation.provisional_aggregate_id,
            )

        if aggregate_type != SyncAggregateType.grocery_line:
            raise GroceryDomainError(
                code="sync_aggregate_not_supported",
                message="The sync upload API currently supports grocery-list adds and grocery-line mutations.",
                status_code=422,
            )

        stable_line_id = self._required_sync_string(
            mutation.aggregate_id or payload.get("grocery_line_id") or payload.get("groceryLineId"),
            field_name="aggregate_id",
        )
        grocery_list = None
        if payload.get("grocery_list_id") or payload.get("groceryListId"):
            grocery_list = self._get_syncable_list(
                session,
                household_id,
                self._required_sync_string(
                    payload.get("grocery_list_id") or payload.get("groceryListId"),
                    field_name="grocery_list_id",
                ),
            )
        if grocery_list is None:
            grocery_list = self._find_syncable_list_by_stable_line_id(session, household_id, stable_line_id)
        if grocery_list is None:
            raise GroceryDomainError(
                code="grocery_line_not_found",
                message="Grocery line not found for sync upload.",
                status_code=404,
            )
        current_version = self._require_current_version(session, grocery_list)
        return SyncMutationContext(
            grocery_list=grocery_list,
            current_version=current_version,
            current_item=self._get_current_line_by_stable_id(session, grocery_list, stable_line_id),
            aggregate_type=aggregate_type,
            aggregate_id=stable_line_id,
            provisional_aggregate_id=mutation.provisional_aggregate_id,
        )

    @staticmethod
    def _warning_reads(payload: str | None) -> list[GroceryIncompleteSlotWarningRead]:
        if not payload:
            return []
        try:
            raw = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if not isinstance(raw, list):
            return []
        return [GroceryIncompleteSlotWarningRead.model_validate(item) for item in raw]

    def _get_version_items(
        self,
        session: Session,
        grocery_list_version_id: str,
        *,
        active_only: bool = False,
    ) -> list[GroceryListItem]:
        stmt = (
            select(GroceryListItem)
            .where(GroceryListItem.grocery_list_version_id == grocery_list_version_id)
            .order_by(GroceryListItem.created_at.asc(), GroceryListItem.id.asc())
        )
        if active_only:
            stmt = stmt.where(GroceryListItem.active.is_(True))
        return session.scalars(stmt).all()

    @staticmethod
    def _ordered_slots(slots: list[MealPlanSlot]) -> list[MealPlanSlot]:
        return sorted(slots, key=lambda slot: (slot.day_of_week, slot.meal_type, slot.slot_key, slot.id))

    def _inventory_items(self, session: Session, household_id: str) -> list[InventoryItem]:
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.household_id == household_id)
            .where(InventoryItem.is_active.is_(True))
            .order_by(InventoryItem.created_at.asc(), InventoryItem.id.asc())
        )
        return session.scalars(stmt).all()

    def _inventory_snapshot_reference(
        self,
        session: Session,
        household_id: str,
        *,
        relevant_keys: set[tuple[str, str]] | None = None,
    ) -> str:
        items = self._inventory_items(session, household_id)
        if relevant_keys is not None:
            items = [
                item
                for item in items
                if (_normalized_name(item.name), item.primary_unit) in relevant_keys
            ]
        digest = hashlib.sha1()
        for item in items:
            digest.update(
                "|".join(
                    [
                        item.id,
                        _normalized_name(item.name),
                        item.primary_unit,
                        str(item.quantity_on_hand),
                        str(item.version),
                        str(int(item.is_active)),
                    ]
                ).encode("utf-8")
            )
            digest.update(b";")
        return f"inventory-{digest.hexdigest()[:16]}"

    def _plan_inventory_relevance_keys(self, plan: MealPlan) -> set[tuple[str, str]]:
        relevant_keys: set[tuple[str, str]] = set()
        for slot in self._ordered_slots(plan.slots):
            ingredients = self._ingredient_catalog.get_ingredients(slot)
            if not ingredients:
                continue
            for ingredient in ingredients:
                relevant_keys.add((_normalized_name(ingredient.ingredient_name), ingredient.unit))
        return relevant_keys

    def _list_plan(self, session: Session, grocery_list: GroceryList) -> MealPlan | None:
        if grocery_list.meal_plan_id is None:
            return None
        return session.get(MealPlan, grocery_list.meal_plan_id)

    def _choose_list_for_derivation(
        self,
        session: Session,
        household_id: str,
        plan: MealPlan,
    ) -> GroceryList:
        existing = self._get_latest_list_for_period(session, household_id=household_id, period_start=plan.period_start)
        if existing is None:
            return self._create_grocery_list(session, household_id=household_id, meal_plan_id=plan.id)
        if existing.status in {
            GroceryListStatus.confirmed.value,
            GroceryListStatus.trip_in_progress.value,
            GroceryListStatus.trip_complete_pending_reconciliation.value,
        }:
            return self._create_grocery_list(session, household_id=household_id, meal_plan_id=plan.id)
        return existing

    def _create_grocery_list(self, session: Session, *, household_id: str, meal_plan_id: str) -> GroceryList:
        now = _utcnow()
        grocery_list = GroceryList(
            household_id=household_id,
            meal_plan_id=meal_plan_id,
            status=GroceryListStatus.deriving.value,
            current_version_number=1,
            created_at=now,
            updated_at=now,
        )
        session.add(grocery_list)
        session.flush()
        return grocery_list

    def _get_receipt(
        self,
        session: Session,
        household_id: str,
        client_mutation_id: str,
    ) -> GroceryMutationResult | None:
        stmt = select(GroceryMutationReceipt).where(
            GroceryMutationReceipt.household_id == household_id,
            GroceryMutationReceipt.client_mutation_id == client_mutation_id,
        )
        receipt = session.scalar(stmt)
        if receipt is None or receipt.result_summary is None:
            return None
        payload = json.loads(receipt.result_summary)
        return GroceryMutationResult.model_validate(payload).model_copy(update={"is_duplicate": True})

    def _has_applied_receipt(self, session: Session, household_id: str, client_mutation_id: str) -> bool:
        stmt = select(GroceryMutationReceipt.id).where(
            GroceryMutationReceipt.household_id == household_id,
            GroceryMutationReceipt.client_mutation_id == client_mutation_id,
        )
        return session.scalar(stmt) is not None

    def _build_duplicate_sync_outcome(
        self,
        session: Session,
        household_id: str,
        actor_id: str,
        client_mutation_id: str,
        *,
        provisional_aggregate_id: str | None = None,
    ) -> SyncMutationOutcomeRead:
        existing = self._get_receipt(session, household_id, client_mutation_id)
        if existing is None:
            raise GroceryDomainError(
                code="sync_duplicate_receipt_missing",
                message="Unable to load the original grocery mutation receipt for duplicate sync replay.",
                status_code=409,
            )
        aggregate = (
            SyncAggregateRef(
                aggregate_type=SyncAggregateType.grocery_line,
                aggregate_id=existing.item.grocery_line_id,
                aggregate_version=existing.grocery_list.current_version_number,
            )
            if existing.item is not None
            else SyncAggregateRef(
                aggregate_type=SyncAggregateType.grocery_list,
                aggregate_id=existing.grocery_list.id,
                aggregate_version=existing.grocery_list.current_version_number,
            )
        )
        self._log_mutation(
            mutation_kind=f"sync_{existing.mutation_kind}",
            outcome=SyncOutcome.duplicate_retry.value,
            household_id=household_id,
            actor_id=actor_id,
            grocery_list_id=existing.grocery_list.id,
            grocery_list_item_id=existing.item.id if existing.item is not None else None,
            grocery_list_version_id=existing.grocery_list.current_version_id,
            client_mutation_id=client_mutation_id,
            aggregate_type=aggregate.aggregate_type.value,
            aggregate_id=aggregate.aggregate_id,
            aggregate_version=aggregate.aggregate_version,
            provisional_aggregate_id=provisional_aggregate_id,
        )
        return SyncMutationOutcomeRead(
            client_mutation_id=client_mutation_id,
            mutation_type=existing.mutation_kind,
            aggregate=aggregate,
            outcome=SyncOutcome.duplicate_retry,
            authoritative_server_version=existing.grocery_list.current_version_number,
            conflict_id=None,
            retryable=False,
            duplicate_of_client_mutation_id=client_mutation_id,
            auto_merge_reason=None,
        )

    def _get_sync_conflict_by_local_mutation(
        self,
        session: Session,
        household_id: str,
        local_mutation_id: str,
    ) -> GrocerySyncConflict | None:
        stmt = select(GrocerySyncConflict).where(
            GrocerySyncConflict.household_id == household_id,
            GrocerySyncConflict.local_mutation_id == local_mutation_id,
        )
        return session.scalar(stmt)

    def _get_sync_conflict(
        self,
        session: Session,
        household_id: str,
        conflict_id: str,
    ) -> GrocerySyncConflict | None:
        stmt = select(GrocerySyncConflict).where(
            GrocerySyncConflict.household_id == household_id,
            GrocerySyncConflict.id == conflict_id,
        )
        return session.scalar(stmt)

    def _sync_mutation_kind(self, mutation_type: str) -> str:
        normalized = mutation_type.strip().casefold()
        if normalized in {"add_ad_hoc", "add_ad_hoc_line"}:
            return "add_ad_hoc"
        if normalized in {"adjust_line", "adjust_quantity"}:
            return "adjust_line"
        if normalized == "remove_line":
            return "remove_line"
        raise GroceryDomainError(
            code="sync_mutation_not_supported",
            message=f"Unsupported sync mutation type '{mutation_type}'.",
            status_code=422,
        )

    def _required_sync_string(self, value: object, *, field_name: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise GroceryDomainError(
            code="sync_payload_invalid",
            message=f"Sync upload payload is missing '{field_name}'.",
            status_code=422,
        )

    def _required_sync_decimal(self, value: object, *, field_name: str) -> Decimal:
        try:
            parsed = Decimal(str(value))
        except Exception as error:  # noqa: BLE001 - normalize to domain error
            raise GroceryDomainError(
                code="sync_payload_invalid",
                message=f"Sync upload payload field '{field_name}' must be numeric.",
                status_code=422,
            ) from error
        if parsed <= 0:
            raise GroceryDomainError(
                code="sync_payload_invalid",
                message=f"Sync upload payload field '{field_name}' must be greater than zero.",
                status_code=422,
            )
        return _normalize_decimal(parsed)

    def _clone_current_version_for_sync(
        self,
        session: Session,
        grocery_list: GroceryList,
        current_version: GroceryListVersion,
        now: datetime,
    ) -> tuple[GroceryListVersion, dict[str, GroceryListItem]]:
        current_items = self._get_version_items(session, current_version.id, active_only=False)
        current_version.invalidated_at = now
        next_version = GroceryListVersion(
            grocery_list_id=grocery_list.id,
            version_number=current_version.version_number + 1,
            plan_period_reference=current_version.plan_period_reference,
            confirmed_plan_id=current_version.confirmed_plan_id,
            derived_at=current_version.derived_at,
            confirmed_plan_version=current_version.confirmed_plan_version,
            inventory_snapshot_reference=current_version.inventory_snapshot_reference,
            invalidated_at=None,
            incomplete_slot_warnings=current_version.incomplete_slot_warnings,
        )
        session.add(next_version)
        session.flush()

        items_by_stable_id: dict[str, GroceryListItem] = {}
        for item in current_items:
            copied = self._copy_item_to_version(item, grocery_list.id, next_version.id, now)
            session.add(copied)
            session.flush()
            items_by_stable_id[copied.stable_line_id] = copied
        return next_version, items_by_stable_id

    def _apply_sync_mutation(
        self,
        session: Session,
        *,
        household_id: str,
        actor_id: str,
        mutation: QueueableSyncMutation,
        context: SyncMutationContext,
        outcome: SyncOutcome = SyncOutcome.applied,
        auto_merge_reason: str | None = None,
        allow_inactive_resolution: bool = False,
    ) -> SyncMutationOutcomeRead:
        mutation_kind = self._sync_mutation_kind(mutation.mutation_type)
        now = _utcnow()
        next_version, cloned_items = self._clone_current_version_for_sync(
            session,
            context.grocery_list,
            context.current_version,
            now,
        )
        grocery_list = context.grocery_list

        item: GroceryListItem | None = None
        if mutation_kind == "add_ad_hoc":
            payload = mutation.payload
            item = GroceryListItem(
                stable_line_id=str(uuid.uuid4()),
                grocery_list_id=grocery_list.id,
                grocery_list_version_id=next_version.id,
                ingredient_name=self._required_sync_string(
                    payload.get("ingredient_name") or payload.get("name"),
                    field_name="ingredient_name",
                ),
                ingredient_ref_id=None,
                required_quantity=self._required_sync_decimal(
                    payload.get("shopping_quantity") or payload.get("quantity_to_buy") or payload.get("quantity_needed"),
                    field_name="shopping_quantity",
                ),
                unit=self._required_sync_string(payload.get("unit"), field_name="unit"),
                offset_quantity=Decimal("0.0000"),
                shopping_quantity=self._required_sync_decimal(
                    payload.get("shopping_quantity") or payload.get("quantity_to_buy") or payload.get("quantity_needed"),
                    field_name="shopping_quantity",
                ),
                origin=GroceryItemOrigin.ad_hoc.value,
                meal_sources=None,
                user_adjusted_quantity=None,
                user_adjustment_note=None,
                user_adjustment_flagged=False,
                ad_hoc_note=(
                    str(payload.get("ad_hoc_note") or payload.get("adHocNote")).strip()
                    if payload.get("ad_hoc_note") or payload.get("adHocNote")
                    else None
                ),
                active=True,
                removed_at=None,
                created_client_mutation_id=mutation.client_mutation_id,
                created_at=now,
                updated_at=now,
            )
            session.add(item)
            session.flush()
        else:
            item = cloned_items.get(context.aggregate_id)
            if item is None:
                raise GroceryDomainError(
                    code="grocery_line_not_found",
                    message="Grocery line not found for sync upload.",
                    status_code=404,
                )
            if not item.active:
                if not allow_inactive_resolution:
                    raise GroceryDomainError(
                        code="grocery_line_not_active",
                        message="Only active grocery lines can be mutated by sync upload.",
                        status_code=409,
                    )
                if mutation_kind == "adjust_line":
                    item.active = True
                    item.removed_at = None
                    item.removed_client_mutation_id = None
            if mutation_kind == "adjust_line":
                quantity = self._required_sync_decimal(
                    mutation.payload.get("user_adjusted_quantity")
                    or mutation.payload.get("quantity_to_buy")
                    or mutation.payload.get("quantityToBuy")
                    or mutation.payload.get("userAdjustedQuantity"),
                    field_name="quantity_to_buy",
                )
                item.user_adjusted_quantity = quantity
                item.user_adjustment_note = (
                    str(
                        mutation.payload.get("user_adjustment_note")
                        or mutation.payload.get("userAdjustmentNote")
                    ).strip()
                    if mutation.payload.get("user_adjustment_note") or mutation.payload.get("userAdjustmentNote")
                    else None
                )
                item.user_adjustment_flagged = quantity != item.shopping_quantity
                item.updated_at = now
            elif mutation_kind == "remove_line":
                item.active = False
                item.removed_at = now
                item.removed_client_mutation_id = mutation.client_mutation_id
                item.updated_at = now

        grocery_list.current_version_number = next_version.version_number
        if grocery_list.status == GroceryListStatus.confirmed.value:
            grocery_list.status = GroceryListStatus.trip_in_progress.value
        grocery_list.updated_at = now
        session.flush()

        result = GroceryMutationResult(
            mutation_kind=mutation_kind,
            grocery_list=self._list_to_read(session, grocery_list),
            item=self._item_to_read(item) if item is not None else None,
        )
        self._store_receipt(
            session,
            household_id=household_id,
            client_mutation_id=mutation.client_mutation_id,
            mutation_kind=mutation_kind,
            result=result,
            accepted_at=now,
        )
        self._log_mutation(
            mutation_kind=f"sync_{mutation_kind}",
            outcome=("accepted" if outcome == SyncOutcome.applied else outcome.value),
            household_id=household_id,
            actor_id=actor_id,
            grocery_list_id=grocery_list.id,
            grocery_list_item_id=item.id if item is not None else None,
            grocery_list_version_id=next_version.id,
            client_mutation_id=mutation.client_mutation_id,
            aggregate_type=(
                SyncAggregateType.grocery_line.value if item is not None else SyncAggregateType.grocery_list.value
            ),
            aggregate_id=item.stable_line_id if item is not None else grocery_list.id,
            aggregate_version=next_version.version_number,
            provisional_aggregate_id=mutation.provisional_aggregate_id,
            base_server_version=mutation.base_server_version,
            current_server_version=next_version.version_number,
            auto_merge_reason=auto_merge_reason,
        )
        return SyncMutationOutcomeRead(
            client_mutation_id=mutation.client_mutation_id,
            mutation_type=mutation_kind,
            aggregate=SyncAggregateRef(
                aggregate_type=(
                    SyncAggregateType.grocery_line if item is not None else SyncAggregateType.grocery_list
                ),
                aggregate_id=item.stable_line_id if item is not None else grocery_list.id,
                aggregate_version=next_version.version_number,
                provisional_aggregate_id=mutation.provisional_aggregate_id,
            ),
            outcome=outcome,
            authoritative_server_version=next_version.version_number,
            conflict_id=None,
            retryable=False,
            duplicate_of_client_mutation_id=None,
            auto_merge_reason=auto_merge_reason,
        )

    def _classify_stale_sync_mutation(
        self,
        session: Session,
        *,
        mutation: QueueableSyncMutation,
        context: SyncMutationContext,
    ) -> SyncReplayDecision:
        mutation_kind = self._sync_mutation_kind(mutation.mutation_type)
        semantic_area = self._sync_mutation_semantic_area(mutation, mutation_kind=mutation_kind)

        if mutation_kind == "add_ad_hoc":
            return SyncReplayDecision(
                outcome=SyncOutcome.auto_merged_non_overlapping,
                auto_merge_reason=(
                    "Auto-merged because the stale offline add creates a new ad hoc line and newer "
                    "server changes affected other grocery records."
                ),
            )

        if context.current_item is None or not context.current_item.active:
            return SyncReplayDecision(
                outcome=SyncOutcome.review_required_deleted_or_archived,
                summary=(
                    "The target grocery line is no longer active on the server and needs review "
                    "before replay can continue."
                ),
            )

        if semantic_area == "freshness_or_location":
            return SyncReplayDecision(
                outcome=SyncOutcome.review_required_freshness_or_location,
                summary=(
                    "Freshness or storage-location edits need review before replay can continue "
                    "against newer server state."
                ),
            )

        base_item = self._sync_base_line_item(
            session,
            grocery_list_id=context.grocery_list.id,
            stable_line_id=context.aggregate_id,
            base_server_version=mutation.base_server_version,
        )
        if base_item is None:
            return SyncReplayDecision(
                outcome=SyncOutcome.review_required_other_unsafe,
                summary=(
                    "The original server state for this offline change is no longer available, so "
                    "replay stopped and now needs review."
                ),
            )

        if self._sync_line_lifecycle_changed(base_item, context.current_item):
            return SyncReplayDecision(
                outcome=SyncOutcome.review_required_deleted_or_archived,
                summary=(
                    "The target grocery line was deleted or archived on the server and needs review "
                    "before replay can continue."
                ),
            )

        if semantic_area == "quantity" and self._sync_line_quantity_or_completion_changed(
            base_item,
            context.current_item,
        ):
            return SyncReplayDecision(
                outcome=SyncOutcome.review_required_quantity,
                summary=(
                    "The target grocery line changed quantity or completion semantics on the server, "
                    "so replay stopped and now needs review."
                ),
            )

        if self._sync_line_other_metadata_changed(base_item, context.current_item):
            return SyncReplayDecision(
                outcome=SyncOutcome.review_required_other_unsafe,
                summary=(
                    "The target grocery line changed on the server in a way that the MVP conflict "
                    "rules cannot safely merge automatically."
                ),
            )

        if semantic_area == "quantity":
            return SyncReplayDecision(
                outcome=SyncOutcome.auto_merged_non_overlapping,
                auto_merge_reason=(
                    "Auto-merged because the target grocery line's quantity and completion state "
                    "did not change on the server after the offline edit's base version."
                ),
            )

        if semantic_area == "lifecycle":
            return SyncReplayDecision(
                outcome=SyncOutcome.auto_merged_non_overlapping,
                auto_merge_reason=(
                    "Auto-merged because the target grocery line stayed unchanged on the server, so "
                    "the offline removal remained deterministic."
                ),
            )

        return SyncReplayDecision(
            outcome=SyncOutcome.review_required_other_unsafe,
            summary=(
                "The server changed after this offline edit, so replay stopped and now needs review."
            ),
        )

    def _stale_sync_outcome_for_context(self, context: SyncMutationContext) -> SyncOutcome:
        if context.aggregate_type == SyncAggregateType.grocery_line and (
            context.current_item is None or not context.current_item.active
        ):
            return SyncOutcome.review_required_deleted_or_archived
        return SyncOutcome.review_required_other_unsafe

    def _sync_mutation_semantic_area(
        self,
        mutation: QueueableSyncMutation,
        *,
        mutation_kind: str,
    ) -> str:
        normalized = mutation.mutation_type.strip().casefold()
        if mutation_kind == "add_ad_hoc":
            return "independent_add"
        if mutation_kind == "adjust_line":
            return "quantity"
        if mutation_kind == "remove_line":
            return "lifecycle"
        if any(token in normalized for token in ("freshness", "location", "storage", "metadata")):
            return "freshness_or_location"
        return "other"

    def _stale_sync_summary_for_context(self, context: SyncMutationContext) -> str:
        if context.aggregate_type == SyncAggregateType.grocery_line and (
            context.current_item is None or not context.current_item.active
        ):
            return "The target grocery line is no longer active on the server and needs review before replay can continue."
        return "The server changed after this offline edit, so replay stopped and now needs review."

    def _sync_base_line_item(
        self,
        session: Session,
        *,
        grocery_list_id: str,
        stable_line_id: str,
        base_server_version: int | None,
    ) -> GroceryListItem | None:
        if base_server_version is None:
            return None
        base_version = session.scalar(
            select(GroceryListVersion).where(
                GroceryListVersion.grocery_list_id == grocery_list_id,
                GroceryListVersion.version_number == base_server_version,
            )
        )
        if base_version is None:
            return None
        return session.scalar(
            select(GroceryListItem).where(
                GroceryListItem.grocery_list_id == grocery_list_id,
                GroceryListItem.grocery_list_version_id == base_version.id,
                GroceryListItem.stable_line_id == stable_line_id,
            )
        )

    @staticmethod
    def _sync_line_lifecycle_changed(base_item: GroceryListItem, current_item: GroceryListItem) -> bool:
        return (
            base_item.active != current_item.active
            or base_item.removed_at != current_item.removed_at
        )

    @staticmethod
    def _sync_line_quantity_or_completion_changed(
        base_item: GroceryListItem,
        current_item: GroceryListItem,
    ) -> bool:
        return (
            base_item.shopping_quantity != current_item.shopping_quantity
            or base_item.user_adjusted_quantity != current_item.user_adjusted_quantity
            or base_item.user_adjustment_flagged != current_item.user_adjustment_flagged
            or base_item.is_purchased != current_item.is_purchased
        )

    @staticmethod
    def _sync_line_other_metadata_changed(base_item: GroceryListItem, current_item: GroceryListItem) -> bool:
        return (
            base_item.ingredient_name != current_item.ingredient_name
            or base_item.unit != current_item.unit
            or base_item.origin != current_item.origin
            or base_item.user_adjustment_note != current_item.user_adjustment_note
            or base_item.ad_hoc_note != current_item.ad_hoc_note
        )

    def _create_sync_conflict(
        self,
        session: Session,
        *,
        household_id: str,
        grocery_list: GroceryList,
        mutation: QueueableSyncMutation,
        context: SyncMutationContext,
        outcome: SyncOutcome,
        summary: str,
    ) -> GrocerySyncConflict:
        existing = self._get_sync_conflict_by_local_mutation(session, household_id, mutation.client_mutation_id)
        if existing is not None:
            return existing

        allowed_actions = [
            SyncResolutionAction.keep_mine.value,
            SyncResolutionAction.use_server.value,
        ]
        conflict = GrocerySyncConflict(
            household_id=household_id,
            grocery_list_id=grocery_list.id,
            aggregate_type=context.aggregate_type.value,
            aggregate_id=context.aggregate_id,
            local_mutation_id=mutation.client_mutation_id,
            mutation_type=self._sync_mutation_kind(mutation.mutation_type),
            outcome=outcome.value,
            base_server_version=mutation.base_server_version,
            current_server_version=context.current_version.version_number,
            requires_review=True,
            summary=summary,
            local_queue_status=SyncMutationState.review_required.value,
            allowed_resolution_actions=json.dumps(allowed_actions),
            resolution_status=SyncResolutionStatus.pending.value,
            local_intent_summary=json.dumps(self._sync_local_intent_summary(mutation)),
            base_state_summary=json.dumps(
                self._sync_base_state_summary(
                    session,
                    grocery_list,
                    aggregate_type=context.aggregate_type,
                    aggregate_id=context.aggregate_id,
                    base_server_version=mutation.base_server_version,
                )
            ),
            server_state_summary=json.dumps(
                self._sync_server_state_summary(
                    grocery_list,
                    context.current_version,
                    context.current_item,
                )
            ),
            created_at=_utcnow(),
            resolved_at=None,
            resolved_by_actor_id=None,
        )
        session.add(conflict)
        session.flush()
        self._log_mutation(
            mutation_kind=f"sync_{conflict.mutation_type}",
            outcome=conflict.outcome,
            household_id=household_id,
            actor_id=mutation.actor_id,
            grocery_list_id=grocery_list.id,
            grocery_list_item_id=context.current_item.id if context.current_item is not None else None,
            grocery_list_version_id=context.current_version.id,
            client_mutation_id=mutation.client_mutation_id,
            aggregate_type=context.aggregate_type.value,
            aggregate_id=context.aggregate_id,
            aggregate_version=context.current_version.version_number,
            provisional_aggregate_id=mutation.provisional_aggregate_id,
            conflict_id=conflict.id,
            base_server_version=mutation.base_server_version,
            current_server_version=context.current_version.version_number,
            summary=summary,
        )
        return conflict

    def _sync_conflict_context(
        self,
        session: Session,
        conflict: GrocerySyncConflict,
    ) -> SyncMutationContext:
        grocery_list = self._get_list(session, conflict.household_id, conflict.grocery_list_id)
        if grocery_list is None:
            raise GroceryDomainError(
                code="grocery_list_not_found",
                message="Grocery list not found for sync conflict.",
                status_code=404,
            )
        current_version = self._require_current_version(session, grocery_list)
        aggregate_type = SyncAggregateType(conflict.aggregate_type)
        current_item = (
            self._get_current_line_by_stable_id(session, grocery_list, conflict.aggregate_id)
            if aggregate_type == SyncAggregateType.grocery_line
            else None
        )
        return SyncMutationContext(
            grocery_list=grocery_list,
            current_version=current_version,
            current_item=current_item,
            aggregate_type=aggregate_type,
            aggregate_id=conflict.aggregate_id,
        )

    def _refresh_sync_conflict_read_model(
        self,
        session: Session,
        conflict: GrocerySyncConflict,
        *,
        context: SyncMutationContext | None = None,
    ) -> bool:
        if conflict.resolution_status != SyncResolutionStatus.pending.value:
            return False
        context = context or self._sync_conflict_context(session, conflict)
        server_state_summary = self._sync_server_state_summary(
            context.grocery_list,
            context.current_version,
            context.current_item,
        )
        changed = (
            conflict.current_server_version != context.current_version.version_number
            or self._parse_json_dict(conflict.server_state_summary) != server_state_summary
        )
        if changed:
            conflict.current_server_version = context.current_version.version_number
            conflict.server_state_summary = json.dumps(server_state_summary)
            session.flush()
        return changed

    @staticmethod
    def _ensure_sync_conflict_pending(conflict: GrocerySyncConflict) -> None:
        if conflict.resolution_status == SyncResolutionStatus.pending.value:
            return
        raise GroceryDomainError(
            code="sync_conflict_already_resolved",
            message="This sync conflict has already been resolved.",
            status_code=409,
        )

    def _sync_resolution_mutation(
        self,
        conflict: GrocerySyncConflict,
        *,
        actor_id: str,
        client_mutation_id: str,
        base_server_version: int,
    ) -> QueueableSyncMutation:
        local_intent = self._parse_json_dict(conflict.local_intent_summary)
        payload = local_intent.get("payload")
        return QueueableSyncMutation(
            client_mutation_id=client_mutation_id,
            household_id=conflict.household_id,
            actor_id=actor_id,
            aggregate_type=SyncAggregateType(str(local_intent.get("aggregate_type") or conflict.aggregate_type)),
            aggregate_id=str(local_intent.get("aggregate_id") or conflict.aggregate_id),
            provisional_aggregate_id=(
                str(local_intent["provisional_aggregate_id"])
                if local_intent.get("provisional_aggregate_id") is not None
                else None
            ),
            mutation_type=str(local_intent.get("mutation_type") or conflict.mutation_type),
            payload=payload if isinstance(payload, dict) else {},
            base_server_version=base_server_version,
            device_timestamp=_utcnow(),
            local_queue_status=SyncMutationState.resolving,
        )

    def _mark_sync_conflict_resolved(
        self,
        conflict: GrocerySyncConflict,
        *,
        action: SyncResolutionAction,
        actor_id: str,
        resolution_client_mutation_id: str,
        resolved_at: datetime,
        context: SyncMutationContext,
        base_server_version: int | None,
    ) -> None:
        resolution_status = (
            SyncResolutionStatus.resolved_keep_mine
            if action == SyncResolutionAction.keep_mine
            else SyncResolutionStatus.resolved_use_server
        )
        local_queue_status = (
            SyncMutationState.resolved_keep_mine
            if action == SyncResolutionAction.keep_mine
            else SyncMutationState.resolved_use_server
        )
        conflict.requires_review = False
        conflict.allowed_resolution_actions = json.dumps([])
        conflict.resolution_status = resolution_status.value
        conflict.local_queue_status = local_queue_status.value
        conflict.current_server_version = context.current_version.version_number
        conflict.server_state_summary = json.dumps(
            self._sync_server_state_summary(
                context.grocery_list,
                context.current_version,
                context.current_item,
            )
        )
        conflict.resolved_at = resolved_at
        conflict.resolved_by_actor_id = actor_id

        local_intent = self._parse_json_dict(conflict.local_intent_summary)
        local_intent["resolution"] = {
            "action": action.value,
            "client_mutation_id": resolution_client_mutation_id,
            "base_server_version": base_server_version,
            "resolved_at": resolved_at.isoformat(),
        }
        conflict.local_intent_summary = json.dumps(local_intent)
        self._log_mutation(
            mutation_kind=f"sync_resolution_{action.value}",
            outcome=resolution_status.value,
            household_id=conflict.household_id,
            actor_id=actor_id,
            grocery_list_id=conflict.grocery_list_id,
            grocery_list_item_id=context.current_item.id if context.current_item is not None else None,
            grocery_list_version_id=context.current_version.id,
            client_mutation_id=resolution_client_mutation_id,
            aggregate_type=conflict.aggregate_type,
            aggregate_id=conflict.aggregate_id,
            aggregate_version=context.current_version.version_number,
            conflict_id=conflict.id,
            base_server_version=base_server_version,
            current_server_version=context.current_version.version_number,
            summary=conflict.summary,
            resolution_action=action.value,
        )

    @staticmethod
    def _resolution_result(result: GroceryMutationResult, *, mutation_kind: str) -> GroceryMutationResult:
        return result.model_copy(update={"mutation_kind": mutation_kind})

    def _sync_local_intent_summary(self, mutation: QueueableSyncMutation) -> dict[str, Any]:
        return {
            "client_mutation_id": mutation.client_mutation_id,
            "mutation_type": mutation.mutation_type,
            "aggregate_type": mutation.aggregate_type.value,
            "aggregate_id": mutation.aggregate_id,
            "provisional_aggregate_id": mutation.provisional_aggregate_id,
            "base_server_version": mutation.base_server_version,
            "payload": mutation.payload,
            "device_timestamp": mutation.device_timestamp.isoformat(),
        }

    def _sync_base_state_summary(
        self,
        session: Session,
        grocery_list: GroceryList,
        *,
        aggregate_type: SyncAggregateType,
        aggregate_id: str,
        base_server_version: int | None,
    ) -> dict[str, Any]:
        if base_server_version is None:
            return {}
        stmt = select(GroceryListVersion).where(
            GroceryListVersion.grocery_list_id == grocery_list.id,
            GroceryListVersion.version_number == base_server_version,
        )
        base_version = session.scalar(stmt)
        if base_version is None:
            return {}
        if aggregate_type == SyncAggregateType.grocery_list:
            return self._sync_list_state_summary(grocery_list, base_version)
        base_item = session.scalar(
            select(GroceryListItem).where(
                GroceryListItem.grocery_list_id == grocery_list.id,
                GroceryListItem.grocery_list_version_id == base_version.id,
                GroceryListItem.stable_line_id == aggregate_id,
            )
        )
        return self._sync_item_state_summary(base_item) if base_item is not None else {}

    def _sync_server_state_summary(
        self,
        grocery_list: GroceryList,
        current_version: GroceryListVersion,
        current_item: GroceryListItem | None,
    ) -> dict[str, Any]:
        if current_item is not None:
            return self._sync_item_state_summary(current_item)
        return self._sync_list_state_summary(grocery_list, current_version)

    def _sync_list_state_summary(
        self,
        grocery_list: GroceryList,
        version: GroceryListVersion,
    ) -> dict[str, Any]:
        return {
            "grocery_list_id": grocery_list.id,
            "grocery_list_version_id": version.id,
            "current_version_number": version.version_number,
            "status": grocery_list.status,
            "trip_state": grocery_list.trip_state,
            "confirmed_plan_version": version.confirmed_plan_version,
        }

    def _sync_item_state_summary(self, item: GroceryListItem) -> dict[str, Any]:
        return {
            "grocery_line_id": item.stable_line_id,
            "ingredient_name": item.ingredient_name,
            "active": item.active,
            "shopping_quantity": str(item.shopping_quantity),
            "user_adjusted_quantity": (
                str(item.user_adjusted_quantity) if item.user_adjusted_quantity is not None else None
            ),
            "user_adjustment_note": item.user_adjustment_note,
            "user_adjustment_flagged": item.user_adjustment_flagged,
            "ad_hoc_note": item.ad_hoc_note,
            "removed_at": item.removed_at.isoformat() if item.removed_at is not None else None,
            "is_purchased": item.is_purchased,
            "origin": item.origin,
            "unit": item.unit,
        }

    def _parse_json_dict(self, payload: str | None) -> dict[str, Any]:
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _parse_json_list(self, payload: str | None) -> list[Any]:
        if not payload:
            return []
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def _sync_conflict_to_summary(self, conflict: GrocerySyncConflict) -> SyncConflictSummaryRead:
        return SyncConflictSummaryRead(
            conflict_id=conflict.id,
            household_id=conflict.household_id,
            aggregate=SyncAggregateRef(
                aggregate_type=SyncAggregateType(conflict.aggregate_type),
                aggregate_id=conflict.aggregate_id,
                aggregate_version=conflict.current_server_version,
            ),
            local_mutation_id=conflict.local_mutation_id,
            mutation_type=conflict.mutation_type,
            outcome=SyncOutcome(conflict.outcome),
            base_server_version=conflict.base_server_version,
            current_server_version=conflict.current_server_version,
            requires_review=conflict.requires_review,
            summary=conflict.summary,
            local_queue_status=SyncMutationState(conflict.local_queue_status),
            allowed_resolution_actions=[
                SyncResolutionAction(action)
                for action in self._parse_json_list(conflict.allowed_resolution_actions)
            ],
            resolution_status=SyncResolutionStatus(conflict.resolution_status),
            created_at=conflict.created_at,
            resolved_at=conflict.resolved_at,
            resolved_by_actor_id=conflict.resolved_by_actor_id,
        )

    def _sync_conflict_to_detail(self, conflict: GrocerySyncConflict) -> SyncConflictDetailRead:
        summary = self._sync_conflict_to_summary(conflict)
        return SyncConflictDetailRead(
            **summary.model_dump(),
            local_intent_summary=self._parse_json_dict(conflict.local_intent_summary),
            base_state_summary=self._parse_json_dict(conflict.base_state_summary),
            server_state_summary=self._parse_json_dict(conflict.server_state_summary),
        )

    def _sync_conflict_to_outcome(self, conflict: GrocerySyncConflict) -> SyncMutationOutcomeRead:
        return SyncMutationOutcomeRead(
            client_mutation_id=conflict.local_mutation_id,
            mutation_type=conflict.mutation_type,
            aggregate=SyncAggregateRef(
                aggregate_type=SyncAggregateType(conflict.aggregate_type),
                aggregate_id=conflict.aggregate_id,
                aggregate_version=conflict.current_server_version,
            ),
            outcome=SyncOutcome(conflict.outcome),
            authoritative_server_version=conflict.current_server_version,
            conflict_id=conflict.id,
            retryable=False,
            duplicate_of_client_mutation_id=None,
            auto_merge_reason=None,
        )

    def _pending_plan_confirmed_events(self, session: Session, household_id: str) -> list[PlannerEvent]:
        stmt = (
            select(PlannerEvent)
            .where(PlannerEvent.household_id == household_id)
            .where(PlannerEvent.event_type == "plan_confirmed")
            .where(PlannerEvent.published_at.is_(None))
            .order_by(PlannerEvent.occurred_at.asc(), PlannerEvent.id.asc())
        )
        return session.scalars(stmt).all()

    def _draft_lists_for_household(self, session: Session, household_id: str) -> list[GroceryList]:
        stmt = (
            select(GroceryList)
            .where(GroceryList.household_id == household_id)
            .where(
                GroceryList.status.in_(
                    [
                        GroceryListStatus.draft.value,
                        GroceryListStatus.stale_draft.value,
                    ]
                )
            )
            .order_by(GroceryList.updated_at.desc(), GroceryList.created_at.desc(), GroceryList.id.desc())
        )
        return session.scalars(stmt).all()

    def _apply_plan_confirmed_event(
        self,
        session: Session,
        *,
        event_model: PlannerEvent,
        payload: PlanConfirmedEvent,
        actor_id: str,
    ) -> None:
        plan = session.get(MealPlan, payload.grocery_refresh_trigger.confirmed_plan_id)
        if plan is None or plan.status != MealPlanStatus.confirmed.value:
            return

        destination_list = self._choose_list_for_derivation(session, payload.household_id, plan)
        self._derive_into_list(
            session,
            household_id=payload.household_id,
            actor_id=actor_id,
            plan=plan,
            grocery_list=destination_list,
            mutation_kind="auto_refresh",
            client_mutation_id=payload.confirmation_client_mutation_id,
            correlation_id=payload.correlation_id,
        )
        event_model.published_at = _utcnow()

    def _store_receipt(
        self,
        session: Session,
        *,
        household_id: str,
        client_mutation_id: str,
        mutation_kind: str,
        result: GroceryMutationResult,
        accepted_at: datetime,
    ) -> None:
        session.add(
            GroceryMutationReceipt(
                household_id=household_id,
                grocery_list_id=result.grocery_list.id,
                grocery_list_item_id=result.item.id if result.item is not None else None,
                client_mutation_id=client_mutation_id,
                mutation_kind=mutation_kind,
                accepted_at=accepted_at,
                result_summary=json.dumps(result.model_dump(mode="json")),
            )
        )

    def _ensure_household_exists(self, session: Session, household_id: str) -> None:
        if session.get(Household, household_id) is not None:
            return
        now = _utcnow()
        session.add(
            Household(
                id=household_id,
                name=f"Household {household_id}",
                created_at=now,
                updated_at=now,
            )
        )

    def _log_mutation(
        self,
        *,
        mutation_kind: str,
        outcome: str,
        household_id: str,
        actor_id: str,
        grocery_list_id: str | None,
        client_mutation_id: str,
        grocery_list_item_id: str | None = None,
        grocery_list_version_id: str | None = None,
        correlation_id: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        aggregate_version: int | None = None,
        provisional_aggregate_id: str | None = None,
        conflict_id: str | None = None,
        base_server_version: int | None = None,
        current_server_version: int | None = None,
        summary: str | None = None,
        resolution_action: str | None = None,
        auto_merge_reason: str | None = None,
    ) -> None:
        level = (
            logging.INFO
            if outcome
            in {
                "accepted",
                "duplicate",
                SyncOutcome.duplicate_retry.value,
                SyncOutcome.auto_merged_non_overlapping.value,
                SyncResolutionStatus.resolved_keep_mine.value,
                SyncResolutionStatus.resolved_use_server.value,
            }
            else logging.WARNING
        )
        extra = {
            "grocery_action": mutation_kind,
            "grocery_outcome": outcome,
            "grocery_household_id": household_id,
            "grocery_actor_id": actor_id,
            "grocery_list_id": grocery_list_id,
            "grocery_list_version_id": grocery_list_version_id,
            "grocery_list_item_id": grocery_list_item_id,
            "grocery_client_mutation_id": client_mutation_id,
            "grocery_correlation_id": correlation_id or client_mutation_id,
        }
        if aggregate_type is not None:
            extra["grocery_aggregate_type"] = aggregate_type
        if aggregate_id is not None:
            extra["grocery_aggregate_id"] = aggregate_id
        if aggregate_version is not None:
            extra["grocery_aggregate_version"] = aggregate_version
        if provisional_aggregate_id is not None:
            extra["grocery_provisional_aggregate_id"] = provisional_aggregate_id
        if conflict_id is not None:
            extra["grocery_conflict_id"] = conflict_id
        if base_server_version is not None:
            extra["grocery_base_server_version"] = base_server_version
        if current_server_version is not None:
            extra["grocery_current_server_version"] = current_server_version
        if summary is not None:
            extra["grocery_sync_summary"] = summary
        if resolution_action is not None:
            extra["grocery_resolution_action"] = resolution_action
        if auto_merge_reason is not None:
            extra["grocery_auto_merge_reason"] = auto_merge_reason
        logger.log(
            level,
            "grocery mutation %s",
            outcome,
            extra=extra,
        )

    def _log_derivation(
        self,
        *,
        household_id: str,
        actor_id: str,
        grocery_list_id: str,
        grocery_list_version_id: str,
        plan_id: str,
        mutation_kind: str,
        client_mutation_id: str,
        correlation_id: str,
        raw_need_count: int,
        offset_need_count: int,
        consolidated_line_count: int,
        incomplete_slot_count: int,
        unmatched_need_count: int,
        inventory_snapshot_reference: str,
        confirmed_plan_version: int,
    ) -> None:
        logger.info(
            "grocery derivation accepted",
            extra={
                "grocery_action": mutation_kind,
                "grocery_outcome": "accepted",
                "grocery_household_id": household_id,
                "grocery_actor_id": actor_id,
                "grocery_list_id": grocery_list_id,
                "grocery_list_version_id": grocery_list_version_id,
                "grocery_plan_id": plan_id,
                "grocery_client_mutation_id": client_mutation_id,
                "grocery_correlation_id": correlation_id,
                "grocery_raw_need_count": raw_need_count,
                "grocery_offset_need_count": offset_need_count,
                "grocery_consolidated_line_count": consolidated_line_count,
                "grocery_incomplete_slot_count": incomplete_slot_count,
                "grocery_unmatched_need_count": unmatched_need_count,
                "grocery_inventory_snapshot_reference": inventory_snapshot_reference,
                "grocery_confirmed_plan_version": confirmed_plan_version,
            },
        )

    def _log_incomplete_slots(
        self,
        *,
        household_id: str,
        actor_id: str,
        grocery_list_id: str,
        grocery_list_version_id: str,
        client_mutation_id: str,
        correlation_id: str,
        warnings: list[GroceryIncompleteSlotWarningRead],
    ) -> None:
        if not warnings:
            return
        logger.warning(
            "grocery derivation incomplete slots detected",
            extra={
                "grocery_action": "derivation_incomplete_slots",
                "grocery_outcome": "warning",
                "grocery_household_id": household_id,
                "grocery_actor_id": actor_id,
                "grocery_list_id": grocery_list_id,
                "grocery_list_version_id": grocery_list_version_id,
                "grocery_client_mutation_id": client_mutation_id,
                "grocery_correlation_id": correlation_id,
                "grocery_incomplete_slot_count": len(warnings),
                "grocery_incomplete_slot_ids": [warning.meal_slot_id for warning in warnings],
            },
        )

    def _log_stale_transition(
        self,
        *,
        household_id: str,
        actor_id: str | None,
        grocery_list_id: str,
        grocery_list_version_id: str | None,
        previous_status: str,
        current_status: str,
        stale_reason: str | None,
        correlation_id: str | None,
    ) -> None:
        logger.info(
            "grocery stale status changed",
            extra={
                "grocery_action": "stale_detection",
                "grocery_outcome": "detected" if stale_reason is not None else "cleared",
                "grocery_household_id": household_id,
                "grocery_actor_id": actor_id,
                "grocery_list_id": grocery_list_id,
                "grocery_list_version_id": grocery_list_version_id,
                "grocery_previous_status": previous_status,
                "grocery_current_status": current_status,
                "grocery_stale_reason": stale_reason,
                "grocery_correlation_id": correlation_id,
            },
        )

    def _log_confirmation(
        self,
        *,
        household_id: str,
        actor_id: str,
        grocery_list_id: str,
        grocery_list_version_id: str,
        client_mutation_id: str,
        confirmed_at: datetime,
    ) -> None:
        logger.info(
            "grocery list confirmed",
            extra={
                "grocery_action": "confirm_list",
                "grocery_outcome": "accepted",
                "grocery_household_id": household_id,
                "grocery_actor_id": actor_id,
                "grocery_list_id": grocery_list_id,
                "grocery_list_version_id": grocery_list_version_id,
                "grocery_client_mutation_id": client_mutation_id,
                "grocery_correlation_id": client_mutation_id,
                "grocery_confirmed_at": confirmed_at.isoformat(),
            },
        )


_default_service = GroceryService.for_default_app()


def get_grocery_service() -> GroceryService:
    return _default_service
