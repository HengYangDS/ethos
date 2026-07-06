from __future__ import annotations

import shlex
from typing import Any


def _command_capability_gaps(
    record: dict[str, Any],
    package_report: dict[str, Any],
) -> list[str]:
    skill_id = str(record["id"] or "<missing>")
    capability_commands = [
        _command_key(item["command"])
        for item in package_report["capabilities"]
        if item.get("command")
    ]
    gaps: list[str] = []
    for command in record["commands"]:
        command_key = _command_key(_split_command(command))
        if not any(_command_covers(capability, command_key) for capability in capability_commands):
            gaps.append(f"skill_package_capability_missing_command:{skill_id}:{command}")
    return gaps


def _split_command(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _command_key(command: list[str]) -> tuple[str, ...]:
    return tuple(part for part in command if part != "--json")


def _command_covers(capability: tuple[str, ...], command: tuple[str, ...]) -> bool:
    return capability[: len(command)] == command
