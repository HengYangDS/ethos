"""Function summary input observations preserve actual receiver identity."""

from __future__ import annotations

import ast

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@pytest.mark.parametrize(
    ("body", "actual", "inputs", "unknown"),
    [
        ("env['K']", "os.environ", {"K"}, set()),
        ("env['K']", "{'K': 'x'}", set(), set()),
        ("env[f'K_{os.getenv('N', '')}']", "os.environ", {"N"}, {"os.environ.__getitem__"}),
    ],
    ids=["environment", "mapping", "dynamic-key"],
)
def test_parameter_subscript_replays_actual_environment_reads(
    body: str, actual: str, inputs: set[str], unknown: set[str]
) -> None:
    """A subscript on a symbolic parameter is consumed against each actual receiver."""
    source = f"import os\ndef read(env):\n    return {body}\nread({actual})\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == inputs
    assert {item.target for item in observation.uncertainties if item.state == "unknown"} == unknown
