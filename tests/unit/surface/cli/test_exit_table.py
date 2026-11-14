"""The declared process exit table, every CLI exit by kind, and help's copy of the table."""

from __future__ import annotations

import ast
import json
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

import ethos.application.console as console_module
import ethos.cli as cli
import ethos.surface.cli.output as output
from ethos.contracts.operations.declaration import EXIT_CODES
from ethos.contracts.operations.declaration import exits
from ethos.result import EthosResult

ROOT = Path(__file__).resolve().parents[4]
SURFACE = ROOT / "src" / "ethos" / "surface"
EXPECTED = [("pass", 0), ("blocked", 1), ("usage", 2), ("undelivered", 3), ("refused", 125)]
BLOCK = EthosResult(command="status", verdict="block", state="gapped", required_gaps=("p",))
USAGE = EthosResult(command="status", verdict="block", state="usage_refused", required_gaps=("p",))
PASS = EthosResult(command="status", verdict="pass", state="done")


@pytest.mark.parametrize(("kind", "status"), EXPECTED)
def test_each_declared_exit_kind_holds_its_number(kind: str, status: int) -> None:
    assert EXIT_CODES[kind].status == status


def test_only_refused_is_reserved_and_process_carries_the_childs_status() -> None:
    assert [row.kind for row in exits()] == [*[kind for kind, _ in EXPECTED], "process"]
    assert [row.kind for row in exits() if row.reserved] == ["refused"]
    assert EXIT_CODES["process"].status is None
    assert all(row.meaning for row in exits())


@pytest.mark.parametrize(("result", "kind"), [(USAGE, "usage"), (BLOCK, "blocked")])
def test_an_enforced_result_exits_by_the_table(result: EthosResult, kind: str) -> None:
    with pytest.raises(SystemExit) as exit_info:
        output.emit(result, json_output=True)
    assert exit_info.value.code == EXIT_CODES[kind].status


def test_an_undelivered_result_exits_by_the_table(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys.stdout, "write", lambda _text: 0)
    with pytest.raises(SystemExit) as exit_info:
        output.emit(PASS, json_output=True)
    assert exit_info.value.code == EXIT_CODES["undelivered"].status
    assert "output_partial" in capsys.readouterr().err


def test_the_root_help_prints_the_exit_table(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(console_module, "command_scope", lambda **_: nullcontext())
    # No binding means no selected runtime to re-execute into: the subject is help's copy of the
    # table, not which interpreter runs it, and an exec here would replace the test process.
    monkeypatch.setattr(console_module, "git_common_dir", lambda _target: "")
    monkeypatch.setattr(sys, "argv", ["ethos", "--help", "--json"])
    cli.console_main()
    assert json.loads(capsys.readouterr().out)["data"]["exits"] == [
        row.to_contract() for row in exits()
    ]


def test_no_surface_module_exits_by_a_numeric_literal() -> None:
    found = [
        f"{path.relative_to(ROOT).as_posix()}:{node.lineno}"
        for path in sorted(SURFACE.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SystemExit"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert found == []
