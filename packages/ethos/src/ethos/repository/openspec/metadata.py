"""OpenSpec `.openspec.yaml` metadata compatibility — pure file-reading, repository layer.

Extracted from `ethos.adapters.openspec` so the always-run shape audit
(`ethos.repository.openspec.audit`) can consume it without importing the adapters
layer, which the surface > domain > adapters > repository layering forbids. This logic
touches only the filesystem (no `openspec` CLI, no subprocess), so it belongs in the
repository layer beside the audit that uses it. The adapters archive-metadata code
imports the shared helpers back from here (adapters -> repository is the legal
direction), keeping a single source of truth.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

OPENSPEC_METADATA_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")
ALLOWED_OPENSPEC_METADATA_KEYS = frozenset({"schema", "created", "status"})


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def read_openspec_metadata(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = OPENSPEC_METADATA_PATTERN.fullmatch(line)
        if match is not None:
            metadata[match.group(1)] = match.group(2).strip().strip("\"'")
    return metadata


def openspec_metadata_compatibility_report(root: Path) -> dict[str, Any]:
    """Report `.openspec.yaml` metadata keys incompatible with the official IDE model.

    JetBrains' OpenSpec parser treats change metadata as a closed shape. ETHOS
    therefore checks every active and archived `.openspec.yaml` on the always-run
    product path instead of discovering unknown keys only after an editor opens
    the workspace.
    """
    changes_root = root / "openspec" / "changes"
    metadata_paths = (
        tuple(sorted(changes_root.rglob(".openspec.yaml"))) if changes_root.exists() else ()
    )
    issues: list[dict[str, str]] = []
    for path in metadata_paths:
        metadata = read_openspec_metadata(path)
        for key in sorted(set(metadata) - ALLOWED_OPENSPEC_METADATA_KEYS):
            relative = (
                path.relative_to(root).as_posix() if is_relative_to(path, root) else path.as_posix()
            )
            issues.append(
                {
                    "code": "openspec_metadata_key_unsupported",
                    "key": key,
                    "path": relative,
                    "gap": f"openspec_metadata_key_unsupported:{key}:{relative}",
                }
            )
    required_gaps = sorted({issue["gap"] for issue in issues})
    return {
        "ok": not required_gaps,
        "state": "blocked" if required_gaps else "clean",
        "allowed_keys": sorted(ALLOWED_OPENSPEC_METADATA_KEYS),
        "metadata_files": [path.relative_to(root).as_posix() for path in metadata_paths],
        "issues": sorted(issues, key=lambda issue: (issue["path"], issue["key"])),
        "required_gaps": required_gaps,
        "summary": {
            "metadata_file_count": len(metadata_paths),
            "issue_count": len(issues),
        },
    }
