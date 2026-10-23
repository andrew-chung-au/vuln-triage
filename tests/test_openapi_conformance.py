"""OpenAPI conformance, I-CONTRACT (issue #88, task 14).

Compares FastAPI's generated document (``app.openapi()``) with
``_docs/openapi.yaml`` for every operation, at the granularity the hand-built
routes actually express (human decision, 2026-10-23, Option A):

- the path set (template variables normalised, so the contract's ``{id}`` and
  FastAPI's ``{finding_id}`` match), excluding ``GET /health`` by name;
- the HTTP method set per path;
- the success status code per operation;
- the security requirement per operation, checked against the ``Depends(...)``
  guard wired on the route (the generated document carries no ``security`` block
  for a ``Depends``-based guard, so the requirement is read off the guard).

Fields the test deliberately IGNORES, because they are documentation-only or are
not expressed by the current hand-built routes (and the endpoint shape is tasks
9b/10a/10b, out of scope here): ``title``, ``description``, ``summary``,
``operationId`` and ``examples``; declared query and header parameters; request
and response body schemas (the routes parse the body from raw bytes and return
plain ``dict``/``list`` with no ``response_model``); and the non-2xx responses.
``VERIFY:`` a fully schema/response/declared-``security`` conformance test needs
``response_model`` and declared parameters/security on every route, which is a
task-9b/10 change, not this one.

The contract's ``paths`` block is parsed by a small, strict reader (no YAML
dependency is added); any shape it does not expect raises, so it cannot pass by
mis-parsing. ``make openapi-validate`` validates the contract document itself.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from vulntriage.main import create_app

pytestmark = pytest.mark.sqlite_integration

CONTRACT = Path(__file__).resolve().parents[1] / "_docs" / "openapi.yaml"

# GET /health is infrastructure outside the contract (api.md): excluded by name.
EXCLUDED_PATHS = {"/health"}

# Each auth guard maps to the security scheme(s) the contract requires. A route
# with no guard is public (the contract's `security: []`).
GUARD_SCHEMES: dict[str, frozenset[str]] = {
    "require_session": frozenset({"cookieAuth"}),
    "require_session_or_mcp": frozenset({"cookieAuth", "mcpAuth"}),
    "require_n8n": frozenset({"n8nAuth"}),
    "require_mcp": frozenset({"mcpAuth"}),
    "require_responder": frozenset({"responderAuth"}),
}

_METHODS = {"get", "post", "put", "patch", "delete"}


def _normalise(path: str) -> str:
    """Collapse every ``{var}`` template segment to ``{}`` so FastAPI's
    function-derived names (``{finding_id}``) match the contract's (``{id}``)."""
    return "/".join("{}" if seg.startswith("{") and seg.endswith("}") else seg
                    for seg in path.split("/"))


# -- the contract side: a strict reader of the paths block ------------------


def _parse_contract_paths(text: str) -> dict[tuple[str, str], dict]:
    """Return {(normalised path, method): {status, security}} from the contract.

    Strict and scoped to the ``paths:`` block only. It reads, per operation, the
    single 2xx response status and the ``security`` scheme names. Anything that
    does not match the expected 2/4/6/8-space OpenAPI shape raises.
    """
    lines = text.splitlines()
    i = 0
    # advance to the top-level `paths:` key
    while i < len(lines) and lines[i].rstrip() != "paths:":
        i += 1
    if i == len(lines):
        raise AssertionError("contract has no top-level `paths:` block")
    i += 1

    ops: dict[tuple[str, str], dict] = {}
    path: str | None = None
    while i < len(lines):
        line = lines[i]
        if line.strip() == "" or line.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0:
            break  # left the paths block (next top-level key, e.g. components:)
        if indent == 2 and stripped.endswith(":"):
            path = stripped[:-1]
            if not path.startswith("/"):
                raise AssertionError(f"unexpected path key: {stripped!r}")
            i += 1
            continue
        if indent == 4 and stripped.endswith(":"):
            method = stripped[:-1]
            if method not in _METHODS:
                raise AssertionError(f"unexpected method key: {stripped!r} under {path}")
            assert path is not None
            op, consumed = _parse_operation(lines, i + 1)
            ops[(_normalise(path), method)] = op
            i = consumed
            continue
        raise AssertionError(f"unexpected line in paths block: {line!r}")
    return ops


def _parse_operation(lines: list[str], i: int) -> tuple[dict, int]:
    """Read one operation's body (indent >= 6); return its {status, security}."""
    security: set[str] = set()
    security_declared = False
    statuses: list[str] = []
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= 4:
            break  # next method or path
        stripped = line.strip()
        if indent == 6 and stripped == "security:":
            security_declared = True
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                ind = len(lines[i]) - len(lines[i].lstrip(" "))
                if ind == 8 and s.startswith("- "):
                    # e.g. "- cookieAuth: []"
                    scheme = s[2:].split(":", 1)[0].strip()
                    security.add(scheme)
                    i += 1
                else:
                    break
            continue
        if indent == 6 and stripped == "responses:":
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                ind = len(lines[i]) - len(lines[i].lstrip(" "))
                if ind == 8 and s.endswith(":"):
                    code = s[:-1].strip().strip("'\"")
                    if code.isdigit():
                        statuses.append(code)
                    i += 1
                elif ind >= 8:
                    i += 1  # nested lines under a status (description/content/$ref)
                else:
                    break
            continue
        i += 1
    success = [c for c in statuses if c.startswith("2")]
    if len(success) != 1:
        raise AssertionError(f"expected exactly one 2xx response, got {success}")
    return {"status": int(success[0]),
            "security": frozenset(security) if security_declared else frozenset()}, i


# -- the generated side -----------------------------------------------------
#
# Path, method and success status come from ``app.openapi()`` -- the document the
# contract test exists to check, and the same source ``test_smoke`` reads. The
# security requirement is read off each route's ``Depends`` guard, because the
# generated document carries no ``security`` block for a ``Depends``-based guard;
# routes are matched to openapi operations by their normalised path and method.


def _route_app():  # type: ignore[no-untyped-def]
    return create_app(session_factory=None, reader=None, run_worker=False)


def _guard_names_from_signature(func: object, seen: set[int]) -> set[str]:
    """Guard-function names reached from ``func``'s ``Depends(...)`` parameters.

    Reads the source of truth: every parameter default that is a FastAPI
    ``Depends`` marker exposes the dependency callable on ``.dependency``. A
    dependency may itself depend on a guard, so this recurses into each
    dependency callable (cycle-guarded by ``id``). This does not rely on how
    FastAPI builds its internal ``Dependant`` tree.
    """
    names: set[str] = set()
    if func is None or id(func) in seen:
        return names
    seen.add(id(func))
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return names
    for param in params.values():
        dependency = getattr(param.default, "dependency", None)
        if dependency is None:
            continue
        name = getattr(dependency, "__name__", "")
        if name in GUARD_SCHEMES:
            names.add(name)
        names |= _guard_names_from_signature(dependency, seen)
    return names


def _guard_schemes(route: object) -> frozenset[str]:
    """The security schemes implied by the ``Depends`` guards on a route.

    Guards are read from the route endpoint's own ``Depends(...)`` parameters
    (and, recursively, their dependencies) via the function signature -- the
    source of truth -- so a guard taken as a value (``user: User =
    Depends(require_session)``) is found as reliably as one taken for its effect
    only (``_: None = Depends(require_n8n)``). The route's ``dependant`` tree is
    also walked as a backstop for guards attached off the endpoint signature
    (e.g. router- or decorator-level ``dependencies=[...]``).
    """
    schemes: set[str] = set()
    endpoint = getattr(route, "endpoint", None)
    for name in _guard_names_from_signature(endpoint, set()):
        schemes |= set(GUARD_SCHEMES[name])

    root = getattr(route, "dependant", None)
    seen: set[int] = set()
    stack = [root] if root is not None else []
    while stack:
        dep = stack.pop()
        if dep is None or id(dep) in seen:
            continue
        seen.add(id(dep))
        name = getattr(getattr(dep, "call", None), "__name__", "")
        if name in GUARD_SCHEMES:
            schemes |= set(GUARD_SCHEMES[name])
        stack.extend(getattr(dep, "dependencies", []) or [])
    return frozenset(schemes)


def _iter_leaf_routes(routes, prefix: str = "", seen: set[int] | None = None):  # type: ignore[no-untyped-def]
    """Yield ``(full path, leaf route)`` for every endpoint route, descending into
    sub-routers/mounts.

    ``app.include_router`` in this FastAPI build keeps each router as a nested
    container object (its routes are not flattened onto ``app.routes``), so the
    tree is walked: a node with HTTP ``methods`` and a ``path`` is a leaf; a node
    that only carries nested ``routes`` is a container and is descended into, its
    ``prefix`` (if any) accumulated onto the path.
    """
    seen = set() if seen is None else seen
    for route in routes or []:
        if id(route) in seen:
            continue
        seen.add(id(route))
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path and methods:
            yield prefix + path, route
        nested = getattr(route, "routes", None)
        if nested:
            sub_prefix = prefix + (getattr(route, "prefix", "") or "")
            yield from _iter_leaf_routes(nested, sub_prefix, seen)


def _route_guards(app) -> dict[tuple[str, str], frozenset[str]]:  # type: ignore[no-untyped-def]
    """{(normalised path, method): guard schemes} for every API route on the app.

    The route tree is flattened first (this build nests included routers rather
    than flattening them onto ``app.routes``). HEAD/OPTIONS that FastAPI adds are
    dropped. The last writer wins, which is harmless: a given (path, method) has
    one leaf route.
    """
    guards: dict[tuple[str, str], frozenset[str]] = {}
    for full_path, route in _iter_leaf_routes(app.routes):
        methods = getattr(route, "methods", None) or set()
        schemes = _guard_schemes(route)
        for method in methods:
            m = method.lower()
            if m in _METHODS:
                guards[(_normalise(full_path), m)] = schemes
    return guards


def _generated_ops(app=None) -> dict[tuple[str, str], dict]:  # type: ignore[no-untyped-def]
    """{(normalised path, method): {status, security}} from the live FastAPI app.

    Path/method/success-status are taken from ``app.openapi()`` (so a route that
    openapi does not surface cannot pass unseen); the security requirement is the
    guard wired on the matching route.
    """
    app = app or _route_app()
    guards = _route_guards(app)
    ops: dict[tuple[str, str], dict] = {}
    for raw_path, methods in app.openapi()["paths"].items():
        if raw_path in EXCLUDED_PATHS:
            continue
        path = _normalise(raw_path)
        for method, operation in methods.items():
            m = method.lower()
            if m not in _METHODS:
                continue
            responses = operation.get("responses", {})
            success = sorted(c for c in responses if str(c).startswith("2"))
            if len(success) != 1:
                raise AssertionError(
                    f"{method.upper()} {raw_path}: expected one 2xx response, got {success}"
                )
            ops[(path, m)] = {
                "status": int(success[0]),
                "security": guards.get((path, m), frozenset()),
            }
    return ops


# -- the comparison ---------------------------------------------------------


def _contract_ops() -> dict[tuple[str, str], dict]:
    return _parse_contract_paths(CONTRACT.read_text())


def test_generated_and_contract_cover_the_same_operations() -> None:
    generated = set(_generated_ops())
    contract = set(_contract_ops())
    assert generated == contract, (
        f"only in generated: {generated - contract}; only in contract: {contract - generated}"
    )


def test_every_operation_has_the_contract_method_and_status() -> None:
    generated = _generated_ops()
    contract = _contract_ops()
    for key, c in contract.items():
        g = generated[key]
        assert g["status"] == c["status"], f"{key}: status {g['status']} != {c['status']}"


def test_every_operation_is_guarded_by_the_contract_security_scheme() -> None:
    # The generated document has no `security` block (auth is via Depends), so
    # the requirement is verified against the guard wired on each route.
    generated = _generated_ops()
    contract = _contract_ops()
    for key, c in contract.items():
        assert generated[key]["security"] == c["security"], (
            f"{key}: guard schemes {set(generated[key]['security'])} "
            f"!= contract {set(c['security'])}"
        )


def test_DIAG_dump_guard_map() -> None:  # TEMP diagnostic, remove after
    """Dump the flattened leaf routes and the computed guard map."""
    app = _route_app()
    leaves = list(_iter_leaf_routes(app.routes))
    guards = _route_guards(app)
    lines = [f"leaf routes found: {len(leaves)}"]
    for full_path, route in leaves:
        lines.append(f"  {full_path!r} methods={getattr(route, 'methods', None)!r} "
                     f"endpoint={getattr(getattr(route, 'endpoint', None), '__name__', None)}")
    lines.append(f"guard map entries: {len(guards)}")
    for k in sorted(guards):
        lines.append(f"  {k} -> {sorted(guards[k])}")
    raise AssertionError("DIAG guard map:\n" + "\n".join(lines))


def test_the_route_tree_is_flattened_and_guards_are_read() -> None:
    # Regression for the bug that cost several rounds: this FastAPI build nests
    # included routers rather than flattening them onto `app.routes`, so a scan
    # of `app.routes` alone found no endpoint routes and every guard read empty.
    # Assert the flattener reaches the leaf routes and that at least the four
    # guard families (and a public route) are detected, so an empty guard map
    # can never again masquerade as "all operations unguarded".
    app = _route_app()
    guards = _route_guards(app)
    assert ("/auth/me", "get") in guards, sorted(guards)
    assert guards[("/auth/me", "get")] == frozenset({"cookieAuth"})
    assert guards[("/signals/refresh", "post")] == frozenset({"n8nAuth"})
    assert guards[("/mcp/top-exposures", "get")] == frozenset({"mcpAuth"})
    assert guards[("/responder/notification-jobs", "get")] == frozenset({"responderAuth"})
    assert guards[("/assets/{}", "get")] == frozenset({"cookieAuth", "mcpAuth"})
    # login and logout are public (no guard).
    assert guards.get(("/auth/login", "post"), frozenset()) == frozenset()
    assert guards.get(("/auth/logout", "post"), frozenset()) == frozenset()
    # Every operation the contract lists must have a matching flattened route.
    missing = set(_contract_ops()) - set(guards)
    assert not missing, f"operations with no flattened route: {missing}"


def test_health_is_excluded_by_name_and_not_in_the_contract() -> None:
    # /health is not an operation in the contract and the backend serves none;
    # the exclusion is defensive so a future /health route cannot slip in.
    assert "/health" not in {p for p, _ in _contract_ops()}

    app = create_app(session_factory=None, reader=None, run_worker=False)

    @app.get("/health")
    def _health() -> dict[str, str]:  # type: ignore[no-untyped-def]
        return {"status": "ok"}

    # With /health served but excluded by name, the operation sets still match.
    assert set(_generated_ops(app)) == set(_contract_ops())


def test_a_route_missing_from_the_contract_fails_the_comparison() -> None:
    # Adding a route not in the contract must break operation-set equality, so
    # the exclusion hides nothing else (testing.md).
    app = create_app(session_factory=None, reader=None, run_worker=False)

    @app.get("/_not_in_contract")
    def _extra() -> dict[str, str]:  # type: ignore[no-untyped-def]
        return {}

    gen = set(_generated_ops(app))
    assert gen != set(_contract_ops())
    assert ("/_not_in_contract", "get") in gen


def test_a_deliberate_contract_mismatch_fails(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # A .scratch/ copy of the contract with one operation changed must make the
    # comparison fail. We flip one compared dimension — a success status code —
    # on one operation (schema internals are not compared; see ignored fields).
    text = CONTRACT.read_text()
    # auth/login's only 2xx is 200; change it to 299 in the copy.
    marker = "      operationId: login\n"
    assert marker in text
    broken = text.replace(
        "        '200':\n          description: Signed in. The response sets the `vt_session` cookie.",
        "        '299':\n          description: Signed in. The response sets the `vt_session` cookie.",
        1,
    )
    assert broken != text, "the deliberate-mismatch edit did not apply"
    copy = tmp_path / "openapi-broken.yaml"
    copy.write_text(broken)

    contract = _parse_contract_paths(broken)
    generated = _generated_ops()
    key = ("/auth/login", "post")
    # The mutated login status (299) no longer matches the generated 200.
    assert contract[key]["status"] == 299
    assert generated[key]["status"] == 200
    mismatches = [k for k in contract if generated[k]["status"] != contract[k]["status"]]
    assert mismatches == [key], mismatches
