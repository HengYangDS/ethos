"""Read and validate the retained authoring preimage of one native role transition."""

from __future__ import annotations

import hashlib
import os
import stat
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict

from pydantic import TypeAdapter

from ethos.adapters.admission.role_rename import ROLE_RENAME_OPERATION
from ethos.adapters.repo.content.observation import read_link_target
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.merge.observation import git_path
from ethos.adapters.repo.merge.observation import metadata_bytes
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path

_STATE_STALE = "legacy_role_rename_state_stale"
_WORKTREE_UNSAFE = "legacy_role_rename_worktree_unsafe"


class WorktreeSnapshot(TypedDict):
    source: str
    target: str
    head: str
    content: dict[str, object]


class LeaseSnapshot(TypedDict):
    target: str
    lease: dict[str, Any]


class RenameSnapshot(TypedDict):
    worktrees: dict[str, WorktreeSnapshot]
    leases: dict[str, LeaseSnapshot]


_SNAPSHOT = TypeAdapter(RenameSnapshot)
_TARGETS = TypeAdapter(dict[str, str])


def prepared_snapshot(
    prepared: Attestation,
) -> tuple[TransitionPlan, RenameSnapshot, dict[str, str]]:
    """Validate the entire carried wire and its exact ref/coordination correspondence."""
    try:
        body = prepared.payload.body
        plan = TransitionPlan.model_validate(mutable_json(body["plan"]))
        effect = git_effect_from_plan(plan)
        values = plan.facts["values"]
        snapshot = _SNAPSHOT.validate_python(
            mutable_json(values["role_rename_snapshot"]), strict=True
        )
        targets = _TARGETS.validate_python(mutable_json(values["role_renames"]), strict=True)
        paired = {
            source: (target, effect.updates[source].expected) for source, target in targets.items()
        }
        leases = {
            source.removeprefix("refs/heads/"): target.removeprefix("refs/heads/")
            for source, target in targets.items()
        }
        invalid = (
            not targets
            or set(targets) & set(targets.values())
            or len(set(targets.values())) != len(targets)
            or set(effect.updates) != set(targets) | set(targets.values())
            or effect.assertions
            or body["head"] != plan.facts["head"]
            or prepared.plan_digest != plan.digest
            or prepared.effect_digest != body["state_digest"]
            or body["state_digest"] != values["role_rename_state"]
            or body["state_digest"]
            != canonical_json_digest(
                {"head": body["head"], "renames": paired, "snapshot": snapshot}
            )
            or plan.policy.get("transition") != ROLE_RENAME_OPERATION
            or any(
                effect.updates[source].desired != "0" * len(head)
                or effect.updates[target].expected != "0" * len(head)
                or effect.updates[target].desired != head
                for source, (target, head) in paired.items()
            )
            or set(snapshot["leases"]) != set(leases)
            or any(
                record["target"] != leases[source] or record["lease"].get("subject") != source
                for source, record in snapshot["leases"].items()
            )
            or any(
                record["source"] not in paired
                or (record["target"], record["head"]) != paired[record["source"]]
                for record in snapshot["worktrees"].values()
            )
        )
    except (KeyError, TypeError, ValueError) as error:
        message = "legacy_role_rename_preparation_invalid"
        raise ValueError(message) from error
    if invalid:
        message = "legacy_role_rename_preparation_invalid"
        raise ValueError(message)
    return plan, snapshot, targets


def worktree_fields(root: Path) -> tuple[dict[str, str], ...]:
    return tuple(
        dict(field.partition(" ")[::2] for field in os.fsdecode(block).split("\0"))
        for block in run_git(
            root, "worktree", "list", "--porcelain", "-z", text=False
        ).stdout.split(b"\0\0")
        if block
    )


def preserved_content(root: Path) -> dict[str, object]:
    """Bind raw index, staged objects, working overlay and actual tracked/new file modes."""
    index = metadata_bytes(git_path(root, "index"))
    paths = run_git(
        root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        text=False,
        observation=True,
    ).stdout
    modes, digest = {}, hashlib.sha256()
    for raw in sorted(set(filter(None, paths.split(b"\0")))):
        relative = raw.decode(errors="surrogateescape")
        path = root / relative
        modes[relative] = path.lstat().st_mode if os.path.lexists(path) else None
        content = b""
        if modes[relative] is not None:
            content = (
                os.fsencode(
                    read_link_target(
                        root, relative, unsafe_gap=_WORKTREE_UNSAFE, unstable_gap=_STATE_STALE
                    )
                )
                if stat.S_ISLNK(modes[relative])
                else read_regular_bytes(
                    root,
                    relative,
                    unsafe_gap=_WORKTREE_UNSAFE,
                    unstable_gap=_STATE_STALE,
                    size_gap=_WORKTREE_UNSAFE,
                )
            )
        for part in (raw, content):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return {
        "index": hashlib.sha256(index).hexdigest() if index is not None else None,
        "stages": hashlib.sha256(
            run_git(root, "ls-files", "--stage", "-z", text=False, observation=True).stdout
        ).hexdigest(),
        "working": digest.hexdigest(),
        "modes": modes,
    }
