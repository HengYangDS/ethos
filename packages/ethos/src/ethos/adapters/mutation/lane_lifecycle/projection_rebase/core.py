from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any
from typing import Protocol
from typing import TypedDict
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_lifecycle.projection_rebase.ledger import (
    resolve_source_budget_ledger_rebase_conflict,
)

PARITY_EVIDENCE_ROOT = Path("evidence/parity")
PARITY_SHADOW_SUFFIX = "-shadow.json"
SOURCE_BUDGET_SCOPE_CLAIM_ID = "fine-grained-source-budget-scope-20260718"
SOURCE_BUDGET_SCOPE_SUBJECT = "quality:source-budget-proof-scope"
SOURCE_BUDGET_SCOPE_PATHS = (
    "packages/ethos/src/ethos/domain/reporting/scoring.py",
    "tests/unit/domain/test_report.py",
    "tests/unit/governance/validation/test_gates.py",
)
SOURCE_BUDGET_REPORT_PATH = "packages/ethos/src/ethos/domain/report.py"
SOURCE_BUDGET_GATES_PATH = "system/gates.toml"
MAX_PROJECTION_REBASE_STEPS = 64


class ProjectionRebaseRuntime(Protocol):
    """Runtime dependency boundary for bounded projection rebase recovery."""

    def run_git(self, root: Path, *args: str, check: bool = True) -> Any:
        """Run a Git command in the target repository."""


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


def _resolution(
    ok: bool,  # noqa: FBT001
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    actions: list[str] | None = None,
    stderr: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": ok,
        "paths": paths or [],
        "gaps": gaps or [],
        "next_actions": actions or [],
    }
    if stderr is not None:
        result["stderr"] = stderr
    return result


def projection_resolution(
    *,
    ok: bool,
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> ProjectionResolution:
    """Return the stable projection-conflict payload."""
    return cast("ProjectionResolution", _resolution(ok, paths, gaps, next_actions))


def projection_rebase_resolution(
    *,
    ok: bool,
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    next_actions: list[str] | None = None,
    stderr: str = "",
) -> ProjectionRebaseResolution:
    """Return the stable bounded-rebase payload."""
    return cast(
        "ProjectionRebaseResolution",
        _resolution(ok, paths, gaps, next_actions, stderr),
    )


def append_unique(target: list[str], values: list[str]) -> None:
    """Append values once while preserving observation order."""
    target.extend(value for value in values if value not in target)


def unmerged_paths(
    root: Path,
    *,
    runtime: ProjectionRebaseRuntime | None = None,
) -> list[str]:
    git = runtime.run_git if runtime else run_git
    result = git(root, "diff", "--name-only", "--diff-filter=U", check=False)
    return [] if result.returncode else [line for line in result.stdout.splitlines() if line]


def parity_adopter(path: str) -> str:
    candidate = Path(path)
    return (
        candidate.name[: -len(PARITY_SHADOW_SUFFIX)]
        if candidate.parent == PARITY_EVIDENCE_ROOT
        and candidate.name.endswith(PARITY_SHADOW_SUFFIX)
        else ""
    )


def parity_projection_resolution(paths: list[str]) -> ProjectionResolution:
    adopters = list(map(parity_adopter, paths))
    return projection_resolution(
        ok=True,
        paths=paths,
        gaps=[f"projection_regeneration_required:parity:{name}" for name in adopters],
        next_actions=[
            f"ethos parity shadow --adopter {name} --target . --execute --write-evidence --json"
            for name in adopters
        ],
    )


def staged_parity_projection(root: Path, path: str, *, git: Any) -> bool:
    staged = git(root, "show", f":0:{path}", check=False)
    if staged.returncode:
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


def resolve_projection_only_rebase_conflict(
    root: Path,
    *,
    runtime: ProjectionRebaseRuntime | None = None,
) -> ProjectionResolution:
    git = runtime.run_git if runtime else run_git
    paths = unmerged_paths(root, runtime=runtime)
    if paths and all(staged_parity_projection(root, path, git=git) for path in paths):
        return parity_projection_resolution(paths)
    if not paths or not all(map(parity_adopter, paths)):
        return projection_resolution(ok=False)
    for args in (("checkout", "--ours", "--", *paths), ("add", *paths)):
        if git(root, *args, check=False).returncode:
            return projection_resolution(ok=False, paths=paths)
    return parity_projection_resolution(paths)


def empty_projection_patch(stderr: str) -> bool:
    """Return whether Git reports a projection-only patch already empty."""
    lowered = stderr.lower()
    return any(
        phrase in lowered
        for phrase in (
            "no changes",
            "nothing to commit",
            "patch is empty",
            "previous cherry-pick is now empty",
        )
    )


def _scope_claim_bound(root: Path) -> bool:
    try:
        payload = tomllib.loads(
            (root / "evidence" / "claims" / f"{SOURCE_BUDGET_SCOPE_CLAIM_ID}.toml").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, tomllib.TOMLDecodeError):
        return False
    claim, boundary = payload.get("claim"), payload.get("boundary")
    carriers, promotion = payload.get("carriers"), payload.get("promotion")
    if not (
        isinstance(claim, dict)
        and isinstance(boundary, dict)
        and isinstance(carriers, dict)
        and isinstance(promotion, dict)
    ):
        return False
    carrier = str(carriers.get("openspec") or "")
    targets = promotion.get("targets")
    return (
        claim.get("id") == claim.get("change_id") == SOURCE_BUDGET_SCOPE_CLAIM_ID
        and claim.get("state") == "archived"
        and claim.get("subject") == SOURCE_BUDGET_SCOPE_SUBJECT
        and boundary.get("scope")
        == "Default fine-grained promotion proof versus global source-budget compression closeout."
        and carrier == f"openspec/changes/archive/2026-07-18-{SOURCE_BUDGET_SCOPE_CLAIM_ID}"
        and (root / carrier).is_dir()
        and isinstance(targets, list)
        and set(SOURCE_BUDGET_SCOPE_PATHS)
        <= {str(item.get("path") if isinstance(item, dict) else item) for item in targets}
    )


def candidate_source_budget_scope_invariant(root: Path, path: str, *, git: Any) -> bool:
    staged = git(root, "show", f":2:{path}", check=False)
    if staged.returncode:
        return False
    required = (
        ("def global_compression_report", "source_budget_report(repo)")
        if path.endswith("scoring.py")
        else ("test_scorecard_surfaces_global_compression_separately",)
        if path.endswith("test_report.py")
        else ("source-budget", "gate_graph(full=True)")
    )
    return all(token in staged.stdout for token in required)


def candidate_source_budget_scope_context(root: Path, candidate_head: str, *, git: Any) -> bool:
    report = git(root, "show", f"{candidate_head}:{SOURCE_BUDGET_REPORT_PATH}", check=False)
    gates = git(root, "show", f"{candidate_head}:{SOURCE_BUDGET_GATES_PATH}", check=False)
    if report.returncode or gates.returncode:
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


def archived_source_budget_scope_bound(root: Path, paths: list[str]) -> bool:
    """Require the exact archived claim and promotion target set."""
    return tuple(paths) == SOURCE_BUDGET_SCOPE_PATHS and _scope_claim_bound(root)


def resolve_archived_source_budget_scope_conflict(
    root: Path,
    *,
    runtime: ProjectionRebaseRuntime | None = None,
    candidate_head: str = "",
) -> ProjectionResolution:
    git = runtime.run_git if runtime else run_git
    paths = unmerged_paths(root, runtime=runtime)
    valid = archived_source_budget_scope_bound(root, paths)
    valid = valid and all(
        candidate_source_budget_scope_invariant(root, path, git=git) for path in paths
    )
    valid = valid and (
        not candidate_head or candidate_source_budget_scope_context(root, candidate_head, git=git)
    )
    if not valid:
        return projection_resolution(ok=False, paths=paths)
    for args in (("checkout", "--ours", "--", *paths), ("add", *paths)):
        if git(root, *args, check=False).returncode:
            return projection_resolution(ok=False, paths=paths)
    return projection_resolution(
        ok=True,
        paths=paths,
        gaps=["semantic_scope_preserved:source_budget_proof_scope"],
        next_actions=[
            "rerun source-budget validation and HEAD-bound proof after the refreshed lane is complete"  # noqa: E501
        ],
    )


def resolve_projection_rebase(
    root: Path,
    initial: object,
    *,
    runtime: ProjectionRebaseRuntime | None = None,
    candidate_head: str = "",
) -> ProjectionRebaseResolution:
    """Recover only known projection conflicts while replaying a Work Lane."""
    git = runtime.run_git if runtime else run_git
    paths: list[str] = []
    gaps: list[str] = []
    actions: list[str] = []
    completed = initial
    for _ in range(MAX_PROJECTION_REBASE_STEPS):
        if getattr(completed, "returncode", 1) == 0:
            return projection_rebase_resolution(
                ok=bool(paths), paths=paths, gaps=gaps, next_actions=actions
            )
        result = resolve_projection_only_rebase_conflict(root, runtime=runtime)
        if not result["ok"]:
            result = resolve_archived_source_budget_scope_conflict(
                root, runtime=runtime, candidate_head=candidate_head
            )
        if not result["ok"]:
            result = resolve_source_budget_ledger_rebase_conflict(
                root,
                runtime=runtime,
                resolution=projection_resolution,
                unmerged_paths=unmerged_paths,
            )
        if result["ok"]:
            append_unique(paths, result["paths"])
            append_unique(gaps, result["gaps"])
            append_unique(actions, result["next_actions"])
            completed = git(root, "-c", "core.editor=true", "rebase", "--continue", check=False)
            continue
        stderr = str(getattr(completed, "stderr", ""))
        if paths and empty_projection_patch(stderr):
            completed = git(root, "rebase", "--skip", check=False)
            continue
        return projection_rebase_resolution(
            ok=False,
            paths=paths,
            gaps=gaps,
            next_actions=actions,
            stderr=stderr,
        )
    return projection_rebase_resolution(
        ok=False,
        paths=paths,
        gaps=gaps,
        next_actions=actions,
        stderr="projection rebase recovery exceeded bounded step limit",
    )
