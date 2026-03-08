"""
Session and identity models.

The API owns all Auth0 interaction. The frontend calls GET /api/v1/me to
bootstrap session state. This module defines the contract shape so downstream
consumers (frontend, tests) can depend on stable field names.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class HouseholdRole(str, Enum):
    owner = "owner"
    member = "member"


class HouseholdMembership(BaseModel):
    household_id: str
    household_name: str
    role: HouseholdRole


class SessionUser(BaseModel):
    user_id: str
    email: str
    display_name: str
    active_household_id: str
    households: list[HouseholdMembership] = Field(default_factory=list)


class SessionResponse(BaseModel):
    """
     Contract returned by GET /api/v1/me.

    authenticated=True means the API resolved a caller identity plus an active
    household membership for the current request.
    """

    authenticated: bool
    user: SessionUser | None = None
