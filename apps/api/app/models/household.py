from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Household(Base):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    memberships: Mapped[list["HouseholdMembership"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="household")
    inventory_adjustments: Mapped[list["InventoryAdjustment"]] = relationship(back_populates="household")
    mutation_receipts: Mapped[list["MutationReceipt"]] = relationship(back_populates="household")
    grocery_lists: Mapped[list["GroceryList"]] = relationship(back_populates="household")
    grocery_mutation_receipts: Mapped[list["GroceryMutationReceipt"]] = relationship(
        back_populates="household"
    )


class HouseholdMembership(Base):
    __tablename__ = "household_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    user_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("household_id", "user_id", name="uq_household_membership_household_user"),
    )

    household: Mapped["Household"] = relationship(back_populates="memberships")
