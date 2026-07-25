from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import TypedDict

from ethos.adapters.repo.git import run_git

PARITY_EVIDENCE_ROOT = Path("evidence/parity")
PARITY_SHADOW_SUFFIX = "-shadow.json"
MAX_PROJECTION_REBASE_STEPS = 64


class ProjectionResolution(TypedDict):
    ok: bool
    paths: list[str]
    gaps: list[str]
    next_actions: list[str]


class ProjectionRebaseResolution(TypedDict):
    ok: bool
    paths: list[str]
    gaps: list[str]
    next_actions: list[str]
    stderr: str


def projection_resolution(
    *,
    ok: bool,
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> ProjectionResolution:
    return {
        "ok": ok,
        "paths": paths or [],
        "gaps": gaps or [],
        "next_actions": next_actions or [],
    }


def projection_rebase_resolution(
    *,
    ok: bool,
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    next_actions: list[str] | None = None,
    stderr: str = "",
) -> ProjectionRebaseResolution:
    return {
        "ok": ok,
        "paths": paths or [],
        "gaps": gaps or [],
        "next_actions": next_actions or [],
        "stderr": stderr,
    }


def append_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def resolve_projection_only_rebase_conflict(
    root: Path,
) -> ProjectionResolution:
    paths = unmerged_paths(root)
    if paths and all(staged_parity_projection(root, path, git=run_git) for path in paths):
        return parity_projection_resolution(paths)
    adopters = [parity_adopter(path) for path in paths]
    result = projection_resolution(ok=False)
    if paths and all(adopters):
        checkout = run_git(root, "checkout", "--ours", "--", *paths, check=False)
        if checkout.returncode != 0:
            result = projection_resolution(ok=False, paths=paths)
        else:
            added = run_git(root, "add", *paths, check=False)
            if added.returncode != 0:
                result = projection_resolution(ok=False, paths=paths)
            else:
                result = parity_projection_resolution(paths)
    return result


def unmerged_paths(
    root: Path,
) -> list[str]:
    completed = run_git(root, "diff", "--name-only", "--diff-filter=U", check=False)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def parity_adopter(path: str) -> str:
    candidate = Path(path)
    if candidate.parent != PARITY_EVIDENCE_ROOT or not candidate.name.endswith(
        PARITY_SHADOW_SUFFIX
    ):
        return ""
    adopter = candidate.name[: -len(PARITY_SHADOW_SUFFIX)]
    return adopter or ""


def empty_projection_patch(stderr: str) -> bool:
    lowered = stderr.lower()
    return (
        "no changes" in lowered
        or "nothing to commit" in lowered
        or "patch is empty" in lowered
        or "previous cherry-pick is now empty" in lowered
    )


def resolve_projection_rebase(
    root: Path,
    initial: object,
) -> ProjectionRebaseResolution:
    paths: list[str] = []
    gaps: list[str] = []
    next_actions: list[str] = []
    completed = initial
    for _ in range(MAX_PROJECTION_REBASE_STEPS):
        if getattr(completed, "returncode", 1) == 0:
            return projection_rebase_resolution(
                ok=bool(paths),
                paths=paths,
                gaps=gaps,
                next_actions=next_actions,
                stderr="",
            )
        projection_result = resolve_projection_only_rebase_conflict(root)
        if projection_result["ok"]:
            append_unique(paths, projection_result["paths"])
            append_unique(gaps, projection_result["gaps"])
            append_unique(next_actions, projection_result["next_actions"])
            completed = run_git(root, "-c", "core.editor=true", "rebase", "--continue", check=False)
            continue
        if paths and empty_projection_patch(str(getattr(completed, "stderr", ""))):
            completed = run_git(root, "rebase", "--skip", check=False)
            continue
        return projection_rebase_resolution(
            ok=False,
            paths=paths,
            gaps=gaps,
            next_actions=next_actions,
            stderr=str(getattr(completed, "stderr", "")),
        )
    return projection_rebase_resolution(
        ok=False,
        paths=paths,
        gaps=gaps,
        next_actions=next_actions,
        stderr="projection rebase recovery exceeded bounded step limit",
    )


def parity_projection_resolution(paths: list[str]) -> ProjectionResolution:
    """Render the bounded regeneration obligation for parity projections."""
    adopters = [parity_adopter(path) for path in paths]
    return projection_resolution(
        ok=True,
        paths=paths,
        gaps=[f"projection_regeneration_required:parity:{adopter}" for adopter in adopters],
        next_actions=[
            f"ethos parity shadow --adopter {adopter} --target . --execute --write-evidence --json"
            for adopter in adopters
        ],
    )


def staged_parity_projection(root: Path, path: str, *, git: Any) -> bool:
    """Return whether rerere staged a structurally valid parity JSON projection."""
    staged = git(root, "show", f":0:{path}", check=False)
    if staged.returncode != 0:
        return False
    try:
        payload = json.loads(staged.stdout)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(payload, dict)
        and payload.get("schema_version") == 1
        and payload.get("adopter") == parity_adopter(path)
    )
