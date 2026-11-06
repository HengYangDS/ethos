"""Refuse to activate a runtime that refuses the root's publication declaration.

A rollback runs a predecessor on a tree that its successor may have repaired. Before activation
pins or selects anything, the named runtime's own publish readiness reads the root's tree. A
refusal names restoring the predecessor's declaration in a lane, where the lane's HEAD contains
the accepted tip, so a stale lane cannot stand for the accepted declaration.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.process as process
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.paradigm.parameters import seconds
from ethos.result import expand_result

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.identity import BuildIdentity

RESTORE_ACTION = (
    "restore the predecessor's publication declaration in a lane whose HEAD contains the "
    "accepted tip, then run this hook install with --root <lane>"
)
# The predecessor's loader refuses a repaired declaration with this one gap.
_REPAIRED = "publication_topology_declaration_invalid"


class RollbackRefusalError(ValueError):
    """Carry one exact refusal gap and its next action to the command surface."""

    def __init__(self, gap: str, next_action: str) -> None:
        super().__init__(gap)
        self.gap = gap
        self.next_action = next_action


def rollback_preflight(root: Path, target: SelectedRuntime, *, invoking: BuildIdentity) -> None:
    """Probe a named runtime other than the invoking one; refuse a declaration it refuses."""
    if target.build == invoking:
        return
    accepted = ref_head(root, load_branch_role_policy(root).accepted_branch)
    if accepted and not is_ancestor(root, accepted, current_head(root)):
        gap = "runtime_rollback_root_behind_accepted"
        raise RollbackRefusalError(gap, RESTORE_ACTION)
    if _REPAIRED in _publication_gaps(root, target.python):
        gap = "runtime_rollback_declaration_repaired"
        raise RollbackRefusalError(gap, RESTORE_ACTION)


def _publication_gaps(root: Path, python: Path) -> tuple[str, ...]:
    """Run the target's read-only publish readiness on the root; an unknown answer refuses."""
    command = (str(python), "-B", "-I", "-m", "ethos.cli", "publish", "--root", str(root), "--json")
    # The probe itself is the action that shows why the target could not answer.
    failed = RollbackRefusalError("runtime_rollback_probe_failed", shlex.join(command))
    try:
        run = process.run_command(root, command, stdin="", timeout=seconds("tool"), check=False)
        payload = json.loads(run.stdout)
        # A bound may shorten the gaps; the digest-bound detail holds all of them.
        payload = expand_result(payload) if isinstance(payload, dict) else payload
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise failed from error
    gaps = payload.get("required_gaps") if isinstance(payload, dict) else None
    if not isinstance(gaps, list):
        raise failed
    return tuple(str(gap) for gap in gaps)
