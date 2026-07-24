from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "packages/ethos/src/ethos/adapters/repo/source_budget/snapshots.py"


def _snapshot_ast() -> ast.Module:
    return ast.parse(SNAPSHOTS.read_text(encoding="utf-8"))


def test_snapshot_adapter_uses_git_objects_without_private_measurement_imports() -> None:
    tree = _snapshot_ast()
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }

    assert "_measure_carrier_content" not in imports
    assert "_read_carrier" not in imports


def test_snapshot_adapter_git_commands_are_read_only_and_statically_bounded() -> None:
    tree = _snapshot_ast()
    run_git_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_run_git"
    ]

    assert run_git_calls
    assert all(
        len(call.args) >= 2
        and isinstance(call.args[1], ast.Constant)
        and isinstance(call.args[1].value, str)
        for call in run_git_calls
    )
    command_names = {cast_arg.value for call in run_git_calls for cast_arg in [call.args[1]]}
    assert command_names == {"cat-file", "ls-tree", "rev-parse", "status"}


def test_snapshot_adapter_has_one_subprocess_boundary_owned_by_run_git() -> None:
    tree = _snapshot_ast()
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    run_git = functions["_run_git"]
    subprocess_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]

    assert len(subprocess_calls) == 1
    assert subprocess_calls[0] in tuple(ast.walk(run_git))
