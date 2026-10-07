"""Scope-qualified graph traversal expands heap edges once without discarding aliases."""

from __future__ import annotations

import ast
import inspect
from collections import Counter

import pytest

from ethos.repository.policy.references.python.bindings import AggregateIdentity
from ethos.repository.policy.references.python.bindings import BindingScope
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ReturnProjection
from ethos.repository.policy.references.python.control import FlowExit
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.custody import InvocationCustody
from ethos.repository.policy.references.python.functions.invocation import SourceInvocation
from ethos.repository.policy.references.python.functions.returns import FunctionDefinition
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns
from ethos.repository.policy.references.python.syntax import NativeScopes


@pytest.mark.parametrize("aliases", [2, 16])
@pytest.mark.parametrize("later", [None, False, True])
def test_heap_edges_expand_once_per_identity_and_scope(
    monkeypatch: pytest.MonkeyPatch, aliases: int, *, later: bool | None
) -> None:
    """Repeated aliases share heap edges while distinct inline edges and owners survive."""
    root = AggregateIdentity("owner", 1, 0)
    child = AggregateIdentity("owner", 2, 0)
    inline = tuple(AggregateIdentity("owner", index + 3, 0) for index in range(aliases))
    child_value = BindingValue(aggregates=frozenset({child}))
    owners = (
        BindingScope("first", members={root: child_value}, member_history={root: child_value}),
        BindingScope("second", members={root: child_value}, member_history={root: child_value}),
    )
    roots = [
        (
            BindingValue(
                aggregates=frozenset({root}),
                items=(BindingValue(aggregates=frozenset({identity})),),
            ),
            owner,
        )
        for owner in owners
        for identity in inline
    ]
    expansions: Counter[tuple[AggregateIdentity, int]] = Counter()
    member_values = InvocationCustody.member_values

    def counted(
        key: AggregateIdentity,
        source: BindingScope,
        target: BindingScope | None,
        *,
        later: bool | None,
    ) -> tuple[BindingValue, ...]:
        expansions[(key, id(source))] += 1
        return member_values(key, source, target, later=later)

    monkeypatch.setattr(InvocationCustody, "member_values", staticmethod(counted))
    sources = PythonSourceReturns({}, {}, PythonReferenceFlow)
    retained = sources.invocations.custody.reachable(roots, later=later)

    assert set(retained) == {root, child, *inline}
    assert all(set(witnesses) == {id(owner) for owner in owners} for witnesses in retained.values())
    assert set(expansions.values()) == {1}, expansions


@pytest.mark.parametrize("aliases", [2, 16])
@pytest.mark.parametrize("state", ["pending", "returned", "unknown"])
def test_return_request_edges_expand_once_without_losing_inline_owners(
    aliases: int, state: str
) -> None:
    """Aliases share fixed request custody; inline siblings and a later read remain distinct."""
    source = "def select(value=None, *, option):\n    return value\n"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.FunctionDef)
    sources = PythonSourceReturns({}, {}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.lexical = NativeScopes.from_source(source, "probe.py")
    argument, keyword, returned, capture = (
        AggregateIdentity("request", index, 0) for index in range(4)
    )
    preserved = BindingValue(strings=frozenset({"retained_probe"}))
    caller = BindingScope(
        "caller", members={argument: preserved, keyword: preserved, returned: preserved}
    )
    parent = BindingScope(
        "captured", values={"value": BindingValue(aggregates=frozenset({capture}))}
    )
    definition = sources.definition(
        flow, node, parent, (BindingValue(aggregates=frozenset({capture})),), (None,)
    )
    call = ast.parse("select(value, option=value)", mode="eval").body
    assert isinstance(call, ast.Call)
    request = SourceInvocation(
        sources.definitions[next(iter(definition.targets))],
        (BindingValue(aggregates=frozenset({argument})),),
        {"option": BindingValue(aggregates=frozenset({keyword}))},
        call,
        caller,
        parent,
    )
    if state != "pending":
        request.returned = BindingValue(
            aggregates=frozenset({returned}), unknown=state == "unknown"
        )
    reads: list[int] = []

    class Requests(list[SourceInvocation]):
        def __getitem__(self, index):
            reads.append(index)
            return super().__getitem__(index)

    sources.invocations.requests = Requests([request])
    owners = (BindingScope("first"), BindingScope("second"))
    inline = tuple(AggregateIdentity("inline", index, 0) for index in range(aliases))
    roots = [
        (
            BindingValue(
                projections=frozenset({ReturnProjection(0)}),
                items=(BindingValue(aggregates=frozenset({identity})),),
            ),
            owner,
        )
        for owner in owners
        for identity in inline
    ]
    expected = {argument, keyword, capture, *inline}
    if state != "pending":
        expected.add(returned)
    retained = sources.invocations.custody.reachable(roots)
    assert set(retained) == expected
    assert set(retained[argument]) == {id(caller)}
    assert set(retained[keyword]) == {id(caller)}
    assert set(retained[capture]) == {id(parent)}
    assert all(set(retained[identity]) == {id(owner) for owner in owners} for identity in inline)
    assert reads == [0], reads
    request.returned = BindingValue(aggregates=frozenset({returned}))
    assert returned in sources.invocations.custody.reachable(roots)
    assert reads == [0, 0]


@pytest.mark.parametrize(
    "value",
    [
        BindingValue(),
        BindingValue(strings=frozenset({"literal"})),
        BindingValue(targets=frozenset({"native.module"}), unknown=True),
        BindingValue(aggregates=frozenset({AggregateIdentity("owner", 1, 0)})),
    ],
)
def test_already_normalized_witness_preserves_identity(value: BindingValue) -> None:
    """A dependency with no mutable shape needs no replacement allocation."""
    assert InvocationCustody.witness(value) is value


def test_witness_preserves_inline_shape_and_erases_mutable_shape() -> None:
    """Structural sharing must not retain copied contents as live heap evidence."""
    leaf = BindingValue(strings=frozenset({"value"}))
    immutable = BindingValue(items=(leaf,), entries=(("key", leaf),), element=leaf)
    mutable = BindingValue(
        aggregates=frozenset({AggregateIdentity("owner", 1, 0)}),
        items=(leaf,),
        entries=(("key", leaf),),
        fields=(("field", leaf),),
        element=leaf,
    )
    assert InvocationCustody.witness(immutable) == immutable
    assert InvocationCustody.witness(mutable) == BindingValue(aggregates=mutable.aggregates)


@pytest.mark.parametrize("unrelated", [2, 64])
def test_transfer_does_not_expand_inert_ambient_heap(
    monkeypatch: pytest.MonkeyPatch, unrelated: int
) -> None:
    """An effectful leaf exports no unrelated allocations while retaining its native effect."""
    source = "import subprocess as sp\ndef perform():\n    sp.run(('selected_probe',))\n"
    source += "".join(f"padding_{index} = [['unused_probe']]\n" for index in range(unrelated))
    source += "perform()\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    transfer = InvocationCustody.transfer
    member_values = InvocationCustody.member_values
    expansions: list[int] = []
    active = False
    count = 0

    def counted(
        key: AggregateIdentity,
        scope: BindingScope,
        target: BindingScope | None,
        *,
        later: bool | None,
    ) -> tuple[BindingValue, ...]:
        nonlocal count
        count += active
        return member_values(key, scope, target, later=later)

    def tracked(
        custody: InvocationCustody,
        invocation: SourceInvocation,
        paths: tuple[FlowExit, ...],
        returned: BindingValue,
    ) -> None:
        nonlocal active, count
        active, count = True, 0
        try:
            transfer(custody, invocation, paths, returned)
        finally:
            active = False
        expansions.append(count)

    monkeypatch.setattr(InvocationCustody, "member_values", staticmethod(counted))
    monkeypatch.setattr(InvocationCustody, "transfer", tracked)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == {"selected_probe"}, result
    assert not result.uncertainties, result
    assert expansions
    assert all(count == 0 for count in expansions), expansions


@pytest.mark.parametrize("install", ["history", "during"])
@pytest.mark.parametrize("lineage", ["same", "unproved"])
def test_transfer_retains_missing_default_custody(install: str, lineage: str) -> None:
    """Unchanged backing cannot hide a foreign callable's absent default allocation."""
    source = "def idle():\n    return\ndef foreign(saved=None):\n    return saved\n"
    tree = ast.parse(source)
    idle_node, foreign_node = tree.body
    assert isinstance(idle_node, ast.FunctionDef)
    assert isinstance(foreign_node, ast.FunctionDef)
    sources = PythonSourceReturns({}, {}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.lexical = NativeScopes.from_source(source, "probe.py")
    root = AggregateIdentity("caller", 1, 0)
    backing = AggregateIdentity("caller", 2, 0)
    capture = AggregateIdentity("foreign", 3, 0)
    scalar = BindingValue(strings=frozenset({"stable"}))
    preserved = BindingValue(strings=frozenset({"captured_probe"}))
    foreign = BindingScope(
        "foreign", members={capture: preserved}, member_history={capture: preserved}
    )
    signature = inspect.Signature(
        [
            inspect.Parameter(
                "saved",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=BindingValue(aggregates=frozenset({capture})),
            )
        ]
    )
    foreign_value = sources.definition(flow, foreign_node, foreign, (), ())
    foreign_key = next(iter(foreign_value.targets))
    sources.definitions[foreign_key] = FunctionDefinition(
        foreign_key, foreign_node, flow, foreign, signature
    )
    caller = BindingScope(
        "caller",
        members={
            root: BindingValue(items=(BindingValue(aggregates=frozenset({backing})),)),
            backing: scalar,
        },
        member_history={
            root: BindingValue(items=(BindingValue(aggregates=frozenset({backing})),)),
            backing: foreign_value if install == "history" else scalar,
        },
    )
    idle = sources.definition(flow, idle_node, caller, (), ())
    definition = sources.definitions[next(iter(idle.targets))]
    call = ast.parse("idle()", mode="eval").body
    assert isinstance(call, ast.Call)
    invocation = SourceInvocation(definition, (), {}, call, caller, caller.fork())
    child = BindingScope(
        "caller.idle",
        parent=invocation.parent,
        members=dict(invocation.state.members),
        member_history=dict(invocation.state.member_history),
    )
    child.member_base = invocation.state if lineage == "same" else caller.fork()
    if install == "during":
        child.member_history[backing] = foreign_value

    sources.invocations.custody.transfer(invocation, (FlowExit(child),), BindingValue(local=True))

    assert caller.member_binding(capture) == preserved
    assert caller.member_binding(capture, later=True) == preserved


def test_transfer_preserves_live_branch_and_summarized_obligations() -> None:
    """No-op branches retain fresh caller data; weak-update facts cannot disappear."""
    source = "def idle():\n    return\n"
    tree = ast.parse(source)
    idle_node = tree.body[0]
    assert isinstance(idle_node, ast.FunctionDef)
    sources = PythonSourceReturns({}, {}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.lexical = NativeScopes.from_source(source, "probe.py")
    identity = AggregateIdentity("caller", 1, 0)
    initial = BindingValue(strings=frozenset({"before"}))
    live = BindingValue(strings=frozenset({"live"}))
    changed = BindingValue(strings=frozenset({"changed"}))
    caller = BindingScope("caller", members={identity: initial}, member_history={identity: initial})
    idle = sources.definition(flow, idle_node, caller, (), ())
    definition = sources.definitions[next(iter(idle.targets))]
    call = ast.parse("idle()", mode="eval").body
    assert isinstance(call, ast.Call)
    invocation = SourceInvocation(definition, (), {}, call, caller, caller.fork())
    unchanged = BindingScope(
        "caller.idle",
        parent=invocation.parent,
        members=dict(invocation.state.members),
        member_history=dict(invocation.state.member_history),
    )
    unchanged.member_base = invocation.state
    effect = unchanged.fork()
    effect.assign_member(identity, changed)
    unchanged.summarized.add(identity)
    caller.assign_member(identity, live)

    sources.invocations.custody.transfer(
        invocation, (FlowExit(unchanged), FlowExit(effect)), BindingValue(local=True)
    )

    assert caller.member(identity).strings == {"live", "changed"}
    assert caller.member(identity, later=True).strings == {"before", "live", "changed"}
    assert identity in caller.summarized


@pytest.mark.parametrize("present", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_branch_merge_preserves_presence_sensitive_unknown(*, present: bool, reverse: bool) -> None:
    """Present empty facts are real bindings; only an absent branch needs UNKNOWN."""
    empty = BindingValue()
    left = BindingScope("left", values={"value": empty}, history={"value": empty})
    right = BindingScope(
        "right",
        values={"value": empty} if present else {},
        history={"value": empty} if present else {},
    )
    merged = BindingScope("merged")
    merged.merge(*(right, left) if reverse else (left, right))

    assert merged.values["value"].unknown is not present
    assert merged.history["value"].unknown is not present


@pytest.mark.parametrize("count", [2, 16])
@pytest.mark.parametrize("shared_base", [False, True])
def test_branch_merge_reuses_equal_facts_without_rejoining(
    monkeypatch: pytest.MonkeyPatch, count: int, *, shared_base: bool
) -> None:
    """Equal branch facts share immutable values, not mutable environment dictionaries."""
    identity = AggregateIdentity("caller", 1, 0)
    base = BindingScope("base")
    branches = tuple(
        BindingScope(
            "branch",
            values={"value": BindingValue(strings=frozenset({"stable"}))},
            history={"value": BindingValue(strings=frozenset({"stable"}))},
            members={identity: BindingValue(unknown=True)},
            member_history={identity: BindingValue()},
            member_base=base if shared_base else BindingScope("separate"),
            summarized={identity},
        )
        for _ in range(count)
    )
    merged = BindingScope("merged")
    joined: list[tuple[BindingValue, BindingValue]] = []
    join = BindingValue.join

    def counted(left: BindingValue, right: BindingValue) -> BindingValue:
        joined.append((left, right))
        return join(left, right)

    monkeypatch.setattr(BindingValue, "join", counted)
    merged.merge(*branches)

    assert joined == []
    assert merged.member_base is (base if shared_base else None)
    assert merged.summarized == {identity}
    for name in ("values", "history", "members", "member_history"):
        mapping = getattr(merged, name)
        assert all(mapping == getattr(branch, name) for branch in branches)
        assert all(mapping is not getattr(branch, name) for branch in branches)
        mapping.clear()
        assert all(getattr(branch, name) for branch in branches)


def test_branch_merge_rejoins_only_changed_fact_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    """A changed lexical channel preserves its may-values without rescanning stable history."""
    left = BindingScope(
        "left",
        values={"value": BindingValue(strings=frozenset({"left"}))},
        history={"value": BindingValue(strings=frozenset({"shared"}))},
    )
    right = BindingScope(
        "right",
        values={"value": BindingValue(strings=frozenset({"right"}))},
        history={"value": BindingValue(strings=frozenset({"shared"}))},
    )
    merged = BindingScope("merged")
    joined: list[tuple[BindingValue, BindingValue]] = []
    join = BindingValue.join

    def counted(first: BindingValue, second: BindingValue) -> BindingValue:
        joined.append((first, second))
        return join(first, second)

    monkeypatch.setattr(BindingValue, "join", counted)
    merged.merge(left, right)

    assert joined == [(left.values["value"], right.values["value"])]
    assert merged.values["value"].strings == {"left", "right"}
    assert merged.history["value"].strings == {"shared"}
