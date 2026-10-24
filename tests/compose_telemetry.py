"""Helpers for the telemetry Compose test (#157, task 25).

Used only by the ``compose``-marked case in ``tests/test_compose_telemetry.py``,
which runs under ``make test-compose JOB=telemetry`` against the running
observability stack. It never runs under ``make test`` / ``make verify`` (the
``compose`` marker is deselected there), so it is free to open loopback HTTP
connections to the published service ports.

Scope (Option C narrowing, 2026-10-24): #157 ships only ``T-REFUSE``, so these
helpers cover only Tempo (span attributes) and Loki (log lines). The Prometheus,
MailHog and metric/trace-join helpers return with the delivery-dependent cases
in prerequisite #172.

The host endpoints are the ports ``observability/compose.yaml`` publishes to
``localhost``; overridable via the environment so the same case runs in CI, a
codespace or the human's host.

VERIFY (external service query shapes — confirmed by the human on the running
stack, pinned images Tempo 2.6.1 / Loki 3.2.1):
- Tempo trace lookup ``GET /api/traces/{trace_id}`` and its JSON shape for span
  attributes on 2.6.1.
- Loki range-query ``GET /loki/api/v1/query_range`` and the stream/line shape;
  the label/field under which OTLP-ingested logs are queryable.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

TEMPO_URL = os.environ.get("VT_TEMPO_URL", "http://localhost:3200")
LOKI_URL = os.environ.get("VT_LOKI_URL", "http://localhost:3100")

# How long to wait for a signal to appear (export + ingest latency).
DEFAULT_TIMEOUT_S = float(os.environ.get("VT_COMPOSE_POLL_TIMEOUT", "60"))
_POLL_INTERVAL_S = 2.0


class ComposeQueryError(RuntimeError):
    """A telemetry backend could not be queried (a hard failure, never a skip)."""


def _get_json(url: str) -> Any:
    """GET ``url`` and parse JSON. Loopback only (the network guard allows it)."""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 (loopback)
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise ComposeQueryError(f"GET {url} failed: {exc}") from exc


def _poll(predicate, timeout_s: float = DEFAULT_TIMEOUT_S):  # type: ignore[no-untyped-def]
    """Call ``predicate`` until it returns a truthy value or the timeout passes.

    Returns the truthy value, or raises ``ComposeQueryError`` on timeout. Uses a
    bounded loop with a fixed interval, never an open-ended wait.
    """
    deadline = time.monotonic() + timeout_s
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except ComposeQueryError as exc:
            last_exc = exc
        time.sleep(_POLL_INTERVAL_S)
    msg = f"condition not met within {timeout_s:.0f}s"
    if last_exc is not None:
        msg = f"{msg} (last error: {last_exc})"
    raise ComposeQueryError(msg)


# -- Tempo ------------------------------------------------------------------


def tempo_trace(trace_id: str) -> dict[str, Any]:
    """Fetch a trace by its 32-hex id.

    VERIFY: Tempo 2.6.1 trace-by-id endpoint (``GET /api/traces/{id}``) and the
    returned JSON shape (resource spans -> scope spans -> spans with name/attrs).
    """
    return _get_json(f"{TEMPO_URL}/api/traces/{trace_id}")


def wait_for_trace(trace_id: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """Wait until Tempo has the trace (export + ingest latency)."""
    return _poll(lambda: tempo_trace(trace_id), timeout_s)


def span_attribute_keys(trace: dict[str, Any]) -> set[str]:
    """Collect every span-attribute key present in a Tempo trace document.

    VERIFY: the exact nesting keys (``batches``/``scopeSpans``/``spans`` or
    ``resourceSpans``) differ by Tempo version; this reads both common shapes.
    """
    keys: set[str] = set()
    batches = trace.get("batches") or trace.get("resourceSpans") or []
    for batch in batches:
        scopes = batch.get("scopeSpans") or batch.get("instrumentationLibrarySpans") or []
        for scope in scopes:
            for sp in scope.get("spans", []):
                for attr in sp.get("attributes", []):
                    key = attr.get("key")
                    if key:
                        keys.add(key)
    return keys


# -- Loki -------------------------------------------------------------------


def loki_query_range(logql: str, since_s: int = 3600) -> list[dict[str, Any]]:
    """Run a LogQL range query and return the stream results.

    VERIFY: Loki 3.2.1 ``/loki/api/v1/query_range`` params and response shape,
    and the stream label under which OTLP-ingested logs are queryable.
    """
    end = int(time.time() * 1_000_000_000)
    start = end - since_s * 1_000_000_000
    url = f"{LOKI_URL}/loki/api/v1/query_range?" + urllib.parse.urlencode(
        {"query": logql, "start": start, "end": end, "limit": 500}
    )
    payload = _get_json(url)
    if payload.get("status") != "success":
        raise ComposeQueryError(f"loki query {logql!r} not successful: {payload}")
    return payload.get("data", {}).get("result", [])


def loki_lines(logql: str, since_s: int = 3600) -> list[str]:
    """Return the raw log line strings matching a LogQL query."""
    lines: list[str] = []
    for stream in loki_query_range(logql, since_s):
        for _ts, line in stream.get("values", []):
            lines.append(line)
    return lines


def loki_labels() -> list[str]:
    """The label names Loki currently knows (diagnostic). VERIFY: /labels API."""
    payload = _get_json(f"{LOKI_URL}/loki/api/v1/labels")
    return payload.get("data", []) or []


def loki_label_values(label: str) -> list[str]:
    """The values Loki has for ``label`` (diagnostic). VERIFY: /label/<n>/values."""
    try:
        payload = _get_json(f"{LOKI_URL}/loki/api/v1/label/{label}/values")
    except ComposeQueryError:
        return []
    return payload.get("data", []) or []


def _loki_diagnostic(logql: str) -> str:
    """A one-string snapshot of what Loki holds, for a timed-out log wait.

    Turns a blind "no line found" timeout into a decisive next step: it shows
    the label names Loki knows, the values of common OTLP labels, and a sample
    of whatever the selector *does* return — so the log says whether the
    selector label is wrong, logs never arrived, or the marker is missing.
    """
    parts: list[str] = []
    try:
        parts.append(f"loki labels: {loki_labels()}")
    except ComposeQueryError as exc:
        parts.append(f"loki labels query failed: {exc}")
    for label in ("service_name", "service", "exporter", "job"):
        values = loki_label_values(label)
        if values:
            parts.append(f"{label} values: {values}")
    try:
        sample = loki_lines(logql)[:5]
        parts.append(f"sample lines for {logql!r}: {sample}")
    except ComposeQueryError as exc:
        parts.append(f"sample query failed: {exc}")
    # Also try a wide selector so we see lines even if the given selector is wrong.
    try:
        wide = loki_lines('{service_name=~".+"}')[:5]
        parts.append(f'sample lines for {{service_name=~".+"}}: {wide}')
    except ComposeQueryError as exc:
        parts.append(f"wide query failed: {exc}")
    return " | ".join(parts)


def wait_for_log_line(logql: str, contains: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> list[str]:
    """Wait until at least one line matching ``logql`` contains ``contains``.

    Returns the matching lines. Polling (rather than a single fetch) closes the
    loophole where slow ingestion returns nothing and the caller's "no excluded
    value in any matching line" check passes without inspecting anything. On
    timeout it raises with a Loki diagnostic (labels + sample lines), so a blind
    "no line" result is turned into a decisive next step rather than a guess.
    """
    try:
        return _poll(
            lambda: [ln for ln in loki_lines(logql) if contains in ln] or False,
            timeout_s,
        )
    except ComposeQueryError as exc:
        raise ComposeQueryError(
            f"{exc}; waited for a line matching {logql!r} containing {contains!r}. "
            f"Loki state: {_loki_diagnostic(logql)}"
        ) from exc
