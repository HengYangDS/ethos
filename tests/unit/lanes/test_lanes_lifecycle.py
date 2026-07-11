from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation import lanes as lane_mutation
from ethos.adapters.mutation.lanes import bind_work_lane_claim
from ethos.adapters.mutation.lanes import refresh_work_lane_base
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.runtime.core import runtime_binding
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.projection import active_leases
from ethos_core.contracts.branch.roles import BranchRolePolicy
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import write_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def test_branch_role_policy_semantic_order_uses_configured_roles_without_hardcoded_names() -> None:
    policy = BranchRolePolicy(
        release_branch="release",
        accepted_branch="integration",
        candidate_branch="stage/integration",
        work_branch_prefix="lane/",
        submit_branch_prefix="review/",
    )

    assert policy.as_status_policy() == {
        "release_branch": "release",
        "accepted_branch": "integration",
        "candidate_branch": "stage/integration",
        "work_branch_prefix": "lane/",
        "submit_branch_prefix": "review/",
        "semantic_order": [
            {
                "role": "release_root",
                "kind": "exact_branch",
                "config_key": "release_branch",
                "pattern": "release",
            },
            {
                "role": "accepted_root",
                "kind": "exact_branch",
                "config_key": "accepted_branch",
                "pattern": "integration",
            },
            {
                "role": "candidate",
                "kind": "exact_branch",
                "config_key": "candidate_branch",
                "pattern": "stage/integration",
            },
            {
                "role": "work_lane",
                "kind": "branch_prefix",
                "config_key": "work_branch_prefix",
                "pattern": "lane/*",
            },
            {
                "role": "submit_lane",
                "kind": "branch_prefix",
                "config_key": "submit_branch_prefix",
                "pattern": "review/*",
            },
        ],
    }
    assert policy.role_for_branch("release") == "release_root"
    assert policy.role_for_branch("integration") == "accepted_root"
    assert policy.role_for_branch("stage/integration") == "candidate"
    assert policy.role_for_branch("lane/feature") == "work_lane"
    assert policy.role_for_branch("review/feature") == "submit_lane"
    assert policy.role_for_branch("main") == "other"
    assert policy.role_for_branch("dev") == "other"
    assert policy.role_for_branch("candidate/dev") == "other"
    assert policy.role_for_branch("work/feature") == "other"
    assert policy.role_for_branch("submit/feature") == "other"


def test_start_work_lane_uses_configured_candidate_and_work_role_policy(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "stage/dev",
        (tmp_path / "repo-stage-dev").as_posix(),
        "dev",
    )
    worktree = tmp_path / "repo-lane-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "lane/feature"
    assert report["base"] == "stage/dev"
    assert git(worktree, "branch", "--show-current") == "lane/feature"


def test_existing_work_lane_claim_binding_can_be_applied_without_restarting_lane(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    report = bind_work_lane_claim(
        root=worktree,
        claim_id="sample-trust",
        apply=True,
    )
    status = workspace_status(worktree)

    assert report["ok"] is True
    assert report["state"] == "bound"
    assert report["branch"] == "work/feature"
    assert report["holder_ref"] == "agent:test:case:agent-test"
    assert report["claim_id"] == "sample-trust"
    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "agent:test:case:agent-test",
        "lease_id": status["closeout_support"]["lease_id"],
        "lease_epoch": 1,
        "claim_id": "sample-trust",
        "claim_binding": "bound",
        "required_gaps": [],
    }


def test_prewrite_rejects_tracked_path_from_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == "protected_lane_prewrite_blocked"
    assert report["role"] == "accepted_root"


def test_prewrite_allows_owned_work_lane_with_matching_editor_root(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-owned"
    start_work_lane(
        root=repo,
        name="owned",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is True
    assert report["role"] == "work_lane"
    assert report["error"] == ""


def test_prewrite_blocks_product_root_when_runner_source_differs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")
    product_marker = worktree / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    product_marker.parent.mkdir(parents=True)
    product_marker.write_text("", encoding="utf-8")
    external_runner = tmp_path / "external" / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    external_runner.parent.mkdir(parents=True)
    (tmp_path / "external" / "pyproject.toml").write_text(
        "[project]\nname='external'\n", encoding="utf-8"
    )
    external_runner.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.core.ethos.__file__", external_runner.as_posix()
    )

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == "root_binding_mismatch"
    assert report["runtime_binding"]["product_audit_root"] is True
    assert report["runtime_binding"]["runner_matches_audit_root"] is False


def test_prewrite_rejects_work_lane_without_editor_root_binding(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-owned"
    start_work_lane(
        root=repo,
        name="owned",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
    )

    assert report["ok"] is False
    assert report["role"] == "work_lane"
    assert report["error"] == "editor_root_missing"


def test_prewrite_rejects_protected_lane_roles(tmp_path: Path) -> None:
    cases = {
        "release_root": ("main",),
        "candidate": ("candidate/dev",),
        "submit_lane": ("submit/review",),
        "other": ("feature/unknown",),
    }
    for role, checkout_args in cases.items():
        repo = init_repo(tmp_path / f"repo-{role}")
        git(repo, "checkout", "-b", *checkout_args)

        report = prewrite_guard(
            root=repo,
            paths=[repo / "README.md"],
            editor_root=repo,
            require_editor_root=True,
        )

        assert report["ok"] is False
        assert report["role"] == role
        assert report["error"] == "protected_lane_prewrite_blocked"


def test_prewrite_rejects_detached_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo-detached")
    git(repo, "checkout", "--detach", "HEAD")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["role"] == "detached"
    assert report["error"] == "protected_lane_prewrite_blocked"


def test_start_work_lane_apply_creates_worktree_and_records_lease(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "work/feature"
    assert report["worktree"] == {
        "branch": "work/feature",
        "path": worktree.resolve().as_posix(),
        "head": git(worktree, "rev-parse", "HEAD"),
        "role": "work_lane",
        "worktree_binding": "linked",
    }
    assert worktree.exists()
    assert git(worktree, "branch", "--show-current") == "work/feature"
    leases = active_leases(repo / ".ethos" / "state" / "state.sqlite")
    assert [(lease["subject"], lease["holder_ref"]) for lease in leases] == [
        ("work/feature", "agent:test:case:agent-test")
    ]


def test_start_work_lane_defaults_path_to_sibling_candidate_home(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    expected = repo.with_name(f"{repo.name}-work-feature")

    report = start_work_lane(
        root=repo,
        name="feature",
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["path"] == expected.resolve().as_posix()
    assert expected.exists()
    assert git(expected, "branch", "--show-current") == "work/feature"


def test_start_work_lane_apply_requires_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "candidate_branch_missing" in report["required_gaps"]
    assert not worktree.exists()


def test_start_work_lane_apply_requires_candidate_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev", "dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "candidate_worktree_missing" in report["required_gaps"]
    assert not worktree.exists()


def test_start_work_lane_apply_rejects_dirty_candidate_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    (candidate / "README.md").write_text("# dirty candidate\n", encoding="utf-8")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["candidate_worktree_dirty"]
    assert not worktree.exists()


def test_start_work_lane_apply_starts_from_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    candidate_head = git(repo, "rev-parse", "candidate/dev")
    (repo / "README.md").write_text("# changed on dev\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance dev only",
    )
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert git(worktree, "rev-parse", "HEAD") == candidate_head
    assert git(repo, "rev-parse", "dev") != candidate_head


def test_refresh_work_lane_base_plans_stale_candidate_base(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "work/feature",
        worktree.as_posix(),
        "candidate/dev",
    )
    (candidate / "CANDIDATE.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "CANDIDATE.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance candidate",
    )
    (worktree / "FEATURE.md").write_text("# feature\n", encoding="utf-8")
    git(worktree, "add", "FEATURE.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "feature work",
    )
    work_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")

    report = refresh_work_lane_base(
        root=worktree,
        apply=False,
        authorized=False,
        expect_head=None,
    )

    assert report["ok"] is True
    assert report["state"] == "ready_to_refresh_base"
    assert report["branch"] == "work/feature"
    assert report["head"] == work_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == []


def test_refresh_work_lane_base_apply_rebases_current_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "work/feature",
        worktree.as_posix(),
        "candidate/dev",
    )
    (candidate / "CANDIDATE.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "CANDIDATE.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance candidate",
    )
    (worktree / "FEATURE.md").write_text("# feature\n", encoding="utf-8")
    git(worktree, "add", "FEATURE.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "feature work",
    )
    previous_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")

    report = refresh_work_lane_base(
        root=worktree,
        apply=True,
        authorized=True,
        expect_head=previous_head,
    )

    refreshed_head = git(worktree, "rev-parse", "HEAD")
    assert report["ok"] is True
    assert report["state"] == "base_refreshed"
    assert report["branch"] == "work/feature"
    assert report["previous_head"] == previous_head
    assert report["head"] == refreshed_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == []
    assert refreshed_head != previous_head
    assert git(repo, "merge-base", "--is-ancestor", candidate_head, refreshed_head) == ""
    assert (worktree / "CANDIDATE.md").exists()
    assert (worktree / "FEATURE.md").exists()


def test_refresh_work_lane_base_rejects_noop_rebase_success(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "work/feature",
        worktree.as_posix(),
        "candidate/dev",
    )
    (candidate / "CANDIDATE.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "CANDIDATE.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance candidate",
    )
    (worktree / "FEATURE.md").write_text("# feature\n", encoding="utf-8")
    git(worktree, "add", "FEATURE.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "feature work",
    )
    previous_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    original_run_git = lane_mutation.run_git

    def successful_noop_rebase(
        root: Path, *args: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == ("-c", "rebase.updateRefs=false", "rebase", "candidate/dev"):
            return subprocess.CompletedProcess(["git", *args], 0, "", "")
        return original_run_git(root, *args, **kwargs)

    monkeypatch.setattr(lane_mutation, "run_git", successful_noop_rebase)

    report = refresh_work_lane_base(
        root=worktree,
        apply=True,
        authorized=True,
        expect_head=previous_head,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["head"] == previous_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == ["refresh_base_postcondition_failed"]
    assert report["next_actions"] == [
        "inspect current Git ancestry and runner, signing, or hook diagnostics",
        "repair the replay environment and rerun ethos lane refresh-base",
    ]


def test_refresh_work_lane_base_apply_requires_authorization_and_expected_head(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "work/feature",
        worktree.as_posix(),
        "candidate/dev",
    )
    (candidate / "CANDIDATE.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "CANDIDATE.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance candidate",
    )

    report = refresh_work_lane_base(
        root=worktree,
        apply=True,
        authorized=False,
        expect_head=None,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required", "expect_head_required"]


def test_start_work_lane_apply_requires_clean_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    current_worktree = tmp_path / "repo-work-current"
    new_worktree = tmp_path / "repo-work-nested"
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "work/current",
        current_worktree.as_posix(),
        "dev",
    )

    report = start_work_lane(
        root=current_worktree,
        name="nested",
        path=new_worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not new_worktree.exists()


def test_start_work_lane_apply_rejects_dirty_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["dirty"] is True
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not worktree.exists()


def test_workspace_status_reports_runtime_binding_for_audited_checkout(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")

    status = workspace_status(repo)

    binding = status["runtime_binding"]
    assert binding["kind"] == "workspace_status_runtime_binding"
    assert binding["audit_root"] == repo.resolve().as_posix()
    assert binding["runner_module_path"]
    assert binding["runner_source_root"]
    assert binding["schema_source_root"]
    assert isinstance(binding["runner_matches_audit_root"], bool)
    assert isinstance(binding["schema_matches_audit_root"], bool)
    assert isinstance(binding["advisory_gaps"], list)
    assert binding["next_action"]


def test_workspace_status_runtime_binding_warns_when_runner_is_external(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    external_runner = tmp_path / "external" / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    external_runner.parent.mkdir(parents=True)
    (tmp_path / "external" / "pyproject.toml").write_text(
        "[project]\nname='external'\n", encoding="utf-8"
    )
    external_runner.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.core.ethos.__file__", external_runner.as_posix()
    )

    status = workspace_status(repo)

    binding = status["runtime_binding"]
    assert binding["state"] == "external_current_runner"
    assert binding["runner_matches_audit_root"] is False
    assert "workspace_status_runner_source_differs_from_audit_root" in binding["advisory_gaps"]
    assert "package-bound runner" in binding["next_action"]


def test_runtime_binding_lives_in_semantic_subpackage(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    binding = runtime_binding(repo)

    assert binding["kind"] == "workspace_status_runtime_binding"
    assert binding["audit_root"] == repo.resolve().as_posix()
