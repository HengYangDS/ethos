from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.process as process_adapter

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "fault",
    [
        "valid",
        "fd-gone",
        "process-gone",
        "permission",
        "unclassified",
        "unknown-source",
        "invalid-gone-fd",
        "orphan-gone",
        "non-darwin-gone",
        "named-live-file",
        "empty",
        "truncated",
        "duplicate",
        "pid",
        "nofd",
        "type",
        "inode",
        "field",
        "empty-fd",
        "empty-type",
        "orphan",
        "negative-inode",
        "status",
        "stderr",
        "timeout",
        "missing",
    ],
)
def test_native_file_references_are_bounded_and_incomplete_observation_fails_closed(
    tmp_path, monkeypatch, fault
):
    executable = tmp_path / "lsof"
    executable.write_text("native observer\n")
    observed = []
    monkeypatch.setenv("PATH", str(tmp_path / "ambient"))

    def resolve(name, *, path):
        observed.append((name, path))
        return None if fault == "missing" else str(executable)

    monkeypatch.setattr(process_adapter.shutil, "which", resolve)
    monkeypatch.setattr(sys, "platform", "linux" if fault == "non-darwin-gone" else "darwin")
    payload = b"p12\0\nfcwd\0tDIR\0D0x10\0i31\0\nf3\0tREG\0D0x20\0i31\0\nf4\0tIPv4\0\n"
    absent = b"f5\0nsocket: FD unavailable\0\n"
    payload = {
        "fd-gone": payload + absent,
        "process-gone": payload + b"f5\0nvnode: process unavailable\0\n",
        "permission": payload + b"f5\0nsocket: Operation not permitted\0\n",
        "unclassified": payload + b"f5\0\n",
        "unknown-source": payload + absent.replace(b"socket:", b"unknown:"),
        "invalid-gone-fd": payload + absent.replace(b"f5", b"fNOFD"),
        "orphan-gone": absent + payload,
        "non-darwin-gone": payload + absent,
        "named-live-file": payload.replace(b"i31\0", b"i31\0nsocket: FD unavailable\0", 1),
        "empty": b"",
        "truncated": payload[:-2],
        "duplicate": payload.replace(b"i31\0", b"i31\0i32\0", 1),
        "pid": payload.replace(b"p12", b"pnot-a-pid"),
        "nofd": payload + b"fNOFD\0\n",
        "type": payload.replace(b"tDIR\0", b"tunknown\0"),
        "inode": payload.replace(b"i31\0", b"", 1),
        "field": payload.replace(b"fcwd\0", b"fcwd\0gunexpected\0"),
        "empty-fd": payload.replace(b"fcwd\0", b"f\0"),
        "empty-type": payload.replace(b"tDIR\0", b"t\0"),
        "orphan": payload.removeprefix(b"p12\0\n"),
        "negative-inode": payload.replace(b"i31\0", b"i-1\0", 1),
    }.get(fault, payload)

    def capture(root, command, **kwargs):
        assert root == tmp_path
        assert command == (str(executable), "-nP", "-F0pftDin")
        assert kwargs["timeout"] == 10
        assert kwargs["text"] is False
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(
            command,
            1 if fault == "status" else 0,
            payload,
            b"permission denied" if fault == "stderr" else b"",
        )

    monkeypatch.setattr(process_adapter, "run_command", capture)
    if fault in {"valid", "fd-gone", "process-gone", "named-live-file"}:
        assert process_adapter.process_file_identities(tmp_path) == frozenset({(16, 31), (32, 31)})
    else:
        with pytest.raises(process_adapter.ProcessExecutionError) as error:
            process_adapter.process_file_identities(tmp_path)
        assert error.value.code == "native_process_observer_unavailable"
        assert error.value.reason == "file_references_unavailable"
        assert error.value.cwd == str(tmp_path)
        if fault == "empty-type":
            assert repr(b"fcwd\0t\0D0x10\0i31") in error.value.cause
    assert observed[0][0] == "lsof"
    assert str(tmp_path / "ambient") not in observed[0][1]


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
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        observed.update(environment)
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
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        observed.update(environment)
        return subprocess.CompletedProcess(("tool",), 0, "", "")

    monkeypatch.setattr(process_adapter.subprocess, "run", capture_run)

    process_adapter.run_command(
        tmp_path,
        ("tool",),
        remove_env_prefixes=("GIT_",),
    )

    assert "GIT_DIR" not in observed
    assert observed["ETHOS_PRESERVED"] == "inherited"
