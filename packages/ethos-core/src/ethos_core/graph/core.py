from __future__ import annotations

from dataclasses import dataclass
from graphlib import CycleError
from graphlib import TopologicalSorter


@dataclass(frozen=True)
class GraphValidation:
    ok: bool
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphNode:
    id: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
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

    def ordered_ids(self) -> tuple[str, ...]:
        validation = self.validate()
        if not validation.ok:
            return self.stable_ids()
        return tuple(self._sorter().static_order())

    def stable_ids(self) -> tuple[str, ...]:
        return tuple(sorted(node.id for node in self.nodes))

    def _sorter(self) -> TopologicalSorter[str]:
        sorter: TopologicalSorter[str] = TopologicalSorter()
        for node in sorted(self.nodes, key=lambda item: item.id):
            sorter.add(node.id, *sorted(node.depends_on))
        return sorter
