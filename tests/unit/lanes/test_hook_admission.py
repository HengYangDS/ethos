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
from ethos.adapters.repo.runtime.binding import runner_source_root
from ethos.adapters.repo.runtime.binding import runtime_binding
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.admission import HookAdmissionRequest
from ethos.repository.policy.gates import resolve_gate_policy
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import conformant_proof_check
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology
from tests.support.lane_scenarios import leased_worktree as create_leased_worktree


def _assert_fields(actual: dict[str, object], **expected: object) -> None:
    assert {key: actual[key] for key in expected} == expected


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
    *,
    author: str = "Canonical User",
    committer: str = "Canonical User",
    name: str = "new",
) -> str:
    for role, identity in (("AUTHOR", author), ("COMMITTER", committer)):
        monkeypatch.setenv(f"GIT_{role}_NAME", identity)
        monkeypatch.setenv(
            f"GIT_{role}_EMAIL",
            "canonical@example.invalid"
            if identity == "Canonical User"
            else f"{identity.lower().replace(' ', '-')}@example.invalid",
        )
    (repo / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
    git(repo, "add", f"{name}.txt")
    git(repo, "commit", "-m", f"{name} identity")
    return git(repo, "rev-parse", "HEAD")


def _proof_attestation_for_head(root: Path, head: str):
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
    for name in (
        "ETHOS_TEST_ATTESTATION_STATE_DIR",
        "PYTEST_CURRENT_TEST",
        "PYTEST_XDIST_WORKER",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def leased_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    worktree = create_leased_worktree(
        init_git_repo(tmp_path / "repo"), tmp_path / "repo-work-feature"
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    return worktree


@pytest.mark.parametrize(
    ("target_ref", "remote_name", "gap", "proof_check"),
    [
        (
            "refs/heads/candidate/dev",
            "origin",
            "publication_candidate_branch_remote_forbidden:candidate/dev",
            "any",
        ),
        ("refs/heads/dev", "unknown", "publication_remote_target_unknown:unknown", "any"),
        (
            "refs/heads/work/dual-remote",
            "github",
            "publication_remote_branch_forbidden:work/dual-remote",
            "absent",
        ),
    ],
)
def test_push_admission_rejects_invalid_targets_before_or_without_proof(
    tmp_path: Path, target_ref: str, remote_name: str, gap: str, proof_check: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    report = push_admission_report(
        root=repo,
        target_ref=target_ref,
        pushed_head=git(repo, "rev-parse", "HEAD"),
        remote_name=remote_name,
    )
    assert report["verdict"] == "block"
    assert "ok" not in report
    assert gap in report["required_gaps"]
    if proof_check == "absent":
        assert not any("proof" in str(item) for item in report["required_gaps"])


def test_push_admission_rejects_legacy_topology_without_enforcement_bypass(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "release.toml").write_text(
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


def test_context_hook_rejects_stale_target_root(tmp_path: Path) -> None:
    repo, other = init_git_repo(tmp_path / "repo"), init_git_repo(tmp_path / "other")
    report = _hook(repo, "context", expected_root=other)
    _assert_fields(
        report,
        verdict="block",
        state="blocked",
        decision={"action": "block", "reason": "hook_context_root_mismatch"},
        target_root=repo.resolve().as_posix(),
        expected_root=other.resolve().as_posix(),
    )
    assert "hook_context_root_mismatch" in report["required_gaps"]


def test_unknown_hook_layer_blocks_without_pretool_fallback(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    report = _hook(repo, "unknown-layer")

    _assert_fields(
        report,
        verdict="block",
        state="blocked",
        layer="unknown-layer",
        decision={"action": "block", "reason": "hook_layer_invalid"},
    )
    assert report["hook"] == {}
    assert report["required_gaps"] == ["hook_layer_invalid"]
    assert "ok" not in report


@pytest.mark.parametrize(
    ("kind", "expected_role", "reason", "admission_error"),
    [
        (
            "protected-path",
            "accepted_root",
            "protected_lane_prewrite_blocked",
            "protected_lane_prewrite_blocked",
        ),
        ("protected-no-path", "accepted_root", "protected_root_pretool_paths_required", ""),
        ("unleased-work", "work_lane", "work_lane_missing_lease:work/feature", ""),
    ],
)
def test_pre_tool_hook_blocks_protected_or_unleased_mutation(
    tmp_path: Path, kind: str, expected_role: str, reason: str, admission_error: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    root = repo
    values: dict[str, object] = {"editor_root": repo, "require_editor_root": True}
    if kind == "protected-path":
        values["paths"] = [repo / "README.md"]
    elif kind == "unleased-work":
        root = tmp_path / "repo-work-feature"
        git(repo, "worktree", "add", "-b", "work/feature", root.as_posix(), "dev")
        values.update(editor_root=root, paths=[root / "README.md"])
    report = _hook(root, "pre-tool", **values)
    _assert_fields(
        report,
        verdict="block",
        state="blocked",
        role=expected_role,
        decision={"action": "block", "reason": reason},
    )
    assert reason in report["required_gaps"]
    if admission_error:
        assert report["admission"]["error"] == admission_error
    elif kind == "unleased-work":
        assert report["admission"]["work_lane_lease"]["verdict"] == "block"
        assert report["next_action"] == (
            "ethos lane start <name> --commitment <commitment.toml> "
            "--holder-ref <holder-ref> --apply --json"
        )


@pytest.mark.parametrize(
    ("actor", "state", "action", "reason"),
    [
        ("agent:test:case:agent-a", "admitted", "allow", "matched"),
        ("agent:test:case:agent-b", "blocked", "block", "lease_holder_mismatch:work/feature"),
    ],
)
def test_pre_tool_hook_evaluates_leased_work_lane_actor(
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
    _assert_fields(
        report,
        verdict="pass" if state == "admitted" else "block",
        state=state,
        role="work_lane",
        decision={
            "action": action,
            "reason": "prewrite_admitted" if state == "admitted" else reason,
        },
    )
    lease = report["admission"]["work_lane_lease"]
    _assert_fields(
        lease,
        verdict="pass" if state == "admitted" else "block",
        required=True,
        branch="work/feature",
        holder_ref="agent:test:case:agent-a",
        invocation_holder_ref=actor,
        epoch=1,
        reason=reason,
    )
    assert lease["lease_id"].startswith("lease:")
    assert lease["expected_head"] == git(leased_worktree, "rev-parse", "HEAD")
    if state == "blocked":
        assert report["next_action"] == (
            "set ETHOS_ACTOR=agent:test:case:agent-a and rerun the blocked command, "
            "or obtain handoff"
        )


def test_pre_tool_hook_handles_rebase_context(leased_worktree: Path) -> None:
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
    rebase_dir = Path(git(leased_worktree, "rev-parse", "--absolute-git-dir")) / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/work/feature\n", encoding="utf-8")
    report = _hook(
        leased_worktree,
        "pre-tool",
        paths=[leased_worktree / "README.md"],
        editor_root=leased_worktree,
        require_editor_root=True,
    )
    _assert_fields(report, verdict="pass", role="work_lane", branch="work/feature")
    _assert_fields(
        report["admission"],
        status_role="detached",
        effective_context={
            "role": "work_lane",
            "branch": "work/feature",
            "source": "git_rebase_head_name",
            "rebase_head_name": "work/feature",
        },
    )
    _assert_fields(
        report["admission"]["work_lane_lease"],
        current_head=detached_head,
        binding_head=branch_head,
        head_source="rebase_branch_ref",
    )


def test_pre_tool_hook_keeps_non_work_lane_detached_rebase_protected(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "checkout", "--detach")
    rebase_dir = Path(git(repo, "rev-parse", "--absolute-git-dir")) / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/dev\n", encoding="utf-8")
    report = _hook(
        repo, "pre-tool", paths=[repo / "README.md"], editor_root=repo, require_editor_root=True
    )
    _assert_fields(
        report,
        verdict="block",
        role="detached",
        decision={"action": "block", "reason": "protected_lane_prewrite_blocked"},
    )
    assert report["admission"]["effective_context"] == {
        "role": "detached",
        "branch": "detached",
        "source": "prewrite_context",
        "rebase_head_name": "dev",
    }


@pytest.mark.parametrize(
    "command",
    [
        'python -c \'from pathlib import Path; Path("README.md").write_text("x")\'',
        "python scripts/generate.py",
        "git apply patch.diff",
        "touch README.md",
    ],
)
def test_pre_run_hook_blocks_mutation_risk_without_target_paths(
    tmp_path: Path, command: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    report = _hook(repo, "pre-run", command=command, editor_root=repo, require_editor_root=True)
    _assert_fields(
        report,
        verdict="block",
        state="blocked",
        decision={"action": "block", "reason": "hook_prerun_paths_required"},
    )
    assert report["command_risk"]["tracked_mutation_risk"] is True
    assert "hook_prerun_paths_required" in report["required_gaps"]


@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "git branch --show-current",
        "git branch --list 'work/*'",
        "git tag --list 'v*'",
        "git tag --points-at HEAD",
        "git stash list",
        "git stash show --stat",
        "ethos status --json",
        "ethos plan --root=. --json",
    ],
)
def test_shell_admission_read_allowlist(command: str) -> None:
    assert command_risk(command) == {
        "tracked_mutation_risk": False,
        "unclassifiable": False,
        "reason": "observe_only_command",
    }


@pytest.mark.parametrize(
    "command",
    [
        "git branch feature",
        "git branch -D feature",
        "git tag v1",
        "git tag -d v1",
        "ethos status --execute=true",
        "ethos plan --apply=true",
        "find . -delete",
    ],
)
def test_shell_admission_routes_effect_capable_commands_to_path_admission(command: str) -> None:
    risk = command_risk(command)

    assert risk["tracked_mutation_risk"] is True
    assert risk["unclassifiable"] is False


@pytest.mark.parametrize(
    "command",
    [
        "git status\nrm README.md",
        "echo $(touch README.md)",
        "echo `touch README.md`",
        "cat <(touch README.md)",
        "git status; rm README.md",
        "git status 'unterminated",
    ],
)
def test_pre_run_hook_blocks_unclassifiable_shell_even_with_target_paths(
    tmp_path: Path, command: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    report = _hook(
        repo,
        "pre-run",
        command=command,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    _assert_fields(
        report,
        verdict="block",
        state="blocked",
        decision={"action": "block", "reason": "shell_command_unclassifiable"},
    )
    assert report["command_risk"]["unclassifiable"] is True


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("git stash list --format=%gd", {"forbidden": False, "operation": "list"}),
        ("git -C . stash show --stat", {"forbidden": False, "operation": "show"}),
        ("git stash", {"forbidden": True, "operation": "push"}),
        ("git stash -u", {"forbidden": True, "operation": "push"}),
        ("git stash push -- README.md", {"forbidden": True, "operation": "push"}),
        ("command git stash", {"forbidden": True, "operation": "push"}),
        ("env MODE=test git stash", {"forbidden": True, "operation": "push"}),
        ("sudo git stash", {"forbidden": True, "operation": "push"}),
    ],
)
def test_git_stash_policy_is_operation_exact(command: str, expected: dict[str, object]) -> None:
    policy = git_stash_policy(command)

    assert {key: policy[key] for key in expected} == expected


def test_runner_source_root_ignores_inherited_git_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    module = repo / "src/ethos/__init__.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    git(repo, "add", module.relative_to(repo).as_posix())
    monkeypatch.setenv("GIT_DIR", git(repo, "rev-parse", "--absolute-git-dir"))

    assert runner_source_root(module) == repo.resolve()


def test_runner_source_root_treats_an_installed_distribution_as_external(
    tmp_path: Path,
) -> None:
    module = tmp_path / "venv" / "lib" / "python3.12" / "site-packages" / "ethos" / "__init__.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")

    assert runner_source_root(module) == module.parent


def test_runtime_binding_recognizes_the_exact_repository_family_hook_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    python = tmp_path / "common" / "ethos" / "runtime" / "digest" / "venv" / "bin/python"
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

    report = runtime_binding(repo)

    assert report["state"] == "bound_to_repository_family"


def test_prewrite_accepts_exact_repository_family_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    monkeypatch.setattr(
        "ethos.adapters.admission.prewrite.profile_gate_registry",
        lambda _root: {"quality": object()},
    )

    report = runtime_binding_check(
        {
            "runtime_binding": {
                "audit_root": repo.resolve().as_posix(),
                "runner_source_root": "/external/package/ethos",
                "schema_source_root": repo.resolve().as_posix(),
                "runner_matches_audit_root": False,
                "state": "bound_to_repository_family",
                "schema_matches_audit_root": True,
            }
        }
    )

    assert report["verdict"] == "pass"
    assert report["runner_matches_repository_family"] is True

    rejected = runtime_binding_check(
        {
            "runtime_binding": {
                "audit_root": repo.resolve().as_posix(),
                "runner_source_root": "/external/package/ethos",
                "schema_source_root": repo.resolve().as_posix(),
                "runner_matches_audit_root": False,
                "state": "external_declared_runner",
                "schema_matches_audit_root": True,
            }
        }
    )
    assert rejected["verdict"] == "block"
    assert rejected["runner_matches_repository_family"] is False


@pytest.mark.parametrize(
    ("kind", "role", "reason"),
    [
        ("protected", "accepted_root", "post_write_protected_root_dirty"),
        ("work", "work_lane", "post_write_unexpected_path"),
    ],
)
def test_post_write_hook_fuses_dirty_state(
    tmp_path: Path, kind: str, role: str, reason: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    root = repo
    values: dict[str, object] = {"editor_root": repo, "require_editor_root": True}
    if kind == "work":
        root = tmp_path / "repo-work-feature"
        git(repo, "worktree", "add", "-b", "work/feature", root.as_posix(), "dev")
        values["editor_root"] = root
    else:
        values["paths"] = [repo / "README.md"]
    (root / "README.md").write_text("# changed\n", encoding="utf-8")
    report = _hook(root, "post-write", **values)
    _assert_fields(
        report,
        verdict="block",
        state="fused",
        role=role,
        decision={"action": "fuse", "reason": reason},
        changed_paths=["README.md"],
    )
    assert reason in report["required_gaps"]
    if kind == "work":
        assert report["unexpected_paths"] == ["README.md"]


def test_push_admission_blocks_unproven_protected_and_work_lane_pushes(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    head = git(repo, "rev-parse", "HEAD")
    for ref, gap in (
        ("refs/heads/dev", "proof"),
        ("refs/heads/work/feature", "publication_remote_branch_forbidden:work/feature"),
    ):
        report = push_admission_report(root=repo, target_ref=ref, pushed_head=head)
        assert report["verdict"] == "block"
        assert "ok" not in report
        assert report["state"] == "blocked"
        assert any(gap in str(item) for item in report["required_gaps"])


@pytest.mark.parametrize(
    ("author", "committer", "expected_result"),
    [
        ("Canonical User", "Canonical User", "allowed"),
        ("Codex", "Codex", "blocked"),
        ("Other Author", "Canonical User", "blocked"),
        ("Canonical User", "Other Committer", "blocked"),
    ],
)
def test_push_identity_policy_checks_configured_author_and_committer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    author: str,
    committer: str,
    expected_result: str,
) -> None:
    repo = _identity_repo(tmp_path / "repo")
    remote_head = git(repo, "rev-parse", "HEAD")
    pushed_head = _identity_commit(repo, monkeypatch, author=author, committer=committer)
    policy = push_identity_policy_report(repo, pushed_head, remote_head)
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/work/identity",
        pushed_head=pushed_head,
        remote_head=remote_head,
    )
    _assert_fields(
        policy,
        verdict="pass" if expected_result == "allowed" else "block",
        checked_commit_count=1,
    )
    assert report["identity_policy"] == policy
    assert "publication_remote_branch_forbidden:work/identity" in report["required_gaps"]
    for kind, identity in (("author", author), ("committer", committer)):
        assert (
            f"pushed_commit_{kind}_not_configured_identity:{pushed_head}" in report["required_gaps"]
        ) is (identity != "Canonical User")


@pytest.mark.parametrize(
    ("baseline", "count", "gap"),
    [
        ("valid", 1, ""),
        ("missing", 0, "push_identity_proposal_baseline_missing:origin/dev"),
        ("diverged", 0, "push_identity_proposal_baseline_not_ancestor:origin/dev"),
    ],
)
def test_new_proposal_push_validates_origin_accepted_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, baseline: str, count: int, gap: str
) -> None:
    repo = _identity_repo(tmp_path / "repo")
    if baseline == "valid":
        git(
            repo,
            "update-ref",
            "refs/remotes/origin/dev",
            _identity_commit(
                repo, monkeypatch, author="Legacy User", committer="Legacy User", name="legacy"
            ),
        )
    if baseline == "diverged":
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
    assert (gap in policy["required_gaps"]) if gap else policy["verdict"] == "pass"


def test_push_identity_helpers_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    head = git(repo, "rev-parse", "HEAD")
    run = admission_identity.subprocess.run

    def fail_rev_list(args, **kwargs):
        if args[:2] == ["git", "rev-list"]:
            return admission_identity.subprocess.CompletedProcess(args, 1, "", "fatal")
        return run(args, **kwargs)

    monkeypatch.setattr(admission_identity.subprocess, "run", fail_rev_list)

    report = push_identity_policy_report(repo, head)

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["checked_commit_count"] == 0
    assert report["required_gaps"] == ["push_identity_commit_range_unreadable"]


def test_attestation_store_defaults_and_worker_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_attestation_env(monkeypatch)
    assert attestation_store_dir(tmp_path) == tmp_path / ".ethos" / "state" / "attestations"
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    observed_common = Path(git(repo, "rev-parse", "--git-common-dir"))
    common = (
        (repo / observed_common).resolve() if not observed_common.is_absolute() else observed_common
    )
    assert state_database(repo) == common / "ethos" / "state.sqlite"
    assert attestation_store_dir(repo) == common / "ethos" / "attestations"
    assert state_database(repo) != repo / ".ethos" / "state" / "state.sqlite"
    assert attestation_store_dir(repo) != repo / ".ethos" / "state" / "attestations"
    head = git(repo, "rev-parse", "HEAD")
    store = tmp_path / ".ethos" / "state" / "attestations-gw1"
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw1")
    monkeypatch.setenv("ETHOS_TEST_ATTESTATION_STATE_DIR", store.as_posix())
    attestation = _proof_attestation_for_head(repo, head)

    assert persist_proof_attestation(repo, attestation) == store / f"{attestation.id}.json"
    assert proof_attestation(repo, head) == attestation
    assert not (repo / ".ethos" / "state" / "proof" / f"{head}.json").exists()


def test_proof_attestation_ignores_legacy_forgery_and_requires_complete_floor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_attestation_env(monkeypatch)
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    legacy = repo / ".ethos" / "state" / "proof" / f"{head}.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"head": head, "state": "proven"}), encoding="utf-8")

    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["proof_not_proven"]

    focused_gate = resolve_gate_policy(repo, tree_ref=head).gate_ids[0]
    focused_plan = proof_plan(repo, head=head, gate_ids=(focused_gate,))
    focused_check = conformant_proof_check(focused_gate, repo, tree_ref=head)
    focused = issue_proof_attestation(
        repo,
        {
            "plan": focused_plan,
            "checks": (focused_check,),
            "verdict": "pass",
            "issuer": "agent:test:case:hook",
            "scope": "repository",
            "boundary": "focused",
        },
    )
    persist_proof_attestation(repo, focused)
    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["proof_attestation_context_mismatch"]

    complete = _proof_attestation_for_head(repo, head)
    persist_proof_attestation(repo, complete)
    assert proof_attestation(repo, head) == complete
    assert proof_gaps(repo, head) == []


def test_promotion_completeness_helper_edges(tmp_path: Path) -> None:
    assert proof_gaps(tmp_path, "f" * 40) == ["proof_not_proven"]
