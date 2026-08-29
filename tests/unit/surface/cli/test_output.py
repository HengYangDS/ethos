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

    assert capsys.readouterr().out == "plan: gapped\nnext: repair the repository\n"
    with pytest.raises(SystemExit, match="1"):
        output.emit(result, json_output=False)


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
