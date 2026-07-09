from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_action_graph_does_not_reintroduce_custom_dag_traversal() -> None:
    source = (ROOT / "packages/ethos-core/src/ethos_core/action_graph/core.py").read_text(
        encoding="utf-8"
    )

    forbidden_tokens = (
        "visiting",
        "visited",
        "remaining =",
        "while remaining",
        "ready =",
        "def visit(",
    )
    for token in forbidden_tokens:
        assert token not in source
    assert "GraphKernel" in source


def test_shared_graph_kernel_uses_standard_graphlib() -> None:
    source = (ROOT / "packages/ethos-core/src/ethos_core/graph/core.py").read_text(encoding="utf-8")

    assert "from graphlib import" in source
    assert "TopologicalSorter" in source
