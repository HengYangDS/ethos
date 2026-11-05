"""Failure boundaries build results from the decision an error carries, losing none of it."""

from __future__ import annotations

import json
import sys

import pytest

import ethos.surface.cli.application as application
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GIT_PROCESS_TIMED_OUT
from ethos.adapters.repo.git import GitExecutionError
from ethos.cli import main
from ethos.contracts.outcome import refusal
from ethos.domain.execution import process_failure_result


def test_process_failures_keep_every_carried_gap_and_the_declared_class(tmp_path) -> None:
    carried = ProcessExecutionError(
        "lead", reason="r", observation={"required_gaps": ["lead", "second"]}, verdict="unknown"
    )
    result = process_failure_result("status", carried, root=tmp_path)
    assert (result.verdict, result.state, result.required_gaps) == (
        "unknown",
        "unknown",
        ("lead", "second"),
    )
    assert result.data["error_boundary"] == "process_execution"
    timed_out = process_failure_result(
        "status", GitExecutionError(GIT_PROCESS_TIMED_OUT, reason="r")
    )
    rejected = GitExecutionError("git_effect_cas_rejected", reason="r", verdict="unknown")
    assert (timed_out.verdict, process_failure_result("land", rejected).verdict) == (
        "unknown",
        "unknown",
    )
    assert process_failure_result("land", GitExecutionError("x", reason="r")).verdict == "block"


def test_public_contract_failures_keep_every_gap_and_the_declared_verdict(
    monkeypatch, capsys, tmp_path
) -> None:
    refused = refusal("first_gap", "second_gap", verdict="unknown")

    def refuse(*_args, **_kwargs):
        raise refused

    monkeypatch.setattr(application, "load_command_groups", refuse)
    monkeypatch.setattr(sys, "argv", ["ethos", "status", "--root", str(tmp_path), "--json"])
    with pytest.raises(SystemExit, match=r"^1$"):
        main()
    payload = json.loads(capsys.readouterr().out)
    assert (payload["verdict"], payload["state"]) == ("unknown", "unknown")
    assert payload["required_gaps"] == ["first_gap", "second_gap"]
    assert payload["data"]["error_boundary"] == "public_command_contract"
