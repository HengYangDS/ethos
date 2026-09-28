"""Project human-readable decisions and treat closed output pipes as terminal."""

from __future__ import annotations

import sys

import pytest

import ethos.surface.cli.output as output
from ethos.result import EthosResult


def test_human_output_projects_state_next_action_and_enforcement(capsys) -> None:
    result = EthosResult(
        command="plan",
        verdict="block",
        state="gapped",
        required_gaps=("repository_invalid",),
        next_action="repair the repository",
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "plan: gapped\nwhy: repository invalid\nnext: repair the repository\n"
    )
    with pytest.raises(SystemExit, match="1"):
        output.emit(result, json_output=False)


def test_human_output_exposes_every_blocker_and_decision_boundary(capsys) -> None:
    result = EthosResult(
        command="prove",
        verdict="block",
        state="gapped",
        required_gaps=(
            "openspec_active_change_ambiguous:greenfield-formation,installed-product",
            "required_tool_unavailable",
        ),
        next_action="openspec list --json",
        user_decision_required=True,
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "prove: gapped\n"
        "why: openspec active change ambiguous: greenfield-formation,installed-product\n"
        "why: required tool unavailable\n"
        "decision: human choice required\n"
        "next: openspec list --json\n"
    )


def test_human_output_uses_existing_diagnostic_message_for_a_block(capsys) -> None:
    result = EthosResult(
        command="status",
        verdict="block",
        state="gapped",
        diagnostics=(
            {
                "severity": "error",
                "code": "repository_binding_missing",
                "message": "Repository binding is missing.",
            },
        ),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == "status: gapped\nwhy: Repository binding is missing.\n"


def test_human_output_does_not_repeat_one_required_gap(capsys) -> None:
    result = EthosResult(
        command="prove",
        verdict="block",
        state="gapped",
        required_gaps=("openspec_official_cli_missing", "openspec_official_cli_missing"),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == "prove: gapped\nwhy: openspec official cli missing\n"


def test_human_output_keeps_distinct_diagnostics_without_codes(capsys) -> None:
    result = EthosResult(
        command="status",
        verdict="block",
        state="gapped",
        diagnostics=(
            {"severity": "warning", "message": "Policy observation unavailable."},
            {"severity": "error", "message": "Runtime binding unavailable."},
        ),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "status: gapped\nwhy: Policy observation unavailable.\nwhy: Runtime binding unavailable.\n"
    )


def test_human_output_keeps_distinct_messages_for_one_reason_code(capsys) -> None:
    result = EthosResult(
        command="prove",
        verdict="block",
        state="gapped",
        required_gaps=("gate_failed",),
        diagnostics=(
            {"severity": "warning", "code": "gate_failed", "message": "Unit tests failed."},
            {"severity": "error", "code": "gate_failed", "message": "Coverage is low."},
        ),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "prove: gapped\nwhy: Unit tests failed.\nwhy: Coverage is low.\n"
    )


@pytest.mark.parametrize("error", [BrokenPipeError(), BlockingIOError()])
def test_output_pipe_failure_is_a_terminal_no_op(
    monkeypatch: pytest.MonkeyPatch, error: OSError
) -> None:
    monkeypatch.setattr(
        sys.stdout,
        "write",
        lambda _text: (_ for _ in ()).throw(error),
    )

    output.emit(
        EthosResult(
            command="status",
            verdict="block",
            state="gapped",
            required_gaps=("repository_invalid",),
        ),
        json_output=False,
    )
