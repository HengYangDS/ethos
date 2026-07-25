from __future__ import annotations

from ethos.contracts.plan import PlanIR
from ethos.contracts.plan import PlanNode


def test_plan_ir_orders_dependencies_before_dependents() -> None:
    plan = PlanIR(
        nodes=(
            PlanNode(
                id="publish",
                kind="effect",
                command=("ethos", "publish"),
                depends_on=("prove",),
            ),
            PlanNode(id="status", kind="check", command=("ethos", "status")),
            PlanNode(
                id="prove",
                kind="decision",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    assert [node.id for node in plan.ordered_nodes()] == ["status", "prove", "publish"]
    assert plan.to_dict()["nodes"][0]["id"] == "status"


def test_plan_ir_rejects_missing_dependency() -> None:
    plan = PlanIR(
        nodes=(
            PlanNode(
                id="prove",
                kind="decision",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    assert plan.ok is False
    assert "missing_dependency:prove->status" in plan.gaps()


def test_plan_ir_rejects_cycle() -> None:
    plan = PlanIR(
        nodes=(
            PlanNode(id="a", kind="check", command=("a",), depends_on=("b",)),
            PlanNode(id="b", kind="check", command=("b",), depends_on=("a",)),
        )
    )

    assert plan.ok is False
    assert "cycle_detected" in plan.gaps()


def test_plan_ir_rejects_duplicate_node_id() -> None:
    plan = PlanIR(
        nodes=(
            PlanNode(id="prove", kind="check", command=("ethos", "prove")),
            PlanNode(id="prove", kind="check", command=("ethos", "prove", "--json")),
        )
    )

    assert plan.ok is False
    assert "duplicate_node_id:prove" in plan.gaps()


def test_invalid_plan_ir_still_serializes_without_recursion() -> None:
    plan = PlanIR(
        nodes=(
            PlanNode(
                id="prove",
                kind="decision",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    payload = plan.to_dict()

    assert payload["nodes"][0]["id"] == "prove"
    assert payload["validation"]["ok"] is False
