from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import AISuggestionStatus


class AISuggestionRequestCreate(BaseModel):
    household_id: str
    actor_id: Optional[str] = None
    plan_period_start: date
    plan_period_end: date
    target_slot_id: Optional[str] = None
    meal_plan_id: Optional[str] = None
    meal_plan_slot_id: Optional[str] = None
    request_idempotency_key: str = Field(min_length=1, max_length=128)
    prompt_family: Optional[str] = None
    prompt_version: Optional[str] = None
    policy_version: Optional[str] = None
    context_contract_version: Optional[str] = None
    result_contract_version: Optional[str] = None


class AISuggestionRequestRead(BaseModel):
    id: str
    household_id: str
    actor_id: Optional[str]
    plan_period_start: date
    plan_period_end: date
    target_slot_id: Optional[str]
    meal_plan_id: Optional[str]
    meal_plan_slot_id: Optional[str]
    status: AISuggestionStatus
    request_idempotency_key: str
    prompt_family: Optional[str]
    prompt_version: Optional[str]
    policy_version: Optional[str]
    context_contract_version: Optional[str]
    result_contract_version: Optional[str]
    grounding_hash: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AISuggestionSlotRead(BaseModel):
    id: str
    result_id: str
    slot_key: str
    day_of_week: int
    meal_type: str
    meal_title: str
    meal_summary: Optional[str]
    reason_codes: Optional[str]
    explanation_entries: Optional[str]
    uses_on_hand: Optional[str]
    missing_hints: Optional[str]
    is_fallback: bool

    model_config = {"from_attributes": True}


class AISuggestionResultRead(BaseModel):
    id: str
    request_id: str
    meal_plan_id: Optional[str]
    fallback_mode: str
    stale_flag: bool
    result_contract_version: Optional[str]
    created_at: datetime
    slots: list[AISuggestionSlotRead] = []

    model_config = {"from_attributes": True}
