"""Select shared native tool policy without competing legacy directory owners."""

from __future__ import annotations

from pathlib import Path

from ethos.contracts.paradigm.declaration import load_repository_paradigm

NATIVE_TOOL_LOCATIONS = {tool.id: tool.carrier for tool in load_repository_paradigm().tool}
_NESTED_TOOLS = frozenset(tool.id for tool in load_repository_paradigm().tool if tool.nested)


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
    """Select the carrier a tool reads at its location, a nested owner's tree included.

    A misplaced or competing carrier is never read, so it binds nothing; admission reports it.
    """
    location = NATIVE_TOOL_LOCATIONS.get(tool)
    tree = f"{Path(location).parent.as_posix()}/" if location and tool in _NESTED_TOOLS else None
    selected = (location,) if location and location in repository_paths else ()
    nested = (path for path in repository_paths if tree and path.startswith(tree))
    return tuple(dict.fromkeys((*selected, *nested)))


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
