from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import MealPlanStatus, PlanSlotRegenStatus, SlotOrigin


class MealPlanCreate(BaseModel):
    household_id: str
    period_start: date
    period_end: date
    ai_suggestion_request_id: Optional[str] = None
    ai_suggestion_result_id: Optional[str] = None

    @property
    def is_valid_period(self) -> bool:
        return self.period_end >= self.period_start


class MealPlanRead(BaseModel):
    id: str
    household_id: str
    period_start: date
    period_end: date
    status: MealPlanStatus
    version: int
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime]
    confirmation_client_mutation_id: Optional[str]
    ai_suggestion_request_id: Optional[str]
    ai_suggestion_result_id: Optional[str]
    stale_warning_acknowledged: bool

    model_config = {"from_attributes": True}


class MealPlanConfirmCommand(BaseModel):
    meal_plan_id: str
    household_id: str
    actor_id: Optional[str] = None
    stale_warning_acknowledged: bool = False
    client_mutation_id: str = Field(min_length=1, max_length=128)


class MealPlanSlotCreate(BaseModel):
    meal_plan_id: str
    slot_key: str = Field(min_length=1, max_length=64)
    day_of_week: int = Field(ge=0, le=6)
    meal_type: str = Field(min_length=1, max_length=32)
    meal_title: Optional[str] = Field(default=None, max_length=255)
    meal_summary: Optional[str] = None
    meal_reference_id: Optional[str] = None
    slot_origin: SlotOrigin = SlotOrigin.manually_added
    ai_suggestion_request_id: Optional[str] = None
    ai_suggestion_result_id: Optional[str] = None
    reason_codes: Optional[str] = None
    explanation_entries: Optional[str] = None
    prompt_family: Optional[str] = None
    prompt_version: Optional[str] = None
    fallback_mode: Optional[bool] = None
    regen_status: PlanSlotRegenStatus = PlanSlotRegenStatus.idle
    pending_regen_request_id: Optional[str] = None
    notes: Optional[str] = None


class MealPlanSlotRead(BaseModel):
    id: str
    meal_plan_id: str
    slot_key: str
    day_of_week: int
    meal_type: str
    meal_title: Optional[str]
    meal_summary: Optional[str]
    meal_reference_id: Optional[str]
    slot_origin: SlotOrigin
    ai_suggestion_request_id: Optional[str]
    ai_suggestion_result_id: Optional[str]
    reason_codes: Optional[str]
    explanation_entries: Optional[str]
    prompt_family: Optional[str]
    prompt_version: Optional[str]
    fallback_mode: Optional[bool]
    regen_status: PlanSlotRegenStatus
    pending_regen_request_id: Optional[str]
    is_user_locked: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MealPlanSlotHistoryRead(BaseModel):
    id: str
    meal_plan_slot_id: str
    meal_plan_id: str
    slot_key: str
    slot_origin: SlotOrigin
    ai_suggestion_request_id: Optional[str]
    ai_suggestion_result_id: Optional[str]
    reason_codes: Optional[str]
    explanation_entries: Optional[str]
    prompt_family: Optional[str]
    prompt_version: Optional[str]
    fallback_mode: Optional[bool]
    stale_warning_present_at_confirmation: bool
    confirmed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
