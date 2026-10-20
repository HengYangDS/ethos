"""Select shared native tool policy without competing legacy directory owners."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ethos.contracts.paradigm.declaration import load_repository_paradigm

if TYPE_CHECKING:
    from ethos.contracts.gates import Gate

NATIVE_TOOL_LOCATIONS = {tool.id: tool.carrier for tool in load_repository_paradigm().tool}
_PROVIDER_TOOLS = {
    "ethos.adapters.gates.formatting:source_format_report": (
        "prettier",
        "prettier-ignore",
        "taplo",
        "ruff",
    ),
    "ethos.adapters.gates.tool:markdown_lint_report": (
        "prettier",
        "prettier-ignore",
        "markdownlint-cli2",
    ),
    "ethos.adapters.gates.tool:markdown_links_report": ("lychee",),
    "ethos.adapters.gates.tool:external_links_report": ("lychee",),
    "ethos.adapters.gates.tool:prose_report": ("codespell",),
    "ethos.adapters.gates.configuration:configuration_report": (
        "taplo",
        "prettier",
        "prettier-ignore",
        "yamllint",
    ),
}


def native_gate_tools(gate: Gate) -> tuple[str, ...]:
    """Select the native policy owners invoked by this gate's providers."""
    return tuple(
        dict.fromkeys(
            tool
            for reference in (*gate.providers, *gate.verification_providers)
            for tool in _PROVIDER_TOOLS.get(reference, ())
        )
    )


def native_tool_configuration(repository_paths: tuple[str, ...], tool: str) -> str | None:
    """Resolve the shared native configuration shape, refusing competing legacy owners."""
    location, selected = _configuration_carriers(repository_paths, tool)
    if len(selected) > 1:
        message = f"native_tool_configuration_ambiguous:{tool}"
        raise ValueError(message)
    if selected and selected[0] != location:
        message = f"native_tool_configuration_location_invalid:{tool}"
        raise ValueError(message)
    return selected[0] if selected else None


def native_tool_configurations(repository_paths: tuple[str, ...], tool: str) -> tuple[str, ...]:
    """Observe every exact carrier without asserting its current placement validity."""
    return _configuration_carriers(repository_paths, tool)[1]


def _configuration_carriers(
    repository_paths: tuple[str, ...], tool: str
) -> tuple[str | None, tuple[str, ...]]:
    """Select carrier identities once for strict admission and historical observation."""
    location = NATIVE_TOOL_LOCATIONS.get(tool)
    declaration = next((item for item in load_repository_paradigm().tool if item.id == tool), None)
    names = set(declaration.root_names) if declaration is not None else set()
    if location:
        names.add(Path(location).name)
    selected = tuple(path for path in repository_paths if Path(path).name in names)
    if location in repository_paths and location not in selected:
        selected = (*selected, location)
    return location, selected
