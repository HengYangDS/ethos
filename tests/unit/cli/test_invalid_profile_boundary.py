from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ethos.cli import _command
from ethos.cli import main
from ethos.result import EthosResult
from ethos.result import apply_payload_budget
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


def test_plan_payload_budget_externalizes_oversized_detail(tmp_path: Path) -> None:
    result = EthosResult(
        command="plan",
        ok=False,
        state="gapped",
        summary={"required_gate_count": 1},
        required_gaps=("example_gap",),
        next_actions=("repair example",),
        data={"verbose": "x" * 40_000},
    )

    bounded = apply_payload_budget(result, root=tmp_path)

    assert len(bounded.to_json().encode()) <= 32 * 1024
    assert bounded.ok is False
    assert bounded.required_gaps == result.required_gaps
    assert bounded.next_actions == result.next_actions
    reference = bounded.data["artifact_reference"]
    artifact = tmp_path / reference["path"]
    assert artifact.is_file()
    assert reference["sha256"].startswith("sha256:")
    assert reference["size_bytes"] == artifact.stat().st_size
    assert json.loads(artifact.read_text(encoding="utf-8"))["data"] == result.data


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
