"""Context budgets widen one procedure without widening unrelated procedures."""

from __future__ import annotations

import ast

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@pytest.mark.parametrize("dynamic", [False, True], ids=["default", "dynamic"])
def test_escaped_context_budget_keeps_unrelated_default_reads_closed(*, dynamic: bool) -> None:
    """A busy helper widens itself; another helper keeps its only actual default context."""
    calls = "".join(f"    noisy('{index}')\n" for index in range(200))
    source = (
        "import os\n"
        "import thing\n"
        "def native(*, environment=None):\n"
        "    values = os.environ if environment is None else environment\n"
        "    return values.get('SYSTEMROOT', '')\n"
        "def noisy(name):\n"
        f"    return {'os.environ[name]' if dynamic else 'name'}\n"
        "def admitted():\n"
        "    value = native()\n"
        f"{calls}"
        "    return value\n"
        "thing.run(admitted)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    unknown = {
        (item.target, item.line) for item in observation.uncertainties if item.state == "unknown"
    }
    assert ("os.environ.get", 5) not in unknown
    assert "SYSTEMROOT" in observation.inputs
    assert (("os.environ.__getitem__", 7) in unknown) is dynamic
