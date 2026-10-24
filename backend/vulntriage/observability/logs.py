"""JSON-lines structured logging (task 23).

One log line is a JSON object carrying ``event`` (the event name), ``trace_id``
and ``span_id`` from the current span context, and only allowlisted extra
fields. Log bodies are event names only — never advisory text, owner details,
URLs, SQL or credentials — because every extra field is passed through the
allowlist first.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from typing import Any, TextIO

from opentelemetry import trace

from vulntriage.observability.allowlist import filter_attributes


def log_event(event: str, attributes: Mapping[str, Any] | None = None, *, stream: TextIO | None = None) -> None:
    """Write one JSON line: ``{event, trace_id, span_id, ...allowlisted}``.

    ``event`` is a short machine name (e.g. ``"scan.finished"``). ``attributes``
    are filtered through the allowlist, so a caller cannot leak a non-allowlisted
    field. ``trace_id``/``span_id`` come from the current span context, joining
    the log to the trace.
    """
    ctx = trace.get_current_span().get_span_context()
    record: dict[str, Any] = {
        "event": event,
        "trace_id": trace.format_trace_id(ctx.trace_id),
        "span_id": trace.format_span_id(ctx.span_id),
    }
    record.update(filter_attributes(attributes or {}))
    out = stream if stream is not None else sys.stdout
    out.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
