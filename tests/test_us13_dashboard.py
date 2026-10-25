"""Static check of the US-13 dashboard's Prometheus queries (#195).

Every Prometheus ``expr`` in ``observability/grafana/dashboards/us13-journey.json``
must use only metric and label names the backend exports. The allowed sets are
derived from the backend source (instrument names in
``vulntriage/observability/metrics.py``; attribute keys passed to the counter and
histogram in ``vulntriage/mail/delivery.py``). The Collector's Prometheus exporter
(``observability/otel-collector.yaml``) turns dots into underscores, so the
attribute ``vt.notification.kind`` is the Prometheus label ``vt_notification_kind``.

VERIFY: the exporter's sanitising rule is inferred; the live check is #199.
"""

from __future__ import annotations

import json
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_DASHBOARD = _ROOT / "observability/grafana/dashboards/us13-journey.json"
_METRICS_PY = _ROOT / "backend/vulntriage/observability/metrics.py"
_DELIVERY_PY = _ROOT / "backend/vulntriage/mail/delivery.py"

# Template variable queries whose labels cannot be proved statically: they may be
# resource attributes that never become series labels. Unverified, live check
# pending (#199); deliberately not asserted valid.
_UNVERIFIED_VARIABLE_LABELS = {"deployment_environment", "service_version"}

_PROMQL_KEYWORDS = {"by", "without", "on", "ignoring", "group_left", "group_right", "bool"}


def _sanitise(name: str) -> str:
    """The exporter's rule: dots become underscores (one helper, used everywhere)."""
    return name.replace(".", "_")


def _allowed_metrics() -> set[str]:
    src = _METRICS_PY.read_text()
    names = re.findall(r'create_\w+\(\s*"([A-Za-z0-9_.]+)"', src)
    return {_sanitise(n) for n in names}


def _allowed_labels() -> set[str]:
    src = _DELIVERY_PY.read_text()
    keys: set[str] = set()
    call = re.compile(
        r"(?:notifications_total\.add|notification_delivery_seconds\.record)"
        r"\(.*?(\{[^{}]*\})",
        re.DOTALL,
    )
    for m in call.finditer(src):
        keys.update(re.findall(r'"([A-Za-z0-9_.]+)"\s*:', m.group(1)))
    # The overdue gauge's own labels (metrics.py, _observe_overdue).
    keys.update({"finding_id", "tier"})
    return {_sanitise(k) for k in keys}


def _prom_exprs(dash: dict) -> list[str]:
    """Every Prometheus expr: panel targets and templating queries."""
    out: list[str] = []
    for panel in dash.get("panels", []):
        if panel.get("datasource", {}).get("type") != "prometheus":
            continue
        out.extend(t["expr"] for t in panel.get("targets", []) if "expr" in t)
    for var in dash.get("templating", {}).get("list", []):
        if var.get("datasource", {}).get("type") == "prometheus" and "query" in var:
            out.append(var["query"])
    return out


def _check_expr(expr: str, metrics: set[str], labels: set[str]) -> list[str]:
    """Return a list of problems with one Prometheus expression."""
    problems: list[str] = []

    lv = re.fullmatch(r"\s*label_values\(\s*([A-Za-z0-9_]+)\s*\)\s*", expr)
    if lv:
        label = lv.group(1)
        if label not in _UNVERIFIED_VARIABLE_LABELS:
            problems.append(f"unknown label '{label}' in {expr!r}")
        return problems  # unverified, live check pending (#199): not asserted valid

    text = re.sub(r'"[^"]*"', '""', expr)  # drop string literals
    for clause in re.finditer(r"\b(?:by|without)\s*\(([^)]*)\)", text):
        for lab in (s.strip() for s in clause.group(1).split(",")):
            if lab and lab not in labels:
                problems.append(f"unknown label '{lab}' in {expr!r}")
    for sel in re.finditer(r"\{([^}]*)\}", text):
        for lab in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:=~|!~|!=|=)", sel.group(1)):
            if lab not in labels:
                problems.append(f"unknown label '{lab}' in {expr!r}")

    bare = re.sub(r"\b(?:by|without)\s*\([^)]*\)", " ", text)
    bare = re.sub(r"\{[^}]*\}", " ", bare)
    bare = re.sub(r"\[[^\]]*\]", " ", bare)
    bare = re.sub(r"\b\d+(?:\.\d+)?[smhdwy]?\b", " ", bare)
    for m in re.finditer(r"[A-Za-z_:][A-Za-z0-9_:]*(?!\w)(\s*\()?", bare):
        if m.group(1) or m.group(0).strip() in _PROMQL_KEYWORDS:
            continue  # function / aggregation name or keyword
        name = m.group(0).strip()
        if name not in metrics:
            problems.append(f"unknown metric '{name}' in {expr!r}")
    return problems


def test_derived_sets_contain_the_exported_names() -> None:
    assert "vt_notifications_total" in _allowed_metrics()
    assert {"vt_notification_kind", "vt_outcome"} <= _allowed_labels()


def test_dashboard_prometheus_queries_use_exported_names() -> None:
    dash = json.loads(_DASHBOARD.read_text())
    exprs = _prom_exprs(dash)
    assert exprs, "no Prometheus queries found"
    metrics, labels = _allowed_metrics(), _allowed_labels()
    problems = [p for e in exprs for p in _check_expr(e, metrics, labels)]
    assert not problems, "\n".join(problems)


def test_panel_one_legend_uses_exported_label_names() -> None:
    dash = json.loads(_DASHBOARD.read_text())
    target = dash["panels"][0]["targets"][0]
    assert "vt_notifications_total" in target["expr"]
    assert target["legendFormat"] == "{{vt_notification_kind}}/{{vt_outcome}}"


def test_old_panel_query_is_rejected_naming_the_label() -> None:
    old = "sum by (kind, outcome) (rate(vt_notifications_total[5m]))"
    problems = _check_expr(old, _allowed_metrics(), _allowed_labels())
    assert any("unknown label 'kind'" in p for p in problems)
    assert any("unknown label 'outcome'" in p for p in problems)


def test_unknown_metric_name_is_rejected() -> None:
    problems = _check_expr(
        "sum by (vt_outcome) (rate(vt_no_such_total[5m]))",
        _allowed_metrics(),
        _allowed_labels(),
    )
    assert any("unknown metric 'vt_no_such_total'" in p for p in problems)


def test_unknown_matcher_label_is_rejected() -> None:
    problems = _check_expr(
        'vt_notifications_total{outcome="sent"}', _allowed_metrics(), _allowed_labels()
    )
    assert any("unknown label 'outcome'" in p for p in problems)


def test_valid_query_passes() -> None:
    expr = 'sum by (vt_notification_kind, vt_outcome) (rate(vt_notifications_total{vt_outcome="sent"}[5m]))'
    assert _check_expr(expr, _allowed_metrics(), _allowed_labels()) == []
