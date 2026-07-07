# ruff: noqa: TC002, TC003
"""Coverage-closure v2: mutation and repo adapters (100% no-exemption campaign).

Exercises defensive branches with no prior coverage: proof-record verification
rejections, proof-carry failure paths, and git plumbing fallbacks.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ethos.adapters.mutation import proof as mutation_proof
from ethos.adapters.repo import git


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@e.co", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )


# --- mutation/proof.py -------------------------------------------------------


def test_runs_prove_head_rejects_unpassed_run() -> None:
    # A run whose verdict is not "passed" fails the head-proof check (line 52).
    assert mutation_proof._runs_prove_head([{"verdict": "failed"}]) is False


def test_runs_prove_head_rejects_trust_bearing_not_proven() -> None:
    # A passed trust-bearing run that is not in state "proven" is rejected (line 56).
    runs = [{"verdict": "passed", "trust_bearing": True, "state": "executed"}]
    assert mutation_proof._runs_prove_head(runs) is False


def test_executed_proof_record_rejects_non_proven_state(tmp_path: Path) -> None:
    # A record on disk whose state is not "proven" is treated as absent (line 97).
    proof_dir = tmp_path / ".ethos" / "state" / "proof"
    proof_dir.mkdir(parents=True)
    (proof_dir / "H.json").write_text(
        json.dumps({"state": "executed", "head": "H"}), encoding="utf-8"
    )
    assert mutation_proof.executed_proof_record(tmp_path, "H") is None


def test_carry_executed_proof_record_fails_on_copy_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A verified source record whose copy raises OSError yields a failed carry
    # (lines 161-162).
    head = "abc123"
    evidence = _proven_evidence(head)
    source = tmp_path / "src"
    mutation_proof.record_executed_proof(source, evidence)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(mutation_proof.shutil, "copyfile", _boom)
    result = mutation_proof.carry_executed_proof_record(
        source_root=source, target_root=tmp_path / "dst", head=head
    )
    assert result["ok"] is False
    assert result["state"] == "failed"
    assert result["reason"] == "OSError"


def test_carry_executed_proof_record_fails_when_target_invalid_after_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # If the target record fails re-verification after copy, the carry fails (line 170).
    head = "def456"
    evidence = _proven_evidence(head)
    source = tmp_path / "src"
    mutation_proof.record_executed_proof(source, evidence)

    calls = {"n": 0}
    real = mutation_proof.executed_proof_record

    def _second_none(root: Path, h: str) -> object:
        calls["n"] += 1
        # First call (source verification) is real; second (target re-check) is None.
        return real(root, h) if calls["n"] == 1 else None

    monkeypatch.setattr(mutation_proof, "executed_proof_record", _second_none)
    result = mutation_proof.carry_executed_proof_record(
        source_root=source, target_root=tmp_path / "dst", head=head
    )
    assert result["ok"] is False
    assert result["reason"] == "target-proof-invalid-after-copy"


def _proven_evidence(head: str) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "evidence",
        "head": head,
        "durability": "local",
        "runs": [{"verdict": "passed", "trust_bearing": True, "state": "proven"}],
    }
    body["digest"] = mutation_proof._evidence_digest(body)
    return body


# --- adapters/repo/git.py ----------------------------------------------------


def test_git_common_dir_empty_outside_repo(tmp_path: Path) -> None:
    # A non-git directory yields an empty common dir (line 77).
    assert git.git_common_dir(tmp_path) == ""


def test_git_files_lists_tracked_files(tmp_path: Path) -> None:
    # A real repo returns its tracked files, filtering blank lines (line 103).
    _git(tmp_path, "init", "-b", "main")
    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "c1")
    assert git.git_files(tmp_path, "a.txt") == ["a.txt"]


def test_git_files_empty_outside_repo(tmp_path: Path) -> None:
    # ls-files fails outside a repo, returning [] (line 101-102 already covered; this
    # guards the non-zero returncode path).
    assert git.git_files(tmp_path) == []


def test_commits_equivalent_over_paths_empty_head(tmp_path: Path) -> None:
    # An empty head short-circuits to an empty tuple (line 124).
    assert git.commits_equivalent_over_paths(tmp_path, "", relevant_paths=("packages",)) == ()


def test_remote_availability_unconfigured(tmp_path: Path) -> None:
    # A repo with no such remote reports unconfigured (lines 148-157).
    _git(tmp_path, "init", "-b", "main")
    result = git.remote_availability(tmp_path, "origin")
    assert result["state"] == "unconfigured"
    assert result["available"] is False


def test_remote_availability_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A configured remote whose probe times out reports the timeout branch
    # (lines 167-168). Patch only the ls-remote probe; other git calls run normally.
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "remote", "add", "origin", "ssh://unreachable.example/repo.git")

    real_run = subprocess.run

    def _maybe_timeout(cmd: list[str], *args: object, **kwargs: object) -> object:
        if "ls-remote" in cmd:
            raise subprocess.TimeoutExpired(cmd="git", timeout=3.0)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(git.subprocess, "run", _maybe_timeout)
    result = git.remote_availability(tmp_path, "origin", timeout_seconds=0.1)
    assert result["available"] is False


def test_current_head_untracked_when_root_missing(tmp_path: Path) -> None:
    # A nonexistent cwd raises FileNotFoundError from subprocess; current_head must
    # treat it as untracked rather than propagating the exception.
    missing = tmp_path / "does-not-exist"
    assert git.current_head(missing) == "untracked"
    assert git.current_tracked_head(missing) == ""


def test_git_stdout_empty_when_root_missing(tmp_path: Path) -> None:
    # Same missing-cwd guard for the generic stdout helper.
    missing = tmp_path / "gone"
    assert git.git_stdout(missing, "rev-parse", "HEAD") == ""
