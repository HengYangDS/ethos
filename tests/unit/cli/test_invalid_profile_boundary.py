from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest

from ethos.cli import _command
from ethos.cli import main
from tests.support.contract_helpers import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--root", "status", "plan", "--json"], "plan"),
        (["--root", "openspec", "status", "--json"], "status"),
        (["quality", "status", "--json"], "ethos"),
    ],
)
def test_invalid_profile_command_detection_uses_declared_root_commands(
    argv: list[str], expected: str
) -> None:
    assert _command(argv) == expected


@pytest.mark.parametrize("command", ["status", "plan", "openspec"])
def test_invalid_profile_reader_commands_emit_json_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    repo, _ = init_repo_with_candidate(tmp_path)
    profile = repo / ".ethos" / "profile.toml"
    profile.write_text(
        'profile_id = "invalid"\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n'
        "[roots]\n"
        'rules = "."\n',
        encoding="utf-8",
    )
    args = ["ethos", command, "--root", repo.as_posix(), "--json"]
    if command == "openspec":
        args.insert(2, "--lifecycle")
    monkeypatch.setattr(sys, "argv", args)

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["adopter_profile_invalid:.ethos/profile.toml"]


@pytest.mark.parametrize(
    "case",
    [
        ("prove", (), True),
        ("land", (), False),
        ("land", ("--apply",), True),
    ],
)
def test_invalid_profile_workflow_commands_emit_structured_result_before_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    case: tuple[str, tuple[str, ...], bool],
) -> None:
    command, extra_args, enforcing = case
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "invalid"\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n'
        "[roots]\n"
        'rules = "."\n',
        encoding="utf-8",
    )
    command_args = ["ethos", command, *extra_args, "--root", tmp_path.as_posix(), "--json"]
    monkeypatch.setattr(sys, "argv", command_args)

    if enforcing:
        with pytest.raises(SystemExit, match="1"):
            main()
    elif command == "land":
        with pytest.raises(SystemExit, match="0"):
            main()
    else:
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == command
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["adopter_profile_invalid:.ethos/profile.toml"]
