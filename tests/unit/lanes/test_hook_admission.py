from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import ethos.adapters.admission.identity as admission_identity
from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.admission.identity import push_identity_policy_report
from ethos.adapters.admission.prewrite import runtime_binding_check
from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy
from ethos.adapters.mutation.proof import attestation_store_dir
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.runtime.binding import runner_source_root
from ethos.adapters.repo.runtime.binding import runtime_binding
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.admission import HookAdmissionRequest
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import conformant_proof_check
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology
from tests.support.lane_scenarios import leased_worktree as create_leased_worktree


def _assert(actual: dict[str, object], expected: dict[str, object]) -> None:
    for key, value in expected.items():
        assert actual[key] == value


def _hook(root: Path, layer: str, **values: object) -> dict[str, object]:
    return hook_admission_report(HookAdmissionRequest(root=root, layer=layer, **values))


def _identity_repo(path: Path) -> Path:
    repo = init_git_repo(path)
    write_publication_topology(repo)
    for key, value in (
        ("user.name", "Canonical User"),
        ("user.email", "canonical@example.invalid"),
        ("ethos.pushIdentityPolicy", "configured-user"),
    ):
        git(repo, "config", key, value)
    return repo


def _identity_commit(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    author: str = "Canonical User",
    committer: str = "Canonical User",
    name: str = "new",
) -> str:
    for role, identity in (("AUTHOR", author), ("COMMITTER", committer)):
        monkeypatch.setenv(f"GIT_{role}_NAME", identity)
        email = (
            "canonical@example.invalid"
            if identity == "Canonical User"
            else f"{identity.lower().replace(' ', '-')}@example.invalid"
        )
        monkeypatch.setenv(f"GIT_{role}_EMAIL", email)
    (repo / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
    git(repo, "add", f"{name}.txt")
    git(repo, "commit", "-m", f"{name} identity")
    return git(repo, "rev-parse", "HEAD")


def _proof_for_head(root: Path, head: str):
    plan = proof_plan(root, head=head)
    checks = tuple(
        conformant_proof_check(gate, root, tree_ref=head)
        for gate in resolve_gate_policy(root, tree_ref=head).gate_ids
    )
    return issue_proof_attestation(
        root,
        {
            "plan": plan,
            "checks": checks,
            "verdict": "pass",
            "issuer": "agent:test:case:hook",
            "scope": "repository",
            "boundary": "repository",
        },
    )


def _clear_attestation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ETHOS_TEST_ATTESTATION_STATE_DIR", "PYTEST_CURRENT_TEST", "PYTEST_XDIST_WORKER"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def leased_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    worktree = create_leased_worktree(
        init_git_repo(tmp_path / "repo"), tmp_path / "repo-work-feature"
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    return worktree


PUSH_INVALID_TARGETS = (
    pytest.param(
        "refs/heads/candidate/dev",
        "origin",
        "publication_candidate_branch_remote_forbidden:candidate/dev",
        "any",
        id="candidate_remote_forbidden",
    ),
    pytest.param(
        "refs/heads/dev",
        "unknown",
        "publication_remote_target_unknown:unknown",
        "any",
        id="unknown_remote",
    ),
    pytest.param(
        "refs/heads/work/dual-remote",
        "github",
        "publication_remote_branch_forbidden:work/dual-remote",
        "absent",
        id="work_remote_forbidden_without_proof",
    ),
)

PREWRITE_STATES = (
    pytest.param(
        "protected_path", "accepted_root", "protected_lane_prewrite_blocked", id="protected_path"
    ),
    pytest.param(
        "protected_missing_paths",
        "accepted_root",
        "protected_root_pretool_paths_required",
        id="protected_missing_paths",
    ),
    pytest.param(
        "work_missing_lease",
        "work_lane",
        "work_lane_missing_lease:work/feature",
        id="work_missing_lease",
    ),
)

PREWRITE_ACTOR_STATES = (
    pytest.param("agent:test:case:agent-a", "admitted", "allow", "matched", id="holder_match"),
    pytest.param(
        "agent:test:case:agent-b",
        "blocked",
        "block",
        "lease_holder_mismatch:work/feature",
        id="holder_mismatch",
    ),
)

MUTATION_WITHOUT_PATHS = (
    'python -c \'from pathlib import Path; Path("README.md").write_text("x")\'',
    "python scripts/generate.py",
    "git apply patch.diff",
    "touch README.md",
)

OBSERVE_ONLY_COMMANDS = (
    "git status --short",
    "git branch --show-current",
    "git branch --list 'work/*'",
    "git tag --list 'v*'",
    "git tag --points-at HEAD",
    "git stash list",
    "git stash show --stat",
    "ethos status --json",
    "ethos plan --root=. --json",
)

EFFECT_CAPABLE_COMMANDS = (
    "git branch feature",
    "git branch -D feature",
    "git tag v1",
    "git tag -d v1",
    "ethos status --execute=true",
    "ethos plan --apply=true",
    "find . -delete",
)

UNCLASSIFIABLE_WITH_PATHS = (
    "git status\nrm README.md",
    "echo $(touch README.md)",
    "echo `touch README.md`",
    "cat <(touch README.md)",
    "git status; rm README.md",
    "git status 'unterminated",
)

STASH_OPERATION_STATES = (
    pytest.param("git stash list --format=%gd", False, "list", id="list"),
    pytest.param("git -C . stash show --stat", False, "show", id="show"),
    pytest.param("git stash", True, "push", id="implicit_push"),
    pytest.param("git stash -u", True, "push", id="short_option_push"),
    pytest.param("git stash push -- README.md", True, "push", id="explicit_push"),
    pytest.param("command git stash", True, "push", id="command_wrapper"),
    pytest.param("env MODE=test git stash", True, "push", id="env_wrapper"),
    pytest.param("sudo git stash", True, "push", id="sudo_wrapper"),
)

POSTWRITE_STATES = (
    pytest.param(
        "protected", "accepted_root", "post_write_protected_root_dirty", id="protected_dirty"
    ),
    pytest.param("work", "work_lane", "post_write_unexpected_path", id="work_unexpected_path"),
)

IDENTITY_STATES = (
    pytest.param("Canonical User", "Canonical User", "pass", id="canonical"),
    pytest.param("Codex", "Codex", "block", id="both_noncanonical"),
    pytest.param("Other Author", "Canonical User", "block", id="author_noncanonical"),
    pytest.param("Canonical User", "Other Committer", "block", id="committer_noncanonical"),
)

PROPOSAL_BASELINE_STATES = (
    pytest.param("valid", 1, "", id="valid"),
    pytest.param("missing", 0, "push_identity_proposal_baseline_missing:origin/dev", id="missing"),
    pytest.param(
        "diverged", 0, "push_identity_proposal_baseline_not_ancestor:origin/dev", id="diverged"
    ),
)


@pytest.mark.parametrize(("target_ref", "remote", "gap", "proof_check"), PUSH_INVALID_TARGETS)
def test_push_invalid_target_matrix(
    tmp_path: Path, target_ref: str, remote: str, gap: str, proof_check: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    report = push_admission_report(
        root=repo,
        target_ref=target_ref,
        pushed_head=git(repo, "rev-parse", "HEAD"),
        remote_name=remote,
    )
    _assert(report, {"verdict": "block"})
    assert "ok" not in report
    assert gap in report["required_gaps"]
    if proof_check == "absent":
        assert not any("proof" in str(item) for item in report["required_gaps"])


def test_hook_state_matrix(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    other = init_git_repo(tmp_path / "other")
    report = _hook(repo, "context", expected_root=other)
    _assert(
        report,
        {
            "verdict": "block",
            "state": "blocked",
            "decision": {"action": "block", "reason": "hook_context_root_mismatch"},
            "target_root": repo.resolve().as_posix(),
            "expected_root": other.resolve().as_posix(),
        },
    )
    assert "hook_context_root_mismatch" in report["required_gaps"]
    report = _hook(repo, "unknown-layer")
    _assert(
        report,
        {
            "verdict": "block",
            "state": "blocked",
            "layer": "unknown-layer",
            "decision": {"action": "block", "reason": "hook_layer_invalid"},
            "hook": {},
            "required_gaps": ["hook_layer_invalid"],
        },
    )
    assert "ok" not in report


@pytest.mark.parametrize(("state", "role", "reason"), PREWRITE_STATES)
def test_prewrite_state_matrix(tmp_path: Path, state: str, role: str, reason: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    root, values = (repo, {"editor_root": repo, "require_editor_root": True})
    if state == "protected_path":
        values["paths"] = [repo / "README.md"]
    elif state == "work_missing_lease":
        root = tmp_path / "repo-work-feature"
        git(repo, "worktree", "add", "-b", "work/feature", root.as_posix(), "dev")
        values.update(editor_root=root, paths=[root / "README.md"])
    report = _hook(root, "pre-tool", **values)
    _assert(
        report,
        {
            "verdict": "block",
            "state": "blocked",
            "role": role,
            "decision": {"action": "block", "reason": reason},
        },
    )
    assert reason in report["required_gaps"]
    if state == "protected_path":
        assert report["admission"]["error"] == reason
    elif state == "work_missing_lease":
        assert report["admission"]["work_lane_lease"]["verdict"] == "block"
        next_action = (
            "ethos lane start <name> --commitment <commitment.toml> "
            "--holder-ref <holder-ref> --apply --json"
        )
        assert report["next_action"] == next_action


@pytest.mark.parametrize(("actor", "state", "action", "reason"), PREWRITE_ACTOR_STATES)
def test_prewrite_actor_lease_matrix(
    leased_worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
    actor: str,
    state: str,
    action: str,
    reason: str,
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    report = _hook(
        leased_worktree,
        "pre-tool",
        paths=[leased_worktree / "README.md"],
        editor_root=leased_worktree,
        require_editor_root=True,
    )
    verdict = "pass" if state == "admitted" else "block"
    _assert(
        report,
        {
            "verdict": verdict,
            "state": state,
            "role": "work_lane",
            "decision": {
                "action": action,
                "reason": "prewrite_admitted" if state == "admitted" else reason,
            },
        },
    )
    lease = report["admission"]["work_lane_lease"]
    _assert(
        lease,
        {
            "verdict": verdict,
            "required": True,
            "branch": "work/feature",
            "holder_ref": "agent:test:case:agent-a",
            "invocation_holder_ref": actor,
            "epoch": 1,
            "reason": reason,
        },
    )
    assert lease["lease_id"].startswith("lease:")
    assert lease["expected_head"] == git(leased_worktree, "rev-parse", "HEAD")
    if state == "blocked":
        next_action = (
            "set ETHOS_ACTOR=agent:test:case:agent-a and rerun the blocked command, "
            "or obtain handoff"
        )
        assert report["next_action"] == next_action


def test_prewrite_rebase_state_matrix(leased_worktree: Path) -> None:
    root = leased_worktree
    branch_head = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "--detach")
    (root / "REBASE.md").write_text("# replay checkpoint\n", encoding="utf-8")
    git(root, "add", "REBASE.md")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "replay checkpoint",
    )
    detached_head = git(root, "rev-parse", "HEAD")
    rebase_dir = Path(git(root, "rev-parse", "--absolute-git-dir")) / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/work/feature\n", encoding="utf-8")
    report = _hook(
        root, "pre-tool", paths=[root / "README.md"], editor_root=root, require_editor_root=True
    )
    _assert(report, {"verdict": "pass", "role": "work_lane", "branch": "work/feature"})
    _assert(
        report["admission"],
        {
            "status_role": "detached",
            "effective_context": {
                "role": "work_lane",
                "branch": "work/feature",
                "source": "git_rebase_head_name",
                "rebase_head_name": "work/feature",
            },
        },
    )
    _assert(
        report["admission"]["work_lane_lease"],
        {
            "current_head": detached_head,
            "binding_head": branch_head,
            "head_source": "rebase_branch_ref",
        },
    )
    root = init_git_repo(leased_worktree.parent / "protected")
    git(root, "checkout", "--detach")
    rebase_dir = Path(git(root, "rev-parse", "--absolute-git-dir")) / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/dev\n", encoding="utf-8")
    report = _hook(
        root, "pre-tool", paths=[root / "README.md"], editor_root=root, require_editor_root=True
    )
    _assert(
        report,
        {
            "verdict": "block",
            "role": "detached",
            "decision": {"action": "block", "reason": "protected_lane_prewrite_blocked"},
        },
    )
    assert report["admission"]["effective_context"] == {
        "role": "detached",
        "branch": "",
        "source": "prewrite_context",
        "rebase_head_name": "dev",
    }


@pytest.mark.parametrize("command", MUTATION_WITHOUT_PATHS)
def test_prerun_mutation_without_paths_matrix(tmp_path: Path, command: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    report = _hook(repo, "pre-run", command=command, editor_root=repo, require_editor_root=True)
    _assert(
        report,
        {
            "verdict": "block",
            "state": "blocked",
            "decision": {"action": "block", "reason": "hook_prerun_paths_required"},
        },
    )
    assert report["command_risk"]["tracked_mutation_risk"] is True
    assert "hook_prerun_paths_required" in report["required_gaps"]


@pytest.mark.parametrize("command", OBSERVE_ONLY_COMMANDS)
def test_shell_read_parity_matrix(command: str) -> None:
    assert command_risk(command) == {
        "tracked_mutation_risk": False,
        "unclassifiable": False,
        "reason": "observe_only_command",
    }


@pytest.mark.parametrize("command", EFFECT_CAPABLE_COMMANDS)
def test_shell_write_parity_matrix(command: str) -> None:
    _assert(command_risk(command), {"tracked_mutation_risk": True, "unclassifiable": False})


@pytest.mark.parametrize("command", UNCLASSIFIABLE_WITH_PATHS)
def test_prerun_unclassifiable_matrix(tmp_path: Path, command: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    report = _hook(
        repo,
        "pre-run",
        command=command,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )
    _assert(
        report,
        {
            "verdict": "block",
            "state": "blocked",
            "decision": {"action": "block", "reason": "shell_command_unclassifiable"},
        },
    )
    assert report["command_risk"]["unclassifiable"] is True


@pytest.mark.parametrize(("command", "forbidden", "operation"), STASH_OPERATION_STATES)
def test_stash_operation_matrix(command: str, forbidden: object, operation: str) -> None:
    _assert(git_stash_policy(command), {"forbidden": forbidden, "operation": operation})


def test_runtime_state_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_git_repo(tmp_path / "repo")
    module = repo / "src/ethos/__init__.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    git(repo, "add", module.relative_to(repo).as_posix())
    monkeypatch.setenv("GIT_DIR", git(repo, "rev-parse", "--absolute-git-dir"))
    assert runner_source_root(module) == repo.resolve()
    module = tmp_path / "venv/lib/python3.12/site-packages/ethos/__init__.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    assert runner_source_root(module) == module.parent
    python = tmp_path / "common/ethos/runtime/digest/venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    monkeypatch.setattr("ethos.adapters.repo.runtime.binding.sys.executable", python.as_posix())
    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.binding._schema_source_root",
        lambda audit_root, _runner_root: audit_root,
    )
    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.binding.hook_runtime_binding",
        lambda _root: {
            "python": python.as_posix(),
            "required_gaps": [],
            "hooks_path": "",
            "runtime_manifest_path": "",
            "runtime_digest": "digest",
            "wheel_sha256": "0" * 64,
            "scripts": [],
        },
    )
    assert runtime_binding(repo)["state"] == "bound_to_common_runtime"
    monkeypatch.setattr(
        "ethos.adapters.admission.prewrite.profile_gate_registry",
        lambda _root: {"quality": object()},
    )
    common = {
        "audit_root": repo.resolve().as_posix(),
        "runner_source_root": "/external/package/ethos",
        "schema_source_root": repo.resolve().as_posix(),
        "runner_matches_audit_root": False,
        "schema_matches_audit_root": True,
    }
    report = runtime_binding_check(
        {"runtime_binding": {**common, "state": "bound_to_common_runtime"}}
    )
    _assert(report, {"verdict": "pass", "runner_matches_common_runtime": True})
    report = runtime_binding_check(
        {"runtime_binding": {**common, "state": "external_declared_runner"}}
    )
    _assert(report, {"verdict": "block", "runner_matches_common_runtime": False})


@pytest.mark.parametrize(("state", "role", "reason"), POSTWRITE_STATES)
def test_postwrite_state_matrix(tmp_path: Path, state: str, role: str, reason: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    root, values = (repo, {"editor_root": repo, "require_editor_root": True})
    if state == "work":
        root = tmp_path / "repo-work-feature"
        git(repo, "worktree", "add", "-b", "work/feature", root.as_posix(), "dev")
        values["editor_root"] = root
    else:
        values["paths"] = [repo / "README.md"]
    (root / "README.md").write_text("# changed\n", encoding="utf-8")
    report = _hook(root, "post-write", **values)
    _assert(
        report,
        {
            "verdict": "block",
            "state": "fused",
            "role": role,
            "decision": {"action": "fuse", "reason": reason},
            "changed_paths": ["README.md"],
        },
    )
    assert reason in report["required_gaps"]
    if state == "work":
        assert report["unexpected_paths"] == ["README.md"]


def test_push_topology_and_proof_state_matrix(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos/release.toml").write_text(
        '[publication]\nremotes = ["origin", "github"]\n', encoding="utf-8"
    )
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/dev",
        pushed_head=git(repo, "rev-parse", "HEAD"),
        remote_name="origin",
    )
    assert report["publication_branch_admission"]["enforcement_gaps"] == [
        "publication_topology_declaration_invalid"
    ]
    assert "publication_topology_declaration_invalid" in report["required_gaps"]
    write_publication_topology(repo)
    head = git(repo, "rev-parse", "HEAD")
    for ref, gap in (
        ("refs/heads/dev", "proof"),
        ("refs/heads/work/feature", "publication_remote_branch_forbidden:work/feature"),
    ):
        report = push_admission_report(root=repo, target_ref=ref, pushed_head=head)
        _assert(report, {"verdict": "block", "state": "blocked"})
        assert "ok" not in report
        assert any(gap in str(item) for item in report["required_gaps"])


@pytest.mark.parametrize(("author", "committer", "verdict"), IDENTITY_STATES)
def test_identity_state_matrix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, author: str, committer: str, verdict: str
) -> None:
    repo = _identity_repo(tmp_path / "repo")
    remote_head = git(repo, "rev-parse", "HEAD")
    pushed_head = _identity_commit(repo, monkeypatch, author, committer)
    policy = push_identity_policy_report(repo, pushed_head, remote_head)
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/work/identity",
        pushed_head=pushed_head,
        remote_head=remote_head,
    )
    _assert(policy, {"verdict": verdict, "checked_commit_count": 1})
    assert report["identity_policy"] == policy
    assert "publication_remote_branch_forbidden:work/identity" in report["required_gaps"]
    for kind, identity in (("author", author), ("committer", committer)):
        assert (
            f"pushed_commit_{kind}_not_configured_identity:{pushed_head}" in report["required_gaps"]
        ) is (identity != "Canonical User")


@pytest.mark.parametrize(("state", "count", "gap"), PROPOSAL_BASELINE_STATES)
def test_proposal_baseline_state_matrix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, state: str, count: int, gap: str
) -> None:
    repo = _identity_repo(tmp_path / "repo")
    if state == "valid":
        git(
            repo,
            "update-ref",
            "refs/remotes/origin/dev",
            _identity_commit(repo, monkeypatch, "Legacy User", "Legacy User", "legacy"),
        )
    elif state == "diverged":
        git(repo, "checkout", "-b", "remote-source")
        git(
            repo,
            "update-ref",
            "refs/remotes/origin/dev",
            _identity_commit(repo, monkeypatch, name="remote"),
        )
        git(repo, "checkout", "dev")
    policy = push_admission_report(
        root=repo,
        target_ref="refs/heads/proposal/identity-baseline",
        pushed_head=_identity_commit(repo, monkeypatch),
        remote_head="0" * 40,
    )["identity_policy"]
    assert policy["checked_commit_count"] == count
    assert gap in policy["required_gaps"] if gap else policy["verdict"] == "pass"


def test_identity_failure_state_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    assert set(push_identity_policy_report(repo, "missing-head")["required_gaps"]) >= {
        "push_identity_user_name_missing",
        "push_identity_user_email_missing",
        "push_identity_commit_range_unreadable",
    }
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.com")
    run_git = admission_identity.run_git

    def fail_rev_list(root, *args, **kwargs):
        return (
            type("FailedProcess", (), {"returncode": 1, "stdout": "", "stderr": "fatal"})()
            if args[:1] == ("rev-list",)
            else run_git(root, *args, **kwargs)
        )

    monkeypatch.setattr(admission_identity, "run_git", fail_rev_list)
    report = push_identity_policy_report(repo, git(repo, "rev-parse", "HEAD"))
    _assert(
        report,
        {
            "verdict": "block",
            "checked_commit_count": 0,
            "required_gaps": ["push_identity_commit_range_unreadable"],
        },
    )
    assert "ok" not in report


def test_attestation_state_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_attestation_env(monkeypatch)
    assert attestation_store_dir(tmp_path) == tmp_path / ".ethos/state/attestations"
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    observed_common = Path(git(repo, "rev-parse", "--git-common-dir"))
    common = (
        (repo / observed_common).resolve() if not observed_common.is_absolute() else observed_common
    )
    assert state_database(repo) == common / "ethos/state.sqlite"
    assert attestation_store_dir(repo) == common / "ethos/attestations"
    assert state_database(repo) != repo / ".ethos/state/state.sqlite"
    assert attestation_store_dir(repo) != repo / ".ethos/state/attestations"
    head = git(repo, "rev-parse", "HEAD")
    store = tmp_path / ".ethos/state/attestations-gw1"
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw1")
    monkeypatch.setenv("ETHOS_TEST_ATTESTATION_STATE_DIR", store.as_posix())
    attestation = _proof_for_head(repo, head)
    assert persist_proof_attestation(repo, attestation) == store / f"{attestation.id}.json"
    assert proof_attestation(repo, head) == attestation
    assert not (repo / f".ethos/state/proof/{head}.json").exists()


def test_attestation_validity_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_attestation_env(monkeypatch)
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    legacy = repo / f".ethos/state/proof/{head}.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"head": head, "state": "proven"}), encoding="utf-8")
    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["proof_not_proven"]
    gate = resolve_gate_policy(repo, tree_ref=head).gate_ids[0]
    focused = issue_proof_attestation(
        repo,
        {
            "plan": proof_plan(repo, head=head, gate_ids=(gate,)),
            "checks": (conformant_proof_check(gate, repo, tree_ref=head),),
            "verdict": "pass",
            "issuer": "agent:test:case:hook",
            "scope": "repository",
            "boundary": "focused",
        },
    )
    persist_proof_attestation(repo, focused)
    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["proof_attestation_context_mismatch"]
    complete = _proof_for_head(repo, head)
    persist_proof_attestation(repo, complete)
    assert proof_attestation(repo, head) == complete
    assert proof_gaps(repo, head) == []
    assert proof_gaps(tmp_path, "f" * 40) == ["proof_not_proven"]
