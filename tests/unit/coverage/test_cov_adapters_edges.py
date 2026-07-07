# ruff: noqa: TC002, TC003
"""Coverage-closure edge tests for the adapters cluster (100% no-exemption campaign)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ethos.adapters.gates import signature
from ethos.adapters.repo import status_bindings
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import BranchRolePolicy


def _patch_signature(
    monkeypatch: pytest.MonkeyPatch,
    *,
    policy: dict[str, object],
    git: dict[tuple[str, ...], str],
) -> None:
    monkeypatch.setattr(signature, "load_commit_policy", lambda _root: policy)
    monkeypatch.setattr(signature, "_git", lambda _root, *args: git[args])


_SIGNED_GIT = {
    ("config", "--get", "commit.gpgsign"): "true",
    ("config", "--get", "gpg.format"): "ssh",
    ("config", "--get", "user.signingkey"): "SHA256:AAAA",
    ("log", "-1", "--pretty=%s"): "feat: ok",
    ("log", "-1", "--pretty=%G?"): "G",
}


def test_signature_policy_flags_user_name_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    # A configured expected_name that differs from git user.name raises a mismatch.
    policy = {
        "expected_name": "Ada Lovelace",
        "expected_email": "ada@example.com",
        "subject_pattern": ".+",
        "signing_required": False,
        "signing_format": "",
    }
    git = {
        ("config", "--get", "user.name"): "Someone Else",
        ("config", "--get", "user.email"): "ada@example.com",
        **_SIGNED_GIT,
    }
    _patch_signature(monkeypatch, policy=policy, git=git)
    assert signature.signature_policy_report()["required_gaps"] == ["git_user_name_mismatch"]


def test_signature_policy_flags_user_email_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = {
        "expected_name": "Ada Lovelace",
        "expected_email": "ada@example.com",
        "subject_pattern": ".+",
        "signing_required": False,
        "signing_format": "",
    }
    git = {
        ("config", "--get", "user.name"): "Ada Lovelace",
        ("config", "--get", "user.email"): "nope@example.com",
        **_SIGNED_GIT,
    }
    _patch_signature(monkeypatch, policy=policy, git=git)
    assert signature.signature_policy_report()["required_gaps"] == ["git_user_email_mismatch"]


def test_signature_policy_flags_missing_identity_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # With no configured identity, an EMPTY git identity self-fails on presence only.
    policy = {
        "expected_name": "",
        "expected_email": "",
        "subject_pattern": ".+",
        "signing_required": False,
        "signing_format": "",
    }
    git = {
        ("config", "--get", "user.name"): "",
        ("config", "--get", "user.email"): "",
        **_SIGNED_GIT,
    }
    _patch_signature(monkeypatch, policy=policy, git=git)
    assert signature.signature_policy_report()["required_gaps"] == [
        "git_user_name_missing",
        "git_user_email_missing",
    ]


def test_signature_policy_flags_signing_gaps_when_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # signing_required with a configured ssh format: disabled signing, wrong format,
    # and a missing key all surface together.
    policy = {
        "expected_name": "",
        "expected_email": "",
        "subject_pattern": ".+",
        "signing_required": True,
        "signing_format": "ssh",
    }
    git = {
        ("config", "--get", "user.name"): "Ada",
        ("config", "--get", "user.email"): "ada@example.com",
        ("config", "--get", "commit.gpgsign"): "false",
        ("config", "--get", "gpg.format"): "openpgp",
        ("config", "--get", "user.signingkey"): "",
        ("log", "-1", "--pretty=%s"): "feat: ok",
        ("log", "-1", "--pretty=%G?"): "G",
    }
    _patch_signature(monkeypatch, policy=policy, git=git)
    assert signature.signature_policy_report()["required_gaps"] == [
        "commit_signing_disabled",
        "commit_signing_format_mismatch",
        "commit_signing_key_missing",
    ]


def test_signature_policy_clean_when_signing_not_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # signing_required False: unsigned commits raise no gap (the signing block is skipped).
    policy = {
        "expected_name": "",
        "expected_email": "",
        "subject_pattern": ".+",
        "signing_required": False,
        "signing_format": "",
    }
    git = {
        ("config", "--get", "user.name"): "Ada",
        ("config", "--get", "user.email"): "ada@example.com",
        ("config", "--get", "commit.gpgsign"): "false",
        ("config", "--get", "gpg.format"): "",
        ("config", "--get", "user.signingkey"): "",
        ("log", "-1", "--pretty=%s"): "anything at all",
        ("log", "-1", "--pretty=%G?"): "N",
    }
    _patch_signature(monkeypatch, policy=policy, git=git)
    report = signature.signature_policy_report()
    assert report["required_gaps"] == []
    assert report["ok"] is True


def test_has_changed_paths_returns_true_when_git_status_fails(tmp_path: Path) -> None:
    # tmp_path is not a git repo, so `git status` exits non-zero and _run_git
    # (check=True) raises CalledProcessError -> the except returns True (lines 27-28).
    assert status_bindings._has_changed_paths(tmp_path) is True


def test_branch_bindings_skips_duplicate_protected_branch(tmp_path: Path) -> None:
    # release_branch == accepted_branch: the protected-branch loop meets "main" a
    # second time and hits `if branch in seen: continue` (line 54), emitting it once.
    policy = BranchRolePolicy(release_branch="main", accepted_branch="main")
    candidate: dict[str, object] = {
        "branch": "candidate/dev",
        "head": "",
        "worktree_path": "",
        "worktree_binding": "absent",
    }
    bindings = status_bindings._branch_bindings(
        tmp_path, [], candidate, policy=policy, lease_by_branch={}
    )
    branches = [b["branch"] for b in bindings]
    assert branches.count("main") == 1
    assert "candidate/dev" in branches
    assert len(bindings) == 2


def test_branch_bindings_dedups_duplicate_worktree_branch(tmp_path: Path) -> None:
    # Two worktree rows carry the same work-lane branch. The sorted `remaining` loop
    # appends it once, then the duplicate hits `if branch in seen: continue` (line 90).
    policy = BranchRolePolicy()
    candidate: dict[str, object] = {
        "branch": "candidate/dev",
        "head": "",
        "worktree_path": "",
        "worktree_binding": "absent",
    }
    worktree: dict[str, str] = {
        "branch": "work/foo",
        "role": ROLE_WORK_LANE,
        "head": "0" * 40,
        "path": str(tmp_path / "wt"),
        "worktree_binding": "linked",
    }
    bindings = status_bindings._branch_bindings(
        tmp_path,
        [dict(worktree), dict(worktree)],
        candidate,
        policy=policy,
        lease_by_branch={},
    )
    assert [b["branch"] for b in bindings].count("work/foo") == 1


def test_ref_relation_descendant_of_accepted(tmp_path: Path) -> None:
    # work/ahead == accepted "dev" plus one commit: dev is-ancestor-of branch but not
    # vice-versa, so line 141's check is True -> "descendant_of_accepted" (line 142).
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=T", "-c", "user.email=t@e.co", *args],
            cwd=repo,
            check=True,
            text=True,
            capture_output=True,
        )

    run("init", "-b", "dev")
    (repo / "a.txt").write_text("1", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c1")
    run("checkout", "-b", "work/ahead")
    (repo / "b.txt").write_text("2", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c2")
    run("checkout", "dev")

    assert status_bindings._ref_relation(repo, "work/ahead", "dev") == "descendant_of_accepted"


def test_ref_relation_diverged_from_accepted(tmp_path: Path) -> None:
    # work/div and dev each hold a commit the other lacks: neither _is_ancestor call
    # (lines 139, 141) is True, so the function falls through to line 143.
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=T", "-c", "user.email=t@e.co", *args],
            cwd=repo,
            check=True,
            text=True,
            capture_output=True,
        )

    run("init", "-b", "dev")
    (repo / "a.txt").write_text("1", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c1")
    run("checkout", "-b", "work/div")
    (repo / "c.txt").write_text("3", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c3")
    run("checkout", "dev")
    (repo / "d.txt").write_text("4", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c4")

    assert status_bindings._ref_relation(repo, "work/div", "dev") == "diverged_from_accepted"


def test_unbound_ref_next_action_descendant_of_accepted(tmp_path: Path) -> None:
    # descendant relation -> line 150 True -> line 151 message.
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=T", "-c", "user.email=t@e.co", *args],
            cwd=repo,
            check=True,
            text=True,
            capture_output=True,
        )

    run("init", "-b", "dev")
    (repo / "a.txt").write_text("1", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c1")
    run("checkout", "-b", "work/ahead")
    (repo / "b.txt").write_text("2", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c2")
    run("checkout", "dev")

    assert (
        status_bindings._unbound_ref_next_action(repo, "work/ahead", "dev")
        == "bind a lease or land the unbound Work Lane ref before cleanup"
    )


def test_unbound_ref_next_action_diverged_from_accepted(tmp_path: Path) -> None:
    # diverged relation -> neither the ancestor (line 148) nor descendant (line 150)
    # branch matches, so the function returns the diverged message (line 152).
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=T", "-c", "user.email=t@e.co", *args],
            cwd=repo,
            check=True,
            text=True,
            capture_output=True,
        )

    run("init", "-b", "dev")
    (repo / "a.txt").write_text("1", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c1")
    run("checkout", "-b", "work/div")
    (repo / "c.txt").write_text("3", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c3")
    run("checkout", "dev")
    (repo / "d.txt").write_text("4", encoding="utf-8")
    run("add", ".")
    run("commit", "-m", "c4")

    assert (
        status_bindings._unbound_ref_next_action(repo, "work/div", "dev")
        == "inspect diverged unbound Work Lane ref before merge, supersede, or deletion"
    )
