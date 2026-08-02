"""Terminal command-plane regression coverage."""

from __future__ import annotations

import json

import pytest

from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import start_adopted_work_lane
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw

PUBLIC_ROOT_COMMANDS = ("status", "plan", "prove", "land", "publish", "adopt")
RETIRED_ROOT_COMMANDS = (
    "orient",
    "report",
    "doctor",
    "explain",
    "docs",
    "audit",
    "openspec",
    "fleet",
    "intake",
    "rules",
    "assistants",
    "campaign",
    "parity",
    "quality",
    "playbooks",
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


@pytest.mark.parametrize("command", RETIRED_ROOT_COMMANDS)
def test_retired_root_commands_are_not_registered(command: str) -> None:
    completed = run_ethos_raw(command)

    assert completed.returncode != 0
    assert "Unknown command" in f"{completed.stdout}{completed.stderr}"


@pytest.mark.parametrize(
    ("arguments", "native_error"),
    [
        (("lane", "bind-claim", "--claim-id=retired"), "Unknown command"),
        (
            (
                "lane",
                "start",
                "feature",
                "--holder-ref",
                "agent:test:case:holder",
                "--claim-id=retired",
            ),
            "Unknown option",
        ),
    ],
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


def test_status_uses_stage_gate_actions_when_dirty_lane_base_is_stale(tmp_path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")
    completed = run_ethos_raw("status", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    expected = [
        "ethos lane prewrite <path>",
        f"ethos lane refresh-base --apply --authorize --expect-head {payload['data']['head']} --json",
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
