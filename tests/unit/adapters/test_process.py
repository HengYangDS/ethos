"""Native process selection and observations preserve their failure boundaries."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from contextvars import copy_context
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.process as process_adapter
import ethos.adapters.repo.runtime.retirement as retirement
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.subprocesses import ready_descendant

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("outcome", ["success", "nonzero", "timeout"])
def test_native_command_owns_its_handle_without_an_outer_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    """Every native command registers and releases one real owned process."""
    started: list[tuple[process_adapter.CommandScope, subprocess.Popen[str]]] = []
    terminated: list[subprocess.Popen[str]] = []
    discarded: list[subprocess.Popen[str]] = []
    start = process_adapter.CommandScope.start
    terminate = process_adapter.CommandScope.terminate
    discard = process_adapter.CommandScope.discard

    def observed_start(
        owner: process_adapter.CommandScope, command: tuple[str, ...], **options: object
    ) -> subprocess.Popen[str]:
        child = start(owner, command, **options)
        started.append((owner, child))
        return child

    def observed_terminate(
        owner: process_adapter.CommandScope, child: subprocess.Popen[str]
    ) -> None:
        assert (owner, child) in started
        terminated.append(child)
        terminate(owner, child)

    def observed_discard(owner: process_adapter.CommandScope, child: subprocess.Popen[str]) -> None:
        assert (owner, child) in started
        assert child.returncode is not None
        discarded.append(child)
        discard(owner, child)

    monkeypatch.setattr(process_adapter.CommandScope, "start", observed_start)
    monkeypatch.setattr(process_adapter.CommandScope, "terminate", observed_terminate)
    monkeypatch.setattr(process_adapter.CommandScope, "discard", observed_discard)
    body = "import time; time.sleep(1)" if outcome == "timeout" else "raise SystemExit(7)"
    if outcome == "success":
        body = "print('complete')"
    command = (sys.executable, "-c", body)
    if outcome == "success":
        result = process_adapter.run_command(tmp_path, command, check=True)
        assert result.returncode == 0
        assert result.stdout == "complete\n"
    else:
        failure = (
            subprocess.TimeoutExpired if outcome == "timeout" else subprocess.CalledProcessError
        )
        with pytest.raises(failure):
            process_adapter.run_command(
                tmp_path, command, check=True, timeout=0.1 if outcome == "timeout" else 2
            )
    assert len(started) == 1
    child = started[0][1]
    assert child.returncode is not None
    assert discarded == [child]
    assert terminated == ([child] if outcome == "timeout" else [])


def test_caught_command_failure_preserves_a_live_sibling(tmp_path, monkeypatch) -> None:
    """A checked failure cancels only when it escapes the caller's scope."""
    ready = threading.Event()
    children = []

    def observed(child, _options):
        children.append(child)
        ready.set()

    with (
        ready_descendant(monkeypatch, observed) as (body, _closed),
        process_adapter.command_scope(timeout_seconds=5) as scope,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        pending = pool.submit(
            copy_context().run,
            process_adapter.run_command,
            tmp_path,
            (sys.executable, "-c", body),
            timeout=4,
        )
        try:
            assert ready.wait(2)
            with pytest.raises(subprocess.CalledProcessError):
                process_adapter.run_command(
                    tmp_path, (sys.executable, "-c", "raise SystemExit(7)"), check=True, timeout=2
                )
            assert children[0].poll() is None
        finally:
            scope.cancel()
            assert pending.result(timeout=2).returncode != 0
    assert children[0].returncode is not None


@pytest.mark.parametrize("failure", [RuntimeError("initial"), KeyboardInterrupt()])
def test_command_scope_preserves_initiating_failure_when_cleanup_fails(monkeypatch, failure):
    cleanup = OSError("cleanup")
    monkeypatch.setattr(process_adapter.CommandScope, "cancel", Mock(side_effect=cleanup))
    with pytest.raises(BaseExceptionGroup) as result, process_adapter.command_scope():
        raise failure
    assert result.value.exceptions == (failure, cleanup)


def test_cancelled_command_scope_rejects_creation(tmp_path, monkeypatch) -> None:
    """Cancellation fences creation before any native process can start."""
    creation = Mock(wraps=subprocess.Popen)
    monkeypatch.setattr(subprocess, "Popen", creation)
    with process_adapter.command_scope() as scope:
        scope.cancel()
        with pytest.raises(process_adapter.ProcessExecutionError, match="process_cancelled"):
            process_adapter.run_command(tmp_path, (sys.executable, "-c", "pass"), timeout=2)
    creation.assert_not_called()


def test_command_scope_conserves_one_deadline_across_native_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later or nested command cannot renew a caller's finite execution budget."""
    command = (sys.executable, "-c", "pass")
    clock = 100.0
    budgets: list[float | None] = []
    started: list[subprocess.Popen[str]] = []
    start = process_adapter.CommandScope.start

    def observed_start(
        owner: process_adapter.CommandScope, argv: tuple[str, ...], **options: object
    ) -> subprocess.Popen[str]:
        child = start(owner, argv, **options)
        started.append(child)
        communicate = child.communicate

        def observed_communication(*, timeout: float | None) -> tuple[str, str]:
            nonlocal clock
            budgets.append(timeout)
            result = communicate(timeout=10)
            clock += 0.6
            return result

        monkeypatch.setattr(child, "communicate", observed_communication)
        return child

    monkeypatch.setattr(process_adapter, "monotonic", lambda: clock)
    monkeypatch.setattr(process_adapter.CommandScope, "start", observed_start)
    with process_adapter.command_scope(timeout_seconds=1.0):
        assert process_adapter.run_command(tmp_path, command, timeout=10).returncode == 0
        with process_adapter.command_scope(timeout_seconds=10):
            assert process_adapter.run_command(tmp_path, command, timeout=10).returncode == 0
        assert len(started) == 2
        with pytest.raises(subprocess.TimeoutExpired):
            process_adapter.run_command(tmp_path, command, timeout=10)
        assert len(started) == 2
    assert budgets == pytest.approx([1.0, 0.4])
    assert process_adapter.run_command(tmp_path, command, timeout=10).returncode == 0
    assert budgets == pytest.approx([1.0, 0.4, 10.0])


def test_command_scope_expires_at_remaining_native_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later or nested command cannot renew a caller's finite execution budget."""
    now = [1_000.0]
    monkeypatch.setattr(process_adapter, "monotonic", lambda: now[0])
    with process_adapter.command_scope(timeout_seconds=60):
        process_adapter.run_command(tmp_path, (sys.executable, "-c", "pass"), timeout=600)
        now[0] += 59.75
        with (
            process_adapter.command_scope(timeout_seconds=600),
            pytest.raises(subprocess.TimeoutExpired) as expired,
        ):
            process_adapter.run_command(
                tmp_path, (sys.executable, "-c", "import time; time.sleep(60)"), timeout=600
            )
    assert expired.value.timeout == pytest.approx(0.25)
    assert process_adapter.run_command(tmp_path, (sys.executable, "-c", "pass")).returncode == 0


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
        **dict.fromkeys(
            ("valid", "status", "fatal", "stderr", "timeout", "missing", "slow-scan"), payload
        ),
        "no-match": b"",
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
        assert command == (str(executable), "-nP", "-F0pftDin", "+D", str(root), str(executable))
        assert 0 < kwargs["timeout"] <= 30
        assert kwargs["text"] is False
        if fault == "timeout" or (fault == "slow-scan" and kwargs["timeout"] < 12):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        status = 2 if fault == "fatal" else 1 if fault in {"status", "no-match"} else 0
        stderr = b"permission denied" if fault == "stderr" else b""
        return subprocess.CompletedProcess(command, status, payload, stderr)

    monkeypatch.setattr(process_adapter, "run_command", capture)
    observe = process_adapter.process_file_identities
    if fault in {
        "valid",
        "status",
        "fd-gone",
        "process-gone",
        "named-live-file",
        "unix-inode",
        "slow-scan",
    }:
        assert observe(tmp_path, tree=tmp_path, index=executable) == frozenset({(16, 31), (32, 31)})
    elif fault == "no-match":
        assert observe(tmp_path, tree=tmp_path, index=executable) == frozenset()
    else:
        with pytest.raises(process_adapter.ProcessExecutionError) as error:
            observe(tmp_path, tree=tmp_path, index=executable)
        assert error.value.code == "native_process_observer_unavailable"
        assert error.value.reason == "file_references_unavailable"
        assert error.value.cwd == str(tmp_path)
        if fault == "empty-type":
            assert repr(b"fcwd\0t\0D0x10\0i31") in error.value.cause
    assert (observed[0][0], str(tmp_path / "ambient") in observed[0][1]) == ("lsof", False)


@pytest.mark.parametrize("platform", ["posix", "nt"])
def test_process_observer_resolves_native_authority(tmp_path, monkeypatch, platform):
    """Native observation excludes ambient executable and incompatible module paths."""
    relative = "System32/WindowsPowerShell/v1.0/powershell.exe" if platform == "nt" else "bin/ps"
    native = tmp_path / relative
    native.parent.mkdir(parents=True)
    native.write_text(
        '#!/bin/sh\n[ -z "${PSModulePath+x}${GIT_INDEX_FILE+x}" ] || exit 91\nprintf "%s\\n" "$*"\n'
    )
    native.chmod(0o700)
    monkeypatch.setenv("SYSTEMROOT", tmp_path.as_posix())
    monkeypatch.setenv("PATH", (tmp_path / "ambient").as_posix())
    monkeypatch.setenv("PSModulePath", "foreign-powershell-modules")
    monkeypatch.setenv("GIT_INDEX_FILE", "foreign-index")
    native_run = retirement.run_command

    def observe(root, command, **options):
        assert (root, options["timeout"]) == (tmp_path, 10)
        return native_run(root, command, **options)

    monkeypatch.setattr(retirement, "run_command", observe)

    def resolve(name, *, path):
        assert (name, path) == ("ps", os.defpath)
        return native.as_posix()

    monkeypatch.setattr(process_adapter.shutil, "which", resolve)
    expected = (
        "-NoLogo -NoProfile -NonInteractive -Command Get-CimInstance Win32_Process | % CommandLine"
        if platform == "nt"
        else "-axww -o command="
    )
    assert retirement.process_commands(tmp_path, platform_name=platform).strip() == expected
    if platform == "nt":
        monkeypatch.delenv("SYSTEMROOT")
        with pytest.raises(process_adapter.ProcessExecutionError) as caught:
            process_adapter.windows_powershell()
        assert caught.value.code == "native_windows_powershell_unavailable"
        assert caught.value.reason == "system_root_missing"


@pytest.mark.parametrize("phase", ["spawn", "communication", "completed"])
def test_process_failure_preserves_its_actual_boundary(tmp_path, monkeypatch, phase):
    """Only failure before successful creation is a process-creation error."""
    failure = OSError(5, "boundary probe")
    target, attribute = (
        (subprocess, "Popen") if phase == "spawn" else (subprocess.Popen, "communicate")
    )

    def reject(*args, **_kwargs):
        if phase == "completed":
            if not hasattr(os, "waitid"):
                pytest.skip("Native unreaped child observation requires waitid")
            os.waitid(os.P_PID, args[0].pid, os.WEXITED | os.WNOWAIT)
        raise failure

    monkeypatch.setattr(target, attribute, reject)
    command = (sys.executable, "-c", "pass")
    with pytest.raises(
        process_adapter.ProcessExecutionError if phase == "spawn" else OSError
    ) as caught:
        process_adapter.run_command(tmp_path, command)
    if phase != "spawn":
        assert caught.value is failure
    else:
        assert isinstance(caught.value, process_adapter.ProcessExecutionError)
        assert caught.value.evidence() == {
            "code": "process_creation_failed",
            "reason": "operating_system_rejected_process_creation",
            "command": list(command),
            "cwd": tmp_path.resolve().as_posix(),
            "cause": "OSError: [Errno 5] boundary probe",
        }


@pytest.mark.parametrize("mode", ["key", "prefix", "isolated"])
@pytest.mark.timeout(5)
def test_command_environment_and_native_io(tmp_path, monkeypatch, mode):
    """Native children consume exactly the selected environment and input."""
    environment = {"PSModulePath": "pwsh", "ETHOS_PRESERVED": "inherited", "GIT_PRESERVED": "git"}
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    body = (
        "import json,os,stat,sys; print(json.dumps(dict(os.environ))); "
        "assert stat.S_ISREG(os.fstat(0).st_mode) or not sys.argv[1] == '0'; "
        "sys.stderr.write('output'*16384); sys.stderr.flush(); "
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
        stdin="input" * 16384 if textual else b"input" * 16384,
    )
    observed = json.loads(result.stdout)
    expected_output = "output" * 16384 + "input" * 16384
    assert result.stderr == (expected_output if textual else expected_output.encode())
    expected = {} if mode == "isolated" else environment.copy()
    if mode != "isolated":
        del expected["PSModulePath" if mode == "key" else "GIT_PRESERVED"]
    expected["ETHOS_ADDED"] = "explicit"
    assert {k: observed[k] for k in (*environment, "ETHOS_ADDED") if k in observed} == expected
    with pytest.raises(subprocess.CalledProcessError) as failure:
        process_adapter.run_command(tmp_path, (sys.executable, "-c", body, "7"), check=True)
    assert failure.value.returncode == 7
    assert failure.value.stderr == "output" * 16384
    assert json.loads(failure.value.stdout)["ETHOS_PRESERVED"] == "inherited"


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group boundary")
@pytest.mark.parametrize("failure", ["timeout", "cancel", "gate-cancel", "gate-overlap"])
@pytest.mark.parametrize(
    ("parent_exited", "inherit_pipes"), [(False, False), (False, True), (True, True)]
)
def test_command_failure_closes_owned_descendants(
    tmp_path, monkeypatch, failure, inherit_pipes, parent_exited
):
    """A ready descendant cannot retain its socket after the command is interrupted."""
    fallback = []
    signals = Mock(wraps=os.killpg)
    monkeypatch.setattr(os, "killpg", signals)

    def after_ready(process, _options):
        if parent_exited:
            waitid = getattr(os, "waitid", None)
            assert callable(waitid)
            waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT)
        if failure == "gate-overlap":
            monkeypatch.setattr(subprocess.Popen, "wait", Mock(side_effect=KeyboardInterrupt))
            raise subprocess.TimeoutExpired(process.args, 1)
        if failure == "gate-cancel":

            def rescue():
                fallback.append(True)
                process.poll()
                os.killpg(process.pid, signal.SIGKILL)

            timer = threading.Timer(2, rescue)
            interrupts.callback(timer.join)
            interrupts.callback(timer.cancel)
            timer.start()
            os.kill(os.getpid(), signal.SIGINT)
        elif failure != "timeout":
            raise KeyboardInterrupt

    with ready_descendant(monkeypatch, after_ready) as (child, closed):
        parent = (
            "import subprocess,sys; print('started',flush=True); "
            f"subprocess.Popen([sys.executable,'-c',{child!r}],"
            f"stdout={None if inherit_pipes else subprocess.DEVNULL},"
            f"stderr={None if inherit_pipes else subprocess.DEVNULL})"
            + ("" if parent_exited else ".wait()")
        )

        def execute():
            command = (sys.executable, "-c", parent)
            if not failure.startswith("gate-"):
                process_adapter.run_command(tmp_path, command, timeout=0.2)
            else:
                gate = Gate(id="probe", kind="test", command=command)
                node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
                gate_runner.run_gate_graph(
                    gate_runner.LocalGateRunner(),
                    (node,),
                    {gate.id: gate},
                    root=tmp_path,
                    capacity=1,
                    parallel=True,
                )

        error = subprocess.TimeoutExpired if failure == "timeout" else KeyboardInterrupt
        with pytest.raises(error) as raised, ExitStack() as interrupts:
            execute()
        if failure == "timeout":
            assert isinstance(raised.value, subprocess.TimeoutExpired)
            assert raised.value.output == b"started\n"
        assert closed()
        assert not fallback, "caller cancellation waited for external rescue"
        assert sum(call.args[1] == signal.SIGKILL for call in signals.call_args_list) == 1
