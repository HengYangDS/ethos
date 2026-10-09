"""Native member dependencies select exact observation reuse, not namespace snapshots."""

from __future__ import annotations

import ast
import sys
from collections import Counter
from types import BuiltinFunctionType
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ParameterProjection
from ethos.repository.policy.references.python.bindings import ReceiverMethod
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.custody import InvocationCustody
from ethos.repository.policy.references.python.functions.effects import substitute
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType

    from ethos.repository.policy.references.python.bindings import BindingScope
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.functions.effects import EffectSummary
    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation


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


@pytest.mark.parametrize("change", ["none", "selected"])
def test_summary_validation_does_not_collect_ancestor_dependencies(change: str) -> None:
    """Checking a callee witness cannot turn the validator's frame into a dependency."""
    source = (
        "import types as ns\nns.flag = 'before_probe'\n"
        "def leaf(): return ns.flag\n"
        "def outer(): return leaf()\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    invocations = sources.invocations
    leaf = sources.definitions[next(iter(scope.lookup("leaf").targets))]
    outer = sources.definitions[next(iter(scope.lookup("outer").targets))]
    selected = invocations.summary_for(leaf, flow.result, scope)
    ancestor = invocations.summary_for(outer, flow.result, scope)
    before = (dict(ancestor.reads), dict(ancestor.members), tuple(ancestor.calls))
    if change == "selected":
        scope.assign_member(
            "types.flag", type(selected.returned)(strings=frozenset({"after_probe"}))
        )
    invocations.summarizing.append(outer.key)
    try:
        valid = invocations.custody.unchanged(selected, scope, flow.result)
    finally:
        invocations.summarizing.pop()

    assert valid == (change == "none")
    assert (ancestor.reads, ancestor.members, tuple(ancestor.calls)) == before


def test_validation_read_does_not_extend_active_summary() -> None:
    """Validation may resolve a lexical value without collecting a new dependency."""
    source = "flag = 'before_probe'\ndef owner(): return ''\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    invocations = sources.invocations
    definition = sources.definitions[next(iter(scope.lookup("owner").targets))]
    summary = invocations.summary_for(definition, flow.result, scope)
    before = dict(summary.reads)
    invocations.summarizing.append(definition.key)
    invocations.validating += 1
    try:
        value = invocations.read(scope, "flag")
    finally:
        invocations.validating -= 1
        invocations.summarizing.pop()

    assert value.strings == {"before_probe"}
    assert summary.reads == before
    invocations.summarizing.append(definition.key)
    try:
        invocations.read(scope, "flag")
    finally:
        invocations.summarizing.pop()
    assert set(summary.reads) - before.keys() == {(scope.identity, "flag", False)}


@pytest.mark.parametrize("unrelated", [0, 64])
def test_source_target_lookup_is_bounded_by_selected_relations(unrelated: int) -> None:
    """Native/source alternatives preserve effects without scanning unrelated registries."""
    source = (
        "import subprocess as sp\n"
        "def executable(): return 'selected_probe'\n"
        "def launch(): sp.run([executable()])\n"
        "launch()\n"
        + "\n".join(f"def unused_{index}(): return {index}" for index in range(unrelated))
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    enumerations: Counter[str] = Counter()

    def observe(_frame: FrameType, event: str, value: object) -> None:
        if (
            event == "c_call"
            and isinstance(value, BuiltinFunctionType)
            and value.__name__ == "keys"
        ):
            if value.__self__ is sources.definitions:
                enumerations["definitions"] += 1
            elif value.__self__ is sources.records:
                enumerations["records"] += 1

    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    finally:
        sys.setprofile(previous)

    assert result.executables == {"selected_probe"}
    assert result.uncertainties == []
    assert enumerations == {}, enumerations


@pytest.mark.parametrize("shape", ["leaf", "items", "fields"])
@pytest.mark.parametrize("deep", [False, True])
def test_native_resolution_shares_unchanged_semantic_values(shape: str, *, deep: bool) -> None:
    """Resolution retains unchanged paths, including their uncertainty and provenance."""
    source = "import subprocess as sp\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    leaf = BindingValue(strings=frozenset({"shared_probe"}), unknown=True, context_limited=True)
    value = (
        BindingValue(items=(leaf,), ordered=True)
        if shape == "items"
        else BindingValue(fields=(("selected", leaf),))
        if shape == "fields"
        else leaf
    )

    for _ in range(3):
        assert sources.invocations.resolve(value, scope, flow.result, deep=deep) is value

    assert leaf.strings == {"shared_probe"}
    assert leaf.unknown
    assert leaf.context_limited
    assert not flow.result.executables
    assert not flow.result.uncertainties


@pytest.mark.parametrize(
    "wrap",
    [
        lambda value: value,
        lambda value: BindingValue(items=(value,), ordered=True),
        lambda value: BindingValue(entries=(("selected", value),)),
        lambda value: BindingValue(fields=(("selected", value),)),
        lambda value: BindingValue(element=value),
        lambda value: BindingValue(methods=frozenset({ReceiverMethod(value, "get")})),
    ],
    ids=["leaf", "items", "entries", "fields", "element", "methods"],
)
def test_substitution_preserves_unchanged_structural_identity(
    wrap: Callable[[BindingValue], BindingValue],
) -> None:
    """Complete recursive substitution retains unchanged ownership and all value channels."""
    source = "def choose(command): return command\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    leaf = BindingValue(
        strings=frozenset({"unchanged_probe"}),
        parameters=frozenset({ParameterProjection("command", owner="foreign_invocation")}),
        unknown=True,
        context_limited=True,
    )
    value = wrap(leaf)
    assert substitute(value, {}, scope, sources, flow.result, owner="selected_invocation") is value
    assert not flow.result.uncertainties


def test_substitution_rebuilds_only_the_changed_ancestor() -> None:
    """A selected parameter changes its ancestors, never their immutable siblings."""
    source = "def choose(command): return command\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    stable = BindingValue(strings=frozenset({"stable_probe"}))
    selected = BindingValue(
        parameters=frozenset({ParameterProjection("command", owner="selected")})
    )
    value = BindingValue(fields=(("stable", stable), ("selected", selected)))
    actual = BindingValue(strings=frozenset({"changed_probe"}))
    resolved = substitute(value, {"command": actual}, scope, sources, flow.result, owner="selected")
    assert resolved is not value
    assert resolved.fields == (("stable", stable), ("selected", actual))
    assert resolved.fields[0][1] is stable
    assert resolved.fields[1][1] is actual


def test_native_resolution_rebuilds_only_the_changed_ancestor() -> None:
    """An actual deferred child resolves without reconstructing its immutable sibling."""
    source = "def choose(command): return command\nselected = choose('changed_probe')\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    stable = BindingValue(strings=frozenset({"stable_probe"}))
    value = BindingValue(fields=(("stable", stable), ("selected", scope.lookup("selected"))))

    resolved = sources.invocations.resolve(value, scope, flow.result)

    assert resolved is not value
    assert resolved.fields is not None
    fields = dict(resolved.fields)
    assert fields["stable"] is stable
    assert fields["selected"].strings == {"changed_probe"}
    assert not fields["selected"].projections
    assert sources.invocations.resolve(resolved, scope, flow.result) is resolved
    assert not flow.result.executables
    assert not flow.result.uncertainties
