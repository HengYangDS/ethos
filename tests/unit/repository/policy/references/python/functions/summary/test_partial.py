"""Native partial objects bind captured arguments without escaping their callable."""

from __future__ import annotations

import ast

import pytest

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.arguments import bound_arguments
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns

_READ = (
    "import os\n"
    "import thing\n"
    "from functools import partial\n"
    "def read(environment, name='SYSTEMROOT', *, suffix=''):\n"
    "    return environment.get(name + suffix, '')\n"
    "def run(admit):\n"
    "    return admit()\n"
)


@pytest.mark.parametrize(
    ("call", "inputs", "unknown"),
    [
        ("run(partial(read, os.environ))", {"SYSTEMROOT"}, set()),
        ("run(partial(read, os.environ, 'HOME'))", {"HOME"}, set()),
        ("run(partial(partial(read, os.environ), suffix='_X'))", {"SYSTEMROOT_X"}, set()),
        ("run(partial(read, os.environ, suffix='_X'))", {"SYSTEMROOT_X"}, set()),
        ("partial(read, os.environ)(name='PATH')", {"PATH"}, set()),
        ("run(partial(read, thing.mapping()))", set(), set()),
        ("run(partial(thing.read, os.environ))", set(), {"os.environ"}),
        ("run(partial(read, *thing.values()))", set(), set()),
        ("thing.run(partial(read, os.environ))", {"SYSTEMROOT"}, {"os.environ.get"}),
        ("partial(read, os.environ, 'HOME')(name='PATH')", set(), set()),
        ("partial(read, environment=os.environ)('HOME')", set(), set()),
        ("partial(read, os.environ)(environment=os.environ)", set(), set()),
        ("partial(partial(read, os.environ), suffix='_X')(name='P')", {"P_X"}, set()),
        ("partial(read, os.environ, suffix='_X')(suffix='_Y')", {"SYSTEMROOT_Y"}, set()),
    ],
    ids=[
        "bound",
        "positional",
        "nested",
        "keyword",
        "override",
        "opaque-argument",
        "opaque-callable",
        "spread",
        "native-callback",
        "duplicate-positional",
        "duplicate-keyword",
        "duplicate-captured",
        "nested-call",
        "keyword-override",
    ],
)
def test_partial_binds_captured_arguments_at_each_call(
    call: str, inputs: set[str], unknown: set[str]
) -> None:
    """Captured values reach the bound call; opaque callables and inputs stay unknown."""
    source = f"{_READ}{call}\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    found = {item.target for item in observation.uncertainties if item.state == "unknown"}
    assert observation.inputs == inputs
    assert found == unknown


def test_equivalent_partials_reuse_one_definition() -> None:
    """Equal composed captures share identity; distinct captures stay distinct."""
    calls = "".join(f"f{index} = partial(partial(read))\n" for index in range(8))
    source = f"{_READ}{calls}g = partial(read, os.environ)\nh = partial(read, os.environ)\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert len(sources.definitions) == 3


@pytest.mark.parametrize(
    ("definition", "valid"),
    [("def read(environment, name='HOME'):\n", False), ("def read(environment, **named):\n", True)],
    ids=["named", "variadic"],
)
def test_partial_binding_keeps_every_actual_keyword(definition: str, *, valid: bool) -> None:
    """An empty keyword is a real native keyword; only the original signature decides."""
    source = f"import os\nfrom functools import partial\n{definition}    return 1\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.observe(tree, source=source)
    (read,) = sources.definitions.values()
    environment = BindingValue(targets=frozenset({"os.environ"}))
    target = sources.partial((BindingValue(targets=frozenset({read.key})), environment), {})
    assert target is not None
    (bound,) = (sources.definitions[key] for key in target.targets)
    actual = bound_arguments(bound, (), {"": BindingValue(strings=frozenset({"x"}))})
    assert (actual is not None) is valid


@pytest.mark.parametrize(
    ("definition", "capture", "inputs", "unknown"),
    [
        ("def read(*items):\n    for item in items:\n", "os.environ", {"C"}, {"os.environ.get"}),
        ("def read(item):\n    for item in (item,):\n", "os.environ", {"C"}, set()),
        ("def read(item):\n    for item in (item,):\n", "os.environ, os.environ", set(), set()),
    ],
    ids=["variadic", "positional", "invalid"],
)
def test_escaped_partial_packs_captures_with_runtime_slots(
    definition: str, capture: str, inputs: set[str], unknown: set[str]
) -> None:
    """Escaped captures keep native packing; later runtime arguments stay unknown."""
    source = (
        "import os\nimport thing\nfrom functools import partial\n"
        f"{definition}        item.get('C')\nthing.run(partial(read, {capture}))\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == inputs
    assert {item.target for item in observation.uncertainties if item.state == "unknown"} == unknown


@pytest.mark.parametrize(
    ("call", "unknown"),
    [
        ("run(*thing.args())", False),
        ("run(*thing.args(), env=thing.env())", True),
        ("run(**thing.kwargs())", True),
        ("thing.run(run)", True),
    ],
    ids=["positional-only-uncertainty", "explicit-keyword", "keyword-pack", "escaped-callback"],
)
def test_positional_pack_keeps_keyword_only_receiver(call: str, *, unknown: bool) -> None:
    """Actual positional uncertainty cannot erase an independent keyword-only default."""
    source = (
        "import os, thing\n"
        "def overlay(*environments):\n"
        "    for environment in environments:\n"
        "        environment.get('C')\n"
        "def run(*args, env=None):\n"
        "    overlay(os.environ, env or {})\n"
        f"{call}\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == {"C"}
    assert bool([item for item in observation.uncertainties if item.state == "unknown"]) is unknown


@pytest.mark.parametrize(
    ("default", "call", "unknown"),
    [
        ("", "invoke(*(sp.run,))", False),
        ("=sp.run", "invoke(*thing.args())", True),
    ],
    ids=["finite-pack", "possibly-empty-pack"],
)
def test_positional_pack_preserves_callback_effect(
    default: str, call: str, *, unknown: bool
) -> None:
    """Possible empty packs retain default effects alongside unknown supplied callbacks."""
    source = (
        "import subprocess as sp, thing\n"
        f"def invoke(callback{default}):\n"
        "    callback(['spread_probe'])\n"
        f"{call}\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.executables == {"spread_probe"}
    assert bool(observation.uncertainties) is unknown
