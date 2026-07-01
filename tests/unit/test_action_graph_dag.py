from __future__ import annotations

from ethos_core.action_graph import ActionGraph, ActionNode


def test_action_graph_orders_dependencies_before_dependents() -> None:
    graph = ActionGraph(
        nodes=(
            ActionNode(
                id="publish",
                kind="release",
                command=("ethos", "publish"),
                depends_on=("prove",),
            ),
            ActionNode(id="status", kind="inspect", command=("ethos", "status")),
            ActionNode(
                id="prove",
                kind="proof",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    assert [node.id for node in graph.topological_nodes()] == ["status", "prove", "publish"]
    assert graph.to_dict()["nodes"][0]["id"] == "status"


def test_action_graph_rejects_missing_dependency() -> None:
    graph = ActionGraph(
        nodes=(
            ActionNode(
                id="prove",
                kind="proof",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    result = graph.validate()

    assert result.ok is False
    assert "missing_dependency:prove->status" in result.gaps


def test_action_graph_rejects_cycle() -> None:
    graph = ActionGraph(
        nodes=(
            ActionNode(id="a", kind="proof", command=("a",), depends_on=("b",)),
            ActionNode(id="b", kind="proof", command=("b",), depends_on=("a",)),
        )
    )

    result = graph.validate()

    assert result.ok is False
    assert "cycle_detected" in result.gaps


def test_action_graph_rejects_duplicate_node_id() -> None:
    graph = ActionGraph(
        nodes=(
            ActionNode(id="prove", kind="proof", command=("ethos", "prove")),
            ActionNode(id="prove", kind="proof", command=("ethos", "prove", "--json")),
        )
    )

    result = graph.validate()

    assert result.ok is False
    assert "duplicate_node_id:prove" in result.gaps


def test_invalid_action_graph_still_serializes_without_recursion() -> None:
    graph = ActionGraph(
        nodes=(
            ActionNode(
                id="prove",
                kind="proof",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    payload = graph.to_dict()

    assert payload["nodes"][0]["id"] == "prove"
    assert payload["validation"]["ok"] is False
