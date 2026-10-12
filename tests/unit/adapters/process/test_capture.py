"""Finite native output preserves bytes, text translation and failure custody."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from contextlib import suppress
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.process as process_adapter
from tests.support.subprocesses import ready_descendant

if TYPE_CHECKING:
    from pathlib import Path


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
            assert signum == signal.SIGKILL
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
