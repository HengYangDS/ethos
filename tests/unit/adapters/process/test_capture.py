"""Finite native output preserves bytes, text translation and failure custody."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
from contextlib import ExitStack
from contextlib import suppress
from pathlib import Path

import pytest

import ethos.adapters.process as process_adapter
from tests.support.subprocesses import ready_descendant


@pytest.mark.timeout(30)
@pytest.mark.parametrize("spool_stdout", [False, True])
def test_native_output_is_captured_through_regular_files(
    tmp_path: Path, *, spool_stdout: bool
) -> None:
    """Native stdout is regular-file backed with optional finite diagnostic capture."""
    body = (
        "import os,stat,sys; "
        "assert os.name!='posix' or stat.S_ISREG(os.fstat(1).st_mode); "
        "assert os.name!='posix' or sys.argv[1]=='False' or stat.S_ISREG(os.fstat(2).st_mode); "
        "sys.stdout.buffer.write(b'o' * 8388608); sys.stderr.buffer.write(b'e' * 65536)"
    )
    result = process_adapter.run_command(
        tmp_path,
        (sys.executable, "-c", body, str(spool_stdout)),
        text=False,
        check=True,
        timeout=20,
        spool_stdout=spool_stdout,
    )
    assert (result.stdout, result.stderr) == (b"o" * 8388608, b"e" * 65536)


@pytest.mark.parametrize("text", [False, True])
@pytest.mark.parametrize("outcome", ["success", "nonzero", "timeout"])
def test_bulk_stdout_preserves_native_output_and_closes_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, text: bool, outcome: str
) -> None:
    """A finite producer retains output and closes its invocation-local capture."""
    opened = []
    temporary_file = process_adapter.TemporaryFile

    def capture(*args, **kwargs):
        value = temporary_file(*args, **kwargs)
        opened.append(value)
        return value

    monkeypatch.setattr(process_adapter, "TemporaryFile", capture)
    payload = b"first\r\nsecond\rthird\n" * 65_536
    diagnostic = b"diagnostic\r\nnext\rlast\n"
    body = (
        "import os,stat,sys,time; "
        "assert os.name!='posix' or all(stat.S_ISREG(os.fstat(fd).st_mode) for fd in (1,2)); "
        "sys.stdout.buffer.write(b'first\\r\\nsecond\\rthird\\n'*65536); "
        "sys.stdout.flush(); sys.stderr.buffer.write(b'diagnostic\\r\\nnext\\rlast\\n'); "
        "sys.stderr.flush(); "
        "time.sleep(10) if sys.argv[1]=='timeout' else None; "
        "raise SystemExit(7 if sys.argv[1]=='nonzero' else 0)"
    )
    command = (sys.executable, "-c", body, outcome)
    options = {"text": text, "check": True, "spool_stdout": True}
    expected = "first\nsecond\nthird\n" * 65_536 if text else payload
    if outcome == "success":
        result = process_adapter.run_command(tmp_path, command, timeout=5, **options)
        assert result.stdout == expected
        assert result.stderr == ("diagnostic\nnext\nlast\n" if text else diagnostic)
        assert result.returncode == 0
    else:
        failure = (
            subprocess.TimeoutExpired if outcome == "timeout" else subprocess.CalledProcessError
        )
        with pytest.raises(failure) as caught:
            process_adapter.run_command(
                tmp_path, command, timeout=1 if outcome == "timeout" else 5, **options
            )
        if outcome == "timeout":
            assert caught.value.stdout == payload
            assert caught.value.stderr == diagnostic
        else:
            assert caught.value.returncode == 7
            assert caught.value.stdout == expected
            assert caught.value.stderr == ("diagnostic\nnext\nlast\n" if text else diagnostic)
    assert len(opened) == (2 if os.name == "posix" else 0)
    assert all(value.closed for value in opened)


@pytest.mark.parametrize("text", [False, True])
def test_bulk_stdout_timeout_retains_closed_stderr(tmp_path: Path, *, text: bool) -> None:
    """Closing the diagnostic pipe does not discard bytes when native wait times out."""
    body = (
        "import os,sys,time; sys.stdout.buffer.write(b'output\\r\\n'); sys.stdout.flush(); "
        "sys.stderr.buffer.write(b'diagnostic\\r\\n'); sys.stderr.flush(); os.close(2); "
        "time.sleep(10)"
    )
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        process_adapter.run_command(
            tmp_path, (sys.executable, "-c", body), timeout=1, text=text, spool_stdout=True
        )
    assert caught.value.stdout == b"output\r\n"
    assert caught.value.stderr == b"diagnostic\r\n"


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group boundary")
@pytest.mark.parametrize("parent_returncode", [0, 7])
def test_bulk_stdout_closes_stdout_only_descendant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, parent_returncode: int
) -> None:
    """A completed finite producer cannot leave its stdout-only descendant alive."""
    launched = []

    def after_ready(process, _options):
        launched.append(process)

    with ready_descendant(monkeypatch, after_ready) as (child, closed):
        body = (
            "import subprocess,sys; print('output',flush=True); "
            f"subprocess.Popen([sys.executable,'-c',{child!r}],stderr=subprocess.DEVNULL)"
            f"; raise SystemExit({parent_returncode})"
        )
        released = False
        try:
            result = process_adapter.run_command(
                tmp_path, (sys.executable, "-c", body), timeout=1, text=False, spool_stdout=True
            )
            assert result.returncode == parent_returncode
            assert result.stdout == b"output\n"
            assert closed()
            released = True
        finally:
            if not released:
                for process in launched:
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)


@pytest.mark.parametrize("outcome", ["success", "nonzero", "timeout"])
@pytest.mark.parametrize("spool_stdout", [False, True])
def test_native_command_owns_its_handle_without_an_outer_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str, *, spool_stdout: bool
) -> None:
    """Every native command registers and releases one real owned process."""
    started: list[tuple[process_adapter.CommandScope, subprocess.Popen[str]]] = []
    terminated: list[subprocess.Popen[str]] = []
    discarded: list[subprocess.Popen[str]] = []
    start = process_adapter.CommandScope.start
    discard = process_adapter.CommandScope.discard

    def observed_start(
        owner: process_adapter.CommandScope, command: tuple[str, ...], **options: object
    ) -> subprocess.Popen[str]:
        child = start(owner, command, **options)
        started.append((owner, child))
        return child

    if os.name == "posix":
        killpg = os.killpg

        def observed_group_termination(pid: int, signum: int) -> None:
            child = next(child for _, child in started if child.pid == pid)
            assert signum in {signal.SIGINT, signal.SIGKILL}
            if signum == signal.SIGKILL:
                terminated.append(child)
            killpg(pid, signum)

        monkeypatch.setattr(os, "killpg", observed_group_termination)
    else:
        kill = subprocess.Popen.kill

        def observed_process_termination(child: subprocess.Popen[str]) -> None:
            assert any(child is registered for _, registered in started)
            terminated.append(child)
            kill(child)

        monkeypatch.setattr(subprocess.Popen, "kill", observed_process_termination)

    def observed_discard(owner: process_adapter.CommandScope, child: subprocess.Popen[str]) -> None:
        assert (owner, child) in started
        assert child.returncode is not None
        discarded.append(child)
        discard(owner, child)

    monkeypatch.setattr(process_adapter.CommandScope, "start", observed_start)
    monkeypatch.setattr(process_adapter.CommandScope, "discard", observed_discard)
    body = "import time; time.sleep(1)" if outcome == "timeout" else "raise SystemExit(7)"
    if outcome == "success":
        body = "print('complete')"
    command = (sys.executable, "-c", body)
    if outcome == "success":
        result = process_adapter.run_command(
            tmp_path, command, check=True, spool_stdout=spool_stdout
        )
        assert result.returncode == 0
        assert result.stdout == "complete\n"
    else:
        failure = (
            subprocess.TimeoutExpired if outcome == "timeout" else subprocess.CalledProcessError
        )
        with pytest.raises(failure):
            process_adapter.run_command(
                tmp_path,
                command,
                check=True,
                timeout=0.1 if outcome == "timeout" else 2,
                spool_stdout=spool_stdout,
            )
    assert len(started) == 1
    child = started[0][1]
    assert child.returncode is not None
    assert discarded == [child]
    assert terminated == (
        [child] if outcome != "success" or (spool_stdout and os.name == "posix") else []
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX native execution-group cancellation")
def test_cancellation_reaches_native_nox_pytest_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Official executors can release a worker's separately registered native child."""
    source_root = str(Path(process_adapter.__file__).resolve().parents[2])
    marker = tmp_path / "owned-child.pid"
    with ready_descendant(monkeypatch, lambda *_: None) as (body, closed):
        child = (
            "import os; from pathlib import Path; "
            f"Path({str(marker)!r}).write_text(str(os.getpid())); " + body
        )
        (tmp_path / "test_owned.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            f"sys.path.insert(0, {source_root!r})\n"
            "from ethos.adapters.process import command_scope, run_command\n"
            "def test_owned():\n"
            "    with command_scope(handle_termination=True):\n"
            f"        run_command(Path.cwd(), (sys.executable, '-B', '-I', '-c', {child!r}), "
            "timeout=20)\n"
        )
        (tmp_path / "noxfile.py").write_text(
            "import nox, sys\n"
            "nox.options.default_venv_backend = 'none'\n"
            "@nox.session(python=False)\n"
            "def tests(session):\n"
            "    session.run(sys.executable, '-B', '-m', 'pytest', '-n', '1', "
            "'--max-worker-restart=0', '-q', 'test_owned.py')\n"
        )
        command = (sys.executable, "-B", "-m", "nox", "-s", "tests")
        launch = (
            "import sys; from pathlib import Path; from types import SimpleNamespace; "
            f"sys.path.insert(0, {source_root!r}); "
            "from ethos.adapters.process import run_command; from ethos import cli; "
            "application = SimpleNamespace(load_command_groups=lambda _: None, "
            "dispatch_arguments=lambda args: args, "
            f"app=lambda _: run_command(Path.cwd(), {command!r}, timeout=20, spool_stdout=True)); "
            "native_import = cli.import_module; "
            "cli.import_module = lambda name: application if "
            "name == 'ethos.surface.cli.application' else native_import(name); "
            "sys.argv = ['ethos', 'probe']; cli.main()"
        )
        try:
            with pytest.raises(subprocess.TimeoutExpired):
                process_adapter.run_command(
                    tmp_path,
                    (sys.executable, "-B", "-I", "-c", launch),
                    timeout=0.2,
                    spool_stdout=True,
                )
            assert closed(), "executor interruption lost the worker's registered child"
        finally:
            if marker.exists():
                with suppress(ProcessLookupError):
                    os.killpg(int(marker.read_text()), signal.SIGKILL)


@pytest.mark.skipif(os.name != "posix", reason="POSIX catchable-signal fallback")
def test_uncooperative_native_command_is_killed_and_reaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignoring cooperative interruption cannot retain the owned group or its socket."""
    children = []
    with ready_descendant(monkeypatch, lambda child, _: children.append(child)) as (body, closed):
        command = "import signal; signal.signal(signal.SIGINT, signal.SIG_IGN); " + body
        with pytest.raises(subprocess.TimeoutExpired) as caught:
            process_adapter.run_command(
                tmp_path, (sys.executable, "-c", command), timeout=0.1, spool_stdout=True
            )
        assert caught.value.timeout == 0.1
        assert children[0].returncode == -signal.SIGKILL
        assert closed()


@pytest.mark.skipif(os.name != "posix", reason="POSIX shared cancellation budget")
def test_nested_scope_cancels_all_registered_groups_with_one_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An outer deadline cannot strand later groups while the first consumes its grace."""
    count = 3
    source_root = str(Path(process_adapter.__file__).resolve().parents[2])
    native_communicate = subprocess.Popen.communicate
    with ExitStack() as resources:
        listener = resources.enter_context(socket.create_server(("127.0.0.1", 0)))
        listener.settimeout(10)
        connections = []
        child = (
            "import os,socket,signal,sys; from pathlib import Path; "
            "signal.signal(signal.SIGINT, signal.SIG_IGN); "
            "Path(sys.argv[1]).write_text(str(os.getpid())); "
            f"s=socket.create_connection({listener.getsockname()!r},timeout=10); "
            "s.settimeout(None); s.sendall(b'R'); s.recv(1)"
        )
        markers = [tmp_path / f"owned-{i}.pid" for i in range(count)]
        commands = [(sys.executable, "-B", "-I", "-c", child, str(m)) for m in markers]
        launch = (
            "import sys; from pathlib import Path; from types import SimpleNamespace; "
            "from concurrent.futures import ThreadPoolExecutor; "
            "from contextvars import copy_context; "
            f"sys.path.insert(0, {source_root!r}); "
            "from ethos.adapters.process import command_scope, run_command; from ethos import cli\n"
            "def app(_):\n"
            f"    with ThreadPoolExecutor(max_workers={count}) as pool, command_scope():\n"
            f"        futures=[pool.submit(copy_context().run, run_command, Path.cwd(), c, "
            f"timeout=10) for c in {commands!r}]\n"
            "        for future in futures: future.result()\n"
            "application=SimpleNamespace(load_command_groups=lambda _: None, "
            "dispatch_arguments=lambda args: args, app=app)\n"
            "native_import=cli.import_module\n"
            "cli.import_module=lambda name: application if "
            "name=='ethos.surface.cli.application' else native_import(name)\n"
            "sys.argv=['ethos','probe']; cli.main()"
        )

        def ready(process, *args, **kwargs):
            for _ in range(count):
                connection = resources.enter_context(listener.accept()[0])
                connection.settimeout(2)
                assert connection.recv(1) == b"R"
                connections.append(connection)
            return native_communicate(process, *args, **kwargs)

        monkeypatch.setattr(subprocess.Popen, "communicate", ready)
        try:
            with pytest.raises(subprocess.TimeoutExpired):
                process_adapter.run_command(
                    tmp_path, (sys.executable, "-B", "-I", "-c", launch), timeout=0.1
                )
            assert all(connection.recv(1) == b"" for connection in connections)
        finally:
            for marker in markers:
                if marker.exists():
                    with suppress(ProcessLookupError):
                        os.killpg(int(marker.read_text()), signal.SIGKILL)
