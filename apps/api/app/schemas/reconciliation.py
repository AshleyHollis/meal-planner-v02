from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import (
    CookingEventStatus,
    CookingOutcome,
    ReconciliationStatus,
    ShoppingOutcome,
    StorageLocation,
    FreshnessBasis,
)


class ShoppingReconciliationRead(BaseModel):
    id: str
    household_id: str
    actor_id: Optional[str]
    trip_session_id: Optional[str]
    grocery_list_version_id: Optional[str]
    status: ReconciliationStatus
    client_apply_mutation_id: Optional[str]
    source_grocery_list_version_number: Optional[int]
    failure_reason: Optional[str]
    review_required_reason: Optional[str]
    applied_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShoppingReconciliationRowInput(BaseModel):
    grocery_list_item_id: Optional[str] = None
    item_name: str
    planned_quantity: Optional[Decimal] = None
    planned_unit: Optional[str] = None
    outcome: ShoppingOutcome
    actual_quantity: Optional[Decimal] = None
    actual_unit: Optional[str] = None
    storage_location: Optional[StorageLocation] = None
    inventory_item_id: Optional[str] = None
    inventory_item_version: Optional[int] = Field(default=None, ge=1)


class ShoppingApplyCommand(BaseModel):
    household_id: str
    actor_id: Optional[str] = None
    trip_session_id: Optional[str] = None
    grocery_list_version_id: Optional[str] = None
    source_grocery_list_version_number: Optional[int] = Field(default=None, ge=1)
    rows: list[ShoppingReconciliationRowInput]
    client_apply_mutation_id: str


class CookingEventRead(BaseModel):
    id: str
    household_id: str
    actor_id: Optional[str]
    meal_plan_slot_id: Optional[str]
    status: CookingEventStatus
    client_apply_mutation_id: Optional[str]
    expected_meal_plan_version: Optional[int]
    failure_reason: Optional[str]
    review_required_reason: Optional[str]
    applied_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CookingIngredientRowInput(BaseModel):
    ingredient_name: str
    planned_quantity: Optional[Decimal] = None
    planned_unit: Optional[str] = None
    outcome: CookingOutcome
    actual_quantity: Optional[Decimal] = None
    actual_unit: Optional[str] = None
    inventory_item_id: Optional[str] = None
    inventory_item_version: Optional[int] = Field(default=None, ge=1)


class LeftoverRowInput(BaseModel):
    display_name: str
    quantity: Decimal
    unit: str
    storage_location: StorageLocation = StorageLocation.leftovers
    target_inventory_item_id: Optional[str] = None
    target_inventory_item_version: Optional[int] = Field(default=None, ge=1)
    freshness_basis: FreshnessBasis = FreshnessBasis.unknown
    expiry_date: Optional[str] = None


class CookingApplyCommand(BaseModel):
    household_id: str
    actor_id: Optional[str] = None
    meal_plan_slot_id: Optional[str] = None
    expected_meal_plan_version: Optional[int] = Field(default=None, ge=1)
    ingredient_rows: list[CookingIngredientRowInput]
    leftover_rows: list[LeftoverRowInput]
    client_apply_mutation_id: str
