"""Admit one full proof per repository onto a host whose load leaves room for it.

A full proof that starts beside another full proof, or on a host already loaded by local CI
virtual machines or other test runs, fails its gates by timeout rather than by any defect.
Admission therefore waits before the first gate runs: first for the repository's proof slot,
then, while holding it, for both the 1- and 5-minute load averages to fall within the limit, so
a short lull between other jobs is not mistaken for room. Waiting is bounded; contention that
outlasts the bound ends the proof with a gap before any gate runs. A Work Lane that falls behind
its candidate meanwhile could no longer land, so its proof also ends before any gate runs.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from contextlib import contextmanager
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from pathlib import Path

LOAD_LIMIT_VARIABLE = "ETHOS_PROOF_HOST_LOAD_LIMIT"
CONTENDED = "proof_admission_contended"
STALE = "candidate_base_stale"
_LIMIT_INVALID = "proof_host_load_limit_invalid"
_ADMISSION_SECONDS = 3600.0
_POLL_SECONDS = 15.0


@dataclass(frozen=True)
class SlotAdmission:
    """How long a full proof waited and the host load it was admitted at."""

    waited_seconds: float
    load: float | None
    limit: float | None


def load_limit() -> float | None:
    """Return the admitted host load; `0` disables the load condition.

    Half the CPUs stay free for others by default: a full proof's own test workers fill the
    rest, and a busier host stretches its slowest tests past their timeout.
    """
    raw = os.environ.get(LOAD_LIMIT_VARIABLE, "")
    if not raw:
        return max(1.0, (os.cpu_count() or 1) / 2)
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value < 0:
        raise ValueError(_LIMIT_INVALID)
    return value or None


def host_load() -> float | None:
    """Observe the higher of the 1- and 5-minute load averages, or None where unreported."""
    try:
        return max(os.getloadavg()[:2])
    except (AttributeError, OSError):
        return None


def candidate_current(root: Path, *, head: str) -> Callable[[], bool]:
    """Judge whether a Work Lane head still contains its candidate; other checkouts do.

    Landing requires the candidate in the lane's history. A clone without the candidate
    branch has nothing to fall behind.
    """
    policy = load_branch_role_policy(root)
    if policy.role_for_branch(current_branch(root)) != ROLE_WORK_LANE:
        return lambda: True
    ref = f"refs/heads/{policy.candidate_branch}^{{commit}}"

    def current() -> bool:
        candidate = git_stdout(root, "rev-parse", "--verify", "--quiet", ref)
        return not candidate or is_ancestor(root, candidate, head)

    return current


def _report(event: dict[str, object]) -> None:
    sys.stderr.write(json.dumps(event, sort_keys=True) + "\n")
    sys.stderr.flush()


def _holder(path: Path) -> dict[str, object] | None:
    """Read who holds the slot; a missing or half-written record is simply unknown."""
    with suppress(OSError, ValueError):
        holder = json.loads(path.read_text(encoding="utf-8"))
        return holder if isinstance(holder, dict) else None
    return None


@contextmanager
def admitted_full_proof(
    root: Path,
    *,
    head: str,
    current: Callable[[], bool] | None = None,
    limit: Callable[[], float | None] = load_limit,
    load: Callable[[], float | None] = host_load,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    seconds: float = _ADMISSION_SECONDS,
    report: Callable[[dict[str, object]], None] = _report,
) -> Generator[SlotAdmission]:
    """Hold the repository's proof slot once host load allows; release it when the proof ends."""
    admitted_limit = limit()
    base_current = current or candidate_current(root, head=head)
    state = local_state_root(root)
    state.mkdir(parents=True, exist_ok=True)
    slot = FileLock(state / "proof-slot.lock", mode=0o600)
    holder = state / "proof-slot.json"
    started = clock()
    acquired = False
    reason = ""
    try:
        while True:
            if not base_current():
                raise ValueError(STALE)
            if not acquired:
                with suppress(Timeout):
                    slot.acquire(timeout=0)
                    acquired = True
                    record = {"pid": os.getpid(), "head": head, "since": datetime.now(UTC)}
                    holder.write_text(json.dumps(record, default=str), encoding="utf-8")
            observed = load() if acquired and admitted_limit is not None else None
            roomy = admitted_limit is None or observed is None or observed <= admitted_limit
            if acquired and roomy:
                break
            waiting = "host_load" if acquired else "slot_held"
            if waiting != reason:
                reason = waiting
                report(
                    {
                        "event": "proof_admission_waiting",
                        "head": head,
                        "reason": waiting,
                        "load": observed,
                        "limit": admitted_limit,
                        "holder": None if acquired else _holder(holder),
                    }
                )
            remaining = started + seconds - clock()
            if remaining <= 0:
                raise ValueError(CONTENDED)
            sleep(min(_POLL_SECONDS, remaining))
        admission = SlotAdmission(round(clock() - started, 1), observed, admitted_limit)
        report({"event": "proof_admission_granted", "head": head, **admission.__dict__})
        yield admission
    finally:
        if acquired:
            holder.unlink(missing_ok=True)
            slot.release()
