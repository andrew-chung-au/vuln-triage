"""Bearer service-token guards for the n8n, MCP and responder operations (#83).

Each service operation lists exactly one credential. The guard enforces the
contract's status order for service operations (``_docs/api.md`` § Status
codes): ``401`` for a missing or invalid credential, then ``403`` for a valid
credential the operation does not list (another service token, or a session
cookie). There is no CSRF step for bearer operations.

A credential is "valid" when it matches one of the configured service tokens.
A session cookie on a service operation is a wrong consumer, so ``403``. Tokens
are compared in constant time.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from vulntriage.api.security import COOKIE_NAME
from vulntriage.api.service_settings import (
    get_mcp_api_token,
    get_n8n_api_token,
    get_responder_api_token,
)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "unauthenticated", "message": "No valid credential."},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "forbidden", "message": "The request is not allowed."},
)


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if header is None:
        return None
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def _matches(token: str | None, candidate: str) -> bool:
    return token is not None and secrets.compare_digest(token, candidate)


def _all_known_tokens() -> list[str]:
    return [t for t in (get_n8n_api_token(), get_mcp_api_token(),
                        get_responder_api_token()) if t]


def _require_service_token(request: Request, expected: str | None) -> None:
    """Allow only ``expected``; 401 missing/invalid, 403 wrong consumer.

    ``expected`` is the operation's configured token (None when unset, so no
    credential can satisfy it and every caller is refused with 401/403).
    """
    presented = _bearer(request)
    if presented is None:
        # No bearer: a session cookie is a wrong consumer (403); nothing is 401.
        if request.cookies.get(COOKIE_NAME):
            raise _FORBIDDEN
        raise _UNAUTHENTICATED
    if expected is not None and _matches(expected, presented):
        return
    # A valid token for another consumer is 403; an unknown token is 401.
    if any(_matches(known, presented) for known in _all_known_tokens()):
        raise _FORBIDDEN
    raise _UNAUTHENTICATED


def require_n8n(request: Request) -> None:
    _require_service_token(request, get_n8n_api_token())


def require_mcp(request: Request) -> None:
    _require_service_token(request, get_mcp_api_token())


def require_responder(request: Request) -> None:
    _require_service_token(request, get_responder_api_token())


def dependency(guard: Callable[[Request], None]) -> Callable[[Request], None]:
    """Wrap a guard as a FastAPI dependency (kept explicit for readability)."""
    return guard
