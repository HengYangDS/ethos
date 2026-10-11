"""Native record allocation retains fields, mutable aliases and constructor custody."""

from __future__ import annotations

import ast

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns

_PROCESS = 'import os\nimport subprocess\nimport thing\nc = subprocess.CompletedProcess(["x"], 0'


@pytest.mark.parametrize(
    ("body", "inputs", "unknown"),
    [
        (', "KEY")\n', {"KEY"}, False),
        (", stdout='KEY')\n", {"KEY"}, False),
        (", **thing.named())\n", set(), True),
        (", *thing.values())\n", set(), True),
        (', "KEY")\nc.stdout = thing.value()\n', set(), True),
        (', "KEY")\nd = c\nd.stdout = "NEW"\n', {"NEW"}, False),
        (
            ', "A")\nc = c if thing.flag() else thing.other()\nc.stdout = "NEW"\n',
            {"A", "NEW"},
            True,
        ),
        (', "KEY")\ndel c.stdout\n', set(), True),
        (', "KEY")\nthing.mutate(c)\n', set(), True),
        (', "KEY")\nc.__dict__["stdout"] = thing.value()\n', set(), True),
    ],
    ids=[
        "positional",
        "keyword",
        "kwargs",
        "spread",
        "opaque",
        "alias",
        "weak",
        "del",
        "escape",
        "dict",
    ],
)
def test_native_completed_process_fields_follow_aggregate_stores(
    body: str, inputs: set[str], *, unknown: bool
) -> None:
    """Native process fields are allocated once; exact stores replace, aliases only join."""
    source = f"{_PROCESS}{body}os.environ.get(c.stdout)\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.inputs == inputs
    assert bool(observation.uncertainties) is unknown


@pytest.mark.parametrize(
    ("constructor", "member"),
    [
        ("subprocess.CompletedProcess(state, 0)", "args"),
        ("subprocess.TimeoutExpired(state, 1)", "cmd"),
        ("subprocess.CalledProcessError(1, state)", "cmd"),
    ],
)
@pytest.mark.parametrize("mutation", ["none", "alias", "escape"])
def test_native_record_retention_is_not_mutation(
    constructor: str, member: str, mutation: str
) -> None:
    """Field retention preserves aliases; only actual stores or opaque escape change state."""
    source = f"import subprocess, thing\nstate = ['record_probe']\nrecord = {constructor}\n"
    if mutation == "alias":
        source += f"record.{member}[0] = 'changed_probe'\n"
    if mutation == "escape":
        source += "thing.mutate(record)\n"
    source += "subprocess.run(state)\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert bool(observation.uncertainties) is (mutation == "escape"), observation
    if mutation != "escape":
        assert observation.executables == (
            {"changed_probe"} if mutation == "alias" else {"record_probe"}
        ), observation


@pytest.mark.parametrize(
    "constructor", ["CompletedProcess", "TimeoutExpired", "CalledProcessError"]
)
def test_native_record_constructor_replacement_invalidates_captured_state(constructor: str) -> None:
    """A native signature does not close the effects of a replaced initializer."""
    source = (
        "import subprocess\n"
        "state = ['before_probe']\n"
        "def replacement(*args, **kwargs):\n"
        "    state[0] = 'after_probe'\n"
        f"subprocess.{constructor}.__init__ = replacement\n"
        f"subprocess.{constructor}(state, 1)\n"
        "subprocess.run(state)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert any(item.state == "unknown" for item in observation.uncertainties), observation


@pytest.mark.parametrize(
    "constructor",
    ["subprocess.TimeoutExpired('cmd', 1)", "subprocess.CalledProcessError(1, 'cmd')"],
)
@pytest.mark.parametrize("stored", ["output", "stdout"])
def test_native_exception_output_alias_follows_actual_store(constructor: str, stored: str) -> None:
    """Both public names refer to the same output slot, not two independent copies."""
    source = (
        "import subprocess\n"
        f"record = {constructor[:-1]}, output='before_probe')\n"
        f"record.{stored} = 'after_probe'\n"
        "subprocess.run([record.stdout])\n"
        "subprocess.run([record.output])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.executables == {"after_probe"}, observation
    assert not observation.uncertainties, observation


def test_native_exception_replaced_descriptor_cannot_preserve_captured_output() -> None:
    """A changed property setter owns effects, even when the constructor stays native."""
    source = (
        "import subprocess, thing\n"
        "state = ['before_probe']\n"
        "def setter(*args):\n"
        "    state[0] = 'after_probe'\n"
        "subprocess.TimeoutExpired.stdout = property(thing.getter, setter)\n"
        "record = subprocess.TimeoutExpired('cmd', 1)\n"
        "record.stdout = 'unused_probe'\n"
        "subprocess.run(state)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert any(item.state == "unknown" for item in observation.uncertainties), observation


def test_native_exception_replaced_getter_havocs_implicit_receiver() -> None:
    """Discarding a descriptor result does not discard mutation of its receiver."""
    source = (
        "import subprocess\n"
        "record = subprocess.TimeoutExpired('cmd', 1, output='before_probe')\n"
        "def getter(self):\n"
        "    self.output = 'after_probe'\n"
        "    return self.output\n"
        "subprocess.TimeoutExpired.stdout = property(getter)\n"
        "ignored = record.stdout\n"
        "subprocess.run([record.output])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert any(item.state == "unknown" for item in observation.uncertainties), observation
