"""Preview a repository's exit from ETHOS's hook runtime, without any effect.

An exit restores the Git configuration that adoption replaced and then removes the runtime
selectors, so a repository leaves ETHOS without a guessed hooks path. This slice reports the plan:
the configuration now and what the recorded preimage restores, each linked worktree's own
values, the CURRENT and ROLLBACK selectors with their hashes, the Lease snapshot, what blocks the
exit, and a digest over all of them that an apply will bind. It reads the state database
read-only and probes each lock without creating it. Consumer records stay with the host store,
and the apply follows in its own slice.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from filelock import FileLock
from filelock import Timeout

import ethos.adapters.repo.config_effects as config_effects
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import ACTIVATION_KEYS
from ethos.adapters.repo.hook.activation import WORKTREE_ACTIVATION_KEYS
from ethos.adapters.repo.hook.activation import linked_worktree_paths
from ethos.adapters.repo.hook.preimage import read_hooks_preimage
from ethos.adapters.store.state.lease.projection import lease_observations
from ethos.adapters.store.state.schema import state_database
from ethos.result import EthosResult

_SELECTORS = ("CURRENT", "ROLLBACK")
_LOCKS = (
    ("runtime-selection.lock", "adoption_exit_selection_held"),
    ("proof-slot.lock", "adoption_exit_proof_running"),
)


def _selector(common: Path, name: str) -> dict[str, object]:
    path = common / "ethos" / "runtime" / name
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return {"present": False}
    return {
        "present": True,
        "sha256": hashlib.sha256(content).hexdigest(),
        "names": content.decode("utf-8", "replace").strip(),
    }


def _held(path: Path) -> bool:
    """Probe an existing lock without creating it; a lock that cannot be taken is held."""
    if not path.is_file():
        return False
    lock = FileLock(path, timeout=0)
    try:
        lock.acquire(blocking=False)
    except Timeout:
        return True
    lock.release()
    return False


def _blockers(leases: list[dict[str, Any]], common: Path) -> list[str]:
    gaps = [
        f"adoption_exit_lease_live:{lease['subject']}"
        for lease in leases
        if lease["lease_state"] in {"valid", "unknown"}
    ]
    return gaps + [gap for name, gap in _LOCKS if _held(common / "ethos" / name)]


def exit_preview(root: Path) -> dict[str, Any]:
    """Plan the exit of one repository family; nothing is written."""
    repo = root.resolve()
    common = Path(git_common_dir(repo)).resolve()
    record = read_hooks_preimage(common)
    current = config_effects.config_values(repo, ACTIVATION_KEYS, scope="local")
    leases = sorted(
        (observation.record() for observation in lease_observations(state_database(repo))),
        key=lambda lease: str(lease["subject"]),
    )
    plan: dict[str, Any] = {
        "common_current": {key: list(values) for key, values in sorted(current.items())},
        "restore": record,
        "worktrees": {
            worktree.as_posix(): {
                key: list(values)
                for key, values in sorted(
                    config_effects.config_values(
                        worktree, WORKTREE_ACTIVATION_KEYS, scope="worktree"
                    ).items()
                )
            }
            for worktree in linked_worktree_paths(repo)
        },
        "selectors": {name: _selector(common, name) for name in _SELECTORS},
        "leases": leases,
        "consumer_records": "unchanged",
    }
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    gaps = _blockers(leases, common)
    if record is None:
        gaps.append("adoption_exit_preimage_unrecorded")
    return plan | {
        "plan_digest": hashlib.sha256(canonical).hexdigest(),
        "required_gaps": gaps,
        "user_decision_required": record is None,
    }


def adopt_exit(root: Path, *, apply: bool = False) -> EthosResult:
    """Report the exit plan; the apply ships in the next slice and is refused until then."""
    plan = exit_preview(root)
    gaps = ("adoption_exit_apply_unavailable",) if apply else tuple(plan["required_gaps"])
    next_action = (
        "an exit's apply is not available in this release; keep the preview as the plan"
        if apply
        else "resolve the named blockers; then the exit's apply, when it ships"
        if gaps
        else "review the plan; the exit's apply ships in a later release"
    )
    return EthosResult(
        command="adopt",
        verdict="block" if gaps else "pass",
        state="blocked" if gaps else "planned",
        required_gaps=gaps,
        next_action=next_action,
        user_decision_required=bool(plan["user_decision_required"]),
        data=plan,
    )
