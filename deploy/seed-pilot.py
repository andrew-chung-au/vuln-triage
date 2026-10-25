#!/usr/bin/env python3
"""Register the pilot seed assets through POST /assets (task 22 / #144).

Reads deploy/pilot-seed.json and registers each asset against a running
VulnTriage backend **through the API** (US-1) — it never writes to the database.
Use it against the dev environment once that is up (the human runs it; the agent
holds no dev credentials). Stdlib only (urllib); no new dependency.

The repository URLs stay out of telemetry (A38): this is a plain API client and
emits no spans, metrics or logs; it only prints to the console for the operator.

Usage:
    # password is read from a prompt (never passed on the command line) or, for
    # non-interactive use, from the VT_SEED_PASSWORD environment variable.
    python deploy/seed-pilot.py \\
        --base-url https://dev.<eip>.sslip.io \\
        --username <security-lead-username>

    python deploy/seed-pilot.py --base-url http://localhost:8080 \\
        --username lead --seed-file deploy/pilot-seed.json --insecure

Only a `security lead` may register an asset (US-1); sign in as one. Each asset
starts its first scan asynchronously; check the dashboard for the scan status
and findings (the acceptance check).
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from typing import Any

_CSRF_HEADER = "X-Requested-With"
_CSRF_VALUE = "XMLHttpRequest"
_COOKIE_NAME = "vt_session"
_SKIP_FLAG = "_use_only_if_juice_shop_has_no_package_lock"
_REGISTER_FIELDS = (
    "name",
    "ownerName",
    "ownerEmail",
    "criticality",
    "internetFacing",
    "repositoryUrl",
)


class SeedError(Exception):
    """A fatal error registering the pilot seed."""


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    ctx: ssl.SSLContext | None,
    cookie: str | None = None,
    json_body: Any | None = None,
) -> tuple[int, dict[str, str], bytes]:
    data = None
    headers: dict[str, str] = {}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if method != "GET":
        headers[_CSRF_HEADER] = _CSRF_VALUE
    if cookie is not None:
        headers["Cookie"] = f"{_COOKIE_NAME}={cookie}"
    req = urllib.request.Request(
        f"{base_url}{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:  # noqa: S310
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, exc.read()
    except (urllib.error.URLError, OSError) as exc:
        raise SeedError(f"{method} {path} failed: {exc}") from exc


def login(base_url: str, username: str, password: str, ctx: ssl.SSLContext | None) -> str:
    status, headers, body = _request(
        base_url, "POST", "/auth/login",
        ctx=ctx, json_body={"username": username, "password": password},
    )
    if status != 200:
        raise SeedError(
            f"login failed ({status}). Use a `security lead` account; a wrong "
            f"username/password returns 401. Body: {body[:200]!r}"
        )
    match = re.search(rf"{_COOKIE_NAME}=([^;]+)", headers.get("set-cookie", ""))
    if not match:
        raise SeedError("login succeeded but no vt_session cookie was returned")
    return match.group(1)


def load_seed(path: str) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedError(f"could not read seed file {path}: {exc}") from exc
    assets = doc.get("assets")
    if not isinstance(assets, list):
        raise SeedError(f"{path} has no 'assets' list")
    return assets


def to_body(entry: dict[str, Any]) -> dict[str, Any]:
    """The exact NewAssetInput body for an entry (only the registration fields)."""
    missing = [f for f in _REGISTER_FIELDS if f not in entry]
    if missing:
        raise SeedError(f"seed entry {entry.get('name', '?')!r} is missing {missing}")
    if "REPLACE_ME" in str(entry.get("repositoryUrl", "")):
        raise SeedError(
            f"seed entry {entry.get('name', '?')!r} still has a REPLACE_ME "
            "repositoryUrl — fill in the real pilot repositories first"
        )
    return {f: entry[f] for f in _REGISTER_FIELDS}


def register_all(
    base_url: str, cookie: str, assets: list[dict[str, Any]], ctx: ssl.SSLContext | None
) -> int:
    registered = skipped = failed = 0
    for entry in assets:
        name = entry.get("name", "?")
        if entry.get(_SKIP_FLAG):
            print(f"  skip (A41 fallback, remove the flag to use): {name}")
            skipped += 1
            continue
        body = to_body(entry)
        status, _headers, resp = _request(
            base_url, "POST", "/assets", ctx=ctx, cookie=cookie, json_body=body
        )
        if status == 201:
            asset = json.loads(resp)
            print(f"  registered: {name}  (id={asset.get('id')}, scan={asset.get('scanStatus')})")
            registered += 1
        elif status == 403:
            raise SeedError(
                "403 registering an asset: the signed-in user is not a "
                "`security lead` (only a security lead may register; US-1)."
            )
        else:
            print(f"  FAILED ({status}): {name}: {resp[:200]!r}", file=sys.stderr)
            failed += 1
    print(f"\n{registered} registered, {skipped} skipped, {failed} failed.")
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register the pilot seed assets through POST /assets.")
    parser.add_argument("--base-url", required=True, help="Backend base URL, e.g. https://dev.<eip>.sslip.io")
    parser.add_argument("--username", required=True, help="A `security lead` username to sign in as")
    parser.add_argument("--seed-file", default="deploy/pilot-seed.json", help="Seed JSON (default: deploy/pilot-seed.json)")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification (local/self-signed only)")
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    ctx: ssl.SSLContext | None = None
    if args.insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    # Password: from VT_SEED_PASSWORD if set, else prompted — never a CLI arg,
    # so it does not land in shell history or process listings (same rule as the
    # operator create-user command).
    password = os.environ.get("VT_SEED_PASSWORD") or getpass.getpass("Password: ")
    if not password:
        print("No password given (set VT_SEED_PASSWORD or type one at the prompt).", file=sys.stderr)
        return 2

    try:
        assets = load_seed(args.seed_file)
        cookie = login(base_url, args.username, password, ctx)
        print(f"Signed in to {base_url}; registering {len(assets)} seed entr(y/ies)…")
        failed = register_all(base_url, cookie, assets, ctx)
    except SeedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
