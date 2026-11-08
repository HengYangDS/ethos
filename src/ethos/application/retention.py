"""Preview which Git-common store records may retire, and apply an approved plan.

Only the runtime that `runtime/CURRENT` selects runs the verb, so its kinds and bounds are the
running package's. Each run holds `retention.lock` and first restores the tombstones that an
interrupted apply left. The preview reads the age floors from the accepted branch, holds the proof
slot while it scans, keeps every record that a live member, a kept store file, a kept or reached
record or the accepted tree names, and writes the plan of the others. The apply deletes, batch by
batch, only the planned items that a fresh scan still selects, and receipts each run.
"""

from __future__ import annotations

import shlex
import sys
import time
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.store.retention.apply import Apply
from ethos.adapters.store.retention.apply import hold_proof_slot
from ethos.adapters.store.retention.apply import try_hold
from ethos.adapters.store.retention.closure import Closure
from ethos.adapters.store.retention.kinds import classify_store
from ethos.adapters.store.retention.kinds import owned_directories
from ethos.adapters.store.retention.plan import Cutoffs
from ethos.adapters.store.retention.plan import RetirementReceipt
from ethos.adapters.store.retention.plan import applied_receipt
from ethos.adapters.store.retention.plan import read_plan
from ethos.adapters.store.retention.plan import write_plan
from ethos.adapters.store.retention.plan import write_receipt
from ethos.adapters.store.retention.tombstones import restore_all
from ethos.adapters.store.retention.writers import writer_roots
from ethos.adapters.store.state.schema import local_state_root
from ethos.application.invocation import application_result
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.parameters import parameter_resolution
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Sequence

    from filelock import FileLock

    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.adapters.store.retention.kinds import StoreItem
    from ethos.adapters.store.retention.plan import RetirementPlan

_COMMAND = "hook retire-records"
_NANOSECONDS = 1_000_000_000


def _fail(reason: str) -> NoReturn:
    raise ValueError(reason)


def _selected(root: Path) -> SelectedRuntime | None:
    try:
        return current_runtime(Path(git_common_dir(root)))
    except (OSError, ValueError):
        return None


def runtime_selected(root: Path) -> bool:
    """Return whether this interpreter and build are the runtime that `runtime/CURRENT` selects."""
    selected = _selected(root)
    return (
        selected is not None
        and Path(sys.executable).absolute() == selected.python.absolute()
        and selected.build == invoking_build_identity()
    )


@application_result(_COMMAND)
def preview_record_retirement(root: Path) -> EthosResult:
    """Plan the retirement of every owned, unnamed record older than its floor."""
    repo = root.resolve()
    store = local_state_root(repo)
    try:
        if not runtime_selected(repo):
            _fail("record_retirement_runtime_unselected")
        with _holding(try_hold(store / "retention.lock"), "record_retirement_in_progress"):
            conflicts = _restored(store)
            floors = _accepted_floors(repo)
            with _holding(hold_proof_slot(store), "record_retirement_proof_slot_held"):
                summary, report, plan = _preview(repo, store, *floors)
    except (OSError, ValueError) as error:
        return _blocked(error)
    return EthosResult(
        command=_COMMAND,
        verdict="pass",
        state="planned",
        summary=summary,
        user_decision_required=bool(plan),
        next_action=_apply_command(repo, plan) if plan else "",
        data={**report, "conflicts": conflicts},
    )


@application_result(_COMMAND)
def apply_record_retirement(root: Path, *, expect_plan: str, authorize: bool) -> EthosResult:
    """Delete the planned records that a fresh scan still selects, and receipt the run."""
    repo = root.resolve()
    store = local_state_root(repo)
    try:
        if not authorize:
            _fail("authorization_required")
        if not expect_plan:
            _fail("record_retirement_plan_required")
        if not runtime_selected(repo):
            _fail("record_retirement_runtime_unselected")
        with _holding(try_hold(store / "retention.lock"), "record_retirement_in_progress"):
            conflicts = _restored(store)
            plan = read_plan(store, expect_plan)
            applied = applied_receipt(store, expect_plan)
            if applied is None:
                return _applied(repo, store, expect_plan, plan, conflicts)
    except (OSError, ValueError) as error:
        return _blocked(error)
    return EthosResult(
        command=_COMMAND,
        verdict="pass",
        state="already_applied",
        summary={"deleted": 0},
        data={"receipt": applied, "conflicts": conflicts},
    )


@contextmanager
def _holding(lock: FileLock | None, refusal: str) -> Generator[None]:
    """Hold a lock taken without waiting for one block, or refuse when another process held it."""
    if lock is None:
        _fail(refusal)
    try:
        yield
    finally:
        lock.release()


def _restored(store: Path) -> list[str]:
    """Restore every tombstone an interrupted apply left; return those a differing record blocks."""
    return [path.relative_to(store).as_posix() for path in restore_all(owned_directories(store))]


def _blocked(error: Exception) -> EthosResult:
    return EthosResult(
        command=_COMMAND,
        verdict="block",
        state="blocked",
        required_gaps=(str(error) or error.__class__.__name__,),
    )


def _apply_command(repo: Path, plan: str) -> str:
    return shlex.join(
        (
            *("ethos", "hook", "retire-records", "--expect-plan", plan),
            *("--apply", "--authorize", "--root", repo.as_posix(), "--json"),
        )
    )


def _accepted_floors(repo: Path) -> tuple[str, str, dict[str, int]]:
    """Return the accepted branch, its commit and the retention values its binding declares."""
    paradigm = load_repository_paradigm()
    branch = load_branch_role_policy(repo).accepted_branch
    observed = run_git(
        repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False
    )
    if observed.returncode:
        _fail("record_retirement_floor_unreadable")
    commit = observed.stdout.strip()
    carrier = f"{commit}:{paradigm.binding.path('rules')}"
    text = ""
    if run_git(repo, "cat-file", "-e", carrier, check=False).returncode == 0:
        shown = run_git(repo, "show", carrier, check=False)
        try:
            if shown.returncode:
                _fail("record_retirement_floor_unreadable")
            tomllib.loads(shown.stdout)
        except tomllib.TOMLDecodeError as error:
            message = "record_retirement_floor_unreadable"
            raise ValueError(message) from error
        text = shown.stdout
    return branch, commit, parameter_resolution(text, paradigm).values["retention"]


def _closure(
    repo: Path, store: Path, branch: str, values: dict[str, int], items: Sequence[StoreItem]
) -> Closure:
    """Return the closure over every root, read once; no owned item counts as a root."""
    closure = Closure(
        repo,
        store,
        branch,
        depth=values["decode_depth"],
        budget=values["decode_bytes"],
        owned=frozenset(path for item in items for path in item.paths),
    )
    closure.refresh()
    return closure


def _cutoffs(values: dict[str, int], now: int) -> dict[str, int]:
    return {
        "artifact": now - values["grace_seconds"] * _NANOSECONDS,
        "record": now - values["record_seconds"] * _NANOSECONDS,
    }


def _old(item: StoreItem, cutoffs: dict[str, int]) -> bool:
    """Return whether an item's newest file is older than its floor: grace for an artifact."""
    floor = "artifact" if item.state == "artifact" else "record"
    return max(path.stat().st_mtime_ns for path in item.paths) < cutoffs[floor]


def _preview(
    repo: Path, store: Path, branch: str, accepted: str, values: dict[str, int]
) -> tuple[dict[str, object], dict[str, object], str]:
    """Return one preview's summary and data, and the plan to apply when it has candidates."""
    cutoffs = _cutoffs(values, time.time_ns())
    items, unowned = classify_store(store)
    closure = _closure(repo, store, branch, values, items)
    candidates = [item for item in items if _old(item, cutoffs)]
    for item in set(items) - set(candidates):
        closure.lend(item.paths)
    while reached := closure.reached(candidates):
        for item in reached:
            candidates.remove(item)
            closure.lend(item.paths)
    planned = [
        {
            "kind": item.kind,
            "state": item.state,
            "files": [
                {
                    "path": path.relative_to(store).as_posix(),
                    "size": info.st_size,
                    "mtime_ns": str(info.st_mtime_ns),
                }
                for path in item.paths
                for info in (path.stat(),)
            ],
        }
        for item in candidates
    ]
    plan = write_plan(
        store,
        {
            "schema_version": 2,
            "kind": "record-retirement-plan",
            "accepted_commit": accepted,
            "cutoffs": {key: str(value) for key, value in cutoffs.items()},
            "items": planned,
        },
    )
    counts: dict[str, int] = {}
    sizes: dict[str, int] = {}
    for item in candidates:
        counts[item.kind] = counts.get(item.kind, 0) + 1
        sizes[item.kind] = sizes.get(item.kind, 0) + sum(path.stat().st_size for path in item.paths)
    reported = [(path.as_posix(), path.stat().st_size) for path in unowned]
    summary = {
        "candidates": counts,
        "candidate_bytes": sizes,
        "unowned_bytes": sum(size for _path, size in reported),
    }
    data = {"plan": plan, "unowned": [{"path": path, "bytes": size} for path, size in reported]}
    return summary, data, str(plan["sha256"]) if candidates else ""


def _applied(
    repo: Path, store: Path, digest: str, plan: RetirementPlan, conflicts: list[str]
) -> EthosResult:
    """Apply one plan under the frozen or the fresh floor, whichever keeps more, and receipt it."""
    branch, _accepted, values = _accepted_floors(repo)
    fresh = _cutoffs(values, time.time_ns())
    frozen = {"artifact": int(plan.cutoffs.artifact), "record": int(plan.cutoffs.record)}
    cutoffs = {key: min(frozen[key], fresh[key]) for key in fresh}
    items, _unowned = classify_store(store)
    selected = _selected(repo)
    run = Apply(
        repo,
        store,
        _closure(repo, store, branch, values, items),
        selected=lambda: runtime_selected(repo),
        writer_roots=lambda: writer_roots(repo, selected=selected.root if selected else None),
    )
    run.run(run.select(plan.items, items, lambda item: _old(item, cutoffs)))
    receipt = RetirementReceipt(
        plan=digest,
        runtime_build=invoking_build_identity().projection(),
        cutoffs=Cutoffs(artifact=str(cutoffs["artifact"]), record=str(cutoffs["record"])),
        kinds=run.tally,
        live_members_clear=run.closure.members_clear(run.deleted),
    )
    written = write_receipt(store, receipt)
    gaps = tuple(
        sorted(
            f"record_retirement_batch_deferred:{kind}:{reason}"
            for kind, tally in run.tally.items()
            for reason in tally.deferred
        )
    )
    tallies = run.tally.values()
    return EthosResult(
        command=_COMMAND,
        verdict="block" if gaps else "pass",
        state="deferred" if gaps else "applied",
        summary={
            "deleted": sum(tally.deleted for tally in tallies),
            "deleted_bytes": sum(tally.deleted_bytes for tally in tallies),
            "deferred": sum(sum(tally.deferred.values()) for tally in tallies),
        },
        required_gaps=gaps,
        next_action=_apply_command(repo, digest) if gaps else "",
        data={
            "receipt": written,
            "kinds": {kind: tally.model_dump() for kind, tally in sorted(run.tally.items())},
            "live_members_clear": receipt.live_members_clear,
            "writers": sorted(run.writers),
            "conflicts": conflicts,
        },
    )
