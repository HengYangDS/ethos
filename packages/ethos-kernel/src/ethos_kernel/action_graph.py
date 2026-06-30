from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


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

    def ordered_nodes(self) -> tuple[ActionNode, ...]:
        return tuple(sorted(self.nodes, key=lambda node: node.id))

    def to_dict(self) -> dict[str, Any]:
        nodes = [node.to_dict() for node in self.ordered_nodes()]
        return {
            "schema_version": 1,
            "nodes": nodes,
            "digest": self.digest(),
        }

    def digest(self) -> str:
        nodes = [node.normalized() for node in self.ordered_nodes()]
        return hashlib.sha256(_stable_json({"nodes": nodes}).encode("utf-8")).hexdigest()
