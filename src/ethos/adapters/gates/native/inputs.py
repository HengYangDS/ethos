"""Observe exact native quality inputs and mandatory configuration without formatting."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.git_attributes import binary_content_paths
from ethos.adapters.repo.git_attributes import received_paths
from ethos.repository.policy.gates import resolve_gate_declaration
from ethos.repository.policy.projections import PROJECTION_DECLARATIONS
from ethos.repository.policy.projections import projection_relations
from ethos.repository.policy.quality.format_selection import POLICY_PATH
from ethos.repository.policy.quality.format_selection import audit
from ethos.repository.policy.quality.format_selection import declared_paths
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
    from collections.abc import Sequence
    from pathlib import Path

    from ethos.repository.policy.quality.format_selection import CarrierAudit
    from ethos.repository.policy.quality.format_selection import OwnerDeclaration


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


def authored_text_files(root: Path, files: Sequence[str]) -> tuple[str, ...]:
    """Select declared text before formatters narrow it, preserving received and binary owners."""
    policy = tomllib.loads(canonical_resource(POLICY_PATH.as_posix()).read_text(encoding="utf-8"))
    extensions = {extension for item in policy["format"] for extension in item["extensions"]}
    ownership = format_ownership(root, tuple(files))
    preserved = received_paths(root, tuple(files)) | {
        item["path"]
        for item in ownership["assignments"]
        if item["format_owner"] in {"source-binary", "immutable-carrier"}
    }
    return tuple(
        relative
        for relative in files
        if relative not in preserved
        and (not (root / relative).suffix or (root / relative).suffix.lower() in extensions)
    )


def authored_text_gaps(root: Path, files: Sequence[str]) -> list[str]:
    """Require complete UTF-8 text without NUL; checkout attributes do not decide validity."""
    selected = tuple(dict.fromkeys(files))
    binary = binary_content_paths(root, selected)
    gaps = []
    for path in selected:
        try:
            content = read_regular_bytes(
                root,
                path,
                unsafe_gap=f"authored_text_path_invalid:{path}",
                unstable_gap=f"authored_text_input_changed:{path}",
                size_gap=f"authored_text_input_too_large:{path}",
            )
        except ValueError as error:
            gaps.append(str(error))
            continue
        if path in (binary or ()) or b"\0" in content:
            gaps.append(f"authored_text_binary:{path}")
            continue
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            gaps.append(f"authored_text_encoding:{path}")
    return gaps or (["authored_text_unobserved"] if binary is None else [])


def authored_text_report(root: Path, files: Sequence[str]) -> dict[str, object]:
    """Project the one authored-text judgement as the result a native consumer includes."""
    gaps = authored_text_gaps(root, files)
    return {
        "id": "authored-text",
        "verdict": "block" if gaps else "pass",
        "state": "failed" if gaps else "passed",
        "file_count": len(files),
        "required_gaps": gaps,
    }


def format_ownership(root: Path, paths: tuple[str, ...]) -> CarrierAudit:
    """Join the shipped format ownership with the repository's byte-bound carriers once."""
    product = canonical_resource(POLICY_PATH.as_posix())
    return audit(root, paths=paths, configuration=product, carriers=_carriers(root, product))


def paradigm_received_paths(root: Path, paths: tuple[str, ...]) -> frozenset[str]:
    """Return the paths whose bytes and names are owned outside authoring here.

    Git attributes mark vendored and generated paths, and the repository's verified byte-bound
    carriers freeze theirs. An invalid carrier increment freezes nothing; its gate reports it.
    """
    try:
        carriers = _carriers(root, canonical_resource(POLICY_PATH.as_posix()))
    except (OSError, ValueError):
        carriers = ()
    return received_paths(root, paths) | declared_paths(paths, carriers)


def _carriers(root: Path, product: Path) -> tuple[OwnerDeclaration, ...]:
    """Read the repository's own byte-bound carriers, which the shipped policy never declares."""
    increment = root / POLICY_PATH
    owned = increment.is_file() or increment.is_symlink()
    if not owned or increment.resolve() == product.resolve():
        return ()
    return tuple(repository_carriers(root, gate_ids=_proof_gate_ids(root)))


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
    """Return the repository's own native configuration at its paradigm carrier, if any.

    The tool reads its carrier from the worktree, so an indexed path deleted there is absent.
    """
    live = tuple(p for p in quality_source_files(root) if (root / p).exists(follow_symlinks=False))
    if (selected := native_tool_configuration(live, tool)) is None:
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
