from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.unit.cli.test_contracts import git
from tests.unit.cli.test_contracts import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_orient_json_is_projection_not_truth_store() -> None:
    payload = run_ethos("orient", "--json")

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
    }
    assert orientation["runtime_binding"]["state"]
    assert isinstance(orientation["runtime_binding"]["advisory_items"], list)
    assert payload["summary"]["role"] == orientation["where"]["role"]
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


def test_orient_human_output_is_concise_and_actionable() -> None:
    completed = run_ethos_raw("orient")

    assert completed.returncode == 0
    lines = completed.stdout.splitlines()
    assert 4 <= len(lines) <= 7
    assert lines[0].startswith(("ready:", "dirty:", "gapped:"))
    where_line = next(line for line in lines if line.startswith("where:"))
    json_payload = run_ethos("orient", "--json")
    head = json_payload["data"]["orientation"]["where"]["head"]
    assert f"@ {head[:12]}" in where_line
    assert any(line.startswith("can:") for line in lines)
    assert any(line.startswith("next:") for line in lines)


def test_orient_reports_current_head_from_status_branch_binding() -> None:
    payload = run_ethos("orient", "--json")
    status = run_ethos("status", "--json")

    orientation = payload["data"]["orientation"]
    branch = status["data"]["branch"]
    binding = next(item for item in status["data"]["branch_bindings"] if item["branch"] == branch)
    assert orientation["where"]["head"] == binding["head"]
    assert orientation["where"]["head"]
