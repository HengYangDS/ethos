from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.status.core import workspace_status
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import assert_no_ui_projection
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import write_role_policy

if TYPE_CHECKING:
    from pathlib import Path


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
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

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
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
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
    start_work_lane(
        root=repo,
        name="current",
        path=current,
        holder_ref="agent:test:case:agent-current",
        apply=True,
    )
    start_work_lane(
        root=repo,
        name="foreign",
        path=foreign,
        holder_ref="agent:test:case:agent-foreign",
        apply=True,
    )

    status = workspace_status(current)

    assert status["stage_gates"]["authoring_allowed"] is True
    assert status["stage_gates"]["integration_allowed"] is True
    assert status["stage_gates"]["recommended_next_command"] == "ethos land --json"


def test_workspace_status_reports_missing_foreign_worktree_without_crashing(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    foreign = tmp_path / "repo-work-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", foreign.as_posix(), "dev")
    git(repo, "worktree", "lock", foreign.as_posix(), "--reason", "simulate stale registry")
    # Simulate a concurrent host or agent removing the physical worktree while
    # Git's registry still advertises it. ETHOS must surface the lane as
    # unobservable, not crash closeout/status readers.
    shutil.rmtree(foreign)

    status = workspace_status(repo)
    lane = status["foreign_work_lanes"][0]

    assert lane["branch"] == "work/foreign"
    assert lane["worktree_binding"] == "missing"
    assert lane["dirty"] is False
    assert lane["dirty_paths"] == []
    assert lane["scope_state"] == "empty"
    assert lane["coordination_state"] == "advisory"
    assert status["coordination"]["blocking"] is False
    assert status["required_gaps"] == []
    assert validate_schema_instance("workspace-status.schema.json", status)["ok"] is True


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
            "lease": {
                "lane_incarnation_id": "",
                "lease_id": "",
                "holder_ref": "",
                "epoch": 0,
                "expected_head": "",
                "expires_at": "",
                "normalization_state": "legacy_ambiguous",
                "mints_authority": False,
            },
            "lease_state": "missing",
            "claim_id": "",
            "claim_binding": "missing",
            "relation_to_accepted": "ancestor_of_accepted",
            "closeout_disposition": "none",
            "residue_state": "clean_or_none",
            "next_action": "observe lane state; use owner-bound lifecycle command when ready",
            "dirty": False,
            "dirty_paths": [],
            "path_scope": [],
            "scope_state": "empty",
            "coordination_state": "advisory",
            "action_preview": {
                "candidate_actions": ["observe"],
                "blocked_actions": ["write", "land", "retire"],
                "why": ["foreign_lane_requires_handoff_or_accepted_decision"],
                "mints_authority": False,
                "recheck_required": True,
            },
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
        "invalid_states": {
            "categories": {
                "change_unbounded": [
                    "foreign_work_lane_present",
                    "work_lane_missing_lease:work/foreign",
                ]
            },
            "category_count": 1,
            "gap_count": 2,
        },
        "foreign_work_lane_count": 1,
        "unbound_work_lane_count": 0,
        "unbound_work_lane_refs": [],
        "missing_lease_count": 1,
        "overlap_count": 0,
        "unknown_scope_count": 0,
        "closeout_residue_count": 0,
        "dirty_closeout_residue_count": 0,
        "closeout_residue_lanes": [],
        "next_action": "bind or inspect Work Lane leases before candidate integration",
        "migration_recommendations": [],
    }
    assert status["closeout_support"] == {
        "supported": False,
        "branch": "",
        "target_branch": "candidate/dev",
        "target_path": (tmp_path / "repo-candidate-dev").as_posix(),
        "operation": "",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "unbound",
        "required_gaps": ["protected_root_mutation"],
    }
    assert_no_ui_projection(status)


def test_workspace_status_explains_landed_dirty_lane_preservation_path(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        claim_id="sample-claim",
        apply=True,
    )
    (worktree / "README.md").write_text("# unpreserved residue\n", encoding="utf-8")

    status = workspace_status(repo)

    lane = status["foreign_work_lanes"][0]
    assert lane["closeout_disposition"] == "landed_dirty"
    assert lane["residue_state"] == "unpreserved_worktree_delta"
    assert lane["next_action"] == (
        "owner must preserve or intentionally discard dirty worktree delta before retirement"
    )
    assert "ethos lane retire landed" not in lane["next_action"]
    assert status["coordination_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_closeout_residue_present",
    ]


def test_workspace_status_calls_claim_bound_landed_lane_retire_ready(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        claim_id="sample-claim",
        apply=True,
    )

    status = workspace_status(repo)

    lane = status["foreign_work_lanes"][0]
    assert lane["relation_to_accepted"] == "ancestor_of_accepted"
    assert lane["lease_state"] == "leased"
    assert lane["claim_binding"] == "bound"
    assert lane["closeout_disposition"] == "retire_ready"
    assert lane["next_action"] == (
        "retire clean absorbed Work Lane with "
        "ethos lane retire landed --branch work/feature "
        f"--expect-head {lane['head']} --apply --json"
    )
    assert status["coordination_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_closeout_residue_present",
    ]
    assert status["coordination"]["advisory_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_closeout_residue_present",
    ]


def test_ref_relation_reports_unknown_when_ref_is_missing(tmp_path: Path) -> None:
    from ethos.adapters.repo.status.bindings import ref_relation

    repo = init_repo(tmp_path / "repo")

    assert ref_relation(repo, "work/missing", "dev") == "unknown"


def test_closeout_disposition_classifier_is_mece() -> None:
    from ethos.adapters.repo.coordination import closeout_disposition

    assert (
        closeout_disposition(
            lease_state="leased",
            claim_binding="bound",
            relation_to_accepted="ancestor_of_accepted",
            dirty=False,
        )
        == "retire_ready"
    )
    assert (
        closeout_disposition(
            lease_state="leased",
            claim_binding="missing",
            relation_to_accepted="ancestor_of_accepted",
            dirty=False,
        )
        == "none"
    )
    assert (
        closeout_disposition(
            lease_state="missing",
            claim_binding="missing",
            relation_to_accepted="ancestor_of_accepted",
            dirty=False,
        )
        == "none"
    )
    assert (
        closeout_disposition(
            lease_state="leased",
            claim_binding="bound",
            relation_to_accepted="ancestor_of_accepted",
            dirty=True,
        )
        == "landed_dirty"
    )
    assert (
        closeout_disposition(
            lease_state="leased",
            claim_binding="bound",
            relation_to_accepted="descendant_of_accepted",
            dirty=False,
        )
        == "unlanded"
    )
    assert (
        closeout_disposition(
            lease_state="leased",
            claim_binding="bound",
            relation_to_accepted="diverged_from_accepted",
            dirty=False,
        )
        == "diverged"
    )
    assert (
        closeout_disposition(
            lease_state="leased",
            claim_binding="bound",
            relation_to_accepted="unknown",
            dirty=False,
        )
        == "unknown"
    )


def test_workspace_status_does_not_call_fresh_empty_leased_lane_retire_ready(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    status = workspace_status(repo)

    assert status["foreign_work_lanes"][0]["relation_to_accepted"] == "ancestor_of_accepted"
    assert status["foreign_work_lanes"][0]["lease_state"] == "leased"
    assert status["foreign_work_lanes"][0]["closeout_disposition"] == "none"
    assert status["coordination_gaps"] == ["foreign_work_lane_present"]
    assert status["coordination"]["advisory_gaps"] == ["foreign_work_lane_present"]


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


def test_workspace_status_reports_branchworktree_bindings_without_ui_actions(
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
        "release_mirror": "independent",
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


def test_workspace_status_reports_current_work_lanecloseout_support(tmp_path: Path) -> None:
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

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "agent:test:case:agent-test",
        "lease_id": status["closeout_support"]["lease_id"],
        "lease_epoch": 1,
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
        holder_ref="agent:test:case:agent-test",
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
        "holder_ref": "agent:test:case:agent-test",
        "lease_id": status["closeout_support"]["lease_id"],
        "lease_epoch": 1,
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
    start_work_lane(
        root=repo,
        name="first",
        path=first,
        holder_ref="agent:test:case:agent-first",
        apply=True,
    )
    start_work_lane(
        root=repo,
        name="second",
        path=second,
        holder_ref="agent:test:case:agent-second",
        apply=True,
    )

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
    assert status["foreign_work_lanes"][0]["action_preview"] == {
        "candidate_actions": ["observe"],
        "blocked_actions": ["write", "land", "retire"],
        "why": ["foreign_lane_requires_handoff_or_accepted_decision"],
        "mints_authority": False,
        "recheck_required": True,
    }
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
    start_work_lane(
        root=repo,
        name="first",
        path=first,
        holder_ref="agent:test:case:agent-first",
        apply=True,
    )
    start_work_lane(
        root=repo,
        name="second",
        path=second,
        holder_ref="agent:test:case:agent-second",
        apply=True,
    )

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
    assert validate_schema_instance("workspace-status.schema.json", status)["ok"] is True


def test_workspace_status_reports_candidate_branch_without_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev", "dev")

    status = workspace_status(repo)

    assert status["candidate"]["exists"] is True
    assert status["candidate"]["worktree_exists"] is False
    assert status["candidate"]["worktree_path"] == ""
    assert status["candidate"]["worktree_binding"] == "unbound"
    assert "candidate_worktree_missing" in status["required_gaps"]
    assert validate_schema_instance("workspace-status.schema.json", status)["ok"] is True


def test_workspace_status_reports_missing_candidate_registry_worktree_without_crashing(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "worktree", "lock", candidate.as_posix(), "--reason", "simulate stale registry")

    shutil.rmtree(candidate)

    status = workspace_status(repo)

    assert status["candidate"]["exists"] is True
    assert status["candidate"]["worktree_exists"] is False
    assert status["candidate"]["worktree_path"] == candidate.as_posix()
    assert status["candidate"]["worktree_binding"] == "missing"
    assert "candidate_worktree_missing" in status["required_gaps"]
    assert validate_schema_instance("workspace-status.schema.json", status)["ok"] is True


def test_workspace_status_reports_landing_readiness_for_current_work_lane(tmp_path: Path) -> None:
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
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
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
