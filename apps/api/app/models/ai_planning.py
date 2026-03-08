from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AISuggestionRequest(Base):
    """Async weekly-plan or slot-regen request scoped to a household."""

    __tablename__ = "ai_suggestion_requests"
    __table_args__ = (
        UniqueConstraint(
            "household_id",
            "request_idempotency_key",
            name="uq_ai_request_household_idempotency",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    plan_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    plan_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    target_slot_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    meal_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meal_plans.id"), nullable=True, index=True
    )
    meal_plan_slot_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meal_plan_slots.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    request_idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_family: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    context_contract_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    result_contract_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    grounding_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    result: Mapped[Optional["AISuggestionResult"]] = relationship(back_populates="request", uselist=False)


class AISuggestionResult(Base):
    """Normalized AI suggestion result, distinct from editable or confirmed plan state."""

    __tablename__ = "ai_suggestion_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ai_suggestion_requests.id"), nullable=False, unique=True
    )
    meal_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meal_plans.id"), nullable=True
    )
    fallback_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    stale_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result_contract_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    request: Mapped["AISuggestionRequest"] = relationship(back_populates="result")
    slots: Mapped[list["AISuggestionSlot"]] = relationship(back_populates="result", cascade="all, delete-orphan")


class AISuggestionSlot(Base):
    """Structured suggestion content for one planner slot."""

    __tablename__ = "ai_suggestion_slots"
    __table_args__ = (
        UniqueConstraint("result_id", "slot_key", name="uq_ai_suggestion_slot_result_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ai_suggestion_results.id"), nullable=False, index=True
    )
    slot_key: Mapped[str] = mapped_column(String(64), nullable=False)
    day_of_week: Mapped[int] = mapped_column(nullable=False)
    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    meal_title: Mapped[str] = mapped_column(String(255), nullable=False)
    meal_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation_entries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uses_on_hand: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_hints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    result: Mapped["AISuggestionResult"] = relationship(back_populates="slots")
