"""
Tests for GET /api/v1/me session bootstrap endpoint.

Covers:
- Authenticated request-scoped session bootstrap.
- 401 for unauthenticated requests.
- 403 when the active household is not part of the caller's memberships.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.dependencies.session import (
    DEV_ACTIVE_HOUSEHOLD_ID_HEADER,
    DEV_ACTIVE_HOUSEHOLD_NAME_HEADER,
    DEV_ACTIVE_HOUSEHOLD_ROLE_HEADER,
    DEV_HOUSEHOLDS_HEADER,
    DEV_USER_EMAIL_HEADER,
    DEV_USER_ID_HEADER,
    DEV_USER_NAME_HEADER,
)
from app.main import app

HOUSEHOLD = "household-abc"


def _session_headers(
    *,
    household_id: str = HOUSEHOLD,
    memberships: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    headers = {
        DEV_USER_ID_HEADER: "user-123",
        DEV_USER_EMAIL_HEADER: "ashley@example.com",
        DEV_USER_NAME_HEADER: "Ashley",
        DEV_ACTIVE_HOUSEHOLD_ID_HEADER: household_id,
        DEV_ACTIVE_HOUSEHOLD_NAME_HEADER: "Primary Household",
        DEV_ACTIVE_HOUSEHOLD_ROLE_HEADER: "owner",
    }
    if memberships is not None:
        headers[DEV_HOUSEHOLDS_HEADER] = json.dumps(memberships)
    return headers


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_get_me_returns_authenticated_request_session(client: TestClient) -> None:
    response = client.get("/api/v1/me", headers=_session_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["user_id"] == "user-123"
    assert data["user"]["active_household_id"] == HOUSEHOLD
    assert data["user"]["households"][0]["household_id"] == HOUSEHOLD


def test_get_me_returns_401_without_session(client: TestClient) -> None:
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "unauthenticated",
        "message": "No authenticated household session was resolved for this request.",
    }


def test_get_me_returns_403_when_active_household_is_not_a_membership(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/me",
        headers=_session_headers(
            memberships=[
                {
                    "household_id": "different-household",
                    "household_name": "Different Household",
                    "role": "member",
                }
            ]
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "household_access_forbidden",
        "message": "The active household selected for this request is not one of the caller's memberships.",
    }
