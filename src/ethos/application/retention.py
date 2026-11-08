"""Preview which Git-common store records may retire, and write the plan an apply executes.

Only the runtime that `runtime/CURRENT` selects runs the preview, so its kinds and bounds are the
running package's. It reads the age floors from the accepted branch, holds the proof slot so no
proof writes beside it, keeps every record that a live member, a kept store file, a kept or
reached record or the accepted tree names, and writes the plan of the others. Nothing is deleted.
"""

from __future__ import annotations

import sys
import time
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.store.retention.kinds import StoreItem
from ethos.adapters.store.retention.kinds import classify_store
from ethos.adapters.store.retention.plan import write_plan
from ethos.adapters.store.retention.roots import carrier_tokens
from ethos.adapters.store.state.schema import local_state_root
from ethos.application.invocation import application_result
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.parameters import parameter_resolution
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Iterable

_COMMAND = "hook retire-records"
# Owners of these trees keep their own retention; the verb neither reads nor retires them.
_UNSCANNED = frozenset({"runtime", "packages", "hooks", "tool-cache", "cache"})
_OWN_RECORDS = ("requests/record-retirement", "receipts/record-retirement")
_NANOSECONDS = 1_000_000_000


def _fail(reason: str) -> None:
    raise ValueError(reason)


def runtime_selected(root: Path) -> bool:
    """Return whether this interpreter and build are the runtime that `runtime/CURRENT` selects."""
    try:
        selected = current_runtime(Path(git_common_dir(root)))
    except (OSError, ValueError):
        return False
    return (
        selected is not None
        and Path(sys.executable).absolute() == selected.python.absolute()
        and selected.build == invoking_build_identity()
    )


def live_member_bytes(root: Path) -> list[bytes]:
    """Return each live Attestation member's bytes; a damaged set refuses, none is empty."""
    try:
        _set_root, members = read_attestation_set(root)
    except ValueError as error:
        message = f"record_retirement_roots_unavailable:{error}"
        raise ValueError(message) from error
    return [member.model_dump_json().encode() for member in members]


@application_result(_COMMAND)
def preview_record_retirement(root: Path) -> EthosResult:
    """Plan the retirement of every owned, unnamed record older than its floor."""
    repo = root.resolve()
    store = local_state_root(repo)
    try:
        if not runtime_selected(repo):
            _fail("record_retirement_runtime_unselected")
        accepted, values = _accepted_floors(repo)
        with _held_proof_slot(store):
            summary, report = _preview(repo, store, accepted, values)
    except (OSError, ValueError) as error:
        return EthosResult(
            command=_COMMAND,
            verdict="block",
            state="blocked",
            required_gaps=(str(error) or error.__class__.__name__,),
        )
    return EthosResult(
        command=_COMMAND,
        verdict="pass",
        state="planned",
        summary=summary,
        data=report,
    )


def _accepted_floors(repo: Path) -> tuple[str, dict[str, int]]:
    """Return the accepted commit and the retention values its binding declares."""
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
    return commit, parameter_resolution(text, paradigm).values["retention"]


@contextmanager
def _held_proof_slot(store: Path) -> Generator[None]:
    """Hold the repository's proof slot for the preview, or refuse while a proof holds it."""
    store.mkdir(parents=True, exist_ok=True)
    slot = FileLock(str(store / "proof-slot.lock"), mode=0o600)
    try:
        slot.acquire(blocking=False)
    except Timeout as error:
        message = "record_retirement_proof_slot_held"
        raise ValueError(message) from error
    try:
        yield
    finally:
        slot.release()


def _preview(
    repo: Path, store: Path, accepted: str, values: dict[str, int]
) -> tuple[dict[str, object], dict[str, object]]:
    """Return the summary and the data of one preview, after writing its plan."""
    now = time.time_ns()
    cutoffs = {
        "artifact": now - values["grace_seconds"] * _NANOSECONDS,
        "record": now - values["record_seconds"] * _NANOSECONDS,
    }
    bounds = {"depth": values["decode_depth"], "budget": values["decode_bytes"]}
    items, unowned = classify_store(store)
    owned = {path for item in items for path in item.paths}
    tokens: set[str] = set()
    for data in live_member_bytes(repo):
        tokens |= carrier_tokens(data, name="attestation member", **bounds)
    for path in _kept_files(store, owned):
        tokens |= _file_tokens(path, store, bounds)
    for name, data in _accepted_blobs(repo, accepted):
        tokens |= carrier_tokens(data, name=f"{accepted}:{name}", **bounds)
    candidates: list[StoreItem] = []
    for item in items:
        if max(path.stat().st_mtime_ns for path in item.paths) < cutoffs[_floor(item)]:
            candidates.append(item)
        else:
            tokens |= _item_tokens(item, store, bounds)
    while reached := [item for item in candidates if item.tokens & tokens]:
        for item in reached:
            candidates.remove(item)
            tokens |= _item_tokens(item, store, bounds)
    planned = [
        {
            "kind": item.kind,
            "state": item.state,
            "files": [
                {"path": path.as_posix(), "size": stat.st_size, "mtime_ns": str(stat.st_mtime_ns)}
                for path in item.paths
                for stat in (path.stat(),)
            ],
        }
        for item in candidates
    ]
    plan = write_plan(
        store,
        {
            "schema_version": 1,
            "kind": "record-retirement-plan",
            "accepted_commit": accepted,
            # Nanosecond times exceed JSON's exact integers, so they are kept as decimal strings.
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
    return summary, data


def _floor(item: StoreItem) -> str:
    return "artifact" if item.state == "artifact" else "record"


def _kept_files(store: Path, owned: set[Path]) -> Iterable[Path]:
    """Yield every regular store file outside other owners' trees, owned items and own records."""
    own = tuple(store / name for name in _OWN_RECORDS)
    for path in sorted(store.rglob("*")):
        relative = path.relative_to(store)
        if (
            relative.parts[0] in _UNSCANNED
            or path in owned
            or any(path.is_relative_to(directory) for directory in own)
            or path.is_symlink()
            or not path.is_file()
        ):
            continue
        yield path


def _item_tokens(item: StoreItem, store: Path, bounds: dict[str, int]) -> set[str]:
    tokens: set[str] = set()
    for path in item.paths:
        tokens |= _file_tokens(path, store, bounds)
    return tokens


def _file_tokens(path: Path, store: Path, bounds: dict[str, int]) -> frozenset[str]:
    name = path.relative_to(store).as_posix()
    if path.stat().st_size > bounds["budget"]:
        _fail(f"record_retirement_carrier_undecodable:{name}")
    return carrier_tokens(path.read_bytes(), name=name, **bounds)


def _accepted_blobs(repo: Path, commit: str) -> list[tuple[str, bytes]]:
    """Return each blob of the accepted tree with its path."""
    listing = run_git(repo, "ls-tree", "-r", "-z", commit, text=False).stdout
    entries = [
        (meta.split()[2].decode(), name.decode("utf-8", errors="surrogateescape"))
        for record in listing.split(b"\0")
        if record
        for meta, _tab, name in (record.partition(b"\t"),)
        if meta.split()[1] == b"blob"
    ]
    if not entries:
        return []
    request = b"".join(f"{oid}\n".encode() for oid, _name in entries)
    stream = run_git(repo, "cat-file", "--batch", stdin=request, text=False).stdout
    blobs: list[tuple[str, bytes]] = []
    offset = 0
    for _oid, name in entries:
        header_end = stream.index(b"\n", offset)
        size = int(stream[offset:header_end].split()[2])
        blobs.append((name, stream[header_end + 1 : header_end + 1 + size]))
        offset = header_end + 1 + size + 1
    return blobs
