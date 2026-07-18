from __future__ import annotations

from dataclasses import dataclass
from graphlib import CycleError
from graphlib import TopologicalSorter


@dataclass(frozen=True, slots=True)
class GraphValidation:
    ok: bool
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: str
    target: str
    relation: str = "depends_on"

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
        }


@dataclass(frozen=True, slots=True)
class GraphPlan:
    ok: bool
    ordered_ids: tuple[str, ...]
    edges: tuple[GraphEdge, ...]
    gaps: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "ordered_ids": list(self.ordered_ids),
            "edges": [edge.to_dict() for edge in self.edges],
            "gaps": list(self.gaps),
        }


@dataclass(frozen=True, slots=True)
class GraphKernel:
    nodes: tuple[GraphNode, ...]

    def validate(self) -> GraphValidation:
        seen: set[str] = set()
        duplicate_ids: set[str] = set()
        for node in self.nodes:
            if node.id in seen:
                duplicate_ids.add(node.id)
            seen.add(node.id)

        ids = {node.id for node in self.nodes}
        gaps: list[str] = [f"duplicate_node_id:{node_id}" for node_id in sorted(duplicate_ids)]
        for node in self.nodes:
            for dependency in node.depends_on:
                if dependency not in ids:
                    gaps.append(f"missing_dependency:{node.id}->{dependency}")

        if not gaps:
            try:
                tuple(self._sorter().static_order())
            except CycleError:
                gaps.append("cycle_detected")
        return GraphValidation(ok=not gaps, gaps=tuple(gaps))

    def plan(self) -> GraphPlan:
        validation = self.validate()
        ordered_ids = self.ordered_ids_for(validation)
        return GraphPlan(
            ok=validation.ok,
            ordered_ids=ordered_ids,
            edges=self.edges_for(ordered_ids, valid=validation.ok),
            gaps=validation.gaps,
        )

    def ordered_ids(self) -> tuple[str, ...]:
        return self.plan().ordered_ids

    def ordered_ids_for(self, validation: GraphValidation) -> tuple[str, ...]:
        if not validation.ok:
            return self.stable_ids()
        return self._ordered_ids_by_declaration()

    def stable_ids(self) -> tuple[str, ...]:
        return tuple(sorted(node.id for node in self.nodes))

    def _ordered_ids_by_declaration(self) -> tuple[str, ...]:
        sorter = self._sorter()
        order = {node.id: index for index, node in enumerate(self.nodes)}
        ordered: list[str] = []
        sorter.prepare()
        while sorter.is_active():
            ready = sorted(sorter.get_ready(), key=lambda node_id: order[node_id])
            ordered.extend(ready)
            sorter.done(*ready)
        return tuple(ordered)

    def edges(self) -> tuple[GraphEdge, ...]:
        return self.plan().edges

    def edges_for(self, ordered_ids: tuple[str, ...], *, valid: bool) -> tuple[GraphEdge, ...]:
        if not valid:
            return self.declared_edges()
        by_id = {node.id: node for node in self.nodes}
        return tuple(
            GraphEdge(source=dependency, target=node_id)
            for node_id in ordered_ids
            for dependency in by_id.get(node_id, GraphNode(id=node_id)).depends_on
        )

    def declared_edges(self) -> tuple[GraphEdge, ...]:
        return tuple(
            GraphEdge(source=dependency, target=node.id)
            for node in self.nodes
            for dependency in node.depends_on
        )

    def _sorter(self) -> TopologicalSorter[str]:
        sorter: TopologicalSorter[str] = TopologicalSorter()
        for node in self.nodes:
            sorter.add(node.id, *sorted(node.depends_on))
        return sorter
