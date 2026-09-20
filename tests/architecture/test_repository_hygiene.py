"""Enforce repository hygiene and reject source-level quality suppressions."""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from tools.ci.repository_hygiene import audit

ROOT = Path(__file__).resolve().parents[2]


def _initialize_repository(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)


def _write_policy(repo: Path) -> None:
    """Exercise the shipped policy rather than copy its declaration."""
    path = Path(".config/checks/repository-hygiene/policy.toml")
    (repo / path).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / path, repo / path)


def test_repository_hygiene_is_one_python_nox_owner(pytestconfig: pytest.Config) -> None:
    policy = (ROOT / ".config/checks/repository-hygiene/policy.toml").read_text(encoding="utf-8")
    sessions = (ROOT / "tools/ci/sessions.py").read_text(encoding="utf-8")

    assert [path.resolve() for path in pytestconfig.getini("pythonpath")] == [ROOT, ROOT / "src"]
    assert "root_host_residue = [" in policy
    assert '".DS_Store"' in policy
    assert "def repository_hygiene(session)" in sessions
    assert '"--ignore-noqa"' in sessions
    coverage = tomllib.loads(
        (ROOT / ".config/checks/coverage/coverage.toml").read_text(encoding="utf-8")
    )["tool"]["coverage"]
    assert coverage["run"]["branch"] is True
    assert coverage["report"]["exclude_lines"] == []
    assert not (ROOT / "tools/ci/scripts/run-repository-hygiene.sh").exists()


def test_full_proof_includes_the_repository_hygiene_owner_once() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {item["id"]: item for item in declaration["gates"]}

    assert full.count("repository-hygiene") == 1
    assert gates["repository-hygiene"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "repository_hygiene",
    ]


def test_repository_hygiene_rejects_global_ignored_ds_store(tmp_path: Path) -> None:
    repo = tmp_path
    _write_policy(repo)
    _initialize_repository(repo)
    (repo / ".DS_Store").write_bytes(b"host-local residue")

    failures = audit(repo)

    assert ".DS_Store: host-local root residue is not repository truth; remove it" in failures


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        ("module.py", "value = call()  # noqa: F821\n", ("1:noqa",)),
        (
            "check.sh",
            "#!/bin/sh\n# shellcheck disable=SC2086\nprintf ok\n",
            ("2:shellcheck-disable",),
        ),
        (
            "module.py",
            "# fmt: off\nvalue = 1  # pragma: no cover\n# fmt: on\n",
            ("1:format-off", "2:coverage-ignore", "3:format-on"),
        ),
    ],
)
def test_repository_hygiene_rejects_source_suppressions(
    tmp_path: Path, filename: str, content: str, expected: tuple[str, ...]
) -> None:
    """All suppression transports use the same native hygiene owner."""
    _write_policy(tmp_path)
    (tmp_path / filename).write_text(content, encoding="utf-8")
    _initialize_repository(tmp_path)
    failures = audit(tmp_path)
    assert all(
        f"{filename}:{line}: forbidden quality suppression: {label}" in failures
        for item in expected
        for line, label in (item.split(":"),)
    )


@pytest.mark.parametrize("tracked", [False, True])
def test_hygiene_rejects_directory_indexes_across_authored_roots(
    tmp_path: Path, *, tracked: bool
) -> None:
    """Reject nested indexes without erasing inert history or example mentions."""
    _write_policy(tmp_path)
    _initialize_repository(tmp_path)
    denied = (
        "index.md",
        "docs/concepts/index.md",
        "rules/index.md",
        ".agents/skills/sample/index.md",
        "openspec/specs/sample/index.md",
    )
    retained = (
        "docs/README.md",
        "docs/guide.md",
        "openspec/changes/archive/old/index.md",
        "docs/history/index.md",
        "node_modules/dependency/index.md",
    )
    for relative in (*denied, *retained):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Directory\n\nSee index.md in the historical example.\n")
    if tracked:
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    failures = audit(tmp_path)
    expected = {f"{path}: directory navigation must use README.md, not index.md" for path in denied}
    assert set(failures) == expected
    for relative in denied:
        (tmp_path / relative).unlink()
    assert audit(tmp_path) == ()
