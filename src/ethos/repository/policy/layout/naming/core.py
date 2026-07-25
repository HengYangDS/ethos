from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.layout.filesystem.core import DEFAULT_FLAT_DIRECTORY_LIMIT
from ethos.repository.policy.layout.filesystem.core import DEFAULT_SUFFIX_GROUP_MIN
from ethos.repository.policy.layout.filesystem.core import python_files

if TYPE_CHECKING:
    from pathlib import Path


def suffix_module_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find suffix-flat module names such as `foo_report.py`."""
    findings: list[dict[str, object]] = []
    for path in python_files(root, policy):
        if path.name == "__init__.py" or path.stem.startswith("_") or "_" not in path.stem:
            continue
        rel = path.relative_to(root).as_posix()
        gap = f"module_layout_suffix_module:{rel}:{path.stem}"
        findings.append({"gap": gap, "path": rel, "module": path.stem})
    return findings


def suffix_group_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find grouped suffix-flat modules sharing one prefix."""
    minimum = int(policy.get("suffix_flat_group_min", DEFAULT_SUFFIX_GROUP_MIN))
    grouped: dict[Path, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for path in python_files(root, policy):
        if path.name == "__init__.py" or path.stem.startswith("_") or "_" not in path.stem:
            continue
        prefix, _suffix = path.stem.split("_", maxsplit=1)
        grouped[path.parent.relative_to(root)][prefix].append(path.name)
    findings: list[dict[str, object]] = []
    for parent, groups in sorted(grouped.items()):
        parent_text = parent.as_posix()
        for prefix, names in sorted(groups.items()):
            if len(names) < minimum:
                continue
            gap = f"module_layout_suffix_flat:{parent_text}:{prefix}:{len(names)}"
            findings.append(
                {"gap": gap, "directory": parent_text, "prefix": prefix, "files": names}
            )
    return findings


def flat_directory_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find directories with too many direct governed Python modules."""
    limit = int(policy.get("flat_directory_limit", DEFAULT_FLAT_DIRECTORY_LIMIT))
    counts: dict[Path, int] = defaultdict(int)
    for path in python_files(root, policy):
        if path.name != "__init__.py":
            counts[path.parent.relative_to(root)] += 1
    findings: list[dict[str, object]] = []
    for directory, count in sorted(counts.items()):
        directory_text = directory.as_posix()
        if count <= limit:
            continue
        gap = f"module_layout_flat_directory:{directory_text}:{count}>{limit}"
        findings.append({"gap": gap, "directory": directory_text, "module_count": count})
    return findings
