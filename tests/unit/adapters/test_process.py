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
from contextlib import nullcontext
from contextlib import suppress
from contextvars import copy_context
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.process as process_adapter
import ethos.adapters.repo.runtime.retirement as retirement
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.subprocesses import ready_descendant


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


def test_cancelled_command_scope_rejects_creation(tmp_path, monkeypatch) -> None:
    """Cancellation fences creation before any native process can start."""
    creation = Mock(wraps=subprocess.Popen)
    monkeypatch.setattr(subprocess, "Popen", creation)
    with process_adapter.command_scope() as scope:
        scope.cancel()
        with pytest.raises(process_adapter.ProcessExecutionError, match="process_cancelled"):
            process_adapter.run_command(tmp_path, (sys.executable, "-c", "pass"), timeout=2)
    creation.assert_not_called()


@pytest.mark.skipif(os.name != "posix", reason="POSIX SIGTERM delivery")
def test_interruption_after_process_creation_retains_and_reaps_child(tmp_path, monkeypatch):
    """Registration must finish before a native termination can escape its start."""
    native = subprocess.Popen
    children = []

    def create(*args, **kwargs):
        child = native(*args, **kwargs)
        children.append(child)
        os.kill(os.getpid(), signal.SIGTERM)
        return child

    monkeypatch.setattr(subprocess, "Popen", create)
    try:
        with (
            pytest.raises(KeyboardInterrupt),
            process_adapter.command_scope(handle_termination=True),
        ):
            process_adapter.run_command(
                tmp_path, (sys.executable, "-c", "import time; time.sleep(30)")
            )
        assert len(children) == 1
        assert children[0].poll() is not None
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=2)


@pytest.mark.skipif(os.name != "posix", reason="POSIX signal delivery")
@pytest.mark.parametrize("boundary", ["scope", "deferral"])
def test_signal_installation_already_owns_restoration(monkeypatch, boundary):
    """A signal between native installation and return cannot leave a replaced handler."""
    original = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    install = signal.signal
    fired = []

    def interrupt_install(number, handler):
        previous = install(number, handler)
        target = signal.SIGTERM if boundary == "scope" else signal.SIGINT
        if number == target and handler != original[number] and not fired:
            fired.append(number)
            os.kill(os.getpid(), signal.SIGTERM)
        return previous

    monkeypatch.setattr(signal, "signal", interrupt_install)
    try:
        with (
            pytest.raises(KeyboardInterrupt),
            process_adapter.command_scope(handle_termination=True),
            process_adapter.defer_interruptions(),
        ):
            pass
        assert fired
        assert all(signal.getsignal(number) == handler for number, handler in original.items())
    finally:
        for number, handler in original.items():
            install(number, handler)


@pytest.mark.skipif(os.name != "posix", reason="POSIX signal delivery")
@pytest.mark.parametrize("boundary", ["registered-return", "process-context"])
@pytest.mark.parametrize("outer_scope", [False, True])
def test_process_handoff_already_owns_reaping_and_pipes(
    tmp_path, monkeypatch, boundary, outer_scope
):
    """Both standalone and scoped callers own a child before its handle can escape."""
    native = subprocess.Popen
    children, outputs, fired = [], [], []

    def deliver():
        fired.append(True)
        os.kill(os.getpid(), signal.SIGINT)

    def create(*args, **kwargs):
        child = native(*args, **kwargs)
        children.append(child)
        outputs.append(kwargs["stdout"])
        return child

    def trace(frame, event, _argument):
        registered_return = (
            event == "return" and frame.f_code is process_adapter.CommandScope.start.__code__
        )
        caller_context = (
            event == "line"
            and frame.f_globals is vars(process_adapter)
            and frame.f_code.co_name == "_execute_command"
            and "process" in frame.f_locals
        )
        if not fired and (registered_return if boundary == "registered-return" else caller_context):
            deliver()
        return trace

    monkeypatch.setattr(subprocess, "Popen", create)
    previous_trace = sys.gettrace()
    try:
        sys.settrace(trace)
        with (
            process_adapter.command_scope() if outer_scope else nullcontext(),
            pytest.raises(KeyboardInterrupt),
        ):
            process_adapter.run_command(
                tmp_path, (sys.executable, "-c", "import time; time.sleep(30)")
            )
        assert fired
        assert len(children) == 1
        child = children[0]
        assert child.returncode is not None
        assert child.stdout is None
        assert child.stderr.closed
        assert all(output.closed for output in outputs)
    finally:
        sys.settrace(previous_trace)
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.__exit__(None, None, None)


def test_command_scope_conserves_one_deadline_across_native_calls(tmp_path, monkeypatch) -> None:
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
        assert command == (str(executable), "-nP", "-F0pftDin")
        assert 0 < kwargs["timeout"] <= 30
        assert kwargs["text"] is False
        if fault == "timeout" or (fault == "slow-scan" and "+D" in command):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        status = 2 if fault == "fatal" else 1 if fault in {"status", "no-match"} else 0
        stderr = b"permission denied" if fault == "stderr" else b""
        return subprocess.CompletedProcess(command, status, payload, stderr)

    monkeypatch.setattr(process_adapter, "run_command", capture)
    observe = process_adapter.process_file_identities
    if fault in {
        "valid",
        "fd-gone",
        "process-gone",
        "named-live-file",
        "unix-inode",
        "slow-scan",
    }:
        assert observe(tmp_path, tree=tmp_path, index=executable) == frozenset({(16, 31), (32, 31)})
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


def _interrupt_first_native_wait(monkeypatch):
    """Interrupt once, then retain the native wait that proves reaping."""
    native_wait = subprocess.Popen.wait
    delivered = False

    def interrupted_wait(child, *args, **kwargs):
        nonlocal delivered
        if not delivered:
            delivered = True
            os.kill(os.getpid(), signal.SIGINT)
        return native_wait(child, *args, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "wait", interrupted_wait)


def _observe_ready_parent(process, parent_exited, failure):
    """Distinguish an unreaped exited leader from a natively reaped leader."""
    if parent_exited:
        waitid = getattr(os, "waitid", None)
        assert callable(waitid)
        waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT)
        if failure == "cancel":
            assert process.poll() == 0


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group boundary")
@pytest.mark.parametrize(
    ("failure", "spool_stdout"),
    [(failure, mode) for failure in ("timeout", "cancel", "terminate") for mode in (False, True)]
    + [(failure, False) for failure in ("gate-cancel", "gate-overlap")],
)
@pytest.mark.parametrize(
    ("parent_exited", "inherit_pipes"), [(False, False), (False, True), (True, True)]
)
def test_command_failure_closes_owned_descendants(
    tmp_path, monkeypatch, failure, inherit_pipes, parent_exited, spool_stdout
):
    """A ready descendant cannot retain its socket after the command is interrupted."""
    fallback = []
    signals = Mock(wraps=os.killpg)
    monkeypatch.setattr(os, "killpg", signals)

    def after_ready(process, _options):
        _observe_ready_parent(process, parent_exited, failure)
        if failure == "gate-overlap":
            _interrupt_first_native_wait(monkeypatch)
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
        elif failure == "terminate":
            os.kill(os.getpid(), signal.SIGTERM)
        elif failure == "cancel":
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
                return process_adapter.run_command(
                    tmp_path, command, timeout=0.2, spool_stdout=spool_stdout
                )
            gate = Gate(id="probe", kind="test", command=command)
            node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
            return gate_runner.run_gate_graph(
                gate_runner.LocalGateRunner(),
                (node,),
                {gate.id: gate},
                root=tmp_path,
                capacity=1,
                parallel=True,
            )

        error = subprocess.TimeoutExpired if failure == "timeout" else KeyboardInterrupt
        completed = failure == "timeout" and spool_stdout and parent_exited
        previous_handler = signal.getsignal(signal.SIGTERM)
        with (
            nullcontext() if completed else pytest.raises(error) as raised,
            ExitStack() as interrupts,
            process_adapter.command_scope(handle_termination=failure == "terminate"),
        ):
            result = execute()
        assert signal.getsignal(signal.SIGTERM) == previous_handler
        if completed:
            assert result.returncode == 0
            assert result.stdout == "started\n"
        else:
            assert getattr(raised.value, "output", None) == (
                b"started\n" if failure == "timeout" else None
            )
        assert closed()
        assert not fallback, "caller cancellation waited for external rescue"
        assert sum(call.args[1] == signal.SIGKILL for call in signals.call_args_list) == 1


@pytest.mark.skipif(os.name != "posix", reason="POSIX nested command-group signals")
@pytest.mark.parametrize("boundary", ["command-timeout", "cli-termination"])
def test_catchable_cancellation_closes_nested_registered_groups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    """A live nested owner gets cancellation before its caller can hard-kill it."""
    marker = tmp_path / "owned-child.pid"

    def after_ready(parent, _options):
        if boundary == "cli-termination":
            parent.send_signal(signal.SIGTERM)

    with ready_descendant(monkeypatch, after_ready) as (body, closed):
        child = (
            "import os; from pathlib import Path; "
            f"Path({str(marker)!r}).write_text(str(os.getpid())); " + body
        )
        launch = (
            "import sys; from pathlib import Path; from types import SimpleNamespace; "
            f"sys.path.insert(0, {str(Path(process_adapter.__file__).resolve().parents[2])!r}); "
            "from ethos.adapters.process import run_command; from ethos import cli; "
            f"command = (sys.executable, '-B', '-I', '-c', {child!r}); "
            "application = SimpleNamespace(load_command_groups=lambda _: None, "
            "dispatch_arguments=lambda args: args, "
            "app=lambda _: run_command(Path.cwd(), command, timeout=10)); "
            "native_import = cli.import_module; "
            "cli.import_module = lambda name: application if "
            "name == 'ethos.surface.cli.application' else native_import(name); "
            "sys.argv = ['ethos', 'probe']; cli.main()"
        )
        try:
            failure = (
                pytest.raises(subprocess.TimeoutExpired)
                if boundary == "command-timeout"
                else nullcontext()
            )
            with failure:
                result = process_adapter.run_command(
                    tmp_path,
                    (sys.executable, "-B", "-I", "-c", launch),
                    timeout=0.2 if boundary == "command-timeout" else 10,
                )
                assert result.returncode != 0
            assert closed(), "catchable cancellation left the registered child's socket open"
        finally:
            if marker.exists():
                with suppress(ProcessLookupError):
                    os.killpg(int(marker.read_text()), signal.SIGKILL)
