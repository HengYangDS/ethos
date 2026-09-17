"""Native process selection and observations preserve their failure boundaries."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.process as process_adapter
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity

if TYPE_CHECKING:
    from pathlib import Path


def _file_reference_payloads():
    """Declare each observed file-reference counterexample once."""
    payload = b"p12\0\nfcwd\0tDIR\0D0x10\0i31\0\nf3\0tREG\0D0x20\0i31\0\nf4\0tIPv4\0\n"
    absent = b"f5\0nsocket: FD unavailable\0\n"
    unix = b"f6\0tunix\0i50690625\0ntype=STREAM\0\n"
    return {
        "unix-inode": payload + unix,
        "unix-empty-inode": payload + unix.replace(b"i50690625", b"i"),
        "unix-negative-inode": payload + unix.replace(b"i50690625", b"i-1"),
        "unix-duplicate-inode": payload + unix.replace(b"i50690625", b"i1\0i2"),
        "unix-orphan": unix + payload,
        "regular-inode-only": payload + unix.replace(b"tunix", b"tREG"),
        "directory-inode-only": payload + unix.replace(b"tunix", b"tDIR"),
        "unknown-inode-only": payload + unix.replace(b"tunix", b"tunknown"),
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
        **dict.fromkeys(("valid", "status", "stderr", "timeout", "missing"), payload),
    }


_FILE_REFERENCE_PAYLOADS = _file_reference_payloads()


@pytest.mark.parametrize("fault", _FILE_REFERENCE_PAYLOADS)
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
    payload = _FILE_REFERENCE_PAYLOADS[fault]

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
    if fault in {"valid", "fd-gone", "process-gone", "named-live-file", "unix-inode"}:
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
        "-axww",
        "-o",
        "command=",
    )
    assert observed == {"name": "ps", "path": os.defpath}


@pytest.mark.parametrize("phase", ["spawn", "communication"])
def test_process_failure_preserves_its_actual_boundary(tmp_path, monkeypatch, phase):
    """Only failure before successful creation is a process-creation error."""
    failure = OSError(5, "boundary probe")
    target, attribute = (
        (subprocess, "Popen") if phase == "spawn" else (subprocess.Popen, "communicate")
    )
    monkeypatch.setattr(target, attribute, lambda *_a, **_kw: (_ for _ in ()).throw(failure))
    command = (sys.executable, "-c", "pass")
    with pytest.raises(
        process_adapter.ProcessExecutionError if phase == "spawn" else OSError
    ) as caught:
        process_adapter.run_command(tmp_path, command)
    if phase == "communication":
        assert caught.value is failure
    else:
        assert caught.value.evidence() == {
            "code": "process_creation_failed",
            "reason": "operating_system_rejected_process_creation",
            "command": list(command),
            "cwd": tmp_path.resolve().as_posix(),
            "cause": "OSError: [Errno 5] boundary probe",
        }


@pytest.mark.parametrize("mode", ["key", "prefix", "isolated"])
def test_command_environment_and_native_io(tmp_path, monkeypatch, mode):
    """Native children consume exactly the selected environment and input."""
    environment = {"PSModulePath": "pwsh", "ETHOS_PRESERVED": "inherited", "GIT_PRESERVED": "git"}
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    body = (
        "import json,os,sys; print(json.dumps(dict(os.environ))); "
        "sys.stderr.write(sys.stdin.read()); sys.exit(int(sys.argv[1]))"
    )
    textual = mode != "prefix"
    result = process_adapter.run_command(
        tmp_path,
        (sys.executable, "-c", body, "0"),
        text=textual,
        check=True,
        timeout=10,
        env={"ETHOS_ADDED": "explicit"},
        inherit_environment=mode != "isolated",
        remove_env=("psmodulepath",) if mode == "key" else (),
        remove_env_prefixes=("git_",) if mode == "prefix" else (),
        stdin="input" if textual else b"input",
    )
    observed = json.loads(result.stdout)
    assert result.stderr == ("input" if textual else b"input")
    expected = {} if mode == "isolated" else environment.copy()
    if mode != "isolated":
        del expected["PSModulePath" if mode == "key" else "GIT_PRESERVED"]
    expected["ETHOS_ADDED"] = "explicit"
    assert {k: observed[k] for k in (*environment, "ETHOS_ADDED") if k in observed} == expected
    with pytest.raises(subprocess.CalledProcessError) as failure:
        process_adapter.run_command(tmp_path, (sys.executable, "-c", body, "7"), check=True)
    assert failure.value.returncode == 7
    assert failure.value.stderr == ""
    assert json.loads(failure.value.stdout)["ETHOS_PRESERVED"] == "inherited"


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group boundary")
@pytest.mark.parametrize("failure", ["timeout", "cancel", "gate-cancel"])
@pytest.mark.parametrize("inherit_pipes", [False, True])
def test_command_failure_closes_owned_descendants(tmp_path, monkeypatch, failure, inherit_pipes):
    """A ready descendant cannot retain its socket after the command is interrupted."""
    communicate = subprocess.Popen.communicate
    connection = None
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(10)
        child = (
            f"import socket; s=socket.create_connection({listener.getsockname()!r},timeout=10); "
            "s.settimeout(None); s.sendall(b'R'); s.recv(1)"
        )
        parent = (
            "import subprocess,sys; print('started',flush=True); "
            f"subprocess.Popen([sys.executable,'-c',{child!r}],"
            f"stdout={None if inherit_pipes else subprocess.DEVNULL},"
            f"stderr={None if inherit_pipes else subprocess.DEVNULL}).wait()"
        )

        def after_ready(process, *args, **kwargs):
            nonlocal connection
            if connection is None:
                connection, _ = listener.accept()
                connection.settimeout(2)
                assert connection.recv(1) == b"R"
                if failure != "timeout":
                    raise KeyboardInterrupt
            return communicate(process, *args, **kwargs)

        monkeypatch.setattr(subprocess.Popen, "communicate", after_ready)

        def execute():
            command = (sys.executable, "-c", parent)
            if failure != "gate-cancel":
                return process_adapter.run_command(tmp_path, command, timeout=0.2)
            gate = Gate(id="probe", kind="test", command=command)
            node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
            return LocalGateRunner().run(node, gate, root=tmp_path)

        try:
            error = subprocess.TimeoutExpired if failure == "timeout" else KeyboardInterrupt
            with pytest.raises(error) as raised:
                execute()
            if failure == "timeout":
                assert raised.value.output == b"started\n"
            assert connection is not None
            assert connection.recv(1) == b""
        finally:
            if connection is not None:
                connection.close()
