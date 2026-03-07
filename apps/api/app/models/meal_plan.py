from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MealPlan(Base):
    """Editable household draft or authoritative confirmed weekly plan."""

    __tablename__ = "meal_plans"
    __table_args__ = (
        UniqueConstraint(
            "household_id",
            "confirmation_client_mutation_id",
            name="uq_meal_plan_confirmation_mutation",
        ),
        Index(
            "ix_meal_plans_active_draft_household_period",
            "household_id",
            "period_start",
            "period_end",
            unique=True,
            sqlite_where=text("status = 'draft'"),
            postgresql_where=text("status = 'draft'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmation_client_mutation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ai_suggestion_request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ai_suggestion_result_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    stale_warning_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    slots: Mapped[list["MealPlanSlot"]] = relationship(back_populates="meal_plan", cascade="all, delete-orphan")


class MealPlanSlot(Base):
    """Current slot content plus draft-time AI lineage and regen status."""

    __tablename__ = "meal_plan_slots"
    __table_args__ = (
        UniqueConstraint("meal_plan_id", "slot_key", name="uq_meal_plan_slot_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meal_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("meal_plans.id"), nullable=False, index=True)
    slot_key: Mapped[str] = mapped_column(String(64), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    meal_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meal_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meal_reference_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    slot_origin: Mapped[str] = mapped_column(String(32), nullable=False, default="manually_added")
    ai_suggestion_request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ai_suggestion_result_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reason_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation_entries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_family: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    fallback_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    regen_status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle")
    pending_regen_request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    is_user_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    meal_plan: Mapped["MealPlan"] = relationship(back_populates="slots")
    history: Mapped[list["MealPlanSlotHistory"]] = relationship(back_populates="slot", cascade="all, delete-orphan")


class MealPlanSlotHistory(Base):
    """Stores AI origin metadata at the time a plan is confirmed. Non-authoritative audit trail."""
    __tablename__ = "meal_plan_slot_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meal_plan_slot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meal_plan_slots.id"), nullable=False, index=True
    )
    meal_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("meal_plans.id"), nullable=False)
    slot_key: Mapped[str] = mapped_column(String(64), nullable=False)
    slot_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    ai_suggestion_request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ai_suggestion_result_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reason_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation_entries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_family: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    fallback_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    stale_warning_present_at_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    slot: Mapped["MealPlanSlot"] = relationship(back_populates="history")
