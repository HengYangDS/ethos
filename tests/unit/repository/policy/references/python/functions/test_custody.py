"""Invocation custody preserves live graphs and exact dependency reuse."""

from __future__ import annotations

import ast
from collections import Counter
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.python.bindings import AggregateIdentity
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ParameterProjection
from ethos.repository.policy.references.python.bindings import ReceiverMethod
from ethos.repository.policy.references.python.effects import PythonConsumption
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.effects import substitute
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns
from ethos.repository.policy.references.python.scope import BindingScope

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation
    from ethos.repository.policy.references.python.functions.returns import FunctionDefinition


@pytest.mark.parametrize(
    ("live_root", "child_state"),
    [(False, "missing"), (True, "missing"), (True, "live"), (True, "unknown")],
)
def test_publication_follows_selected_live_edges(*, live_root: bool, child_state: str) -> None:
    """Missing custody is filled per identity; present contents never roll back."""
    root = AggregateIdentity("owner", 1, 0)
    old = AggregateIdentity("owner", 2, 0)
    new = AggregateIdentity("owner", 3, 0)
    reference = BindingValue(aggregates=frozenset({root}))
    old_reference = BindingValue(aggregates=frozenset({old}))
    new_reference = BindingValue(aggregates=frozenset({new}))
    before = BindingValue(strings=frozenset({"before_probe"}))
    after = BindingValue(strings=frozenset({"after_probe"}))
    live = BindingValue(strings=frozenset({"live_probe"}))
    source = BindingScope(
        "owner",
        members={root: BindingValue(items=(old_reference,)), old: before, new: after},
        member_history={root: BindingValue(items=(old_reference,)), old: before, new: after},
    )
    target = BindingScope("caller")
    if live_root:
        target.members[root] = BindingValue(items=(new_reference,))
    if child_state != "missing":
        target.members[new] = live if child_state == "live" else BindingValue(unknown=True)
    sources = PythonSourceReturns({}, {}, PythonReferenceFlow)

    sources.invocations.custody.publish(reference, source, target)

    child = new if live_root else old
    expected = (
        before
        if not live_root
        else after
        if child_state == "missing"
        else live
        if child_state == "live"
        else BindingValue(unknown=True)
    )
    assert target.members == {
        root: BindingValue(items=(new_reference if live_root else old_reference,)),
        child: expected,
    }
    assert old not in target.member_history if live_root else target.member_history[old] == before
    assert (
        root not in target.member_history
        if live_root
        else target.member_history[root] == source.member_history[root]
    )


@pytest.mark.parametrize("action", ["stable", "alias", "rebind"])
@pytest.mark.parametrize("repetitions", [1, 6])
def test_imported_summaries_reuse_only_unchanged_custody(
    monkeypatch: pytest.MonkeyPatch, action: str, repetitions: int
) -> None:
    """Discarded calls reuse dependencies; alias mutation and rebinding still invalidate."""
    builds: Counter[str] = Counter()
    evaluations: Counter[str] = Counter()
    summarize = PythonInvocations.summarize
    evaluate = PythonInvocations.evaluate

    def record_summary(
        self: PythonInvocations,
        definition: FunctionDefinition,
        result: PythonConsumption,
        scope: BindingScope | None = None,
    ) -> None:
        builds[getattr(definition.node, "name", "<lambda>")] += 1
        summarize(self, definition, result, scope)

    def record_evaluation(
        self: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        if not self.summarizing:
            evaluations[getattr(invocation.definition.node, "name", "<lambda>")] += 1
        return evaluate(self, invocation, result)

    monkeypatch.setattr(PythonInvocations, "summarize", record_summary)
    monkeypatch.setattr(PythonInvocations, "evaluate", record_evaluation)
    owner = (
        'TABLE = {"nested": {"command": "before_probe"}}\n'
        'def leaf():\n    return TABLE["nested"].get("command")\n'
        "def alias():\n    return TABLE\n"
        'def rebind():\n    global TABLE\n    TABLE = {"nested": {"command": "rebound_probe"}}\n'
    )
    consumer = (
        "import subprocess as sp\nimport example.owner as owner\n"
        "def relay():\n    return owner.leaf()\n" + "relay()\n" * repetitions
    )
    if action != "stable":
        consumer += "saved = owner.alias()\n"
        consumer += (
            'saved["nested"]["command"] = "after_probe"\n'
            if action == "alias"
            else "owner.rebind()\n"
        )
        consumer += "relay()\n" * repetitions
    consumer += "sp.run([relay()])\n"
    if action == "rebind":
        consumer += 'sp.run([saved["nested"]["command"]])\n'
    path = "src/example/probe.py"
    files = {"src/example/owner.py": owner, path: consumer}
    trees = {name: ast.parse(text) for name, text in files.items()}
    sources = PythonSourceReturns(files, trees, PythonReferenceFlow)
    flow = PythonReferenceFlow(path, {}, sources=sources)

    flow.initialize(trees[path], source=consumer)

    expected = {
        "stable": {"before_probe"},
        "alias": {"after_probe"},
        "rebind": {"before_probe", "rebound_probe"},
    }
    assert flow.result.executables == expected[action], flow.result
    assert not flow.result.uncertainties, flow.result
    expected_builds = 1 if action == "stable" else 2
    assert builds["relay"] == builds["leaf"] == expected_builds, builds
    assert evaluations["relay"] == evaluations["leaf"] == 1, evaluations


@pytest.mark.parametrize("reader", ["index", "get", "truth", "keys", "values"])
@pytest.mark.parametrize("changed", [False, True])
def test_cache_follows_consumed_relation(
    monkeypatch: pytest.MonkeyPatch, reader: str, *, changed: bool
) -> None:
    """Binding, selected content and shape have distinct cache dependencies."""
    expression = {
        "index": "state['selected']['callback']",
        "get": "state['selected'].get('callback', noop)",
        "truth": "sp.run if state['selected'] else noop",
        "keys": "sp.run if tuple(state['selected'].keys()) else noop",
        "values": "tuple(state['selected'].values())[0]",
    }[reader]
    initial = "{}" if reader in {"get", "truth", "keys"} else "{'callback': noop}"
    member = "selected" if changed else "sibling"
    source = (
        "import subprocess as sp\ndef noop(command):\n    return None\n"
        f"state = {{'selected': {initial}, 'sibling': {{'callback': noop}}}}\n"
        f"def choose():\n    return {expression}\n"
        "def apply():\n    choose()(['relation_probe'])\n"
        f"apply()\nstate['{member}']['callback'] = sp.run\napply()\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    builds: Counter[str] = Counter()
    summarize = PythonInvocations.summarize

    def counted(
        owner: PythonInvocations,
        definition: FunctionDefinition,
        result: PythonConsumption,
        scope: BindingScope | None = None,
    ) -> None:
        builds[getattr(definition.node, "name", "<lambda>")] += 1
        summarize(owner, definition, result, scope)

    monkeypatch.setattr(PythonInvocations, "summarize", counted)
    flow.initialize(tree, source=source)

    assert flow.result.executables == ({"relation_probe"} if changed else set()), flow.result
    assert builds["choose"] == (2 if changed else 1), builds


@pytest.mark.parametrize("history", [BindingValue(unknown=True), BindingValue(local=True)])
def test_publication_preserves_independent_history_presence(history: BindingValue) -> None:
    """Filling missing current custody cannot overwrite present historical custody."""
    source, target = BindingScope("source"), BindingScope("target")
    identity = AggregateIdentity("probe.py", 1, 0)
    source.assign_member(identity, BindingValue(entries=(("command", BindingValue(local=True)),)))
    target.member_history[identity] = history
    sources = PythonSourceReturns({}, {}, PythonReferenceFlow)

    sources.invocations.custody.publish(
        BindingValue(aggregates=frozenset({identity})), source, target
    )

    assert target.member_binding(identity) == source.member(identity)
    assert target.member_binding(identity, later=True) == history


@pytest.mark.parametrize("depth", [1, 8, 12])
@pytest.mark.parametrize("repetitions", [1, 6])
def test_definition_summary_reuse_does_not_inherit_caller_limits(
    monkeypatch: pytest.MonkeyPatch, depth: int, repetitions: int
) -> None:
    """Equivalent discarded native reads reuse closed definitions, not depth cutoffs."""
    summarized: Counter[str] = Counter()
    evaluated: Counter[str] = Counter()
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        name = getattr(invocation.definition.node, "name", "<lambda>")
        (summarized if owner.summarizing else evaluated)[name] += 1
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    source = "from pathlib import Path\ndef leaf(value):\n    return Path(value).as_posix()\n"
    for index in range(depth):
        target = "leaf" if index == 0 else f"layer_{index - 1}"
        source += f"def layer_{index}(value):\n    return {target}(value)\n"
    source += f"layer_{depth - 1}('first')\n" * repetitions
    source += "leaf('later')\n" * repetitions
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert not flow.result.executables
    assert not flow.result.inputs
    assert not flow.result.uncertainties, flow.result
    assert not evaluated, evaluated
    assert max(summarized.values()) <= 2, summarized


@pytest.mark.parametrize("depth", [1, 6])
@pytest.mark.parametrize("behavior", ["pure", "effect", "recursive", "dynamic"])
def test_summary_context_preserves_consumed_effects_and_unknowns(depth: int, behavior: str) -> None:
    """Acyclic depth preserves native consumption; unsupported calls stay unresolved."""
    bodies = {
        "pure": "return value",
        "effect": "sp.run([value])\n    return value",
        "recursive": "return leaf(value)",
        "dynamic": "return value()",
    }
    source = f"import subprocess as sp\ndef leaf(value):\n    {bodies[behavior]}\n"
    for index in range(depth):
        target = "leaf" if index == 0 else f"layer_{index - 1}"
        source += f"def layer_{index}(value):\n    return {target}(value)\n"
    source += f"sp.run([layer_{depth - 1}('observed_probe')])\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert not flow.result.inputs
    if behavior in {"pure", "effect"}:
        assert flow.result.executables == {"observed_probe"}
        assert not flow.result.uncertainties, flow.result
    else:
        assert not flow.result.executables
        assert {item.reason for item in flow.result.uncertainties} == {"value_not_resolved"}


@pytest.mark.parametrize("depth", [1, 6, 7, 12])
@pytest.mark.parametrize("repetitions", [1, 3])
def test_consumed_returned_callable_preserves_transitive_incompleteness(
    depth: int, repetitions: int
) -> None:
    """A consumed return hole retains effects or bounded UNKNOWN, never false closure."""
    source = "import subprocess as sp\ndef leaf(): return sp.run\n"
    for index in range(depth):
        target = "leaf" if index == 0 else f"relay_{index - 1}"
        source += f"def relay_{index}(): return {target}()\n"
    source += f"def entry(): relay_{depth - 1}()('returned_probe')\n"
    source += "entry()\n" * repetitions
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert not flow.result.inputs
    if depth < 7:
        assert flow.result.executables == {"returned_probe"}
        assert not flow.result.uncertainties, flow.result
    else:
        assert flow.result.executables == {"returned_probe"} or flow.result.uncertainties
        assert {item.reason for item in flow.result.uncertainties} <= {
            "source_invocation_not_closed",
            "value_not_resolved",
        }


@pytest.mark.parametrize("depth", [7, 12])
@pytest.mark.parametrize("unrelated_first", [False, True])
def test_unrelated_call_order_preserves_pure_summary_reuse(
    monkeypatch: pytest.MonkeyPatch, depth: int, *, unrelated_first: bool
) -> None:
    """Unconsumed opaque calls do not inherit another value's analysis cutoff."""
    summarized: Counter[str] = Counter()
    evaluated: Counter[str] = Counter()
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        name = getattr(invocation.definition.node, "name", "<lambda>")
        (summarized if owner.summarizing else evaluated)[name] += 1
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    source = "def leaf(value):\n    return value\n"
    for index in range(depth):
        target = "leaf" if index == 0 else f"layer_{index - 1}"
        source += f"def layer_{index}(value):\n    return {target}(value)\n"
    selected = f"    selected = layer_{depth - 1}(value)\n"
    unrelated = "    ValueError('unused')\n"
    source += "def entry(value):\n"
    source += unrelated + selected if unrelated_first else selected + unrelated
    source += "    return selected\n" + "entry('unchanged')\n" * 3
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert not flow.result.executables
    assert not flow.result.inputs
    assert not flow.result.uncertainties, flow.result
    assert not evaluated, evaluated
    assert max(summarized.values()) <= 2, summarized


@pytest.mark.parametrize("residual", [False, True])
def test_parameter_substitution_preserves_independent_return_alternatives(
    *, residual: bool
) -> None:
    """Only the selected parameter obligation is discharged; independent branches survive."""
    slot = BindingValue(parameters=frozenset({ParameterProjection("callback", owner="choose")}))
    actual = BindingValue(targets=frozenset({"subprocess.run"}))
    value = slot.join(BindingValue(deferred=True, local=True, unknown=True)) if residual else slot
    scope = BindingScope("caller")
    sources = PythonSourceReturns({}, {}, PythonReferenceFlow)
    result = PythonConsumption("probe.py", {}, sources=sources)

    selected = substitute(value, {"callback": actual}, scope, sources, result, owner="choose")

    expected = (
        actual.join(BindingValue(deferred=True, local=True, unknown=True)) if residual else actual
    )
    assert selected == expected


@pytest.mark.parametrize("depth", [1, 6, 7, 12])
@pytest.mark.parametrize("native_fallback", [False, True])
def test_joined_returned_callable_preserves_independent_incompleteness(
    depth: int, *, native_fallback: bool
) -> None:
    """Joining a signature slot cannot erase a consumed deep source-call alternative."""
    source = "import subprocess as sp\ndef leaf(): return sp.run\n"
    for index in range(depth):
        target = "leaf" if index == 0 else f"relay_{index - 1}"
        source += f"def relay_{index}(): return {target}()\n"
    fallback = "sp.run" if native_fallback else "ValueError"
    source += (
        f"def choose(fallback, flag): return fallback if flag else relay_{depth - 1}()\n"
        f"def entry(): choose({fallback}, False)('joined_probe')\nentry()\nentry()\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert not flow.result.inputs
    assert flow.result.executables == {"joined_probe"} or flow.result.uncertainties
    if depth == 1 or native_fallback:
        assert flow.result.executables == {"joined_probe"}, flow.result


@pytest.mark.parametrize("repetitions", [1, 3])
@pytest.mark.parametrize("flag", [False, True])
def test_joined_parameter_callee_retains_native_effect(repetitions: int, *, flag: bool) -> None:
    """Source and signature alternatives survive dispatch before effect substitution."""
    source = (
        "import subprocess as sp\ndef noop(command): return None\n"
        "def entry(callback, flag):\n"
        "    (noop if flag else callback)(['branch_probe'])\n"
        + f"entry(sp.run, {flag})\n"
        * repetitions
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == (set() if flag else {"branch_probe"}), flow.result
    assert not flow.result.uncertainties, flow.result


@pytest.mark.parametrize("repetitions", [1, 3])
@pytest.mark.parametrize("flag", [False, True])
def test_joined_parameter_callee_retains_argument_custody(repetitions: int, *, flag: bool) -> None:
    """A selected callback's write reaches the later read without contaminating noop."""
    source = (
        "import subprocess as sp\ndef noop(container): return None\n"
        "def change(container): container['command'] = 'after_probe'\n"
        "state = {'command': 'before_probe'}\n"
        "def entry(callback, flag, container):\n"
        "    (noop if flag else callback)(container)\n"
        + f"entry(change, {flag}, state)\n" * repetitions
        + "sp.run([state['command']])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == ({"before_probe"} if flag else {"after_probe"}), flow.result
    assert not flow.result.uncertainties, flow.result


@pytest.mark.parametrize("wrapper", ["state", "(state,)", "{'nested': state}"])
@pytest.mark.parametrize("flag", [False, True])
def test_opaque_call_preserves_unmaterialized_return_custody(wrapper: str, *, flag: bool) -> None:
    """Missing current heap does not prove a lazy actual argument transfer-free."""
    source = (
        "import subprocess as sp\ndef factory():\n"
        "    return {'command': 'before_probe'}\n"
        "def entry(receiver, value, flag):\n    if flag: receiver.check(value)\n"
        f"state = factory()\nentry(receiver=opaque, value={wrapper}, flag={flag})\n"
        "sp.run([state['command']])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)
    assert any(item.state == "unknown" for item in flow.result.uncertainties) is flag
    if not flag:
        assert flow.result.executables == {"before_probe"}, flow.result


@pytest.mark.parametrize("receiver", ["local", "argument", "capture", "default"])
@pytest.mark.parametrize("repetitions", [1, 6])
@pytest.mark.parametrize("consume", [False, True])
def test_closed_native_mutation_follows_receiver_custody(
    monkeypatch: pytest.MonkeyPatch, receiver: str, repetitions: int, *, consume: bool
) -> None:
    """Local list writes do not replay; published writes and demanded contents remain real."""
    signature = (
        "values" if receiver == "argument" else "values=state" if receiver == "default" else ""
    )
    setup = (
        "    values = []\n"
        if receiver == "local"
        else "    values = state\n"
        if receiver == "capture"
        else ""
    )
    call = "produce(state)" if receiver == "argument" else "produce()"
    source = (
        "from dataclasses import dataclass\nimport subprocess as sp\n"
        "@dataclass(frozen=True, slots=True)\nclass Record:\n    command: str\nstate = []\n"
        f"def produce({signature}):\n{setup}"
        "    values.append(Record('stored_probe'))\n    return values\n" + f"{call}\n" * repetitions
    )
    if consume:
        source += (
            "value = produce()\nsp.run([value[0].command])\n"
            if receiver == "local"
            else "sp.run([state[0].command])\n"
        )
    observed: Counter[str] = Counter()
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        if not owner.summarizing:
            observed[getattr(invocation.definition.node, "name", "<lambda>")] += 1
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)
    assert flow.result.executables == ({"stored_probe"} if consume else set()), flow.result
    assert not flow.result.uncertainties, flow.result
    assert observed["produce"] == (int(consume) if receiver == "local" else repetitions), observed


@pytest.mark.parametrize("receiver", ["local", "external"])
def test_opaque_method_does_not_inherit_native_mutation_contract(receiver: str) -> None:
    """Only the native receiver may store a callback without invoking it."""
    source = (
        "from dataclasses import dataclass\nimport subprocess as sp\n"
        "@dataclass(frozen=True, slots=True)\nclass Record:\n    callback: object\n"
        "def produce(value):\n    value.append(Record(sp.run))\n"
        + ("produce([])\n" if receiver == "local" else "produce(external)\n")
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)
    assert any(item.state == "unknown" for item in flow.result.uncertainties) is (
        receiver == "external"
    )


def test_native_append_method_alternatives_have_weak_resource_updates() -> None:
    """An unselected method's receiver may retain its original empty state."""
    scope = BindingScope("probe.py")
    node, other = (
        statement.value
        for statement in ast.parse("left.append('value')\nright").body
        if isinstance(statement, ast.Expr)
    )
    assert isinstance(node, ast.Call)
    left = scope.aggregate(BindingValue(items=(), native_kind="list"), node)
    right = scope.aggregate(BindingValue(items=(), native_kind="list"), other)
    observer = PythonConsumption("probe.py", {})
    methods = frozenset({ReceiverMethod(left, "append"), ReceiverMethod(right, "append")})

    observer.receiver_returns(
        methods, (BindingValue(strings=frozenset({"value"})),), {}, node, scope
    )

    assert scope.resolve(left).truthiness() is None
    assert scope.resolve(right).truthiness() is None


@pytest.mark.parametrize("consume", [False, True])
@pytest.mark.parametrize("repetitions", [1, 6])
@pytest.mark.parametrize("unrelated_cutoff", [False, True])
def test_opaque_primitive_dispatch_is_replayed_only_when_its_result_is_demanded(
    monkeypatch: pytest.MonkeyPatch, repetitions: int, *, consume: bool, unrelated_cutoff: bool
) -> None:
    """A deferred opaque result is not a supported effect or published mutable footprint."""
    source = "import subprocess as sp\nstate = {}\ndef leaf(): return 'unused'\n"
    for index in range(12):
        target = "leaf" if index == 0 else f"relay_{index - 1}"
        source += f"def relay_{index}(): return {target}()\n"
    source += "def produce(value, untouched):\n"
    if unrelated_cutoff:
        source += "    relay_11()\n"
    source += "    return value.project('suffix')\n"
    source += "produce((value for value in opaque), state)\n" * repetitions
    if consume:
        source += "sp.run([produce((value for value in opaque), state)])\n"
    observed: Counter[str] = Counter()
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        if not owner.summarizing:
            observed[getattr(invocation.definition.node, "name", "<lambda>")] += 1
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)
    assert not flow.result.executables, flow.result
    assert bool(flow.result.uncertainties) is consume, flow.result
    assert observed["produce"] == int(consume), observed
