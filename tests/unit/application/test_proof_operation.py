"""Proof is an application operation: it returns the result that `ethos prove` renders."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.application.proof.operation import ProofRequest
from ethos.application.proof.operation import prove_repository
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_FIELDS = ("verdict", "state", "required_gaps", "next_action")


@pytest.mark.parametrize(
    ("proof_request", "argv"),
    [
        (
            ProofRequest(acceptance_purpose="local-source", gate=("ruff",)),
            ("--acceptance-purpose", "local-source", "--gate", "ruff"),
        ),
        (ProofRequest(), ()),
    ],
    ids=["refused-mode", "unadopted-repository"],
)
def test_the_operation_returns_what_the_command_renders(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    proof_request: ProofRequest,
    argv: tuple[str, ...],
) -> None:
    """In process, proof writes no stdout, raises no exit and agrees with the rendered result."""
    repo = init_git_repo(tmp_path / "repo")

    returned = prove_repository(repo, proof_request).to_dict()
    written = capsys.readouterr().out
    rendered = json.loads(run_ethos_raw("prove", *argv, "--root", str(repo), "--json").stdout)

    assert written == ""
    assert returned["verdict"] != "pass"
    assert {name: returned[name] for name in _FIELDS} == {name: rendered[name] for name in _FIELDS}
