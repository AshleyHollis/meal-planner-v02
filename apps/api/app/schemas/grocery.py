from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.schemas.enums import (
    GroceryItemOrigin,
    GroceryListStatus,
    SyncAggregateType,
    SyncMutationState,
    SyncOutcome,
    SyncResolutionAction,
    SyncResolutionStatus,
    TripState,
)


def _parse_json_list(value: object) -> list[object]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


class GroceryMealSourceRead(BaseModel):
    meal_slot_id: str = Field(validation_alias=AliasChoices("meal_slot_id", "meal_plan_slot_id"))
    meal_name: Optional[str] = None
    contributed_quantity: Decimal = Field(
        validation_alias=AliasChoices("contributed_quantity", "quantity"),
        decimal_places=4,
    )


class GroceryIncompleteSlotWarningRead(BaseModel):
    meal_slot_id: str = Field(validation_alias=AliasChoices("meal_slot_id", "meal_plan_slot_id"))
    meal_name: Optional[str] = None
    reason: str = "missing_ingredient_data"
    message: Optional[str] = None


class GroceryListVersionRead(BaseModel):
    id: str
    grocery_list_id: str
    version_number: int
    plan_period_reference: Optional[str]
    confirmed_plan_id: Optional[str]
    derived_at: datetime
    confirmed_plan_version: Optional[int]
    inventory_snapshot_reference: Optional[str]
    invalidated_at: Optional[datetime]
    incomplete_slot_warnings: list[GroceryIncompleteSlotWarningRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @field_validator("incomplete_slot_warnings", mode="before")
    @classmethod
    def validate_warning_payload(cls, value: object) -> list[object]:
        return _parse_json_list(value)


class GroceryListItemRead(BaseModel):
    id: str
    grocery_line_id: str = Field(
        validation_alias=AliasChoices("grocery_line_id", "stable_line_id", "id"),
        serialization_alias="grocery_line_id",
    )
    grocery_list_id: str
    grocery_list_version_id: str
    ingredient_name: str
    ingredient_ref_id: Optional[str] = None
    required_quantity: Decimal
    unit: str
    offset_quantity: Decimal
    offset_inventory_item_id: Optional[str] = None
    offset_inventory_item_version: Optional[int] = None
    shopping_quantity: Decimal
    origin: GroceryItemOrigin
    meal_sources: list[GroceryMealSourceRead] = Field(default_factory=list)
    user_adjusted_quantity: Optional[Decimal] = None
    user_adjustment_note: Optional[str] = None
    user_adjustment_flagged: bool
    ad_hoc_note: Optional[str] = None
    active: bool
    removed_at: Optional[datetime] = None
    created_client_mutation_id: Optional[str] = None
    removed_client_mutation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("meal_sources", mode="before")
    @classmethod
    def validate_meal_sources(cls, value: object) -> list[object]:
        return _parse_json_list(value)


class GroceryListRead(BaseModel):
    id: str
    household_id: str
    meal_plan_id: Optional[str]
    status: GroceryListStatus
    current_version_number: int
    grocery_list_version_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("grocery_list_version_id", "current_version_id"),
        serialization_alias="grocery_list_version_id",
    )
    current_version_id: Optional[str] = None
    confirmed_at: Optional[datetime]
    confirmation_client_mutation_id: Optional[str] = None
    trip_state: TripState = Field(
        default=TripState.confirmed_list_ready,
        validation_alias=AliasChoices("trip_state"),
    )
    last_derived_at: Optional[datetime] = None
    plan_period_start: Optional[date] = None
    plan_period_end: Optional[date] = None
    confirmed_plan_version: Optional[int] = None
    inventory_snapshot_reference: Optional[str] = None
    is_stale: bool = False
    incomplete_slot_warnings: list[GroceryIncompleteSlotWarningRead] = Field(default_factory=list)
    lines: list[GroceryListItemRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("incomplete_slot_warnings", mode="before")
    @classmethod
    def validate_incomplete_slot_warnings(cls, value: object) -> list[object]:
        return _parse_json_list(value)


class SyncAggregateRef(BaseModel):
    aggregate_type: SyncAggregateType
    aggregate_id: str
    aggregate_version: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("aggregate_version", "server_version", "current_server_version"),
    )
    provisional_aggregate_id: Optional[str] = None


class QueueableSyncMutation(BaseModel):
    client_mutation_id: str = Field(min_length=1, max_length=128)
    household_id: str
    actor_id: str
    aggregate_type: SyncAggregateType
    aggregate_id: Optional[str] = None
    provisional_aggregate_id: Optional[str] = None
    mutation_type: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    base_server_version: Optional[int] = Field(default=None, ge=1)
    device_timestamp: datetime
    local_queue_status: SyncMutationState = SyncMutationState.queued_offline


class GroceryConfirmedListBootstrapRead(BaseModel):
    household_id: str
    grocery_list_id: str
    grocery_list_version_id: str
    grocery_list_status: GroceryListStatus = Field(
        validation_alias=AliasChoices("grocery_list_status", "status")
    )
    trip_state: TripState = Field(
        default=TripState.confirmed_list_ready,
        validation_alias=AliasChoices("trip_state"),
    )
    aggregate: SyncAggregateRef
    confirmed_at: datetime
    confirmed_plan_version: Optional[int] = None
    inventory_snapshot_reference: Optional[str] = None
    incomplete_slot_warnings: list[GroceryIncompleteSlotWarningRead] = Field(default_factory=list)
    lines: list[GroceryListItemRead] = Field(default_factory=list)

    @field_validator("incomplete_slot_warnings", mode="before")
    @classmethod
    def validate_bootstrap_incomplete_slot_warnings(cls, value: object) -> list[object]:
        return _parse_json_list(value)


class GroceryMutationReceiptRead(BaseModel):
    id: str
    household_id: str
    grocery_list_id: str
    grocery_list_item_id: Optional[str]
    client_mutation_id: str
    mutation_kind: str
    accepted_at: datetime
    result_summary: Optional[str]

    model_config = {"from_attributes": True}


class GroceryListItemAdHocCreate(BaseModel):
    grocery_list_id: str = Field(
        validation_alias=AliasChoices("grocery_list_id", "groceryListId")
    )
    household_id: str
    ingredient_name: str = Field(min_length=1, max_length=255)
    shopping_quantity: Decimal = Field(
        gt=Decimal("0"),
        decimal_places=4,
        validation_alias=AliasChoices("shopping_quantity", "quantity_needed"),
        serialization_alias="shopping_quantity",
    )
    unit: str = Field(min_length=1, max_length=64)
    ad_hoc_note: Optional[str] = None
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )

    model_config = {"populate_by_name": True}


class GroceryListDeriveCommand(BaseModel):
    household_id: str
    plan_period_start: date = Field(
        validation_alias=AliasChoices("plan_period_start", "planPeriodStart")
    )
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )

    model_config = {"populate_by_name": True}


class GroceryListConfirmCommand(BaseModel):
    grocery_list_id: str = Field(
        validation_alias=AliasChoices("grocery_list_id", "groceryListId")
    )
    household_id: str
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )

    model_config = {"populate_by_name": True}


class GroceryListQuantityAdjustCommand(BaseModel):
    grocery_list_item_id: str = Field(
        validation_alias=AliasChoices("grocery_list_item_id", "groceryListItemId")
    )
    household_id: str
    user_adjusted_quantity: Decimal = Field(
        gt=Decimal("0"),
        decimal_places=4,
        validation_alias=AliasChoices("user_adjusted_quantity", "userAdjustedQuantity"),
    )
    user_adjustment_note: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("user_adjustment_note", "userAdjustmentNote"),
    )
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )

    model_config = {"populate_by_name": True}


class GroceryListRemoveLineCommand(BaseModel):
    grocery_list_item_id: str = Field(
        validation_alias=AliasChoices("grocery_list_item_id", "groceryListItemId")
    )
    household_id: str
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )

    model_config = {"populate_by_name": True}


class SyncMutationOutcomeRead(BaseModel):
    client_mutation_id: str
    mutation_type: str
    aggregate: SyncAggregateRef
    outcome: SyncOutcome
    authoritative_server_version: Optional[int] = Field(default=None, ge=1)
    conflict_id: Optional[str] = None
    retryable: bool = False
    duplicate_of_client_mutation_id: Optional[str] = None
    auto_merge_reason: Optional[str] = None


class SyncConflictSummaryRead(BaseModel):
    conflict_id: str
    household_id: str
    aggregate: SyncAggregateRef
    local_mutation_id: str
    mutation_type: str
    outcome: SyncOutcome
    base_server_version: Optional[int] = Field(default=None, ge=1)
    current_server_version: int = Field(ge=1)
    requires_review: bool = True
    summary: str
    local_queue_status: SyncMutationState = SyncMutationState.review_required
    allowed_resolution_actions: list[SyncResolutionAction] = Field(default_factory=list)
    resolution_status: SyncResolutionStatus = SyncResolutionStatus.pending
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_actor_id: Optional[str] = None


class SyncConflictDetailRead(SyncConflictSummaryRead):
    local_intent_summary: dict[str, Any] = Field(default_factory=dict)
    base_state_summary: dict[str, Any] = Field(default_factory=dict)
    server_state_summary: dict[str, Any] = Field(default_factory=dict)


class SyncConflictKeepMineCommand(BaseModel):
    conflict_id: str = Field(validation_alias=AliasChoices("conflict_id", "conflictId"))
    household_id: str
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )
    base_server_version: Optional[int] = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("base_server_version", "baseServerVersion"),
    )

    model_config = {"populate_by_name": True}


class SyncConflictUseServerCommand(BaseModel):
    conflict_id: str = Field(validation_alias=AliasChoices("conflict_id", "conflictId"))
    household_id: str
    client_mutation_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("client_mutation_id", "clientMutationId"),
    )

    model_config = {"populate_by_name": True}


class GroceryMutationResult(BaseModel):
    mutation_kind: str
    grocery_list: GroceryListRead
    item: Optional[GroceryListItemRead] = None
    is_duplicate: bool = False
