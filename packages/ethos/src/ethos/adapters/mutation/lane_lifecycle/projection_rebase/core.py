from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any
from typing import TypedDict

from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_lifecycle.projection_rebase.ledger import (
    resolve_source_budget_ledger_rebase_conflict,
)

PARITY_EVIDENCE_ROOT = Path("evidence/parity")
PARITY_SHADOW_SUFFIX = "-shadow.json"
SOURCE_BUDGET_SCOPE_SUBJECT = "quality:source-budget-proof-scope"
SOURCE_BUDGET_SCOPE_CLAIM_ID = "fine-grained-source-budget-scope-20260718"
SOURCE_BUDGET_SCOPE_PATHS = (
    "packages/ethos/src/ethos/domain/reporting/scoring.py",
    "tests/unit/domain/test_report.py",
    "tests/unit/governance/validation/test_gates.py",
)
SOURCE_BUDGET_REPORT_PATH = "packages/ethos/src/ethos/domain/report.py"
SOURCE_BUDGET_GATES_PATH = "system/gates.toml"
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
    *,
    candidate_head: str = "",
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
        if not projection_result["ok"]:
            projection_result = resolve_archived_source_budget_scope_conflict(
                root, candidate_head=candidate_head
            )
        if not projection_result["ok"]:
            projection_result = resolve_source_budget_ledger_rebase_conflict(
                root,
                resolution=projection_resolution,
                unmerged_paths=unmerged_paths,
            )
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


def resolve_archived_source_budget_scope_conflict(
    root: Path,
    *,
    candidate_head: str = "",
) -> ProjectionResolution:
    """Preserve a previously archived candidate scope correction, or fail closed."""
    paths = unmerged_paths(root)
    if not archived_source_budget_scope_bound(root, paths):
        return projection_resolution(ok=False, paths=paths)
    if not all(candidate_source_budget_scope_invariant(root, path, git=run_git) for path in paths):
        return projection_resolution(ok=False, paths=paths)
    if candidate_head and not candidate_source_budget_scope_context(
        root, candidate_head, git=run_git
    ):
        return projection_resolution(ok=False, paths=paths)
    checkout = run_git(root, "checkout", "--ours", "--", *paths, check=False)
    if checkout.returncode != 0:
        return projection_resolution(ok=False, paths=paths)
    added = run_git(root, "add", *paths, check=False)
    if added.returncode != 0:
        return projection_resolution(ok=False, paths=paths)
    return projection_resolution(
        ok=True,
        paths=paths,
        gaps=["semantic_scope_preserved:source_budget_proof_scope"],
        next_actions=[
            "rerun source-budget validation and HEAD-bound proof after the refreshed lane "
            "is complete"
        ],
    )


def archived_source_budget_scope_bound(root: Path, paths: list[str]) -> bool:
    """Require one archived claim carrier whose promotion targets match exactly."""
    if tuple(paths) != SOURCE_BUDGET_SCOPE_PATHS:
        return False
    claim_path = root / "evidence" / "claims" / f"{SOURCE_BUDGET_SCOPE_CLAIM_ID}.toml"
    if not claim_path.is_file():
        return False
    try:
        payload = tomllib.loads(claim_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    claim = payload.get("claim")
    boundary = payload.get("boundary")
    carriers = payload.get("carriers")
    promotion = payload.get("promotion")
    if (
        not isinstance(claim, dict)
        or not isinstance(boundary, dict)
        or not isinstance(carriers, dict)
        or not isinstance(promotion, dict)
        or claim.get("id") != SOURCE_BUDGET_SCOPE_CLAIM_ID
        or claim.get("change_id") != SOURCE_BUDGET_SCOPE_CLAIM_ID
        or claim.get("state") != "archived"
        or boundary.get("scope")
        != "Default fine-grained promotion proof versus global source-budget compression closeout."
        or claim.get("subject") != SOURCE_BUDGET_SCOPE_SUBJECT
    ):
        return False
    carrier = str(carriers.get("openspec") or "")
    expected_carrier = f"openspec/changes/archive/2026-07-18-{SOURCE_BUDGET_SCOPE_CLAIM_ID}"
    targets = promotion.get("targets")
    if (
        carrier != expected_carrier
        or not (root / carrier).is_dir()
        or not isinstance(targets, list)
    ):
        return False
    target_paths = {str(item.get("path") if isinstance(item, dict) else item) for item in targets}
    return set(SOURCE_BUDGET_SCOPE_PATHS) <= target_paths


def candidate_source_budget_scope_invariant(root: Path, path: str, *, git: Any) -> bool:
    """Check one candidate stage-2 file preserves the archived scope contract."""
    staged = git(root, "show", f":2:{path}", check=False)
    if staged.returncode != 0:
        return False
    text = staged.stdout
    if path.endswith("scoring.py"):
        return "def global_compression_report" in text and "source_budget_report(repo)" in text
    if path.endswith("test_report.py"):
        return "test_scorecard_surfaces_global_compression_separately" in text
    return "source-budget" in text and "gate_graph(full=True)" in text


def candidate_source_budget_scope_context(root: Path, candidate_head: str, *, git: Any) -> bool:
    """Require candidate scorecard and proof-floor context for the exact recovery."""
    report = git(root, "show", f"{candidate_head}:{SOURCE_BUDGET_REPORT_PATH}", check=False)
    gates = git(root, "show", f"{candidate_head}:{SOURCE_BUDGET_GATES_PATH}", check=False)
    if report.returncode != 0 or gates.returncode != 0:
        return False
    try:
        proof_sets = tomllib.loads(gates.stdout).get("proof_sets", {})
    except tomllib.TOMLDecodeError:
        return False
    default = proof_sets.get("product_default") if isinstance(proof_sets, dict) else None
    full = proof_sets.get("product_full") if isinstance(proof_sets, dict) else None
    return (
        "global_compression_report(repo)" in report.stdout
        and '"global_compression": global_compression' in report.stdout
        and isinstance(default, list)
        and isinstance(full, list)
        and "source-budget" not in default
        and "source-budget" in full
    )
