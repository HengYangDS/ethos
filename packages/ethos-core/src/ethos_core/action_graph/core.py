from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class GraphValidation:
    ok: bool
    gaps: tuple[str, ...] = ()


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ActionNode:
    id: str
    kind: str
    command: tuple[str, ...]
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    policy: str = "required"
    tool: str = "ethos"
    tool_version: str = "0.1.0"
    env: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "command": list(self.command),
            "inputs": sorted(self.inputs),
            "outputs": sorted(self.outputs),
            "policy": self.policy,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "env": sorted(self.env),
            "depends_on": sorted(self.depends_on),
            "metadata": self.metadata,
        }

    def cache_key(self) -> str:
        return hashlib.sha256(_stable_json(self.normalized()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = self.normalized()
        payload["cache_key"] = self.cache_key()
        return payload


@dataclass(frozen=True)
class ActionGraph:
    nodes: tuple[ActionNode, ...]

    def validate(self) -> GraphValidation:
        seen: set[str] = set()
        duplicate_ids: set[str] = set()
        for node in self.nodes:
            if node.id in seen:
                duplicate_ids.add(node.id)
            seen.add(node.id)
        ids = {node.id for node in self.nodes}
        gaps: list[str] = []
        gaps.extend(f"duplicate_node_id:{node_id}" for node_id in sorted(duplicate_ids))
        for node in self.nodes:
            for dependency in node.depends_on:
                if dependency not in ids:
                    gaps.append(f"missing_dependency:{node.id}->{dependency}")
        if not gaps and self._has_cycle():
            gaps.append("cycle_detected")
        return GraphValidation(ok=not gaps, gaps=tuple(gaps))

    def _has_cycle(self) -> bool:
        dependencies = {node.id: set(node.depends_on) for node in self.nodes}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for dependency in dependencies[node_id]:
                if dependency in dependencies and visit(dependency):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node.id) for node in self.nodes)

    def topological_nodes(self) -> tuple[ActionNode, ...]:
        validation = self.validate()
        if not validation.ok:
            return self._stable_nodes()
        by_id = {node.id: node for node in self.nodes}
        remaining = {node.id: set(node.depends_on) for node in self.nodes}
        ordered: list[ActionNode] = []
        # validate() above rejects cycles, so a validated graph is acyclic and Kahn's
        # algorithm always finds a ready node until `remaining` is exhausted.
        while remaining:
            ready = sorted(node_id for node_id, deps in remaining.items() if not deps)
            for node_id in ready:
                ordered.append(by_id[node_id])
                remaining.pop(node_id)
                for deps in remaining.values():
                    deps.discard(node_id)
        return tuple(ordered)

    def _stable_nodes(self) -> tuple[ActionNode, ...]:
        return tuple(sorted(self.nodes, key=lambda node: node.id))

    def ordered_nodes(self) -> tuple[ActionNode, ...]:
        return self.topological_nodes()

    def to_dict(self) -> dict[str, Any]:
        validation = self.validate()
        nodes = [node.to_dict() for node in self.ordered_nodes()]
        return {
            "schema_version": 1,
            "nodes": nodes,
            "validation": {"ok": validation.ok, "gaps": list(validation.gaps)},
            "digest": self.digest(),
        }

    def digest(self) -> str:
        nodes = [node.normalized() for node in self.ordered_nodes()]
        return hashlib.sha256(_stable_json({"nodes": nodes}).encode("utf-8")).hexdigest()
