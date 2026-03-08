from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_item_non_negative_quantity"),
        CheckConstraint("version >= 1", name="ck_inventory_item_version_positive"),
        CheckConstraint(
            "freshness_basis IN ('known', 'estimated', 'unknown')",
            name="ck_inventory_item_freshness_basis",
        ),
        CheckConstraint(
            "freshness_basis != 'known' OR (expiry_date IS NOT NULL AND estimated_expiry_date IS NULL)",
            name="ck_inventory_item_known_freshness_dates",
        ),
        CheckConstraint(
            "freshness_basis != 'estimated' OR (estimated_expiry_date IS NOT NULL AND expiry_date IS NULL)",
            name="ck_inventory_item_estimated_freshness_dates",
        ),
        CheckConstraint(
            "freshness_basis != 'unknown' OR (expiry_date IS NULL AND estimated_expiry_date IS NULL)",
            name="ck_inventory_item_unknown_freshness_dates",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_location: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    primary_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    freshness_basis: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    freshness_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    freshness_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    household: Mapped["Household"] = relationship(back_populates="inventory_items")
    adjustments: Mapped[list["InventoryAdjustment"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"
    __table_args__ = (
        CheckConstraint(
            "quantity_before IS NULL OR quantity_before >= 0",
            name="ck_inventory_adjustment_quantity_before_non_negative",
        ),
        CheckConstraint(
            "quantity_after IS NULL OR quantity_after >= 0",
            name="ck_inventory_adjustment_quantity_after_non_negative",
        ),
        CheckConstraint(
            "corrects_adjustment_id IS NULL OR corrects_adjustment_id != id",
            name="ck_inventory_adjustment_no_self_correction",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inventory_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), nullable=False, index=True
    )
    mutation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    delta_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_before: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_after: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    storage_location_before: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    storage_location_after: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    freshness_basis_before: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    expiry_date_before: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_expiry_date_before: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    freshness_basis_after: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    expiry_date_after: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_expiry_date_after: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    client_mutation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    causal_workflow_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    causal_workflow_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    corrects_adjustment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_adjustments.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    household: Mapped["Household"] = relationship(back_populates="inventory_adjustments")
    item: Mapped["InventoryItem"] = relationship(back_populates="adjustments")
    corrects: Mapped[Optional["InventoryAdjustment"]] = relationship(
        back_populates="corrected_by_adjustments",
        foreign_keys=[corrects_adjustment_id],
        remote_side="InventoryAdjustment.id",
    )
    corrected_by_adjustments: Mapped[list["InventoryAdjustment"]] = relationship(
        back_populates="corrects", foreign_keys=[corrects_adjustment_id]
    )
    receipts: Mapped[list["MutationReceipt"]] = relationship(back_populates="adjustment")


class MutationReceipt(Base):
    __tablename__ = "mutation_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), nullable=False, index=True
    )
    client_mutation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inventory_adjustment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_adjustments.id"), nullable=True
    )

    __table_args__ = (UniqueConstraint("household_id", "client_mutation_id", name="uq_mutation_receipt"),)

    household: Mapped["Household"] = relationship(back_populates="mutation_receipts")
    adjustment: Mapped[Optional["InventoryAdjustment"]] = relationship(back_populates="receipts")
