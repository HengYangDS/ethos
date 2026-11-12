"""`ethos lane repair-signature` selects the census and rebuild readiness before its old modes."""

from __future__ import annotations

import io
import json
import sys
from typing import TYPE_CHECKING

import pytest

from ethos.application.catalog import Refused
from ethos.application.catalog import select_operation
from ethos.contracts.operations.catalog import COMMANDS
from ethos.contracts.operations.catalog import select_argv
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.rebuild import F1
from tests.support.rebuild import H1
from tests.support.rebuild import KEY_TEXT
from tests.support.rebuild import MAIN
from tests.support.rebuild import RECORD
from tests.support.rebuild import land_record
from tests.support.rebuild import peer_history
from tests.support.rebuild import record

if TYPE_CHECKING:
    from pathlib import Path

COMMAND = "lane repair-signature"
HEAD = "a" * 40


@pytest.mark.parametrize(
    ("argv", "operation", "effects"),
    [
        ("--census", "lane.repair-signature.census", ("read",)),
        (
            f"--rebuild {RECORD} --key-stdin",
            "lane.repair-signature.rebuild.preview",
            ("read", "remote-read"),
        ),
        (f"--rebuild {RECORD}", "lane.repair-signature.rebuild.preview", ("read", "remote-read")),
        (
            f"--expect-head {HEAD}",
            "lane.repair-signature.preview",
            ("read", "local-evidence-write"),
        ),
    ],
)
def test_each_mode_selects_its_operation_and_declares_its_effects(
    argv: str, operation: str, effects: tuple[str, ...]
) -> None:
    """The census comes first, readiness needs no head, and the key arrives on standard input."""
    command = COMMANDS[COMMAND]
    selected = select_argv(["ethos", *COMMAND.split(), *argv.split()])

    assert selected is not None
    assert selected[1] is not None
    assert (selected[1].id, selected[1].effects) == (operation, effects)
    assert command.operations[0].id == "lane.repair-signature.census"
    assert (command.stdin, command.stdin_limit) == ("key_stdin", 67)
    assert command.request.model_fields["expect_head"].default is None


@pytest.mark.parametrize(
    ("fields", "gap"),
    [
        ({"census": True, "rebuild": RECORD}, "command_field_refused:rebuild"),
        ({"census": True, "key_stdin": True}, "command_field_refused:key_stdin"),
        ({"census": True, "apply": True}, "command_field_refused:apply"),
        ({"census": True, "expect_head": HEAD}, "command_field_refused:expect_head"),
        ({"rebuild": RECORD, "expect_head": HEAD}, "command_field_refused:expect_head"),
        ({"rebuild": RECORD, "backup": "x.bundle"}, "command_field_refused:backup"),
        ({"key_stdin": True, "expect_head": HEAD}, "command_field_refused:key_stdin"),
    ],
)
def test_a_field_outside_the_selected_operation_refuses(
    fields: dict[str, object], gap: str
) -> None:
    """Beside the census nothing else is taken, and only readiness takes the key."""
    chosen = select_operation(COMMAND, fields)

    assert isinstance(chosen, Refused)
    assert gap in chosen.result.required_gaps


def _run(repo: Path, monkeypatch: pytest.MonkeyPatch, *argv: str) -> dict[str, object]:
    monkeypatch.setattr(sys, "stdin", io.StringIO(KEY_TEXT))
    completed = run_ethos_raw(*COMMAND.split(), *argv, "--root", str(repo), "--json", cwd=repo)
    assert H1 not in completed.stdout
    assert F1 not in completed.stdout
    return json.loads(completed.stdout)


def test_readiness_and_the_census_run_without_a_head_and_signature_modes_need_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Readiness reads the key from standard input; today's repair still refuses a missing head."""
    repo, base = peer_history(tmp_path, bare=True)
    old = land_record(repo, record(base, dev='{ gitlab = "old", github = "absent" }', refs=MAIN))
    git(repo, "branch", "-f", "main", old)
    git(repo, "push", "-q", "--no-verify", "gitlab", "dev", "main")

    ready = _run(repo, monkeypatch, "--rebuild", RECORD, "--key-stdin")
    counted = _run(repo, monkeypatch, "--census")
    unbound = _run(repo, monkeypatch)

    assert (ready["state"], ready["required_gaps"]) == ("ready_to_rebuild", []), ready
    assert counted["state"] == "counted"
    assert unbound["required_gaps"] == ["expect_head_required"]
