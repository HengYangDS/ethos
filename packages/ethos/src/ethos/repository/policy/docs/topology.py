"""Documentation topology audit for ETHOS and governed repositories."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos_core.contracts.docs.topology import PRODUCT_EXTENSION_ROOTS
from ethos_core.contracts.docs.topology import STATE_VALUES
from ethos_core.contracts.docs.topology import docs_topology_contract
from ethos_core.contracts.docs.topology import forbidden_docs_topology_roots
from ethos_core.contracts.docs.topology import kernel_role_roots
from ethos_core.contracts.docs.topology import required_docs_topology_paths

if TYPE_CHECKING:
    from pathlib import Path


def docs_topology_report(root: Path) -> dict[str, object]:
    """Report whether a repository exposes the common governed docs topology."""
    required = _required_path_entries(root)
    missing = [entry["path"] for entry in required if not entry["exists"]]
    forbidden = _forbidden_roots(root)
    state_report = _state_metadata_report(root, required)
    missing_state = _string_list(state_report["missing_required_state_paths"])
    invalid_states = _invalid_state_gap_entries(state_report)
    role_mismatches = _role_root_mismatches(root)
    required_gaps = [f"docs_topology_missing:{path}" for path in missing]
    required_gaps.extend(f"docs_topology_state_missing:{path}" for path in missing_state)
    required_gaps.extend(
        f"docs_topology_state_invalid:{path}:{state}" for path, state in invalid_states
    )
    required_gaps.extend(
        f"docs_topology_role_root_mismatch:{path}:{role}:{root_name}"
        for path, role, root_name in role_mismatches
    )
    required_gaps.extend(f"docs_topology_forbidden_time_state_root:{path}" for path in forbidden)
    extension_roots = _extension_roots(root)
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "contract": docs_topology_contract(),
        "summary": {
            "required_path_count": len(required),
            "missing_required_path_count": len(missing),
            "forbidden_root_count": len(forbidden),
            "missing_required_state_count": len(missing_state),
            "invalid_state_count": len(invalid_states),
            "role_root_mismatch_count": len(role_mismatches),
            "decision_record_path_count": sum(
                1 for entry in required if str(entry["path"]).startswith("docs/decisions/")
            ),
            "product_extension_root_count": len(extension_roots),
        },
        "required_paths": required,
        "missing_paths": missing,
        "forbidden_roots": forbidden,
        "state_metadata": state_report,
        "role_root_mismatches": [
            {"path": path, "role": role, "root": root_name}
            for path, role, root_name in role_mismatches
        ],
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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _state_metadata_report(
    root: Path,
    required: list[dict[str, object]],
) -> dict[str, object]:
    state_by_path = _docs_state_by_path(root)
    required_existing = [
        str(entry["path"])
        for entry in required
        if bool(entry["exists"]) and isinstance(entry.get("path"), str)
    ]
    missing_required_state = [path for path in required_existing if path not in state_by_path]
    invalid = [
        {"path": path, "state": state}
        for path, state in sorted(state_by_path.items())
        if state not in STATE_VALUES
    ]
    return {
        "supported_state_values": list(STATE_VALUES),
        "required_state_paths": required_existing,
        "state_by_path": state_by_path,
        "missing_required_state_paths": missing_required_state,
        "invalid_states": invalid,
    }


def _invalid_state_gap_entries(
    state_report: dict[str, object],
) -> list[tuple[str, str]]:
    raw = state_report.get("invalid_states")
    if not isinstance(raw, list):
        return []
    entries: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        state = item.get("state")
        if isinstance(path, str) and isinstance(state, str):
            entries.append((path, state))
    return entries


def _docs_state_by_path(root: Path) -> dict[str, str]:
    return _docs_field_by_path(root, "state:")


def _docs_role_by_path(root: Path) -> dict[str, str]:
    return _docs_field_by_path(root, "role:")


def _docs_field_by_path(root: Path, field: str) -> dict[str, str]:
    docs_root = root / "docs"
    if not docs_root.exists():
        return {}
    values: dict[str, str] = {}
    for path in sorted(docs_root.rglob("*.md")):
        if not path.is_file():
            continue
        value = _front_matter_field(path, field)
        if value:
            values[path.relative_to(root).as_posix()] = value
    return values


def _front_matter_field(path: Path, field: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return ""
        if stripped.startswith(field):
            return stripped.split(":", maxsplit=1)[1].strip().strip("\"'")
    return ""


def _extension_root_law(root: Path) -> dict[str, set[str]]:
    """Return per-root allowed-role sets declared in the repo taxonomy.

    ETHOS ships its own product extension-root law in docs/_meta/taxonomy.toml;
    adopters declare theirs the same way. Kernel bindings are enforced separately
    from the contract, so they are not required here.
    """
    path = root / "docs" / "_meta" / "taxonomy.toml"
    if not path.exists():
        return {}
    try:
        taxonomy = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    section = taxonomy.get("extension_roots")
    if not isinstance(section, dict):
        return {}
    law: dict[str, set[str]] = {}
    for extension_root, roles in section.items():
        if isinstance(roles, list):
            law[str(extension_root)] = {role for role in roles if isinstance(role, str)}
    return law


def _root_of(rel_path: str) -> str:
    parts = rel_path.split("/")
    return "/".join(parts[:2]) if len(parts) > 2 else "docs"


def _role_root_mismatches(root: Path) -> list[tuple[str, str, str]]:
    """Return (path, role, root) where a document's role is illegal for its directory.

    A role is legal in a directory when (a) it is a kernel role bound to that
    directory, or (b) the directory is an extension root whose taxonomy law
    permits that role. `index` (a README index) is legal in any root. A role in
    a directory with no governing binding at all is a mismatch — this forces
    extension roots to declare their contract rather than sprawl.
    """
    kernel = kernel_role_roots()
    # Invert kernel bindings: for each root, which kernel roles are legal there.
    kernel_by_root: dict[str, set[str]] = {}
    for role, roots in kernel.items():
        for kernel_root in roots:
            kernel_by_root.setdefault(kernel_root, set()).add(role)
    extension_law = _extension_root_law(root)
    mismatches: list[tuple[str, str, str]] = []
    for rel_path, role in sorted(_docs_role_by_path(root).items()):
        if role == "index":
            continue
        doc_root = _root_of(rel_path)
        allowed = kernel_by_root.get(doc_root, set()) | extension_law.get(doc_root, set())
        if role not in allowed:
            mismatches.append((rel_path, role, doc_root))
    return mismatches


def _extension_roots(root: Path) -> list[str]:
    return sorted(path for path in PRODUCT_EXTENSION_ROOTS if (root / path).exists())


def _forbidden_roots(root: Path) -> list[str]:
    return sorted(path for path in forbidden_docs_topology_roots() if (root / path).exists())
