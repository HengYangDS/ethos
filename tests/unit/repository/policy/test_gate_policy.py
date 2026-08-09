from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.repository.policy.gates import canonical_gate_command
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_script_gate_policy

if TYPE_CHECKING:
    from pathlib import Path


def test_gate_policy_binds_committed_sources_and_reports_missing_source(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo)
    first = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "policy"))
    assert tuple(node.id for node in first.nodes) == ("check", "publish")
    assert first.gaps == ()

    registry = repo / "system/gates.toml"
    registry.write_text(registry.read_text().replace("tools/check.sh", "tools/check-v2.sh"))
    (repo / "tools/check-v2.sh").write_text("#!/bin/sh\nexit 0\n")
    changed = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "command"))
    assert changed.digest != first.digest

    (repo / "tools/check-v2.sh").unlink()
    missing = commit_fixture(repo, "missing")
    (repo / "tools/check-v2.sh").write_text("#!/bin/sh\nexit 0\n")
    assert resolve_gate_policy(repo, tree_ref=missing).gaps == (
        "gate_policy_source_missing:check:tools/check-v2.sh",
    )


def test_nox_gate_binds_repository_sources_and_requires_runtime(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo)
    registry = repo / "system/gates.toml"
    registry.write_text(
        registry.read_text().replace(
            '["tools/check.sh"]',
            '["{python}", "-m", "nox", "-s", "check"]',
        )
    )
    for relative, text in (
        ("noxfile.py", "def check(): pass\n"),
        ("pyproject.toml", "[project]\nname='x'\nversion='0'\n"),
        ("uv.lock", "version=1\n"),
    ):
        (repo / relative).write_text(text)

    missing = commit_fixture(repo, "nox without runtime")
    assert resolve_gate_policy(repo, tree_ref=missing).gaps == (
        "gate_runtime_missing:repository-python",
    )

    runtime = repo / ".venv/bin/python"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("")
    bound = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "bind nox runtime"))
    assert bound.gaps == ()
    assert {path for path, _digest in bound.sources[0][1]} == {
        "noxfile.py",
        "pyproject.toml",
        "uv.lock",
    }


def test_gate_policy_identity_binds_profile_semantics_and_python_command(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    profile = repo / ".ethos/profile.toml"
    first = resolve_gate_policy(repo, tree_ref=git(repo, "rev-parse", "HEAD")).digest

    profile.write_text(
        profile.read_text().replace(
            'dimensions = ["test", "coverage"]',
            'dimensions = ["test", "coverage", "property"]',
        )
    )
    changed = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "change dimensions"))
    assert changed.digest != first

    profile.write_text(
        profile.read_text().replace(
            'static-analysis = "sample-static"',
            'static-analysis = "sample-tests"',
        )
    )
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "invalidate map"))

    assert canonical_gate_command(("/one/bin/python3.14", "-m", "tool")) == (
        "python",
        "-m",
        "tool",
    )
    assert canonical_gate_command(("python3.12", "-m", "tool")) != canonical_gate_command(
        ("python3.13", "-m", "tool")
    )
