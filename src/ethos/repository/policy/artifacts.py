"""Generated artifact topology audit."""

from __future__ import annotations

import subprocess
from os import walk
from pathlib import Path
from typing import Any

from ethos.adapters.repo.git import run_git
from ethos.contracts.artifacts.topology import GeneratedArtifactTopologyDeclaration
from ethos.contracts.artifacts.topology import generated_artifact_contract
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration
from ethos.repository.policy.artifact_entrypoints import generated_artifact_entrypoint_audit

_ROOT_TEST_RESIDUE_FILENAMES = frozenset({".coverage", "coverage.xml", "junit.xml"})
_ROOT_TEST_RESIDUE_PREFIXES = (".coverage.",)


_PRUNE_DIRS = frozenset({".git", ".pixi", ".venv", "__pycache__", "node_modules"})


def generated_artifact_topology_report(root: Path) -> dict[str, Any]:
    """Report generated artifact placement drift without mutating the repository."""
    declaration = load_generated_artifact_topology_declaration(
        root / "system/policies/generated-artifact-topology.toml"
    )
    allowed_paths: list[str] = []
    denied_paths: list[str] = []
    review_paths: list[str] = []
    ignored_local_paths: list[str] = []
    tracked_untracked_paths = _tracked_untracked_paths(root, declaration)
    review_gaps: list[str] = []
    path_blockers: list[str] = []

    for path in _candidate_paths(root, declaration):
        rel = path.relative_to(root).as_posix()
        if _is_ignored_local_test_residue(root, rel):
            ignored_local_paths.append(rel)
            continue

        policy = path_policy_from_declaration(rel, declaration)
        decision = str(policy["decision"])
        if decision == "allow":
            allowed_paths.append(rel)
        elif decision == "review":
            review_paths.append(rel)
            review_gap = str(policy.get("required_gap") or "")
            if review_gap:
                review_gaps.append(review_gap)
        elif decision == "deny":
            denied_paths.append(rel)
            required_gap = str(policy.get("required_gap") or "")
            if required_gap:
                path_blockers.append(required_gap)

    entrypoint_audit = generated_artifact_entrypoint_audit(root)
    entrypoint_blockers = [str(gap) for gap in entrypoint_audit["required_gaps"]]
    path_blockers.extend(
        f"generated_artifact_tracked_untracked_home:{path}" for path in tracked_untracked_paths
    )
    required_gaps = sorted({*path_blockers, *entrypoint_blockers})

    allowed_paths.sort()
    denied_paths.sort()
    review_paths.sort()
    ignored_local_paths.sort()
    tracked_untracked_paths.sort()
    review_gaps.sort()
    path_blockers.sort()
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "contract": generated_artifact_contract(declaration),
        "summary": {
            "allowed_path_count": len(allowed_paths),
            "denied_path_count": len(denied_paths),
            "review_path_count": len(review_paths),
            "ignored_local_path_count": len(ignored_local_paths),
            "tracked_untracked_path_count": len(tracked_untracked_paths),
            "review_gap_count": len(review_gaps),
            "path_blocker_count": len(path_blockers),
            "entrypoint_checked_file_count": entrypoint_audit["summary"]["checked_file_count"],
            "entrypoint_blocker_count": entrypoint_audit["summary"]["blocker_count"],
            "blocker_count": len(required_gaps),
        },
        "allowed_paths": allowed_paths,
        "denied_paths": denied_paths,
        "review_paths": review_paths,
        "ignored_local_paths": ignored_local_paths,
        "tracked_untracked_paths": tracked_untracked_paths,
        "review_gaps": review_gaps,
        "path_blockers": path_blockers,
        "entrypoint_audit": entrypoint_audit,
        "required_gaps": required_gaps,
    }


def _candidate_paths(root: Path, declaration: GeneratedArtifactTopologyDeclaration) -> list[Path]:
    candidates = {
        rel: root / rel for rel in _explicit_denied_roots(declaration) if (root / rel).exists()
    }
    prefixes = (
        *declaration.product_adopter_root_prefixes,
        *(
            item.prefix.rstrip("/")
            for group in (
                "declarative_prefix",
                "review_prefix",
                "denied_prefix",
                "denied_root_cache_prefix",
                "denied_legacy_generated_prefix",
            )
            for item in getattr(declaration, group)
        ),
        declaration.cache_flat_root_prefix,
        declaration.runtime_flat_root_prefix,
    )
    descendant_prefixes = tuple(f"{prefix}/" for prefix in prefixes)
    for parent, directories, filenames in walk(root, topdown=True):
        directory = Path(parent)
        rel_directory = directory.relative_to(root)
        directories[:] = [
            name for name in directories if not _skip_descendant(rel_directory / name, declaration)
        ]
        if directory != root:
            rel = rel_directory.as_posix()
            if rel not in candidates and (rel in prefixes or rel.startswith(descendant_prefixes)):
                policy = path_policy_from_declaration(rel_directory, declaration)
                if policy["decision"] == "deny" and not any(
                    child.is_file() for child in directory.rglob("*")
                ):
                    candidates[rel] = directory
        for name in filenames:
            path = directory / name
            rel = path.relative_to(root).as_posix()
            generated = (
                name not in declaration.source_metadata_filenames
                and not name.endswith(declaration.source_schema_suffix)
                and (
                    name in declaration.generated_filenames
                    or path.suffix in declaration.generated_suffixes
                    or name.startswith(declaration.generated_filename_prefixes)
                )
            )
            if (
                rel not in candidates
                and (generated or rel in prefixes or rel.startswith(descendant_prefixes))
                and path_policy_from_declaration(path.relative_to(root), declaration)["decision"]
                != "ignore"
            ):
                candidates[rel] = path
    return [candidates[key] for key in sorted(candidates)]


def _skip_descendant(rel: Path, declaration: GeneratedArtifactTopologyDeclaration) -> bool:
    """Skip excluded implementation trees and recursive allowed artifact homes."""
    return rel.name in _PRUNE_DIRS or any(
        rel.as_posix() == item.prefix.rstrip("/") for item in declaration.allowed_prefix
    )


def _explicit_denied_roots(declaration: GeneratedArtifactTopologyDeclaration) -> list[str]:
    contract = generated_artifact_contract(declaration)
    return [
        prefix
        for group in ("denied_root_cache_prefixes", "denied_legacy_generated_prefixes")
        for item in contract[group]
        if (prefix := str(item["prefix"]).rstrip("/"))
    ]


def _is_ignored_local_test_residue(root: Path, rel: str) -> bool:
    return (
        "/" not in rel
        and (rel in _ROOT_TEST_RESIDUE_FILENAMES or rel.startswith(_ROOT_TEST_RESIDUE_PREFIXES))
        and _git_status_check(root, "check-ignore", "--quiet", "--", rel)
        and not _git_status_check(root, "ls-files", "--error-unmatch", "--", rel)
    )


def _tracked_untracked_paths(
    root: Path, declaration: GeneratedArtifactTopologyDeclaration
) -> list[str]:
    homes = tuple(
        home.rstrip("/")
        for lifecycle in declaration.lifecycle_class
        if not lifecycle.tracked
        for home in lifecycle.homes
    )
    completed = run_git(root, "ls-files", "--", *homes, check=False)
    return sorted(
        path for path in completed.stdout.splitlines() if path and path != ".ethos/state/.gitignore"
    )


def _git_status_check(root: Path, *args: str) -> bool:
    return (
        subprocess.run(
            ("git", *args),
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )
