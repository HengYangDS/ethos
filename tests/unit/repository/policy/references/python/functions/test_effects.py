"""Parameterized source effects preserve callbacks without replaying pure helpers."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.bindings import BindingValue
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation


def test_pure_deferred_methods_do_not_replay_discarded_source_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A native Path receiver does not become an effectful callback by being deferred."""
    source = (
        "from pathlib import Path\n"
        "def local_path(value):\n"
        "    if not isinstance(value, str):\n"
        "        raise ValueError('type')\n"
        "    path = Path(value)\n"
        "    if path.is_absolute():\n"
        "        raise ValueError('absolute')\n"
        "    return path.as_posix()\n"
        "for item in ('one', 'two', 'three', 'four', 'five', 'six'):\n"
        "    local_path(item)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observed: list[str] = []
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        observed.append(getattr(invocation.definition.node, "name", "<lambda>"))
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == set()
    assert result.inputs == set()
    assert observed.count("local_path") == 1, observed


def test_native_scalar_validation_does_not_promote_type_objects_to_effects() -> None:
    """An opaque validation result cannot turn an immutable type argument into a write."""
    source = (
        "from pathlib import Path\n"
        "def validate(value):\n"
        "    if not isinstance(value, str):\n        raise ValueError('type')\n"
        "    return Path(value).as_posix()\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)
    definition = next(iter(sources.definitions.values()))

    sources.invocations.summarize(definition, flow.result)

    assert not sources.invocations.summaries[definition.key].direct


@pytest.mark.parametrize(
    "source",
    [
        (
            "import subprocess as sp\ndef apply(callback):\n"
            "    callback(['effect_probe_binary'])\napply(sp.run)\n"
        ),
        (
            "import subprocess as sp\ndef apply(module):\n"
            "    module.run(['effect_probe_binary'])\napply(sp)\n"
        ),
        (
            "import subprocess as sp\ndef leaf(command):\n    sp.run(command)\n"
            "def apply(callback, command):\n    callback(command)\n"
            "def relay(callback, command):\n    apply(callback, command)\n"
            "relay(leaf, ['effect_probe_binary'])\n"
        ),
        (
            "import subprocess as sp\ndef identity(callback):\n    return callback\n"
            "def apply(callback):\n    identity(callback)(['effect_probe_binary'])\n"
            "apply(sp.run)\n"
        ),
    ],
)
def test_source_callback_substitution_preserves_native_consumption(source: str) -> None:
    """Callable, member and transitive source dependencies retain actual bindings."""
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == {"effect_probe_binary"}, result


@pytest.mark.parametrize("opaque", [False, True])
def test_discarded_source_call_preserves_argument_footprint(*, opaque: bool) -> None:
    """A dropped return cannot drop a write or an opaque escape of its argument."""
    operation = "opaque(data)" if opaque else "data['command'] = ['effect_probe_binary']"
    source = (
        "import subprocess as sp\nshared = {'command': ['old_probe_binary']}\n"
        f"def update(data):\n    {operation}\n"
        "update(shared)\nsp.run(shared['command'])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    if opaque:
        assert any(item.state == "unknown" for item in result.uncertainties), result
    else:
        assert result.executables == {"effect_probe_binary"}, result


def test_lambda_return_transfers_newly_allocated_heap() -> None:
    """The same custody boundary applies to lambda and statement-function returns."""
    source = (
        "import subprocess as sp\n"
        "allocate = lambda: {'command': ['effect_probe_binary']}\n"
        "value = allocate()\nsp.run(value['command'])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == {"effect_probe_binary"}, result
    assert not any(item.state == "unknown" for item in result.uncertainties), result


@pytest.mark.parametrize("opaque", [False, True])
def test_exported_defaults_preserve_distinct_capture_custody(*, opaque: bool) -> None:
    """Each exported closure retains its own default and only its escaped state invalidates."""
    tail = "opaque(read_first)\n" if opaque else "state_first['key'] = 'changed_probe'\n"
    source = (
        "import subprocess as sp\n"
        "def make(value):\n"
        "    disposable = {'padding': ['unused_probe']}\n"
        "    state = {'key': value}\n"
        "    def read(saved=state):\n        return saved['key']\n"
        "    return read, state\n"
        "first = make('first_probe')\nread_first = first[0]\nstate_first = first[1]\n"
        "second = make('second_probe')\nread_second = second[0]\n"
        f"{tail}sp.run([read_first()])\nsp.run([read_second()])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    scope = flow.initialize(tree, source=source)

    assert "second_probe" in flow.result.executables, flow.result
    assert not any(getattr(key, "line", None) == 3 for key in scope.members)
    if opaque:
        assert any(item.state == "unknown" for item in flow.result.uncertainties), flow.result
        assert "first_probe" not in flow.result.executables, flow.result
    else:
        assert flow.result.executables == {"changed_probe", "second_probe"}, flow.result
        assert not flow.result.uncertainties, flow.result


def test_lazy_call_reads_each_capture_at_its_call_program_point() -> None:
    """Later consumption does not make earlier and later scalar calls identical."""
    source = (
        "import subprocess as sp\n"
        "state = {'key': 'before_probe'}\n"
        "def read(saved=state):\n    return saved['key']\n"
        "before = read()\nstate['key'] = 'after_probe'\nafter = read()\n"
        "sp.run([before])\nsp.run([after])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == {"before_probe", "after_probe"}, flow.result
    assert not flow.result.uncertainties, flow.result


def test_return_demand_does_not_force_unused_sibling_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selecting one pure return field does not calculate a sibling without an observer."""
    source = (
        "import subprocess as sp\n"
        "def identity(value):\n    return value\n"
        "def selection():\n"
        "    return identity('effect_probe_binary'), identity('unused_probe_binary')\n"
        "sp.run([selection()[0]])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observed: list[str] = []
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        if not owner.summarizing:
            observed.append(getattr(invocation.definition.node, "name", "<lambda>"))
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == {"effect_probe_binary"}, flow.result
    assert observed.count("identity") == 1, observed


@pytest.mark.parametrize("opaque", [False, True])
def test_exported_record_preserves_method_default_capture(*, opaque: bool) -> None:
    """Record methods retain default heaps and an opaque class escape cannot close them."""
    tail = "opaque(Record)" if opaque else "state['key'] = 'after_probe'"
    source = (
        "import subprocess as sp\nfrom dataclasses import dataclass\n"
        "def make(value):\n"
        "    state = {'key': value}\n"
        "    @dataclass(frozen=True)\n"
        "    class Selection:\n"
        "        executable: str\n"
        "        @classmethod\n"
        "        def read(cls, saved=state):\n            return cls(saved['key'])\n"
        "    return Selection, state\n"
        "bundle = make('before_probe')\nRecord = bundle[0]\nstate = bundle[1]\n"
        f"{tail}\nsp.run([Record.read().executable])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    if opaque:
        assert any(item.state == "unknown" for item in flow.result.uncertainties), flow.result
    else:
        assert flow.result.executables == {"after_probe"}, flow.result
        assert not flow.result.uncertainties, flow.result


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            (
                "import subprocess as sp\ndef noop(command):\n    return len(command)\n"
                "def apply(callback):\n    callback(['effect_probe_binary'])\n"
                "def relay():\n    apply(sp.run)\n    apply(noop)\nrelay()\n"
            ),
            {"effect_probe_binary"},
        ),
        (
            (
                "import subprocess as sp\ndef noop(command):\n    return len(command)\n"
                "def outer(callback):\n    saved = callback\n"
                "    def inner(callback):\n        saved(['effect_probe_binary'])\n"
                "    inner(noop)\nouter(sp.run)\n"
            ),
            {"effect_probe_binary"},
        ),
        (
            (
                "import subprocess as sp\ndef spread(*callbacks):\n"
                "    callbacks[0](['effect_probe_binary'])\nspread(sp.run)\n"
            ),
            {"effect_probe_binary"},
        ),
        (
            (
                "import subprocess as sp\nstate = {'key': 'before_probe'}\n"
                "def alias(saved=state):\n    return saved\n"
                "view = alias()\nsp.run([view['key']])\n"
                "state['key'] = 'after_probe'\nsp.run([view['key']])\n"
            ),
            {"before_probe", "after_probe"},
        ),
        (
            (
                "import subprocess as sp\ndef make():\n    value = 'before_probe'\n"
                "    def write():\n        nonlocal value\n        value = 'after_probe'\n"
                "    def read():\n        return value\n    return write, read\n"
                "pair = make()\nwrite = pair[0]\nread = pair[1]\nwrite()\nsp.run([read()])\n"
            ),
            {"after_probe"},
        ),
        (
            (
                "import subprocess as sp\nstate = {'key': 'before_probe'}\n"
                "def change(saved=state):\n    try:\n        saved['key'] = 'after_probe'\n"
                "        raise ValueError()\n    except ValueError:\n"
                "        sp.run([saved['key']])\nchange()\nsp.run([state['key']])\n"
            ),
            {"after_probe"},
        ),
    ],
)
def test_source_effect_composition_retains_binding_and_custody(
    source: str, expected: set[str]
) -> None:
    """Symbolic composition preserves each defining slot and live observation point."""
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == expected, flow.result


def test_summary_substitution_retains_cyclic_actual_without_expansion() -> None:
    """A symbolic container inserts a finite heap alias without recursively rewriting it."""
    source = (
        "import subprocess as sp\nshared = {'command': ['effect_probe_binary']}\n"
        "shared['self'] = shared\ndef escape(data):\n    opaque((data,))\n"
        "escape(shared)\nsp.run(shared['command'])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert any(item.state == "unknown" for item in flow.result.uncertainties), flow.result


def test_native_container_validation_does_not_replay_discarded_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proven native isinstance does not escape a mapping through unknown dispatch."""
    source = (
        "def validate(value):\n    if not isinstance(value, dict):\n"
        "        raise ValueError('type')\n    return value\n"
        "for item in ({'key': 'one'}, {'key': 'two'}, {'key': 'three'}):\n"
        "    validate(item)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observed: list[str] = []
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        observed.append(getattr(invocation.definition.node, "name", "<lambda>"))
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.observe(tree, source=source)

    assert observed.count("validate") == 1, observed


@pytest.mark.parametrize("nested", [False, True])
def test_effect_summary_reads_rebound_lexical_callback(*, nested: bool) -> None:
    """An earlier pure summary cannot hide a later call-time captured native effect."""
    body = (
        "def apply():\n    callback(['changed_callback_probe'])\n"
        if not nested
        else "def apply():\n    relay()\ndef relay():\n    callback(['changed_callback_probe'])\n"
    )
    source = (
        "import subprocess as sp\ndef noop(command):\n    return None\n"
        f"callback = noop\n{body}apply()\ncallback = sp.run\napply()\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == {"changed_callback_probe"}, flow.result
    assert not any(item.state == "unknown" for item in flow.result.uncertainties), flow.result


@pytest.mark.parametrize("alternative", ["external", "sp.run"])
def test_source_and_other_call_alternatives_preserve_outgoing_effects(
    alternative: str,
) -> None:
    """A source branch never erases a native effect or opaque argument escape."""
    argument = "state" if alternative == "external" else "['native_alternative_probe']"
    source = (
        "import subprocess as sp\ndef noop(value):\n    return None\n"
        "state = {'key': 'known_probe'}\n"
        f"callback = noop if flag else {alternative}\ncallback({argument})\n"
        "sp.run([state['key']])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    if alternative == "external":
        assert any(item.state == "unknown" for item in flow.result.uncertainties), flow.result
    else:
        assert flow.result.executables == {"native_alternative_probe", "known_probe"}, flow.result


def test_returned_heap_and_scalar_keep_distinct_consumption_program_points() -> None:
    """Live heap aliases refresh while saved scalars retain their call-time binding."""
    source = (
        "import subprocess as sp\nstate = {'key': 'before_probe'}\n"
        "def heap():\n    return state\ndef scalar():\n    return state['key']\n"
        "view = heap()\nsaved = scalar()\nsp.run([view['key']])\n"
        "state['key'] = 'after_probe'\nsp.run([view['key']])\n"
        "sp.run([saved])\nsp.run([scalar()])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(ast.Module(body=[], type_ignores=[]), source=source)
    consumed = []

    for statement in tree.body:
        flow.block([statement], scope)
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            consumed.append(set(flow.result.executables))
            flow.result.executables.clear()

    assert consumed == [{"before_probe"}, {"after_probe"}, {"before_probe"}, {"after_probe"}]


@pytest.mark.parametrize("opaque", [False, True])
def test_alternative_return_custody_retains_each_source_result(*, opaque: bool) -> None:
    """Branch-local allocations survive projection without closing an opaque branch."""
    second = "external" if opaque else "second"
    source = (
        "import subprocess as sp\ndef first():\n    return {'key': 'first_probe'}\n"
        "def second():\n    return {'key': 'second_probe'}\n"
        f"selected = first if flag else {second}\nview = selected()\n"
        "sp.run([view['key']])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == (
        {"first_probe"} if opaque else {"first_probe", "second_probe"}
    )
    assert any(item.state == "unknown" for item in flow.result.uncertainties) is opaque


@pytest.mark.parametrize("alternative", [False, True])
def test_source_global_write_joins_alternative_effect_cells(*, alternative: bool) -> None:
    """A call publishes owned cell deltas, not a stale full lexical snapshot."""
    selected = "write if flag else noop" if alternative else "write"
    source = (
        "import subprocess as sp\ncommand = 'old_probe'\n"
        "def write():\n    global command\n    command = 'new_probe'\n"
        "def noop():\n    return None\n"
        f"selected = {selected}\nselected()\nsp.run([command])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == ({"old_probe", "new_probe"} if alternative else {"new_probe"})


@pytest.mark.parametrize("selected_member", [False, True])
def test_cached_return_depends_only_on_consumed_heap_members(
    monkeypatch: pytest.MonkeyPatch, *, selected_member: bool
) -> None:
    """Consumed nested cells invalidate reuse; a disjoint sibling cannot force replay."""
    member = "selected" if selected_member else "sibling"
    source = (
        "import subprocess as sp\ndef noop(command):\n    return None\n"
        "state = {'selected': {'callback': noop}, 'sibling': {'callback': noop}}\n"
        "def choose():\n    return state['selected']['callback']\n"
        "def apply():\n    choose()(['nested_callback_probe'])\n"
        f"apply()\nstate['{member}']['callback'] = sp.run\napply()\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    observed = []
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        observed.append(
            (getattr(invocation.definition.node, "name", "<lambda>"), bool(owner.summarizing))
        )
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    flow.initialize(tree, source=source)

    assert flow.result.executables == ({"nested_callback_probe"} if selected_member else set())
    if not selected_member:
        assert observed.count(("choose", True)) == 1, observed


@pytest.mark.parametrize("count", [1, 6])
@pytest.mark.parametrize("expanded", [False, True])
@pytest.mark.parametrize("native_read", [False, True])
def test_discarded_comprehension_calls_reuse_invocation_owned_bindings(
    monkeypatch: pytest.MonkeyPatch,
    count: int,
    *,
    expanded: bool,
    native_read: bool,
) -> None:
    """A yielded element is not call expansion or a capture from the module."""
    sequence = "(*receiver['inputs'], *receiver['outputs'])" if expanded else "receiver['inputs']"
    if native_read:
        sequence = sequence.replace("receiver['inputs']", "receiver.get('inputs')").replace(
            "receiver['outputs']", "receiver.get('outputs')"
        )
    source = (
        "def leaf(value):\n    return value\n"
        f"def helper(receiver):\n    return tuple(leaf(item) for item in {sequence})\n"
        + "helper({'inputs': ('one',), 'outputs': ('two',)})\n"
        * count
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observed = []
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        observed.append(
            (getattr(invocation.definition.node, "name", "<lambda>"), bool(owner.summarizing))
        )
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    expected = [("helper", True), ("leaf", True)]
    assert sorted(observed) == sorted(expected), observed
    assert not flow.result.uncertainties, flow.result


@pytest.mark.parametrize("mutating", [False, True])
@pytest.mark.parametrize("opaque", [False, True])
def test_source_receiver_effect_keeps_native_custody(*, mutating: bool, opaque: bool) -> None:
    """Native read-only access stays pure; unsupported mutation cannot leave false GREEN."""
    operation = "update({'command': ['after_probe']})" if mutating else "get('command')"
    selected = "state if flag else external" if opaque else "state"
    source = (
        "import subprocess as sp\n"
        f"def helper(receiver):\n    receiver.{operation}\n"
        f"state = {{'command': ['before_probe']}}\nhelper({selected})\nsp.run(state['command'])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert any(item.state == "unknown" for item in flow.result.uncertainties) is (
        mutating or opaque
    )
    if not (mutating or opaque):
        assert flow.result.executables == {"before_probe"}, flow.result


@pytest.mark.parametrize("mutable", [False, True])
@pytest.mark.parametrize("flag", [False, True])
@pytest.mark.parametrize("fresh_return", [False, True])
def test_unknown_call_replays_only_reachable_state_transfer(
    monkeypatch: pytest.MonkeyPatch, *, mutable: bool, flag: bool, fresh_return: bool
) -> None:
    """Stable unknown dispatch is not purity; guarded mutable custody still replays."""
    value = "{'command': 'before_probe'}" if mutable else "'before_probe'"
    command = "state['command']" if mutable else "state"
    returned = "    return {'value': value}\n" if fresh_return else ""
    source = (
        "import subprocess as sp\ndef entry(receiver, value, flag):\n"
        "    if flag: receiver.check(value)\n"
        f"{returned}state = {value}\n"
        + f"entry(opaque, state, {flag})\n" * 3
        + f"sp.run([{command}])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observed: list[str] = []
    evaluate = PythonInvocations.evaluate

    def counted(
        owner: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        observed.append(getattr(invocation.definition.node, "name", "<lambda>"))
        return evaluate(owner, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)
    assert (observed.count("entry") == 1) is not mutable, observed
    assert any(item.state == "unknown" for item in flow.result.uncertainties) is (mutable and flag)
    if not (mutable and flag):
        assert flow.result.executables == {"before_probe"}, flow.result
