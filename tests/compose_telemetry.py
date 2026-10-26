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
PROMETHEUS_URL = os.environ.get("VT_PROMETHEUS_URL", "http://localhost:9090")
MAILHOG_URL = os.environ.get("VT_MAILHOG_URL", "http://localhost:8025")
BACKEND_URL = os.environ.get("VT_BACKEND_URL", "http://localhost:8000")

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


def wait_for_trace_spans(
    trace_id: str, required: set[str], timeout_s: float = DEFAULT_TIMEOUT_S
) -> dict[str, Any]:
    """Wait until the trace contains every span name in ``required``; return it.

    The journey spans arrive over time: the scan spans first, then
    ``notification.deliver`` when the DeliveryWorker next polls (~30s) and its
    export flushes. Polling the full set (not just trace existence) avoids
    asserting before the delivery span lands. Raises with the names seen so far
    on timeout.
    """
    def _complete():  # type: ignore[no-untyped-def]
        try:
            trace = tempo_trace(trace_id)
        except ComposeQueryError:
            return False
        names = {sp.get("name") for sp in _iter_spans(trace) if sp.get("name")}
        return trace if required <= names else False

    try:
        return _poll(_complete, timeout_s)
    except ComposeQueryError as exc:
        seen: set[str] = set()
        try:
            seen = {sp.get("name") for sp in _iter_spans(tempo_trace(trace_id)) if sp.get("name")}
        except ComposeQueryError:
            pass
        raise ComposeQueryError(
            f"{exc}; trace {trace_id} missing spans {required - seen}; present: {seen}"
        ) from exc


def _normalize_trace_id(trace_id: str) -> str:
    """Zero-pad a Tempo trace id to the canonical 32-char lowercase hex form (#185).

    Tempo's search API (``traces[].traceID``) returns the id **without leading
    zeros**, so a 128-bit id whose high-order nibble(s) are zero comes back as
    fewer than 32 chars (31 roughly 1 run in 16). The backend's ids are valid
    128-bit ids — only the search response strips the zeros — so left-pad to 32
    hex digits and lowercase. This makes ``len(trace_id) == 32`` hold for every
    id and keeps the subsequent ``GET /api/traces/{id}`` lookup on the canonical
    form Tempo stored.
    """
    return trace_id.lower().rjust(32, "0")


def tempo_search_trace_ids(span_name: str, lookback_s: int = 3600) -> list[str]:
    """Trace ids that contain a span named ``span_name`` (Tempo search API).

    VERIFY: Tempo 2.6.1 search endpoint ``GET /api/search?q=...`` (TraceQL) and
    the result shape (``traces[].traceID``); the older ``tags=`` form is the
    fallback. Used to find the journey's trace id from the ``scan.run`` root span
    after a scan is driven over HTTP (the HTTP response does not expose it).

    Ids are normalised to the canonical 32-hex form (#185): Tempo's search result
    drops leading zeros, so the raw id can be shorter than 32 chars.
    """
    end = int(time.time())
    start = end - lookback_s
    query = f'{{ name = "{span_name}" }}'
    url = f"{TEMPO_URL}/api/search?" + urllib.parse.urlencode(
        {"q": query, "start": start, "end": end, "limit": 50}
    )
    payload = _get_json(url)
    traces = payload.get("traces") or []
    return [_normalize_trace_id(t["traceID"]) for t in traces if t.get("traceID")]


def wait_for_trace_with_span(span_name: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> str:
    """Wait until Tempo has a trace containing ``span_name``; return its trace id."""
    ids = _poll(lambda: tempo_search_trace_ids(span_name) or False, timeout_s)
    return ids[0]


def _iter_spans(trace: dict[str, Any]):  # type: ignore[no-untyped-def]
    """Yield each span dict in a Tempo trace document (both nesting shapes)."""
    batches = trace.get("batches") or trace.get("resourceSpans") or []
    for batch in batches:
        scopes = batch.get("scopeSpans") or batch.get("instrumentationLibrarySpans") or []
        for scope in scopes:
            yield from scope.get("spans", [])


def span_attribute_keys(trace: dict[str, Any]) -> set[str]:
    """Collect every span-attribute key present in a Tempo trace document.

    VERIFY: the exact nesting keys (``batches``/``scopeSpans``/``spans`` or
    ``resourceSpans``) differ by Tempo version; this reads both common shapes.
    """
    keys: set[str] = set()
    for sp in _iter_spans(trace):
        for attr in sp.get("attributes", []):
            key = attr.get("key")
            if key:
                keys.add(key)
    return keys


def span_names(trace: dict[str, Any]) -> set[str]:
    """Collect every span name present in a Tempo trace document."""
    return {sp.get("name") for sp in _iter_spans(trace) if sp.get("name")}


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
    return [line for line, _meta in loki_entries(logql, since_s)]


def loki_entries(logql: str, since_s: int = 3600) -> list[tuple[str, dict[str, Any]]]:
    """Return (line, metadata) for each matching entry.

    OTLP log *attributes* land in Loki as structured metadata, not the line body
    (the body is the event name). ``metadata`` merges the stream labels and any
    per-entry structured metadata, so a caller can check attribute values.
    VERIFY: on Loki 3.2.1 a query_range value is ``[ts, line]`` or
    ``[ts, line, {structured metadata}]``; both shapes are handled here.
    """
    entries: list[tuple[str, dict[str, Any]]] = []
    for stream in loki_query_range(logql, since_s):
        labels = dict(stream.get("stream", {}) or {})
        for value in stream.get("values", []):
            line = value[1] if len(value) > 1 else ""
            meta = dict(labels)
            if len(value) > 2 and isinstance(value[2], dict):
                meta.update(value[2])
            entries.append((line, meta))
    return entries


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


def wait_for_log_entry(
    logql: str, marker: str, timeout_s: float = DEFAULT_TIMEOUT_S
) -> list[tuple[str, dict[str, Any]]]:
    """Wait until an entry whose line or metadata contains ``marker`` appears.

    The marker (this run's vt.scan.id value) is in the record's structured
    metadata, not the body (the body is the event name), so this checks both.
    Returns the matching (line, metadata) entries; raises with a Loki diagnostic
    on timeout, so a blind miss is a decisive next step rather than a guess.
    """

    def _match() -> list[tuple[str, dict[str, Any]]] | bool:
        found = [
            (line, meta)
            for line, meta in loki_entries(logql)
            if marker in line or any(marker in str(v) for v in meta.values())
        ]
        return found or False

    try:
        return _poll(_match, timeout_s)
    except ComposeQueryError as exc:
        raise ComposeQueryError(
            f"{exc}; waited for a Loki entry matching {logql!r} with marker {marker!r}. "
            f"Loki state: {_loki_diagnostic(logql)}"
        ) from exc


# -- Prometheus -------------------------------------------------------------


def prometheus_query(promql: str) -> list[dict[str, Any]]:
    """Run an instant query and return its result vector (``data.result``).

    VERIFY: the ``/api/v1/query`` response shape on Prometheus v2.54.1.
    """
    url = f"{PROMETHEUS_URL}/api/v1/query?" + urllib.parse.urlencode({"query": promql})
    payload = _get_json(url)
    if payload.get("status") != "success":
        raise ComposeQueryError(f"prometheus query {promql!r} not successful: {payload}")
    return payload.get("data", {}).get("result", [])


def wait_for_metric(promql: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    """Wait until an instant query returns at least one series.

    The series set depends on the Collector exporter's scrape interval and
    Prometheus's own scrape, so polling (not a single query) is required.
    """
    return _poll(lambda: prometheus_query(promql) or False, timeout_s)


def prometheus_exemplar_trace_ids(promql: str, lookback_s: int = 3600) -> set[str]:
    """Return the ``trace_id`` labels of every exemplar stored for ``promql``.

    Reads ``/api/v1/query_exemplars``, whose ``data`` is a list of
    ``{seriesLabels, exemplars: [{labels: {trace_id, span_id}, value, timestamp}]}``.
    Needs Prometheus started with ``--enable-feature=exemplar-storage`` and the
    Collector's Prometheus exporter with ``enable_open_metrics: true``.

    VERIFY: the ``query_exemplars`` response shape and the ``trace_id`` exemplar
    label key on Prometheus v2.54.1 / Collector contrib 0.111.0.
    """
    now = time.time()
    params = urllib.parse.urlencode(
        {"query": promql, "start": f"{now - lookback_s:.3f}", "end": f"{now + 60:.3f}"}
    )
    payload = _get_json(f"{PROMETHEUS_URL}/api/v1/query_exemplars?{params}")
    if payload.get("status") != "success":
        raise ComposeQueryError(f"prometheus exemplar query {promql!r} not successful: {payload}")
    ids: set[str] = set()
    for series in payload.get("data") or []:
        for exemplar in series.get("exemplars") or []:
            trace_id = (exemplar.get("labels") or {}).get("trace_id")
            if trace_id:
                ids.add(trace_id)
    return ids


def wait_for_exemplar_trace_id(
    promql: str, trace_id: str, timeout_s: float = DEFAULT_TIMEOUT_S
) -> set[str]:
    """Wait until an exemplar of ``promql`` carries ``trace_id``; return all seen ids.

    Polls with the bounded ``_poll``; on timeout it raises with the trace ids
    that were found, so a wrong id and a missing exemplar are told apart.
    """
    try:
        return _poll(
            lambda: (ids if trace_id in (ids := prometheus_exemplar_trace_ids(promql)) else False),
            timeout_s,
        )
    except ComposeQueryError as exc:
        try:
            seen = prometheus_exemplar_trace_ids(promql)
        except ComposeQueryError as inner:
            seen = {f"<query failed: {inner}>"}
        raise ComposeQueryError(
            f"{exc}; no exemplar of {promql!r} carried trace id {trace_id!r}; "
            f"exemplar trace ids seen: {sorted(seen)}"
        ) from exc


# -- MailHog ----------------------------------------------------------------


def mailhog_messages() -> list[dict[str, Any]]:
    """Return the messages MailHog currently holds.

    VERIFY: MailHog v1.0.1 ``GET /api/v2/messages`` shape (``items`` with
    ``Content``/``To``/``From``).
    """
    payload = _get_json(f"{MAILHOG_URL}/api/v2/messages")
    if isinstance(payload, dict):
        return payload.get("items", []) or []
    return payload or []


def mailhog_recipients(messages: list[dict[str, Any]]) -> set[str]:
    """Collect recipient addresses from MailHog messages (VERIFY: v1.0.1 shape)."""
    out: set[str] = set()
    for msg in messages:
        for to in msg.get("To", []) or []:
            mailbox, domain = to.get("Mailbox"), to.get("Domain")
            if mailbox and domain:
                out.add(f"{mailbox}@{domain}")
    return out


def wait_for_mail(count: int = 1, timeout_s: float = DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    """Wait until MailHog holds at least ``count`` messages."""

    def _enough() -> list[dict[str, Any]] | bool:
        msgs = mailhog_messages()
        return msgs if len(msgs) >= count else False

    return _poll(_enough, timeout_s)


# -- Backend HTTP (drive the journey over the published port) ---------------
# The journey logs in as the seeded security-lead user and registers the pygoat
# asset; the container's workers then run scan -> enqueue -> deliver. The
# vt_session cookie is Secure, so (as tests/auth_helpers.py does) scrape it from
# Set-Cookie and resend it; every non-GET carries the X-Requested-With CSRF
# header.

_CSRF_HEADER = "X-Requested-With"
_CSRF_VALUE = "XMLHttpRequest"
_COOKIE_NAME = "vt_session"


def _backend_request(
    method: str, path: str, *, cookie: str | None = None, json_body: Any | None = None
) -> tuple[int, dict[str, str], bytes]:
    """One request to the backend; returns (status, headers, body). Loopback only."""
    data = None
    headers: dict[str, str] = {}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if method != "GET":
        headers[_CSRF_HEADER] = _CSRF_VALUE
    if cookie is not None:
        headers["Cookie"] = f"{_COOKIE_NAME}={cookie}"
    req = urllib.request.Request(f"{BACKEND_URL}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (loopback)
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, exc.read()
    except (urllib.error.URLError, OSError) as exc:
        raise ComposeQueryError(f"{method} {path} failed: {exc}") from exc


def backend_login(username: str, password: str) -> str:
    """POST /auth/login; return the vt_session cookie value (raises on failure)."""
    status, headers, body = _backend_request(
        "POST", "/auth/login", json_body={"username": username, "password": password}
    )
    if status != 200:
        raise ComposeQueryError(f"login failed ({status}): {body!r}")
    set_cookie = headers.get("set-cookie", "")
    import re

    match = re.search(rf"{_COOKIE_NAME}=([^;]+)", set_cookie)
    if not match:
        raise ComposeQueryError(f"login response had no {_COOKIE_NAME} cookie: {set_cookie!r}")
    return match.group(1)


def backend_register_asset(cookie: str, asset: dict[str, Any]) -> dict[str, Any]:
    """POST /assets with the session cookie; return the created asset JSON."""
    status, _headers, body = _backend_request("POST", "/assets", cookie=cookie, json_body=asset)
    if status != 201:
        raise ComposeQueryError(f"POST /assets failed ({status}): {body!r}")
    return json.loads(body)


def wait_for_backend_health(timeout_s: float = DEFAULT_TIMEOUT_S) -> bool:
    """Wait until the backend answers /health (the container is serving)."""
    def _ok() -> bool:
        status, _h, _b = _backend_request("GET", "/health")
        return status == 200
    return _poll(lambda: _ok() or False, timeout_s)