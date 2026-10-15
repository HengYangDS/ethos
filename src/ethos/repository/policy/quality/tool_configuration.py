"""Select shared native tool policy without competing legacy directory owners."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ethos.contracts.gates import Gate

NATIVE_TOOL_LOCATIONS = {
    "ruff": ".config/checks/ruff/ruff.toml",
    "gitleaks": ".config/checks/gitleaks/gitleaks.toml",
    "gitleaks-ignore": ".config/checks/gitleaks/gitleaksignore",
    "lychee": ".config/checks/links/lychee.toml",
    "markdownlint-cli2": ".config/checks/markdown/markdownlint.yaml",
    "prettier": ".config/checks/format/prettier.toml",
    "codespell": ".config/checks/prose/codespell.toml",
    "taplo": ".config/checks/taplo/taplo.toml",
    "yamllint": ".config/checks/yaml/yamllint.yaml",
}


def native_gate_tools(gate: Gate) -> tuple[str, ...]:
    """Select the native policy owners invoked by this gate's providers."""
    return tuple(
        dict.fromkeys(
            tool
            for reference in (*gate.providers, *gate.verification_providers)
            for tool in (
                ("prettier", "taplo", "ruff")
                if reference == "ethos.adapters.gates.formatting:source_format_report"
                else ("prettier", "markdownlint-cli2")
                if reference == "ethos.adapters.gates.tool:markdown_lint_report"
                else ("lychee",)
                if reference
                in (
                    "ethos.adapters.gates.tool:markdown_links_report",
                    "ethos.adapters.gates.tool:external_links_report",
                )
                else ()
            )
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
    names = {
        "ruff": {"ruff.toml", ".ruff.toml"},
        "gitleaks": {"gitleaks.toml", ".gitleaks.toml"},
        "gitleaks-ignore": {"gitleaksignore", ".gitleaksignore"},
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
    }
    selected = tuple(path for path in repository_paths if Path(path).name in names.get(tool, set()))
    if location in repository_paths and location not in selected:
        selected = (*selected, location)
    return location, selected
