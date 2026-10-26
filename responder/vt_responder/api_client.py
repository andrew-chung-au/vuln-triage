"""Read-only backend API client: exactly the two operations the responder token may call.

``GET /responder/findings/{id}`` and ``GET /responder/notification-jobs?findingId=``
(`_docs/api.md` section Responder). There is no other method, so no write is possible
from here. The token is sent as a bearer header and is never logged; error
messages carry the status code only, never a response body (which could hold
advisory-derived text).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class ApiError(RuntimeError):
    def __init__(self, status: int | None, what: str) -> None:
        super().__init__(f"{what}: status {status}" if status is not None else what)
        self.status = status


class ResponderApi:
    def __init__(self, base_url: str, token: str, *, transport: httpx.BaseTransport | None = None,
                 timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, what: str, **params: str) -> Any:
        try:
            response = self._client.get(path, params=params or None)
        except httpx.HTTPError as exc:
            raise ApiError(None, f"{what}: request failed ({type(exc).__name__})") from None
        if response.status_code != 200:
            raise ApiError(response.status_code, what)
        try:
            return response.json()
        except ValueError:
            raise ApiError(response.status_code, f"{what}: response is not JSON") from None

    def get_finding(self, finding_id: str) -> dict[str, Any]:
        """``responderGetFinding``. Raises ``ApiError(404)`` for an unknown id."""
        data = self._get(f"/responder/findings/{quote(finding_id, safe='')}", "get finding")
        if not isinstance(data, dict):
            raise ApiError(200, "get finding: unexpected shape")
        return data

    def list_jobs(self, finding_id: str) -> list[dict[str, Any]]:
        """``responderListNotificationJobs``. An unknown id returns ``[]``."""
        data = self._get("/responder/notification-jobs", "list notification jobs", findingId=finding_id)
        if not isinstance(data, list):
            raise ApiError(200, "list notification jobs: unexpected shape")
        return data
