from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GroceryList(Base):
    __tablename__ = "grocery_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    meal_plan_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("meal_plans.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="deriving")
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    versions: Mapped[list["GroceryListVersion"]] = relationship(back_populates="grocery_list", cascade="all, delete-orphan")
    items: Mapped[list["GroceryListItem"]] = relationship(back_populates="grocery_list", cascade="all, delete-orphan")


class GroceryListVersion(Base):
    __tablename__ = "grocery_list_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    grocery_list_id: Mapped[str] = mapped_column(String(36), ForeignKey("grocery_lists.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_period_reference: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confirmed_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meal_plans.id"), nullable=True
    )
    derived_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    source_plan_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inventory_snapshot_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    grocery_list: Mapped["GroceryList"] = relationship(back_populates="versions")


class GroceryListItem(Base):
    __tablename__ = "grocery_list_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    grocery_list_id: Mapped[str] = mapped_column(String(36), ForeignKey("grocery_lists.id"), nullable=False, index=True)
    grocery_list_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("grocery_list_versions.id"), nullable=True
    )
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ingredient_ref_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    quantity_needed: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity_offset: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    offset_inventory_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("inventory_items.id"), nullable=True
    )
    quantity_to_buy: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="derived")
    meal_sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_adjusted_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    user_adjustment_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_adjustment_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ad_hoc_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_purchased: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    grocery_list: Mapped["GroceryList"] = relationship(back_populates="items")
