from __future__ import annotations

import sys
from dataclasses import dataclass

from ethos_kernel.action_graph import ActionGraph, ActionNode


@dataclass(frozen=True)
class Gate:
    id: str
    kind: str
    command: tuple[str, ...]
    policy: str = "required"
    depends_on: tuple[str, ...] = ()

    def to_node(self) -> ActionNode:
        return ActionNode(
            id=self.id,
            kind=self.kind,
            command=self.command,
            policy=self.policy,
            tool="ethos",
            depends_on=self.depends_on,
        )


def gate_registry() -> dict[str, Gate]:
    python = sys.executable
    return {
        "self-audit": Gate(
            id="self-audit",
            kind="governance",
            command=(python, "-m", "ethos.cli", "self", "audit", "--mode", "shape", "--json"),
        ),
        "claims": Gate(
            id="claims",
            kind="governance",
            command=(python, "-m", "ethos.cli", "quality", "claims", "--json"),
        ),
        "docs-registry": Gate(
            id="docs-registry",
            kind="docs",
            command=(python, "-m", "ethos.cli", "quality", "docs-registry", "--json"),
        ),
        "schemas": Gate(
            id="schemas",
            kind="schema",
            command=(python, "-m", "ethos.cli", "quality", "schemas", "--json"),
        ),
        "openspec": Gate(
            id="openspec",
            kind="governance",
            command=("openspec", "validate", "--all", "--strict", "--json"),
            depends_on=("schemas",),
        ),
        "unit-architecture": Gate(
            id="unit-architecture",
            kind="test",
            command=(
                "uv",
                "run",
                "--group",
                "dev",
                "pytest",
                "tests/unit",
                "tests/architecture",
                "-q",
            ),
        ),
        "ruff": Gate(
            id="ruff",
            kind="lint",
            command=("uv", "run", "--group", "dev", "ruff", "check", "."),
        ),
        "build": Gate(
            id="build",
            kind="package",
            command=("uv", "build", "--all-packages"),
            depends_on=("unit-architecture", "ruff"),
        ),
    }


def default_gate_ids(*, full: bool = False) -> tuple[str, ...]:
    if full:
        return (
            "self-audit",
            "claims",
            "docs-registry",
            "schemas",
            "openspec",
            "unit-architecture",
            "ruff",
            "build",
        )
    return ("self-audit", "claims", "docs-registry", "schemas")


def gate_graph(gate_ids: tuple[str, ...] = (), *, full: bool = False) -> ActionGraph:
    registry = gate_registry()
    selected = gate_ids or default_gate_ids(full=full)
    nodes = []
    for gate_id in selected:
        gate = registry[gate_id]
        nodes.append(gate.to_node())
    return ActionGraph(nodes=tuple(nodes))
