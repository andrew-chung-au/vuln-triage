"""Keep the responder's secrets out of the agent's and the installer's environment, and out of the log (#244 B1, S6).

The Agent SDK starts the CLI with ``{**os.environ, **options.env}`` (read in
``claude_agent_sdk/_internal/transport/subprocess_cli.py``, 0.2.174): it can add
or override a variable but never remove one. So ``blank_non_allowlisted`` returns
an override of ``""`` for every inherited variable that is not on a short
allowlist of non-secret system names; that is how a responder secret is kept out.
``minimal_env`` is the same idea for a subprocess the runner starts itself, where
the environment can be given whole (``subprocess.run(env=...)``).

What this does NOT do: the model key and the git/``gh`` token the agent is given
on purpose stay visible to everything the agent runs (see
``_docs/responder-security-limits.md``). ``CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`` is
a name inside the bundled CLI, but it needs bubblewrap and a sandbox, and the
responder does not rely on it.
"""

from __future__ import annotations

import base64
from typing import Iterable, Mapping

# Names that carry no secret and that a CLI, git, make, uv or npm need to work.
# Proxy and CA names are here because the CLI needs the network; a proxy URL may
# carry credentials, which is a known, documented limit.
ENV_ALLOWLIST = frozenset({
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LANGUAGE", "TERM", "TZ", "PWD",
    "TMPDIR", "TEMP", "TMP",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
    "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "UV_CACHE_DIR", "UV_NATIVE_TLS", "UV_SYSTEM_CERTS",
})
ENV_ALLOWED_PREFIXES = ("LC_",)
MIN_REDACTED_LENGTH = 4  # shorter values would mangle ordinary text


def is_allowlisted(name: str) -> bool:
    return name in ENV_ALLOWLIST or name.startswith(ENV_ALLOWED_PREFIXES)


def blank_non_allowlisted(environ: Mapping[str, str]) -> dict[str, str]:
    """``{name: ""}`` for every variable in ``environ`` that is not allowlisted."""
    return {name: "" for name in environ if not is_allowlisted(name)}


def minimal_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Only the allowlisted variables of ``environ``: no secret can be in it."""
    return {name: value for name, value in environ.items() if is_allowlisted(name)}


def secret_forms(secret: str) -> set[str]:
    """The secret, its base64, and the base64 git sends (``x-access-token:<secret>``)."""
    if len(secret) < MIN_REDACTED_LENGTH:
        return set()
    b64 = lambda s: base64.b64encode(s.encode()).decode()  # noqa: E731
    return {secret, b64(secret), b64(f"x-access-token:{secret}")}


def redact(text: str | None, secrets: Iterable[str]) -> str | None:
    """``text`` with every known secret value (and its base64 forms) replaced by ``[REDACTED]``."""
    if not text:
        return text
    forms: set[str] = set()
    for secret in secrets:
        forms |= secret_forms(secret or "")
    for form in sorted(forms, key=len, reverse=True):  # longest first
        text = text.replace(form, "[REDACTED]")
    return text
