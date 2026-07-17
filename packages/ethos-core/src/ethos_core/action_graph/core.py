from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ethos_core.graph.core import GraphKernel
from ethos_core.graph.core import GraphNode
from ethos_core.graph.core import GraphPlan
from ethos_core.graph.core import GraphValidation


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class ActionGraph:
    nodes: tuple[ActionNode, ...]
    validation_issues: tuple[str, ...] = ()

    def validate(self) -> GraphValidation:
        plan = self.plan()
        return GraphValidation(ok=plan.ok, gaps=plan.gaps)

    def plan(self) -> GraphPlan:
        graph_plan = self._kernel().plan()
        gaps = tuple(dict.fromkeys((*self.validation_issues, *graph_plan.gaps)))
        return GraphPlan(
            ok=not gaps,
            ordered_ids=graph_plan.ordered_ids,
            edges=graph_plan.edges,
            gaps=gaps,
        )

    def ordered_nodes(self) -> tuple[ActionNode, ...]:
        ordered_ids = self.plan().ordered_ids
        by_id = {node.id: node for node in self.nodes}
        return tuple(by_id[node_id] for node_id in ordered_ids if node_id in by_id)

    def _kernel(self) -> GraphKernel:
        return GraphKernel(
            nodes=tuple(
                GraphNode(id=node.id, depends_on=node.depends_on)
                for node in sorted(self.nodes, key=lambda item: item.id)
            )
        )

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
        payload: dict[str, Any] = {"nodes": nodes}
        if self.validation_issues:
            payload["validation_issues"] = list(self.validation_issues)
        return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()
