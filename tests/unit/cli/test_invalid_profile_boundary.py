"""Normalize invalid-profile failures without hiding CLI argument boundaries."""

from __future__ import annotations

import json
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import cast

import pytest

import ethos.adapters.repo.runtime.authority as runtime_authority
import ethos.surface.cli.application as application
import ethos.surface.cli.version as version_module
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GIT_PROCESS_TIMED_OUT
from ethos.adapters.repo.git import GitExecutionError
from ethos.cli import console_main
from ethos.cli import main
from ethos.contracts.admission import root_command
from ethos.domain.adoption import adopt_repository
from ethos.domain.inspection import inspect_repository
from ethos.domain.land.operation import land_repository
from ethos.domain.plan import plan_repository
from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.literal_cases import literal_case


def _invoke(monkeypatch, capsys, *args, exit_code=1, entrypoint=main):
    """Capture the native public boundary without suppressing exit semantics."""
    monkeypatch.setattr(sys, "argv", ["ethos", *args])
    with (
        pytest.raises(SystemExit, match=f"^{exit_code}$")
        if exit_code is not None
        else nullcontext()
    ):
        entrypoint()
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err + captured.out
    protocol = root_command(list(args)) == "mcp"
    assert not (captured.out if protocol else captured.err)
    return json.loads(captured.err if protocol else captured.out)


@pytest.mark.parametrize(
    "operation", [inspect_repository, plan_repository, adopt_repository, land_repository]
)
@pytest.mark.parametrize("code", ["git_executable_unavailable", GIT_PROCESS_TIMED_OUT])
@pytest.mark.parametrize("keyword", [False, True])
def test_application_native_failure_preserves_result(
    tmp_path, monkeypatch, capsys, operation, code, keyword
):
    """Native failures are typed application results, not transport-dependent exceptions."""

    def fail(*_args, **_kwargs):
        raise GitExecutionError(code, reason="unavailable")

    monkeypatch.setattr("ethos.adapters.repo.git.git_executable", fail)
    result = operation(root=tmp_path) if keyword else operation(tmp_path)
    assert result.verdict == ("unknown" if code == GIT_PROCESS_TIMED_OUT else "block")
    assert result.required_gaps == (code,)
    assert result.data["cwd"] == str(tmp_path.resolve())
    assert not capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "expected"),
    cast(
        "list[object]",
        literal_case(
            "cli.test_invalid_profile_boundary:parametrize:test_invalid_profilecommand_name_detection_skips_option_values:0"
        ),
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


@pytest.mark.parametrize(
    ("command", "extra_args", "exit_code", "repository"),
    [
        ("status", (), 0, True),
        ("plan", (), 0, True),
        *(
            (command, args, 1 if enforcing else 0 if command == "land" else None, False)
            for command, args, enforcing in cast(
                "list[tuple[str, tuple[str, ...], bool]]",
                literal_case(
                    "cli.test_invalid_profile_boundary:parametrize:test_invalid_profile_workflowcommand_names_emit_structured_result_before_admission:1"
                ),
            )
        ),
    ],
)
def test_invalid_profile_workflowcommand_names_emit_structured_result_before_admission(
    tmp_path, monkeypatch, capsys, command, extra_args, exit_code, repository
):
    root = init_repo_with_candidate(tmp_path)[0] if repository else tmp_path
    profile = root / ".ethos/profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text(
        'profile_id = "invalid"\n[openspec]\nmaterial_paths = ["openspec/**"]\n'
        '[roots]\nrules = "."\n',
    )
    payload = _invoke(
        monkeypatch,
        capsys,
        command,
        *extra_args,
        "--root",
        str(root),
        "--json",
        exit_code=exit_code,
    )
    assert payload["command"] == command
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["repository_profile_invalid:.ethos/profile.toml"]
    reader = {"status": inspect_repository, "plan": plan_repository}.get(command)
    if reader is not None:
        assert reader(root).to_dict() == payload
        assert not capsys.readouterr().out


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        *cast(
            "list[object]",
            literal_case(
                "cli.test_invalid_profile_boundary:parametrize:test_git_execution_failures_emit_structured_json_without_traceback:2"
            ),
        ),
        ("native_windows_powershell_unavailable", "native_executable_missing"),
    ],
)
@pytest.mark.parametrize("arguments", [("status",), ("mcp",), ("hook", "install")])
@pytest.mark.parametrize("entrypoint", [main, console_main])
def test_native_execution_failures_preserve_evidence_and_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    code: str,
    reason: str,
    arguments: tuple[str, ...],
    entrypoint,
) -> None:
    git_failure = code.startswith("git_")
    error_type = GitExecutionError if git_failure else ProcessExecutionError
    executed = (
        ("/usr/bin/git", "status")
        if git_failure
        else ("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",)
    )
    cause = "OSError: denied" if git_failure else "FileNotFoundError: missing"

    def fail(_root: Path | None) -> Path:
        raise error_type(
            code,
            reason=reason,
            command=executed,
            cwd=tmp_path.resolve().as_posix(),
            cause=cause,
        )

    if entrypoint is console_main:
        monkeypatch.setattr("ethos.cli.git_common_dir", fail)
    else:
        monkeypatch.setattr(application, "load_command_groups", fail)
    payload = _invoke(
        monkeypatch, capsys, *arguments, "--root", str(tmp_path), "--json", entrypoint=entrypoint
    )
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == [code]
    assert payload["data"] == {
        "error_boundary": "git_execution" if git_failure else "process_execution",
        "code": code,
        "reason": reason,
        "command": list(executed),
        "cwd": tmp_path.resolve().as_posix(),
        "cause": cause,
    }


@pytest.mark.parametrize("command", ["status", "--version"])
def test_source_timeout_reaches_public_failure_without_reinstall_or_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    """Source observation failure remains evidence, not stale-runtime diagnosis."""
    repo, _candidate = init_repo_with_candidate(tmp_path)

    def expire(*_args, **_kwargs):
        raise GitExecutionError(
            GIT_PROCESS_TIMED_OUT,
            reason="deadline_exceeded",
            command=("/usr/bin/git", "read-tree", "a" * 40),
            cwd=repo.as_posix(),
            cause="native source observation timed out",
            observation={"timeout_seconds": 0.01, "stdout": "partial", "stderr": "waiting"},
        )

    monkeypatch.setattr(runtime_authority, "expected_runtime_build", expire)
    monkeypatch.setattr(version_module, "invoking_build_identity", expire)
    payload = _invoke(monkeypatch, capsys, command, "--root", str(repo), "--json")
    assert payload["required_gaps"] == ["git_process_timed_out"]
    assert payload["data"]["observation"]["stderr"] == "waiting"
    assert payload["data"]["cwd"] == repo.as_posix()
    assert payload["next_action"] == f"ethos status --root {repo.as_posix()} --json"


def test_version_source_movement_is_reported_with_its_actual_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Version inspection reuses the native error envelope for a changed source."""

    def moved():
        message = "build_source_identity_changed"
        raise GitExecutionError(
            message,
            reason="head_changed_during_observation",
            cwd=tmp_path.as_posix(),
            observation={"expected_head": "a" * 40, "observed_head": "b" * 40},
        )

    monkeypatch.setattr(version_module, "invoking_build_identity", moved)
    payload = _invoke(monkeypatch, capsys, "--version", "--json")
    assert payload["command"] == "version"
    assert payload["data"]["observation"]["observed_head"] == "b" * 40
    assert payload["next_action"] == f"ethos status --root {tmp_path.as_posix()} --json"


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

    monkeypatch.setattr(
        application,
        "load_command_groups" if phase == "registration" else "dispatch_arguments",
        fail,
    )
    payload = _invoke(monkeypatch, capsys, "status", "--json")
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
