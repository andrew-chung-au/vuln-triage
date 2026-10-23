"""Vulnerability identity (E9)."""

from __future__ import annotations


def identity_key(cve_id: str | None, primary_advisory_id: str) -> str:
    """Return the CVE when present, else the primary advisory id.

    Aliases that name the same CVE therefore share one identity key. Merging
    aliases (A15) and choosing the primary advisory are not done here.
    """
    return cve_id if cve_id else primary_advisory_id
