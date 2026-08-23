"""Installed reference-transaction runtime and fail-closed integration."""

from __future__ import annotations

import io
import os
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.hook_runtime import execute_hook
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import render_branch_policy

if TYPE_CHECKING:
    import pytest


def _unavailable_runtime_repo(tmp_path: Path):
    def g(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=False, env=env
        )

    g("init", "-b", "dev")
    g("config", "user.name", "t")
    g("config", "user.email", "t@e.x")
    hooks = tmp_path / ".git/test-hooks"
    hooks.mkdir(exist_ok=True)
    hook = hooks / "reference-transaction"
    hook.write_text(
        "#!/bin/sh\n"
        "# Deliberately unavailable runtime: fail closed before policy execution.\n"
        'exec "/missing/ethos/python" -I -m ethos.cli hook run reference-transaction "$@"\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    (workspace := tmp_path / ".ethos/workspace.toml").parent.mkdir()
    workspace.write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        ),
        encoding="utf-8",
    )
    (tmp_path / "a").write_text("1", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "base")
    g("branch", "candidate/dev")
    g("branch", "work/x")
    g("config", "core.hooksPath", hooks.as_posix())
    return g, hooks, {**os.environ, "PATH": "/usr/bin:/bin"}


def test_reference_transaction_hook_fails_closed_on_governed_branches(tmp_path: Path) -> None:
    """A missing bound runtime blocks raw governed ref changes without an env escape."""
    g, hooks, no_binary = _unavailable_runtime_repo(tmp_path)

    raw_creation = g("checkout", "-b", "work/unleased", env=no_binary)
    assert raw_creation.returncode != 0
    assert g("show-ref", "--verify", "refs/heads/work/unleased").returncode != 0

    dev_before_noop = g("rev-parse", "dev").stdout.strip()
    maintenance = g("pack-refs", "--all", "--prune", env=no_binary)
    assert maintenance.returncode != 0
    assert g("rev-parse", "dev").stdout.strip() == dev_before_noop
    g("checkout", "work/x", env=no_binary)
    blocked_delete = g("branch", "-D", "dev", env=no_binary)
    assert blocked_delete.returncode != 0
    assert g("rev-parse", "dev").stdout.strip() == dev_before_noop
    g("checkout", "dev", env=no_binary)

    (tmp_path / "b").write_text("2", encoding="utf-8")
    g("add", ".")
    blocked = g("commit", "-m", "direct to dev", env=no_binary)
    assert blocked.returncode != 0
    dev_head = g("rev-parse", "dev").stdout.strip()

    g("config", "core.hooksPath", "")
    assert g("checkout", "work/x").returncode == 0
    g("config", "core.hooksPath", hooks.as_posix())
    (tmp_path / "w").write_text("w", encoding="utf-8")
    g("add", ".")
    work_commit = g("commit", "-m", "work commit", env=no_binary)
    assert work_commit.returncode != 0
    g("config", "core.hooksPath", "")
    committed = g("commit", "-m", "work commit")
    assert committed.returncode == 0
    assert g("checkout", "dev").returncode == 0
    g("config", "core.hooksPath", hooks.as_posix())

    escape = g("merge", "--ff-only", "work/x", env={**no_binary, "ETHOS_ALLOW_REF_MOVE": "1"})
    assert escape.returncode != 0
    assert g("rev-parse", "dev").stdout.strip() == dev_head


def test_reference_transaction_hook_fails_closed_on_empty_release_mirror_verdict(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "candidate"
    git(repo, "branch", "main")
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    (candidate / "change").write_text("candidate\n", encoding="utf-8")
    git(candidate, "add", "change")
    git(candidate, "commit", "-m", "candidate")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    exclude = repo / git(repo, "rev-parse", "--git-path", "info/exclude")
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as excluded:
        excluded.write("build/\nsrc/\ntools/\n")
    install_hook_launchers(repo)
    install_hook_launchers(candidate)
    package = candidate / "src/ethos"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir(parents=True)
    workspace.write_text('[branch_roles]\nrelease_mirror = "accepted_ff"\n', encoding="utf-8")
    hook = Path(str(hook_runtime_binding(repo)["hooks_path"])) / "reference-transaction"

    completed = subprocess.run(
        [hook, "prepared"],
        cwd=repo,
        input=f"{git(repo, 'rev-parse', 'main')} {candidate_head} refs/heads/main\n",
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0


def test_reference_transaction_hook_uses_the_candidate_project_environment() -> None:
    owner = Path(__file__).resolve().parents[3] / "src/ethos/adapters/repo/hook_runtime.py"
    text = owner.read_text(encoding="utf-8")

    assert "def _candidate_python(" in text
    assert "binding = hook_runtime_binding(candidate)" in text
    assert 'if binding["required_gaps"]:' in text
    assert '"-I",' in text
    assert '"ethos.cli",' in text
    assert '"ref-transaction",' in text


def test_reference_transaction_reads_only_git_common_lease_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A prepared ref decision reads Lease state without walking runtime generations."""
    repo = init_git_repo(tmp_path / "repo")
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir(parents=True)
    workspace.write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        ),
        encoding="utf-8",
    )
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "declare branch roles")
    git(repo, "branch", "work/x")
    database = state_database(repo)
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.commit()
    old = git(repo, "rev-parse", "work/x")
    new = git(repo, "commit-tree", git(repo, "rev-parse", "HEAD^{tree}"), "-p", old, "-m", "next")
    status = execute_hook(
        repo,
        "reference-transaction",
        ("prepared",),
        stdin=io.StringIO(f"{old} {new} refs/heads/work/x\n"),
    )

    assert status == 1
    assert "work_lane_missing_lease:work/x" in capsys.readouterr().err
