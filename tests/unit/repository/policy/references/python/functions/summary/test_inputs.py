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


@pytest.mark.parametrize(
    ("call", "inputs", "unknown"),
    [
        ("run()", {"PATH"}, set()),
        ("run({'PATH': 'x'})", {"PATH"}, set()),
        ("run(thing.environment())", {"PATH"}, set()),
        ("run([('PATH', os.environ)])", {"PATH"}, {"os.environ"}),
    ],
    ids=["omitted", "mapping", "opaque", "pairs"],
)
def test_environment_copy_defers_each_actual_mapping(
    call: str, inputs: set[str], unknown: set[str]
) -> None:
    """A native dict copy reads the environment branch and keeps other mappings exact."""
    source = (
        "import os\nimport thing\n"
        "def run(env=None):\n"
        "    environment = dict(os.environ if env is None else env)\n"
        "    return environment['PATH']\n"
        f"{call}\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == inputs
    assert {item.target for item in observation.uncertainties if item.state == "unknown"} == unknown


@pytest.mark.parametrize(
    ("statements", "inputs"),
    [
        ("again = dict(copied)\n", {"PROBE"}),
        ("again = dict(copied)\ncopied['PROBE'] = 'literal'\n", {"PROBE"}),
        ("copied['PROBE'] = 'literal'\nagain = dict(copied)\n", set()),
    ],
    ids=["second-copy", "mutated-after-copy", "overlay-before-copy"],
)
def test_environment_copy_of_copy_conserves_native_provenance(
    statements: str, inputs: set[str]
) -> None:
    """A fresh copy keeps the source copy's environment reads and its own overlays."""
    source = f"import os\ncopied = dict(os.environ)\n{statements}result = again['PROBE']\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == inputs
    assert not [item for item in observation.uncertainties if item.state == "unknown"]
