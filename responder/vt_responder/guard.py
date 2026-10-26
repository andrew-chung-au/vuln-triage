"""Repeat-fingerprint guard with a record that survives a restart.

The handled fingerprints are kept in a JSON file, rewritten atomically
(temp file, fsync, rename) on every change. ``claim`` is check-and-add under a
lock, so two concurrent deliveries of one fingerprint give one run.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


class FingerprintGuard:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._handled = self._load()
        # In-memory only: runs in flight and resolved notifications waiting for them.
        self._inflight: set[str] = set()
        self._deferred: set[str] = set()

    def _load(self) -> set[str]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return set()
        except (OSError, ValueError):
            # An unreadable record must not silently allow repeats: refuse to start.
            raise RuntimeError(f"cannot read handled-fingerprint record {self._path}") from None
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise RuntimeError(f"handled-fingerprint record {self._path} is malformed")
        return set(data)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(sorted(self._handled), fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._path)

    def claim(self, fingerprint: str) -> bool:
        """Return True the first time a fingerprint is seen, False after.

        A repeat firing that arrives while a release is deferred (see ``resolve``)
        cancels that release: the run in flight covers the alert that is firing now.
        """
        with self._lock:
            if fingerprint in self._handled:
                self._deferred.discard(fingerprint)
                return False
            self._handled.add(fingerprint)
            self._inflight.add(fingerprint)
            self._save()
            return True

    def release(self, fingerprint: str) -> None:
        """Forget a fingerprint (used when a run failed, so a re-sent alert retries)."""
        with self._lock:
            self._release_locked(fingerprint)

    def _release_locked(self, fingerprint: str) -> None:
        if fingerprint in self._handled:
            self._handled.discard(fingerprint)
            self._save()

    def resolve(self, fingerprint: str) -> str:
        """The alert resolved: forget the fingerprint so a later firing runs again.

        Returns ``released``, ``deferred`` (a run is in flight, so the release waits
        for ``finish``; releasing now would allow a second concurrent run) or
        ``unknown`` (nothing recorded; the record is left untouched).

        Limit: if a fix does not hold and the alert never resolves, Grafana sends
        nothing (no repeat), so the guard is not the cause.
        """
        with self._lock:
            if fingerprint in self._inflight:
                self._deferred.add(fingerprint)
                return "deferred"
            if fingerprint in self._handled:
                self._release_locked(fingerprint)
                return "released"
            return "unknown"

    def finish(self, fingerprint: str, *, failed: bool = False) -> None:
        """A run ended. Release it if it failed or a resolved was deferred (once)."""
        with self._lock:
            self._inflight.discard(fingerprint)
            deferred = fingerprint in self._deferred
            self._deferred.discard(fingerprint)
            if failed or deferred:
                self._release_locked(fingerprint)
