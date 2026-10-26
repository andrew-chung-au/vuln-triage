"""Helpers for the `responder` Compose job (task 28c, #220).

Used only by the ``compose``-marked cases in ``tests/test_compose_responder.py``
(``make test-compose JOB=responder``). They WERE WRITTEN WITHOUT BEING RUN: the
cloud session that wrote them has no working Docker build. Every external
detail they depend on is marked ``VERIFY:``.

Reuses ``compose_alert`` (the #159 seam, the webhook-sink client, MailHog and
Prometheus helpers) and ``compose_telemetry._poll``; no second harness.

The responder's log is stdout JSON lines (``vt_responder.actlog``), not Loki, so
the cases read ``docker compose logs responder``.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any

from compose_alert import _compose_base  # noqa: F401 (the same project + file list as the seam)
from compose_telemetry import DEFAULT_TIMEOUT_S, ComposeQueryError, _poll

# Published by compose.responder.yaml on loopback only.
RESPONDER_URL = os.environ.get("VT_RESPONDER_HOST_URL", "http://localhost:9100")
WEBHOOK_PATH = "/webhook/grafana"
# Grafana is published on 3000 by observability/compose.yaml.
GRAFANA_URL = os.environ.get("VT_GRAFANA_HOST_URL", "http://localhost:3000")

# The same value Grafana's contact point presents (ci/test-compose.sh exports it).
WEBHOOK_TOKEN = os.environ.get("VT_RESPONDER_WEBHOOK_TOKEN", "")
GRAFANA_ADMIN_PASSWORD = os.environ.get("GRAFANA_ADMIN_PASSWORD", "")

STATE_FILE = "/tmp/responder-state/handled-fingerprints.json"  # compose.responder.yaml
_DOCKER_TIMEOUT_S = 120


def _docker(
    args: list[str], *, timeout: float = _DOCKER_TIMEOUT_S, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*_compose_base(), *args], capture_output=True, text=True, timeout=timeout, check=False,
        env=env,
    )


def recreate_backend(defect: str | None) -> None:
    """Recreate the backend container with ``VT_DEMO_DEFECT`` set to ``defect`` (``None`` = unset).

    ``docker compose restart`` does NOT re-read the environment, so the harness
    recreates the container: ``up -d --force-recreate --no-deps --wait backend``
    (#233). compose.responder.yaml passes ``${VT_DEMO_DEFECT:-}`` through, so the
    value comes from THIS subprocess's environment: the variable is removed first
    so ``None`` really means unset, whatever the caller's environment held. Raises
    ``ComposeQueryError`` on a non-zero exit (never a skip).
    """
    env = {k: v for k, v in os.environ.items() if k != "VT_DEMO_DEFECT"}
    if defect is not None:
        env["VT_DEMO_DEFECT"] = defect
    proc = _docker(
        ["up", "-d", "--force-recreate", "--no-deps", "--wait", "backend"], timeout=300, env=env
    )
    if proc.returncode != 0:
        raise ComposeQueryError(f"recreating the backend failed (rc={proc.returncode}): {proc.stderr}")


def backend_demo_defect() -> str:
    """The ``VT_DEMO_DEFECT`` value inside the running backend container ('' when off)."""
    proc = _docker(["exec", "-T", "backend", "sh", "-c", 'printf %s "$VT_DEMO_DEFECT"'])
    if proc.returncode != 0:
        raise ComposeQueryError(f"reading VT_DEMO_DEFECT from the backend failed: {proc.stderr}")
    return proc.stdout.strip()


def message_subject(message: dict[str, Any]) -> str:
    """The Subject header of a MailHog v2 message ('' when absent)."""
    values = ((message.get("Content") or {}).get("Headers") or {}).get("Subject") or []
    return str(values[0]) if values else ""


# -- the responder's action log (stdout JSON lines) ---------------------------


def responder_log() -> list[dict[str, Any]]:
    """Every JSON line the responder container has printed so far.

    Non-JSON lines (uvicorn's own access log) are skipped. VERIFY: ``--no-log-prefix``
    on the Compose version in CI (it removes the ``responder-1  |`` prefix; the
    parser also tolerates a prefix by cutting at the first ``{``).
    """
    proc = _docker(["logs", "--no-color", "--no-log-prefix", "responder"])
    if proc.returncode != 0:
        raise ComposeQueryError(f"docker compose logs responder failed: {proc.stderr}")
    out: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        start = line.find("{")
        if start < 0:
            continue
        try:
            record = json.loads(line[start:])
        except ValueError:
            continue
        if isinstance(record, dict) and "event" in record:
            out.append(record)
    return out


def events(name: str, records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [r for r in (responder_log() if records is None else records) if r.get("event") == name]


def wait_for_event(name: str, predicate, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Wait for a log line of event ``name`` that satisfies ``predicate``; return it."""
    return _poll(lambda: next((r for r in events(name) if predicate(r)), False), timeout_s)


def guard_record() -> list[str]:
    """The guard's handled-fingerprint record, read from inside the container.

    A missing file means nothing has been claimed yet (``[]``). Only fingerprints
    are in it (no secret).
    """
    proc = _docker(["exec", "-T", "responder", "python", "-c",
                    f"import pathlib,sys; p=pathlib.Path({STATE_FILE!r}); "
                    "sys.stdout.write(p.read_text() if p.exists() else '[]')"])
    if proc.returncode != 0:
        raise ComposeQueryError(f"reading the guard record failed: {proc.stderr}")
    return sorted(json.loads(proc.stdout))


def container_env_keys() -> dict[str, str]:
    """``docker compose exec responder env`` as a dict. Callers log KEY NAMES only."""
    proc = _docker(["exec", "-T", "responder", "env"])
    if proc.returncode != 0:
        raise ComposeQueryError(f"docker compose exec responder env failed: {proc.stderr}")
    env: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            env[key] = value
    return env


# -- sending requests to the published responder port -------------------------


def post_webhook(body: bytes, headers: dict[str, str]) -> tuple[int, bytes]:
    """POST ``body`` to the responder's published port; return (status, response body)."""
    req = urllib.request.Request(RESPONDER_URL + WEBHOOK_PATH, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (loopback)
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, OSError) as exc:
        raise ComposeQueryError(f"POST {RESPONDER_URL}{WEBHOOK_PATH} failed: {exc}") from exc


def firing_body(fingerprint: str, finding_id: str = "999999") -> bytes:
    """A well-formed Grafana-shaped firing body (used only by the refused cases)."""
    return json.dumps(
        {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "fingerprint": fingerprint,
                    "labels": {"finding_id": finding_id, "tier": "P1"},
                }
            ],
        }
    ).encode("utf-8")


# -- the Grafana test notification -------------------------------------------


def send_grafana_test_notification() -> tuple[int, str]:
    """Ask Grafana to send a test notification to the responder; return (status, body text).

    VERIFY: the receivers-test endpoint and body on grafana/grafana:11.3.0. This
    uses ``POST /api/alertmanager/grafana/config/api/v1/receivers/test`` with a
    one-receiver ``grafana_managed_receiver_configs`` list (a webhook to the
    responder with the bearer credentials), basic-auth as the admin user. If
    11.3.0 wants the credentials under ``secureSettings``, or a different path,
    the response body is returned for the failure message so the fix is one edit.
    """
    body = {
        "receivers": [
            {
                "name": "responder-test",
                "grafana_managed_receiver_configs": [
                    {
                        "name": "responder-test",
                        "type": "webhook",
                        "settings": {
                            "url": "http://responder:9100" + WEBHOOK_PATH,
                            "httpMethod": "POST",
                            "authorization_scheme": "Bearer",
                            "authorization_credentials": WEBHOOK_TOKEN,
                        },
                    }
                ],
            }
        ]
    }
    auth = base64.b64encode(f"admin:{GRAFANA_ADMIN_PASSWORD}".encode()).decode()
    req = urllib.request.Request(
        GRAFANA_URL + "/api/alertmanager/grafana/config/api/v1/receivers/test",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (loopback)
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as exc:
        raise ComposeQueryError(f"Grafana receivers test failed: {exc}") from exc


# -- one-off container runs ---------------------------------------------------


def run_responder_once(mode_env: str | None) -> subprocess.CompletedProcess[str]:
    """Start a one-off responder container with RESPONDER_MODE set to ``mode_env``.

    ``None`` is passed as an empty value (the variable present and empty, which the
    responder refuses just as it does an unset one). No port is published by
    ``run`` (no ``--service-ports``), and ``--no-deps`` keeps the stack as it is.
    VERIFY: the ``docker compose run`` flags on the CI Compose version.
    """
    return _docker(
        ["run", "-T", "--rm", "--no-deps", "-e", f"RESPONDER_MODE={mode_env or ''}", "responder"],
        timeout=120,
    )
