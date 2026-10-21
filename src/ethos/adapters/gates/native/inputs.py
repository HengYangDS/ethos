"""Observe exact native quality inputs and mandatory configuration without formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.gates import resolve_gate_declaration
from ethos.repository.policy.projections import PROJECTION_DECLARATIONS
from ethos.repository.policy.projections import projection_relations
from ethos.repository.policy.quality.format_selection import POLICY_PATH
from ethos.repository.policy.quality.format_selection import audit
from ethos.repository.policy.quality.format_selection import repository_carriers
from ethos.repository.policy.quality.source_budget import policy_for_root
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.policy.rules.config import path_matches
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.resources import canonical_resource
from ethos.repository.release.resources import packaged_resource
from ethos.repository.release.resources import require_packaged_resource

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path

    from ethos.repository.policy.quality.format_selection import CarrierAudit


def quality_source_files(root: Path, *patterns: str) -> list[str]:
    """Read current authored input through native Git without swallowing inventory failure."""
    return git_files(
        root, "--cached", "--others", "--exclude-standard", "--", *patterns, check=True
    )


def authored_source_files(root: Path, *patterns: str, paths: tuple[str, ...] = ()) -> list[str]:
    """Join authored inputs once, preserving producer, upstream and archived-record ownership."""
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    foreign = profile.declaration.proof.source_kinds if profile.declaration else {}
    declarations = {
        path: (root / path).read_text(encoding="utf-8")
        for path in PROJECTION_DECLARATIONS
        if (root / path).is_file()
    }
    generated = {item.output for item in projection_relations(declarations)}
    policy, gaps = policy_for_root(canonical_resource())
    if policy is None or gaps:
        raise ValueError(gaps[0] if gaps else "source_budget_policy_invalid")
    dependencies = tuple(
        pattern
        for item in policy.carriers
        if item.category == "dependency_resolution"
        for pattern in item.paths
    )
    selected = [
        relative
        for relative in paths or quality_source_files(root, *patterns)
        if relative not in foreign
        and relative not in generated
        and not relative.startswith(("evidence/", "docs/archive/", "openspec/changes/archive/"))
        and not path_matches(relative, dependencies)
    ]
    if any(relative.endswith(".md") for relative in selected):
        origins = observed_document_origins(root)
        if origins.required_gaps:
            raise ValueError(origins.required_gaps[0])
        selected = [relative for relative in selected if relative not in origins.entries]
    return selected


def format_ownership(root: Path, paths: tuple[str, ...]) -> CarrierAudit:
    """Join the shipped format ownership with the repository's byte-bound carriers once."""
    product = canonical_resource(POLICY_PATH.as_posix())
    increment = root / POLICY_PATH
    carriers = (
        tuple(repository_carriers(root, gate_ids=_proof_gate_ids(root)))
        if (increment.is_file() or increment.is_symlink())
        and increment.resolve() != product.resolve()
        else ()
    )
    return audit(root, paths=paths, configuration=product, carriers=carriers)


def _proof_gate_ids(root: Path) -> frozenset[str]:
    """Name the full proof set whose gates may verify byte-bound carriers."""
    profile = load_repository_profile(root)
    registry = profile.declaration.proof.gate_registry if profile.declaration else None
    source = root / registry if registry else None
    declaration, _profile = resolve_gate_declaration(
        profile,
        gate_registry_source=source.read_bytes()
        if source is not None and source.is_file() and not source.is_symlink()
        else None,
    )
    return frozenset(declaration.proof_sets.full)


def quality_inventory_failure(
    root: Path, gate_id: str, error: GitExecutionError | subprocess.CalledProcessError
) -> dict[str, object]:
    """Unavailable input remains unknown with its original native execution evidence."""
    evidence = (
        error.evidence()
        if isinstance(error, GitExecutionError)
        else {
            "command": list(error.cmd),
            "cwd": str(root),
            "exit_code": error.returncode,
            "stdout": error.stdout.decode(errors="replace")
            if isinstance(error.stdout, bytes)
            else error.stdout or "",
            "stderr": error.stderr.decode(errors="replace")
            if isinstance(error.stderr, bytes)
            else error.stderr or "",
        }
    )
    return {
        "id": gate_id,
        "verdict": "unknown",
        "state": "inventory_unavailable",
        "file_count": 0,
        "required_gaps": [f"quality_input_inventory_unavailable:{gate_id}"],
        "errors": [evidence],
    }


def native_repository_configuration(root: Path, tool: str) -> Path | None:
    """Return the repository's own native configuration at its paradigm carrier, if any."""
    selected = native_tool_configuration(tuple(quality_source_files(root)), tool)
    if selected is None:
        return None
    path = root / selected
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        message = f"native_tool_configuration_invalid:{tool}"
        raise ValueError(message)
    return path


def native_configurations(root: Path, tool: str, shared: str) -> tuple[str, ...]:
    """The shipped policy is mandatory; repository policy is a native increment."""
    common = canonical_resource(shared)
    if common == packaged_resource(shared):
        common = require_packaged_resource(shared)
    path = native_repository_configuration(root, tool)
    if path is not None and path.resolve() != common.resolve():
        return str(common), str(path)
    return (str(common),)
