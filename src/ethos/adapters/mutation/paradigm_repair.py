"""Preview or apply deterministic paradigm repairs inside one Work Lane."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.repo.git import tracked_paths
from ethos.adapters.repo.git_attributes import received_paths
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.repair import paradigm_repair_plan
from ethos.repository.paradigm.report import repository_paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.paradigm.repair import CarrierEdit

_APPLY = "ethos lane repair-paradigm --apply --json"


def repair_paradigm(*, root: Path, apply: bool = False) -> dict[str, object]:
    """Derive the repair plan, and apply it only after exact-path prewrite admission."""
    repo = root.resolve()
    tracked = tracked_paths(repo)
    received = received_paths(repo, tracked)
    report = repository_paradigm_report(repo, tracked_paths=tracked, received_paths=received)
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
        "next_action": _APPLY if plan.edits else _first(plan.actions, plan.report_only),
    }
    if not apply or not plan.edits:
        return planned
    admission = prewrite_guard(
        root=repo,
        paths=[repo / edit.path for edit in plan.edits],
        editor_root=repo,
        require_editor_root=True,
    )
    if report_verdict(admission) != "pass":
        return {
            **planned,
            "verdict": "block",
            "state": "blocked",
            "required_gaps": list(string_sequence(admission.get("required_gaps"))),
            "admission": admission,
            "next_action": str(admission.get("next_action") or ""),
        }
    for edit in plan.edits:
        path = repo / edit.path
        if edit.after is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(edit.after, encoding="utf-8")
    written = {edit.path for edit in plan.edits if edit.after is not None}
    removed = {edit.path for edit in plan.edits if edit.after is None}
    remaining = repository_paradigm_report(
        repo, tracked_paths=tuple(sorted({*tracked, *written} - removed)), received_paths=received
    )
    return {
        **planned,
        "state": "repaired",
        "applied": True,
        "remaining_gaps": remaining["required_gaps"],
        "next_action": _first(plan.actions, plan.report_only),
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
        "diff": "".join(diff),
    }


def _first(actions: tuple[str, ...], report_only: tuple[ParadigmGap, ...]) -> str:
    """Name the follow-up command first, then the first gap that needs judgment."""
    if actions:
        return actions[0]
    return report_only[0].repair if report_only else ""
