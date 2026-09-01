from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import ethos.cli as cli
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GitExecutionError
from ethos.cli import main
from ethos.contracts.admission import root_command
from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.literal_cases import literal_case


@pytest.mark.parametrize(
    ("argv", "expected"),
    literal_case(
        "cli.test_invalid_profile_boundary:parametrize:test_invalid_profilecommand_name_detection_skips_option_values:0"
    ),
)
def test_invalid_profilecommand_name_detection_skips_option_values(
    argv: list[str], expected: str
) -> None:
    assert root_command(argv) == expected


def test_plan_payload_budget_externalizes_oversized_detail(tmp_path: Path) -> None:
    result = EthosResult(
        command="plan",
        verdict="block",
        state="gapped",
        summary={"required_gate_count": 1},
        required_gaps=("example_gap",),
        next_action="repair example",
        data={"verbose": "x" * 40_000},
    )

    bounded = apply_payload_budget(result, root=tmp_path)

    assert len(bounded.to_json().encode()) <= 32 * 1024
    assert bounded.verdict == "block"
    assert bounded.required_gaps == result.required_gaps
    assert bounded.next_action == result.next_action
    reference = bounded.data["artifact_reference"]
    artifact = Path(reference["path"])
    assert artifact.is_file()
    assert reference["sha256"].startswith("sha256:")
    assert reference["size_bytes"] == artifact.stat().st_size
    assert json.loads(artifact.read_text(encoding="utf-8"))["data"] == result.data


@pytest.mark.parametrize("command", ["status", "plan"])
def test_invalid_profile_readercommand_names_emit_json_result(
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
    monkeypatch.setattr(sys, "argv", args)

    if command == "plan":
        with pytest.raises(SystemExit, match="0"):
            main()
    else:
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["repository_profile_invalid:.ethos/profile.toml"]


@pytest.mark.parametrize(
    "case",
    literal_case(
        "cli.test_invalid_profile_boundary:parametrize:test_invalid_profile_workflowcommand_names_emit_structured_result_before_admission:1"
    ),
)
def test_invalid_profile_workflowcommand_names_emit_structured_result_before_admission(
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
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["repository_profile_invalid:.ethos/profile.toml"]


@pytest.mark.parametrize(
    ("code", "reason"),
    literal_case(
        "cli.test_invalid_profile_boundary:parametrize:test_git_execution_failures_emit_structured_json_without_traceback:2"
    ),
)
def test_git_execution_failures_emit_structured_json_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    code: str,
    reason: str,
) -> None:
    def fail(_root: Path | None) -> Path:
        raise GitExecutionError(
            code,
            reason=reason,
            command=("/usr/bin/git", "status"),
            cwd=tmp_path.resolve().as_posix(),
            cause="OSError: denied",
        )

    monkeypatch.setattr("ethos.surface.cli.root.inspection.resolve_root", fail)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ethos", "status", "--root", tmp_path.as_posix(), "--json"],
    )

    with pytest.raises(SystemExit, match="1"):
        main()

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err + captured.out
    payload = json.loads(captured.out)
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == [code]
    assert payload["data"]["reason"] == reason
    assert payload["data"]["command"] == ["/usr/bin/git", "status"]
    assert payload["data"]["cwd"] == tmp_path.resolve().as_posix()
    assert payload["data"]["cause"] == "OSError: denied"


def test_process_execution_failure_emits_structured_json_without_git_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        code = "native_windows_powershell_unavailable"
        raise ProcessExecutionError(
            code,
            reason="native_executable_missing",
            command=("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",),
            cwd=tmp_path.resolve().as_posix(),
            cause="FileNotFoundError: missing",
        )

    monkeypatch.setattr(cli, "load_command_groups", fail)
    monkeypatch.setattr(sys, "argv", ["ethos", "hook", "install", "--json"])

    with pytest.raises(SystemExit, match="1"):
        main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_gaps"] == ["native_windows_powershell_unavailable"]
    assert payload["data"] == {
        "error_boundary": "process_execution",
        "code": "native_windows_powershell_unavailable",
        "reason": "native_executable_missing",
        "command": ["C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"],
        "cwd": tmp_path.resolve().as_posix(),
        "cause": "FileNotFoundError: missing",
    }


@pytest.mark.parametrize(
    ("phase", "error"),
    [
        ("registration", ValueError("branch_roles contains unknown fields")),
        ("dispatch", RuntimeError("state_schema_lease_table_definition_mismatch")),
    ],
)
def test_public_boundary_normalizes_contract_failures_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    phase: str,
    error: Exception,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(cli, "load_command_groups" if phase == "registration" else "app", fail)
    monkeypatch.setattr(sys, "argv", ["ethos", "status", "--json"])

    with pytest.raises(SystemExit, match="1"):
        main()

    captured = capsys.readouterr()
    assert "Traceback" not in captured.out + captured.err
    payload = json.loads(captured.out)
    assert (payload["verdict"], payload["state"], payload["continuation"]) == (
        "block",
        "gapped",
        "blocked",
    )
    assert payload["required_gaps"] == [str(error)]
    if str(error).startswith("state_schema_"):
        schema = payload["data"]["state_schema"]
        assert schema["expected_state"] == "current"
        assert schema["observed_state"] in {"absent", "current", "legacy", "incompatible"}
        assert payload["next_action"].startswith("ethos hook install --root ")
