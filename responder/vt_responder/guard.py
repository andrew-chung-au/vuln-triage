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
        """Return True the first time a fingerprint is seen, False after."""
        with self._lock:
            if fingerprint in self._handled:
                return False
            self._handled.add(fingerprint)
            self._save()
            return True

    def release(self, fingerprint: str) -> None:
        """Forget a fingerprint (used when a run failed, so a re-sent alert retries)."""
        with self._lock:
            if fingerprint in self._handled:
                self._handled.discard(fingerprint)
                self._save()
