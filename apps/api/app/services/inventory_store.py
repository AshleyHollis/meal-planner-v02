"""
SQL-backed inventory store for Wave 1.

The inventory router still talks to a narrow service interface, but the backing
implementation is now authoritative SQL persistence. Each accepted mutation
commits the inventory item update, the append-only adjustment record, and the
idempotency receipt in the same transaction.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import app.models  # noqa: F401
from sqlalchemy import Engine, URL, create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.household import Household
from app.models.inventory import (
    InventoryAdjustment as InventoryAdjustmentModel,
    InventoryItem as InventoryItemModel,
    MutationReceipt as MutationReceiptModel,
)
from app.schemas.enums import FreshnessBasis, MutationType, ReasonCode, StorageLocation
from app.schemas.inventory import (
    AdjustQuantityCommand,
    AdjustmentReceiptResponse,
    ArchiveItemCommand,
    CorrectionCommand,
    CreateItemCommand,
    FreshnessInfo,
    InventoryAdjustment,
    InventoryCorrectionLinks,
    InventoryFreshnessTransition,
    InventoryHistoryResponse,
    InventoryHistorySummary,
    InventoryItem,
    InventoryLocationTransition,
    InventoryQuantityTransition,
    InventoryWorkflowReference,
    MoveLocationCommand,
    SetMetadataCommand,
)
from app.services.local_db_compat import resolve_local_db_path

_QUANTITY_SCALE = Decimal("0.0001")
logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _to_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(_QUANTITY_SCALE)


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


class InventoryConflictError(Exception):
    def __init__(self, *, expected_version: int, current_version: int) -> None:
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"Stale inventory mutation: expected version {expected_version}, current version is {current_version}"
        )


class InventoryDomainError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class InventoryStore:
    """
    SQL-backed inventory service.

    `InventoryStore()` defaults to an isolated in-memory SQLite database so the
    API tests can still inject a fresh store per test. The app singleton uses a
    file-backed SQLite database so state survives process restarts in dev.
    """

    def __init__(self, database_url: str | URL | None = None) -> None:
        self._engine = self._create_engine(database_url)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @classmethod
    def for_default_app(cls) -> InventoryStore:
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
            if isinstance(database_url, URL):
                db_url = database_url
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

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_items(
        self,
        household_id: str,
        include_archived: bool = False,
    ) -> list[InventoryItem]:
        with self._session_factory() as session:
            stmt = select(InventoryItemModel).where(InventoryItemModel.household_id == household_id)
            if not include_archived:
                stmt = stmt.where(InventoryItemModel.is_active.is_(True))
            stmt = stmt.order_by(InventoryItemModel.created_at.asc(), InventoryItemModel.id.asc())
            items = session.scalars(stmt).all()
            return [self._item_to_schema(item) for item in items]

    def get_item(self, household_id: str, item_id: str) -> InventoryItem | None:
        with self._session_factory() as session:
            item = self._get_item_model(session, household_id, item_id)
            if item is None:
                return None
            summary = self._history_summary(session, household_id, item_id)
            latest = self._latest_adjustment_model(session, household_id, item_id)
            corrected_by_map = self._corrected_by_map(
                session,
                [latest.id] if latest is not None else [],
            )
            return self._item_to_schema(
                item,
                history_summary=summary,
                latest_adjustment=(
                    self._adjustment_to_schema(
                        latest,
                        primary_unit=item.primary_unit,
                        corrected_by_adjustment_ids=corrected_by_map.get(latest.id, []),
                    )
                    if latest is not None
                    else None
                ),
            )

    def get_history(
        self,
        household_id: str,
        item_id: str,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> InventoryHistoryResponse:
        with self._session_factory() as session:
            item = self._get_item_model(session, household_id, item_id)
            if item is None:
                raise InventoryDomainError(
                    code="inventory_item_not_found",
                    message="Inventory item not found",
                )
            total = self._history_total(session, household_id, item_id)
            summary = self._history_summary(session, household_id, item_id)
            stmt = (
                select(InventoryAdjustmentModel)
                .where(
                    InventoryAdjustmentModel.household_id == household_id,
                    InventoryAdjustmentModel.inventory_item_id == item_id,
                )
                .order_by(InventoryAdjustmentModel.created_at.desc(), InventoryAdjustmentModel.id.desc())
                .offset(offset)
                .limit(limit)
            )
            adjustments = session.scalars(stmt).all()
            corrected_by_map = self._corrected_by_map(session, [adjustment.id for adjustment in adjustments])
            entries = [
                self._adjustment_to_schema(
                    adjustment,
                    primary_unit=item.primary_unit,
                    corrected_by_adjustment_ids=corrected_by_map.get(adjustment.id, []),
                )
                for adjustment in adjustments
            ]
            return InventoryHistoryResponse(
                entries=entries,
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(entries)) < total,
                summary=summary,
            )

    def _check_version(self, item: InventoryItemModel, expected_version: int | None) -> None:
        if expected_version is not None and expected_version != item.version:
            raise InventoryConflictError(
                expected_version=expected_version,
                current_version=item.version,
            )

    def _ensure_non_negative_quantity(self, after: Decimal, *, mutation_type: MutationType) -> None:
        if after < 0:
            raise InventoryDomainError(
                code="negative_quantity_not_allowed",
                message=f"{mutation_type.value} cannot commit a negative inventory quantity",
            )

    def _get_item_model(
        self,
        session: Session,
        household_id: str,
        item_id: str,
    ) -> InventoryItemModel | None:
        stmt = select(InventoryItemModel).where(
            InventoryItemModel.id == item_id,
            InventoryItemModel.household_id == household_id,
        )
        return session.scalar(stmt)

    def _get_adjustment_model(
        self,
        session: Session,
        household_id: str,
        item_id: str,
        adjustment_id: str,
    ) -> InventoryAdjustmentModel | None:
        stmt = select(InventoryAdjustmentModel).where(
            InventoryAdjustmentModel.id == adjustment_id,
            InventoryAdjustmentModel.household_id == household_id,
            InventoryAdjustmentModel.inventory_item_id == item_id,
        )
        return session.scalar(stmt)

    def _get_receipt(
        self,
        session: Session,
        household_id: str,
        client_mutation_id: str,
        *,
        mark_duplicate: bool = True,
    ) -> AdjustmentReceiptResponse | None:
        stmt = select(MutationReceiptModel).where(
            MutationReceiptModel.household_id == household_id,
            MutationReceiptModel.client_mutation_id == client_mutation_id,
        )
        receipt = session.scalar(stmt)
        if receipt is None:
            return None

        parsed = self._receipt_model_from_record(receipt)
        if mark_duplicate:
            return parsed.model_copy(update={"is_duplicate": True})
        return parsed

    def _history_total(self, session: Session, household_id: str, item_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(InventoryAdjustmentModel)
            .where(
                InventoryAdjustmentModel.household_id == household_id,
                InventoryAdjustmentModel.inventory_item_id == item_id,
            )
        )
        return int(session.scalar(stmt) or 0)

    def _latest_adjustment_model(
        self,
        session: Session,
        household_id: str,
        item_id: str,
    ) -> InventoryAdjustmentModel | None:
        stmt = (
            select(InventoryAdjustmentModel)
            .where(
                InventoryAdjustmentModel.household_id == household_id,
                InventoryAdjustmentModel.inventory_item_id == item_id,
            )
            .order_by(InventoryAdjustmentModel.created_at.desc(), InventoryAdjustmentModel.id.desc())
            .limit(1)
        )
        return session.scalar(stmt)

    def _history_summary(
        self,
        session: Session,
        household_id: str,
        item_id: str,
    ) -> InventoryHistorySummary:
        total = self._history_total(session, household_id, item_id)
        correction_stmt = (
            select(func.count())
            .select_from(InventoryAdjustmentModel)
            .where(
                InventoryAdjustmentModel.household_id == household_id,
                InventoryAdjustmentModel.inventory_item_id == item_id,
                InventoryAdjustmentModel.mutation_type == MutationType.correction.value,
            )
        )
        correction_count = int(session.scalar(correction_stmt) or 0)
        latest = self._latest_adjustment_model(session, household_id, item_id)
        return InventoryHistorySummary(
            committed_adjustment_count=total,
            correction_count=correction_count,
            latest_adjustment_id=latest.id if latest is not None else None,
            latest_mutation_type=(
                MutationType(latest.mutation_type) if latest is not None else None
            ),
            latest_actor_user_id=latest.actor_id if latest is not None else None,
            latest_created_at=latest.created_at if latest is not None else None,
        )

    def _corrected_by_map(
        self,
        session: Session,
        adjustment_ids: list[str],
    ) -> dict[str, list[str]]:
        if not adjustment_ids:
            return {}
        rows = session.execute(
            select(
                InventoryAdjustmentModel.corrects_adjustment_id,
                InventoryAdjustmentModel.id,
            ).where(InventoryAdjustmentModel.corrects_adjustment_id.in_(adjustment_ids))
        ).all()
        corrected_by: dict[str, list[str]] = {adjustment_id: [] for adjustment_id in adjustment_ids}
        for target_id, correction_id in rows:
            if target_id is None:
                continue
            corrected_by.setdefault(target_id, []).append(correction_id)
        for linked_ids in corrected_by.values():
            linked_ids.sort()
        return corrected_by

    def _store_receipt(
        self,
        session: Session,
        household_id: str,
        client_mutation_id: str,
        receipt: AdjustmentReceiptResponse,
        accepted_at: datetime,
    ) -> None:
        record = MutationReceiptModel(
            household_id=household_id,
            client_mutation_id=client_mutation_id,
            accepted_at=accepted_at,
            result_summary=json.dumps(
                {
                    "inventory_adjustment_id": receipt.inventory_adjustment_id,
                    "inventory_item_id": receipt.inventory_item_id,
                    "mutation_type": receipt.mutation_type.value,
                    "quantity_after": receipt.quantity_after,
                    "version_after": receipt.version_after,
                }
            ),
            inventory_adjustment_id=receipt.inventory_adjustment_id,
        )
        session.add(record)

    def _log_mutation(
        self,
        *,
        outcome: str,
        household_id: str,
        client_mutation_id: str | None,
        mutation_type: MutationType | str | None,
        actor_user_id: str | None,
        inventory_item_id: str | None = None,
        inventory_adjustment_id: str | None = None,
        version_after: int | None = None,
        quantity_after: float | None = None,
        expected_version: int | None = None,
        current_version: int | None = None,
        correlation_id: str | None = None,
        corrects_adjustment_id: str | None = None,
    ) -> None:
        level = logging.INFO if outcome in {"accepted", "duplicate"} else logging.WARNING
        resolved_mutation_type = (
            mutation_type.value if isinstance(mutation_type, MutationType) else mutation_type
        )
        logger.log(
            level,
            "inventory mutation %s",
            outcome,
            extra={
                "inventory_outcome": outcome,
                "inventory_household_id": household_id,
                "inventory_client_mutation_id": client_mutation_id,
                "inventory_mutation_type": resolved_mutation_type,
                "inventory_actor_user_id": actor_user_id,
                "inventory_item_id": inventory_item_id,
                "inventory_adjustment_id": inventory_adjustment_id,
                "inventory_version_after": version_after,
                "inventory_quantity_after": quantity_after,
                "inventory_expected_version": expected_version,
                "inventory_current_version": current_version,
                "inventory_correlation_id": correlation_id,
                "inventory_corrects_adjustment_id": corrects_adjustment_id,
            },
        )

    def _ensure_household_exists(self, session: Session, household_id: str) -> None:
        household = session.get(Household, household_id)
        if household is not None:
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

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def create_item(
        self,
        command: CreateItemCommand,
        actor_user_id: str,
        correlation_id: str | None = None,
    ) -> AdjustmentReceiptResponse:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, command.household_id, command.client_mutation_id):
                    self._log_mutation(
                        outcome="duplicate",
                        household_id=command.household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=existing.mutation_type,
                        actor_user_id=actor_user_id,
                        inventory_item_id=existing.inventory_item_id,
                        inventory_adjustment_id=existing.inventory_adjustment_id,
                        version_after=existing.version_after,
                        quantity_after=existing.quantity_after,
                        correlation_id=correlation_id,
                    )
                    return existing

                self._ensure_household_exists(session, command.household_id)

                now = _utcnow()
                item = InventoryItemModel(
                    household_id=command.household_id,
                    name=command.name,
                    storage_location=command.storage_location.value,
                    quantity_on_hand=_to_decimal(command.initial_quantity) or Decimal("0"),
                    primary_unit=command.primary_unit,
                    is_active=True,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                self._apply_freshness_to_item(item, command.freshness, at=now)
                session.add(item)
                session.flush()

                adjustment = InventoryAdjustmentModel(
                    inventory_item_id=item.id,
                    household_id=command.household_id,
                    mutation_type=MutationType.create_item.value,
                    delta_quantity=_to_decimal(command.initial_quantity),
                    quantity_before=Decimal("0.0000"),
                    quantity_after=item.quantity_on_hand,
                    storage_location_after=item.storage_location,
                    reason_code=ReasonCode.manual_create.value,
                    actor_id=actor_user_id,
                    correlation_id=correlation_id,
                    client_mutation_id=command.client_mutation_id,
                    notes=command.note,
                    created_at=now,
                )
                self._apply_freshness_snapshot(
                    adjustment,
                    prefix="after",
                    freshness=command.freshness,
                )
                session.add(adjustment)
                session.flush()

                receipt = AdjustmentReceiptResponse(
                    inventory_adjustment_id=adjustment.id,
                    inventory_item_id=item.id,
                    mutation_type=MutationType.create_item,
                    quantity_after=_to_float(item.quantity_on_hand),
                    version_after=item.version,
                )
                self._store_receipt(
                    session,
                    command.household_id,
                    command.client_mutation_id,
                    receipt,
                    accepted_at=now,
                )
                self._log_mutation(
                    outcome="accepted",
                    household_id=command.household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_type=receipt.mutation_type,
                    actor_user_id=actor_user_id,
                    inventory_item_id=item.id,
                    inventory_adjustment_id=adjustment.id,
                    version_after=item.version,
                    quantity_after=receipt.quantity_after,
                    correlation_id=correlation_id,
                )
                return receipt

    def adjust_quantity(
        self,
        household_id: str,
        item_id: str,
        command: AdjustQuantityCommand,
        actor_user_id: str,
        correlation_id: str | None = None,
    ) -> AdjustmentReceiptResponse | None:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        outcome="duplicate",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=existing.mutation_type,
                        actor_user_id=actor_user_id,
                        inventory_item_id=existing.inventory_item_id,
                        inventory_adjustment_id=existing.inventory_adjustment_id,
                        version_after=existing.version_after,
                        quantity_after=existing.quantity_after,
                        correlation_id=correlation_id,
                    )
                    return existing

                item = self._get_item_model(session, household_id, item_id)
                if item is None:
                    return None
                try:
                    self._check_version(item, command.version)
                except InventoryConflictError as error:
                    self._log_mutation(
                        outcome="conflict",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=command.mutation_type,
                        actor_user_id=actor_user_id,
                        inventory_item_id=item.id,
                        expected_version=error.expected_version,
                        current_version=error.current_version,
                        correlation_id=correlation_id,
                    )
                    raise

                allowed = {
                    MutationType.increase_quantity,
                    MutationType.decrease_quantity,
                    MutationType.set_quantity,
                }
                if command.mutation_type not in allowed:
                    raise ValueError(f"adjust_quantity does not accept {command.mutation_type}")

                now = _utcnow()
                before = item.quantity_on_hand
                delta = _to_decimal(command.delta_quantity) or Decimal("0")

                if command.mutation_type == MutationType.increase_quantity:
                    after = before + delta
                elif command.mutation_type == MutationType.decrease_quantity:
                    after = before - delta
                else:
                    after = delta
                self._ensure_non_negative_quantity(after, mutation_type=command.mutation_type)

                item.quantity_on_hand = after
                item.version += 1
                item.updated_at = now
                session.flush()

                adjustment = InventoryAdjustmentModel(
                    inventory_item_id=item.id,
                    household_id=household_id,
                    mutation_type=command.mutation_type.value,
                    delta_quantity=delta,
                    quantity_before=before,
                    quantity_after=after,
                    reason_code=command.reason_code.value,
                    actor_id=actor_user_id,
                    correlation_id=correlation_id,
                    client_mutation_id=command.client_mutation_id,
                    notes=command.note,
                    created_at=now,
                )
                session.add(adjustment)
                session.flush()

                receipt = AdjustmentReceiptResponse(
                    inventory_adjustment_id=adjustment.id,
                    inventory_item_id=item.id,
                    mutation_type=command.mutation_type,
                    quantity_after=_to_float(after),
                    version_after=item.version,
                )
                self._store_receipt(
                    session,
                    household_id,
                    command.client_mutation_id,
                    receipt,
                    accepted_at=now,
                )
                self._log_mutation(
                    outcome="accepted",
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_type=receipt.mutation_type,
                    actor_user_id=actor_user_id,
                    inventory_item_id=item.id,
                    inventory_adjustment_id=adjustment.id,
                    version_after=item.version,
                    quantity_after=receipt.quantity_after,
                    correlation_id=correlation_id,
                )
                return receipt

    def set_metadata(
        self,
        household_id: str,
        item_id: str,
        command: SetMetadataCommand,
        actor_user_id: str,
        correlation_id: str | None = None,
    ) -> AdjustmentReceiptResponse | None:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        outcome="duplicate",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=existing.mutation_type,
                        actor_user_id=actor_user_id,
                        inventory_item_id=existing.inventory_item_id,
                        inventory_adjustment_id=existing.inventory_adjustment_id,
                        version_after=existing.version_after,
                        quantity_after=existing.quantity_after,
                        correlation_id=correlation_id,
                    )
                    return existing

                item = self._get_item_model(session, household_id, item_id)
                if item is None:
                    return None
                try:
                    self._check_version(item, command.version)
                except InventoryConflictError as error:
                    self._log_mutation(
                        outcome="conflict",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=MutationType.set_metadata,
                        actor_user_id=actor_user_id,
                        inventory_item_id=item.id,
                        expected_version=error.expected_version,
                        current_version=error.current_version,
                        correlation_id=correlation_id,
                    )
                    raise

                now = _utcnow()
                before_location = item.storage_location
                before_freshness = self._freshness_from_item(item)

                if command.name is not None:
                    item.name = command.name
                if command.storage_location is not None:
                    item.storage_location = command.storage_location.value
                if command.freshness is not None:
                    self._apply_freshness_to_item(item, command.freshness, at=now)
                item.version += 1
                item.updated_at = now
                session.flush()

                adjustment = InventoryAdjustmentModel(
                    inventory_item_id=item.id,
                    household_id=household_id,
                    mutation_type=MutationType.set_metadata.value,
                    storage_location_before=before_location,
                    storage_location_after=item.storage_location,
                    reason_code=ReasonCode.manual_edit.value,
                    actor_id=actor_user_id,
                    correlation_id=correlation_id,
                    client_mutation_id=command.client_mutation_id,
                    notes=command.note,
                    created_at=now,
                )
                self._apply_freshness_snapshot(
                    adjustment,
                    prefix="before",
                    freshness=before_freshness,
                )
                self._apply_freshness_snapshot(
                    adjustment,
                    prefix="after",
                    freshness=self._freshness_from_item(item),
                )
                session.add(adjustment)
                session.flush()

                receipt = AdjustmentReceiptResponse(
                    inventory_adjustment_id=adjustment.id,
                    inventory_item_id=item.id,
                    mutation_type=MutationType.set_metadata,
                    quantity_after=_to_float(item.quantity_on_hand),
                    version_after=item.version,
                )
                self._store_receipt(
                    session,
                    household_id,
                    command.client_mutation_id,
                    receipt,
                    accepted_at=now,
                )
                self._log_mutation(
                    outcome="accepted",
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_type=receipt.mutation_type,
                    actor_user_id=actor_user_id,
                    inventory_item_id=item.id,
                    inventory_adjustment_id=adjustment.id,
                    version_after=item.version,
                    quantity_after=receipt.quantity_after,
                    correlation_id=correlation_id,
                )
                return receipt

    def move_location(
        self,
        household_id: str,
        item_id: str,
        command: MoveLocationCommand,
        actor_user_id: str,
        correlation_id: str | None = None,
    ) -> AdjustmentReceiptResponse | None:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        outcome="duplicate",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=existing.mutation_type,
                        actor_user_id=actor_user_id,
                        inventory_item_id=existing.inventory_item_id,
                        inventory_adjustment_id=existing.inventory_adjustment_id,
                        version_after=existing.version_after,
                        quantity_after=existing.quantity_after,
                        correlation_id=correlation_id,
                    )
                    return existing

                item = self._get_item_model(session, household_id, item_id)
                if item is None:
                    return None
                try:
                    self._check_version(item, command.version)
                except InventoryConflictError as error:
                    self._log_mutation(
                        outcome="conflict",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=MutationType.move_location,
                        actor_user_id=actor_user_id,
                        inventory_item_id=item.id,
                        expected_version=error.expected_version,
                        current_version=error.current_version,
                        correlation_id=correlation_id,
                    )
                    raise

                now = _utcnow()
                before_location = item.storage_location
                before_freshness = self._freshness_from_item(item)

                item.storage_location = command.storage_location.value
                if command.freshness is not None:
                    self._apply_freshness_to_item(item, command.freshness, at=now)
                item.version += 1
                item.updated_at = now
                session.flush()

                adjustment = InventoryAdjustmentModel(
                    inventory_item_id=item.id,
                    household_id=household_id,
                    mutation_type=MutationType.move_location.value,
                    storage_location_before=before_location,
                    storage_location_after=item.storage_location,
                    reason_code=ReasonCode.location_move.value,
                    actor_id=actor_user_id,
                    correlation_id=correlation_id,
                    client_mutation_id=command.client_mutation_id,
                    notes=command.note,
                    created_at=now,
                )
                self._apply_freshness_snapshot(
                    adjustment,
                    prefix="before",
                    freshness=before_freshness,
                )
                self._apply_freshness_snapshot(
                    adjustment,
                    prefix="after",
                    freshness=self._freshness_from_item(item),
                )
                session.add(adjustment)
                session.flush()

                receipt = AdjustmentReceiptResponse(
                    inventory_adjustment_id=adjustment.id,
                    inventory_item_id=item.id,
                    mutation_type=MutationType.move_location,
                    quantity_after=_to_float(item.quantity_on_hand),
                    version_after=item.version,
                )
                self._store_receipt(
                    session,
                    household_id,
                    command.client_mutation_id,
                    receipt,
                    accepted_at=now,
                )
                self._log_mutation(
                    outcome="accepted",
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_type=receipt.mutation_type,
                    actor_user_id=actor_user_id,
                    inventory_item_id=item.id,
                    inventory_adjustment_id=adjustment.id,
                    version_after=item.version,
                    quantity_after=receipt.quantity_after,
                    correlation_id=correlation_id,
                )
                return receipt

    def archive_item(
        self,
        household_id: str,
        item_id: str,
        command: ArchiveItemCommand,
        actor_user_id: str,
        correlation_id: str | None = None,
    ) -> AdjustmentReceiptResponse | None:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        outcome="duplicate",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=existing.mutation_type,
                        actor_user_id=actor_user_id,
                        inventory_item_id=existing.inventory_item_id,
                        inventory_adjustment_id=existing.inventory_adjustment_id,
                        version_after=existing.version_after,
                        quantity_after=existing.quantity_after,
                        correlation_id=correlation_id,
                    )
                    return existing

                item = self._get_item_model(session, household_id, item_id)
                if item is None:
                    return None
                try:
                    self._check_version(item, command.version)
                except InventoryConflictError as error:
                    self._log_mutation(
                        outcome="conflict",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=MutationType.archive_item,
                        actor_user_id=actor_user_id,
                        inventory_item_id=item.id,
                        expected_version=error.expected_version,
                        current_version=error.current_version,
                        correlation_id=correlation_id,
                    )
                    raise

                now = _utcnow()
                item.is_active = False
                item.version += 1
                item.updated_at = now
                session.flush()

                adjustment = InventoryAdjustmentModel(
                    inventory_item_id=item.id,
                    household_id=household_id,
                    mutation_type=MutationType.archive_item.value,
                    reason_code=ReasonCode.manual_edit.value,
                    actor_id=actor_user_id,
                    correlation_id=correlation_id,
                    client_mutation_id=command.client_mutation_id,
                    notes=command.note,
                    created_at=now,
                )
                session.add(adjustment)
                session.flush()

                receipt = AdjustmentReceiptResponse(
                    inventory_adjustment_id=adjustment.id,
                    inventory_item_id=item.id,
                    mutation_type=MutationType.archive_item,
                    quantity_after=_to_float(item.quantity_on_hand),
                    version_after=item.version,
                )
                self._store_receipt(
                    session,
                    household_id,
                    command.client_mutation_id,
                    receipt,
                    accepted_at=now,
                )
                self._log_mutation(
                    outcome="accepted",
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_type=receipt.mutation_type,
                    actor_user_id=actor_user_id,
                    inventory_item_id=item.id,
                    inventory_adjustment_id=adjustment.id,
                    version_after=item.version,
                    quantity_after=receipt.quantity_after,
                    correlation_id=correlation_id,
                )
                return receipt

    def apply_correction(
        self,
        household_id: str,
        item_id: str,
        command: CorrectionCommand,
        actor_user_id: str,
        correlation_id: str | None = None,
    ) -> AdjustmentReceiptResponse | None:
        with self._session_factory() as session:
            with session.begin():
                if existing := self._get_receipt(session, household_id, command.client_mutation_id):
                    self._log_mutation(
                        outcome="duplicate",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=existing.mutation_type,
                        actor_user_id=actor_user_id,
                        inventory_item_id=existing.inventory_item_id,
                        inventory_adjustment_id=existing.inventory_adjustment_id,
                        version_after=existing.version_after,
                        quantity_after=existing.quantity_after,
                        correlation_id=correlation_id,
                    )
                    return existing

                item = self._get_item_model(session, household_id, item_id)
                if item is None:
                    return None
                try:
                    self._check_version(item, command.version)
                except InventoryConflictError as error:
                    self._log_mutation(
                        outcome="conflict",
                        household_id=household_id,
                        client_mutation_id=command.client_mutation_id,
                        mutation_type=MutationType.correction,
                        actor_user_id=actor_user_id,
                        inventory_item_id=item.id,
                        expected_version=error.expected_version,
                        current_version=error.current_version,
                        correlation_id=correlation_id,
                        corrects_adjustment_id=command.corrects_adjustment_id,
                    )
                    raise

                correction_target = self._get_adjustment_model(
                    session,
                    household_id,
                    item.id,
                    command.corrects_adjustment_id,
                )
                if correction_target is None:
                    raise InventoryDomainError(
                        code="correction_target_not_found",
                        message="The correction must reference an existing adjustment on this household inventory item.",
                    )

                now = _utcnow()
                before = item.quantity_on_hand
                delta = _to_decimal(command.delta_quantity)
                after = before

                if delta is not None:
                    after = before + delta
                    self._ensure_non_negative_quantity(after, mutation_type=MutationType.correction)
                    item.quantity_on_hand = after
                    item.version += 1
                item.updated_at = now
                session.flush()

                adjustment = InventoryAdjustmentModel(
                    inventory_item_id=item.id,
                    household_id=household_id,
                    mutation_type=MutationType.correction.value,
                    delta_quantity=delta,
                    quantity_before=before if delta is not None else None,
                    quantity_after=after if delta is not None else None,
                    reason_code=command.reason_code.value,
                    actor_id=actor_user_id,
                    correlation_id=correlation_id,
                    client_mutation_id=command.client_mutation_id,
                    corrects_adjustment_id=command.corrects_adjustment_id,
                    notes=command.note,
                    created_at=now,
                )
                session.add(adjustment)
                session.flush()

                receipt = AdjustmentReceiptResponse(
                    inventory_adjustment_id=adjustment.id,
                    inventory_item_id=item.id,
                    mutation_type=MutationType.correction,
                    quantity_after=_to_float(item.quantity_on_hand),
                    version_after=item.version,
                )
                self._store_receipt(
                    session,
                    household_id,
                    command.client_mutation_id,
                    receipt,
                    accepted_at=now,
                )
                self._log_mutation(
                    outcome="accepted",
                    household_id=household_id,
                    client_mutation_id=command.client_mutation_id,
                    mutation_type=receipt.mutation_type,
                    actor_user_id=actor_user_id,
                    inventory_item_id=item.id,
                    inventory_adjustment_id=adjustment.id,
                    version_after=item.version,
                    quantity_after=receipt.quantity_after,
                    correlation_id=correlation_id,
                    corrects_adjustment_id=command.corrects_adjustment_id,
                )
                return receipt

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _apply_freshness_to_item(
        self,
        item: InventoryItemModel,
        freshness: FreshnessInfo,
        *,
        at: datetime,
    ) -> None:
        basis = freshness.basis.value
        item.freshness_basis = basis
        item.freshness_note = freshness.estimated_note if freshness.basis == FreshnessBasis.estimated else None
        item.expiry_date = None
        item.estimated_expiry_date = None

        if freshness.basis == FreshnessBasis.known:
            item.expiry_date = freshness.best_before.date() if freshness.best_before else None
        elif freshness.basis == FreshnessBasis.estimated:
            item.estimated_expiry_date = freshness.best_before.date() if freshness.best_before else None

        item.freshness_updated_at = at

    def _freshness_from_item(self, item: InventoryItemModel) -> FreshnessInfo:
        basis = FreshnessBasis(item.freshness_basis)
        if basis == FreshnessBasis.known:
            return FreshnessInfo(
                basis=basis,
                best_before=_date_to_datetime(item.expiry_date),
            )
        if basis == FreshnessBasis.estimated:
            return FreshnessInfo(
                basis=basis,
                best_before=_date_to_datetime(item.estimated_expiry_date),
                estimated_note=item.freshness_note,
            )
        return FreshnessInfo(basis=basis)

    def _apply_freshness_snapshot(
        self,
        adjustment: InventoryAdjustmentModel,
        *,
        prefix: str,
        freshness: FreshnessInfo | None,
    ) -> None:
        if freshness is None:
            setattr(adjustment, f"freshness_basis_{prefix}", None)
            setattr(adjustment, f"expiry_date_{prefix}", None)
            setattr(adjustment, f"estimated_expiry_date_{prefix}", None)
            return

        setattr(adjustment, f"freshness_basis_{prefix}", freshness.basis.value)
        setattr(adjustment, f"expiry_date_{prefix}", None)
        setattr(adjustment, f"estimated_expiry_date_{prefix}", None)

        if freshness.best_before is None:
            return

        best_before_date = freshness.best_before.date()
        if freshness.basis == FreshnessBasis.known:
            setattr(adjustment, f"expiry_date_{prefix}", best_before_date)
        elif freshness.basis == FreshnessBasis.estimated:
            setattr(adjustment, f"estimated_expiry_date_{prefix}", best_before_date)

    def _freshness_from_adjustment(
        self,
        adjustment: InventoryAdjustmentModel,
        *,
        prefix: str,
    ) -> FreshnessInfo | None:
        basis_value = getattr(adjustment, f"freshness_basis_{prefix}")
        if basis_value is None:
            return None

        basis = FreshnessBasis(basis_value)
        expiry_date = getattr(adjustment, f"expiry_date_{prefix}")
        estimated_expiry_date = getattr(adjustment, f"estimated_expiry_date_{prefix}")

        if basis == FreshnessBasis.known:
            return FreshnessInfo(
                basis=basis,
                best_before=_date_to_datetime(expiry_date),
            )
        if basis == FreshnessBasis.estimated:
            return FreshnessInfo(
                basis=basis,
                best_before=_date_to_datetime(estimated_expiry_date),
                estimated_note=None,
            )
        return FreshnessInfo(basis=basis)

    def _item_to_schema(
        self,
        item: InventoryItemModel,
        *,
        history_summary: InventoryHistorySummary | None = None,
        latest_adjustment: InventoryAdjustment | None = None,
    ) -> InventoryItem:
        return InventoryItem(
            inventory_item_id=item.id,
            household_id=item.household_id,
            name=item.name,
            storage_location=StorageLocation(item.storage_location),
            quantity_on_hand=_to_float(item.quantity_on_hand) or 0.0,
            primary_unit=item.primary_unit,
            freshness=self._freshness_from_item(item),
            is_active=item.is_active,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at,
            history_summary=history_summary,
            latest_adjustment=latest_adjustment,
        )

    def _adjustment_to_schema(
        self,
        adjustment: InventoryAdjustmentModel,
        *,
        primary_unit: str | None = None,
        corrected_by_adjustment_ids: list[str] | None = None,
    ) -> InventoryAdjustment:
        quantity_before = _to_float(adjustment.quantity_before)
        quantity_after = _to_float(adjustment.quantity_after)
        delta_quantity = _to_float(adjustment.delta_quantity)
        location_before = (
            StorageLocation(adjustment.storage_location_before)
            if adjustment.storage_location_before is not None
            else None
        )
        location_after = (
            StorageLocation(adjustment.storage_location_after)
            if adjustment.storage_location_after is not None
            else None
        )
        freshness_before = self._freshness_from_adjustment(adjustment, prefix="before")
        freshness_after = self._freshness_from_adjustment(adjustment, prefix="after")
        corrected_by_ids = corrected_by_adjustment_ids or []
        return InventoryAdjustment(
            inventory_adjustment_id=adjustment.id,
            inventory_item_id=adjustment.inventory_item_id,
            household_id=adjustment.household_id,
            mutation_type=MutationType(adjustment.mutation_type),
            delta_quantity=delta_quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            storage_location_before=location_before,
            storage_location_after=location_after,
            freshness_before=freshness_before,
            freshness_after=freshness_after,
            reason_code=ReasonCode(adjustment.reason_code),
            actor_user_id=adjustment.actor_id or "",
            correlation_id=adjustment.correlation_id,
            client_mutation_id=adjustment.client_mutation_id,
            causal_workflow_id=adjustment.causal_workflow_id,
            causal_workflow_type=adjustment.causal_workflow_type,
            corrects_adjustment_id=adjustment.corrects_adjustment_id,
            note=adjustment.notes,
            created_at=adjustment.created_at,
            primary_unit=primary_unit,
            quantity_transition=InventoryQuantityTransition(
                before=quantity_before,
                after=quantity_after,
                delta=delta_quantity,
                unit=primary_unit,
                changed=(
                    delta_quantity is not None
                    or quantity_before is not None
                    or quantity_after is not None
                ),
            ),
            location_transition=InventoryLocationTransition(
                before=location_before,
                after=location_after,
                changed=location_before != location_after,
            ),
            freshness_transition=InventoryFreshnessTransition(
                before=freshness_before,
                after=freshness_after,
                changed=freshness_before != freshness_after,
            ),
            workflow_reference=InventoryWorkflowReference(
                correlation_id=adjustment.correlation_id,
                causal_workflow_id=adjustment.causal_workflow_id,
                causal_workflow_type=adjustment.causal_workflow_type,
            ),
            correction_links=InventoryCorrectionLinks(
                corrects_adjustment_id=adjustment.corrects_adjustment_id,
                corrected_by_adjustment_ids=corrected_by_ids,
                is_correction=adjustment.corrects_adjustment_id is not None,
                is_corrected=bool(corrected_by_ids),
            ),
        )

    def _receipt_model_from_record(
        self,
        receipt: MutationReceiptModel,
    ) -> AdjustmentReceiptResponse:
        if receipt.result_summary is None:
            raise InventoryDomainError(
                code="mutation_receipt_missing_summary",
                message="The stored mutation receipt could not be replayed.",
            )

        payload = json.loads(receipt.result_summary)
        return AdjustmentReceiptResponse(
            inventory_adjustment_id=payload["inventory_adjustment_id"],
            inventory_item_id=payload["inventory_item_id"],
            mutation_type=MutationType(payload["mutation_type"]),
            quantity_after=payload.get("quantity_after"),
            version_after=payload["version_after"],
        )


# Module-level singleton used by routers. Replaced in tests via dependency override.
_default_store = InventoryStore.for_default_app()


def get_inventory_store() -> InventoryStore:
    return _default_store
