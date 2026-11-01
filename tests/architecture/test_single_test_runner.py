"""ETHOS proves its Python suite only through the behavior probe it ships (V1)."""

from __future__ import annotations

import ast
import inspect
import itertools
from importlib import import_module
from pathlib import Path

import pytest

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from tools.ci import sessions

ROOT = Path(__file__).resolve().parents[2]
_PROBE = "ethos.adapters.gates.python_quality:behavior_report"


def _starts_pytest(values: list[object]) -> bool:
    """Whether an argument sequence passes the consecutive arguments `-m pytest`."""
    return any(item == "-m" and after == "pytest" for item, after in itertools.pairwise(values))


def _builds_pytest(node: ast.AST) -> bool:
    """Whether a parsed body builds a call or sequence with the arguments `-m pytest`."""
    return any(
        _starts_pytest([item.value if isinstance(item, ast.Constant) else None for item in items])
        for child in ast.walk(node)
        for items in (child.args if isinstance(child, ast.Call) else getattr(child, "elts", ()),)
    )


def _session_starts_pytest(name: str) -> bool:
    """Whether a Nox session reaches, by name, a function that builds a pytest argv.

    The search follows every name and attribute from the session into the functions of
    `tools.ci.sessions` and the modules the session imports by name.
    """
    body = ast.parse(
        inspect.getsource(
            sessions.SESSION_IMPLEMENTATIONS.get(name, None) or getattr(sessions, name)
        )
    )
    modules = {
        node.args[0].value
        for node in ast.walk(body)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "import_module"
        and isinstance(node.args[0], ast.Constant)
    }
    functions: dict[str, list[ast.AST]] = {}
    for module in (sessions, *(import_module(str(item)) for item in modules)):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node, ast.FunctionDef):
                functions.setdefault(node.name, []).append(node)
    pending: list[ast.AST] = [body]
    seen: set[str | None] = set()
    while pending:
        node = pending.pop()
        if _builds_pytest(node):
            return True
        names = {
            getattr(child, "attr", None) or getattr(child, "id", None) for child in ast.walk(node)
        }
        pending.extend(f for reference in names - seen for f in functions.get(str(reference), ()))
        seen |= names
    return False


@pytest.mark.parametrize("full", [False, True], ids=["default", "full"])
def test_the_proof_runs_python_tests_only_through_the_shipped_probe(*, full: bool) -> None:
    """One selected gate runs ETHOS's Python tests, and it is the shipped probe's provider row."""
    policy = resolve_gate_policy(ROOT, full=full)
    gates = [policy.registry[gate_id] for gate_id in policy.gate_ids]

    probes = [gate.id for gate in gates if _PROBE in gate.providers]
    runners = [
        gate.id
        for gate in gates
        if _starts_pytest(list(gate.command))
        or ("nox" in gate.command and _session_starts_pytest(gate.command[-1]))
    ]

    assert probes == ["unit-architecture"]
    assert policy.registry["unit-architecture"].execution_mode == "provider"
    assert runners == []
