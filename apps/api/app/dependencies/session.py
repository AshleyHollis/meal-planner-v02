"""
Request-scoped session dependency.

The long-term production path is backend-owned Auth0 session or bearer-token
validation. Until that wiring is complete, the API exposes an explicit
deterministic dev/test seam via `X-Dev-*` headers so routes can resolve caller
identity and active household membership once per request without trusting
client-owned household IDs in business payloads.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ValidationError

from app.models.session import HouseholdMembership, HouseholdRole, SessionUser

DEV_USER_ID_HEADER = "X-Dev-User-Id"
DEV_USER_EMAIL_HEADER = "X-Dev-User-Email"
DEV_USER_NAME_HEADER = "X-Dev-User-Name"
DEV_ACTIVE_HOUSEHOLD_ID_HEADER = "X-Dev-Active-Household-Id"
DEV_ACTIVE_HOUSEHOLD_NAME_HEADER = "X-Dev-Active-Household-Name"
DEV_ACTIVE_HOUSEHOLD_ROLE_HEADER = "X-Dev-Active-Household-Role"
DEV_HOUSEHOLDS_HEADER = "X-Dev-Households"
logger = logging.getLogger(__name__)


class RequestSession(BaseModel):
    user: SessionUser
    active_household: HouseholdMembership


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "unauthenticated",
            "message": "No authenticated household session was resolved for this request.",
        },
    )


def _forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "household_access_forbidden",
            "message": message,
        },
    )


def _normalize_memberships(
    *,
    active_household_id: str,
    active_household_name: str,
    active_household_role: HouseholdRole,
    raw_households: str | None,
) -> list[HouseholdMembership]:
    if raw_households is None:
        return [
            HouseholdMembership(
                household_id=active_household_id,
                household_name=active_household_name,
                role=active_household_role,
            )
        ]

    try:
        payload = json.loads(raw_households)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_dev_session_headers",
                "message": f"{DEV_HOUSEHOLDS_HEADER} must be valid JSON.",
            },
        ) from error

    try:
        memberships = [
            HouseholdMembership.model_validate(item)
            for item in payload
        ]
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_dev_session_headers",
                "message": f"{DEV_HOUSEHOLDS_HEADER} did not match the expected membership shape.",
            },
        ) from error

    active_membership = next(
        (membership for membership in memberships if membership.household_id == active_household_id),
        None,
    )
    if active_membership is None:
        raise _forbidden(
            "The active household selected for this request is not one of the caller's memberships."
        )

    return [
        active_membership,
        *[membership for membership in memberships if membership.household_id != active_household_id],
    ]


def _resolve_dev_session(request: Request) -> RequestSession | None:
    headers = request.headers
    user_id = headers.get(DEV_USER_ID_HEADER)
    email = headers.get(DEV_USER_EMAIL_HEADER)
    active_household_id = headers.get(DEV_ACTIVE_HOUSEHOLD_ID_HEADER)
    if not user_id or not email or not active_household_id:
        return None

    display_name = headers.get(DEV_USER_NAME_HEADER) or email
    active_household_name = headers.get(DEV_ACTIVE_HOUSEHOLD_NAME_HEADER) or "Household"
    active_household_role = HouseholdRole(
        headers.get(DEV_ACTIVE_HOUSEHOLD_ROLE_HEADER, HouseholdRole.member.value)
    )
    memberships = _normalize_memberships(
        active_household_id=active_household_id,
        active_household_name=active_household_name,
        active_household_role=active_household_role,
        raw_households=headers.get(DEV_HOUSEHOLDS_HEADER),
    )

    active_household = memberships[0]
    return RequestSession(
        user=SessionUser(
            user_id=user_id,
            email=email,
            display_name=display_name,
            active_household_id=active_household.household_id,
            households=memberships,
        ),
        active_household=active_household,
    )


def get_request_session(request: Request) -> RequestSession:
    cached = getattr(request.state, "request_session", None)
    if cached is not None:
        return cached

    session = _resolve_dev_session(request)
    if session is None:
        raise _unauthenticated()

    request.state.request_session = session
    return session


def assert_household_access(
    session: RequestSession,
    requested_household_id: str | None,
) -> str:
    active_household_id = session.active_household.household_id
    if requested_household_id is None or requested_household_id == active_household_id:
        return active_household_id

    logger.warning(
        "household access forbidden",
        extra={
            "session_user_id": session.user.user_id,
            "session_active_household_id": active_household_id,
            "session_requested_household_id": requested_household_id,
        },
    )
    raise _forbidden(
        "The requested household does not match the active household bound to this request."
    )


def get_request_household_id(
    household_id: Annotated[
        str | None,
        Query(
            description="Legacy household scope seam. When supplied it must match the active request household.",
        ),
    ] = None,
    session: RequestSession = Depends(get_request_session),
) -> str:
    return assert_household_access(session, household_id)
