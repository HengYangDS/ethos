"""Documentation topology audit for ETHOS and governed repositories."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.repository.profile import load_repository_profile
from ethos_core.contracts.docs.topology import FORBIDDEN_DOCS_ROOTS
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
    profile_policy = _profile_docs_topology_policy(root)
    forbidden = _forbidden_roots(root, profile_policy)
    state_report = _state_metadata_report(root, required, profile_policy)
    missing_state = _string_list(state_report["missing_required_state_paths"])
    invalid_states = _invalid_state_gap_entries(state_report)
    unmapped_states = _unmapped_state_gap_entries(state_report)
    role_mismatches = _role_root_mismatches(root)
    required_gaps = [f"docs_topology_missing:{path}" for path in missing]
    required_gaps.extend(f"docs_topology_state_missing:{path}" for path in missing_state)
    required_gaps.extend(
        f"docs_topology_state_invalid:{path}:{state}" for path, state in invalid_states
    )
    required_gaps.extend(
        f"docs_topology_state_unmapped:{path}:{status}" for path, status in unmapped_states
    )
    required_gaps.extend(
        f"docs_topology_role_root_mismatch:{path}:{role}:{root_name}"
        for path, role, root_name in role_mismatches
    )
    required_gaps.extend(_string_list(profile_policy.get("required_gaps")))
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
            "unmapped_state_count": len(unmapped_states),
            "role_root_mismatch_count": len(role_mismatches),
            "decision_record_path_count": sum(
                1 for entry in required if str(entry["path"]).startswith("docs/decisions/")
            ),
            "product_extension_root_count": len(extension_roots),
        },
        "required_paths": required,
        "missing_paths": missing,
        "forbidden_roots": forbidden,
        "profile_policy": profile_policy,
        "time_state_roots": _string_list(profile_policy.get("time_state_roots")),
        "state_metadata": state_report,
        "role_root_mismatches": [
            {"path": path, "role": role, "root": root_name}
            for path, role, root_name in role_mismatches
        ],
        "product_extension_roots": extension_roots,
        "required_gaps": required_gaps,
    }


def _profile_docs_topology_policy(root: Path) -> dict[str, object]:
    """Return adopter-declared docs topology policy from .ethos/profile.toml.

    The policy is a binding manifest, not documentation truth. It may declare
    that an existing adopter owns compatibility time-state roots while the common
    semantic kernel remains mandatory. Product repositories and repositories
    without this explicit table keep the default fail-closed prohibition.
    """
    profile = load_repository_profile(root)
    table = profile.tables.get("docs_topology", {})
    state_root_policy = str(table.get("state_root_policy") or "forbid_time_state_roots")
    if state_root_policy == "profile_declared_legacy":
        state_root_policy = "adopter_declared_compatibility"
    state_metadata_policy = str(table.get("state_metadata_policy") or "front_matter_state")
    status_field = str(table.get("status_field") or table.get("legacy_status_field") or "Status")
    time_state_roots = _string_list(
        table.get("time_state_roots") or table.get("legacy_time_state_roots")
    )
    compatibility_decision = str(
        table.get("compatibility_decision") or table.get("legacy_decision") or ""
    )
    raw_state_map = table.get("state_value_map")
    state_value_map = (
        {
            str(key): str(value)
            for key, value in raw_state_map.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        if isinstance(raw_state_map, dict)
        else {}
    )
    required_gaps: list[str] = []
    allowed_root_policies = {"forbid_time_state_roots", "adopter_declared_compatibility"}
    allowed_state_policies = {"front_matter_state", "front_matter_or_status_line"}
    if state_root_policy not in allowed_root_policies:
        required_gaps.append(f"docs_topology_profile_state_root_policy_invalid:{state_root_policy}")
    if state_metadata_policy not in allowed_state_policies:
        required_gaps.append(
            f"docs_topology_profile_state_metadata_policy_invalid:{state_metadata_policy}"
        )
    valid_time_state_roots: list[str] = []
    for time_state_root in time_state_roots:
        if time_state_root in FORBIDDEN_DOCS_ROOTS:
            valid_time_state_roots.append(time_state_root)
        else:
            required_gaps.append(f"docs_topology_profile_time_state_root_invalid:{time_state_root}")
    time_state_roots = valid_time_state_roots
    needs_compatibility_decision = (
        state_root_policy == "adopter_declared_compatibility" and bool(time_state_roots)
    ) or state_metadata_policy == "front_matter_or_status_line"
    if needs_compatibility_decision:
        decision_gap = _compatibility_decision_gap(root, compatibility_decision)
        if decision_gap:
            required_gaps.append(decision_gap)
    if state_root_policy != "adopter_declared_compatibility":
        time_state_roots = []
    return {
        "source": profile.source,
        "state_root_policy": state_root_policy,
        "time_state_roots": time_state_roots,
        "compatibility_decision": compatibility_decision,
        "state_metadata_policy": state_metadata_policy,
        "status_field": status_field,
        "state_value_map": state_value_map,
        "required_gaps": required_gaps,
    }


def _compatibility_decision_gap(root: Path, compatibility_decision: str) -> str:
    if not compatibility_decision:
        return "docs_topology_profile_compatibility_decision_missing"
    decision_path = root / compatibility_decision
    try:
        decision_path.resolve().relative_to(root.resolve())
    except ValueError:
        return f"docs_topology_profile_compatibility_decision_outside_repo:{compatibility_decision}"
    if not decision_path.exists():
        return f"docs_topology_profile_compatibility_decision_missing:{compatibility_decision}"
    return ""


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
    profile_policy: dict[str, object],
) -> dict[str, object]:
    state_by_path = _docs_state_by_path(root)
    status_by_path: dict[str, str] = {}
    unmapped: list[dict[str, str]] = []
    if profile_policy.get("state_metadata_policy") == "front_matter_or_status_line":
        status_field = str(profile_policy.get("status_field") or "Status")
        state_value_map_raw = profile_policy.get("state_value_map")
        state_value_map = (
            {str(key): str(value) for key, value in state_value_map_raw.items()}
            if isinstance(state_value_map_raw, dict)
            else {}
        )
        status_by_path = _docs_status_by_path(root, status_field)
        for rel_path, status in sorted(status_by_path.items()):
            if rel_path in state_by_path:
                continue
            mapped = state_value_map.get(status)
            if mapped:
                state_by_path[rel_path] = mapped
            else:
                unmapped.append({"path": rel_path, "status": status})
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
        "status_by_path": status_by_path,
        "missing_required_state_paths": missing_required_state,
        "invalid_states": invalid,
        "unmapped_states": unmapped,
    }


def _invalid_state_gap_entries(state_report: dict[str, object]) -> list[tuple[str, str]]:
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


def _unmapped_state_gap_entries(state_report: dict[str, object]) -> list[tuple[str, str]]:
    raw = state_report.get("unmapped_states")
    if not isinstance(raw, list):
        return []
    entries: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        status = item.get("status")
        if isinstance(path, str) and isinstance(status, str):
            entries.append((path, status))
    return entries


def _docs_state_by_path(root: Path) -> dict[str, str]:
    return _docs_field_by_path(root, "state:")


def _docs_status_by_path(root: Path, field: str) -> dict[str, str]:
    docs_root = root / "docs"
    if not docs_root.exists():
        return {}
    marker = f"{field}:"
    values: dict[str, str] = {}
    for path in sorted(docs_root.rglob("*.md")):
        if not path.is_file():
            continue
        value = _line_field(path, marker)
        if value:
            values[path.relative_to(root).as_posix()] = value
    return values


def _line_field(path: Path, field: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(field):
            return stripped.split(":", maxsplit=1)[1].strip().strip("\"'")
    return ""


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


def _front_matter_state(path: Path) -> str:
    return _front_matter_field(path, "state:")


def _extension_roots(root: Path) -> list[str]:
    return sorted(path for path in PRODUCT_EXTENSION_ROOTS if (root / path).exists())


def _forbidden_roots(root: Path, profile_policy: dict[str, object] | None = None) -> list[str]:
    time_state_roots = set(_string_list((profile_policy or {}).get("time_state_roots")))
    return sorted(
        path
        for path in forbidden_docs_topology_roots()
        if (root / path).exists() and path not in time_state_roots
    )
