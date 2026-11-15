"""Preview or apply deterministic paradigm repairs inside one Work Lane."""

from __future__ import annotations

import difflib
import re
import shlex
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.gates.native.inputs import paradigm_received_paths
from ethos.adapters.mutation.branch_roles import rename_retained_topic
from ethos.adapters.mutation.carrier_edit import apply_carrier_edits
from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.git import tracked_paths
from ethos.adapters.repo.git_attributes import checkout_line_endings
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_mapping
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.repair import carrier_text
from ethos.repository.paradigm.repair import paradigm_repair_plan
from ethos.repository.paradigm.repair import pin_move
from ethos.repository.paradigm.repair import repair_next_action
from ethos.repository.paradigm.report import repository_paradigm_report
from ethos.repository.paradigm.toolchain import PIN_OBLIGATION
from ethos.repository.paradigm.toolchain import pin_ahead
from ethos.repository.paradigm.toolchain import pin_gap
from ethos.repository.paradigm.toolchain import pin_unread
from ethos.repository.policy.projections import PROJECTION_DECLARATIONS

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.paradigm.repair import CarrierEdit
    from ethos.repository.paradigm.repair import Handler
    from ethos.repository.paradigm.repair import RepairPlan

_APPLY = "ethos lane repair-paradigm --apply --json"
_PIN_APPLY = _APPLY.replace(" --apply", " --pin --apply")
# A retired peer web repository is identity; no diff line repeats it, context included.
_WITHHELD = re.compile(r"^([ +-]\s*forge_repository\s*=).*$")


def repair_paradigm(
    *, root: Path, apply: bool = False, release: str | None = None
) -> dict[str, object]:
    """Derive the repair plan, and apply it only after exact-path prewrite admission.

    `release` asks for an upgrade: the plan first declares that release as the ETHOS selection,
    and a tree that selects a newer release blocks the request. An empty one comes from a build
    that is no release, which only reports the selection.
    """
    repo = root.resolve()
    tracked = tracked_paths(repo)
    upgrade = _upgrade(repo, tracked, release)
    if ended := _before_plan(repo, upgrade, apply=apply):
        return ended
    received = paradigm_received_paths(repo, tracked)
    # One observation serves both reports, so no repair rewrites a verified retained original.
    origins = observed_document_origins(repo)
    report = repository_paradigm_report(
        repo,
        tracked_paths=tracked,
        received_paths=received,
        line_endings=checkout_line_endings(repo, tracked),
        retained_origins=origins,
    )
    gaps = [
        ParadigmGap(str(gap.get("obligation")), str(gap.get("carrier")), str(gap.get("repair")))
        for gap in map(string_mapping, object_sequence(report["gaps"]))
    ]
    # The pin leads the plan, so its relock is the first follow-up.
    gaps[:0] = upgrade.gaps
    plan = paradigm_repair_plan(repo, gaps, upgrade.handlers)
    planned: dict[str, object] = {
        "verdict": "pass",
        "state": "planned" if plan.edits else "conforming" if not gaps else "report_only",
        "applied": False,
        "edits": [_edit_view(edit) for edit in plan.edits],
        "repaired_gaps": [gap.required_gap for gap in plan.repaired],
        "report_only": [gap._asdict() for gap in plan.report_only],
        "actions": upgrade.actions(plan),
        "required_gaps": [],
        "next_action": upgrade.command if plan.edits else repair_next_action(plan),
    }
    effect = apply_carrier_edits(
        root=repo,
        edits=plan.edits,
        apply=apply,
        next_action=str(planned["next_action"]),
    )
    # The edit views are the preview; the native patch would repeat every removed value.
    result = {key: value for key, value in effect.items() if key != "patch"}
    result = {**planned, **result, "edits": planned["edits"]}
    if not effect["applied"]:
        if report_verdict(effect) == "pass":
            result["state"] = planned["state"]
            result["next_action"] = planned["next_action"]
        return result
    written = {edit.path for edit in plan.edits if edit.after is not None}
    removed = {edit.path for edit in plan.edits if edit.after is None}
    remaining_paths = tuple(sorted({*tracked, *written} - removed))
    remaining = repository_paradigm_report(
        repo,
        tracked_paths=remaining_paths,
        received_paths=received,
        line_endings=checkout_line_endings(repo, remaining_paths),
        retained_origins=origins,
    )
    return {
        **result,
        "state": "repaired",
        "applied": True,
        "remaining_gaps": remaining["required_gaps"],
        "next_action": repair_next_action(plan),
    }


class _Upgrade(NamedTuple):
    """What an upgrade adds: its refusal, or the plan's gap, handler, later steps and apply."""

    refusal: dict[str, object] | None = None
    gaps: tuple[ParadigmGap, ...] = ()
    handlers: tuple[tuple[str, Handler], ...] = ()
    later: tuple[str, ...] = ()
    command: str = _APPLY

    def actions(self, plan: RepairPlan) -> list[str]:
        """List the plan's follow-ups, then the steps that wait for the relock of a moved pin."""
        return [*plan.actions, *(self.later if set(self.gaps) & set(plan.repaired) else ())]


def _upgrade(repo: Path, tracked: tuple[str, ...], release: str | None) -> _Upgrade:
    """Refuse a move to an older release, or compose the pin move with the steps it leaves.

    Mise writes the lock, so the relock is the move's follow-up and names the repository.
    Generated files are admitted only as the patch that `ethos lane project` previews, so a
    repository that declares projections gets that step after the relock.
    """
    if release is None:
        return _Upgrade()
    # The plan edits the working file whether or not the index tracks it yet, so read that file
    # as the plan does. A file that cannot be read is no absent selection: its move stays reported.
    try:
        selection = carrier_text(repo, MISE_CONFIG)
    except (OSError, UnicodeError):
        return _Upgrade(gaps=(pin_unread(MISE_CONFIG),), command=_PIN_APPLY)
    if ahead := pin_ahead(selection, release):
        return _Upgrade(_refused(repo, ahead))
    gap = pin_gap(MISE_CONFIG, selection, release)
    relock = shlex.join(("mise", "--cd", str(repo), "lock"))
    project = shlex.join(("ethos", "lane", "project", "--root", str(repo), "--json"))
    move = (PIN_OBLIGATION, lambda _paradigm, _gap, text: pin_move(text or "", release, relock))
    return _Upgrade(
        None,
        (gap,) if gap else (),
        # A build that is no release names no target, so nothing handles its gap.
        (move,) if release else (),
        (project,) if PROJECTION_DECLARATIONS.keys() & set(tracked) else (),
        _PIN_APPLY,
    )


def _refused(repo: Path, ahead: str) -> dict[str, object]:
    """Block a pin move asked of a tree that selects a newer release, and plan nothing.

    A pass that planned nothing would read as a done bump. The next action runs the same request
    with the release that the tree selects, as the repository's own jobs run ETHOS.
    """
    request = ("ethos", "lane", "repair-paradigm", "--pin", "--root", str(repo), "--json")
    return {
        "verdict": "block",
        "state": "blocked",
        "applied": False,
        "required_gaps": [f"runtime_pin_ahead:{ahead}"],
        "next_action": shlex.join(("mise", "--cd", str(repo), "exec", "--locked", "--", *request)),
    }


def _before_plan(repo: Path, upgrade: _Upgrade, *, apply: bool) -> dict[str, object] | None:
    """Return the report that ends the command before a plan: a refused upgrade, else a rename.

    A rename plans nothing else, so an upgrade asked with it continues to the same request: its
    apply until the rename is done, and its preview after it.
    """
    if upgrade.refusal:
        return upgrade.refusal
    renamed = rename_retained_topic(repo, apply=apply)
    if renamed is None or upgrade.command == _APPLY:
        return renamed
    done = renamed["verdict"] == "pass" and renamed["applied"] is True
    request = upgrade.command.replace(" --apply", "") if done else upgrade.command
    return {**renamed, "next_action": request}


def _edit_view(edit: CarrierEdit) -> dict[str, object]:
    """Show one carrier edit as a unified diff against its current text."""
    diff = difflib.unified_diff(
        (edit.before or "").splitlines(keepends=True),
        (edit.after or "").splitlines(keepends=True),
        fromfile=f"a/{edit.path}" if edit.before is not None else "/dev/null",
        tofile=f"b/{edit.path}" if edit.after is not None else "/dev/null",
    )
    return {
        "path": edit.path,
        "created": edit.before is None,
        "removed": edit.after is None,
        "diff": "".join(_WITHHELD.sub(r"\1 <withheld>", line) for line in diff),
    }
