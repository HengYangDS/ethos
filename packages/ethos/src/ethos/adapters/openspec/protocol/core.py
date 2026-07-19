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
PROFILE_FIELDS = (
    "family",
    "primary_invariant",
    "routing_question",
    "decision_axes",
    "recommended_facets",
    "boundary_rules",
    "owner.package",
    "owner.scope",
    "proof_profile.default_command",
    "proof_profile.executed_command",
    "proof_profile.required_gates",
)


def _proposal_report(
    gaps: list[str], capabilities: list[dict[str, Any]], *, out_of_scope: bool
) -> dict[str, Any]:
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "capabilities": capabilities,
        "out_of_scope": out_of_scope,
    }


def proposal_protocol_report(root: Path, change_name: str) -> dict[str, Any]:
    """Report ETHOS-specific OpenSpec proposal protocol gaps."""
    proposal = root / "openspec" / "changes" / change_name / "proposal.md"
    if not proposal.exists():
        return _proposal_report([], [], out_of_scope=False)
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
        gaps.extend(
            f"openspec_proposal_metadata_missing:{change_name}:{capability}:{field}"
            for field in REQUIRED_PROPOSAL_METADATA
            if not metadata.get(field)
        )
        for field, valid, gap in (
            ("reuse", VALID_REUSE_STANCES, "openspec_proposal_reuse_invalid"),
            ("change", VALID_CHANGE_DIRECTIONS, "openspec_proposal_change_invalid"),
        ):
            if (value := metadata.get(field, "")) and value not in valid:
                gaps.append(f"{gap}:{change_name}:{capability}:{value}")
    return _proposal_report(gaps, capabilities, out_of_scope=out_of_scope)


def proposal_capability_entries(text: str) -> list[dict[str, Any]]:
    """Parse capability metadata entries from an OpenSpec proposal body."""
    entries: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    for line in (*text.splitlines(), "- flush"):
        stripped = line.strip()
        starts_entry = stripped.startswith("- `") and "`:" in stripped
        if current and (starts_entry or stripped.startswith("- ")):
            entries.append(proposal_capability_entry(current["capability"], current["raw"]))
            current = None
        if starts_entry:
            capability = stripped.split("`", 2)[1]
            current = {"capability": capability, "raw": stripped.split("`:", 1)[1]}
        elif current and line[:1].isspace():
            current["raw"] = f"{current['raw']} {stripped}"
    return entries


def proposal_capability_entry(capability: str, raw: str) -> dict[str, Any]:
    """Parse one proposal capability metadata entry."""
    return {
        "capability": capability,
        "metadata": {
            key.strip(): value.strip().strip("`")
            for part in raw.split(";")
            if "=" in part
            for key, value in (part.split("=", 1),)
        },
    }


def capability_profile_gaps(root: Path, change_name: str, capability: str) -> list[str]:
    """Return required gaps for one OpenSpec capability profile."""
    profile_path = root / "openspec" / "specs" / capability / "capability.toml"
    payload, payload_gaps = _capability_profile_payload(profile_path, change_name, capability)
    return payload_gaps or [
        f"openspec_capability_profile_field_missing:{change_name}:{capability}:{field}"
        for field in PROFILE_FIELDS
        if not _profile_field(payload, field)
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


def _profile_field(payload: dict[str, Any], field: str) -> object:
    section, separator, nested = field.partition(".")
    value = payload.get(section)
    return value.get(nested) if separator and isinstance(value, dict) else value
