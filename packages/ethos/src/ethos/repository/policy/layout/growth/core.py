from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
from typing import NamedTuple

import ethos.repository.policy.layout.git.core as layout_git
from ethos.repository.policy.layout.filesystem.core import DEFAULT_FLAT_GROWTH_ADDED_MODULE_LIMIT
from ethos.repository.policy.layout.filesystem.core import DEFAULT_FLAT_GROWTH_EXISTING_MODULE_LIMIT
from ethos.repository.policy.layout.filesystem.core import DEFAULT_PATHS
from ethos.repository.policy.layout.filesystem.core import python_files
from ethos_core.normalization.core import string_list


def flat_growth_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find same-directory flat module growth relative to the layout reference."""
    reference = layout_git.layout_reference(root)
    if reference is None:
        return []
    current = {path.relative_to(root).as_posix() for path in python_files(root, policy)}
    previous = reference_python_files(root, policy, reference)
    added = sorted(rel for rel in current - previous if Path(rel).name != "__init__.py")
    if not added:
        return []

    current_counts = module_counts_by_directory(current)
    previous_counts = module_counts_by_directory(previous)
    grouped: dict[str, list[str]] = defaultdict(list)
    for rel in added:
        grouped[Path(rel).parent.as_posix()].append(rel)

    existing_limit = int(
        policy.get(
            "flat_growth_existing_module_limit",
            DEFAULT_FLAT_GROWTH_EXISTING_MODULE_LIMIT,
        )
    )
    added_limit = int(
        policy.get(
            "flat_growth_added_module_limit",
            DEFAULT_FLAT_GROWTH_ADDED_MODULE_LIMIT,
        )
    )
    context = FlatGrowthContext(
        previous=previous,
        previous_counts=previous_counts,
        current_counts=current_counts,
        existing_limit=existing_limit,
        added_limit=added_limit,
    )
    return _flat_growth_records(grouped, context)


class FlatGrowthContext(NamedTuple):
    """Shared context for same-directory flat-growth decisions."""

    previous: set[str]
    previous_counts: dict[str, int]
    current_counts: dict[str, int]
    existing_limit: int
    added_limit: int


def module_counts_by_directory(files: set[str]) -> dict[str, int]:
    """Count non-`__init__` modules by direct parent directory."""
    counts: dict[str, int] = defaultdict(int)
    for rel in files:
        path = Path(rel)
        if path.name != "__init__.py":
            counts[path.parent.as_posix()] += 1
    return counts


def reference_python_files(root: Path, policy: dict[str, Any], reference: str) -> set[str]:
    """Return governed Python files present at a Git reference."""
    files: set[str] = set()
    for configured in string_list(policy.get("paths")) or list(DEFAULT_PATHS):
        if layout_git.run_git_show(
            root, f"{reference}:{configured}"
        ) is not None and configured.endswith(".py"):
            files.add(configured)
            continue
        output = layout_git.run_git(
            root, "ls-tree", "-r", "--name-only", reference, "--", configured
        )
        if output is None:
            continue
        files.update(
            line
            for line in output.splitlines()
            if line.endswith(".py") and "__pycache__" not in Path(line).parts
        )
    return files


def _flat_growth_records(
    grouped: dict[str, list[str]],
    context: FlatGrowthContext,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for directory, files in sorted(grouped.items()):
        previous_count = context.previous_counts.get(directory, 0)
        new_directory = previous_count == 0 and not _reference_directory_exists(
            directory,
            context.previous,
        )
        current_count = context.current_counts.get(directory, 0)
        if new_directory:
            if len(files) > context.added_limit:
                findings.append(_new_directory_burst_record(directory, files, context.added_limit))
            continue
        if previous_count >= context.existing_limit:
            findings.append(_flat_growth_record(directory, files, previous_count, current_count))
        if len(files) > context.added_limit:
            findings.append(_flat_burst_record(directory, files, context.added_limit))
    return findings


def _flat_growth_record(
    directory: str,
    files: list[str],
    previous_count: int,
    current_count: int,
) -> dict[str, object]:
    gap = f"module_layout_flat_growth:{directory}:{previous_count}+{len(files)}={current_count}"
    return {
        "gap": gap,
        "directory": directory,
        "previous_module_count": previous_count,
        "added_module_count": len(files),
        "module_count": current_count,
        "files": files,
    }


def _flat_burst_record(directory: str, files: list[str], added_limit: int) -> dict[str, object]:
    gap = f"module_layout_flat_growth_burst:{directory}:{len(files)}>{added_limit}"
    return {
        "gap": gap,
        "directory": directory,
        "added_module_count": len(files),
        "files": files,
    }


def _new_directory_burst_record(
    directory: str,
    files: list[str],
    added_limit: int,
) -> dict[str, object]:
    gap = f"module_layout_new_directory_burst:{directory}:{len(files)}>{added_limit}"
    return {
        "gap": gap,
        "directory": directory,
        "added_module_count": len(files),
        "files": files,
    }


def _reference_directory_exists(directory: str, files: set[str]) -> bool:
    prefix = f"{directory}/"
    return any(rel.startswith(prefix) for rel in files)
