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


# The CLI runtime (#260). Docs read 2026-10-27 (code.claude.com/docs/en/authentication): the
# saved login is ``~/.claude/.credentials.json`` (Linux) under ``HOME``, or under
# ``CLAUDE_CONFIG_DIR`` when that is set; ``CLAUDE_CODE_OAUTH_TOKEN`` is a login token from
# ``claude setup-token``. Those three are the whole of "what the CLI needs to find its login".
CLI_LOGIN_VARS = frozenset({"CLAUDE_CONFIG_DIR", "CLAUDE_CODE_OAUTH_TOKEN"})
# Never in the CLI's environment, even if someone adds them to an allowlist: an API key or
# bearer token overrides the saved login and bills the API (authentication precedence in the
# same page), and the git/gh tokens must not reach the agent at all (the runner pushes).
CLI_FORBIDDEN = frozenset({
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_PROFILE",
    "ANTHROPIC_FEDERATION_RULE_ID", "ANTHROPIC_ORGANIZATION_ID", "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_PAT",
})


def cli_env(environ: Mapping[str, str], extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """The whole environment of a ``claude -p`` run: allowlisted names, the login variables,
    then ``extra`` (the run marker, git identity). Built from scratch, so no responder secret,
    API key, or git token can be in it; ``CLI_FORBIDDEN`` is removed last as a second line."""
    env = {n: v for n, v in environ.items() if is_allowlisted(n) or n in CLI_LOGIN_VARS}
    env.update(extra or {})
    for name in CLI_FORBIDDEN:
        env.pop(name, None)
    return env


def secret_forms(secret: str) -> set[str]:
    """The secret, its base64, and the base64 git sends (``x-access-token:<secret>``)."""
    if len(secret) < MIN_REDACTED_LENGTH:
        return set()
    b64 = lambda s: base64.b64encode(s.encode()).decode()  # noqa: E731
    return {secret, b64(secret), b64(f"x-access-token:{secret}")}


def _all_forms(secrets: Iterable[str]) -> set[str]:
    forms: set[str] = set()
    for secret in secrets:
        forms |= secret_forms(secret or "")
    return forms


def redact(text: str | None, secrets: Iterable[str]) -> str | None:
    """``text`` with every known secret value (and its base64 forms) replaced by ``[REDACTED]``."""
    if not text:
        return text
    for form in sorted(_all_forms(secrets), key=len, reverse=True):  # longest first
        text = text.replace(form, "[REDACTED]")
    return text


def redacted_window(text: str, secrets: Iterable[str], size: int, *, tail: bool) -> str:
    """The first (or, with ``tail``, last) ``size`` characters of ``text`` AFTER redaction.

    Redaction comes first and the cut second, so a secret that straddles the cut is replaced whole
    and no fragment of it can survive; redaction may shrink the text, so ``size`` is counted on the
    redacted text. The WHOLE text is redacted, never a bounded region of it: cutting a region first
    would bisect a secret at the region's edge (dropping characters there does not help, the new edge
    bisects the next copy). The cost is bounded already, by the 5 MB output limit on the text, and
    ``str.replace`` over that is milliseconds."""
    text = redact(text, secrets) or ""
    return text[-size:] if tail else text[:size]
