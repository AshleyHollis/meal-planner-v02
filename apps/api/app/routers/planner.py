from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.dependencies.session import RequestSession, assert_household_access, get_request_session
from app.schemas.planner import (
    ConfirmedPlanView,
    DraftConfirmRequest,
    DraftCreateCommand,
    DraftPlanView,
    DraftSlotUpdateCommand,
    PlannerSlotView,
    SlotRegenerateCommand,
    SuggestionEnvelope,
    SuggestionRequestCommand,
)
from app.services.grocery_service import GroceryService, get_grocery_service
from app.services.planner_service import PlannerDomainError, PlannerService, get_planner_service

router = APIRouter(prefix="/api/v1/households/{household_id}/plans", tags=["planner"])
logger = logging.getLogger(__name__)


def _raise_planner_error(error: PlannerDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


def _trigger_grocery_refresh(
    grocery: GroceryService,
    *,
    household_id: str,
    actor_id: str,
    correlation_id: str | None,
) -> None:
    try:
        grocery.process_pending_plan_confirmed_events(household_id, actor_id=actor_id)
    except Exception:  # pragma: no cover - best-effort orchestration safety
        logger.exception(
            "grocery refresh orchestration failed",
            extra={
                "grocery_action": "auto_refresh",
                "grocery_outcome": "failed",
                "grocery_household_id": household_id,
                "grocery_actor_id": actor_id,
                "grocery_correlation_id": correlation_id,
            },
        )


@router.post(
    "/suggestion",
    response_model=SuggestionEnvelope,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a weekly AI suggestion",
)
def request_suggestion(
    household_id: str,
    command: SuggestionRequestCommand,
    background_tasks: BackgroundTasks,
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> SuggestionEnvelope:
    authorized_household_id = assert_household_access(session, household_id)
    try:
        envelope = planner.request_suggestion(
            authorized_household_id,
            actor_id=session.user.user_id,
            command=command,
        )
    except PlannerDomainError as error:
        _raise_planner_error(error)
    background_tasks.add_task(planner.complete_request, envelope.request_id)
    return envelope


@router.get(
    "/suggestion",
    response_model=SuggestionEnvelope,
    summary="Read the latest weekly AI suggestion for a household period",
)
def get_latest_suggestion(
    household_id: str,
    period: date = Query(...),
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> SuggestionEnvelope:
    authorized_household_id = assert_household_access(session, household_id)
    envelope = planner.get_latest_suggestion(authorized_household_id, period)
    if envelope is None:
        raise HTTPException(status_code=404, detail="AI suggestion not found")
    return envelope


@router.get(
    "/requests/{request_id}",
    response_model=SuggestionEnvelope,
    summary="Poll AI request status and result",
)
def get_request_status(
    household_id: str,
    request_id: str,
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> SuggestionEnvelope:
    authorized_household_id = assert_household_access(session, household_id)
    envelope = planner.get_request(authorized_household_id, request_id)
    if envelope is None:
        raise HTTPException(status_code=404, detail="AI request not found")
    return envelope


@router.post(
    "/draft",
    response_model=DraftPlanView,
    status_code=status.HTTP_201_CREATED,
    summary="Open a draft from an AI suggestion",
)
def open_draft_from_suggestion(
    household_id: str,
    command: DraftCreateCommand,
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> DraftPlanView:
    authorized_household_id = assert_household_access(session, household_id)
    try:
        return planner.open_draft_from_suggestion(authorized_household_id, command=command)
    except PlannerDomainError as error:
        _raise_planner_error(error)


@router.get(
    "/draft",
    response_model=DraftPlanView,
    summary="Read the active draft for a household period",
)
def get_draft(
    household_id: str,
    period: date = Query(...),
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> DraftPlanView:
    authorized_household_id = assert_household_access(session, household_id)
    draft = planner.get_draft(authorized_household_id, period)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft plan not found")
    return draft


@router.patch(
    "/draft/{draft_id}/slots/{slot_id}",
    response_model=PlannerSlotView,
    summary="Edit a draft slot",
)
def update_draft_slot(
    household_id: str,
    draft_id: str,
    slot_id: str,
    command: DraftSlotUpdateCommand,
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> PlannerSlotView:
    authorized_household_id = assert_household_access(session, household_id)
    try:
        return planner.update_draft_slot(
            authorized_household_id,
            draft_id=draft_id,
            slot_id=slot_id,
            command=command,
        )
    except PlannerDomainError as error:
        _raise_planner_error(error)


@router.post(
    "/draft/{draft_id}/slots/{slot_id}/revert",
    response_model=PlannerSlotView,
    summary="Restore the original AI suggestion for a draft slot",
)
def revert_draft_slot(
    household_id: str,
    draft_id: str,
    slot_id: str,
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> PlannerSlotView:
    authorized_household_id = assert_household_access(session, household_id)
    try:
        return planner.revert_draft_slot(
            authorized_household_id,
            draft_id=draft_id,
            slot_id=slot_id,
        )
    except PlannerDomainError as error:
        _raise_planner_error(error)


@router.post(
    "/draft/{draft_id}/slots/{slot_id}/regenerate",
    response_model=SuggestionEnvelope,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request per-slot AI regeneration",
)
def request_slot_regeneration(
    household_id: str,
    draft_id: str,
    slot_id: str,
    command: SlotRegenerateCommand,
    background_tasks: BackgroundTasks,
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> SuggestionEnvelope:
    authorized_household_id = assert_household_access(session, household_id)
    try:
        envelope = planner.request_slot_regeneration(
            authorized_household_id,
            draft_id=draft_id,
            slot_id=slot_id,
            actor_id=session.user.user_id,
            command=command,
        )
    except PlannerDomainError as error:
        _raise_planner_error(error)
    background_tasks.add_task(planner.complete_request, envelope.request_id)
    return envelope


@router.post(
    "/draft/{draft_id}/confirm",
    response_model=ConfirmedPlanView,
    summary="Confirm a draft plan",
)
def confirm_draft(
    household_id: str,
    draft_id: str,
    command: DraftConfirmRequest,
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
    grocery: GroceryService = Depends(get_grocery_service),
) -> ConfirmedPlanView:
    authorized_household_id = assert_household_access(session, household_id)
    try:
        result = planner.confirm_draft(
            authorized_household_id,
            draft_id=draft_id,
            actor_id=session.user.user_id,
            command=command,
        )
        _trigger_grocery_refresh(
            grocery,
            household_id=authorized_household_id,
            actor_id=session.user.user_id,
            correlation_id=command.client_mutation_id,
        )
        return result
    except PlannerDomainError as error:
        _raise_planner_error(error)


@router.get(
    "/confirmed",
    response_model=ConfirmedPlanView,
    summary="Read the latest confirmed plan for a household period",
)
def get_confirmed_plan(
    household_id: str,
    period: date = Query(...),
    session: RequestSession = Depends(get_request_session),
    planner: PlannerService = Depends(get_planner_service),
) -> ConfirmedPlanView:
    authorized_household_id = assert_household_access(session, household_id)
    plan = planner.get_confirmed_plan(authorized_household_id, period)
    if plan is None:
        raise HTTPException(status_code=404, detail="Confirmed plan not found")
    return plan
