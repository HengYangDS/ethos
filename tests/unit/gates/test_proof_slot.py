"""A full proof runs alone on its repository and starts only when host load leaves room."""

from __future__ import annotations

import json
import os
import re
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from filelock import FileLock
from filelock import Timeout

import ethos.adapters.gates.host_admission as host_admission
import ethos.adapters.gates.proof_slot as proof_slot
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tests.support.clock import FakeClock
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager
    from pathlib import Path

_HEAD = "a" * 40


class _Host(FakeClock):
    """Fake load beside the fake clock, whose sleeps advance it by their own duration."""

    def __init__(self, loads: list[float | None]) -> None:
        super().__init__()
        self.loads = loads
        self.events: list[dict[str, object]] = []

    def load(self) -> float | None:
        return self.loads.pop(0) if len(self.loads) > 1 else self.loads[0]

    def admit(
        self,
        repo: Path,
        *,
        limit: float | None = 8.0,
        seconds: float = 600.0,
        current: Callable[[], bool] = lambda: True,
    ) -> AbstractContextManager[proof_slot.SlotAdmission]:
        return proof_slot.admitted_full_proof(
            repo,
            head=_HEAD,
            current=current,
            limit=lambda: (limit, "test"),
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

    assert host.sleeps == [15.0]
    assert (admission.waited_seconds, admission.load, admission.limit) == (15.0, 2.0, 8.0)
    assert holder["head"] == _HEAD
    assert host.events[-1]["event"] == "proof_admission_granted"
    assert not _slot(repo)[1].exists()


def test_a_loaded_host_delays_the_proof_until_load_drops(tmp_path: Path) -> None:
    """Load above the limit delays admission; the proof starts once load falls back."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([20.0, 15.0, 6.0])

    with host.admit(repo) as admission:
        pass

    assert len(host.sleeps) == 3
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

    assert len(host.sleeps) == 3
    assert admission.waited_seconds == sum(host.sleeps)
    assert [event["reason"] for event in host.waits()] == ["slot_held", "host_load"]
    assert host.waits()[0]["holder"] == named


def test_contention_that_outlasts_admission_runs_nothing_and_frees_the_slot(tmp_path: Path) -> None:
    """Admission gives up at its bound with a gap and frees the slot for the next proof."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([30.0])

    with (
        pytest.raises(ValueError, match=r"^proof_admission_contended:load=30.0:") as contended,
        host.admit(repo, seconds=60.0),
    ):
        pytest.fail("no gate may run under contention")

    assert sum(host.sleeps) == pytest.approx(60.0)
    lock_path, holder_path = _slot(repo)
    # The failed admission's frame is still referenced, so only an explicit release frees it.
    assert contended.value.args == (f"{proof_slot.CONTENDED}:load=30.0:limit=8.0:source=test",)
    assert FileLock(lock_path).acquire(timeout=0)
    assert not holder_path.exists()


@pytest.mark.parametrize(("observations", "sleeps"), [([False], 0), ([True, True, False], 2)])
def test_a_lane_whose_candidate_moves_on_runs_nothing_and_frees_the_slot(
    tmp_path: Path, observations: list[bool], sleeps: int
) -> None:
    """A lane base that falls behind its candidate, at start or while waiting, ends admission."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([30.0])
    checks = iter(observations)

    with (
        pytest.raises(ValueError, match=r"^candidate_base_stale$") as stale,
        host.admit(repo, current=lambda: next(checks)),
    ):
        pytest.fail("no gate may run for a lane that can no longer land")

    assert len(host.sleeps) == sleeps
    lock_path, holder_path = _slot(repo)
    # The failed admission's frame is still referenced, so only an explicit release frees it.
    assert stale.value.args == (proof_slot.STALE,)
    assert FileLock(lock_path).acquire(timeout=0)
    assert not holder_path.exists()


def test_only_a_work_lane_behind_its_candidate_is_stale(tmp_path: Path) -> None:
    """A lane is judged against its candidate; other checkouts and clones without one are not."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "--quiet", "-c", "work/lane")
    lane = proof_slot.candidate_current(repo, head=head)
    without_candidate = lane()
    git(repo, "branch", "candidate/dev")
    with_candidate = lane()

    git(repo, "switch", "--quiet", "candidate/dev")
    commit_fixture_file(repo, "landed.txt", "landed\n", "chore: land another lane")
    git(repo, "switch", "--quiet", "dev")

    assert (without_candidate, with_candidate, lane()) == (True, True, False)
    assert proof_slot.candidate_current(repo, head=head)()


def test_admission_judges_its_own_lane_by_default(tmp_path: Path) -> None:
    """Without an injected judgment, admission derives staleness from the repository itself."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "--quiet", "-c", "candidate/dev")
    commit_fixture_file(repo, "landed.txt", "landed\n", "chore: land another lane")
    git(repo, "switch", "--quiet", "-c", "work/lane", head)

    with (
        pytest.raises(ValueError, match=r"^candidate_base_stale$"),
        proof_slot.admitted_full_proof(
            repo, head=head, limit=lambda: (None, "test"), report=[].append
        ),
    ):
        pytest.fail("no gate may run for a lane that can no longer land")


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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, (9.0, "default")), ("0", (None, "environment")), ("12.5", (12.5, "environment"))],
)
def test_the_load_limit_defaults_to_half_the_cpus(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: tuple[float | None, str]
) -> None:
    """Half the CPUs stays free for others unless the run or the host declares another limit."""
    monkeypatch.setattr(proof_slot.os, "cpu_count", lambda: 18)
    if raw is None:
        monkeypatch.delenv(proof_slot.LOAD_LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(proof_slot.LOAD_LIMIT_VARIABLE, raw)

    assert proof_slot.effective_load_limit() == expected


@pytest.mark.parametrize("raw", ["-1", "nan", "inf", "many"])
def test_an_invalid_load_limit_is_refused(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    """A malformed limit fails closed instead of silently disabling admission."""
    monkeypatch.setenv(proof_slot.LOAD_LIMIT_VARIABLE, raw)

    with pytest.raises(ValueError, match=r"^proof_host_load_limit_invalid$"):
        proof_slot.effective_load_limit()


@pytest.mark.parametrize(
    ("averages", "expected"), [((3.5, 2.0, 1.0), 3.5), ((3.5, 12.0, 20.0), 3.5), (None, None)]
)
def test_the_host_load_is_the_one_minute_load_where_the_host_reports_it(
    monkeypatch: pytest.MonkeyPatch,
    averages: tuple[float, float, float] | None,
    expected: float | None,
) -> None:
    """The 5-minute average lags a finished run by minutes; two calm 1-minute samples admit."""
    # Windows has no such reading: the patch may meet a host without the name.
    if averages is not None:
        monkeypatch.setattr(proof_slot.os, "getloadavg", lambda: averages, raising=False)
    else:
        monkeypatch.delattr(proof_slot.os, "getloadavg", raising=False)

    assert proof_slot.host_load() == expected


def test_admission_reports_its_grant_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Admission events stay diagnostic stderr lines beside the proof's gate progress."""
    repo = init_git_repo(tmp_path / "repo")

    with proof_slot.admitted_full_proof(
        repo, head=_HEAD, limit=lambda: (None, "test"), clock=lambda: 0.0
    ):
        pass

    granted = json.loads(capsys.readouterr().err.splitlines()[-1])
    assert granted == {
        "event": "proof_admission_granted",
        "head": _HEAD,
        "load_measured": False,
        "limit_source": "test",
        "waited_seconds": 0.0,
        "load": None,
        "limit": None,
    }


def test_a_full_proof_takes_the_host_slot_between_its_slot_and_load(tmp_path: Path) -> None:
    """Another heavy run that holds the host delays the proof after its repository slot is held."""
    repo = init_git_repo(tmp_path / "repo")
    queue = host_admission.host_queue()[0]
    render = queue.enter(tmp_path / "film", "renderer", operation="host.run")

    class _RenderEnds(_Host):
        def sleep(self, seconds: float) -> None:
            super().sleep(seconds)
            if len(self.sleeps) == 1:
                queue.leave(render)

    host = _RenderEnds([20.0, 4.0])
    with host.admit(repo) as admission:
        token = os.environ[host_admission.ADMISSION_ENV]
        assert queue.holds(token)

    assert [event["reason"] for event in host.waits()] == ["host_slot_held", "host_load"]
    holder = host.waits()[0]["holder"]
    assert isinstance(holder, dict)
    assert holder["executable"] == "renderer"
    assert "repository" not in holder
    assert holder["operation"] == "host.run"
    assert str(tmp_path) not in json.dumps(host.waits()[0])
    assert admission.load == pytest.approx(4.0)
    assert host_admission.ADMISSION_ENV not in os.environ
    assert not queue.live()


def test_a_full_proof_keeps_its_place_behind_a_live_holder(tmp_path: Path) -> None:
    """A render that alone outlasts the bound ends no wait, and the load wait has the bound."""
    repo = init_git_repo(tmp_path / "repo")
    queue = host_admission.host_queue()[0]
    renders = [queue.enter(tmp_path / "work", "renderer", operation="host.run")]

    class _RenderEnds(_Host):
        def sleep(self, seconds: float) -> None:
            super().sleep(seconds)
            if self.now >= 6400 and renders:
                queue.leave(renders.pop())

    host = _RenderEnds([20.0, 4.0])
    with host.admit(repo, seconds=3600.0) as admission:
        pass

    # The proof sees the render gone at 6,405 seconds, then waits two calm samples for the load.
    assert admission.waited_seconds == pytest.approx(6435.0)
    assert [event["reason"] for event in host.waits()] == ["host_slot_held", "host_load"]
    assert not queue.live()


@pytest.mark.parametrize(
    ("seconds", "slot_free", "render_gone", "ended", "polls"),
    [
        (3600.0, 3480, 3495, 3615.0, 241),  # 3,480 s for the slot leave the load 120, not 3,600
        (3594.0, 3585, 3630, 3639.0, 243),  # the 9 s left never shorten a poll behind the render
    ],
)
def test_the_slot_wait_and_the_load_wait_share_one_bound(
    tmp_path: Path, seconds: float, slot_free: int, render_gone: int, ended: float, polls: int
) -> None:
    """Only the time behind a live holder of the host slot is left out of a full proof's bound."""
    repo = init_git_repo(tmp_path / "repo")
    lock_path, _record = _slot(repo)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    running = FileLock(lock_path)
    running.acquire()
    queue = host_admission.host_queue()[0]
    render = queue.enter(tmp_path / "work", "renderer", operation="host.run")
    releases = [(slot_free, running.release), (render_gone, lambda: queue.leave(render))]

    class _HoldersEnd(_Host):
        def sleep(self, seconds: float) -> None:
            super().sleep(seconds)
            while releases and self.now >= releases[0][0]:
                releases.pop(0)[1]()

    host = _HoldersEnd([30.0])
    with (
        pytest.raises(ValueError, match=r"^proof_admission_contended:load=30\.0:"),
        host.admit(repo, seconds=seconds),
    ):
        pytest.fail("no gate may run under contention")

    reasons = [event["reason"] for event in host.waits()]
    assert reasons == ["slot_held", "host_slot_held", "host_load"]
    # The bound ran for the slot and for the load, and stood still behind the render.
    assert (host.now, len(host.sleeps)) == (ended, polls)
    assert not queue.live()


def test_a_full_proofs_whole_wait_ends_at_the_declared_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A render that never leaves ends the proof's wait at the ceiling, not at its bound."""
    monkeypatch.setattr(proof_slot, "_POLL_SECONDS", 600.0)
    ceiling = load_repository_paradigm().parameter_row("timeout", "admission_seconds").bound
    repo = init_git_repo(tmp_path / "repo")
    queue = host_admission.host_queue()[0]
    render = queue.enter(tmp_path / "work", "renderer", operation="host.run")

    class _Guarded(_Host):
        def sleep(self, seconds: float) -> None:
            super().sleep(seconds)
            assert self.now <= ceiling, "the wait outlasted the ceiling"

    host = _Guarded([1.0])
    with (
        pytest.raises(ValueError, match=r"^host_admission_contended:host\.run:"),
        host.admit(repo, seconds=3600.0),
    ):
        pytest.fail("no gate may run behind a holder that never leaves")

    assert (ceiling, host.now) == (36_000, 36_000.0)
    queue.leave(render)


_NOT_LEFT = "host_admission_unavailable: PermissionError"


@pytest.mark.parametrize(
    ("ending", "raised", "message", "cause", "notes"),
    [
        ("admitted", ValueError, "^host_admission_unavailable$", PermissionError, []),
        ("bound", ValueError, r"^proof_admission_contended:load=30\.0:", type(None), [_NOT_LEFT]),
        ("interrupt", KeyboardInterrupt, "^$", type(None), [_NOT_LEFT]),
    ],
)
def test_a_host_place_that_cannot_be_given_up_still_frees_the_repositorys_slot(
    tmp_path: Path,
    ending: str,
    raised: type[BaseException],
    message: str,
    cause: type,
    notes: list[str],
) -> None:
    """An OS error while leaving is the named gap after a normal end and keeps an exit in flight.

    The repository's slot and its record go in every case, so the next proof is not held.
    """
    repo = init_git_repo(tmp_path / "repo")
    queue = host_admission.host_queue()[0]
    refused = Mock(side_effect=PermissionError)

    class _Ends(_Host):
        def sleep(self, seconds: float) -> None:
            if ending == "interrupt":
                raise KeyboardInterrupt
            super().sleep(seconds)

    host = _Ends([2.0 if ending == "admitted" else 30.0])
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(host_admission.HostQueue, "leave", refused)
        with pytest.raises(raised) as ended, host.admit(repo, seconds=60.0):
            pass

    # The message alone is the gap that a caller reads; pytest's own match would read the note too.
    assert re.search(message, str(ended.value)) is not None
    assert isinstance(ended.value.__cause__, cause)
    assert getattr(ended.value, "__notes__", []) == notes
    lock_path, holder_path = _slot(repo)
    # The ended admission's frame is still referenced, so only an explicit release frees the slot.
    assert FileLock(lock_path).acquire(timeout=0)
    assert not holder_path.exists()
    # The mock kept the proof's own ticket; the real release then empties the queue.
    for call in refused.call_args_list:
        queue.leave(call.args[0])
    assert refused.call_count == 1
    assert not queue.live()


def test_a_full_proof_names_a_host_queue_that_cannot_be_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A place that cannot be taken is the named gap, as it is for a host proof, not a traceback."""
    repo = init_git_repo(tmp_path / "repo")
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "host-admission").write_text("a file where the queue belongs", encoding="utf-8")
    monkeypatch.setattr(host_admission, "host_store_root", lambda: blocked)

    with (
        pytest.raises(ValueError, match=r"^host_admission_unavailable$") as refused,
        _Host([2.0]).admit(repo),
    ):
        pytest.fail("an unwritable queue admitted a proof")

    # Which OS error a file in the queue's place raises differs by platform.
    assert isinstance(refused.value.__cause__, OSError)
    lock_path, holder_path = _slot(repo)
    assert FileLock(lock_path).acquire(timeout=0)
    assert not holder_path.exists()


@pytest.mark.parametrize("read", ["host_queue", "ahead", "contention"])
def test_a_host_queue_that_cannot_be_read_is_the_named_gap_at_every_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, read: str
) -> None:
    """Opening the queue, naming the holder ahead and naming the contention each answer the gap."""
    monkeypatch.setattr(proof_slot, "_POLL_SECONDS", 6000.0)
    repo = init_git_repo(tmp_path / "repo")
    queue = host_admission.host_queue()[0]
    render = queue.enter(tmp_path / "work", "renderer", operation="host.run")
    owner = host_admission if read == "host_queue" else host_admission.HostQueue

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(owner, read, Mock(side_effect=PermissionError))
        with (
            pytest.raises(ValueError, match=r"^host_admission_unavailable$") as refused,
            _Host([2.0]).admit(repo, seconds=60.0),
        ):
            pytest.fail("a queue that cannot be read admitted a proof")

    assert isinstance(refused.value.__cause__, PermissionError)
    lock_path, holder_path = _slot(repo)
    assert FileLock(lock_path).acquire(timeout=0)
    assert not holder_path.exists()
    queue.leave(render)


def _kept(suffix: str) -> Callable[..., None]:
    """Remove every file but those of one suffix, which refuse as a protected directory does."""
    unlink = os.unlink

    def kept(path: object, *arguments: object, **options: object) -> None:
        if str(path).endswith(suffix):
            raise PermissionError
        unlink(path, *arguments, **options)

    return kept


def test_a_slot_record_that_cannot_be_removed_still_frees_the_slot(tmp_path: Path) -> None:
    """The record names the holder for a reader; left behind, it holds no next proof."""
    repo = init_git_repo(tmp_path / "repo")
    lock_path, holder_path = _slot(repo)

    with pytest.MonkeyPatch.context() as patch, _Host([2.0]).admit(repo):
        patch.setattr(os, "unlink", _kept(holder_path.name))

    assert FileLock(lock_path).acquire(timeout=0)
    assert holder_path.exists()


def test_a_host_without_a_load_average_records_it_unmeasured(tmp_path: Path) -> None:
    """The host slot still serializes, and the admission says that load was not measured."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([None])

    with host.admit(repo) as admission:
        pass

    assert admission.load is None
    assert host.events[-1]["load_measured"] is False


def test_two_calm_one_minute_samples_admit_the_proof(tmp_path: Path) -> None:
    """A single dip between busy phases does not admit; two consecutive calm samples do."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([5.0, 20.0, 5.0, 6.0])

    with host.admit(repo) as admission:
        pass

    assert len(host.sleeps) == 3
    assert admission.load == pytest.approx(6.0)
    assert [event["reason"] for event in host.waits()] == ["host_load"]


def test_a_contended_load_names_its_limit_and_where_it_came_from(tmp_path: Path) -> None:
    """A wait that reaches its bound on load explains itself: the load, the limit, the source."""
    repo = init_git_repo(tmp_path / "repo")
    host = _Host([30.0])

    with (
        pytest.raises(
            ValueError, match=r"^proof_admission_contended:load=30\.0:limit=8\.0:source=test$"
        ),
        host.admit(repo, seconds=60.0),
    ):
        pytest.fail("no gate may run under contention")


@pytest.mark.parametrize(
    ("variable", "declared", "expected"),
    [
        ("7", "load_limit = 14\n", (7.0, "environment")),
        (None, "load_limit = 14\n", (14.0, "host.toml")),
        (None, None, (max(1.0, (os.cpu_count() or 1) / 2), "default")),
    ],
)
def test_the_load_limit_has_one_declared_source(
    monkeypatch: pytest.MonkeyPatch, variable: str | None, declared: str | None, expected: object
) -> None:
    """A run's explicit variable, then the host declaration, then half the CPUs."""
    if variable is None:
        monkeypatch.delenv(proof_slot.LOAD_LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(proof_slot.LOAD_LIMIT_VARIABLE, variable)
    root = host_admission.host_store_root()
    assert root is not None
    if declared is not None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "host.toml").write_text(declared, encoding="utf-8")

    assert proof_slot.effective_load_limit() == expected
