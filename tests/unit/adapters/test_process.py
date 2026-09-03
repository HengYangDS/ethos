from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.process as process_adapter

if TYPE_CHECKING:
    from pathlib import Path


def test_windows_powershell_is_resolved_from_the_native_system_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "System32/WindowsPowerShell/v1.0/powershell.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("native\n", encoding="utf-8")
    monkeypatch.setenv("SYSTEMROOT", tmp_path.as_posix())
    monkeypatch.setenv("PATH", (tmp_path / "ambient").as_posix())

    assert process_adapter.windows_powershell() == executable.resolve().as_posix()


def test_windows_powershell_rejects_missing_native_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SYSTEMROOT", raising=False)

    with pytest.raises(process_adapter.ProcessExecutionError) as failure:
        process_adapter.windows_powershell()

    assert failure.value.evidence() == {
        "code": "native_windows_powershell_unavailable",
        "reason": "system_root_missing",
        "command": [],
        "cwd": "",
        "cause": "",
    }


def test_posix_process_listing_resolves_native_ps_outside_ambient_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = tmp_path / "native/ps"
    native.parent.mkdir()
    native.write_text("native\n", encoding="utf-8")
    native.chmod(0o755)
    observed: dict[str, str] = {}
    monkeypatch.setenv("PATH", (tmp_path / "ambient").as_posix())

    def resolve(name: str, *, path: str) -> str:
        observed.update(name=name, path=path)
        return native.as_posix()

    monkeypatch.setattr(process_adapter.shutil, "which", resolve)

    assert process_adapter.process_listing_command(platform_name="posix") == (
        native.resolve().as_posix(),
        "-axo",
        "command=",
    )
    assert observed == {"name": "ps", "path": os.defpath}


def test_process_creation_failure_preserves_exact_execution_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = ((tmp_path / "tool").as_posix(), "--inspect")
    monkeypatch.setattr(
        process_adapter.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError(2, "missing")),
    )

    with pytest.raises(process_adapter.ProcessExecutionError) as failure:
        process_adapter.run_command(tmp_path, command)

    assert failure.value.evidence() == {
        "code": "process_creation_failed",
        "reason": "operating_system_rejected_process_creation",
        "command": list(command),
        "cwd": tmp_path.resolve().as_posix(),
        "cause": "FileNotFoundError: [Errno 2] missing",
    }


def test_run_command_removes_only_explicit_inherited_environment_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, str] = {}
    monkeypatch.setenv("PSModulePath", "pwsh-modules")
    monkeypatch.setenv("ETHOS_PRESERVED", "inherited")
    monkeypatch.setenv("GIT_PRESERVED", "provider-neutral")

    def capture_run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs["env"])
        return subprocess.CompletedProcess(("tool",), 0, "", "")

    monkeypatch.setattr(process_adapter.subprocess, "run", capture_run)

    process_adapter.run_command(
        tmp_path,
        ("tool",),
        env={"ETHOS_ADDED": "explicit"},
        remove_env=("PSModulePath",),
    )

    assert "PSModulePath" not in observed
    assert observed["ETHOS_PRESERVED"] == "inherited"
    assert observed["GIT_PRESERVED"] == "provider-neutral"
    assert observed["ETHOS_ADDED"] == "explicit"


def test_run_command_removes_explicit_environment_prefixes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, str] = {}
    monkeypatch.setenv("GIT_DIR", "/tmp/foreign.git")
    monkeypatch.setenv("ETHOS_PRESERVED", "inherited")

    def capture_run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs["env"])
        return subprocess.CompletedProcess(("tool",), 0, "", "")

    monkeypatch.setattr(process_adapter.subprocess, "run", capture_run)

    process_adapter.run_command(
        tmp_path,
        ("tool",),
        remove_env_prefixes=("GIT_",),
    )

    assert "GIT_DIR" not in observed
    assert observed["ETHOS_PRESERVED"] == "inherited"
