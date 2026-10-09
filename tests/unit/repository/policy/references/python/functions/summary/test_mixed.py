"""Joined concrete and symbolic alternatives keep their own member relations."""

from __future__ import annotations

import ast

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@pytest.mark.parametrize(
    "caller",
    [
        "def run(path, env):\n    overlay(os.environ, env)\n",
        "def run(path, env=None):\n    overlay(os.environ, env or {})\n",
        "def run(path):\n    overlay(os.environ, {})\n",
        "def run(path, env):\n    overlay(os.environ, env)\nrun('x', thing.env())\n",
        "overlay(os.environ)\n",
    ],
    ids=[
        "symbolic-sibling",
        "defaulted-sibling",
        "literal-sibling",
        "opaque-actual",
        "native",
    ],
)
def test_iterated_pack_keeps_native_and_symbolic_alternatives(caller: str) -> None:
    """A symbolic sibling does not erase the native receiver's member read."""
    source = (
        "import os\nimport thing\n"
        "def overlay(*environments):\n"
        "    for environment in environments:\n"
        "        environment.get('C')\n"
        f"{caller}"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == {"C"}
    assert not [item for item in observation.uncertainties if item.state == "unknown"]


def test_container_pack_keeps_concrete_items_beside_symbolic_sibling() -> None:
    """A concrete list element is projected with its heap custody, not dropped."""
    source = (
        "import os\n"
        "def overlay(*collections):\n"
        "    for collection in collections:\n"
        "        for environment in collection:\n"
        "            environment.get('C')\n"
        "def run(env):\n"
        "    overlay([os.environ], env)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == {"C"}


@pytest.mark.parametrize(
    ("call", "inputs"),
    [
        ("overlay([os.environ], env)", {"C"}),
        ("overlay(env, [os.environ])", {"C"}),
        ("box = [os.environ]\n    box[0] = {}\n    overlay(box, env)", set()),
        ("box = [{}]\n    box[0] = os.environ\n    overlay(box, env)\n    box[0] = {}", {"C"}),
        ("box = [{}]\n    box[-1] = os.environ\n    overlay(box, env)", {"C"}),
        (
            "box = [{}]\n    overlay(box, env)\n    box[0] = os.environ\n    overlay(box, env)",
            {"C"},
        ),
        ("box = [{}]\n    box[3] = os.environ\n    overlay(box, env)", set()),
        ("box = [{}]\n    box[len(env)] = os.environ\n    overlay(box, env)", {"C"}),
    ],
    ids=[
        "actual",
        "reversed",
        "replaced-before-call",
        "replaced-after-call",
        "negative-index",
        "later-call",
        "out-of-range",
        "dynamic-index",
    ],
)
def test_call_edge_keeps_its_own_allocation_custody(call: str, inputs: set[str]) -> None:
    """An actual caller instantiates callee-local allocations from the call program point."""
    source = (
        "import os\n"
        "def overlay(*collections):\n"
        "    for collection in collections:\n"
        "        for environment in collection:\n"
        "            environment.get('C')\n"
        f"def run(env):\n    {call}\n"
        "run([{}])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == inputs
    assert not [item for item in observation.uncertainties if item.state == "unknown"]


@pytest.mark.parametrize(
    ("loop", "call", "inputs", "unknown"),
    [
        ("environments.values()", "read(environment=os.environ)", {"C"}, set()),
        ("environments.values()", "read(environment={})", set(), set()),
        ("environments.keys()", "read(environment=os.environ)", set(), set()),
        ("environments.values()", "read(environment=Shadow())", set(), set()),
        (
            "environments.values()",
            "thing.run(partial(read, environment=os.environ))",
            {"C"},
            {"os.environ.get"},
        ),
    ],
    ids=["values", "plain-mapping", "keys", "shadow-element", "escaped-partial"],
)
def test_symbolic_mapping_view_keeps_packed_values(
    loop: str, call: str, inputs: set[str], unknown: set[str]
) -> None:
    """A native view of a symbolic keyword pack is instantiated against each actual pack."""
    source = (
        "import os\nimport thing\nfrom functools import partial\n"
        "class Shadow:\n    def get(self, name):\n        return name\n"
        f"def read(**environments):\n    for environment in {loop}:\n"
        "        environment.get('C')\n"
        f"{call}\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == inputs
    assert {item.target for item in observation.uncertainties if item.state == "unknown"} == unknown


def test_symbolic_items_unpack_keeps_pair_members() -> None:
    """Tuple unpacking of a symbolic native items view keeps each pair member relation."""
    source = (
        "import os\n"
        "def read(**environments):\n"
        "    for _, environment in environments.items():\n"
        "        environment.get('C')\n"
        "read(environment=os.environ)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == {"C"}
