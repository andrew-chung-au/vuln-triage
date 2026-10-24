#!/usr/bin/env python3
"""Post-process pip-audit JSON into high/critical vs reported-only (issue #140).

pip-audit (2.10.1) exits non-zero on any finding and its JSON carries no
severity (pypa/pip-audit#654). Q1 option 2: derive severity from each
advisory's OSV record so the scan FAILS only on high/critical and REPORTS
lower findings. Q2 option 2: an advisory with no severity is treated as high
(fail closed) — a security gate must not pass a vulnerability of unknown
severity silently.

Input: the pip-audit JSON on the ``SCAN_JSON`` environment variable.
Output: one line per finding, then a final ``COUNTS <high> <low>`` line.
Exit 0 always (the caller drives pass/fail from the counts); exit 2 on a
malformed input (fail closed).

Severity source, in order: the OSV ``database_specific.severity`` label, then
the CVSS v3/v4 base score mapped to a label, then — if neither exists — HIGH
(Q2). This reads only the severity data pip-audit already embeds from OSV; it
makes no extra network call.
"""

from __future__ import annotations

import json
import os
import sys

HIGH_LABELS = {"HIGH", "CRITICAL"}


def _label_from_cvss_score(score: float) -> str:
    # CVSS v3/v4 qualitative bands.
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MODERATE"
    if score > 0.0:
        return "LOW"
    return "NONE"


def _severity_for(vuln: dict) -> str:
    """Return a severity label for one pip-audit vulnerability entry.

    Unknown severity returns ``HIGH`` (Q2, fail closed).
    """
    # pip-audit 2.10.1 nests the OSV record fields; be defensive about shape.
    # 1) explicit label (database_specific.severity), e.g. "HIGH".
    db = vuln.get("database_specific") or {}
    label = db.get("severity")
    if isinstance(label, str) and label.strip():
        up = label.strip().upper()
        if up in {"CRITICAL", "HIGH", "MODERATE", "MEDIUM", "LOW", "NONE"}:
            return "MODERATE" if up == "MEDIUM" else up

    # 2) CVSS vectors/scores under "severity": [{"type": "CVSS_V3", "score": ...}]
    best = None
    for entry in vuln.get("severity") or []:
        score = entry.get("score")
        value = None
        if isinstance(score, (int, float)):
            value = float(score)
        elif isinstance(score, str):
            # A CVSS vector string like "CVSS:3.1/AV:N/..."; no numeric base here,
            # so skip — the label path above is preferred. A bare number string:
            try:
                value = float(score)
            except ValueError:
                value = None
        if value is not None:
            best = value if best is None else max(best, value)
    if best is not None:
        return _label_from_cvss_score(best)

    # 3) Unknown => HIGH (Q2 fail closed).
    return "HIGH"


def main() -> int:
    raw = os.environ.get("SCAN_JSON", "")
    if not raw.strip():
        print("severity: empty pip-audit JSON", file=sys.stderr)
        return 2
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"severity: malformed pip-audit JSON: {exc}", file=sys.stderr)
        return 2

    # pip-audit JSON: {"dependencies": [{"name","version","vulns":[...]}, ...]}.
    dependencies = data.get("dependencies")
    if dependencies is None:
        print("severity: pip-audit JSON has no 'dependencies' key", file=sys.stderr)
        return 2

    high = 0
    low = 0
    for dep in dependencies:
        name = dep.get("name", "?")
        version = dep.get("version", "?")
        for vuln in dep.get("vulns") or []:
            advisory = vuln.get("id", "?")
            fixed = ", ".join(vuln.get("fix_versions") or []) or "none"
            sev = _severity_for(vuln)
            if sev in HIGH_LABELS:
                high += 1
                mark = "FAIL"
            else:
                low += 1
                mark = "reported-only"
            print(
                f"PyPI {name} {version}  {advisory}  severity={sev}  "
                f"fixed={fixed}  [{mark}]"
            )

    print(f"COUNTS {high} {low}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
