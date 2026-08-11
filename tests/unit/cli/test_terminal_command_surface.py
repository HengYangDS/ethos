"""Terminal command-plane regression coverage."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from typing import get_type_hints

import pytest

from ethos.adapters.mutation.proof_artifacts import persist_attestation
from ethos.contracts.semantic import Attestation
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups
from ethos.surface.cli.lane.lease import TakeoverOptions
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.literal_cases import literal_case

PUBLIC_ROOT_COMMANDS = literal_case(
    "cli.test_terminal_command_surface:assign:PUBLIC_ROOT_COMMANDS:0"
)
RETIRED_ROOT_COMMANDS = literal_case(
    "cli.test_terminal_command_surface:assign:RETIRED_ROOT_COMMANDS:1"
)


def test_registered_command_roots_are_exactly_the_terminal_surface() -> None:
    load_command_groups([])
    registered = {command for command in app.resolved_commands() if not command.startswith("-")}

    assert registered == {*PUBLIC_ROOT_COMMANDS, "lane", "hook"}


def test_bare_help_loads_the_terminal_root_surface() -> None:
    completed = run_ethos_raw("--help")

    assert completed.returncode == 0, completed.stderr
    for command in PUBLIC_ROOT_COMMANDS:
        assert command in completed.stdout


def test_takeover_is_a_public_generation_bound_lease_command() -> None:
    completed = run_ethos_raw("lane", "lease", "takeover", "--help")

    assert completed.returncode == 0, completed.stderr
    for option in (
        "--authorization",
        "--source-state",
        "--dirty-content-sha256",
        "--lane-incarnation-id",
        "--expect-tree",
    ):
        assert option in completed.stdout


def test_takeover_runtime_annotations_are_fully_resolvable() -> None:
    annotations = get_type_hints(TakeoverOptions)

    assert annotations["authorization"]


def test_lane_status_shared_inbox_is_schema_validated(tmp_path) -> None:
    fixture = start_adopted_work_lane(
        tmp_path / "shared-inbox-status",
        name="shared-inbox-status",
        holder_ref="agent:test:case:owner",
    )

    payload = run_ethos("lane", "status", "--json", cwd=fixture.worktree)
    inbox = payload["data"]["shared_inbox"]
    assert inbox["state"] == "open"
    assert inbox["item_count"] == len(inbox["items"])
    assert all("workspace_status_schema" not in gap for gap in payload["required_gaps"])


@pytest.mark.parametrize("command", RETIRED_ROOT_COMMANDS)
def test_retired_root_commands_are_not_registered(command: str) -> None:
    completed = run_ethos_raw(command)

    assert completed.returncode != 0
    assert "Unknown command" in f"{completed.stdout}{completed.stderr}"


@pytest.mark.parametrize(
    ("arguments", "native_error"),
    literal_case(
        "cli.test_terminal_command_surface:parametrize:test_retired_claim_lane_surface_is_rejected_by_cyclopts:2"
    ),
)
def test_retired_claim_lane_surface_is_rejected_by_cyclopts(
    arguments: tuple[str, ...],
    native_error: str,
) -> None:
    completed = run_ethos_raw(*arguments)

    assert completed.returncode != 0
    output = f"{completed.stdout}{completed.stderr}"
    assert native_error in output


@pytest.mark.parametrize("command", ["decide", "apply", "inventory", "clear"])
def test_retired_lane_resolution_surface_is_rejected_by_cyclopts(command: str) -> None:
    completed = run_ethos_raw("lane", "resolution", command)

    assert completed.returncode != 0
    assert "Unknown command" in f"{completed.stdout}{completed.stderr}"


def test_archive_change_rejects_the_retired_history_rebuild_option() -> None:
    completed = run_ethos_raw(
        "lane",
        "archive-change",
        "--change",
        "sample-change",
        "--expect-head",
        "a" * 40,
        "--rebuild-from",
        "b" * 40,
    )

    assert completed.returncode != 0
    assert "Unknown option" in f"{completed.stdout}{completed.stderr}"


def test_status_uses_stage_gate_actions_when_dirty_lane_base_is_stale(tmp_path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")
    completed = run_ethos_raw("status", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    refresh_base = (
        "ethos lane refresh-base --apply --authorize "
        f"--expect-head {payload['data']['head']} --json"
    )
    expected = [
        "ethos lane prewrite <path>",
        refresh_base,
    ]
    assert payload["verdict"] == "block"
    assert "ok" not in payload
    assert "ok" not in payload["data"]
    assert payload["required_gaps"] == ["candidate_base_stale"]
    assert payload["next_action"] == expected[-1]
    assert payload["next_action"] == payload["data"]["authority"]["next_action"]
    assert payload["user_decision_required"] is True
    assert payload["continuation"] == "await-user"
    assert "git status --short" not in payload["next_action"]


def test_lane_status_exposes_observations_without_closeout_residue_plane(tmp_path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    payload = run_ethos(
        "lane",
        "status",
        "--root",
        fixture.worktree.as_posix(),
        "--json",
        cwd=fixture.worktree,
    )

    serialized = json.dumps(payload)
    assert "ok" not in payload
    assert "ok" not in payload["data"]
    assert payload["data"]["verdict"] == payload["verdict"]
    for retired in (
        "closeout_disposition",
        "residue_state",
        "closeout_residue_count",
        "dirty_closeout_residue_count",
        "closeout_residue_lanes",
    ):
        assert retired not in serialized
    assert payload["next_action"] == payload["data"]["stage_gates"]["next_action"]


def test_lane_status_rebuilds_shared_inbox_from_facts_and_attestations(tmp_path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    first = run_ethos(
        "lane", "status", "--root", fixture.repository.as_posix(), "--json", cwd=fixture.repository
    )
    inbox = first["data"]["shared_inbox"]
    item = next(item for item in inbox["items"] if item["claim"] == "foreign_work_lane_present")
    digest = str(item["digest"])
    issued = datetime.now(UTC)
    persist_attestation(
        fixture.repository,
        Attestation.issue(
            {
                "predicate": "inbox:acknowledged",
                "verifier": "agent:test:case:reader",
                "subject": f"inbox:item:{digest}",
                "issued_at": issued,
                "verdict": "pass",
                "evidence_refs": (f"inbox:item:{digest}",),
                "statement": {"actor": "agent:test:case:reader", "item_digest": digest},
            }
        ),
    )

    rebuilt = run_ethos(
        "lane", "status", "--root", fixture.repository.as_posix(), "--json", cwd=fixture.repository
    )["data"]["shared_inbox"]
    observed = next(item for item in rebuilt["items"] if item["digest"] == digest)
    assert observed["acknowledged_by"] == ["agent:test:case:reader"]
    assert observed["consumed_by"] == []
