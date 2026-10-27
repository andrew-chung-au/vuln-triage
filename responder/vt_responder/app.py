"""The responder's webhook receiver (FastAPI).

``POST /webhook/grafana`` receives Grafana's webhook contact-point body.
VERIFY: the exact Grafana 11.x body and authorization header. This code reads
the documented common shape ``{"status", "alerts": [{"status", "fingerprint",
"labels": {"finding_id", "tier", ...}}]}`` and an ``Authorization: Bearer``
header (the contact point's "authorization" setting).

Order of checks: bearer token (401, nothing else is read), body size (413),
JSON shape (400), then per alert: resolved starts no run and forgets the
fingerprint (deferred until the run ends if one is in flight), an alert with neither a
fingerprint nor a ``finding_id`` (Grafana's test notification may carry no
fingerprint) logs ``no_change`` with an explanation and touches nothing (no
run, no API read, no repeat-guard claim; US-15), a repeated fingerprint is
ignored, otherwise one stub run.

Real mode (#241) answers ``accepted`` straight away and runs the agent in the
background (``_BackgroundRuns``): the fingerprint stays claimed and in flight until
the run ends; a run that raises, times out, is cancelled or ends ``error`` releases
it (and counts toward ``RESPONDER_MAX_FAILED_RUNS``, after which firings log
``retry_cap_reached`` until the alert resolves). At most
``RESPONDER_MAX_CONCURRENT_RUNS`` run at once; a second alert beyond that is
accepted and queued, up to ``RESPONDER_MAX_QUEUED_RUNS``, and only past that is it
refused (503, claim released, so Grafana's retry runs it). A run lost to a restart
is released at the next start (``run_lost_on_restart``), never stuck.

400 stays for a fingerprint or ``finding_id`` that is present but malformed,
and for a ``finding_id`` with no fingerprint (a real run cannot be guarded
against repeats without one).

Run it: ``uvicorn vt_responder.app:create_app_from_env --factory``.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import threading
from concurrent.futures import CancelledError, ThreadPoolExecutor
from contextlib import asynccontextmanager
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
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


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
        if fingerprint is not None and (not isinstance(fingerprint, str) or not _SAFE_ID.fullmatch(fingerprint)):
            raise _BadPayload("alert fingerprint is malformed")
        labels = alert.get("labels", {})
        if not isinstance(labels, dict):
            raise _BadPayload("alert labels must be an object")
        finding_id = labels.get("finding_id")
        if finding_id is not None and (not isinstance(finding_id, str) or not _SAFE_ID.fullmatch(finding_id)):
            raise _BadPayload("finding_id label is malformed")
        if fingerprint is None and finding_id is not None:
            # A run for a real finding must be guarded against repeats, and the
            # guard is keyed by fingerprint, so this alert cannot be handled safely.
            raise _BadPayload("alert has a finding_id but no fingerprint")
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


class _BackgroundRuns:
    """Real mode (#241): runs the agent off the request, bounded, and always ends the claim.

    The webhook claims the fingerprint (``FingerprintGuard.claim``, which also marks it
    in flight) and calls ``submit``; the claim is ended in ``_job``'s ``finally`` (or by
    the done-callback when the job never ran), so it is never held forever. At most
    ``max_concurrent_runs`` runs execute at once; up to ``max_queued_runs`` more wait
    (accepted and queued). Past that the alert is refused and its claim released.
    """

    def __init__(self, settings: Settings, runner, guard: FingerprintGuard, log: ActionLog) -> None:
        self._runner = runner
        self._guard = guard
        self._log = log
        self._capacity = settings.max_concurrent_runs + settings.max_queued_runs
        self._lock = threading.Lock()
        self._pending = 0  # submitted and not yet ended (running plus queued)
        self._pool = ThreadPoolExecutor(max_workers=settings.max_concurrent_runs,
                                        thread_name_prefix="responder-run")

    def submit(self, fp: str, fid: str | None) -> str:
        """Called with ``fp`` already claimed. Returns ``accepted`` or ``busy_refused``."""
        with self._lock:
            if self._pending >= self._capacity:
                full = True
            else:
                full = False
                self._pending += 1
        if full:
            self._guard.abandon(fp)  # released, so the 503'd re-send is not a "repeat"
            self._log.emit("run_refused", outcome="busy_refused", fingerprint=fp, finding_id=fid,
                           reason="queue_full")
            return "busy_refused"
        try:
            future = self._pool.submit(self._job, fp, fid)
        except RuntimeError:  # the pool is shut down (the app is stopping)
            self._ended(fp, ran=False)
            self._log.emit("run_refused", outcome="busy_refused", fingerprint=fp, finding_id=fid,
                           reason="shutting_down")
            return "busy_refused"
        future.add_done_callback(lambda f: self._ended(fp, ran=False) if f.cancelled() else None)
        self._log.emit("run_accepted", outcome="accepted", fingerprint=fp, finding_id=fid)
        return "accepted"

    def _ended(self, fp: str, *, ran: bool) -> None:
        if not ran:
            self._guard.abandon(fp)  # never started: released, not counted as a failed run
        with self._lock:
            self._pending -= 1

    def _job(self, fp: str, fid: str | None) -> None:
        outcome = "error"  # anything but a returned outcome counts as a failed run
        try:
            outcome = self._runner.run(fp, fid)
        except BaseException as exc:  # noqa: BLE001 - incl. cancellation; must never escape the worker
            cancelled = isinstance(exc, (asyncio.CancelledError, CancelledError))
            reason = "run_cancelled" if cancelled else "run_raised"
            try:
                self._log.emit("run_failed", outcome="error", fingerprint=fp, finding_id=fid, reason=reason)
            except Exception:  # noqa: BLE001
                pass
        finally:
            try:
                self._guard.finish(fp, failed=outcome == "error")
            finally:
                with self._lock:
                    self._pending -= 1

    def shutdown(self) -> None:
        # Queued runs are cancelled (their claims released by the done-callback); a run
        # already executing is left to finish.
        self._pool.shutdown(wait=False, cancel_futures=True)


def create_app(settings: Settings, *, api: ResponderApi | None = None, git: FakeGit | None = None,
               github: FakeGitHub | None = None, log: ActionLog | None = None,
               make_session=None, checkout_git=None, branches=None, installer=None,
               publish_git=None) -> FastAPI:
    if settings.mode not in ("stub", "real"):
        raise ConfigError("RESPONDER_MODE must be 'stub' or 'real'")
    log = log or ActionLog()
    api = api or ResponderApi(settings.api_url, settings.api_token)
    guard = FingerprintGuard(settings.state_file)
    if settings.mode == "real":
        # Real mode (task 28d / #221): an agent session may open a fix PR.
        # The SDK sits behind make_session so tests pass a fake one; by default
        # the live session is built lazily (no SDK import until a run happens).
        from .checkout import SubprocessGit
        from .github_client import GitHubRestBranches
        from .real_runner import RealRunner, build_default_session

        from .installer import SubprocessInstaller

        branch_client = branches or GitHubRestBranches(settings.repo, settings.github_token)
        extra: dict[str, Any] = {}
        if settings.runtime == "cli":
            # #260: headless `claude -p` on the owner's login. The runner (not the agent) checks the
            # commits, pushes and opens the PR, so the GitHub token is used only by the runner.
            from .cli_session import CliSession, preflight
            from .prompt import CLI_SYSTEM_PROMPT, build_cli_task
            from .publisher import GitPublisher, SubprocessPublishGit

            if make_session is None:
                preflight()  # the binary exists and is logged in, or start-up fails with a clear message

            def default_session(model, ctx):
                return CliSession(model, ctx)

            extra = dict(system_prompt=CLI_SYSTEM_PROMPT, task_builder=build_cli_task)
            if make_session is None or publish_git is not None:
                # (an injected fake session without a fake publish git never reports ``fixed``)
                extra["publisher"] = GitPublisher(
                    publish_git or SubprocessPublishGit(settings.repo, settings.github_token), branch_client,
                    secrets=[settings.api_token, settings.webhook_secret, settings.github_token],
                    max_commits=settings.max_commits)
        else:
            def default_session(model, ctx):
                return build_default_session(model, ctx, api_key=settings.anthropic_api_key,
                                             github_token=settings.github_token)

        runner = RealRunner(
            api, log, settings.model, make_session or default_session,
            git=checkout_git or SubprocessGit(settings.repo, settings.github_token),
            branches=branch_client, **extra,
            max_turns=settings.max_turns, timeout_seconds=settings.run_timeout_seconds,
            repo=settings.repo,
            # The real install runs only with the real git seam; an injected (fake) checkout
            # git gets no installer unless the caller passes one.
            installer=installer if installer is not None
            else (SubprocessInstaller() if checkout_git is None else None),
            secrets=[settings.api_token, settings.webhook_secret, settings.github_token,
                     settings.anthropic_api_key],
            max_budget_usd=settings.max_budget_usd,
        )
    else:
        git = git or FakeGit()
        github = github or FakeGitHub()
        runner = StubRunner(api, git, github, log)

    background = _BackgroundRuns(settings, runner, guard, log) if settings.mode == "real" else None
    for lost in guard.lost_on_restart:
        # A run the previous process never finished: its claim was released at startup.
        log.emit("run_lost_on_restart", outcome="released", fingerprint=lost,
                 reason="process_restarted_during_run")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        if background is not None:
            background.shutdown()

    app = FastAPI(title="VulnTriage responder", docs_url=None, redoc_url=None, openapi_url=None,
                  lifespan=lifespan)
    if settings.mode == "stub":
        app.state.git = git
        app.state.github = github
    app.state.guard = guard

    def handle(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for alert in alerts:
            fp, fid = alert["fingerprint"], alert["finding_id"]
            if alert["status"] == "resolved":
                if fp is not None:
                    guard.resolve(fp)  # forget it so a later firing runs again (deferred if in flight)
                log.emit("alert_ignored", outcome="resolved", fingerprint=fp, finding_id=fid)
                results.append({"fingerprint": fp, "outcome": "resolved_ignored"})
                continue
            if fp is None:
                # Neither a fingerprint nor a finding_id (a Grafana test alert may carry
                # no fingerprint; US-15): nothing runs, so nothing is guarded or read.
                log.emit(
                    "no_change", outcome="no_change", fingerprint=None, finding_id=None,
                    explanation="Checked the alert: it carries neither a fingerprint nor a finding_id label, "
                                "so this is a Grafana test alert or a false positive, not an undelivered "
                                "finding. No finding or job was read, so there is no defect to reproduce.",
                )
                results.append({"fingerprint": None, "outcome": "no_change"})
                continue
            if background is not None and guard.failed_runs(fp) >= settings.max_failed_runs:
                # Retry cap (#241): this fingerprint failed N runs in a row. Not claimed,
                # no run; a resolved notification lifts the cap.
                log.emit("retry_cap_reached", outcome="retry_cap_reached", fingerprint=fp, finding_id=fid,
                         reason=f"{guard.failed_runs(fp)} consecutive failed runs")
                results.append({"fingerprint": fp, "outcome": "retry_cap_reached"})
                continue
            if not guard.claim(fp):
                log.emit("alert_ignored", outcome="repeat", fingerprint=fp, finding_id=fid)
                results.append({"fingerprint": fp, "outcome": "repeat_ignored"})
                continue
            if background is not None:
                results.append({"fingerprint": fp, "outcome": background.submit(fp, fid)})
                continue
            outcome = "error"  # an exception out of the run counts as a failed run
            try:
                outcome = runner.run(fp, fid)
            finally:
                # A failed run is released so a re-sent alert retries; a resolved that
                # arrived during the run releases here too (once).
                guard.finish(fp, failed=outcome == "error")
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
        # A refused alert (queue full) is not accepted: answer 503 so Grafana re-sends it.
        # Alerts accepted in the same body are repeats on the re-send, so nothing runs twice.
        refused = any(r["outcome"] == "busy_refused" for r in results)
        return JSONResponse({"results": results}, status_code=503 if refused else 200)

    return app


def create_app_from_env() -> FastAPI:
    """Uvicorn factory. Raises ``ConfigError`` (refuses to start) on a bad mode."""
    return create_app(Settings.from_env())
