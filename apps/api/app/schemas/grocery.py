from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import GroceryItemOrigin, GroceryListStatus


class GroceryListRead(BaseModel):
    id: str
    household_id: str
    meal_plan_id: Optional[str]
    status: GroceryListStatus
    current_version_number: int
    confirmed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroceryListVersionRead(BaseModel):
    id: str
    grocery_list_id: str
    version_number: int
    plan_period_reference: Optional[str]
    confirmed_plan_id: Optional[str]
    derived_at: datetime
    source_plan_version: Optional[int]
    inventory_snapshot_reference: Optional[str]
    invalidated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class GroceryListItemRead(BaseModel):
    id: str
    grocery_list_id: str
    grocery_list_version_id: Optional[str]
    ingredient_name: str
    ingredient_ref_id: Optional[str]
    quantity_needed: Decimal
    unit: str
    quantity_offset: Decimal
    offset_inventory_item_id: Optional[str]
    quantity_to_buy: Decimal
    origin: GroceryItemOrigin
    meal_sources: Optional[str]
    user_adjusted_quantity: Optional[Decimal]
    user_adjustment_note: Optional[str]
    user_adjustment_flagged: bool
    ad_hoc_note: Optional[str]
    is_active: bool
    is_purchased: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroceryListItemAdHocCreate(BaseModel):
    grocery_list_id: str
    household_id: str
    ingredient_name: str = Field(min_length=1, max_length=255)
    quantity_needed: Decimal = Field(gt=Decimal("0"), decimal_places=4)
    unit: str = Field(min_length=1, max_length=64)
    ad_hoc_note: Optional[str] = None
    client_mutation_id: str = Field(min_length=1, max_length=128)


class GroceryListConfirmCommand(BaseModel):
    grocery_list_id: str
    household_id: str
    client_mutation_id: str = Field(min_length=1, max_length=128)


class GroceryListQuantityAdjustCommand(BaseModel):
    grocery_list_item_id: str
    household_id: str
    user_adjusted_quantity: Decimal = Field(gt=Decimal("0"), decimal_places=4)
    user_adjustment_note: Optional[str] = None
    client_mutation_id: str = Field(min_length=1, max_length=128)


class GroceryListRemoveLineCommand(BaseModel):
    grocery_list_item_id: str
    household_id: str
    client_mutation_id: str = Field(min_length=1, max_length=128)
