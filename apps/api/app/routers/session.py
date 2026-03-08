"""
Session bootstrap router.

GET /api/v1/me is the frontend's entry point for discovering whether it has
an active session. The API owns all Auth0 interaction; the frontend must not
embed or import any Auth0 SDK.

Until the production Auth0 seam is wired, request-scoped session resolution
uses an explicit deterministic dev/test header seam. The contract shape stays
backend-owned so frontend and test authors can depend on it.
"""

from fastapi import APIRouter, Depends

from app.dependencies.session import RequestSession, get_request_session
from app.models.session import SessionResponse

router = APIRouter(prefix="/api/v1", tags=["session"])


@router.get(
    "/me",
    response_model=SessionResponse,
    summary="Session bootstrap — returns current session state",
)
def get_me(session: RequestSession = Depends(get_request_session)) -> SessionResponse:
    """
    Returns the caller's resolved session and household membership context.

    The API resolves identity exactly once per request via a backend-owned
    dependency. While production auth wiring is still being finalized, explicit
    `X-Dev-*` headers provide a deterministic dev/test seam.
    """
    return SessionResponse(authenticated=True, user=session.user)
