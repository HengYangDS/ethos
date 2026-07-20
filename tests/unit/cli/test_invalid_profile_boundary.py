from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest

from ethos.cli import main

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("command", ["orient", "report", "plan", "openspec"])
def test_invalid_profile_reader_commands_emit_json_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text(
        'profile_id = "invalid"\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n'
        "[roots]\n"
        'rules = "."\n',
        encoding="utf-8",
    )
    args = ["ethos", command, "--root", tmp_path.as_posix(), "--json"]
    if command == "openspec":
        args.insert(2, "--lifecycle")
    monkeypatch.setattr(sys, "argv", args)

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["adopter_profile_invalid:.ethos/profile.toml"]


def test_invalid_profile_proof_emits_enforcing_json_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
    monkeypatch.setattr(
        sys,
        "argv",
        ["ethos", "prove", "--root", tmp_path.as_posix(), "--json"],
    )

    with pytest.raises(SystemExit, match="1"):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["adopter_profile_invalid:.ethos/profile.toml"]
