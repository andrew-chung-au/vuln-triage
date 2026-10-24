"""Observability: OpenTelemetry SDK setup, the attribute allowlist, the US-13
metrics and the JSON-lines logger (task 23 / #154).

The exclusion rule (US-13) is enforced in code here: every span attribute and
log field is written through :func:`allowlist.filter_attributes`, which keeps
only the A32 allowlist keys and drops the rest. The Collector-side processor
(task 24) is a second line of defence, not the only one.
"""
