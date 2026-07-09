from __future__ import annotations

import inspect

from ethos_core.action_graph.core import ActionGraph
from ethos_core.action_graph.core import ActionNode
from ethos_core.graph.core import GraphKernel
from ethos_core.graph.core import GraphNode


def test_graph_kernel_orders_nodes_with_graphlib() -> None:
    kernel = GraphKernel(
        nodes=(
            GraphNode(id="publish", depends_on=("prove",)),
            GraphNode(id="status"),
            GraphNode(id="prove", depends_on=("status",)),
        )
    )

    validation = kernel.validate()

    assert validation.ok
    assert validation.gaps == ()
    assert kernel.ordered_ids() == ("status", "prove", "publish")


def test_graph_kernel_reports_cycle_with_node_path() -> None:
    kernel = GraphKernel(
        nodes=(
            GraphNode(id="a", depends_on=("b",)),
            GraphNode(id="b", depends_on=("a",)),
        )
    )

    validation = kernel.validate()

    assert not validation.ok
    assert validation.gaps == ("cycle_detected",)


def test_action_graph_delegates_ordering_to_shared_graph_kernel() -> None:
    graph = ActionGraph(
        nodes=(
            ActionNode(
                id="publish", kind="release", command=("ethos", "publish"), depends_on=("prove",)
            ),
            ActionNode(id="status", kind="inspect", command=("ethos", "status")),
            ActionNode(
                id="prove", kind="proof", command=("ethos", "prove"), depends_on=("status",)
            ),
        )
    )

    assert [node.id for node in graph.topological_nodes()] == ["status", "prove", "publish"]
    source = inspect.getsource(ActionGraph._kernel)
    assert "GraphKernel" in source
