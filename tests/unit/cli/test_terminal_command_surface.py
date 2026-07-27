"""Terminal command-plane regression coverage."""

from __future__ import annotations

import pytest

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
    from ethos.surface.cli.application import app
    from ethos.surface.cli.application import load_command_groups

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
