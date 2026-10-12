"""Select shared native tool policy without competing legacy directory owners."""

from __future__ import annotations

from pathlib import Path


def native_tool_configuration(repository_paths: tuple[str, ...], tool: str) -> str | None:
    """Resolve the shared native configuration shape, refusing competing legacy owners."""
    locations = {
        "lychee": ".config/checks/links/lychee.toml",
        "markdownlint-cli2": ".config/checks/markdown/markdownlint.yaml",
        "prettier": ".config/checks/format/prettier.toml",
        "codespell": ".config/checks/prose/codespell.toml",
        "taplo": ".config/checks/taplo/taplo.toml",
        "yamllint": ".config/checks/yaml/yamllint.yaml",
    }
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
    }
    selected = tuple(path for path in repository_paths if Path(path).name in names.get(tool, set()))
    if location in repository_paths and location not in selected:
        selected = (*selected, location)
    if len(selected) > 1:
        message = f"native_tool_configuration_ambiguous:{tool}"
        raise ValueError(message)
    if selected and selected[0] != location:
        message = f"native_tool_configuration_location_invalid:{tool}"
        raise ValueError(message)
    return selected[0] if selected else None
