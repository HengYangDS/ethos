from __future__ import annotations

import sqlite3
import subprocess
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lanes import bind_work_lane_claim
from ethos.adapters.mutation.lanes import refresh_work_lane_base
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.status import workspace_status
from ethos.adapters.store.state import active_leases
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.branch_roles import BranchRolePolicy

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


def add_candidate_worktree(repo: Path, path: Path) -> Path:
    git(repo, "worktree", "add", "-b", "candidate/dev", path.as_posix(), "dev")
    return path


def write_role_policy(
    repo: Path,
    *,
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    submit_branch_prefix: str = "review/",
) -> None:
    (repo / ".ethos" / "workspace.toml").write_text(
        "\n".join(
            [
                "[branch_roles]",
                'release_branch = "main"',
                'accepted_branch = "dev"',
                f'candidate_branch = "{candidate_branch}"',
                f'work_branch_prefix = "{work_branch_prefix}"',
                f'submit_branch_prefix = "{submit_branch_prefix}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configure branch roles",
    )


def assert_no_ui_projection(value: object) -> None:
    if isinstance(value, dict):
        forbidden = {"open_action", "open_label", "action", "label"}
        assert not (forbidden & set(value))
        for child in value.values():
            assert_no_ui_projection(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_ui_projection(child)


def test_workspace_status_reports_stage_gates_for_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")

    status = workspace_status(repo)

    assert status["stage_gates"] == {
        "authoring_allowed": False,
        "integration_allowed": False,
        "accepted_closeout_allowed": False,
        "blocked_stage": "authoring",
        "blocker_owner": "",
        "recommended_next_command": "ethos lane start <name>",
        "next_commands": ["ethos lane start <name>"],
    }


def test_workspace_status_reports_stage_gates_for_owned_work_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(root=repo, name="feature", path=worktree, owner="agent:test", apply=True)

    status = workspace_status(worktree)

    assert status["stage_gates"] == {
        "authoring_allowed": True,
        "integration_allowed": True,
        "accepted_closeout_allowed": False,
        "blocked_stage": "accepted_closeout",
        "blocker_owner": "candidate/dev",
        "recommended_next_command": "ethos land --json",
        "next_commands": ["ethos lane prewrite <path>", "ethos land --json"],
    }


def test_workspace_status_stage_gates_keep_authoring_open_when_lane_is_dirty(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(root=repo, name="feature", path=worktree, owner="agent:test", apply=True)
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")

    status = workspace_status(worktree)

    assert status["stage_gates"]["authoring_allowed"] is True
    assert status["stage_gates"]["integration_allowed"] is False
    assert status["stage_gates"]["accepted_closeout_allowed"] is False
    assert status["stage_gates"]["blocked_stage"] == "candidate_integration"
    assert status["stage_gates"]["blocker_owner"] == "work/feature"
    assert status["stage_gates"]["recommended_next_command"] == "ethos lane prewrite <path>"


def test_workspace_status_stage_gates_keep_authoring_open_with_foreign_lane(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    current = tmp_path / "repo-work-current"
    foreign = tmp_path / "repo-work-foreign"
    start_work_lane(root=repo, name="current", path=current, owner="agent:current", apply=True)
    start_work_lane(root=repo, name="foreign", path=foreign, owner="agent:foreign", apply=True)

    status = workspace_status(current)

    assert status["stage_gates"]["authoring_allowed"] is True
    assert status["stage_gates"]["integration_allowed"] is True
    assert status["stage_gates"]["recommended_next_command"] == "ethos land --json"


def test_workspace_status_reports_foreign_work_lanes_without_reading_them(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    foreign = tmp_path / "repo-work-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", foreign.as_posix(), "dev")

    status = workspace_status(repo)

    assert status["role"] == "accepted_root"
    assert status["foreign_work_lanes"] == [
        {
            "branch": "work/foreign",
            "head": git(repo, "rev-parse", "dev"),
            "path": foreign.as_posix(),
            "role": "work_lane",
            "worktree_binding": "linked",
            "lease_owner": "",
            "lease_state": "missing",
            "claim_id": "",
            "claim_binding": "missing",
            "dirty": False,
            "dirty_paths": [],
            "path_scope": [],
            "scope_state": "empty",
            "coordination_state": "advisory",
            "current_actor_capability": "observe",
            "allowed_actions": ["observe"],
            "forbidden_actions": ["write", "land", "retire"],
            "write_policy": "owner_only",
            "retire_policy": "owner_handoff_or_maintainer_break_glass",
            "handoff_required": True,
        }
    ]
    assert status["required_gaps"] == []
    assert status["coordination_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_missing_lease:work/foreign",
    ]
    assert status["coordination"] == {
        "kind": "work_lane_coordination",
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": [
            "foreign_work_lane_present",
            "work_lane_missing_lease:work/foreign",
        ],
        "foreign_work_lane_count": 1,
        "unbound_work_lane_count": 0,
        "unbound_work_lane_refs": [],
        "missing_lease_count": 1,
        "overlap_count": 0,
        "unknown_scope_count": 0,
        "next_action": "bind or inspect Work Lane leases before candidate integration",
        "migration_recommendations": [],
    }
    assert status["closeout_support"] == {
        "supported": False,
        "branch": "",
        "target_branch": "candidate/dev",
        "target_path": (tmp_path / "repo-candidate-dev").as_posix(),
        "operation": "",
        "owner": "",
        "claim_id": "",
        "claim_binding": "unbound",
        "required_gaps": ["protected_root_mutation"],
    }
    assert_no_ui_projection(status)


def test_workspace_status_reports_unbound_work_lane_ref_without_active_lane(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "work/stale-ref", "dev")

    status = workspace_status(repo)

    bindings = {binding["branch"]: binding for binding in status["branch_bindings"]}
    assert bindings["work/stale-ref"] == {
        "branch": "work/stale-ref",
        "role": "work_lane",
        "head": git(repo, "rev-parse", "dev"),
        "worktree_path": "",
        "worktree_binding": "unbound",
        "claim_id": "",
        "claim_binding": "missing",
    }
    assert status["foreign_work_lanes"] == []
    assert status["required_gaps"] == []
    assert status["coordination_gaps"] == ["unbound_work_lane_ref_present"]
    assert status["coordination"]["blocking"] is False
    assert status["coordination"]["foreign_work_lane_count"] == 0
    assert status["coordination"]["unbound_work_lane_count"] == 1
    assert status["coordination"]["unbound_work_lane_refs"] == [
        {
            "branch": "work/stale-ref",
            "head": git(repo, "rev-parse", "dev"),
            "claim_id": "",
            "claim_binding": "missing",
            "relation_to_accepted": "ancestor_of_accepted",
            "next_action": (
                "retire unbound Work Lane ref after confirming no external owner depends on it"
            ),
        }
    ]
    assert status["coordination"]["advisory_gaps"] == ["unbound_work_lane_ref_present"]
    assert (
        status["coordination"]["next_action"]
        == "inspect or retire unbound Work Lane refs during coordination cleanup"
    )
    assert_no_ui_projection(status)


def test_workspace_status_reports_branch_worktree_bindings_without_ui_actions(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    submit = tmp_path / "repo-submit-feature"
    git(repo, "worktree", "add", "-b", "submit/feature", submit.as_posix(), "dev")

    status = workspace_status(repo)

    assert "branch_actions" not in status
    assert status["role_policy"] == {
        "release_branch": "main",
        "accepted_branch": "dev",
        "candidate_branch": "candidate/dev",
        "work_branch_prefix": "work/",
        "submit_branch_prefix": "submit/",
        "semantic_order": [
            {
                "role": "release_root",
                "kind": "exact_branch",
                "config_key": "release_branch",
                "pattern": "main",
            },
            {
                "role": "accepted_root",
                "kind": "exact_branch",
                "config_key": "accepted_branch",
                "pattern": "dev",
            },
            {
                "role": "candidate",
                "kind": "exact_branch",
                "config_key": "candidate_branch",
                "pattern": "candidate/dev",
            },
            {
                "role": "work_lane",
                "kind": "branch_prefix",
                "config_key": "work_branch_prefix",
                "pattern": "work/*",
            },
            {
                "role": "submit_lane",
                "kind": "branch_prefix",
                "config_key": "submit_branch_prefix",
                "pattern": "submit/*",
            },
        ],
    }
    assert status["candidate"]["worktree_binding"] == "linked"
    assert status["candidate"]["worktree_path"] == candidate.as_posix()
    assert [binding["branch"] for binding in status["branch_bindings"]] == [
        "main",
        "dev",
        "candidate/dev",
        "work/feature",
        "submit/feature",
    ]
    bindings = {binding["branch"]: binding for binding in status["branch_bindings"]}
    assert bindings["main"]["role"] == "release_root"
    assert bindings["main"]["worktree_binding"] == "unbound"
    assert bindings["dev"]["worktree_binding"] == "current"
    assert bindings["dev"]["worktree_path"] == repo.as_posix()
    assert bindings["candidate/dev"]["worktree_binding"] == "linked"
    assert bindings["candidate/dev"]["worktree_path"] == candidate.as_posix()
    assert bindings["work/feature"]["worktree_binding"] == "linked"
    assert bindings["work/feature"]["worktree_path"] == worktree.as_posix()
    assert bindings["submit/feature"]["role"] == "submit_lane"
    assert bindings["submit/feature"]["worktree_binding"] == "linked"
    assert bindings["submit/feature"]["worktree_path"] == submit.as_posix()
    assert_no_ui_projection(status)


def test_workspace_status_uses_configured_branch_role_policy(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "branch", "stage/dev", "dev")

    git(repo, "checkout", "-b", "review/ready")
    assert workspace_status(repo)["role"] == "submit_lane"

    git(repo, "checkout", "dev")
    git(repo, "checkout", "-b", "lane/feature")
    assert workspace_status(repo)["role"] == "work_lane"

    git(repo, "checkout", "dev")
    status = workspace_status(repo)
    assert status["role"] == "accepted_root"
    assert status["candidate"]["branch"] == "stage/dev"
    assert status["candidate"]["exists"] is True

    git(repo, "branch", "main", "dev")
    git(repo, "checkout", "main")
    assert workspace_status(repo)["role"] == "release_root"


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
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "lane/feature"
    assert report["base"] == "stage/dev"
    assert git(worktree, "branch", "--show-current") == "lane/feature"


def test_workspace_status_reports_current_work_lane_closeout_support(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "agent:test",
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": [],
    }


def test_workspace_status_projects_work_lane_claim_binding(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        claim_id="sample-trust",
        apply=True,
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "agent:test",
        "claim_id": "sample-trust",
        "claim_binding": "bound",
        "required_gaps": [],
    }


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
        owner="agent:test",
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
    assert report["owner"] == "agent:test"
    assert report["claim_id"] == "sample-trust"
    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "agent:test",
        "claim_id": "sample-trust",
        "claim_binding": "bound",
        "required_gaps": [],
    }


def test_workspace_status_blocks_current_work_lane_when_foreign_scope_overlaps(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    first = tmp_path / "repo-work-first"
    second = tmp_path / "repo-work-second"
    start_work_lane(root=repo, name="first", path=first, owner="agent:first", apply=True)
    start_work_lane(root=repo, name="second", path=second, owner="agent:second", apply=True)

    (first / "README.md").write_text("# first\n", encoding="utf-8")
    git(first, "add", "README.md")
    git(
        first,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "first change",
    )
    (second / "README.md").write_text("# second\n", encoding="utf-8")
    git(second, "add", "README.md")
    git(
        second,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "second change",
    )

    status = workspace_status(second)

    assert status["foreign_work_lanes"][0]["branch"] == "work/first"
    assert status["foreign_work_lanes"][0]["path_scope"] == ["README.md"]
    assert status["foreign_work_lanes"][0]["scope_state"] == "bounded"
    assert status["foreign_work_lanes"][0]["coordination_state"] == "overlap"
    assert status["foreign_work_lanes"][0]["current_actor_capability"] == "observe"
    # scope_overlap is same-file-only (git's ff-only land backstops a genuine conflict),
    # so it is advisory, not blocking: concurrent lanes sharing a directory no longer
    # serialize.
    assert status["coordination"]["blocking"] is False
    assert "coordination_gap:scope_overlap:work/first" in status["coordination"]["advisory_gaps"]
    assert status["coordination"]["required_gaps"] == []
    assert status["coordination"]["overlap_count"] == 1
    assert status["closeout_support"]["supported"] is True
    assert status["closeout_support"]["required_gaps"] == []
    assert "coordination_gap:scope_overlap:work/first" not in status["required_gaps"]


def test_workspace_status_blocks_current_work_lane_when_foreign_dirty_scope_overlaps(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    first = tmp_path / "repo-work-first"
    second = tmp_path / "repo-work-second"
    start_work_lane(root=repo, name="first", path=first, owner="agent:first", apply=True)
    start_work_lane(root=repo, name="second", path=second, owner="agent:second", apply=True)

    (first / "packages").mkdir()
    (first / "packages" / "core.py").write_text("# dirty foreign\n", encoding="utf-8")
    (second / "packages").mkdir()
    (second / "packages" / "core.py").write_text("# committed current\n", encoding="utf-8")
    git(second, "add", "packages/core.py")
    git(
        second,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "second change",
    )

    status = workspace_status(second)
    lane = status["foreign_work_lanes"][0]

    assert lane["branch"] == "work/first"
    assert lane["dirty"] is True
    assert lane["dirty_paths"] == ["packages/core.py"]
    assert lane["path_scope"] == ["packages/core.py"]
    assert lane["coordination_state"] == "overlap"
    assert status["coordination"]["required_gaps"] == []
    assert "coordination_gap:scope_overlap:work/first" in status["coordination"]["advisory_gaps"]
    assert status["closeout_support"]["required_gaps"] == []


def test_workspace_status_blocks_raw_work_lane_without_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-raw"
    git(repo, "worktree", "add", "-b", "work/raw", worktree.as_posix(), "dev")

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/raw",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "",
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/raw"],
    }
    assert status["required_gaps"] == ["work_lane_missing_lease:work/raw"]


def test_workspace_status_reports_current_work_lane_closeout_gaps(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")

    status = workspace_status(worktree)

    assert status["closeout_support"]["supported"] is False
    assert status["closeout_support"]["operation"] == "land_to_candidate"
    assert status["closeout_support"]["required_gaps"] == ["work_lane_dirty"]


def test_workspace_status_reports_closeout_owner_from_lane_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )
    status = workspace_status(worktree)

    assert report["ok"] is True
    assert status["closeout_support"]["owner"] == "agent:test"


def test_workspace_status_ignores_retired_state_lease_schema(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    state_db = repo / ".ethos" / "state" / "state.sqlite"
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    with closing(sqlite3.connect(state_db)) as connection:
        connection.execute(
            """
            create table leases (
              id text primary key,
              owner text not null default '',
              resource text not null default '',
              expires_at text not null default '',
              created_at text not null
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, resource, expires_at, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                "lease:retired",
                "agent:retired",
                "work/retired",
                expires_at.isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )

    status = workspace_status(repo)
    leases = active_leases(state_db)

    assert status["role"] == "accepted_root"
    assert leases == []


def test_workspace_status_output_validates_against_workspace_status_schema(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")

    validation = validate_schema_instance("workspace-status.schema.json", workspace_status(repo))

    assert validation["ok"] is True
    assert validation["required_gaps"] == []


def test_workspace_status_schema_rejects_ui_projection_fields(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    payload = workspace_status(repo)
    payload["candidate"]["open_action"] = "open_worktree"
    payload["candidate"]["open_label"] = "host-specific label"

    validation = validate_schema_instance("workspace-status.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_workspace_status_reports_missing_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    status = workspace_status(repo)

    assert status["candidate"] == {
        "branch": "candidate/dev",
        "exists": False,
        "head": "",
        "worktree_exists": False,
        "worktree_path": "",
        "worktree_binding": "absent",
        "behind_accepted": 0,
    }
    assert "candidate_branch_missing" in status["required_gaps"]


def test_workspace_status_reports_candidate_branch_without_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev", "dev")

    status = workspace_status(repo)

    assert status["candidate"]["exists"] is True
    assert status["candidate"]["worktree_exists"] is False
    assert status["candidate"]["worktree_path"] == ""
    assert "candidate_worktree_missing" in status["required_gaps"]


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


def test_prewrite_allows_owned_work_lane_with_matching_editor_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")

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
    monkeypatch.setattr("ethos.adapters.repo.status.ethos.__file__", external_runner.as_posix())

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


def test_prewrite_rejects_work_lane_without_editor_root_binding(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")

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


def test_start_work_lane_apply_creates_worktree_and_records_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
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
    assert [(lease["subject"], lease["owner"]) for lease in leases] == [
        ("work/feature", "agent:test")
    ]


def test_start_work_lane_apply_requires_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
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
        owner="agent:test",
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
        owner="agent:test",
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
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is True
    assert git(worktree, "rev-parse", "HEAD") == candidate_head
    assert git(repo, "rev-parse", "dev") != candidate_head


def test_refresh_work_lane_base_plans_stale_candidate_base(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "candidate/dev")
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
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "candidate/dev")
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


def test_refresh_work_lane_base_apply_requires_authorization_and_expected_head(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "candidate/dev")
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
    git(repo, "worktree", "add", "-b", "work/current", current_worktree.as_posix(), "dev")

    report = start_work_lane(
        root=current_worktree,
        name="nested",
        path=new_worktree,
        owner="agent:test",
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
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["dirty"] is True
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not worktree.exists()


def test_workspace_status_reports_runtime_binding_for_audited_checkout(tmp_path: Path) -> None:
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

    monkeypatch.setattr("ethos.adapters.repo.status.ethos.__file__", external_runner.as_posix())

    status = workspace_status(repo)

    binding = status["runtime_binding"]
    assert binding["state"] == "external_current_runner"
    assert binding["runner_matches_audit_root"] is False
    assert "workspace_status_runner_source_differs_from_audit_root" in binding["advisory_gaps"]
    assert "package-bound runner" in binding["next_action"]


def test_workspace_status_reports_landing_readiness_for_current_work_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(root=repo, name="feature", path=worktree, owner="agent:test", apply=True)

    status = workspace_status(worktree)

    readiness = status["landing_readiness"]
    assert readiness["kind"] == "landing_readiness"
    assert readiness["state"] == "candidate_base_current"
    assert readiness["branch"] == "work/feature"
    assert readiness["head"] == git(worktree, "rev-parse", "HEAD")
    assert readiness["candidate_branch"] == "candidate/dev"
    assert readiness["candidate_head"] == git(candidate, "rev-parse", "HEAD")
    assert readiness["required_gaps"] == []
    assert readiness["next_action"] == "ethos land --json"
    assert status["stage_gates"]["integration_allowed"] is True
    assert status["stage_gates"]["recommended_next_command"] == "ethos land --json"


def test_workspace_status_reports_stale_landing_readiness_before_land(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(root=repo, name="feature", path=worktree, owner="agent:test", apply=True)
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

    status = workspace_status(worktree)

    readiness = status["landing_readiness"]
    assert readiness["state"] == "candidate_base_stale"
    assert readiness["head"] == work_head
    assert readiness["candidate_head"] == candidate_head
    assert readiness["required_gaps"] == ["candidate_base_stale"]
    assert readiness["next_action"] == (
        f"ethos lane refresh-base --apply --authorize --expect-head {work_head} --json"
    )
    assert status["stage_gates"]["authoring_allowed"] is True
    assert status["stage_gates"]["integration_allowed"] is False
    assert status["stage_gates"]["blocked_stage"] == "candidate_integration"
    assert status["stage_gates"]["blocker_owner"] == "candidate/dev"
    assert status["stage_gates"]["recommended_next_command"] == readiness["next_action"]
    assert status["stage_gates"]["next_commands"] == [
        "ethos lane prewrite <path>",
        readiness["next_action"],
    ]
