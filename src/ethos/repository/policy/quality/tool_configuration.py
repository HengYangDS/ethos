"""Select shared native tool policy without competing legacy directory owners."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ethos.contracts.paradigm.declaration import load_repository_paradigm

if TYPE_CHECKING:
    from ethos.contracts.gates import Gate


def native_gate_tools(gate: Gate) -> tuple[str, ...]:
    """Select the native policy owners invoked by this gate's providers."""
    providers = {
        "ethos.adapters.gates.markdown:markdown_format_report": ("prettier", "markdownlint-cli2"),
        "ethos.adapters.gates.tool:markdown_links_report": ("lychee",),
        "ethos.adapters.gates.tool:external_links_report": ("lychee",),
        "ethos.adapters.gates.tool:prose_report": ("codespell",),
        "ethos.adapters.gates.configuration:configuration_report": (
            "taplo",
            "prettier",
            "yamllint",
            "python-stdlib-json",
            "format-selection",
        ),
    }
    return tuple(
        dict.fromkeys(
            tool
            for reference in (*gate.providers, *gate.verification_providers)
            for tool in providers.get(reference, ())
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
    locations = {item.id: item.carrier for item in load_repository_paradigm().tool}
    locations.update(
        {
            "python-stdlib-json": ".config/checks/config-quality/policy.toml",
            "format-selection": ".config/checks/format-selection/policy.toml",
        }
    )
    location = locations.get(tool)
    names = {
        "lychee": {"lychee.toml"},
        "markdownlint-cli2": {
            "markdownlint.toml",
            "markdownlint.yaml",
            ".markdownlint-cli2.yaml",
            ".markdownlint-cli2.jsonc",
        },
        "prettier": {"prettier.toml", ".prettierrc.toml", ".prettierrc.json", ".prettierrc.yaml"},
        "codespell": {"codespell.toml", ".codespellrc"},
        "taplo": {"taplo.toml", ".taplo.toml"},
        "yamllint": {"yamllint.yaml", ".yamllint", ".yamllint.yaml", ".yamllint.yml"},
        "python-stdlib-json": {"format.toml"},
        "format-selection": {"selection.toml"},
    }
    identity = Path(location).parts[-2:] if location else ()
    selected = tuple(
        path
        for path in repository_paths
        if Path(path).name in names.get(tool, set()) or Path(path).parts[-2:] == identity
    )
    if location in repository_paths and location not in selected:
        selected = (*selected, location)
    return location, selected
