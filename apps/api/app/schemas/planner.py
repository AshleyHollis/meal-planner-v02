from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, Field

from app.schemas.enums import AISuggestionStatus, MealPlanStatus, PlanSlotRegenStatus, SlotOrigin


class SuggestionRequestCommand(BaseModel):
    plan_period_start: date = Field(
        validation_alias=AliasChoices("plan_period_start", "planPeriodStart")
    )
    request_idempotency_key: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("request_idempotency_key", "requestIdempotencyKey"),
    )
    target_slot_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("target_slot_id", "targetSlotId"),
    )

    model_config = {"populate_by_name": True}


class DraftCreateCommand(BaseModel):
    suggestion_id: str = Field(
        min_length=1,
        validation_alias=AliasChoices("suggestion_id", "suggestionId"),
    )
    replace_existing: bool = Field(
        default=False,
        validation_alias=AliasChoices("replace_existing", "replaceExisting"),
    )

    model_config = {"populate_by_name": True}


class DraftConfirmRequest(BaseModel):
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )
    stale_warning_acknowledged: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "stale_warning_acknowledged",
            "staleWarningAcknowledged",
        ),
    )

    model_config = {"populate_by_name": True}


class DraftSlotUpdateCommand(BaseModel):
    meal_title: Optional[str] = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("meal_title", "mealTitle"),
    )
    meal_summary: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("meal_summary", "mealSummary"),
    )
    meal_reference_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("meal_reference_id", "mealReferenceId"),
    )

    model_config = {"populate_by_name": True}


class SlotRegenerateCommand(BaseModel):
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )

    model_config = {"populate_by_name": True}


class PlannerSlotSuggestionSnapshot(BaseModel):
    meal_title: Optional[str]
    meal_summary: Optional[str]
    reason_codes: list[str] = []
    explanation_entries: list[str] = []
    uses_on_hand: list[str] = []
    missing_hints: list[str] = []


class PlannerSlotView(BaseModel):
    id: str
    slot_key: str
    day_of_week: int
    meal_type: str
    meal_title: Optional[str]
    meal_summary: Optional[str]
    meal_reference_id: Optional[str]
    slot_origin: SlotOrigin
    reason_codes: list[str] = []
    explanation_entries: list[str] = []
    regen_status: PlanSlotRegenStatus
    pending_regen_request_id: Optional[str]
    is_user_locked: bool
    prompt_family: Optional[str]
    prompt_version: Optional[str]
    fallback_mode: Optional[Literal["none", "curated_fallback", "manual_guidance"]]
    slot_message: Optional[str] = None
    original_suggestion: Optional[PlannerSlotSuggestionSnapshot] = None
    uses_on_hand: list[str] = []
    missing_hints: list[str] = []


class SuggestionEnvelope(BaseModel):
    request_id: str
    household_id: str
    plan_period_start: date
    plan_period_end: date
    status: AISuggestionStatus
    created_at: datetime
    completed_at: Optional[datetime]
    suggestion_id: Optional[str] = None
    meal_plan_id: Optional[str] = None
    slots: list[PlannerSlotView] = []
    is_stale: bool = False
    fallback_mode: Literal["none", "curated_fallback", "manual_guidance"] = "none"
    prompt_family: Optional[str] = None
    prompt_version: Optional[str] = None
    policy_version: Optional[str] = None
    context_contract_version: Optional[str] = None
    result_contract_version: Optional[str] = None


class DraftPlanView(BaseModel):
    id: str
    household_id: str
    period_start: date
    period_end: date
    status: MealPlanStatus
    created_at: datetime
    updated_at: datetime
    stale_warning: bool
    stale_warning_acknowledged: bool
    ai_suggestion_request_id: Optional[str]
    ai_suggestion_result_id: Optional[str]
    slots: list[PlannerSlotView] = []


class ConfirmedPlanView(BaseModel):
    id: str
    household_id: str
    period_start: date
    period_end: date
    status: MealPlanStatus
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime
    stale_warning_acknowledged: bool
    ai_suggestion_request_id: Optional[str]
    ai_suggestion_result_id: Optional[str]
    slots: list[PlannerSlotView] = []


class GroceryRefreshTrigger(BaseModel):
    trigger_type: Literal["grocery_refresh_requested"] = "grocery_refresh_requested"
    source_plan_status: Literal["confirmed"] = "confirmed"
    household_id: str
    confirmed_plan_id: str
    plan_period_start: date
    plan_period_end: date
    source_plan_version: int
    correlation_id: str


class PlanConfirmedEvent(BaseModel):
    event_type: Literal["plan_confirmed"] = "plan_confirmed"
    household_id: str
    meal_plan_id: str
    plan_period_start: date
    plan_period_end: date
    confirmed_at: datetime
    source_plan_status: Literal["confirmed"] = "confirmed"
    stale_warning_acknowledged: bool
    confirmation_client_mutation_id: str
    actor_id: str
    slot_count: int
    plan_version: int
    correlation_id: str
    grocery_refresh_trigger: GroceryRefreshTrigger
