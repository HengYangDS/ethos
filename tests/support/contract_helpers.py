"""Shared fixtures for the CLI contract test suites.

The contract coverage lives across sibling `test_contracts*.py` modules split by
command family; these helpers (git plumbing, sample-repo scaffolding, adopt/proof
seeding) are the cross-cutting setup every split imports.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.repository.adoption.planner import adoption_plan

if TYPE_CHECKING:
    from pathlib import Path


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def adopt_and_commit(repo: Path) -> None:
    plan = adoption_plan(repo, profile="generic", apply=True)
    assert plan["applied"] is True
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "adopt ethos governance",
    )


def seed_executed_proof(repo: Path, head: str) -> None:
    """Record an executed-proof at HEAD, as `ethos prove --execute` would.

    Land/publish now require a HEAD-keyed proof record before the merge, so tests
    exercising land mechanics seed the proof the same way the prove command does. The
    record is self-authenticating (digest recomputed on read), so this seeds a REAL
    evidence body — a proof cannot be faked, in tests or production.
    """
    from ethos.adapters.mutation.proof import record_executed_proof
    from ethos.repository.evidence.core import EvidenceSet
    from ethos.repository.evidence.core import ProofRun

    run = ProofRun(
        action_id="python-tests",
        command=("pytest",),
        exit_code=0,
        stdout="",
        stderr="",
        state="proven",
        evidence_class="test",
        verdict="passed",
        trust_bearing=True,
        diagnostics=(),
    )
    record_executed_proof(repo, EvidenceSet.from_runs(id="proof", head=head, runs=(run,)).to_dict())
