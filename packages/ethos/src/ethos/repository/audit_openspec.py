from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

from ethos.repository.openspec_metadata import openspec_metadata_compatibility_report
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_CANDIDATE
from ethos_core.contracts.branch_roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path

OPENSPEC_SPEC_OBLIGATION_PATTERN = re.compile(r"^\*\*(WHEN|THEN|AND)\*\*")


OpenSpecReporter = object


def _active_change_names(openspec_root: Path) -> list[str]:
    """Return active OpenSpec change directory names, excluding archive/templates."""
    changes_root = openspec_root / "changes"
    if not changes_root.exists():
        return []
    return [
        change_dir.name
        for change_dir in sorted(changes_root.iterdir())
        if change_dir.is_dir() and change_dir.name != "archive"
    ]


def _active_change_violations_for_role(openspec_root: Path, role: str) -> list[str]:
    """Block active OpenSpec carriers on accepted and candidate roles.

    Active changes are legal authoring carriers in Work Lanes. Once a change is
    promoted to candidate or accepted-root truth, any remaining active carrier is
    stale state and must be archived so current truth lives in source, specs,
    claims, evidence, and chronicle rather than in `openspec/changes/<id>`.
    """
    if role not in {ROLE_ACCEPTED_ROOT, ROLE_CANDIDATE}:
        return []
    return [
        f"openspec_active_change_unarchived:{name}:{role}"
        for name in _active_change_names(openspec_root)
    ]


def _current_branch_role(root: Path) -> str:
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if branch.returncode != 0:
        return "other"
    return load_branch_role_policy(root).role_for_branch(branch.stdout.strip())


def _completed_unarchived_changes(openspec_root: Path) -> list[str]:
    """Active OpenSpec changes whose tasks are all complete but which are not archived.

    Uses ETHOS's OWN signal (every task box in tasks.md checked) rather than the
    external openspec CLI, so the leak is caught on the always-run audit path — not
    only at `land --closeout` (which raw `git merge` bypasses). A completed change
    left in changes/ is a carrier masquerading as active.
    """
    changes_root = openspec_root / "changes"
    if not changes_root.exists():
        return []
    unarchived: list[str] = []
    for change_dir in sorted(changes_root.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        tasks = change_dir / "tasks.md"
        if not tasks.exists():
            continue
        boxes = re.findall(r"- \[( |x|X)\]", tasks.read_text(encoding="utf-8"))
        if boxes and all(box.lower() == "x" for box in boxes):
            unarchived.append(f"openspec_completed_change_unarchived:{change_dir.name}")
    return unarchived


def _changed_openspec_spec_obligation_removal_gaps(root: Path) -> list[str]:
    """Detect accepted OpenSpec spec obligations removed in the current change.

    OpenSpec archives are projections until their deltas are fused into accepted
    specs. A tool-applied MODIFIED delta can accidentally replace a requirement
    and delete existing scenario obligations. The always-run shape audit treats
    removed WHEN/THEN/AND lines in accepted specs as a blocking small signal so
    humans/agents must either restore/fuse them or carry an explicit removal
    decision in a separate semantic change.
    """
    completed = subprocess.run(
        ["git", "diff", "--unified=0", "--", "openspec/specs/**/*.md"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        return ["openspec_spec_obligation_diff_unavailable"]
    gaps: list[str] = []
    current_file = ""
    for line in completed.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        if not line.startswith("-") or line.startswith("---"):
            continue
        removed = line[1:].strip()
        if OPENSPEC_SPEC_OBLIGATION_PATTERN.match(removed):
            gaps.append(f"openspec_spec_obligation_removed:{current_file}:{removed}")
    return gaps


def _openspec_shape_report(root: Path) -> dict[str, object]:
    openspec_root = root / "openspec"
    required_gaps = []
    if not openspec_root.exists():
        required_gaps.append("openspec_directory_missing")
    if not (openspec_root / "config.yaml").exists():
        required_gaps.append("openspec_config_missing")
    if not (openspec_root / "specs").exists():
        required_gaps.append("openspec_specs_missing")
    required_gaps.extend(
        _active_change_violations_for_role(openspec_root, _current_branch_role(root))
    )
    required_gaps.extend(_completed_unarchived_changes(openspec_root))
    metadata_compatibility = openspec_metadata_compatibility_report(root)
    required_gaps.extend(metadata_compatibility["required_gaps"])
    required_gaps.extend(_changed_openspec_spec_obligation_removal_gaps(root))
    return {
        "ok": not required_gaps,
        "mode": "shape",
        "metadata_compatibility": metadata_compatibility,
        "required_gaps": required_gaps,
    }


def _openspec_provider_missing_report(root: Path) -> dict[str, object]:
    shape = _openspec_shape_report(root)
    return {
        "ok": False,
        "mode": "deep",
        "shape": shape,
        "required_gaps": ["openspec_reporter_not_configured"],
    }
