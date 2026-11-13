"""Preview or apply deterministic paradigm repairs inside one Work Lane."""

from __future__ import annotations

import difflib
import re
from typing import TYPE_CHECKING

from ethos.adapters.gates.native.inputs import paradigm_received_paths
from ethos.adapters.mutation.branch_roles import rename_retained_topic
from ethos.adapters.mutation.carrier_edit import apply_carrier_edits
from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.git import tracked_paths
from ethos.adapters.repo.git_attributes import checkout_line_endings
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_mapping
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.repair import paradigm_repair_plan
from ethos.repository.paradigm.repair import repair_next_action
from ethos.repository.paradigm.report import repository_paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.paradigm.repair import CarrierEdit

_APPLY = "ethos lane repair-paradigm --apply --json"
# A retired peer web repository is identity; no diff line repeats it, context included.
_WITHHELD = re.compile(r"^([ +-]\s*forge_repository\s*=).*$")


def repair_paradigm(*, root: Path, apply: bool = False) -> dict[str, object]:
    """Derive the repair plan, and apply it only after exact-path prewrite admission."""
    repo = root.resolve()
    if renamed := rename_retained_topic(repo, apply=apply):
        return renamed
    tracked = tracked_paths(repo)
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
    plan = paradigm_repair_plan(repo, gaps)
    planned: dict[str, object] = {
        "verdict": "pass",
        "state": "planned" if plan.edits else "conforming" if not gaps else "report_only",
        "applied": False,
        "edits": [_edit_view(edit) for edit in plan.edits],
        "repaired_gaps": [gap.required_gap for gap in plan.repaired],
        "report_only": [gap._asdict() for gap in plan.report_only],
        "actions": list(plan.actions),
        "required_gaps": [],
        "next_action": _APPLY if plan.edits else repair_next_action(plan),
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
