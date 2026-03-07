from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import FreshnessBasis, MutationType, ReasonCode, StorageLocation


class InventoryItemCreate(BaseModel):
    household_id: str
    name: str = Field(min_length=1, max_length=255)
    storage_location: StorageLocation
    quantity_on_hand: Decimal = Field(ge=Decimal("0"), decimal_places=4)
    primary_unit: str = Field(min_length=1, max_length=64)
    freshness_basis: FreshnessBasis = FreshnessBasis.unknown
    expiry_date: Optional[date] = None
    estimated_expiry_date: Optional[date] = None
    freshness_note: Optional[str] = None
    client_mutation_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_freshness_dates(self) -> "InventoryItemCreate":
        if self.freshness_basis == FreshnessBasis.known:
            if self.expiry_date is None:
                raise ValueError("known freshness requires expiry_date")
            if self.estimated_expiry_date is not None:
                raise ValueError("known freshness cannot include estimated_expiry_date")
        elif self.freshness_basis == FreshnessBasis.estimated:
            if self.estimated_expiry_date is None:
                raise ValueError("estimated freshness requires estimated_expiry_date")
            if self.expiry_date is not None:
                raise ValueError("estimated freshness cannot include expiry_date")
        else:
            if self.expiry_date is not None or self.estimated_expiry_date is not None:
                raise ValueError("unknown freshness cannot include expiry dates")
        return self


class InventoryItemRead(BaseModel):
    id: str
    household_id: str
    name: str
    storage_location: StorageLocation
    quantity_on_hand: Decimal
    primary_unit: str
    freshness_basis: FreshnessBasis
    expiry_date: Optional[date]
    estimated_expiry_date: Optional[date]
    freshness_note: Optional[str]
    freshness_updated_at: Optional[datetime]
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryAdjustmentCreate(BaseModel):
    inventory_item_id: str
    household_id: str
    mutation_type: MutationType
    delta_quantity: Optional[Decimal] = None
    quantity_before: Optional[Decimal] = None
    quantity_after: Optional[Decimal] = None
    storage_location_before: Optional[StorageLocation] = None
    storage_location_after: Optional[StorageLocation] = None
    freshness_basis_before: Optional[FreshnessBasis] = None
    expiry_date_before: Optional[date] = None
    estimated_expiry_date_before: Optional[date] = None
    freshness_basis_after: Optional[FreshnessBasis] = None
    expiry_date_after: Optional[date] = None
    estimated_expiry_date_after: Optional[date] = None
    reason_code: ReasonCode
    actor_id: Optional[str] = None
    client_mutation_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causal_workflow_id: Optional[str] = None
    causal_workflow_type: Optional[str] = None
    corrects_adjustment_id: Optional[str] = None
    notes: Optional[str] = None


class InventoryAdjustmentRead(BaseModel):
    id: str
    inventory_item_id: str
    household_id: str
    mutation_type: MutationType
    delta_quantity: Optional[Decimal]
    quantity_before: Optional[Decimal]
    quantity_after: Optional[Decimal]
    storage_location_before: Optional[StorageLocation]
    storage_location_after: Optional[StorageLocation]
    freshness_basis_before: Optional[FreshnessBasis]
    expiry_date_before: Optional[date]
    estimated_expiry_date_before: Optional[date]
    freshness_basis_after: Optional[FreshnessBasis]
    expiry_date_after: Optional[date]
    estimated_expiry_date_after: Optional[date]
    reason_code: ReasonCode
    actor_id: Optional[str]
    client_mutation_id: Optional[str]
    correlation_id: Optional[str]
    causal_workflow_id: Optional[str]
    causal_workflow_type: Optional[str]
    corrects_adjustment_id: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MutationReceiptRead(BaseModel):
    id: str
    household_id: str
    client_mutation_id: str
    accepted_at: datetime
    result_summary: Optional[str]
    inventory_adjustment_id: Optional[str]

    model_config = {"from_attributes": True}


class FreshnessInfo(BaseModel):
    basis: FreshnessBasis = FreshnessBasis.unknown
    best_before: datetime | None = None
    estimated_note: str | None = None

    @model_validator(mode="after")
    def validate_basis(self) -> "FreshnessInfo":
        if self.basis == FreshnessBasis.unknown:
            if self.best_before is not None or self.estimated_note is not None:
                raise ValueError("unknown freshness cannot include best_before or estimated_note")
        elif self.best_before is None:
            raise ValueError(f"{self.basis.value} freshness requires best_before")
        if self.basis != FreshnessBasis.estimated and self.estimated_note is not None:
            raise ValueError("estimated_note is only valid for estimated freshness")
        return self


class InventoryQuantityTransition(BaseModel):
    before: float | None = None
    after: float | None = None
    delta: float | None = None
    unit: str | None = None
    changed: bool = False


class InventoryLocationTransition(BaseModel):
    before: StorageLocation | None = None
    after: StorageLocation | None = None
    changed: bool = False


class InventoryFreshnessTransition(BaseModel):
    before: FreshnessInfo | None = None
    after: FreshnessInfo | None = None
    changed: bool = False


class InventoryWorkflowReference(BaseModel):
    correlation_id: str | None = None
    causal_workflow_id: str | None = None
    causal_workflow_type: str | None = None


class InventoryCorrectionLinks(BaseModel):
    corrects_adjustment_id: str | None = None
    corrected_by_adjustment_ids: list[str] = Field(default_factory=list)
    is_correction: bool = False
    is_corrected: bool = False


class InventoryAdjustment(BaseModel):
    inventory_adjustment_id: str
    inventory_item_id: str
    household_id: str
    mutation_type: MutationType
    delta_quantity: float | None = None
    quantity_before: float | None = None
    quantity_after: float | None = None
    storage_location_before: StorageLocation | None = None
    storage_location_after: StorageLocation | None = None
    freshness_before: FreshnessInfo | None = None
    freshness_after: FreshnessInfo | None = None
    reason_code: ReasonCode
    actor_user_id: str
    correlation_id: str | None = None
    client_mutation_id: str | None = None
    causal_workflow_id: str | None = None
    causal_workflow_type: str | None = None
    corrects_adjustment_id: str | None = None
    note: str | None = None
    created_at: datetime
    primary_unit: str | None = None
    quantity_transition: InventoryQuantityTransition | None = None
    location_transition: InventoryLocationTransition | None = None
    freshness_transition: InventoryFreshnessTransition | None = None
    workflow_reference: InventoryWorkflowReference | None = None
    correction_links: InventoryCorrectionLinks = Field(default_factory=InventoryCorrectionLinks)


class InventoryHistorySummary(BaseModel):
    committed_adjustment_count: int = 0
    correction_count: int = 0
    latest_adjustment_id: str | None = None
    latest_mutation_type: MutationType | None = None
    latest_actor_user_id: str | None = None
    latest_created_at: datetime | None = None


class InventoryHistoryResponse(BaseModel):
    entries: list[InventoryAdjustment]
    total: int
    limit: int
    offset: int
    has_more: bool
    summary: InventoryHistorySummary


class InventoryItem(BaseModel):
    inventory_item_id: str
    household_id: str
    name: str
    storage_location: StorageLocation
    quantity_on_hand: float
    primary_unit: str
    freshness: FreshnessInfo = Field(default_factory=FreshnessInfo)
    is_active: bool = True
    version: int = 1
    created_at: datetime
    updated_at: datetime
    history_summary: InventoryHistorySummary | None = None
    latest_adjustment: InventoryAdjustment | None = None


class CreateItemCommand(BaseModel):
    household_id: str
    name: str
    storage_location: StorageLocation
    initial_quantity: float = Field(ge=0)
    primary_unit: str
    freshness: FreshnessInfo = Field(default_factory=FreshnessInfo)
    client_mutation_id: str
    note: str | None = None


class AdjustQuantityCommand(BaseModel):
    mutation_type: MutationType
    delta_quantity: float = Field(ge=0)
    reason_code: ReasonCode
    client_mutation_id: str
    version: int | None = Field(default=None, ge=1)
    note: str | None = None


class SetMetadataCommand(BaseModel):
    name: str | None = None
    storage_location: StorageLocation | None = None
    freshness: FreshnessInfo | None = None
    note: str | None = None
    client_mutation_id: str
    version: int | None = Field(default=None, ge=1)


class MoveLocationCommand(BaseModel):
    storage_location: StorageLocation
    freshness: FreshnessInfo | None = None
    client_mutation_id: str
    version: int | None = Field(default=None, ge=1)
    note: str | None = None


class ArchiveItemCommand(BaseModel):
    client_mutation_id: str
    version: int | None = Field(default=None, ge=1)
    note: str | None = None


class CorrectionCommand(BaseModel):
    delta_quantity: float | None = None
    reason_code: ReasonCode = ReasonCode.correction
    corrects_adjustment_id: str
    client_mutation_id: str
    version: int | None = Field(default=None, ge=1)
    note: str | None = None


class InventoryItemSummary(BaseModel):
    inventory_item_id: str
    household_id: str
    name: str
    storage_location: StorageLocation
    quantity_on_hand: float
    primary_unit: str
    freshness_basis: FreshnessBasis
    is_active: bool
    version: int
    updated_at: datetime


class InventoryListResponse(BaseModel):
    items: list[InventoryItemSummary]
    total: int


class AdjustmentReceiptResponse(BaseModel):
    inventory_adjustment_id: str
    inventory_item_id: str
    mutation_type: MutationType
    quantity_after: float | None
    version_after: int
    is_duplicate: bool = False
