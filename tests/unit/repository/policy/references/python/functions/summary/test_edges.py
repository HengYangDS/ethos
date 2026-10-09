"""Function summaries retain distinct effect sites and actual binding values."""

from __future__ import annotations

import ast
from dataclasses import replace

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


def test_loop_passes_record_each_effect_edge_once_per_actual_values() -> None:
    """Fixed-point passes re-derive equal edges; distinct sites and values stay separate."""
    source = (
        "import subprocess\n"
        "def run_all(command, items, callback):\n"
        "    for item in items:\n"
        "        subprocess.run([command, item])\n"
        "        callback(item)\n"
        "    subprocess.run([command, 'after'])\n"
        "run_all('tool', ('a', 'b'), print)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    summary = next(iter(sources.invocations.summaries.values()))
    edges = [
        (id(call.node), call.callee, call.arguments, tuple(call.keywords.items()))
        for call in summary.calls
    ]
    assert observation.executables == {"tool"}
    assert len(edges) == len(set(edges))
    assert len({id(call.node) for call in summary.calls}) == 3

    first = summary.calls[0]
    summary.record(first)
    summary.record(replace(first, arguments=(BindingValue(strings=frozenset({"other"})),)))
    summary.record(replace(first, callee=BindingValue(unknown=True, deferred=True)))
    summary.record(replace(first, keywords={"cwd": BindingValue(unknown=True)}))
    assert len(summary.calls) == len(edges) + 3
