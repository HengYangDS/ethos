"""Documentation topology audit for ETHOS and governed repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos_core.contracts.docs.topology import PRODUCT_EXTENSION_ROOTS
from ethos_core.contracts.docs.topology import docs_topology_contract
from ethos_core.contracts.docs.topology import required_docs_topology_paths

if TYPE_CHECKING:
    from pathlib import Path


def docs_topology_report(root: Path) -> dict[str, object]:
    """Report whether a repository exposes the common governed docs topology."""
    required = _required_path_entries(root)
    missing = [entry["path"] for entry in required if not entry["exists"]]
    required_gaps = [f"docs_topology_missing:{path}" for path in missing]
    extension_roots = _extension_roots(root)
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "contract": docs_topology_contract(),
        "summary": {
            "required_path_count": len(required),
            "missing_required_path_count": len(missing),
            "decision_record_path_count": sum(
                1 for entry in required if str(entry["path"]).startswith("docs/decisions/")
            ),
            "product_extension_root_count": len(extension_roots),
        },
        "required_paths": required,
        "missing_paths": missing,
        "product_extension_roots": extension_roots,
        "required_gaps": required_gaps,
    }


def _required_path_entries(root: Path) -> list[dict[str, object]]:
    contract = docs_topology_contract()
    boundary_by_path = {
        str(entry["path"]): str(entry["boundary"])
        for entry in contract["required_paths"]
        if isinstance(entry, dict)
    }
    return [
        {
            "path": path,
            "boundary": boundary_by_path[path],
            "exists": (root / path).exists(),
        }
        for path in required_docs_topology_paths()
    ]


def _extension_roots(root: Path) -> list[str]:
    return sorted(path for path in PRODUCT_EXTENSION_ROOTS if (root / path).exists())
