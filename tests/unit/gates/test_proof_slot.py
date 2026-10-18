"""A full proof runs alone on its repository and starts only when host load leaves room."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from filelock import Timeout

import ethos.adapters.gates.proof_slot as proof_slot
from ethos.adapters.store.state.schema import local_state_root
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from pathlib import Path

_HEAD = "a" * 40


class _Host:
    """Fake load, clock and sleep; each sleep advances the clock by its own duration."""

    def __init__(self, loads: list[float | None]) -> None:
        self.loads = loads
        self.now = 0.0
        self.sleeps: list[float] = []
        self.events: list[dict[str, object]] = []

    def load(self) -> float | None:
        return self.loads.pop(0) if len(self.loads) > 1 else self.loads[0]

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def admit(
        self, repo: Path, *, limit: float | None = 8.0, seconds: float = 600.0
    ) -> AbstractContextManager[proof_slot.SlotAdmission]:
        return proof_slot.admitted_full_proof(
            repo,
            head=_HEAD,
            limit=lambda: limit,
            load=self.load,
            clock=lambda: self.now,
            sleep=self.sleep,
            seconds=seconds,
            report=self.events.append,
        )

    def waits(self) -> list[dict[str, object]]:
        return [event for event in self.events if event["event"] == "proof_admission_waiting"]


def _slot(repo: Path) -> tuple[Path, Path]:
    state = local_state_root(repo)
    return state / "proof-slot.lock", state / "proof-slot.json"


def test_an_uncontended_full_proof_starts_without_waiting(tmp_path: Path) -> None:
    """A free slot on a quiet host admits at once and names its holder while it runs."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([2.0])

    with host.admit(repo) as admission:
        holder = json.loads(_slot(repo)[1].read_text(encoding="utf-8"))

    assert host.sleeps == []
    assert (admission.waited_seconds, admission.load, admission.limit) == (0.0, 2.0, 8.0)
    assert holder["head"] == _HEAD
    assert host.events[-1]["event"] == "proof_admission_granted"
    assert not _slot(repo)[1].exists()


def test_a_loaded_host_delays_the_proof_until_load_drops(tmp_path: Path) -> None:
    """Load above the limit delays admission; the proof starts once load falls back."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([20.0, 15.0, 6.0])

    with host.admit(repo) as admission:
        pass

    assert len(host.sleeps) == 2
    assert (admission.load, admission.waited_seconds) == (6.0, sum(host.sleeps))
    assert [(event["reason"], event["load"]) for event in host.waits()] == [("host_load", 20.0)]


_RUNNING = {"pid": 1, "head": "b" * 40}


@pytest.mark.parametrize(
    ("record", "named"),
    [(json.dumps(_RUNNING), _RUNNING), ('{"pid": 1', None), ("[1]", None), (None, None)],
)
def test_a_second_full_proof_waits_for_the_running_one(
    tmp_path: Path, record: str | None, named: dict[str, object] | None
) -> None:
    """A held slot delays admission, names a readable holder, and frees on its release."""
    repo = init_git_repo(tmp_path / "repo")
    lock_path, holder_path = _slot(repo)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    running = FileLock(lock_path)
    running.acquire()
    if record is not None:
        holder_path.write_text(record, encoding="utf-8")

    class _RunningProofEnds(_Host):
        def sleep(self, seconds: float) -> None:
            super().sleep(seconds)
            if len(self.sleeps) == 2:
                holder_path.unlink(missing_ok=True)
                running.release()

    host = _RunningProofEnds([1.0])
    with host.admit(repo) as admission:
        assert json.loads(holder_path.read_text(encoding="utf-8"))["head"] == _HEAD

    assert len(host.sleeps) == 2
    assert admission.waited_seconds == sum(host.sleeps)
    assert [event["reason"] for event in host.waits()] == ["slot_held"]
    assert host.waits()[0]["holder"] == named


def test_contention_that_outlasts_admission_runs_nothing_and_frees_the_slot(
    tmp_path: Path,
) -> None:
    """Admission gives up at its bound with a gap and frees the slot for the next proof."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([30.0])

    with (
        pytest.raises(ValueError, match=r"^proof_admission_contended$") as contended,
        host.admit(repo, seconds=60.0),
    ):
        pytest.fail("no gate may run under contention")

    assert sum(host.sleeps) == 60.0
    lock_path, holder_path = _slot(repo)
    # The failed admission's frame is still referenced, so only an explicit release frees it.
    assert contended.value.args == (proof_slot.CONTENDED,)
    assert FileLock(lock_path).acquire(timeout=0)
    assert not holder_path.exists()


def test_a_proof_that_never_got_the_slot_leaves_the_running_proof_alone(tmp_path: Path) -> None:
    """Giving up while another proof runs neither frees its slot nor erases its holder."""
    repo = init_git_repo(tmp_path / "repo")
    lock_path, holder_path = _slot(repo)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    running = FileLock(lock_path)
    running.acquire()
    holder_path.write_text(json.dumps(_RUNNING), encoding="utf-8")
    host = _Host([1.0])

    with (
        pytest.raises(ValueError, match=r"^proof_admission_contended$"),
        host.admit(repo, seconds=30.0),
    ):
        pytest.fail("no gate may run while another proof holds the slot")

    with pytest.raises(Timeout):
        FileLock(lock_path).acquire(timeout=0)
    assert json.loads(holder_path.read_text(encoding="utf-8")) == _RUNNING


@pytest.mark.parametrize(("limit", "load"), [(8.0, None), (None, 99.0)])
def test_unobservable_load_or_a_disabled_limit_admits_on_the_slot_alone(
    tmp_path: Path, limit: float | None, load: float | None
) -> None:
    """Without a load reading or a limit, only the slot decides admission."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([load])

    with host.admit(repo, limit=limit) as admission:
        pass

    assert host.sleeps == []
    assert (admission.load, admission.limit) == ((None, 8.0) if limit else (None, None))


@pytest.mark.parametrize(("raw", "expected"), [(None, 9.0), ("0", None), ("12.5", 12.5)])
def test_the_load_limit_defaults_to_half_the_cpus(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: float | None
) -> None:
    """Half the CPUs stays free for others unless the host declares another limit."""
    monkeypatch.setattr(proof_slot.os, "cpu_count", lambda: 18)
    if raw is None:
        monkeypatch.delenv(proof_slot.LOAD_LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(proof_slot.LOAD_LIMIT_VARIABLE, raw)

    assert proof_slot.load_limit() == expected


@pytest.mark.parametrize("raw", ["-1", "nan", "inf", "many"])
def test_an_invalid_load_limit_is_refused(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    """A malformed limit fails closed instead of silently disabling admission."""
    monkeypatch.setenv(proof_slot.LOAD_LIMIT_VARIABLE, raw)

    with pytest.raises(ValueError, match=r"^proof_host_load_limit_invalid$"):
        proof_slot.load_limit()


@pytest.mark.parametrize("reported", [True, False])
def test_the_host_load_is_observed_where_the_host_reports_it(
    monkeypatch: pytest.MonkeyPatch, *, reported: bool
) -> None:
    """A host without a load average leaves load unknown instead of failing admission."""
    if reported:
        monkeypatch.setattr(proof_slot.os, "getloadavg", lambda: (3.5, 2.0, 1.0))
    else:
        monkeypatch.delattr(proof_slot.os, "getloadavg")

    assert proof_slot.host_load() == (3.5 if reported else None)


def test_admission_reports_its_grant_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Admission events stay diagnostic stderr lines beside the proof's gate progress."""
    repo = init_git_repo(tmp_path / "repo")

    with proof_slot.admitted_full_proof(repo, head=_HEAD, limit=lambda: None, clock=lambda: 0.0):
        pass

    granted = json.loads(capsys.readouterr().err.splitlines()[-1])
    assert granted == {
        "event": "proof_admission_granted",
        "head": _HEAD,
        "waited_seconds": 0.0,
        "load": None,
        "limit": None,
    }
