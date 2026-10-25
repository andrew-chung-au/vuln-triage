"""Pure-logic unit tests for the telemetry Compose helpers (no Docker, no network).

These cover the parts of ``tests/compose_telemetry.py`` that are plain functions,
so they run under ``make test`` / ``make verify`` (``unit``-marked, NOT
``compose``-marked). The Compose cases that need the running stack live in
``tests/test_compose_telemetry.py`` and are deselected by the no-Docker gate.

The focus here is #185: Tempo's search API returns a trace id with leading zeros
stripped, so the id can be shorter than 32 chars. ``_normalize_trace_id`` must
left-pad it to the canonical 32-char lowercase hex form. This flake only showed
up ~1 run in 16 on the live stack (when the high-order nibble was 0); a unit test
on the normaliser makes the behaviour deterministic and regression-proof.
"""

from __future__ import annotations

import pytest

# `tests/` is on sys.path (the compose test imports `compose_telemetry` the same
# bare way); importing the module is safe — it pulls only stdlib at import time.
from compose_telemetry import _normalize_trace_id

pytestmark = pytest.mark.unit


def test_already_canonical_id_is_unchanged() -> None:
    tid = "0af7651916cd43dd8448eb211c80319c"
    assert _normalize_trace_id(tid) == tid
    assert len(_normalize_trace_id(tid)) == 32


def test_leading_zero_stripped_id_is_left_padded_to_32() -> None:
    # Tempo dropped the top nibble (0); the canonical id restores it.
    stripped = "af7651916cd43dd8448eb211c80319c"  # 31 chars
    out = _normalize_trace_id(stripped)
    assert len(out) == 32
    assert out == "0af7651916cd43dd8448eb211c80319c"
    # The numeric value is preserved — only zero padding is added.
    assert int(out, 16) == int(stripped, 16)


def test_multiple_leading_zeros_stripped() -> None:
    stripped = "f7651916cd43dd8448eb211c80319c"  # 30 chars (top byte 0x00)
    out = _normalize_trace_id(stripped)
    assert len(out) == 32
    assert out == "00f7651916cd43dd8448eb211c80319c"
    assert int(out, 16) == int(stripped, 16)


def test_uppercase_is_lowercased_and_padded() -> None:
    out = _normalize_trace_id("AF7651916CD43DD8448EB211C80319C")
    assert out == "0af7651916cd43dd8448eb211c80319c"
    assert out == out.lower()
    assert len(out) == 32


def test_assertion_in_t_journey_be_holds_for_every_normalised_id() -> None:
    # The exact assertion T-JOURNEY-BE makes on the returned id:
    #   assert len(trace_id) == 32 and int(trace_id, 16) != 0
    # It must hold for ids whether or not Tempo stripped leading zeros.
    for raw in (
        "0af7651916cd43dd8448eb211c80319c",
        "af7651916cd43dd8448eb211c80319c",
        "f7651916cd43dd8448eb211c80319c",
        "1",
    ):
        tid = _normalize_trace_id(raw)
        assert len(tid) == 32 and int(tid, 16) != 0
