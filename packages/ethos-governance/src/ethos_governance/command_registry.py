from __future__ import annotations

PUBLIC_COMMANDS = (
    "ethos status",
    "ethos plan",
    "ethos prove",
    "ethos land",
    "ethos publish",
    "ethos init",
    "ethos adopt",
    "ethos doctor",
    "ethos campaign",
    "ethos self",
    "ethos quality",
    "ethos report",
    "ethos explain",
    "ethos docs",
)

RETIRED_PUBLIC_ROOTS = (
    "wt",
    "proof",
    "mission",
    "skill-evolution",
    "agent-surface-contract",
)


def public_commands() -> tuple[str, ...]:
    return PUBLIC_COMMANDS


def command_registry_report() -> dict[str, object]:
    leaked = [
        command
        for command in PUBLIC_COMMANDS
        if command.split(" ", 1)[0] in RETIRED_PUBLIC_ROOTS
    ]
    return {
        "ok": not leaked,
        "public_commands": list(PUBLIC_COMMANDS),
        "retired_public_roots": leaked,
        "retired_roots_policy": list(RETIRED_PUBLIC_ROOTS),
    }
