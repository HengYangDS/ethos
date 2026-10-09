"""Native member dependencies select exact observation reuse, not namespace snapshots."""

from __future__ import annotations

import ast
from collections import Counter
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.custody import InvocationCustody
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.bindings import BindingValue
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.functions.effects import EffectSummary
    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation
    from ethos.repository.policy.references.python.scope import BindingScope


@pytest.mark.parametrize("change", ["none", "selected", "sibling"])
def test_native_leaf_reuses_only_unchanged_consumed_members(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    """The selected slot invalidates reuse; native identities and sibling changes do not."""
    source = (
        "import types as ns\nimport subprocess as sp\n"
        "ns.flag = 'before_probe'\nns.other = 'sibling_probe'\n"
        "def read(): return ns.flag\n"
        "sp.run([read()])\nsp.run([read()])\n"
    )
    if change != "none":
        source += f"ns.{'flag' if change == 'selected' else 'other'} = 'after_probe'\n"
    source += "sp.run([read()])\nsp.run([read()])\n"
    bodies: Counter[str] = Counter()
    native = PythonInvocations.return_values

    def counted(
        owner: PythonInvocations,
        invocation: SourceInvocation,
        flow: PythonReferenceFlow,
        child: BindingScope,
    ) -> BindingValue:
        if not owner.summarizing:
            bodies[getattr(invocation.definition.node, "name", "<lambda>")] += 1
        return native(owner, invocation, flow, child)

    monkeypatch.setattr(PythonInvocations, "return_values", counted)
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)

    assert flow.result.executables == (
        {"before_probe", "after_probe"} if change == "selected" else {"before_probe"}
    ), flow.result
    assert not flow.result.uncertainties, flow.result
    assert bodies["read"] == (2 if change == "selected" else 1), bodies


def test_native_namespace_write_is_not_a_reusable_answer() -> None:
    """Write-only native calls must replay their stored effect despite an identical return."""
    source = (
        "import types as ns\nimport subprocess as sp\n"
        "def write():\n    ns.flag = 'namespace_probe'\n    return 'noop_probe'\n"
        "sp.run([write()])\nns.flag = 'reset_probe'\n"
        "sp.run([write()])\nsp.run([ns.flag])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)

    assert flow.result.executables == {"noop_probe", "namespace_probe"}, flow.result
    assert not flow.result.uncertainties, flow.result
    summary = next(
        summary for key, summary in sources.invocations.summaries.items() if ":write:" in key
    )
    assert summary.direct
    assert not summary.answers


@pytest.mark.parametrize("selector", ["'flag'", "name", "str(name)"])
def test_native_member_reuse_requires_a_closed_selector(selector: str) -> None:
    """A concrete invocation cannot make a symbolic summary's dependency exact."""
    source = (
        "import types as ns\nimport subprocess as sp\n"
        "ns.flag = ''\n"
        f"def read(name): return getattr(ns, {selector})\n"
        "sp.run([read('flag')])\n"
        "ns.flag = 'selector_probe'\n"
        "sp.run([read('flag')])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)

    assert flow.result.executables == {"selector_probe"}, flow.result
    summary = next(
        summary for key, summary in sources.invocations.summaries.items() if ":read:" in key
    )
    assert bool(summary.answers) == (selector == "'flag'")


def test_effectful_invocation_does_not_validate_unusable_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject answer reuse before traversing dependencies that cannot authorize a hit."""
    checks = 0
    native = InvocationCustody.unchanged

    def counted(
        custody: InvocationCustody,
        summary: EffectSummary,
        scope: BindingScope,
        observer: PythonConsumption,
    ) -> bool:
        nonlocal checks
        if summary.direct and scope.name.endswith(".run"):
            checks += 1
        return native(custody, summary, scope, observer)

    monkeypatch.setattr(InvocationCustody, "unchanged", counted)
    source = (
        "import subprocess as sp\n"
        "def run():\n    sp.run(['effect_probe'])\n    return ''\n"
        "run()\nrun()\nrun()\nrun()\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)

    assert flow.result.executables == {"effect_probe"}, flow.result
    assert not flow.result.uncertainties, flow.result
    assert checks == 0
