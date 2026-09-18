"""Select official intent using explicit choice and native contribution provenance."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_effect_attestation
from ethos.adapters.repo.merge.observation import pending_merge_heads
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import git_effect_from_plan
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from pathlib import Path


def selected_change(
    rows: list[dict[str, str]],
    requested: str | None,
    *,
    root: Path | None = None,
    tree_ref: str | None = None,
) -> str | None:
    """Select one explicit or unambiguous contribution without storing ownership."""
    return _selection(rows, requested, root=root, tree_ref=tree_ref)[0]


def artifact_path_change(root: Path, paths: tuple[str, ...]) -> str | None:
    """Select one existing Change named by every path, without authorizing writes."""
    parts = [path.split("/") for path in paths]
    if not parts or any(
        len(item) < 4 or item[:2] != ["openspec", "changes"] or ".." in item for item in parts
    ):
        return None
    names = {item[2] for item in parts}
    if len(names) != 1:
        return None
    name = names.pop()
    if name == "archive" or logical_change_identifier_issue(name):
        return None
    target = root / active_change_root(name)
    return name if target.is_dir() and not target.is_symlink() else None


def _selection(
    rows: list[dict[str, str]],
    requested: str | None,
    *,
    root: Path | None,
    tree_ref: str | None,
) -> tuple[str | None, str]:
    names = {item["name"] for item in rows}
    if requested is not None:
        return (
            (requested, "")
            if requested in names
            else (None, f"openspec_requested_change_missing:{requested}")
        )
    if names and root is not None:
        try:
            owned = _lane_contribution(root, names, tree_ref)
        except ValueError:
            return None, "openspec_change_provenance_unresolved"
        if owned is not None:
            names = owned
            if len(owned) == 1:
                return next(iter(owned)), ""
            return None, _unselected_gap(names)
    active = [item["name"] for item in rows if item["status"] in {"in-progress", "no-tasks"}]
    if len(active) == 1:
        return active[0], ""
    return (
        (next(iter(names)), "")
        if not active and len(names) == 1
        else (None, _unselected_gap(names))
    )


def _unselected_gap(names: set[str]) -> str:
    return (
        f"openspec_active_change_ambiguous:{','.join(sorted(names))}"
        if names
        else "openspec_active_change_missing"
    )


def selection_gaps(
    rows: list[dict[str, str]],
    requested: str | None,
    *,
    root: Path | None = None,
    tree_ref: str | None = None,
) -> list[str]:
    """Explain an unresolved official selection without guessing an owner."""
    gap = _selection(rows, requested, root=root, tree_ref=tree_ref)[1]
    return [gap] if gap else []


def incoming_change_gaps(root: Path, selected: str, incoming: str) -> list[str]:
    """Imported official Change content is not owned by the selected lane intent."""
    changes = _change_trees(root, incoming)
    if changes is None:
        return ["openspec_incoming_change_observation_unavailable"]
    return [
        f"openspec_incoming_change_modified:{name}"
        for name in sorted(changes.keys() - {selected})
        if run_git(
            root,
            "diff",
            "--cached",
            "--quiet",
            incoming,
            "--",
            f"openspec/changes/{name}",
            check=False,
            observation=True,
        ).returncode
    ]


def _change_trees(root: Path, revision: str) -> dict[str, str] | None:
    tree = revision
    for component in ("openspec", "changes"):
        entry = run_git(root, "ls-tree", "-z", tree, "--", component, check=False, observation=True)
        if entry.returncode:
            return None
        if not entry.stdout:
            return {}
        metadata, _name = entry.stdout.rstrip("\0").split("\t", 1)
        _mode, kind, tree = metadata.split()
        if kind != "tree":
            return None
    result = run_git(root, "ls-tree", "-z", tree, check=False, observation=True)
    if result.returncode:
        return None
    return {
        name: metadata.split()[2]
        for entry in result.stdout.split("\0")
        if entry
        for metadata, name in (entry.split("\t", 1),)
        if name != "archive" and metadata.split()[1] == "tree"
    }


def _lane_contribution(root: Path, names: set[str], tree_ref: str | None) -> set[str] | None:
    revision = tree_ref or "HEAD"
    pending = pending_merge_heads(root) if tree_ref is None else ()
    if pending:
        ours, theirs, merge = revision, pending[0], ""
        if len(pending) != 1:
            raise ValueError
    else:
        latest = run_git(
            root,
            "rev-list",
            "--first-parent",
            "--merges",
            "--max-count=1",
            revision,
            check=False,
            observation=True,
        )
        merge = latest.stdout.strip()
        if latest.returncode:
            raise ValueError
        if not merge:
            return None
        boundary = _lane_creation_boundary(root, revision)
        if boundary and is_ancestor(root, merge, boundary):
            return None
        parts = run_git(
            root, "rev-list", "--parents", "-n", "1", merge, observation=True
        ).stdout.split()
        ours, theirs = (parts[1], parts[2]) if len(parts) == 3 else ("", "")
    return _owned_changes(root, names, revision, ours, theirs, merge)


def _lane_creation_boundary(root: Path, revision: str) -> str:
    """Read the selected lane's native birth without turning it into authority."""
    branch = current_branch(root)
    policy = load_branch_role_policy(root)
    if policy.role_for_branch(branch) != ROLE_WORK_LANE:
        return ""
    ref = f"refs/heads/{branch}"
    _, records = read_attestation_set(root)
    boundaries: set[str] = set()
    for record in records:
        carried = record.payload.body.get("plan")
        declaration = carried.get("policy") if isinstance(carried, Mapping) else None
        if (
            record.predicate != "effect:git-ref-update"
            or not isinstance(declaration, Mapping)
            or declaration.get("transition") != "lane.start"
            or declaration.get("subject") != branch
        ):
            continue
        plan = plan_from_attestation(record)
        effect = git_effect_from_plan(plan)
        validate_effect_attestation(
            root, effect, record, issuer=record.verifier, plan=plan, current_postconditions=False
        )
        update = effect.updates.get(ref)
        candidate = str(plan.policy.get("candidate_branch") or "")
        if (
            update is None
            or len(effect.updates) != 1
            or update.expected != "0" * len(update.desired)
            or effect.assertions != {f"refs/heads/{candidate}": update.desired}
        ):
            raise ValueError
        if is_ancestor(root, update.desired, revision):
            boundaries.add(update.desired)
    if len(boundaries) > 1:
        raise ValueError
    return next(iter(boundaries), "")


def _owned_changes(
    root: Path, names: set[str], revision: str, ours: str, theirs: str, merge: str
) -> set[str]:
    if not ours or not theirs:
        raise ValueError
    bases = run_git(root, "merge-base", "--all", ours, theirs, check=False, observation=True)
    if bases.returncode or len(bases.stdout.split()) != 1:
        raise ValueError
    base, own, incoming = (_change_trees(root, ref) for ref in (bases.stdout.strip(), ours, theirs))
    if base is None or own is None or incoming is None:
        raise ValueError
    owned = {name for name in names if name in own and own[name] != base.get(name)}
    contributed = {name for name in names if name in incoming and incoming[name] != base.get(name)}
    if owned & contributed:
        raise ValueError
    if merge:
        merged, current = _change_trees(root, merge), _change_trees(root, revision)
        if merged is None or current is None:
            raise ValueError
        owned |= {name for name in names if name in current and current[name] != merged.get(name)}
        owned |= names - current.keys()
    else:
        owned |= names - own.keys() - incoming.keys()
    return owned
