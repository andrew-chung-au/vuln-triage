"""Stub webhook sink for the `alert` Compose job (task 27, #159).

The US-14 alert's responder destination (`finding-responder-webhook`) points at
`VT_RESPONDER_WEBHOOK_URL`. The real responder *receiver* is task 28 (#160); this
job only needs to observe what Grafana POSTs to the responder, so this is a tiny
record-only HTTP server with NO new dependency — it is pure stdlib
(`http.server`) and runs inside the **backend image already in the stack** (the
alert override sets its `command`/`entrypoint` to run this module). It never acts
on a request; it records each one so a case can read "0 requests" (A-HELD,
A-GAP) or "1 request naming finding X" (A-FIRE).

Endpoints (all plaintext, loopback/shared-network only):
- ``POST <any path>`` — record the request (method, path, headers, raw body, and
  the parsed JSON body when the body is JSON). Always answers ``200``.
- ``GET /__recorded`` — return the recorded requests as a JSON array (the case
  reads this to assert counts and the finding_id/tier the payload carries).
- ``GET /__reset`` — clear the recorded requests (the harness calls this between
  cases so each A-* case starts from zero).
- ``GET /__health`` — ``200`` ``ok`` (the harness waits on this before seeding).

VERIFY (external Grafana detail, confirmed on grafana/grafana:11.3.0 against this
sink on a running stack): the webhook POST shape Grafana sends — that the body is
JSON with the firing alert instances, and that each instance's labels carry
``finding_id`` and ``tier`` (and NOT advisory text, owner contact, URL or
credential). The recorder stores the raw body too, so the exact shape can be
inspected on the first real run and the case's extractor adjusted if needed.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_PORT = int(os.environ.get("VT_WEBHOOK_SINK_PORT", "9099"))

# Recorded requests, guarded by a lock (ThreadingHTTPServer serves concurrently).
_lock = threading.Lock()
_recorded: list[dict] = []


class _Handler(BaseHTTPRequestHandler):
    # Quieten the default per-request stderr logging; the CI log stays readable.
    def log_message(self, *args: object) -> None:  # noqa: D401
        return

    def _send(self, status: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path.startswith("/__recorded"):
            with _lock:
                payload = json.dumps(list(_recorded)).encode("utf-8")
            self._send(200, payload, "application/json")
            return
        if self.path.startswith("/__reset"):
            with _lock:
                _recorded.clear()
            self._send(200, b"reset")
            return
        if self.path.startswith("/__health"):
            self._send(200, b"ok")
            return
        # Any other GET is still recorded (Grafana only POSTs, but be permissive).
        self._record("GET")
        self._send(200, b"ok")

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        self._record("POST")
        self._send(200, b"ok")

    def _record(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body_text = raw.decode("utf-8", errors="replace")
        parsed: object | None = None
        try:
            parsed = json.loads(body_text) if body_text else None
        except ValueError:
            parsed = None
        entry = {
            "method": method,
            "path": self.path,
            "headers": {k: v for k, v in self.headers.items()},
            "body": body_text,
            "json": parsed,
        }
        with _lock:
            _recorded.append(entry)


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", _PORT), _Handler)  # noqa: S104 (test-only, shared Compose net)
    print(f"alert webhook sink listening on 0.0.0.0:{_PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
