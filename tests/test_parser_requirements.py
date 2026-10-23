"""U-REQ: requirements.txt parser and include resolution (hand-written text)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from vulntriage.ingest.requirements import parse_requirements, resolve_include


pytestmark = pytest.mark.unit  # task 13: the U-* backend unit layer
FILE = "requirements.txt"


def one(line: str):
    result = parse_requirements(line + "\n", FILE)
    assert len(result.entries) == 1, result
    return result


@pytest.mark.parametrize("spec", ["pkg==1.2.3", "pkg===1.2.3", "pkg == 1.2.3", "pkg[extra,more]==1.2.3"])
def test_exact_pins_give_the_version(spec: str) -> None:
    result = one(spec)
    assert result.entries[0].version == "1.2.3"
    assert result.entries[0].direct is True
    assert result.warnings == []


@pytest.mark.parametrize(
    "spec",
    [
        "pkg>=1.0",
        "pkg~=1.0",
        "pkg!=1.0",
        "pkg==1.2.*",
        "pkg",
        'pkg==1.0; python_version < "3"',
        "pkg==not.a.version",
        "pkg>=1,<2",
        "-e ./local/pkg",
        "-e git+https://example.invalid/x/pkg.git#egg=pkg",
        "git+https://example.invalid/x/pkg.git",
        "pkg @ https://example.invalid/pkg-1.0-py3-none-any.whl",
    ],
)
def test_unpinned_forms_are_version_unknown(spec: str) -> None:
    result = one(spec)
    assert result.entries[0].version is None
    assert [w.kind for w in result.warnings] == ["version unknown"]
    assert result.warnings[0].line == 1
    assert "example.invalid" not in result.warnings[0].message


@pytest.mark.parametrize("flag", ["-c cons.txt", "--constraint cons.txt", "--constraint=cons.txt"])
def test_constraints_give_only_the_exact_warning(flag: str) -> None:
    result = parse_requirements(flag, FILE)
    assert result.entries == [] and result.includes == []
    assert [(w.kind, w.message) for w in result.warnings] == [
        ("constraints file ignored", "constraints file ignored")
    ]


@pytest.mark.parametrize(
    "flag",
    [
        "-i https://x.example/simple",
        "--index-url https://x.example/simple",
        "--index-url=https://x.example/simple",
        "--extra-index-url https://x.example/simple",
        "-f https://x.example/links",
        "--find-links https://x.example/links",
    ],
)
def test_index_options_give_only_the_exact_warning(flag: str) -> None:
    result = parse_requirements(flag, FILE)
    assert result.entries == []
    assert [(w.kind, w.message) for w in result.warnings] == [
        ("index option ignored", "index option ignored")
    ]


def test_continuations_comments_hashes_and_normalised_names() -> None:
    text = (
        "# a comment\n"
        "\n"
        "My_Pkg.Name[x]==1.0 \\\n"
        "    --hash=sha256:abc \\\n"
        "    --hash=sha256:def  # trailing\n"
        "other==2.0   # note\n"
    )
    result = parse_requirements(text, FILE)
    assert [(e.name, e.version) for e in result.entries] == [("my-pkg-name", "1.0"), ("other", "2.0")]
    assert result.warnings == []


def test_warning_line_is_the_first_physical_line() -> None:
    result = parse_requirements("a==1\nb \\\n>=2\n", FILE)
    assert [w.line for w in result.warnings] == [2]


def test_includes_are_returned_for_resolution() -> None:
    result = parse_requirements("-r other.txt\n--requirement sub/x.txt\n-rshort.txt\n", FILE)
    assert [(i.target, i.line) for i in result.includes] == [
        ("other.txt", 1),
        ("sub/x.txt", 2),
        ("short.txt", 3),
    ]


def test_attacker_index_and_url_give_two_warnings_and_no_request() -> None:
    text = "--index-url https://attacker.example/simple\npkg @ https://attacker.example/pkg.whl\n"
    result = parse_requirements(text, FILE)
    assert [w.kind for w in result.warnings] == ["index option ignored", "version unknown"]
    assert len(result.warnings) == 2


@pytest.mark.parametrize(
    ("including", "target", "expected"),
    [
        ("requirements.txt", "dev.txt", "dev.txt"),
        ("requirements.txt", "sub/dev.txt", "sub/dev.txt"),
        ("sub/a.txt", "b.txt", "sub/b.txt"),
        ("sub/a.txt", "../b.txt", "b.txt"),
        ("requirements.txt", "sub/../x.txt", "x.txt"),
        ("requirements.txt", "/etc/passwd", None),
        ("requirements.txt", "../x.txt", None),
        ("requirements.txt", "sub/../../x.txt", None),
        ("sub/a.txt", "../../x.txt", None),
        ("requirements.txt", "https://attacker.example/r.txt", None),
        ("requirements.txt", "file:///etc/passwd", None),
        ("requirements.txt", "C:\\x.txt", None),
        ("requirements.txt", "a\\b.txt", None),
        ("requirements.txt", "a\x00b.txt", None),
        ("requirements.txt", "", None),
        ("requirements.txt", ".", None),
    ],
)
def test_resolve_include(including: str, target: str, expected: str | None) -> None:
    assert resolve_include(including, target) == expected


def test_parser_modules_import_no_network_library() -> None:
    forbidden = {"httpx", "urllib", "socket", "requests", "http"}
    root = Path(__file__).resolve().parent.parent / "backend" / "vulntriage" / "ingest"
    for name in ("uv_lock.py", "requirements.py", "package_lock.py", "models.py"):
        tree = ast.parse((root / name).read_text())
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                assert module.split(".")[0] not in forbidden, f"{name} imports {module}"
