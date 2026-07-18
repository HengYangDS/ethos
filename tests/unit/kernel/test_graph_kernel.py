from __future__ import annotations

import inspect

from ethos_core.action_graph.core import ActionGraph
from ethos_core.action_graph.core import ActionNode
from ethos_core.graph.core import GraphEdge
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


def test_graph_kernel_preserves_declaration_order_for_independent_nodes() -> None:
    kernel = GraphKernel(
        nodes=(
            GraphNode(id="status"),
            GraphNode(id="handoff"),
            GraphNode(id="plan", depends_on=("status",)),
        )
    )

    assert kernel.ordered_ids() == ("status", "handoff", "plan")


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


def test_action_graph_delegates_ordering_to_shared_graph_plan() -> None:
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

    assert [node.id for node in graph.ordered_nodes()] == ["status", "prove", "publish"]
    source = inspect.getsource(ActionGraph)
    assert "GraphKernel" in source
    assert ".plan()" in source


def test_graph_kernel_emits_declarative_plan_with_edges_and_validation() -> None:
    kernel = GraphKernel(
        nodes=(
            GraphNode(id="publish", depends_on=("prove",)),
            GraphNode(id="status"),
            GraphNode(id="prove", depends_on=("status",)),
        )
    )

    plan = kernel.plan()

    assert plan.ok
    assert plan.ordered_ids == ("status", "prove", "publish")
    assert plan.edges == (
        GraphEdge(source="status", target="prove", relation="depends_on"),
        GraphEdge(source="prove", target="publish", relation="depends_on"),
    )
    assert plan.to_dict() == {
        "ok": True,
        "ordered_ids": ["status", "prove", "publish"],
        "edges": [
            {"source": "status", "target": "prove", "relation": "depends_on"},
            {"source": "prove", "target": "publish", "relation": "depends_on"},
        ],
        "gaps": [],
    }


def test_graph_kernel_plan_keeps_invalid_graph_stable_without_recursing() -> None:
    kernel = GraphKernel(
        nodes=(
            GraphNode(id="prove", depends_on=("status",)),
            GraphNode(id="prove", depends_on=("audit",)),
        )
    )

    plan = kernel.plan()

    assert not plan.ok
    assert plan.ordered_ids == ("prove", "prove")
    assert "duplicate_node_id:prove" in plan.gaps
    assert "missing_dependency:prove->audit" in plan.gaps
    assert "missing_dependency:prove->status" in plan.gaps
    assert plan.to_dict()["edges"] == [
        {"source": "status", "target": "prove", "relation": "depends_on"},
        {"source": "audit", "target": "prove", "relation": "depends_on"},
    ]


def test_graph_kernel_edges_method_returns_declared_plan_edges() -> None:
    kernel = GraphKernel(
        nodes=(
            GraphNode(id="plan", depends_on=("status",)),
            GraphNode(id="status"),
        )
    )

    assert kernel.edges() == (GraphEdge(source="status", target="plan", relation="depends_on"),)
