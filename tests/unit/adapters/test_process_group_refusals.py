"""Darwin's refusals to signal an owned process group: exiting leaders, zombies and survivors."""

import os
import signal
from contextlib import nullcontext
from unittest.mock import Mock

import pytest

import ethos.adapters.process as process_adapter


@pytest.mark.skipif(os.name != "posix", reason="Darwin process-group semantics")
@pytest.mark.parametrize("survivor", [False, True])
def test_exited_group_waits_for_reaping_but_never_ignores_a_survivor(
    monkeypatch, *, survivor: bool
) -> None:
    """Zombies a reaper has yet to collect clear within the bound; a lasting refusal stays loud."""
    signals: list[int] = []

    def killpg(_pid: int, sent: int) -> None:
        signals.append(sent)
        if survivor or len(signals) < 4:
            raise PermissionError(1, "Operation not permitted")
        raise ProcessLookupError(3, "No such process")

    monkeypatch.setattr(os, "killpg", killpg)
    exited = Mock(pid=4242, returncode=0, **{"poll.return_value": 0, "wait.return_value": 0})
    terminate = vars(process_adapter)["_terminate_command"]
    with pytest.raises(PermissionError) if survivor else nullcontext():
        terminate(exited, deadline=process_adapter.monotonic() + 0.2)
    assert signals[0] == signal.SIGKILL
    assert set(signals[1:]) == {0}


def _leader(*, exits_after_check: bool) -> Mock:
    """A leader that runs at its first poll and, when it exits, reports that at every later poll."""
    polls: list[int] = []

    def poll() -> int | None:
        polls.append(1)
        return 0 if exits_after_check and len(polls) > 1 else None

    return Mock(pid=4242, returncode=0, **{"poll.side_effect": poll, "wait.return_value": 0})


@pytest.mark.skipif(os.name != "posix", reason="Darwin process-group semantics")
@pytest.mark.parametrize("survivor", [False, True])
def test_a_leader_that_exits_before_its_interrupt_leaves_the_group_to_its_bounded_close(
    monkeypatch, *, survivor: bool
) -> None:
    """EPERM from interrupting a just-exited leader is Darwin's unreaped group, not a survivor."""
    signals: list[int] = []

    def killpg(_pid: int, sent: int) -> None:
        signals.append(sent)
        if sent == signal.SIGINT or survivor or len(signals) < 4:
            raise PermissionError(1, "Operation not permitted")
        raise ProcessLookupError(3, "No such process")

    monkeypatch.setattr(os, "killpg", killpg)
    terminate = vars(process_adapter)["_terminate_commands"]
    with pytest.raises(PermissionError) if survivor else nullcontext():
        terminate((_leader(exits_after_check=True),), grace_seconds=0.2)
    assert signals[:2] == [signal.SIGINT, signal.SIGKILL]


@pytest.mark.skipif(os.name != "posix", reason="Darwin process-group semantics")
def test_a_leader_still_exiting_when_refused_is_not_a_survivor(monkeypatch) -> None:
    """Darwin refuses a leader that is exiting before it can be reaped; the grace settles it."""
    signals: list[int] = []

    def killpg(_pid: int, sent: int) -> None:
        signals.append(sent)
        if sent == signal.SIGKILL:
            raise PermissionError(1, "Operation not permitted")
        raise ProcessLookupError(3, "No such process")

    monkeypatch.setattr(os, "killpg", killpg)
    terminate = vars(process_adapter)["_terminate_command"]
    terminate(_leader(exits_after_check=True), deadline=process_adapter.monotonic() + 0.2)
    assert signals == [signal.SIGKILL, 0]


@pytest.mark.skipif(os.name != "posix", reason="Darwin process-group semantics")
def test_a_running_leader_that_refuses_its_interrupt_still_fails_cleanup(monkeypatch) -> None:
    """A refusal while the leader still runs is a survivor, which must not be ignored."""

    def killpg(_pid: int, _sent: int) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "killpg", killpg)
    terminate = vars(process_adapter)["_terminate_commands"]
    with pytest.raises(ExceptionGroup):
        terminate((_leader(exits_after_check=False),), grace_seconds=0.05)
