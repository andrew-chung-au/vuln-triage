"""The responder's webhook receiver (FastAPI).

``POST /webhook/grafana`` receives Grafana's webhook contact-point body.
VERIFY: the exact Grafana 11.x body and authorization header. This code reads
the documented common shape ``{"status", "alerts": [{"status", "fingerprint",
"labels": {"finding_id", "tier", ...}}]}`` and an ``Authorization: Bearer``
header (the contact point's "authorization" setting).

Order of checks: bearer token (401, nothing else is read), body size (413),
JSON shape (400), then per alert: resolved is ignored, a repeated fingerprint
is ignored, otherwise one stub run.

Run it: ``uvicorn vt_responder.app:create_app_from_env --factory``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .actlog import ActionLog
from .api_client import ResponderApi
from .config import ConfigError, Settings
from .fakes import FakeGit, FakeGitHub
from .guard import FingerprintGuard
from .runner import StubRunner

# Fingerprints become a branch name and finding ids become a URL path segment,
# so both are restricted to a short safe alphabet.
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class _BadPayload(ValueError):
    pass


def _token_ok(header: str | None, secret: str) -> bool:
    if not header:
        return False
    scheme, _, presented = header.partition(" ")
    if scheme.lower() != "bearer" or not presented:
        return False
    # Hash both sides so the comparison is constant-time regardless of length.
    a = hashlib.sha256(presented.strip().encode("utf-8")).digest()
    b = hashlib.sha256(secret.encode("utf-8")).digest()
    return hmac.compare_digest(a, b)


def _parse_alerts(body: bytes) -> list[dict[str, Any]]:
    """Validate the whole payload; return the firing alerts as ``{fingerprint, finding_id}``."""
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise _BadPayload("body is not valid JSON") from None
    if not isinstance(data, dict):
        raise _BadPayload("body must be a JSON object")
    alerts = data.get("alerts")
    if not isinstance(alerts, list) or not alerts:
        raise _BadPayload("alerts must be a non-empty list")
    top_status = data.get("status")
    if top_status not in ("firing", "resolved"):
        raise _BadPayload("status must be 'firing' or 'resolved'")
    out: list[dict[str, Any]] = []
    for alert in alerts:
        if not isinstance(alert, dict):
            raise _BadPayload("each alert must be an object")
        status = alert.get("status", top_status)
        if status not in ("firing", "resolved"):
            raise _BadPayload("alert status must be 'firing' or 'resolved'")
        fingerprint = alert.get("fingerprint")
        if not isinstance(fingerprint, str) or not _SAFE_ID.match(fingerprint):
            raise _BadPayload("alert fingerprint is missing or malformed")
        labels = alert.get("labels", {})
        if not isinstance(labels, dict):
            raise _BadPayload("alert labels must be an object")
        finding_id = labels.get("finding_id")
        if finding_id is not None and (not isinstance(finding_id, str) or not _SAFE_ID.match(finding_id)):
            raise _BadPayload("finding_id label is malformed")
        out.append({"status": status, "fingerprint": fingerprint, "finding_id": finding_id})
    return out


async def _read_capped(request: Request, limit: int) -> bytes | None:
    """Read the body, or return None as soon as it is over ``limit`` bytes."""
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > limit:
                return None
        except ValueError:
            pass
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def create_app(settings: Settings, *, api: ResponderApi | None = None, git: FakeGit | None = None,
               github: FakeGitHub | None = None, log: ActionLog | None = None) -> FastAPI:
    if settings.mode != "stub":
        raise ConfigError("only RESPONDER_MODE=stub is implemented here; the real runner is task 28d (#221)")
    log = log or ActionLog()
    api = api or ResponderApi(settings.api_url, settings.api_token)
    git = git or FakeGit()
    github = github or FakeGitHub()
    guard = FingerprintGuard(settings.state_file)
    runner = StubRunner(api, git, github, log)

    app = FastAPI(title="VulnTriage responder", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.git = git
    app.state.github = github
    app.state.guard = guard

    def handle(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for alert in alerts:
            fp, fid = alert["fingerprint"], alert["finding_id"]
            if alert["status"] == "resolved":
                log.emit("alert_ignored", outcome="resolved", fingerprint=fp, finding_id=fid)
                results.append({"fingerprint": fp, "outcome": "resolved_ignored"})
                continue
            if not guard.claim(fp):
                log.emit("alert_ignored", outcome="repeat", fingerprint=fp, finding_id=fid)
                results.append({"fingerprint": fp, "outcome": "repeat_ignored"})
                continue
            outcome = runner.run(fp, fid)
            if outcome == "error":
                guard.release(fp)  # a re-sent alert may retry a run that failed
            results.append({"fingerprint": fp, "outcome": outcome})
        return results

    @app.post("/webhook/grafana")
    async def grafana_webhook(request: Request) -> JSONResponse:
        if not _token_ok(request.headers.get("authorization"), settings.webhook_secret):
            log.emit("webhook_rejected", outcome="401")
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        body = await _read_capped(request, settings.max_body_bytes)
        if body is None:
            log.emit("webhook_rejected", outcome="413")
            return JSONResponse({"error": "payload too large"}, status_code=413)
        try:
            alerts = _parse_alerts(body)
        except _BadPayload as exc:
            log.emit("webhook_rejected", outcome="400")
            return JSONResponse({"error": str(exc)}, status_code=400)
        results = await run_in_threadpool(handle, alerts)
        return JSONResponse({"results": results})

    return app


def create_app_from_env() -> FastAPI:
    """Uvicorn factory. Raises ``ConfigError`` (refuses to start) on a bad mode."""
    return create_app(Settings.from_env())
