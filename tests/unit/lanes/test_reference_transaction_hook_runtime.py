"""Installed reference-transaction runtime and fail-closed integration."""

from __future__ import annotations

import io
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from typing import TYPE_CHECKING

from ethos.adapters.admission.lease_binding import resolve_current_authority
from ethos.adapters.repo.hook_runtime import execute_hook
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.worktree_effects import restore_rejected_checkout_projection
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from tests.support.governed_repository import commit_active_commitment
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import render_branch_policy

if TYPE_CHECKING:
    from pathlib import Path

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


def test_rejected_accepted_merge_preserves_head_index_and_worktree(tmp_path: Path) -> None:
    """A rejected raw merge must not pollute the accepted checkout."""
    g, hooks, no_binary = _unavailable_runtime_repo(tmp_path)
    driver = hooks / "reference_transaction_driver.py"
    driver.write_text(
        """from pathlib import Path
import sys

import ethos.adapters.repo.hook_runtime as runtime

runtime.current_runtime = lambda _common: object()
raise SystemExit(
    runtime.execute_hook(
        Path.cwd(),
        "reference-transaction",
        tuple(sys.argv[1:]),
        stdin=sys.stdin,
    )
)
""",
        encoding="utf-8",
    )
    hook = hooks / "reference-transaction"
    hook.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{driver}" "$@"\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    g("config", "core.hooksPath", "")
    assert g("checkout", "work/x").returncode == 0
    (tmp_path / "a").write_text("2", encoding="utf-8")
    (tmp_path / "work-only").write_text("work\n", encoding="utf-8")
    assert g("add", ".").returncode == 0
    assert g("commit", "-m", "work change").returncode == 0
    assert g("checkout", "dev").returncode == 0
    g("config", "core.hooksPath", hooks.as_posix())
    before = {
        "symbolic_head": g("symbolic-ref", "-q", "HEAD").stdout,
        "head": g("rev-parse", "HEAD").stdout,
        "index_tree": g("write-tree").stdout,
        "status": g("status", "--porcelain=v1", "-z").stdout,
        "tracked": (tmp_path / "a").read_bytes(),
        "work_only": (tmp_path / "work-only").exists(),
    }

    blocked = g("merge", "--ff-only", "work/x", env=no_binary)

    assert blocked.returncode != 0
    assert {
        "symbolic_head": g("symbolic-ref", "-q", "HEAD").stdout,
        "head": g("rev-parse", "HEAD").stdout,
        "index_tree": g("write-tree").stdout,
        "status": g("status", "--porcelain=v1", "-z").stdout,
        "tracked": (tmp_path / "a").read_bytes(),
        "work_only": (tmp_path / "work-only").exists(),
    } == before


def test_rejected_work_lane_creation_preserves_head_index_and_worktree(tmp_path: Path) -> None:
    """A rejected raw work-branch checkout must restore the source checkout."""
    g, hooks, no_binary = _unavailable_runtime_repo(tmp_path)
    driver = hooks / "reference_transaction_driver.py"
    driver.write_text(
        """from pathlib import Path
import sys

import ethos.adapters.repo.hook_runtime as runtime

runtime.current_runtime = lambda _common: object()
raise SystemExit(
    runtime.execute_hook(
        Path.cwd(),
        "reference-transaction",
        tuple(sys.argv[1:]),
        stdin=sys.stdin,
    )
)
""",
        encoding="utf-8",
    )
    hook = hooks / "reference-transaction"
    hook.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{driver}" "$@"\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    g("config", "core.hooksPath", "")
    assert g("checkout", "work/x").returncode == 0
    (tmp_path / "a").write_text("2", encoding="utf-8")
    (tmp_path / "work-only").write_text("work\n", encoding="utf-8")
    assert g("add", ".").returncode == 0
    assert g("commit", "-m", "work change").returncode == 0
    target = g("rev-parse", "HEAD").stdout.strip()
    assert g("checkout", "dev").returncode == 0
    g("config", "core.hooksPath", hooks.as_posix())
    before = {
        "symbolic_head": g("symbolic-ref", "-q", "HEAD").stdout,
        "head": g("rev-parse", "HEAD").stdout,
        "index_tree": g("write-tree").stdout,
        "status": g("status", "--porcelain=v1", "-z").stdout,
        "tracked": (tmp_path / "a").read_bytes(),
        "work_only": (tmp_path / "work-only").exists(),
    }

    blocked = g("checkout", "-b", "work/unleased", target, env=no_binary)

    assert blocked.returncode != 0
    assert g("show-ref", "--verify", "refs/heads/work/unleased").returncode != 0
    assert {
        "symbolic_head": g("symbolic-ref", "-q", "HEAD").stdout,
        "head": g("rev-parse", "HEAD").stdout,
        "index_tree": g("write-tree").stdout,
        "status": g("status", "--porcelain=v1", "-z").stdout,
        "tracked": (tmp_path / "a").read_bytes(),
        "work_only": (tmp_path / "work-only").exists(),
    } == before


def test_checkout_compensation_refuses_non_exact_index_overlay(tmp_path: Path) -> None:
    """Compensation never guesses how to reconstruct a pre-existing staged overlay."""
    g, _hooks, _no_binary = _unavailable_runtime_repo(tmp_path)
    g("config", "core.hooksPath", "")
    assert g("checkout", "work/x").returncode == 0
    (tmp_path / "a").write_text("2", encoding="utf-8")
    assert g("add", "a").returncode == 0
    assert g("commit", "-m", "work change").returncode == 0
    target = g("rev-parse", "HEAD").stdout.strip()
    assert g("checkout", "dev").returncode == 0
    (tmp_path / "staged-overlay").write_text("owned by caller\n", encoding="utf-8")
    assert g("add", "staged-overlay").returncode == 0
    before = {
        "index_tree": g("write-tree").stdout,
        "status": g("status", "--porcelain=v1", "-z").stdout,
    }

    assert not restore_rejected_checkout_projection(tmp_path, target_head=target)
    assert {
        "index_tree": g("write-tree").stdout,
        "status": g("status", "--porcelain=v1", "-z").stdout,
    } == before


def test_owned_lane_commit_keeps_lease_generation_and_reads_fresh_head(
    tmp_path: Path,
) -> None:
    """Ordinary commits never use an unabortable hook to rewrite Lease authority."""
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    lane = tmp_path / "lane"
    branch = "work/current"
    holder = "agent:test:case:fresh-lane-head"
    git(repo, "worktree", "add", "-b", branch, lane.as_posix(), "dev")
    start = git(lane, "rev-parse", "HEAD")
    acquire_lease(
        state_database(repo),
        lease=exact_lease(
            repo=repo,
            branch=branch,
            holder_ref=holder,
            expected_head=start,
            carrier="openspec/changes/fixture-change/commitment.toml",
        ),
    )
    hooks = repo / ".git/test-hooks"
    hooks.mkdir(exist_ok=True)
    driver = hooks / "reference_transaction_driver.py"
    driver.write_text(
        """from pathlib import Path
import sys

import ethos.adapters.repo.hook_runtime as runtime

runtime.current_runtime = lambda _common: object()
raise SystemExit(
    runtime.execute_hook(
        Path.cwd(),
        "reference-transaction",
        tuple(sys.argv[1:]),
        stdin=sys.stdin,
    )
)
""",
        encoding="utf-8",
    )
    hook = hooks / "reference-transaction"
    hook.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{driver}" "$@"\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    git(lane, "config", "core.hooksPath", hooks.as_posix())
    before = leases_by_branch(lane)[branch]
    (lane / "ordinary.txt").write_text("ordinary\n", encoding="utf-8")
    git(lane, "add", "ordinary.txt")

    committed = subprocess.run(
        ["git", "commit", "-m", "ordinary source change"],
        cwd=lane,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "ETHOS_ACTOR": holder},
    )

    assert committed.returncode == 0, committed.stderr
    head = git(lane, "rev-parse", "HEAD")
    assert head != start
    after = leases_by_branch(lane)[branch]
    assert after["payload_sha256"] == before["payload_sha256"]
    authority = resolve_current_authority(
        root=lane,
        branch=branch,
        lease=after,
        actor=holder,
        current_head=head,
    )
    assert authority.verdict == "pass"
    assert authority.current_head == head


def test_reference_transaction_hook_fails_closed_on_empty_release_mirror_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
            release_mirror="accepted_ff",
        ),
        encoding="utf-8",
    )
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "declare accepted release mirror")
    candidate = tmp_path / "candidate"
    git(repo, "branch", "main")
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    (candidate / "change").write_text("candidate\n", encoding="utf-8")
    git(candidate, "add", "change")
    git(candidate, "commit", "-m", "candidate")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    monkeypatch.setattr(
        "ethos.adapters.repo.hook_runtime.current_runtime",
        lambda _common: object(),
    )
    monkeypatch.setattr(
        "ethos.adapters.repo.hook_runtime._candidate_python",
        lambda *_args, **_kwargs: tmp_path / "python",
    )
    monkeypatch.setattr(
        "ethos.adapters.repo.hook_runtime.run_command",
        lambda *_args, **_kwargs: subprocess.CompletedProcess((), 0, "", ""),
    )
    status = execute_hook(
        repo,
        "reference-transaction",
        ("prepared",),
        stdin=io.StringIO(f"{git(repo, 'rev-parse', 'main')} {candidate_head} refs/heads/main\n"),
    )

    assert status == 1
    assert "candidate_semantic_runner_invalid" in capsys.readouterr().err


def test_reference_transaction_reads_only_git_common_lease_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setattr(
        "ethos.adapters.repo.hook_runtime.current_runtime",
        lambda _common: None,
    )
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
