from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import cast

import yaml

from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_RELEASE_ROOT
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import close_verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from pathlib import Path

OPENSPEC_SPEC_OBLIGATION_PATTERN = re.compile(r"^\*\*(WHEN|THEN|AND)\*\*")
_OPEN_SPEC_CHANGE_PATH_MIN_PARTS = 4


def _load_official_config(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return cast("dict[str, object]", payload) if isinstance(payload, dict) else {}


def official_config_report(root: Path) -> dict[str, object]:
    """Validate `openspec/config.yaml` against the official OpenSpec shape."""
    path = root / "openspec" / "config.yaml"
    if not path.exists():
        return {
            "verdict": "block",
            "path": path.as_posix(),
            "required_gaps": ["openspec_config_missing"],
        }
    try:
        payload = _load_official_config(path)
    except yaml.YAMLError as exc:
        return {
            "verdict": "block",
            "path": path.as_posix(),
            "required_gaps": [f"openspec_config_invalid:{exc.__class__.__name__}"],
        }
    except (OSError, UnicodeError) as exc:
        return {
            "verdict": "unknown",
            "path": path.as_posix(),
            "required_gaps": [f"openspec_config_unavailable:{exc.__class__.__name__}"],
        }
    gaps: list[str] = []
    if not payload:
        gaps.append("openspec_config_not_mapping")
        payload = {}
    if not isinstance(payload.get("schema"), str) or not str(payload["schema"]).strip():
        gaps.append("openspec_config_schema_missing")
    gaps += ["openspec_config_default_store_forbidden"] * ("defaultStore" in payload)
    gaps.extend(
        f"openspec_config_legacy_key:{key}"
        for key in sorted(key for key in ("project", "version") if key in payload)
    )
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "path": path.as_posix(),
        "context": payload.get("context", ""),
        "rules": payload.get("rules", {}),
        "required_gaps": gaps,
    }


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


def protected_branch_active_change_report(
    root: Path,
    *,
    current_branch: str,
    branch_observations: dict[str, tuple[dict[str, object], dict[str, object] | None]],
) -> dict[str, object]:
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
    required_gaps: list[str] = []
    observations: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for branch, role in branches:
        if not branch or branch == current_branch:
            continue
        branch_report, changes = branch_observations[branch]
        observations.append(branch_report)
        if branch_report["verdict"] == "unknown":
            required_gaps.extend(cast("list[str]", branch_report["required_gaps"]))
            continue
        if branch_report["state"] == "absent":
            continue
        if changes is None:
            continue
        observations.append(changes)
        if changes["verdict"] != "pass":
            required_gaps.extend(cast("list[str]", changes["required_gaps"]))
            continue
        for change in cast("list[str]", changes["changes"]):
            key = (branch, role, change)
            if key in seen:
                continue
            seen.add(key)
            gap = f"openspec_protected_branch_active_change_unarchived:{branch}:{role}:{change}"
            advisory_gaps.append(gap)
            records.append({"branch": branch, "role": role, "change": change, "gap": gap})
    return {
        "verdict": reduce_verdicts(
            *(report_verdict(item) for item in observations),
            "block" if advisory_gaps else "pass",
            required_gaps=tuple(required_gaps),
        ),
        "records": records,
        "advisory_gaps": advisory_gaps,
        "required_gaps": required_gaps,
        "observations": observations,
        "summary": {"residue_count": len(records)},
    }


def protected_branch_active_change_required_gaps(
    report: dict[str, object], *, roles: set[str] | None = None
) -> list[str]:
    """Return protected-branch active carriers that block release readiness.

    The lifecycle read model exposes all non-current protected residue as advisory
    because observing another branch does not authorize mutation. Publication is
    stricter: a release-root active OpenSpec carrier means the governed release
    tree still contains an unclosed Change carrier, so publish readiness must fail
    until that carrier is archived on its owning branch.
    """
    blocked_roles = roles or {ROLE_RELEASE_ROOT}
    gaps = list(cast("list[str]", report["required_gaps"]))
    for record in cast("list[object]", report["records"]):
        if not isinstance(record, dict):
            continue
        if str(record.get("role") or "") in blocked_roles:
            gap = str(record.get("gap") or "")
            if gap:
                gaps.append(gap)
    return list(dict.fromkeys(gaps))


def active_change_names_from_paths(ref: str, paths: tuple[str, ...] | None) -> dict[str, object]:
    """Interpret active OpenSpec Change names from one observed Git tree."""
    if paths is None:
        return {
            "verdict": "unknown",
            "ref": ref,
            "changes": [],
            "required_gaps": [f"openspec_ref_tree_unavailable:{ref}"],
        }
    active: set[str] = set()
    for line in paths:
        parts = line.split("/")
        if len(parts) < _OPEN_SPEC_CHANGE_PATH_MIN_PARTS or parts[:2] != ["openspec", "changes"]:
            continue
        change = parts[2]
        if change == "archive":
            continue
        active.add(change)
    return {
        "verdict": "pass",
        "ref": ref,
        "changes": sorted(active),
        "required_gaps": [],
    }


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


def changed_openspec_spec_obligation_removal_gaps(diff_text: str | None) -> list[str]:
    """Detect accepted OpenSpec spec obligations removed in the current change.

    OpenSpec archives are projections until their deltas are fused into accepted
    specs. A tool-applied MODIFIED delta can accidentally replace a requirement
    and delete existing scenario obligations. The always-run shape audit treats
    removed WHEN/THEN/AND lines in accepted specs as a blocking small signal so
    humans/agents must either restore/fuse them or carry an explicit removal
    decision in a separate semantic change.
    """
    if diff_text is None:
        return ["openspec_spec_obligation_diff_unavailable"]
    gaps: list[str] = []
    current_file = ""
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        if not line.startswith("-") or line.startswith("---"):
            continue
        removed = line[1:].strip()
        if OPENSPEC_SPEC_OBLIGATION_PATTERN.match(removed):
            gaps.append(f"openspec_spec_obligation_removed:{current_file}:{removed}")
    return gaps


def _accepted_spec_physical_grammar_gaps(specs_root: Path) -> list[str]:
    """Require README plus capability directories containing only spec.md."""
    if not specs_root.is_dir():
        return ["openspec_specs_not_directory"]
    gaps: list[str] = []
    for entry in sorted(specs_root.iterdir(), key=lambda path: path.name):
        if entry.name == "README.md":
            if not entry.is_file() or entry.is_symlink():
                gaps.append("openspec_specs_root_entry_unexpected:README.md")
            continue
        if not entry.is_dir() or entry.is_symlink():
            gaps.append(f"openspec_specs_root_entry_unexpected:{entry.name}")
            continue
        spec = entry / "spec.md"
        gaps.extend(
            f"openspec_spec_capability_entry_unexpected:{entry.name}:{child.name}"
            for child in sorted(entry.iterdir(), key=lambda path: path.name)
            if child.name != "spec.md" or not child.is_file() or child.is_symlink()
        )
        if not spec.is_file() or spec.is_symlink():
            gaps.append(f"openspec_spec_capability_spec_missing:{entry.name}")
    return gaps


def openspec_shape_report(
    root: Path,
    *,
    current_branch: str,
    protected_branch_residue: dict[str, object],
    spec_diff: str | None,
) -> dict[str, object]:
    """Report OpenSpec repository shape without invoking the OpenSpec CLI."""
    openspec_root = root / "openspec"
    required_gaps = []
    if not openspec_root.exists():
        required_gaps.append("openspec_directory_missing")
    official_config = official_config_report(root)
    required_gaps.extend(cast("list[str]", official_config["required_gaps"]))
    specs_root = openspec_root / "specs"
    if not specs_root.exists():
        required_gaps.append("openspec_specs_missing")
    else:
        required_gaps.extend(_accepted_spec_physical_grammar_gaps(specs_root))
    required_gaps.extend(
        active_change_violations_for_role(
            openspec_root, load_branch_role_policy(root).role_for_branch(current_branch)
        )
    )
    required_gaps.extend(cast("list[str]", protected_branch_residue["required_gaps"]))
    required_gaps.extend(active_change_identifier_violations(openspec_root))
    required_gaps.extend(changed_openspec_spec_obligation_removal_gaps(spec_diff))
    return {
        "verdict": reduce_verdicts(
            report_verdict(official_config),
            ("unknown" if protected_branch_residue["verdict"] == "unknown" else "pass"),
            required_gaps=tuple(required_gaps),
        ),
        "mode": "shape",
        "official_config": official_config,
        "protected_branch_residue": protected_branch_residue,
        "advisory_gaps": protected_branch_residue["advisory_gaps"],
        "required_gaps": required_gaps,
    }
