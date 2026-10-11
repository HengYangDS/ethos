"""Select shared native tool policy without competing legacy directory owners."""

from __future__ import annotations

from pathlib import Path


def native_tool_configuration(repository_paths: tuple[str, ...], tool: str) -> str | None:
    """Resolve the shared native configuration shape, refusing competing legacy owners."""
    locations = {
        "lychee": ".config/checks/links/lychee.toml",
        "markdownlint-cli2": ".config/checks/markdown/markdownlint.yaml",
        "prettier": ".config/checks/format/prettier.toml",
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
    }
    selected = tuple(path for path in repository_paths if Path(path).name in names.get(tool, set()))
    if len(selected) > 1:
        message = f"native_tool_configuration_ambiguous:{tool}"
        raise ValueError(message)
    if selected and selected[0] != location:
        message = f"native_tool_configuration_location_invalid:{tool}"
        raise ValueError(message)
    return selected[0] if selected else None
