from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos.adapters.admission import prewrite as admission_prewrite
from ethos.adapters.admission.core import hook_admission_report
from ethos.adapters.admission.core import push_admission_report
from ethos.adapters.admission.core import ref_move_admission_report
from ethos.adapters.mutation import core
from ethos.adapters.mutation.core import proof_gaps
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.mutation.proof import proof_state_dir
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.adapters.store import state
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun


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


def test_pre_tool_hook_blocks_work_lane_actor_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-b")

    report = hook_admission_report(
        root=worktree,
        layer="pre-tool",
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["decision"] == {
        "action": "block",
        "reason": "work_lane_actor_mismatch:work/feature",
    }
    assert report["admission"]["work_lane_lease"] == {
        "ok": False,
        "required": True,
        "branch": "work/feature",
        "owner": "agent-a",
        "actor": "agent-b",
        "reason": "work_lane_actor_mismatch:work/feature",
    }


def test_pre_tool_hook_admits_leased_work_lane_for_matching_actor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")

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
    assert report["admission"]["work_lane_lease"] == {
        "ok": True,
        "required": True,
        "branch": "work/feature",
        "owner": "agent-a",
        "actor": "agent-a",
        "reason": "matched",
    }


def test_pre_tool_hook_admits_detached_rebase_of_owned_work_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    git(worktree, "checkout", "--detach")
    git_dir = Path(git(worktree, "rev-parse", "--absolute-git-dir"))
    rebase_dir = git_dir / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/work/feature\n", encoding="utf-8")

    report = hook_admission_report(
        root=worktree,
        layer="pre-tool",
        paths=[worktree / "README.md"],
        editor_root=worktree,
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


def test_git_path_falls_back_to_dot_git_when_git_path_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_rev_parse(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git"], 1, "", "not a git repo")

    monkeypatch.setattr(admission_prewrite.subprocess, "run", fail_rev_parse)

    assert admission_prewrite._git_path(tmp_path) == tmp_path / ".git"


def test_pre_tool_hook_keeps_non_work_lane_detached_rebase_protected(tmp_path: Path) -> None:
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


def _trust_bearing_evidence(head: str) -> dict[str, object]:
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
    return EvidenceSet.from_runs(id="proof", head=head, runs=(run,)).to_dict()


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

    path = record_executed_proof(tmp_path, _trust_bearing_evidence(head))

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
        json.dumps({"head": head, "state": "proven", "evidence_digest": "x"}), encoding="utf-8"
    )
    assert executed_proof_record(tmp_path, head) is None
    assert "proof_not_proven" in proof_gaps(tmp_path, head)

    # Non-proven local state never admits a proof even if the file is present.
    (proof_dir / f"{head}.json").write_text(
        json.dumps({"head": head, "state": "pending", "evidence_digest": "x"}), encoding="utf-8"
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
    assert proof_gaps(tmp_path, head) == []


def test_ref_move_admission_blocks_accepted_bypass(tmp_path) -> None:
    """The candidate-train invariant is un-bypassable: advancing the accepted branch to
    a commit that candidate has not validated is blocked, so a raw `git merge --ff-only
    work/x dev` cannot skip candidate. A candidate-contained advance passes containment
    (proof is still separately required)."""

    def g(*a: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *a], cwd=tmp_path, capture_output=True, text=True, check=False
        )

    g("init", "-b", "dev")
    g("config", "user.name", "t")
    g("config", "user.email", "t@e.x")
    (tmp_path / "a").write_text("1", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "base")
    base = g("rev-parse", "HEAD").stdout.strip()
    g("branch", "candidate/dev")
    g("checkout", "-b", "work/x")
    (tmp_path / "b").write_text("2", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "work")
    work = g("rev-parse", "HEAD").stdout.strip()

    # bypass: move dev to a work commit candidate never validated -> blocked
    blocked = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/dev", old_value=base, new_value=work
    )
    assert blocked["ok"] is False
    assert "accepted_advance_not_candidate_validated" in blocked["required_gaps"]

    # a move of a non-accepted (work) ref is admitted untouched
    lane = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/work/x", old_value=base, new_value=work
    )
    assert lane["ok"] is True

    # candidate-first: once candidate contains the commit, containment passes
    g("checkout", "candidate/dev")
    g("merge", "--ff-only", "work/x")
    advanced = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/dev", old_value=base, new_value=work
    )
    assert "accepted_advance_not_candidate_validated" not in advanced["required_gaps"]


def test_ref_move_admission_blocks_unproven_candidate_ref_move(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    candidate_head = "c" * 40

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/candidate/dev",
        old_value=head,
        new_value=candidate_head,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["decision"] == {
        "action": "block",
        "reason": "protected_ref_move_not_proven",
    }
    assert any("proof" in str(gap) or "not_proven" in str(gap) for gap in report["required_gaps"])


def test_official_closeout_sets_ref_move_admission_context(monkeypatch, tmp_path) -> None:
    """Official closeout is the narrow admitted path through the ref-transaction hook.

    Raw accepted-ref movement remains blocked elsewhere; the internal closeout merge must
    carry the scoped environment that the hook recognizes so ETHOS does not deadlock by
    telling users to run the command it then blocks.
    """
    policy = SimpleNamespace(accepted_branch="dev", candidate_branch="candidate/dev")
    advance_envs: list[dict[str, str] | None] = []

    def fake_git(root, *args, check=True, env=None):
        if args == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(["git"], 0, "old\n", "")
        if args == ("rev-parse", "--verify", "refs/heads/dev"):
            return subprocess.CompletedProcess(["git"], 0, "old\n", "")
        if args[:2] == ("merge-base", "--is-ancestor"):
            return subprocess.CompletedProcess(["git"], 0, "", "")
        # The accepted-ref advance is now a git-native compare-and-swap (update-ref
        # <ref> <new> <old>) plus the worktree sync (reset --keep); both must carry the
        # scoped ETHOS_ALLOW_REF_MOVE env the reference-transaction hook recognizes, so
        # official closeout is admitted through the very moat that blocks raw ref moves.
        if args[0] in ("update-ref", "reset"):
            advance_envs.append(env)
            return subprocess.CompletedProcess(["git"], 0, "", "")
        return subprocess.CompletedProcess(["git"], 0, "", "")

    def fake_policy(_root):
        return policy

    monkeypatch.setattr(core, "load_branch_role_policy", fake_policy)
    monkeypatch.setattr(core, "_git", fake_git)

    def fake_closeout_decision(_request=None, *, root=None, current_head=None):
        return core.MutationDecision(ok=True, state="closeout_ready")

    def fake_workspace_status(_root):
        return {"candidate": {"head": "new", "worktree_path": tmp_path.as_posix()}}

    monkeypatch.setattr(core, "evaluate_closeout_mutation", fake_closeout_decision)
    monkeypatch.setattr(core, "workspace_status", fake_workspace_status)

    report = core.apply_candidate_to_accepted(root=tmp_path, authorized=True, expect_head="old")

    assert report["ok"] is True
    assert advance_envs == [{"ETHOS_ALLOW_REF_MOVE": "1"}, {"ETHOS_ALLOW_REF_MOVE": "1"}]


def test_reference_transaction_hook_fails_closed_on_accepted_branch(tmp_path) -> None:
    """The accepted-branch ref-move gate fails CLOSED: with no reachable ethos binary a
    direct commit onto the accepted branch is BLOCKED (the hole that let a direct commit
    bypass candidate while the CLI lagged its own command). Non-accepted branches fail
    OPEN so an unavailable binary does not brick ordinary work-lane commits; the
    sanctioned closeout escape (ETHOS_ALLOW_REF_MOVE=1) still advances the accepted
    branch."""
    hook_src = Path(__file__).resolve().parents[3] / ".githooks" / "reference-transaction"
    if not hook_src.exists():
        pytest.skip("reference-transaction hook script not present")

    def g(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=False, env=env
        )

    g("init", "-b", "dev")
    g("config", "user.name", "t")
    g("config", "user.email", "t@e.x")
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    shutil.copy(hook_src, hooks / "reference-transaction")
    (hooks / "reference-transaction").chmod(0o755)
    (tmp_path / "a").write_text("1", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "base")
    g("branch", "candidate/dev")
    g("config", "core.hooksPath", ".githooks")
    g("config", "ethos.acceptedBranch", "dev")

    no_binary = {**os.environ, "PATH": "/usr/bin:/bin"}

    # (1) accepted branch, no ethos binary -> BLOCKED (fail-closed)
    (tmp_path / "b").write_text("2", encoding="utf-8")
    g("add", ".")
    blocked = g("commit", "-m", "direct to dev", env=no_binary)
    assert blocked.returncode != 0
    dev_head = g("rev-parse", "dev").stdout.strip()

    # (2) non-accepted branch, no ethos binary -> ALLOWED (fail-open)
    g("checkout", "-b", "work/x")
    (tmp_path / "w").write_text("w", encoding="utf-8")
    g("add", ".")
    work_commit = g("commit", "-m", "work commit", env=no_binary)
    assert work_commit.returncode == 0

    # (3) sanctioned closeout escape -> accepted branch advances
    g("checkout", "dev")
    closeout = g("merge", "--ff-only", "work/x", env={**no_binary, "ETHOS_ALLOW_REF_MOVE": "1"})
    assert closeout.returncode == 0
    assert g("rev-parse", "dev").stdout.strip() != dev_head
