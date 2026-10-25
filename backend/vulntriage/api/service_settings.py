"""Service-token settings, read from the environment at call time (issue #83).

The three service credentials are static opaque bearer tokens an operator
provisions (ASSUMPTION A1, #27/#50): the n8n token (``N8N_API_TOKEN``), the MCP
token (``MCP_API_TOKEN``) and the responder token (``RESPONDER_API_TOKEN``). No
value is logged, returned in an error or stored; each is compared in constant
time against the ``Authorization: Bearer`` value. For submission the n8n and MCP
tokens do not exist (their callers are future development); the responder token is used by
task 28's responder.
"""

from __future__ import annotations

import os


def get_n8n_api_token() -> str | None:
    return os.environ.get("N8N_API_TOKEN") or None


def get_mcp_api_token() -> str | None:
    return os.environ.get("MCP_API_TOKEN") or None


def get_responder_api_token() -> str | None:
    return os.environ.get("RESPONDER_API_TOKEN") or None
