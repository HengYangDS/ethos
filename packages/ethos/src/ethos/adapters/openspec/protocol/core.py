from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

REQUIRED_PROPOSAL_METADATA = (
    "subject",
    "reuse",
    "change",
    "facet:lifecycle",
    "facet:surface",
    "facet:authority",
)
VALID_REUSE_STANCES = {"reuse", "extend", "extract", "new"}
VALID_CHANGE_DIRECTIONS = {"add", "modify", "remove", "rename", "retire"}


def proposal_protocol_report(root: Path, change_name: str) -> dict[str, Any]:
    """Report ETHOS-specific OpenSpec proposal protocol gaps."""
    proposal = root / "openspec" / "changes" / change_name / "proposal.md"
    if not proposal.exists():
        return {"ok": True, "required_gaps": [], "capabilities": [], "out_of_scope": False}
    text = proposal.read_text(encoding="utf-8")
    gaps: list[str] = []
    out_of_scope = any(
        line.strip().casefold() in {"## out of scope", "## out-of-scope"}
        for line in text.splitlines()
    )
    if not out_of_scope:
        gaps.append(f"openspec_proposal_out_of_scope_missing:{change_name}")
    capabilities = proposal_capability_entries(text)
    if not capabilities:
        gaps.append(f"openspec_proposal_capabilities_missing:{change_name}")
    for entry in capabilities:
        capability = str(entry["capability"])
        metadata = entry["metadata"]
        if not (root / "openspec" / "specs" / capability / "spec.md").exists():
            gaps.append(f"openspec_proposal_capability_unknown:{change_name}:{capability}")
        gaps.extend(capability_profile_gaps(root, change_name, capability))
        for field in REQUIRED_PROPOSAL_METADATA:
            if not metadata.get(field):
                gaps.append(
                    f"openspec_proposal_metadata_missing:{change_name}:{capability}:{field}"
                )
        reuse = metadata.get("reuse", "")
        if reuse and reuse not in VALID_REUSE_STANCES:
            gaps.append(f"openspec_proposal_reuse_invalid:{change_name}:{capability}:{reuse}")
        direction = metadata.get("change", "")
        if direction and direction not in VALID_CHANGE_DIRECTIONS:
            gaps.append(f"openspec_proposal_change_invalid:{change_name}:{capability}:{direction}")
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "capabilities": capabilities,
        "out_of_scope": out_of_scope,
    }


def proposal_capability_entries(text: str) -> list[dict[str, Any]]:
    """Parse capability metadata entries from an OpenSpec proposal body."""
    entries: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and "`:" in stripped:
            if current:
                entries.append(proposal_capability_entry(current["capability"], current["raw"]))
            capability = stripped.split("`", 2)[1]
            current = {"capability": capability, "raw": stripped.split("`:", 1)[1]}
            continue
        if current and line[:1].isspace() and not stripped.startswith("- `"):
            current["raw"] = f"{current['raw']} {stripped}"
            continue
        if current and stripped.startswith("- "):
            entries.append(proposal_capability_entry(current["capability"], current["raw"]))
            current = None
    if current:
        entries.append(proposal_capability_entry(current["capability"], current["raw"]))
    return entries


def proposal_capability_entry(capability: str, raw: str) -> dict[str, Any]:
    """Parse one proposal capability metadata entry."""
    metadata: dict[str, str] = {}
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        metadata[key.strip()] = value.strip().strip("`")
    return {"capability": capability, "metadata": metadata}


def capability_profile_gaps(root: Path, change_name: str, capability: str) -> list[str]:
    """Return required gaps for one OpenSpec capability profile."""
    profile_path = root / "openspec" / "specs" / capability / "capability.toml"
    payload, payload_gaps = _capability_profile_payload(profile_path, change_name, capability)
    if payload_gaps:
        return payload_gaps
    return [
        *_top_level_profile_field_gaps(payload, change_name, capability),
        *_nested_profile_field_gaps(payload, change_name, capability),
    ]


def _capability_profile_payload(
    profile_path: Path,
    change_name: str,
    capability: str,
) -> tuple[dict[str, Any], list[str]]:
    if not profile_path.exists():
        return {}, [f"openspec_capability_profile_missing:{change_name}:{capability}"]
    try:
        return tomllib.loads(profile_path.read_text(encoding="utf-8")), []
    except tomllib.TOMLDecodeError:
        return {}, [f"openspec_capability_profile_invalid:{change_name}:{capability}"]


def _top_level_profile_field_gaps(
    payload: dict[str, Any],
    change_name: str,
    capability: str,
) -> list[str]:
    fields = (
        "family",
        "primary_invariant",
        "routing_question",
        "decision_axes",
        "recommended_facets",
        "boundary_rules",
    )
    return [
        _capability_profile_field_gap(change_name, capability, field)
        for field in fields
        if not payload.get(field)
    ]


def _nested_profile_field_gaps(
    payload: dict[str, Any],
    change_name: str,
    capability: str,
) -> list[str]:
    return [
        *_missing_nested_profile_fields(
            payload,
            section="owner",
            fields=("package", "scope"),
            change_name=change_name,
            capability=capability,
        ),
        *_missing_nested_profile_fields(
            payload,
            section="proof_profile",
            fields=("default_command", "executed_command", "required_gates"),
            change_name=change_name,
            capability=capability,
        ),
    ]


def _missing_nested_profile_fields(
    payload: dict[str, Any],
    *,
    section: str,
    fields: tuple[str, ...],
    change_name: str,
    capability: str,
) -> list[str]:
    values = payload.get(section, {})
    return [
        _capability_profile_field_gap(change_name, capability, f"{section}.{field}")
        for field in fields
        if not isinstance(values, dict) or not values.get(field)
    ]


def _capability_profile_field_gap(change_name: str, capability: str, field: str) -> str:
    return f"openspec_capability_profile_field_missing:{change_name}:{capability}:{field}"
