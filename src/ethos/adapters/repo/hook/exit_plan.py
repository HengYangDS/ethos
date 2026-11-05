"""Plan a repository's exit from ETHOS's hook runtime, without any effect.

The plan decides the configuration after the exit per key. A key that still holds ETHOS's
activation value returns to its recorded value. A key that ETHOS no longer owns is kept, and an
owned key without a record entry is left; both are named. The plan also names the record entries
it cannot restore, the selectors with their hashes, the Leases, the unlanded topic branches, the
generations the exit removes and keeps, and what blocks the exit, all under one digest. It reads
the state database read-only and probes each lock without creating it. An `applying` receipt
makes the plan resume that exit, and its record stands in for a removed record file.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from filelock import FileLock

import ethos.adapters.repo.config_effects as config_effects
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.activation import linked_worktree_paths
from ethos.adapters.repo.hook.preimage import ACTIVATION_KEYS
from ethos.adapters.repo.hook.preimage import WORKTREE_ACTIVATION_KEYS
from ethos.adapters.repo.hook.preimage import ethos_owns_hooks_path
from ethos.adapters.repo.hook.preimage import ethos_owns_value
from ethos.adapters.repo.hook.preimage import file_bytes
from ethos.adapters.repo.hook.preimage import read_exit_receipt
from ethos.adapters.repo.hook.preimage import read_hooks_preimage
from ethos.adapters.repo.runtime.retirement import operational_reference_paths
from ethos.adapters.repo.runtime.retirement import process_reference_paths
from ethos.adapters.repo.runtime.retirement import retirement_plan
from ethos.adapters.repo.runtime.selection import runtime_selection_lock
from ethos.adapters.store.state.lease.projection import lease_observations
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import load_branch_role_policy

# ROLLBACK goes first, so an interrupted exit never leaves a rollback without its selection.
SELECTORS = ("ROLLBACK", "CURRENT")
Values = dict[str, list[str]]


def _selector(common: Path, name: str) -> dict[str, object]:
    content = file_bytes(common / "ethos" / "runtime" / name)
    if content is None:
        return {"present": False}
    lines = content.decode("utf-8", "replace").splitlines()
    installed = lines[1] if len(lines) > 1 and Path(lines[1]).is_absolute() else ""
    return {
        "present": True,
        "sha256": hashlib.sha256(content).hexdigest(),
        "names": "\n".join(lines),
        "installed": installed,
    }


def _held(lock: FileLock) -> bool:
    """Probe an existing lock without waiting; the probe never creates or unlinks its file.

    Taking a lock creates its file, so a missing file is a lock nobody holds. filelock's Timeout
    is an OSError, so a lock that cannot be taken, or whose state cannot be read, is held.
    """
    if not Path(lock.lock_file).is_file():
        return False
    try:
        with lock.acquire(blocking=False):
            return False
    except OSError:
        return True


def _blockers(
    repo: Path, common: Path, leases: list[dict[str, Any]], selectors: dict[str, Any]
) -> list[str]:
    gaps = [
        f"adoption_exit_lease_live:{lease['subject']}"
        for lease in leases
        if lease["lease_state"] in {"valid", "unknown"}
    ]
    locks = (
        (runtime_selection_lock(common), "adoption_exit_selection_held"),
        (
            FileLock(
                common / "ethos" / "proof-slot.lock",
                fallback_to_soft=False,
                preserve_lock_file=True,
            ),
            "adoption_exit_proof_running",
        ),
    )
    gaps.extend(gap for lock, gap in locks if _held(lock))
    installed = [
        Path(str(selector["installed"]))
        for selector in selectors.values()
        if selector.get("installed")
    ]
    owned = tuple(
        path.resolve()
        for path in (common / "ethos" / "runtime", common / "ethos" / "hooks", *installed)
    )
    try:
        references = process_reference_paths(repo, exclude_pid=os.getpid(), strict=True)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return [*gaps, "adoption_exit_runtime_use_unknown"]
    if any(reference.is_relative_to(path) for reference in references for path in owned):
        gaps.append("adoption_exit_runtime_in_use")
    return gaps


def _unlanded(repo: Path) -> list[dict[str, str]]:
    """Name each topic branch whose head the accepted branch does not contain."""
    policy = load_branch_role_policy(repo)
    accepted = run_git(
        repo,
        "rev-parse",
        "--verify",
        "--quiet",
        f"refs/heads/{policy.accepted_branch}",
        check=False,
    ).stdout.strip()
    listed = run_git(
        repo,
        "for-each-ref",
        "--format=%(objectname) %(refname:lstrip=2)",
        "refs/heads",
        check=False,
    ).stdout.splitlines()
    return [
        {"branch": name, "head": head}
        for head, _, name in (line.partition(" ") for line in listed)
        if policy.is_topic_branch(name) and not (accepted and is_ancestor(repo, head, accepted))
    ]


def _observed(repo: Path) -> tuple[Values, dict[str, Values]]:
    current = config_effects.config_values(repo, ACTIVATION_KEYS, scope="local")
    worktrees = {
        worktree.as_posix(): {
            key: list(values)
            for key, values in sorted(
                config_effects.config_values(
                    worktree, WORKTREE_ACTIVATION_KEYS, scope="worktree"
                ).items()
            )
        }
        for worktree in linked_worktree_paths(repo)
    }
    return {key: list(values) for key, values in sorted(current.items())}, worktrees


def _decide(common: Path, current: Values, recorded: Values, *, worktree: bool) -> dict[str, Any]:
    """Split one scope into its after state and the values written, kept and left."""
    after: Values = {}
    writes: Values = {}
    kept: Values = {}
    left: Values = {}
    for key, values in current.items():
        owned = ethos_owns_value(common, key, tuple(values), worktree=worktree)
        after[key] = recorded[key] if owned and key in recorded else values
        if after[key] != values:
            writes[key] = after[key]
        elif owned and key not in recorded and values:
            left[key] = values
        elif not owned and values != recorded.get(key, []):
            kept[key] = values
    return {"after": after, "writes": writes, "kept": kept, "left": left}


def _worktree_configuration_remains(
    current: Values, worktrees: dict[str, Values], after: dict[str, Values]
) -> bool:
    """Whether a worktree keeps its own configuration, which Git reads only with the extension."""
    if current.get("extensions.worktreeConfig") != ["true"]:
        return False
    owned = {key.lower() for key in WORKTREE_ACTIVATION_KEYS}
    for worktree in worktrees:
        listed = run_git(
            Path(worktree), "config", "--worktree", "--name-only", "--list", check=False
        )
        if any(name.lower() not in owned for name in listed.stdout.split()):
            return True
    return any(any(values.values()) for values in after.values())


def _decisions(
    common: Path, current: Values, worktrees: dict[str, Values], record: dict[str, Any] | None
) -> dict[str, Any]:
    recorded = record or {"common": {}, "worktrees": {}}
    shared = _decide(common, current, recorded["common"], worktree=False)
    scoped = {
        path: _decide(common, values, recorded["worktrees"].get(path, {}), worktree=True)
        for path, values in worktrees.items()
    }
    worktree_after = {path: decided["after"] for path, decided in scoped.items()}
    retained = shared["after"].get("extensions.worktreeConfig") != ["true"] and (
        _worktree_configuration_remains(current, worktrees, worktree_after)
    )
    if retained:
        shared["after"]["extensions.worktreeConfig"] = ["true"]
        shared["writes"].pop("extensions.worktreeConfig", None)
    return {
        "after": {"common": shared["after"], "worktrees": worktree_after},
        **{
            part: {
                "common": shared[part],
                "worktrees": {
                    path: decided[part] for path, decided in scoped.items() if decided[part]
                },
            }
            for part in ("writes", "kept", "left")
        },
        "worktree_configuration_kept": retained,
        "unrestorable": {
            path: entries
            for path, entries in recorded["worktrees"].items()
            if path not in worktrees and any(entries.values())
        },
    }


def _generation_plan(
    repo: Path, common: Path, current: Values, worktrees: dict[str, Values]
) -> dict[str, Any]:
    """The generations the exit removes: unreferenced once ETHOS's own hooks path is gone."""
    values = [
        value
        for scope in (current, *worktrees.values())
        for value in scope.get("core.hooksPath", [])
    ]
    ethos_hooks = frozenset(
        Path(value).resolve() for value in values if ethos_owns_hooks_path(common, (value,))
    )
    try:
        references = operational_reference_paths(repo) - ethos_hooks
        return retirement_plan(repo, references=references)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {"remove": [], "keep": [], "unknown": str(error) or type(error).__name__}


def _record(common: Path, receipt: dict[str, Any] | None) -> dict[str, Any] | None:
    """The recorded configuration; a resumed exit's receipt holds it once the file is removed."""
    record = read_hooks_preimage(common)
    if record is None and receipt is not None and isinstance(receipt.get("record"), dict):
        return receipt["record"]
    return record


def exit_preview(root: Path) -> dict[str, Any]:
    """Plan the exit of one repository family; nothing is written."""
    repo = root.resolve()
    common = Path(git_common_dir(repo)).resolve()
    current, worktrees = _observed(repo)
    selectors = {name: _selector(common, name) for name in SELECTORS}
    receipt = read_exit_receipt(common)
    resuming = receipt is not None and receipt.get("state") == "applying"
    ethos_hooks = any(
        ethos_owns_hooks_path(common, tuple(values.get("core.hooksPath", [])))
        for values in (current, *worktrees.values())
    )
    adopted = resuming or ethos_hooks or any(selector["present"] for selector in selectors.values())
    record = _record(common, receipt if resuming else None) if adopted else None
    leases = sorted(
        (observation.record() for observation in lease_observations(state_database(repo))),
        key=lambda lease: str(lease["subject"]),
    )
    plan: dict[str, Any] = {
        "common_current": current,
        "worktrees": worktrees,
        "record": record,
        "resume": resuming,
        **_decisions(common, current, worktrees, record if adopted else None),
        "selectors": selectors,
        "leases": leases,
        "unlanded_branches": _unlanded(repo) if adopted else [],
        "generations": _generation_plan(repo, common, current, worktrees)
        if adopted
        else {"remove": [], "keep": []},
        "consumer_records": "unchanged",
    }
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    unrecorded = adopted and any(
        "core.hooksPath" in left
        for left in (plan["left"]["common"], *plan["left"]["worktrees"].values())
    )
    return plan | {
        "plan_digest": hashlib.sha256(canonical).hexdigest(),
        "required_gaps": _gaps(repo, common, plan, receipt, adopted=adopted, unrecorded=unrecorded),
        "user_decision_required": unrecorded,
    }


def _gaps(
    repo: Path,
    common: Path,
    plan: dict[str, Any],
    receipt: dict[str, Any] | None,
    *,
    adopted: bool,
    unrecorded: bool,
) -> list[str]:
    if not adopted:
        return ["adoption_exit_not_adopted"]
    gaps = _blockers(repo, common, plan["leases"], plan["selectors"])
    if plan["resume"] and receipt is not None:
        planned = receipt.get("selectors", {})
        if any(
            selector["present"] and selector["sha256"] != planned.get(name, {}).get("sha256")
            for name, selector in plan["selectors"].items()
        ):
            gaps.append("adoption_exit_resume_conflict")
    return gaps + (["adoption_exit_preimage_unrecorded"] if unrecorded else [])
