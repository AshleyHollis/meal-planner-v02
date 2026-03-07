"""
Inventory router.

Exposes the authoritative inventory mutation and query surface for Wave 1.
All mutations produce an explicit adjustment event (append-only audit log)
and return an AdjustmentReceiptResponse so callers can confirm idempotent
replay.

Route structure:
  GET    /api/v1/inventory                          list items
  POST   /api/v1/inventory                          create item
  GET    /api/v1/inventory/{item_id}                get item
  PATCH  /api/v1/inventory/{item_id}/metadata       update non-quantity fields
  POST   /api/v1/inventory/{item_id}/adjustments    change quantity
  POST   /api/v1/inventory/{item_id}/move           move to different location
  POST   /api/v1/inventory/{item_id}/archive        archive item
  POST   /api/v1/inventory/{item_id}/corrections    apply compensating correction
  GET    /api/v1/inventory/{item_id}/history        adjustment history

Auth note: the backend now resolves caller identity and active household once
per request. Legacy household_id fields may still appear in bodies / query
params during the transition, but they are validated against the active
request household rather than trusted as authoritative input.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies.session import (
    RequestSession,
    assert_household_access,
    get_request_household_id,
    get_request_session,
)
from app.schemas.enums import MutationType
from app.schemas.inventory import (
    AdjustQuantityCommand,
    AdjustmentReceiptResponse,
    ArchiveItemCommand,
    CorrectionCommand,
    CreateItemCommand,
    InventoryHistoryResponse,
    InventoryItem,
    InventoryItemSummary,
    InventoryListResponse,
    MoveLocationCommand,
    SetMetadataCommand,
)
from app.services.grocery_service import GroceryService, get_grocery_service
from app.services.inventory_store import InventoryStore, get_inventory_store
from app.services.inventory_store import InventoryConflictError, InventoryDomainError

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])
logger = logging.getLogger(__name__)

def _inventory_conflict_detail(error: InventoryConflictError) -> dict[str, object]:
    return {
        "code": "stale_inventory_version",
        "message": "The inventory item changed since the client last read it.",
        "expected_version": error.expected_version,
        "current_version": error.current_version,
    }


def _inventory_domain_detail(error: InventoryDomainError) -> dict[str, str]:
    return {
        "code": error.code,
        "message": error.message,
    }


def _refresh_grocery_stale_drafts(
    grocery: GroceryService,
    *,
    household_id: str,
    actor_id: str,
    correlation_id: str | None,
) -> None:
    try:
        grocery.refresh_stale_drafts(household_id, actor_id=actor_id, correlation_id=correlation_id)
    except Exception:  # pragma: no cover - best-effort orchestration safety
        logger.exception(
            "grocery stale refresh failed",
            extra={
                "grocery_action": "stale_refresh",
                "grocery_outcome": "failed",
                "grocery_household_id": household_id,
                "grocery_actor_id": actor_id,
                "grocery_correlation_id": correlation_id,
            },
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=InventoryListResponse,
    summary="List inventory items for a household",
)
def list_inventory(
    household_id: str = Depends(get_request_household_id),
    include_archived: bool = Query(False),
    store: InventoryStore = Depends(get_inventory_store),
) -> InventoryListResponse:
    items = store.list_items(household_id, include_archived=include_archived)
    summaries = [
        InventoryItemSummary(
            inventory_item_id=it.inventory_item_id,
            household_id=it.household_id,
            name=it.name,
            storage_location=it.storage_location,
            quantity_on_hand=it.quantity_on_hand,
            primary_unit=it.primary_unit,
            freshness_basis=it.freshness.basis,
            is_active=it.is_active,
            version=it.version,
            updated_at=it.updated_at,
        )
        for it in items
    ]
    return InventoryListResponse(items=summaries, total=len(summaries))


@router.get(
    "/{item_id}",
    response_model=InventoryItem,
    summary="Get a single inventory item",
)
def get_inventory_item(
    item_id: str,
    household_id: str = Depends(get_request_household_id),
    store: InventoryStore = Depends(get_inventory_store),
) -> InventoryItem:
    item = store.get_item(household_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.get(
    "/{item_id}/history",
    response_model=InventoryHistoryResponse,
    summary="Get adjustment history for an item",
)
def get_item_history(
    item_id: str,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    household_id: str = Depends(get_request_household_id),
    store: InventoryStore = Depends(get_inventory_store),
) -> InventoryHistoryResponse:
    item = store.get_item(household_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    try:
        return store.get_history(household_id, item_id, limit=limit, offset=offset)
    except InventoryDomainError as error:
        if error.code == "inventory_item_not_found":
            raise HTTPException(status_code=404, detail="Inventory item not found") from error
        raise HTTPException(status_code=422, detail=_inventory_domain_detail(error)) from error


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AdjustmentReceiptResponse,
    status_code=201,
    summary="Create a new inventory item",
)
def create_inventory_item(
    command: CreateItemCommand,
    session: RequestSession = Depends(get_request_session),
    store: InventoryStore = Depends(get_inventory_store),
    grocery: GroceryService = Depends(get_grocery_service),
) -> AdjustmentReceiptResponse:
    household_id = assert_household_access(session, command.household_id)
    authorized_command = command.model_copy(update={"household_id": household_id})
    receipt = store.create_item(authorized_command, actor_user_id=session.user.user_id)
    _refresh_grocery_stale_drafts(
        grocery,
        household_id=household_id,
        actor_id=session.user.user_id,
        correlation_id=authorized_command.client_mutation_id,
    )
    return receipt


@router.patch(
    "/{item_id}/metadata",
    response_model=AdjustmentReceiptResponse,
    summary="Update non-quantity fields on an inventory item",
)
def update_item_metadata(
    item_id: str,
    household_id: str = Depends(get_request_household_id),
    session: RequestSession = Depends(get_request_session),
    command: SetMetadataCommand = ...,
    store: InventoryStore = Depends(get_inventory_store),
    grocery: GroceryService = Depends(get_grocery_service),
) -> AdjustmentReceiptResponse:
    try:
        receipt = store.set_metadata(
            household_id,
            item_id,
            command,
            actor_user_id=session.user.user_id,
        )
    except InventoryConflictError as error:
        raise HTTPException(status_code=409, detail=_inventory_conflict_detail(error)) from error
    except InventoryDomainError as error:
        raise HTTPException(status_code=422, detail=_inventory_domain_detail(error)) from error
    if receipt is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    _refresh_grocery_stale_drafts(
        grocery,
        household_id=household_id,
        actor_id=session.user.user_id,
        correlation_id=command.client_mutation_id,
    )
    return receipt


@router.post(
    "/{item_id}/adjustments",
    response_model=AdjustmentReceiptResponse,
    status_code=201,
    summary="Adjust quantity (increase / decrease / set)",
)
def adjust_item_quantity(
    item_id: str,
    household_id: str = Depends(get_request_household_id),
    session: RequestSession = Depends(get_request_session),
    command: AdjustQuantityCommand = ...,
    store: InventoryStore = Depends(get_inventory_store),
    grocery: GroceryService = Depends(get_grocery_service),
) -> AdjustmentReceiptResponse:
    allowed = {
        MutationType.increase_quantity,
        MutationType.decrease_quantity,
        MutationType.set_quantity,
    }
    if command.mutation_type not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"mutation_type must be one of {[t.value for t in allowed]}",
        )
    try:
        receipt = store.adjust_quantity(
            household_id,
            item_id,
            command,
            actor_user_id=session.user.user_id,
        )
    except InventoryConflictError as error:
        raise HTTPException(status_code=409, detail=_inventory_conflict_detail(error)) from error
    except InventoryDomainError as error:
        raise HTTPException(status_code=422, detail=_inventory_domain_detail(error)) from error
    if receipt is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    _refresh_grocery_stale_drafts(
        grocery,
        household_id=household_id,
        actor_id=session.user.user_id,
        correlation_id=command.client_mutation_id,
    )
    return receipt


@router.post(
    "/{item_id}/move",
    response_model=AdjustmentReceiptResponse,
    status_code=201,
    summary="Move item to a different storage location",
)
def move_item_location(
    item_id: str,
    household_id: str = Depends(get_request_household_id),
    session: RequestSession = Depends(get_request_session),
    command: MoveLocationCommand = ...,
    store: InventoryStore = Depends(get_inventory_store),
    grocery: GroceryService = Depends(get_grocery_service),
) -> AdjustmentReceiptResponse:
    try:
        receipt = store.move_location(
            household_id,
            item_id,
            command,
            actor_user_id=session.user.user_id,
        )
    except InventoryConflictError as error:
        raise HTTPException(status_code=409, detail=_inventory_conflict_detail(error)) from error
    except InventoryDomainError as error:
        raise HTTPException(status_code=422, detail=_inventory_domain_detail(error)) from error
    if receipt is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    _refresh_grocery_stale_drafts(
        grocery,
        household_id=household_id,
        actor_id=session.user.user_id,
        correlation_id=command.client_mutation_id,
    )
    return receipt


@router.post(
    "/{item_id}/archive",
    response_model=AdjustmentReceiptResponse,
    status_code=201,
    summary="Archive an inventory item",
)
def archive_item(
    item_id: str,
    household_id: str = Depends(get_request_household_id),
    session: RequestSession = Depends(get_request_session),
    command: ArchiveItemCommand = ...,
    store: InventoryStore = Depends(get_inventory_store),
    grocery: GroceryService = Depends(get_grocery_service),
) -> AdjustmentReceiptResponse:
    try:
        receipt = store.archive_item(
            household_id,
            item_id,
            command,
            actor_user_id=session.user.user_id,
        )
    except InventoryConflictError as error:
        raise HTTPException(status_code=409, detail=_inventory_conflict_detail(error)) from error
    except InventoryDomainError as error:
        raise HTTPException(status_code=422, detail=_inventory_domain_detail(error)) from error
    if receipt is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    _refresh_grocery_stale_drafts(
        grocery,
        household_id=household_id,
        actor_id=session.user.user_id,
        correlation_id=command.client_mutation_id,
    )
    return receipt


@router.post(
    "/{item_id}/corrections",
    response_model=AdjustmentReceiptResponse,
    status_code=201,
    summary="Apply a compensating correction to an inventory item",
)
def apply_correction(
    item_id: str,
    household_id: str = Depends(get_request_household_id),
    session: RequestSession = Depends(get_request_session),
    command: CorrectionCommand = ...,
    store: InventoryStore = Depends(get_inventory_store),
    grocery: GroceryService = Depends(get_grocery_service),
) -> AdjustmentReceiptResponse:
    try:
        receipt = store.apply_correction(
            household_id,
            item_id,
            command,
            actor_user_id=session.user.user_id,
        )
    except InventoryConflictError as error:
        raise HTTPException(status_code=409, detail=_inventory_conflict_detail(error)) from error
    except InventoryDomainError as error:
        raise HTTPException(status_code=422, detail=_inventory_domain_detail(error)) from error
    if receipt is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    _refresh_grocery_stale_drafts(
        grocery,
        household_id=household_id,
        actor_id=session.user.user_id,
        correlation_id=command.client_mutation_id,
    )
    return receipt
