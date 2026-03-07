from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GroceryList(Base):
    __tablename__ = "grocery_lists"
    __table_args__ = (
        CheckConstraint("current_version_number >= 1", name="ck_grocery_list_current_version_positive"),
        CheckConstraint(
            "status IN ('no_plan_confirmed', 'deriving', 'draft', 'stale_draft', 'confirming', "
            "'confirmed', 'trip_in_progress', 'trip_complete_pending_reconciliation')",
            name="ck_grocery_list_status",
        ),
        UniqueConstraint(
            "household_id",
            "confirmation_client_mutation_id",
            name="uq_grocery_list_confirmation_mutation",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), nullable=False, index=True
    )
    meal_plan_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("meal_plans.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="deriving")
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmation_client_mutation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    household: Mapped["Household"] = relationship(back_populates="grocery_lists")
    versions: Mapped[list["GroceryListVersion"]] = relationship(
        back_populates="grocery_list",
        cascade="all, delete-orphan",
        order_by="GroceryListVersion.version_number",
    )
    items: Mapped[list["GroceryListItem"]] = relationship(
        back_populates="grocery_list", cascade="all, delete-orphan"
    )
    mutation_receipts: Mapped[list["GroceryMutationReceipt"]] = relationship(
        back_populates="grocery_list", cascade="all, delete-orphan"
    )
    sync_conflicts: Mapped[list["GrocerySyncConflict"]] = relationship(
        back_populates="grocery_list", cascade="all, delete-orphan"
    )

    @property
    def current_version(self) -> Optional["GroceryListVersion"]:
        return next(
            (version for version in self.versions if version.version_number == self.current_version_number),
            None,
        )

    @property
    def current_version_id(self) -> Optional[str]:
        current = self.current_version
        return current.id if current is not None else None

    @property
    def last_derived_at(self) -> Optional[datetime]:
        current = self.current_version
        return current.derived_at if current is not None else None

    @property
    def incomplete_slot_warnings(self) -> list[dict[str, object]]:
        current = self.current_version
        if current is None or not current.incomplete_slot_warnings:
            return []
        try:
            payload = json.loads(current.incomplete_slot_warnings)
        except json.JSONDecodeError:
            return []
        return payload if isinstance(payload, list) else []

    @property
    def trip_state(self) -> str:
        if self.status == "trip_in_progress":
            return "trip_in_progress"
        if self.status == "trip_complete_pending_reconciliation":
            return "trip_complete_pending_reconciliation"
        return "confirmed_list_ready"


class GroceryListVersion(Base):
    __tablename__ = "grocery_list_versions"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="ck_grocery_list_version_positive"),
        UniqueConstraint("grocery_list_id", "version_number", name="uq_grocery_list_version_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    grocery_list_id: Mapped[str] = mapped_column(String(36), ForeignKey("grocery_lists.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_period_reference: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confirmed_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meal_plans.id"), nullable=True
    )
    derived_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_plan_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inventory_snapshot_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    incomplete_slot_warnings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    grocery_list: Mapped["GroceryList"] = relationship(back_populates="versions")
    items: Mapped[list["GroceryListItem"]] = relationship(back_populates="grocery_list_version")


class GroceryListItem(Base):
    __tablename__ = "grocery_list_items"
    __table_args__ = (
        CheckConstraint("required_quantity > 0", name="ck_grocery_list_item_required_positive"),
        CheckConstraint("offset_quantity >= 0", name="ck_grocery_list_item_offset_non_negative"),
        CheckConstraint("shopping_quantity >= 0", name="ck_grocery_list_item_shopping_non_negative"),
        CheckConstraint(
            "user_adjusted_quantity IS NULL OR user_adjusted_quantity > 0",
            name="ck_grocery_list_item_user_adjusted_positive",
        ),
        CheckConstraint("origin IN ('derived', 'ad_hoc')", name="ck_grocery_list_item_origin"),
        CheckConstraint(
            "removed_at IS NULL OR active = 0",
            name="ck_grocery_list_item_removed_requires_inactive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stable_line_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=lambda: str(uuid.uuid4()), index=True
    )
    grocery_list_id: Mapped[str] = mapped_column(String(36), ForeignKey("grocery_lists.id"), nullable=False, index=True)
    grocery_list_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grocery_list_versions.id"), nullable=False, index=True
    )
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ingredient_ref_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    offset_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    offset_inventory_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_items.id"), nullable=True
    )
    offset_inventory_item_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shopping_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="derived")
    meal_sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_adjusted_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    user_adjustment_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_adjustment_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ad_hoc_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_purchased: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_client_mutation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    removed_client_mutation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    grocery_list: Mapped["GroceryList"] = relationship(back_populates="items")
    grocery_list_version: Mapped["GroceryListVersion"] = relationship(back_populates="items")
    mutation_receipts: Mapped[list["GroceryMutationReceipt"]] = relationship(back_populates="grocery_list_item")


class GroceryMutationReceipt(Base):
    __tablename__ = "grocery_mutation_receipts"
    __table_args__ = (
        UniqueConstraint("household_id", "client_mutation_id", name="uq_grocery_mutation_receipt"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), nullable=False, index=True
    )
    grocery_list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grocery_lists.id"), nullable=False, index=True
    )
    grocery_list_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("grocery_list_items.id"), nullable=True
    )
    client_mutation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mutation_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    household: Mapped["Household"] = relationship(back_populates="grocery_mutation_receipts")
    grocery_list: Mapped["GroceryList"] = relationship(back_populates="mutation_receipts")
    grocery_list_item: Mapped[Optional["GroceryListItem"]] = relationship(back_populates="mutation_receipts")


class GrocerySyncConflict(Base):
    __tablename__ = "grocery_sync_conflicts"
    __table_args__ = (
        UniqueConstraint("household_id", "local_mutation_id", name="uq_grocery_sync_conflict_local_mutation"),
        CheckConstraint(
            "aggregate_type IN ('grocery_list', 'grocery_line', 'inventory_item')",
            name="ck_grocery_sync_conflict_aggregate_type",
        ),
        CheckConstraint(
            "outcome IN ("
            "'duplicate_retry', "
            "'auto_merged_non_overlapping', "
            "'failed_retryable', "
            "'review_required_quantity', "
            "'review_required_deleted_or_archived', "
            "'review_required_freshness_or_location', "
            "'review_required_other_unsafe'"
            ")",
            name="ck_grocery_sync_conflict_outcome",
        ),
        CheckConstraint(
            "local_queue_status IN ("
            "'queued_offline', "
            "'syncing', "
            "'synced', "
            "'retrying', "
            "'failed_retryable', "
            "'review_required', "
            "'resolving', "
            "'resolved_keep_mine', "
            "'resolved_use_server'"
            ")",
            name="ck_grocery_sync_conflict_local_queue_status",
        ),
        CheckConstraint(
            "resolution_status IN ('pending', 'resolved_keep_mine', 'resolved_use_server')",
            name="ck_grocery_sync_conflict_resolution_status",
        ),
        CheckConstraint(
            "base_server_version IS NULL OR base_server_version >= 1",
            name="ck_grocery_sync_conflict_base_server_version_positive",
        ),
        CheckConstraint(
            "current_server_version >= 1",
            name="ck_grocery_sync_conflict_current_server_version_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), nullable=False, index=True
    )
    grocery_list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grocery_lists.id"), nullable=False, index=True
    )
    aggregate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    local_mutation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mutation_type: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    base_server_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_server_version: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    local_queue_status: Mapped[str] = mapped_column(String(32), nullable=False, default="review_required")
    allowed_resolution_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    local_intent_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_state_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    server_state_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by_actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    household: Mapped["Household"] = relationship()
    grocery_list: Mapped["GroceryList"] = relationship(back_populates="sync_conflicts")
