from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.admission.core import hook_admission_report

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


def init_repo(path: Path) -> Path:
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


def test_pre_tool_hook_admits_owned_work_lane_with_editor_root(tmp_path: Path) -> None:
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

    assert report["ok"] is True
    assert report["state"] == "admitted"
    assert report["role"] == "work_lane"
    assert report["decision"] == {
        "action": "allow",
        "reason": "prewrite_admitted",
    }
    assert report["admission"]["ok"] is True


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
    import subprocess

    from ethos.adapters.admission.core import push_admission_report

    subprocess.run(["git", "init", "-q", "-b", "dev"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@e.x", "commit", "-qm", "init"],
        cwd=tmp_path,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
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


def test_executed_proof_record_rejects_forgery(tmp_path) -> None:
    """The proof record is tamper-evident: a hand-authored file that did not come from
    an executed proof is rejected, so the write-admission moat cannot be minted with
    `echo`. Only a record whose digest recomputes from its own sealed evidence body,
    with every run proven, is accepted."""
    import json

    from ethos.adapters.mutation.core import _proof_gaps
    from ethos.adapters.mutation.proof import executed_proof_record
    from ethos.adapters.mutation.proof import record_executed_proof
    from ethos.repository.evidence.core import EvidenceSet
    from ethos.repository.evidence.core import ProofRun

    head = "a" * 40
    proof_dir = tmp_path / ".ethos" / "state" / "proof"
    proof_dir.mkdir(parents=True)

    # bare forgery — no evidence body
    (proof_dir / f"{head}.json").write_text(
        json.dumps({"head": head, "state": "proven", "evidence_digest": "x"}), encoding="utf-8"
    )
    assert executed_proof_record(tmp_path, head) is None
    assert "proof_not_proven" in _proof_gaps(tmp_path, head)

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
    # without confusing state with verdict.
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
    assert _proof_gaps(tmp_path, head) == []
