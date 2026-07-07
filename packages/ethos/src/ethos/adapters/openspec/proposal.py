"""Extracted from openspec.py."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
from typing import Any

VALID_REUSE_STANCES = {"reuse", "extend", "extract", "new"}
VALID_CHANGE_DIRECTIONS = {"add", "modify", "remove", "rename", "retire"}


REQUIRED_PROPOSAL_METADATA = (
    "subject",
    "reuse",
    "change",
    "facet:lifecycle",
    "facet:surface",
    "facet:authority",
)


def proposal_protocol_report(root: Path, change_name: str) -> dict[str, Any]:
    """Report the proposal-protocol conformance for an OpenSpec change."""
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
    capabilities = _proposal_capability_entries(text)
    if not capabilities:
        gaps.append(f"openspec_proposal_capabilities_missing:{change_name}")
    for entry in capabilities:
        capability = entry["capability"]
        metadata = entry["metadata"]
        if not (root / "openspec" / "specs" / capability / "spec.md").exists():
            gaps.append(f"openspec_proposal_capability_unknown:{change_name}:{capability}")
        profile_gaps = _capability_profile_gaps(root, change_name, capability)
        gaps.extend(profile_gaps)
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


def _proposal_capability_entries(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and "`:" in stripped:
            if current:
                entries.append(_proposal_capability_entry(current["capability"], current["raw"]))
            capability = stripped.split("`", 2)[1]
            current = {"capability": capability, "raw": stripped.split("`:", 1)[1]}
            continue
        if current and line[:1].isspace() and not stripped.startswith("- `"):
            current["raw"] = f"{current['raw']} {stripped}"
            continue
        if current and stripped.startswith("- "):
            entries.append(_proposal_capability_entry(current["capability"], current["raw"]))
            current = None
    if current:
        entries.append(_proposal_capability_entry(current["capability"], current["raw"]))
    return entries


def _proposal_capability_entry(capability: str, raw: str) -> dict[str, Any]:
    metadata: dict[str, str] = {}
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        metadata[key.strip()] = value.strip().strip("`")
    return {"capability": capability, "metadata": metadata}


def _capability_profile_gaps(root: Path, change_name: str, capability: str) -> list[str]:
    profile_path = root / "openspec" / "specs" / capability / "capability.toml"
    if not profile_path.exists():
        return [f"openspec_capability_profile_missing:{change_name}:{capability}"]
    try:
        payload = tomllib.loads(profile_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return [f"openspec_capability_profile_invalid:{change_name}:{capability}"]
    gaps: list[str] = []
    for field in ("family", "primary_invariant", "routing_question"):
        if not payload.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:{field}"
            )
    for field in ("decision_axes", "recommended_facets"):
        if not payload.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:{field}"
            )
    if not payload.get("boundary_rules"):
        gaps.append(
            f"openspec_capability_profile_field_missing:{change_name}:{capability}:boundary_rules"
        )
    owner = payload.get("owner", {})
    for field in ("package", "scope"):
        if not owner.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:owner.{field}"
            )
    proof = payload.get("proof_profile", {})
    for field in ("default_command", "executed_command", "required_gates"):
        if not proof.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:proof_profile.{field}"
            )
    return gaps
