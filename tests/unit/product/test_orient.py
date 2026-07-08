from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.domain.orient import human_orientation_lines
from ethos.domain.orient import orientation_packet
from tests.support.ethos_cli_runner import run_ethos
from tests.unit.cli.test_contracts import git
from tests.unit.cli.test_contracts import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_orient_json_is_projection_not_truth_store() -> None:
    payload = run_ethos("orient", "--json")
    status = run_ethos("status", "--json")

    assert payload["command"] == "orient"
    assert payload["state"] == "oriented"
    orientation = payload["data"]["orientation"]
    assert orientation["kind"] == "orientation"
    assert orientation["truth_boundary"] == "repository-reader-view"
    assert orientation["mints_truth"] is False
    assert orientation["source_payloads"] == ["status", "report"]
    assert orientation["agent_hints"] == {
        "mutation_requires_prewrite": True,
        "foreign_lanes_observe_only": bool(orientation["coordination"]["foreign_work_lanes"]),
        "use_json_for_evidence": True,
        "orientation_projection_only": True,
        "runner_binding_visible": True,
        "landing_readiness_visible": True,
    }
    assert orientation["runtime_binding"]["state"]
    assert orientation["landing_readiness"]["state"]
    assert isinstance(orientation["runtime_binding"]["advisory_items"], list)
    assert (
        orientation["readiness"]["advisory_gap_count"] == payload["summary"]["advisory_gap_count"]
    )
    assert isinstance(orientation["readiness"]["advisory_items"], list)
    assert isinstance(orientation["readiness"]["advisory_next_actions"], list)
    for action in orientation["readiness"]["advisory_next_actions"]:
        assert action in orientation["next_actions"]
    assert payload["summary"]["role"] == orientation["where"]["role"]
    assert (
        payload["summary"]["foreign_work_lane_count"]
        == orientation["coordination"]["foreign_work_lane_count"]
    )
    assert (
        payload["summary"]["unbound_work_lane_count"]
        == orientation["coordination"]["unbound_work_lane_count"]
    )
    assert payload["summary"]["coordination_blocking"] == orientation["coordination"]["blocking"]
    assert (
        orientation["coordination"]["next_action"] == status["data"]["coordination"]["next_action"]
    )
    assert payload["next_actions"] == orientation["next_actions"]


def test_status_json_keeps_workspace_status_pure() -> None:
    payload = run_ethos("status", "--json")

    assert payload["command"] == "status"
    assert "dirty_provenance" in payload["data"]
    assert "foreign_work_lanes" in payload["data"]
    assert "orientation" not in payload["data"]
    assert payload["diagnostics"] == [
        {
            "kind": "schema_validation",
            "target": "data",
            "schema": "workspace-status.schema.json",
            "ok": True,
            "required_gaps": [],
        }
    ]
    summary = payload["summary"]
    data = payload["data"]
    coordination = data["coordination"]
    assert summary["role"] == data["role"]
    assert summary["dirty"] == data["dirty"]
    assert summary["foreign_work_lane_count"] == coordination["foreign_work_lane_count"]
    assert summary["unbound_work_lane_count"] == coordination["unbound_work_lane_count"]
    assert summary["coordination_blocking"] == coordination["blocking"]


def test_orient_makes_foreign_lane_observe_only_capability_discoverable(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "worktree", "add", "-b", "candidate/dev", (tmp_path / "candidate").as_posix(), "dev")
    worktree = tmp_path / "feature"
    run_ethos(
        "lane",
        "start",
        "feature",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--apply",
        "--json",
        cwd=repo,
    )

    payload = run_ethos("orient", "--root", repo.as_posix(), "--json", cwd=repo)

    coordination = payload["data"]["orientation"]["coordination"]
    assert coordination["foreign_work_lane_count"] == 1
    lane = coordination["foreign_work_lanes"][0]
    assert lane["branch"] == "work/feature"
    assert lane["current_actor_capability"] == "observe"
    assert lane["allowed_actions"] == ["observe"]
    assert lane["forbidden_actions"] == ["write", "land", "retire"]
    assert payload["data"]["orientation"]["agent_hints"]["foreign_lanes_observe_only"] is True


def test_orient_makes_unbound_work_lane_refs_discoverable_without_authority(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "worktree", "add", "-b", "candidate/dev", (tmp_path / "candidate").as_posix(), "dev")
    git(repo, "branch", "work/stale-ref", "dev")

    payload = run_ethos("orient", "--root", repo.as_posix(), "--json", cwd=repo)
    status = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    orientation = payload["data"]["orientation"]
    coordination = orientation["coordination"]
    assert coordination["foreign_work_lane_count"] == 0
    assert coordination["foreign_work_lanes"] == []
    assert coordination["unbound_work_lane_count"] == 1
    assert coordination["unbound_work_lane_refs"] == [
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
    assert orientation["capability"]["current_actor_capability"] == "observe"
    assert orientation["capability"]["can_mutate_tracked_files"] is False
    assert "unbound ref(s) visible" in orientation["human_summary"]
    assert status["summary"]["unbound_work_lane_count"] == 1
    assert status["summary"]["coordination_blocking"] is False
    assert (
        status["summary"]["unbound_work_lane_count"]
        == status["data"]["coordination"]["unbound_work_lane_count"]
    )


def test_orient_projects_advisory_signals_from_report_fixture() -> None:
    gap = (
        "openspec_protected_branch_active_change_unarchived:"
        "main:release_root:ethos-release-hardening"
    )
    action = "git ls-tree -r --name-only main -- openspec/changes/ethos-release-hardening"
    packet = orientation_packet(
        status_payload={
            "root": "/repo",
            "branch": "dev",
            "role": "accepted_root",
            "head": "abcdef1234567890",
            "dirty": False,
            "changed_paths": [],
            "required_gaps": [],
            "closeout_support": {},
            "coordination": {
                "blocking": False,
                "foreign_work_lane_count": 0,
                "unbound_work_lane_count": 0,
                "overlap_count": 0,
                "advisory_gaps": [],
                "required_gaps": [],
                "next_action": "",
                "unbound_work_lane_refs": [],
            },
            "candidate": {},
            "runtime_binding": {"state": "bound", "advisory_gaps": []},
            "landing_readiness": {"state": "not_work_lane", "required_gaps": []},
            "foreign_work_lanes": [],
        },
        report_payload={
            "summary": {
                "score": 16,
                "max_score": 16,
                "governance_gap_count": 0,
                "parity_pending_count": 0,
                "advisory_gap_count": 1,
            },
            "required_gaps": [],
            "data": {
                "gap_layers": {
                    "advisory_signals": {
                        "advisory_gaps": [gap],
                        "next_actions": [action],
                    }
                }
            },
        },
    )

    assert packet["readiness"]["advisory_items"] == [gap]
    assert packet["readiness"]["advisory_next_actions"] == [action]
    assert action in packet["next_actions"]
    assert "1 advisory signal(s)" in packet["human_summary"]
    assert "advisory signals 1" in "\n".join(human_orientation_lines(packet))


def test_orient_human_output_is_concise_and_actionable() -> None:
    json_payload = run_ethos("orient", "--json")
    orientation = json_payload["data"]["orientation"]

    lines = list(human_orientation_lines(orientation))
    assert 4 <= len(lines) <= 8
    assert lines[0].startswith(("ready:", "dirty:", "gapped:"))
    where_line = next(line for line in lines if line.startswith("where:"))
    head = orientation["where"]["head"]
    assert f"@ {head[:12]}" in where_line
    assert any(line.startswith("can:") for line in lines)
    coordination_lines = [line for line in lines if line.startswith("coordination:")]
    assert len(coordination_lines) <= 1
    if coordination_lines:
        assert orientation["coordination"]["next_action"] in coordination_lines[0]
    assert any(line.startswith("next:") for line in lines)


def test_orient_reports_current_head_from_status_branch_binding() -> None:
    payload = run_ethos("orient", "--json")
    status = run_ethos("status", "--json")

    orientation = payload["data"]["orientation"]
    # orient's head is the repository HEAD status reports at the top level — coherent
    # whether attached or detached (GitLab CI checks HEAD out detached, so head must not
    # depend on a branch binding existing).
    assert orientation["where"]["head"] == status["data"]["head"]
    assert orientation["where"]["head"]
    # When on a branch, that head must also agree with the branch's binding.
    branch = status["data"]["branch"]
    binding = next(
        (item for item in status["data"]["branch_bindings"] if item["branch"] == branch),
        None,
    )
    if binding is not None:
        assert orientation["where"]["head"] == binding["head"]


def _orientation_line_packet(**overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "human_summary": "ready: custom",
        "where": {
            "role": "work_lane",
            "branch": "work/demo",
            "head": "abcdef1234567890",
            "changed_path_count": 0,
        },
        "capability": {
            "current_actor_capability": "write_lane",
            "reason": "owned Work Lane; run prewrite before tracked mutation",
        },
        "readiness": {
            "max_score": 16,
            "score": 16,
            "governance_gap_count": 0,
            "parity_pending_count": 0,
            "advisory_gap_count": 0,
            "advisory_items": [],
        },
        "runtime_binding": {"advisory_items": []},
        "landing_readiness": {"required_items": []},
        "coordination": {
            "foreign_work_lane_count": 0,
            "unbound_work_lane_count": 0,
            "blocking": False,
            "required_items": [],
            "next_action": "",
        },
        "next_actions": [],
    }
    packet.update(overrides)
    return packet


def test_human_orientation_lines_renders_status_only_runtime_landing_and_no_coordination() -> None:
    from ethos.domain.orient import human_orientation_lines

    lines = human_orientation_lines(
        _orientation_line_packet(
            where={
                "role": "submit_lane",
                "branch": "submit/demo",
                "head": "abcdef1234567890",
                "changed_path_count": 0,
            },
            capability={
                "current_actor_capability": "observe",
                "reason": "checkout role is not admitted for mutation",
            },
            readiness={"max_score": 0},
            runtime_binding={
                "state": "degraded",
                "advisory_items": ["runner_mismatch"],
                "next_action": "align runner and audit root",
            },
            landing_readiness={
                "state": "blocked",
                "required_items": ["candidate_not_current"],
                "next_action": "refresh candidate base",
            },
        )
    )

    assert "readiness: status-only view; run ethos report --json for scorecard" in lines
    assert "runtime: degraded; align runner and audit root" in lines
    assert "landing: blocked; refresh candidate base" in lines
    assert not any(line.startswith("coordination:") for line in lines)
    assert not any(line.startswith("next:") for line in lines)


def test_human_orientation_lines_marks_blocking_coordination_without_next_action() -> None:
    from ethos.domain.orient import human_orientation_lines

    lines = human_orientation_lines(
        _orientation_line_packet(
            where={"role": "work_lane", "branch": "work/demo", "head": "", "changed_path_count": 2},
            readiness={
                "max_score": 16,
                "score": 12,
                "governance_gap_count": 2,
                "parity_pending_count": 1,
            },
            coordination={
                "foreign_work_lane_count": 2,
                "unbound_work_lane_count": 1,
                "blocking": True,
                "required_items": ["scope_overlap"],
                "next_action": "",
            },
            next_actions=["ethos explain scope_overlap --json", "ethos report --json"],
        )
    )

    assert "where: work_lane on work/demo (2 changed paths)" in lines
    assert "readiness: score 12/16, governance gaps 2, parity pending 1" in lines
    assert "coordination: 2 foreign lane(s), 1 unbound ref(s), blocking" in lines
    assert lines[-1] == "next: ethos explain scope_overlap --json | ethos report --json"
