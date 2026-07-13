from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.store.state.lease.lifecycle.core as state
from ethos.adapters.admission import identity as admission_identity
from ethos.adapters.admission import prewrite as admission_prewrite
from ethos.adapters.admission.core import hook_admission_report
from ethos.adapters.admission.core import push_admission_report
from ethos.adapters.admission.identity import push_identity_policy_report
from ethos.adapters.mutation.core import proof_gaps
from ethos.adapters.mutation.proof import _promotion_required_gate_ids
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.mutation.proof import proof_state_dir
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from tests.support.contract_helpers import conformant_proof_run
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def test_cast_worktrees_treats_non_list_status_payload_as_empty() -> None:
    assert admission_prewrite.cast_worktrees(None) == []
    assert admission_prewrite.cast_worktrees({"branch": "work/x"}) == []


def test_cast_worktrees_normalizes_dict_items_and_skips_noise() -> None:
    assert admission_prewrite.cast_worktrees([{"branch": "work/x", "head": 1}, "noise"]) == [
        {"branch": "work/x", "head": "1"}
    ]


@pytest.fixture
def leased_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        holder_ref="agent:test:case:agent-a",
        payload={
            "path": worktree.as_posix(),
            "branch": "work/feature",
            "expected_head": git(worktree, "rev-parse", "HEAD"),
        },
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    return worktree


def test_context_hook_rejects_stale_target_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    other = init_repo(tmp_path / "other")

    report = hook_admission_report(
        root=repo,
        layer="context",
        expected_root=other,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["decision"] == {
        "action": "block",
        "reason": "hook_context_root_mismatch",
    }
    assert report["target_root"] == repo.resolve().as_posix()
    assert report["expected_root"] == other.resolve().as_posix()
    assert "hook_context_root_mismatch" in report["required_gaps"]


def test_pre_tool_hook_blocks_protected_root_before_mutation(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = hook_admission_report(
        root=repo,
        layer="pre-tool",
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["decision"] == {
        "action": "block",
        "reason": "protected_lane_prewrite_blocked",
    }
    assert report["admission"]["error"] == "protected_lane_prewrite_blocked"
    assert "protected_lane_prewrite_blocked" in report["required_gaps"]


def test_pre_tool_hook_blocks_protected_root_write_tool_without_declared_paths(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")

    report = hook_admission_report(
        root=repo,
        layer="pre-tool",
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["decision"] == {
        "action": "block",
        "reason": "protected_root_pretool_paths_required",
    }
    assert "protected_root_pretool_paths_required" in report["required_gaps"]


def test_pre_tool_hook_blocks_raw_work_lane_without_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")

    report = hook_admission_report(
        root=worktree,
        layer="pre-tool",
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "work_lane"
    assert report["decision"] == {
        "action": "block",
        "reason": "work_lane_missing_lease:work/feature",
    }
    assert report["admission"]["work_lane_lease"]["ok"] is False
    assert "work_lane_missing_lease:work/feature" in report["required_gaps"]


@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        ("agent:test:case:agent-a", ("admitted", "allow", "matched")),
        (
            "agent:test:case:agent-b",
            ("blocked", "block", "lease_holder_mismatch:work/feature"),
        ),
    ],
    ids=["matching-actor", "actor-mismatch"],
)
def test_pre_tool_hook_evaluates_leased_work_lane_actor(
    leased_worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
    actor: str,
    expected: tuple[str, str, str],
) -> None:
    expected_state, expected_action, expected_lease_reason = expected
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    report = hook_admission_report(
        root=leased_worktree,
        layer="pre-tool",
        paths=[leased_worktree / "README.md"],
        editor_root=leased_worktree,
        require_editor_root=True,
    )

    assert report["ok"] is (expected_state == "admitted")
    assert report["state"] == expected_state
    assert report["role"] == "work_lane"
    assert report["decision"] == {
        "action": expected_action,
        "reason": "prewrite_admitted" if expected_state == "admitted" else expected_lease_reason,
    }
    lease_check = report["admission"]["work_lane_lease"]
    assert report["admission"]["ok"] is (expected_state == "admitted")
    assert lease_check["ok"] is (expected_state == "admitted")
    assert lease_check["required"] is True
    assert lease_check["branch"] == "work/feature"
    assert lease_check["holder_ref"] == "agent:test:case:agent-a"
    assert lease_check["invocation_holder_ref"] == actor
    assert lease_check["lease_id"].startswith("lease:")
    assert lease_check["epoch"] == 1
    assert lease_check["expected_head"] == git(leased_worktree, "rev-parse", "HEAD")
    assert lease_check["reason"] == expected_lease_reason
    if expected_state == "blocked":
        assert report["next_actions"] == [
            "set ETHOS_ACTOR=agent:test:case:agent-a and rerun the blocked command, or obtain handoff",
            "ethos lane prewrite <path>",
        ]


def test_pre_tool_hook_admits_detached_rebase_of_owned_work_lane(
    leased_worktree: Path,
) -> None:
    branch_head = git(leased_worktree, "rev-parse", "HEAD")
    git(leased_worktree, "checkout", "--detach")
    (leased_worktree / "REBASE.md").write_text("# replay checkpoint\n", encoding="utf-8")
    git(leased_worktree, "add", "REBASE.md")
    git(
        leased_worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "replay checkpoint",
    )
    detached_head = git(leased_worktree, "rev-parse", "HEAD")
    assert detached_head != branch_head
    git_dir = Path(git(leased_worktree, "rev-parse", "--absolute-git-dir"))
    rebase_dir = git_dir / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/work/feature\n", encoding="utf-8")

    report = hook_admission_report(
        root=leased_worktree,
        layer="pre-tool",
        paths=[leased_worktree / "README.md"],
        editor_root=leased_worktree,
        require_editor_root=True,
    )

    assert report["ok"] is True
    assert report["role"] == "work_lane"
    assert report["branch"] == "work/feature"
    assert report["admission"]["status_role"] == "detached"
    assert report["admission"]["effective_context"] == {
        "role": "work_lane",
        "branch": "work/feature",
        "source": "git_rebase_head_name",
        "rebase_head_name": "work/feature",
    }
    lease_check = report["admission"]["work_lane_lease"]
    assert lease_check["current_head"] == detached_head
    assert lease_check["binding_head"] == branch_head
    assert lease_check["head_source"] == "rebase_branch_ref"


def test_git_path_falls_back_to_dot_git_when_git_path_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_rev_parse(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git"], 1, "", "not a git repo")

    monkeypatch.setattr(admission_prewrite.subprocess, "run", fail_rev_parse)

    assert admission_prewrite._git_path(tmp_path) == tmp_path / ".git"


def test_pre_tool_hook_keeps_non_work_lane_detached_rebase_protected(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "checkout", "--detach")
    git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir"))
    rebase_dir = git_dir / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/dev\n", encoding="utf-8")

    report = hook_admission_report(
        root=repo,
        layer="pre-tool",
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["role"] == "detached"
    assert report["admission"]["effective_context"] == {
        "role": "detached",
        "branch": "detached",
        "source": "workspace_status",
        "rebase_head_name": "dev",
    }
    assert report["decision"] == {
        "action": "block",
        "reason": "protected_lane_prewrite_blocked",
    }


def test_pre_run_hook_blocks_mutation_risk_without_target_paths(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = hook_admission_report(
        root=repo,
        layer="pre-run",
        command='python -c \'from pathlib import Path; Path("README.md").write_text("x")\'',
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["command_risk"] == {
        "tracked_mutation_risk": True,
        "reason": "command_text_matches_mutation_pattern",
    }
    assert report["decision"] == {
        "action": "block",
        "reason": "hook_prerun_paths_required",
    }
    assert "hook_prerun_paths_required" in report["required_gaps"]


@pytest.mark.parametrize(
    "command",
    [
        "python scripts/generate.py",
        "git apply patch.diff",
        "touch README.md",
    ],
)
def test_pre_run_hook_blocks_unknown_or_mutating_protected_root_commands_without_paths(
    tmp_path: Path,
    command: str,
) -> None:
    repo = init_repo(tmp_path / "repo")

    report = hook_admission_report(
        root=repo,
        layer="pre-run",
        command=command,
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["command_risk"]["tracked_mutation_risk"] is True
    assert report["decision"] == {
        "action": "block",
        "reason": "hook_prerun_paths_required",
    }
    assert "hook_prerun_paths_required" in report["required_gaps"]


def test_post_write_hook_fuses_protected_root_dirty_state(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")

    report = hook_admission_report(
        root=repo,
        layer="post-write",
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "fused"
    assert report["role"] == "accepted_root"
    assert report["decision"] == {
        "action": "fuse",
        "reason": "post_write_protected_root_dirty",
    }
    assert report["changed_paths"] == ["README.md"]
    assert "post_write_protected_root_dirty" in report["required_gaps"]


def test_post_write_hook_fuses_work_lane_dirty_state_without_expected_paths(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    (worktree / "README.md").write_text("# changed\n", encoding="utf-8")

    report = hook_admission_report(
        root=worktree,
        layer="post-write",
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "fused"
    assert report["role"] == "work_lane"
    assert report["decision"] == {
        "action": "fuse",
        "reason": "post_write_unexpected_path",
    }
    assert report["changed_paths"] == ["README.md"]
    assert report["unexpected_paths"] == ["README.md"]
    assert "post_write_unexpected_path" in report["required_gaps"]


def test_push_admission_blocks_unproven_push_to_protected_role(tmp_path) -> None:
    """The push tail: a push to an accepted/candidate ref requires an executed proof
    bound to the pushed HEAD (same reducer as land). Work-lane pushes are admitted."""
    subprocess.run(["git", "init", "-q", "-b", "dev"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@e.x", "commit", "-qm", "init"],
        cwd=tmp_path,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # protected accepted root without proof -> blocked
    protected = push_admission_report(root=tmp_path, target_ref="refs/heads/dev", pushed_head=head)
    assert protected["ok"] is False
    assert protected["state"] == "blocked"
    assert any("not_proven" in str(g) or "proof" in str(g) for g in protected["required_gaps"])

    # unprotected work lane -> admitted untouched
    lane = push_admission_report(
        root=tmp_path, target_ref="refs/heads/work/feature", pushed_head=head
    )
    assert lane["ok"] is True
    assert lane["state"] == "admitted"


def test_push_identity_policy_blocks_new_commits_outside_configured_user(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    remote_head = git(repo, "rev-parse", "HEAD")
    git(repo, "config", "user.name", "Canonical User")
    git(repo, "config", "user.email", "canonical@example.invalid")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Codex")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "codex@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Codex")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "codex@example.invalid")
    (repo / "bad.txt").write_text("bad\n", encoding="utf-8")
    git(repo, "add", "bad.txt")
    git(repo, "commit", "-m", "bad identity")
    pushed_head = git(repo, "rev-parse", "HEAD")

    identity = push_identity_policy_report(
        root=repo, pushed_head=pushed_head, remote_head=remote_head
    )
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/work/feature",
        pushed_head=pushed_head,
        remote_head=remote_head,
    )

    assert identity["ok"] is False
    assert identity["checked_commit_count"] == 1
    assert identity["violations"] == [
        {
            "commit": pushed_head,
            "author": "Codex <codex@example.invalid>",
            "committer": "Codex <codex@example.invalid>",
        }
    ]
    assert report["ok"] is False
    assert report["decision"] == {
        "action": "block",
        "reason": "pushed_commit_identity_not_allowed",
    }
    assert f"pushed_commit_author_not_configured_identity:{pushed_head}" in report["required_gaps"]
    assert (
        f"pushed_commit_committer_not_configured_identity:{pushed_head}" in report["required_gaps"]
    )


def test_push_identity_policy_accepts_configured_user_over_new_range(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    remote_head = git(repo, "rev-parse", "HEAD")
    git(repo, "config", "user.name", "Canonical User")
    git(repo, "config", "user.email", "canonical@example.invalid")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Canonical User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "canonical@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Canonical User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "canonical@example.invalid")
    (repo / "good.txt").write_text("good\n", encoding="utf-8")
    git(repo, "add", "good.txt")
    git(repo, "commit", "-m", "good identity")
    pushed_head = git(repo, "rev-parse", "HEAD")

    identity = push_identity_policy_report(
        root=repo, pushed_head=pushed_head, remote_head=remote_head
    )
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/work/feature",
        pushed_head=pushed_head,
        remote_head=remote_head,
    )

    assert identity["ok"] is True
    assert identity["expected_identity"] == "Canonical User <canonical@example.invalid>"
    assert identity["checked_commit_count"] == 1
    assert identity["violations"] == []
    assert report["ok"] is True


def test_push_identity_policy_reports_missing_configured_user_and_unreadable_head(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")

    report = push_identity_policy_report(root=repo, pushed_head="missing-head")

    assert report["ok"] is False
    assert "push_identity_user_name_missing" in report["required_gaps"]
    assert "push_identity_user_email_missing" in report["required_gaps"]
    assert "push_identity_commit_range_unreadable" in report["required_gaps"]


def test_push_identity_policy_reports_author_and_committer_independently(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    remote_head = git(repo, "rev-parse", "HEAD")
    git(repo, "config", "user.name", "Canonical User")
    git(repo, "config", "user.email", "canonical@example.invalid")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Other Author")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "other-author@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Canonical User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "canonical@example.invalid")
    (repo / "author.txt").write_text("author\n", encoding="utf-8")
    git(repo, "add", "author.txt")
    git(repo, "commit", "-m", "author drift")
    author_drift_head = git(repo, "rev-parse", "HEAD")

    author_drift = push_identity_policy_report(
        root=repo, pushed_head=author_drift_head, remote_head=remote_head
    )

    assert (
        f"pushed_commit_author_not_configured_identity:{author_drift_head}"
        in author_drift["required_gaps"]
    )
    assert (
        f"pushed_commit_committer_not_configured_identity:{author_drift_head}"
        not in author_drift["required_gaps"]
    )

    second_repo = init_repo(tmp_path / "second-repo")
    second_remote_head = git(second_repo, "rev-parse", "HEAD")
    git(second_repo, "config", "user.name", "Canonical User")
    git(second_repo, "config", "user.email", "canonical@example.invalid")
    git(second_repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Canonical User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "canonical@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Other Committer")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "other-committer@example.invalid")
    (second_repo / "committer.txt").write_text("committer\n", encoding="utf-8")
    git(second_repo, "add", "committer.txt")
    git(second_repo, "commit", "-m", "committer drift")
    committer_drift_head = git(second_repo, "rev-parse", "HEAD")

    committer_drift = push_identity_policy_report(
        root=second_repo,
        pushed_head=committer_drift_head,
        remote_head=second_remote_head,
    )

    assert (
        f"pushed_commit_author_not_configured_identity:{committer_drift_head}"
        not in committer_drift["required_gaps"]
    )
    assert (
        f"pushed_commit_committer_not_configured_identity:{committer_drift_head}"
        in committer_drift["required_gaps"]
    )


def test_push_identity_helpers_tolerate_git_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_range_run(args, **kwargs):
        if args[:3] == ["git", "cat-file", "-e"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:2] == ["git", "rev-list"]:
            return subprocess.CompletedProcess(args, 1, "", "fatal")
        raise AssertionError(args)

    assert admission_identity._pushed_commit_range(tmp_path, pushed_head="", remote_head="") == []

    monkeypatch.setattr(admission_identity.subprocess, "run", fake_range_run)
    assert admission_identity._pushed_commit_range(tmp_path, pushed_head="h1", remote_head="") == []

    def fake_identity_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, "malformed", "")

    monkeypatch.setattr(admission_identity.subprocess, "run", fake_identity_run)
    assert admission_identity._commit_identity(tmp_path, "h1") == {
        "author_name": "",
        "author_email": "",
        "committer_name": "",
        "committer_email": "",
    }


def _trust_bearing_evidence(head: str, root: Path | None = None) -> dict[str, object]:
    """Seed a COMPLETE, POLICY-CONFORMANT executed-proof evidence body.

    A promotion proof must cover the required land floor AND each run must conform to its
    gate's live policy identity (canonical command / trust_bearing / evidence_class).
    Generate one conformant run per required gate id for `root` (product floor when root
    is None) — the shape a real `ethos prove --execute` produces.
    """
    resolved = root if root is not None else Path()
    required = _promotion_required_gate_ids(resolved)
    runs = tuple(conformant_proof_run(gate_id, resolved) for gate_id in required)
    return EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict()


def test_proof_state_dir_defaults_to_repository_local_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ETHOS_TEST_PROOF_STATE_DIR", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

    assert proof_state_dir(tmp_path) == tmp_path / ".ethos" / "state" / "proof"


def test_proof_state_dir_test_override_is_worker_local(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    head = "abc123"
    proof_dir = tmp_path / ".ethos" / "state" / "proof-gw1"
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw1")
    monkeypatch.setenv("ETHOS_TEST_PROOF_STATE_DIR", proof_dir.as_posix())

    path = record_executed_proof(tmp_path, _trust_bearing_evidence(head, tmp_path))

    assert path == proof_dir / f"{head}.json"
    assert executed_proof_record(tmp_path, head) is not None
    assert not (tmp_path / ".ethos" / "state" / "proof" / f"{head}.json").exists()


def test_executed_proof_record_rejects_forgery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The proof record is tamper-evident: a hand-authored file that did not come from
    an executed proof is rejected, so the write-admission moat cannot be minted with
    `echo`. Only a record whose digest recomputes from its own sealed evidence body,
    with every run proven, is accepted."""
    monkeypatch.delenv("ETHOS_TEST_PROOF_STATE_DIR", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    head = "a" * 40
    proof_dir = tmp_path / ".ethos" / "state" / "proof"
    proof_dir.mkdir(parents=True)

    # bare forgery — no evidence body
    (proof_dir / f"{head}.json").write_text(
        json.dumps({"head": head, "state": "proven", "evidence_digest": "x"}),
        encoding="utf-8",
    )
    assert executed_proof_record(tmp_path, head) is None
    assert "proof_not_proven" in proof_gaps(tmp_path, head)

    # Non-proven local state never admits a proof even if the file is present.
    (proof_dir / f"{head}.json").write_text(
        json.dumps({"head": head, "state": "pending", "evidence_digest": "x"}),
        encoding="utf-8",
    )
    assert executed_proof_record(tmp_path, head) is None

    # forgery with a fabricated failing run + wrong digest
    (proof_dir / f"{head}.json").write_text(
        json.dumps(
            {
                "head": head,
                "state": "proven",
                "evidence_digest": "z",
                "evidence": {
                    "id": "p",
                    "head": head,
                    "durability": "local",
                    "runs": [{"verdict": "failed"}],
                    "digest": "z",
                },
            }
        ),
        encoding="utf-8",
    )
    assert executed_proof_record(tmp_path, head) is None

    # Non-trust-bearing executed/proven-looking records are rejected: a diagnostic pass
    # without any trust-bearing proven gate cannot promote a HEAD.
    non_trust_run = ProofRun(
        action_id="ruff",
        command=("ruff", "check", "."),
        exit_code=0,
        stdout="",
        stderr="",
        state="executed",
        evidence_class="diagnostic",
        verdict="passed",
        trust_bearing=False,
        diagnostics=(),
    )
    non_trust_evidence = EvidenceSet.from_runs(
        id="proof", head=head, runs=(non_trust_run,)
    ).to_dict()
    record_executed_proof(tmp_path, non_trust_evidence)
    assert executed_proof_record(tmp_path, head) is None

    # Real CLI proof records may combine non-trust diagnostic passes with
    # trust-bearing proven gates. Lock that shape so land accepts valid executed proof
    # without confusing state with verdict. `executed_proof_record` is integrity-only,
    # so a mixed non-trust + trust shape verifies as a valid record.
    trust_run = ProofRun(
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
    evidence = EvidenceSet.from_runs(
        id="proof", head=head, runs=(non_trust_run, trust_run)
    ).to_dict()
    record_executed_proof(tmp_path, evidence)
    assert executed_proof_record(tmp_path, head) is not None
    # This mixed proof is a valid record but does NOT cover the required land floor,
    # so proof_gaps reports incomplete (completeness is a promotion-gate concern,
    # separate from record integrity). A complete proof clears it.
    assert any(g.startswith("proof_incomplete") for g in proof_gaps(tmp_path, head))
    record_executed_proof(tmp_path, _trust_bearing_evidence(head, tmp_path))
    assert proof_gaps(tmp_path, head) == []


def test_promotion_completeness_helper_edges(tmp_path: Path) -> None:
    """Cover the two defensive branches of the completeness helpers:
    non-list runs -> not covered; no record present -> no completeness gaps
    (the caller's proof_not_proven path owns absence)."""
    from ethos.adapters.mutation.proof import _runs_cover_required_set
    from ethos.adapters.mutation.proof import promotion_completeness_gaps

    # 131: non-list runs are never a covering set.
    assert _runs_cover_required_set("not-a-list", ("g",)) is False
    # 148: no proof record at head -> completeness reports nothing (absence is the
    # caller's proof_not_proven concern, not incompleteness).
    assert promotion_completeness_gaps(tmp_path, "f" * 40) == []
