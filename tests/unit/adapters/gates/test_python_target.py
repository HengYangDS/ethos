"""The product's Python static check judges code against the version its repository supports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.python_quality as python_quality
from ethos.adapters.gates.python_target import PythonTarget
from ethos.adapters.gates.python_target import compatibility_target
from ethos.adapters.repo.git import current_tree
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.proof import declare_quality_profile
from tests.support.proof import run_quality_proof

if TYPE_CHECKING:
    from pathlib import Path

_TOMLLIB = "import json\nimport tomllib\n\nimport packaging\n\nprint(json, tomllib, packaging)\n"
_GENERIC = 'from typing import Generic, TypeVar\n\nT = TypeVar("T")\n\n\nclass Box(Generic[T]):\n'
_CARRIER = ".config/checks/ruff/ruff.toml"
# Fixture repositories carry the paradigm's Ruff carrier; without a target it decides nothing.
_UNTARGETED = {_CARRIER: "line-length = 100\n"}


def _manifest(requires: str, ruff: str = "") -> str:
    tool = f"\n[tool.ruff]\n{ruff}\n" if ruff else ""
    return f'[project]\nname = "sample"\nversion = "0"\nrequires-python = "{requires}"\n{tool}'


def _target(tmp_path: Path, files: dict[str, str]) -> PythonTarget:
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = 42\n", **_UNTARGETED, **files})
    return compatibility_target(repo, current_tree(repo), ("src/app.py",))


def _codes(report: dict[str, object]) -> list[str]:
    native = report["native"]
    assert isinstance(native, dict)
    return [finding["code"] for finding in json.loads(native["stdout"])]


@pytest.mark.parametrize(
    ("source", "requires", "target", "finding"),
    [
        pytest.param(_TOMLLIB, ">=3.12", "py312", None, id="tomllib-stdlib-at-3.12"),
        pytest.param(_TOMLLIB, ">=3.10", "py310", "I001", id="tomllib-third-party-at-3.10"),
        pytest.param(_GENERIC + "    pass\n", ">=3.11,<3.13", "py311", None, id="generic-at-3.11"),
        pytest.param(_GENERIC + "    pass\n", "~=3.12", "py312", "UP046", id="generic-at-3.12"),
    ],
)
def test_isolated_ruff_judges_code_against_the_declared_target(
    tmp_path: Path, source: str, requires: str, target: str, finding: str | None
) -> None:
    """The same code passes or fails only according to the version the repository supports."""
    repo = committed_source_repo(
        tmp_path, {"src/app.py": source, "pyproject.toml": _manifest(requires), **_UNTARGETED}
    )

    report = python_quality.static_report(repo)

    command = report["native"]["command"]
    assert command[command.index("--target-version") + 1] == target
    assert _codes(report) == ([finding] if finding else [])
    assert report["verdict"] == ("block" if finding else "pass")
    if finding is None:
        assert report["quality_evidence"]["python_target"] == {
            "version": target,
            "basis": "requires-python",
            "files": ["pyproject.toml"],
        }


def test_the_repositorys_own_ignores_do_not_weaken_the_judgment(tmp_path: Path) -> None:
    """A candidate's ignore list or noqa comment cannot remove a finding of its own target."""
    source = _GENERIC.replace("):\n", "):  # noqa: UP046\n") + "    pass\n"
    manifest = _manifest(">=3.12", 'lint.ignore = ["UP046"]')
    repo = committed_source_repo(tmp_path, {"src/app.py": source, "pyproject.toml": manifest})

    report = python_quality.static_report(repo)

    assert _codes(report) == ["UP046"]
    assert report["required_gaps"] == ["quality_static_diagnostics"]


def test_an_undeclared_target_is_a_gap_before_any_judgment(tmp_path: Path) -> None:
    """Without a declared version the checker's own default never decides the result."""
    repo = committed_source_repo(tmp_path, {"src/app.py": _TOMLLIB, **_UNTARGETED})

    report = python_quality.static_report(repo)

    assert report["required_gaps"] == ["quality_static_python_target_undeclared"]
    assert report["native"] == {}


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (
            {"pyproject.toml": _manifest(">=3.11")},
            ("py311", "requires-python", ("pyproject.toml",)),
        ),
        (
            {"pyproject.toml": _manifest(">=3.11", 'target-version = "py310"')},
            ("py310", "ruff-target-version", ("pyproject.toml",)),
        ),
        (
            {
                "pyproject.toml": _manifest(">=3.11", 'target-version = "py39"'),
                "ruff.toml": 'extend = "config/base.toml"\n',
                "config/base.toml": 'target-version = "py310"\n',
            },
            ("py310", "ruff-target-version", ("ruff.toml", "config/base.toml")),
        ),
        (
            {".ruff.toml": 'target-version = "py311"\n', "ruff.toml": 'target-version = "py39"\n'},
            ("py311", "ruff-target-version", (".ruff.toml",)),
        ),
        (
            {_CARRIER: 'target-version = "py312"\n', "pyproject.toml": _manifest(">=3.12,<3.15")},
            ("py312", "ruff-target-version", (_CARRIER,)),
        ),
        (
            {
                "pyproject.toml": _manifest(">=3.12"),
                "src/pyproject.toml": '[project]\nname = "inner"\nrequires-python = ">=3.12"\n',
                "tests/fixtures/ruff.toml": 'target-version = "py38"\n',
            },
            ("py312", "requires-python", ("pyproject.toml",)),
        ),
    ],
)
def test_the_target_follows_the_accepted_declaration_order(
    tmp_path: Path, files: dict[str, str], expected: tuple[str, str, tuple[str, ...]]
) -> None:
    """Ruff's own configuration and extend chain precede requires-python; unrelated trees do not."""
    target = _target(tmp_path, files)

    assert (target.version, target.basis, target.files) == expected


@pytest.mark.parametrize(
    ("files", "gap"),
    [
        ({}, "python_target_undeclared"),
        ({"pyproject.toml": '[project]\nname = "sample"\n'}, "python_target_undeclared"),
        ({"pyproject.toml": _manifest("<4")}, "python_target_undeclared"),
        ({"ruff.toml": "line-length = 88\n"}, "python_target_undeclared"),
        ({"pyproject.toml": _manifest("3.12")}, "python_target_invalid"),
        ({"pyproject.toml": _manifest(">=4")}, "python_target_invalid"),
        (
            {"pyproject.toml": _manifest(">=3.12", 'target-version = "3.12"')},
            "python_target_invalid",
        ),
        ({"pyproject.toml": "[project\n"}, "python_target_invalid"),
        ({"ruff.toml": 'extend = "../outside.toml"\n'}, "python_target_invalid"),
        ({"ruff.toml": 'extend = "missing.toml"\n'}, "python_target_invalid"),
        ({"ruff.toml": 'extend = "ruff.toml"\n'}, "python_target_invalid"),
        (
            {"pyproject.toml": _manifest(">=3.11", 'target-version = "py312"')},
            "python_target_conflict",
        ),
        (
            {_CARRIER: 'target-version = "py312"\n', "ruff.toml": 'target-version = "py311"\n'},
            "python_target_conflict",
        ),
        (
            {"pyproject.toml": _manifest(">=3.12"), "src/ruff.toml": 'target-version = "py310"\n'},
            "python_target_divergent",
        ),
        (
            {"pyproject.toml": _manifest(">=3.12"), "src/ruff.toml": "line-length = 88\n"},
            "python_target_divergent",
        ),
    ],
)
def test_missing_invalid_or_contradictory_context_is_a_gap(
    tmp_path: Path, files: dict[str, str], gap: str
) -> None:
    """Absent, malformed, conflicting and locally divergent declarations never become a default."""
    with pytest.raises(ValueError, match=f"^{gap}$"):
        _target(tmp_path, files)


@pytest.mark.parametrize(
    "files",
    [
        {"ruff.toml": 'extend = "/etc/ruff.toml"\n'},
        {"ruff.toml": 'extend = "~/ruff.toml"\n'},
        {"ruff.toml": "extend = 1\n"},
        {"pyproject.toml": 'tool = "ruff"\n'},
        {"pyproject.toml": '[tool]\nruff = "strict"\n'},
        {"pyproject.toml": 'project = "sample"\n'},
        {"pyproject.toml": "[project]\nrequires-python = 3.12\n"},
    ],
)
def test_malformed_declaration_carriers_are_invalid(tmp_path: Path, files: dict[str, str]) -> None:
    """Escaping or wrongly typed declarations are refused instead of being skipped."""
    with pytest.raises(ValueError, match=r"^python_target_invalid$"):
        _target(tmp_path, files)


def test_an_unreadable_tree_or_a_non_file_declaration_is_invalid(tmp_path: Path) -> None:
    """A declaration Git cannot read as a committed file never decides the target."""
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = 42\n", **_UNTARGETED})
    with pytest.raises(ValueError, match=r"^python_target_invalid$"):
        compatibility_target(repo, "f" * 40, ("src/app.py",))

    head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{head},ruff.toml")
    git(repo, "commit", "-m", "record a non-file Ruff declaration")
    with pytest.raises(ValueError, match=r"^python_target_invalid$"):
        compatibility_target(repo, current_tree(repo), ("src/app.py",))


def test_the_public_proof_reports_an_undeclared_target_as_a_static_gap(tmp_path: Path) -> None:
    """The installed proof surface carries the missing declaration out of the static gate."""
    repo = init_git_repo(tmp_path / "adopter")
    declare_quality_profile(repo, "profile")
    for path, content in {"src/app.py": _TOMLLIB, **_UNTARGETED}.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(content, encoding="utf-8")
    head = commit_fixture(repo, "bind quality without a declared Python target")

    payload = json.loads(run_quality_proof(repo, head).stdout)

    static = next(check for check in payload["data"]["checks"] if check["action_id"] == "static")
    report = json.loads(static["stdout"])["providers"][0]["report"]
    assert static["verdict"] == "block"
    assert report["required_gaps"] == ["quality_static_python_target_undeclared"]
