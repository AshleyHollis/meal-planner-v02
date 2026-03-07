from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ShoppingReconciliation(Base):
    __tablename__ = "shopping_reconciliations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    trip_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    grocery_list_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("grocery_list_versions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="review_draft")
    client_apply_mutation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    source_grocery_list_version_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_required_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    rows: Mapped[list["ShoppingReconciliationRow"]] = relationship(back_populates="reconciliation", cascade="all, delete-orphan")


class ShoppingReconciliationRow(Base):
    __tablename__ = "shopping_reconciliation_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reconciliation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shopping_reconciliations.id"), nullable=False, index=True
    )
    grocery_list_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("grocery_list_items.id"), nullable=True
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    planned_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    planned_unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    actual_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    actual_unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    storage_location: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    inventory_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_items.id"), nullable=True
    )
    inventory_item_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inventory_adjustment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_adjustments.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    reconciliation: Mapped["ShoppingReconciliation"] = relationship(back_populates="rows")


class CookingEvent(Base):
    __tablename__ = "cooking_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    meal_plan_slot_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meal_plan_slots.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="cooking_draft")
    client_apply_mutation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    expected_meal_plan_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_required_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    ingredient_rows: Mapped[list["CookingIngredientRow"]] = relationship(back_populates="cooking_event", cascade="all, delete-orphan")
    leftover_rows: Mapped[list["LeftoverRow"]] = relationship(back_populates="cooking_event", cascade="all, delete-orphan")


class CookingIngredientRow(Base):
    __tablename__ = "cooking_ingredient_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cooking_event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cooking_events.id"), nullable=False, index=True
    )
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    planned_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    planned_unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    actual_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    actual_unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    inventory_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_items.id"), nullable=True
    )
    inventory_item_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inventory_adjustment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_adjustments.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    cooking_event: Mapped["CookingEvent"] = relationship(back_populates="ingredient_rows")


class LeftoverRow(Base):
    __tablename__ = "leftover_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cooking_event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cooking_events.id"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_location: Mapped[str] = mapped_column(String(32), nullable=False, default="leftovers")
    target_inventory_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_items.id"), nullable=True
    )
    target_inventory_item_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inventory_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_items.id"), nullable=True
    )
    inventory_adjustment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_adjustments.id"), nullable=True
    )
    freshness_basis: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    cooking_event: Mapped["CookingEvent"] = relationship(back_populates="leftover_rows")
