from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING
from typing import cast

import yaml

from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_RELEASE_ROOT
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.openspec.identifiers import archive_identity_gaps
from ethos.repository.openspec.identifiers import logical_change_identifier_issue
from ethos.repository.openspec.metadata import openspec_metadata_compatibility_report

if TYPE_CHECKING:
    from pathlib import Path

OPENSPEC_SPEC_OBLIGATION_PATTERN = re.compile(r"^\*\*(WHEN|THEN|AND)\*\*")
OPENSPEC_TASK_PATTERN = re.compile(r"- \[( |x|X)\]")


def tasks_complete(text: str) -> bool:
    """Return whether one OpenSpec task checklist is non-empty and complete."""
    boxes = OPENSPEC_TASK_PATTERN.findall(text)
    return bool(boxes) and all(box.lower() == "x" for box in boxes)


def change_tasks_complete(root: Path, change: str) -> bool:
    """Return whether one working-tree Change has completed its task checklist."""
    try:
        text = (root / "openspec" / "changes" / change / "tasks.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return tasks_complete(text)


def _load_official_config(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return cast("dict[str, object]", payload) if isinstance(payload, dict) else {}


def official_config_report(root: Path) -> dict[str, object]:
    """Validate `openspec/config.yaml` against the official OpenSpec shape."""
    path = root / "openspec" / "config.yaml"
    if not path.exists():
        return {
            "ok": False,
            "path": path.as_posix(),
            "required_gaps": ["openspec_config_missing"],
        }
    try:
        payload = _load_official_config(path)
    except yaml.YAMLError as exc:
        return {
            "ok": False,
            "path": path.as_posix(),
            "required_gaps": [f"openspec_config_invalid:{exc.__class__.__name__}"],
        }
    gaps: list[str] = []
    if not payload:
        gaps.append("openspec_config_not_mapping")
        payload = {}
    if payload.get("schema") != "spec-driven":
        gaps.append("openspec_config_schema_missing")
    context = payload.get("context")
    if not isinstance(context, str) or not context.strip():
        gaps.append("openspec_config_context_missing")
    rules = payload.get("rules")
    if not isinstance(rules, dict):
        gaps.append("openspec_config_rules_missing")
        rules = {}
    for artifact in ("proposal", "specs", "tasks", "design"):
        values = rules.get(artifact)
        if not isinstance(values, list) or not all(
            isinstance(item, str) and item.strip() for item in values
        ):
            gaps.append(f"openspec_config_rule_missing:{artifact}")
    gaps.extend(
        f"openspec_config_legacy_key:{key}"
        for key in sorted(key for key in ("project", "version") if key in payload)
    )
    return {"ok": not gaps, "path": path.as_posix(), "required_gaps": gaps}


def active_change_names(openspec_root: Path) -> list[str]:
    """Return active OpenSpec change directory names, excluding archive/templates."""
    changes_root = openspec_root / "changes"
    if not changes_root.exists():
        return []
    return [
        change_dir.name
        for change_dir in sorted(changes_root.iterdir())
        if change_dir.is_dir() and change_dir.name != "archive"
    ]


def active_change_identifier_violations(openspec_root: Path) -> list[str]:
    """Return invalid active Change directory identifiers before lifecycle work."""
    return [
        f"openspec_active_change_identifier_invalid:{name}"
        for name in active_change_names(openspec_root)
        if logical_change_identifier_issue(name)
    ]


def archive_identity_violations(openspec_root: Path) -> list[str]:
    """Return invalid or ambiguous archive identities without invoking OpenSpec."""
    archive_root = openspec_root / "changes" / "archive"
    names = (
        (path.name for path in archive_root.iterdir() if path.is_dir())
        if archive_root.is_dir()
        else ()
    )
    return archive_identity_gaps(names)


def protected_branch_active_change_report(root: Path, *, current_branch: str) -> dict[str, object]:
    """Return active OpenSpec carriers hiding in governed branch trees.

    The current checkout is not the whole repository truth. Release, accepted,
    and candidate branches can be unbound worktree-wise while still being
    publish/closeout-relevant Git facts. Scan their Git trees directly so active
    `openspec/changes/<id>/...` carriers cannot hide outside the current worktree.
    """
    policy = load_branch_role_policy(root)
    branches = (
        (policy.release_branch, policy.role_for_branch(policy.release_branch)),
        (policy.accepted_branch, policy.role_for_branch(policy.accepted_branch)),
        (policy.candidate_branch, policy.role_for_branch(policy.candidate_branch)),
    )
    records: list[dict[str, str]] = []
    advisory_gaps: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for branch, role in branches:
        if not branch or branch == current_branch or not _branch_exists(root, branch):
            continue
        for change in active_change_names_in_ref(root, branch):
            key = (branch, role, change)
            if key in seen:
                continue
            seen.add(key)
            gap = f"openspec_protected_branch_active_change_unarchived:{branch}:{role}:{change}"
            advisory_gaps.append(gap)
            records.append({"branch": branch, "role": role, "change": change, "gap": gap})
    return {
        "ok": not advisory_gaps,
        "records": records,
        "advisory_gaps": advisory_gaps,
        "summary": {"residue_count": len(records)},
    }


def protected_branch_active_change_required_gaps(
    root: Path, *, current_branch: str, roles: set[str] | None = None
) -> list[str]:
    """Return protected-branch active carriers that block release readiness.

    The lifecycle read model exposes all non-current protected residue as advisory
    because observing another branch does not authorize mutation. Publication is
    stricter: a release-root active OpenSpec carrier means the governed release
    tree still contains an unclosed Change carrier, so publish readiness must fail
    until that carrier is archived on its owning branch.
    """
    blocked_roles = roles or {ROLE_RELEASE_ROOT}
    report = protected_branch_active_change_report(root, current_branch=current_branch)
    gaps: list[str] = []
    for record in cast("list[object]", report["records"]):
        if not isinstance(record, dict):
            continue
        if str(record.get("role") or "") in blocked_roles:
            gap = str(record.get("gap") or "")
            if gap:
                gaps.append(gap)
    return gaps


def _branch_exists(root: Path, branch: str) -> bool:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def active_change_names_in_ref(root: Path, ref: str) -> list[str]:
    """Return active OpenSpec change names found in a protected branch Git tree."""
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", "openspec/changes"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    active: set[str] = set()
    for line in completed.stdout.splitlines():
        parts = line.split("/")
        if len(parts) < 4 or parts[:2] != ["openspec", "changes"]:
            continue
        change = parts[2]
        if change == "archive":
            continue
        active.add(change)
    return sorted(active)


def active_change_violations_for_role(openspec_root: Path, role: str) -> list[str]:
    """Block active OpenSpec carriers on candidate, accepted-root, and release-root roles.

    Active changes are legal authoring carriers in Work Lanes. Once a change is
    promoted to candidate, accepted-root, or release-root truth, any remaining active
    carrier is stale state and must be archived so current truth lives in source,
    specs, claims, evidence, and chronicle rather than in `openspec/changes/<id>`.
    """
    if role not in {ROLE_RELEASE_ROOT, ROLE_ACCEPTED_ROOT, ROLE_CANDIDATE}:
        return []
    return [
        f"openspec_active_change_unarchived:{name}:{role}"
        for name in active_change_names(openspec_root)
    ]


def _current_branch(root: Path) -> str:
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if branch.returncode != 0:
        return ""
    return branch.stdout.strip()


def _current_branch_role(root: Path) -> str:
    return load_branch_role_policy(root).role_for_branch(_current_branch(root))


def completed_unarchived_changes(openspec_root: Path) -> list[str]:
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
        if tasks_complete(tasks.read_text(encoding="utf-8")):
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


def openspec_shape_report(root: Path) -> dict[str, object]:
    """Report OpenSpec repository shape without invoking the OpenSpec CLI."""
    openspec_root = root / "openspec"
    required_gaps = []
    if not openspec_root.exists():
        required_gaps.append("openspec_directory_missing")
    official_config = official_config_report(root)
    required_gaps.extend(cast("list[str]", official_config["required_gaps"]))
    if not (openspec_root / "specs").exists():
        required_gaps.append("openspec_specs_missing")
    current_branch = _current_branch(root)
    required_gaps.extend(
        active_change_violations_for_role(
            openspec_root, load_branch_role_policy(root).role_for_branch(current_branch)
        )
    )
    protected_branch_residue = protected_branch_active_change_report(
        root, current_branch=current_branch
    )
    required_gaps.extend(completed_unarchived_changes(openspec_root))
    required_gaps.extend(active_change_identifier_violations(openspec_root))
    required_gaps.extend(archive_identity_violations(openspec_root))
    metadata_compatibility = openspec_metadata_compatibility_report(root)
    required_gaps.extend(metadata_compatibility["required_gaps"])
    required_gaps.extend(_changed_openspec_spec_obligation_removal_gaps(root))
    return {
        "ok": not required_gaps,
        "mode": "shape",
        "official_config": official_config,
        "metadata_compatibility": metadata_compatibility,
        "protected_branch_residue": protected_branch_residue,
        "advisory_gaps": protected_branch_residue["advisory_gaps"],
        "required_gaps": required_gaps,
    }


def openspec_provider_missing_report(root: Path) -> dict[str, object]:
    """Return the deep-mode gap used when no OpenSpec provider reporter is configured."""
    shape = openspec_shape_report(root)
    return {
        "ok": False,
        "mode": "deep",
        "shape": shape,
        "required_gaps": ["openspec_reporter_not_configured"],
    }
