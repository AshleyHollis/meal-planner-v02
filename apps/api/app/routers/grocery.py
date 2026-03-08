from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.session import RequestSession, assert_household_access, get_request_session
from app.schemas.grocery import (
    GroceryListConfirmCommand,
    GroceryListDeriveCommand,
    GroceryListItemAdHocCreate,
    GroceryListQuantityAdjustCommand,
    GroceryListRead,
    GroceryListRemoveLineCommand,
    GroceryMutationResult,
    QueueableSyncMutation,
    SyncConflictDetailRead,
    SyncConflictKeepMineCommand,
    SyncConflictSummaryRead,
    SyncConflictUseServerCommand,
    SyncMutationOutcomeRead,
)
from app.services.grocery_service import GroceryDomainError, GroceryService, get_grocery_service

router = APIRouter(prefix="/api/v1/households/{household_id}/grocery", tags=["grocery"])


def _raise_grocery_error(error: GroceryDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.post(
    "/derive",
    response_model=GroceryMutationResult,
    status_code=status.HTTP_201_CREATED,
    summary="Derive a draft grocery list from the confirmed plan and inventory",
)
def derive_grocery_list(
    household_id: str,
    command: GroceryListDeriveCommand,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(update={"household_id": authorized_household_id})
    try:
        return grocery.derive_list(
            authorized_household_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.get(
    "",
    response_model=GroceryListRead,
    summary="Read the latest grocery list for a household period",
)
def get_current_grocery_list(
    household_id: str,
    period: date = Query(...),
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryListRead:
    authorized_household_id = assert_household_access(session, household_id)
    grocery_list = grocery.get_current_list(authorized_household_id, period)
    if grocery_list is None:
        raise HTTPException(status_code=404, detail="Grocery list not found")
    return grocery_list


@router.get(
    "/{grocery_list_id}",
    response_model=GroceryListRead,
    summary="Read grocery list detail by identifier",
)
def get_grocery_list_detail(
    household_id: str,
    grocery_list_id: str,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryListRead:
    authorized_household_id = assert_household_access(session, household_id)
    grocery_list = grocery.get_list(authorized_household_id, grocery_list_id)
    if grocery_list is None:
        raise HTTPException(status_code=404, detail="Grocery list not found")
    return grocery_list


@router.post(
    "/{grocery_list_id}/rederive",
    response_model=GroceryMutationResult,
    summary="Re-derive a grocery draft for the same plan period",
)
def rederive_grocery_list(
    household_id: str,
    grocery_list_id: str,
    command: GroceryListDeriveCommand,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(update={"household_id": authorized_household_id})
    try:
        return grocery.rederive_list(
            authorized_household_id,
            grocery_list_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.post(
    "/{grocery_list_id}/lines",
    response_model=GroceryMutationResult,
    status_code=status.HTTP_201_CREATED,
    summary="Add an ad hoc grocery line",
)
def add_ad_hoc_line(
    household_id: str,
    grocery_list_id: str,
    command: GroceryListItemAdHocCreate,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(
        update={
            "household_id": authorized_household_id,
            "grocery_list_id": grocery_list_id,
        }
    )
    try:
        return grocery.add_ad_hoc_item(
            authorized_household_id,
            grocery_list_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.patch(
    "/{grocery_list_id}/lines/{grocery_list_item_id}",
    response_model=GroceryMutationResult,
    summary="Adjust a grocery line quantity override",
)
def adjust_grocery_line(
    household_id: str,
    grocery_list_id: str,
    grocery_list_item_id: str,
    command: GroceryListQuantityAdjustCommand,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(
        update={
            "household_id": authorized_household_id,
            "grocery_list_item_id": grocery_list_item_id,
        }
    )
    try:
        return grocery.adjust_line(
            authorized_household_id,
            grocery_list_id,
            grocery_list_item_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.post(
    "/{grocery_list_id}/lines/{grocery_list_item_id}/remove",
    response_model=GroceryMutationResult,
    summary="Remove a grocery line",
)
def remove_grocery_line(
    household_id: str,
    grocery_list_id: str,
    grocery_list_item_id: str,
    command: GroceryListRemoveLineCommand,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(
        update={
            "household_id": authorized_household_id,
            "grocery_list_item_id": grocery_list_item_id,
        }
    )
    try:
        return grocery.remove_line(
            authorized_household_id,
            grocery_list_id,
            grocery_list_item_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.post(
    "/{grocery_list_id}/confirm",
    response_model=GroceryMutationResult,
    summary="Confirm a grocery list for the upcoming trip",
)
def confirm_grocery_list(
    household_id: str,
    grocery_list_id: str,
    command: GroceryListConfirmCommand,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(
        update={
            "household_id": authorized_household_id,
            "grocery_list_id": grocery_list_id,
        }
    )
    try:
        return grocery.confirm_list(
            authorized_household_id,
            grocery_list_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.post(
    "/sync/upload",
    response_model=list[SyncMutationOutcomeRead],
    summary="Upload queued offline grocery mutations for replay",
)
def upload_sync_mutations(
    household_id: str,
    mutations: list[QueueableSyncMutation],
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> list[SyncMutationOutcomeRead]:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_mutations = [
        mutation.model_copy(
            update={
                "household_id": authorized_household_id,
                "actor_id": session.user.user_id,
            }
        )
        for mutation in mutations
    ]
    try:
        return grocery.upload_sync_mutations(
            authorized_household_id,
            actor_id=session.user.user_id,
            mutations=authorized_mutations,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.get(
    "/sync/conflicts",
    response_model=list[SyncConflictSummaryRead],
    summary="List persisted grocery sync conflicts for a household",
)
def list_sync_conflicts(
    household_id: str,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> list[SyncConflictSummaryRead]:
    authorized_household_id = assert_household_access(session, household_id)
    return grocery.list_sync_conflicts(authorized_household_id)


@router.get(
    "/sync/conflicts/{conflict_id}",
    response_model=SyncConflictDetailRead,
    summary="Read a persisted grocery sync conflict",
)
def get_sync_conflict(
    household_id: str,
    conflict_id: str,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> SyncConflictDetailRead:
    authorized_household_id = assert_household_access(session, household_id)
    conflict = grocery.get_sync_conflict(authorized_household_id, conflict_id)
    if conflict is None:
        raise HTTPException(status_code=404, detail="Sync conflict not found")
    return conflict


@router.post(
    "/sync/conflicts/{conflict_id}/resolve-keep-mine",
    response_model=GroceryMutationResult,
    summary="Resolve a grocery sync conflict by replaying the local intent",
)
def resolve_sync_conflict_keep_mine(
    household_id: str,
    conflict_id: str,
    command: SyncConflictKeepMineCommand,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(
        update={
            "conflict_id": conflict_id,
            "household_id": authorized_household_id,
        }
    )
    try:
        return grocery.resolve_sync_conflict_keep_mine(
            authorized_household_id,
            conflict_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)


@router.post(
    "/sync/conflicts/{conflict_id}/resolve-use-server",
    response_model=GroceryMutationResult,
    summary="Resolve a grocery sync conflict by accepting the current server state",
)
def resolve_sync_conflict_use_server(
    household_id: str,
    conflict_id: str,
    command: SyncConflictUseServerCommand,
    session: RequestSession = Depends(get_request_session),
    grocery: GroceryService = Depends(get_grocery_service),
) -> GroceryMutationResult:
    authorized_household_id = assert_household_access(session, household_id)
    authorized_command = command.model_copy(
        update={
            "conflict_id": conflict_id,
            "household_id": authorized_household_id,
        }
    )
    try:
        return grocery.resolve_sync_conflict_use_server(
            authorized_household_id,
            conflict_id,
            actor_id=session.user.user_id,
            command=authorized_command,
        )
    except GroceryDomainError as error:
        _raise_grocery_error(error)
