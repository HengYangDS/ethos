"""Bounded source return relationships reach the public semantic consumer."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation
    from ethos.repository.policy.references.python.scope import BindingScope


@pytest.mark.parametrize("name", ["select", "renamed_selector"])
def test_public_closure_preserves_source_return_identity(tmp_path: Path, name: str) -> None:
    """Imported names and aliases preserve the exact body, not spelling-based trust."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/selector.py",
        f'def {name}(argument):\n    return ["binding_probe_binary", argument]\n',
    )
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        f"import subprocess\nfrom example.selector import {name} as picked\n"
        'subprocess.run(picked("input"))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}


@pytest.mark.parametrize("opaque", [False, True])
def test_public_closure_keeps_record_field_provenance(tmp_path: Path, *, opaque: bool) -> None:
    """Frozen native records transport fields; opaque replacement stays UNKNOWN."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    source = (
        "from dataclasses import dataclass\nfrom pathlib import Path\n"
        "@dataclass(frozen=True)\nclass Selection:\n    executable: Path\n"
        'def choose(root):\n    return Selection(Path(root) / "binding_probe_binary")\n'
    )
    if opaque:
        source += "choose = external_factory\n"
    write_reference_source(tmp_path, "src/example/selector.py", source)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\nfrom example.selector import choose\n"
        "def run(root):\n    selected = choose(root)\n"
        '    subprocess.run([selected.executable, "--version"])\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == ("unknown" if opaque else "partial"), report
    assert report["verdict"] == ("unknown" if opaque else "block"), report
    if not opaque:
        assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}


@pytest.mark.parametrize("body", ["return opaque(argument)", "return choose(argument)"])
def test_public_closure_does_not_close_unsupported_return(tmp_path: Path, body: str) -> None:
    """Opaque dispatch and recursion cannot inherit parameter-only coverage."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n" + f"def choose(argument):\n    {body}\n"
        "def consume(argument):\n    subprocess.run(choose(argument))\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] == "unknown", report
    assert any(item["state"] == "unknown" for item in report["uncertainties"])


def test_public_closure_keeps_wrapper_input_uncertainty(tmp_path: Path) -> None:
    """A source wrapper cannot turn an opaque command into a deferred parameter."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\ndef execute(command):\n    subprocess.run(command)\n"
        "def consume(parameter):\n    execute(factory(parameter))\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] == "unknown", report


@pytest.mark.parametrize(
    ("body", "identities"),
    [
        (
            'if argument:\n        return ["first_probe"]\n    return ["second_probe"]',
            {"first_probe", "second_probe"},
        ),
    ],
)
def test_public_closure_observes_successful_return_paths(
    tmp_path: Path, body: str, identities: set[str]
) -> None:
    """All successful exits contribute, while a final return replaces an earlier one."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        f"def choose(argument):\n    {body}\n"
        "def consume(argument):\n    subprocess.run(choose(argument))\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == identities


def test_reference_flow_preserves_final_return_override() -> None:
    """Exit projection remains correct; compiler warnings are a separate public boundary."""
    path = "src/example/probe.py"
    source = (
        "import subprocess\ndef choose(argument):\n    try:\n"
        '        return ["discarded_probe"]\n    finally:\n'
        '        return ["binding_probe_binary"]\n'
        "def consume(argument):\n    subprocess.run(choose(argument))\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({path: source}, {path: tree}, PythonReferenceFlow)

    observed = PythonReferenceFlow(path, {}, sources=sources).observe(tree, source=source)

    assert observed.executables == {"binding_probe_binary"}
    assert not observed.uncertainties


@pytest.mark.parametrize(
    "source",
    [
        'def choose(root):\n    return root / "binding_probe_binary"\n',
        (
            'def choose(root):\n    result = ["binding_probe_binary"]\n'
            "    try:\n        return result\n    finally:\n        mutate(result)\n"
        ),
        (
            "from dataclasses import dataclass\nfrom pathlib import Path\n"
            "@dataclass(frozen=True)\nclass Selection:\n    executable: Path\n"
            'def choose(root):\n    selected = Selection(Path(root) / "binding_probe_binary")\n'
            "    alias = selected\n    mutate(alias)\n    return [selected.executable]\n"
        ),
    ],
)
def test_public_closure_keeps_return_mutation_and_dispatch_unknown(
    tmp_path: Path, source: str
) -> None:
    """Opaque operators and relevant mutation cannot inherit a closed command."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n" + source + "def consume(root):\n    subprocess.run(choose(root))\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] == "unknown", report


@pytest.mark.parametrize("subclass", [False, True])
def test_public_closure_binds_actual_record_receiver(tmp_path: Path, *, subclass: bool) -> None:
    """Native classmethod construction binds its receiver; custom subclasses stay opaque."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    source = (
        "import subprocess\nfrom dataclasses import dataclass\nfrom pathlib import Path\n"
        "@dataclass(frozen=True)\nclass Selection:\n    executable: Path\n"
        "    @classmethod\n    def read(cls, root):\n"
        '        return cls(Path(root) / "binding_probe_binary")\n'
    )
    if subclass:
        source += "class Custom(Selection):\n    pass\n"
    receiver = "Custom" if subclass else "Selection"
    source += (
        f"def consume(root):\n    selected = {receiver}.read(root)\n"
        "    subprocess.run([selected.executable])\n"
    )
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == ("unknown" if subclass else "partial"), report
    assert report["verdict"] == ("unknown" if subclass else "block"), report
    if not subclass:
        assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}


def test_public_closure_keeps_leading_named_record_field(tmp_path: Path) -> None:
    """Unknown trailing expansion does not change a proven leading field on successful exits."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\nfrom typing import NamedTuple\nfrom pathlib import Path\n"
        "class Selection(NamedTuple):\n    executable: Path\n    other: str\n"
        "def consume(root, remainder):\n"
        '    selected = Selection(Path(root) / "binding_probe_binary", *remainder)\n'
        "    subprocess.run([selected.executable])\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "partial", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}


@pytest.mark.parametrize(
    "access", ["from example.selector import Selection", "import example.selector as selected"]
)
def test_public_closure_preserves_imported_record_method(tmp_path: Path, access: str) -> None:
    """Class method lookup uses its actual defining scope through either import carrier."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/selector.py",
        "from dataclasses import dataclass\nfrom pathlib import Path\n"
        "@dataclass(frozen=True)\nclass Selection:\n    executable: Path\n"
        "    @classmethod\n    def read(receiver, root):\n"
        '        return receiver(Path(root) / "binding_probe_binary")\n',
    )
    owner = "Selection" if access.startswith("from") else "selected.Selection"
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        f"import subprocess\n{access}\ndef consume(root):\n"
        f"    subprocess.run([{owner}.read(root).executable])\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "partial", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}


@pytest.mark.parametrize(
    "body",
    [
        (
            "selected = Selection if condition else external_class\n"
            "    return selected.read(root).executable"
        ),
        (
            'selected = Selection(Path(root) / "binding_probe_binary")\n'
            "    with external_context:\n        return selected.executable"
        ),
    ],
)
def test_public_closure_preserves_opaque_record_paths(tmp_path: Path, body: str) -> None:
    """Mixed receiver alternatives and unmodeled context protocols retain UNKNOWN."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\nfrom dataclasses import dataclass\nfrom pathlib import Path\n"
        "@dataclass(frozen=True)\nclass Selection:\n    executable: Path\n"
        "    @classmethod\n    def read(receiver, root):\n"
        '        return receiver(Path(root) / "binding_probe_binary")\n'
        f"def choose(root):\n    {body}\n"
        "def consume(root):\n    subprocess.run([choose(root)])\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report


@pytest.mark.parametrize("suffix", ["", "."])
def test_public_closure_keeps_native_lookup_through_identity_path(
    tmp_path: Path, suffix: str
) -> None:
    """Identity suffixes preserve native lookup provenance instead of inventing a new binary."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess, shutil\nfrom pathlib import Path\n"
        'found = shutil.which("binding_probe_binary")\n'
        f"if found:\n    subprocess.run([Path(found) / {suffix!r}])\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}


def test_public_closure_does_not_close_parent_path_traversal(tmp_path: Path) -> None:
    """A parent component cannot become an executable identity from its own spelling."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess, shutil\nfrom pathlib import Path\n"
        'found = shutil.which("binding_probe_binary")\n'
        'if found:\n    subprocess.run([Path(found) / ".."])\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert not report["orphan"], report


@pytest.mark.parametrize("opaque", [False, True])
def test_source_invocation_preserves_escaping_alias_without_private_heap(*, opaque: bool) -> None:
    """Repeated helpers preserve captured aliases without exporting disposable allocations."""
    path = "src/example/probe.py"
    mutation = "mutate(command)" if opaque else 'command["key"] = "after_probe"'
    source = (
        "import subprocess\n"
        "def build(command):\n"
        '    disposable = {"padding": ["unused_probe"]}\n'
        '    def later():\n        return [command["key"]]\n'
        "    return later\n"
        'command = {"key": "before_probe"}\n'
        "for index in (0, 1, 2, 3):\n    selected = build(command)\n"
        f"{mutation}\nsubprocess.run(selected())\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({path: source}, {path: tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow(path, {}, sources=sources)

    scope = flow.initialize(tree, source=source)

    assert flow.result.executables == (set() if opaque else {"after_probe"})
    assert bool(flow.result.uncertainties) == opaque
    assert not any(getattr(key, "line", None) == 3 for key in scope.members)


@pytest.mark.parametrize("mixed", [False, True])
def test_native_and_source_receiver_alternatives_preserve_outgoing_effects(*, mixed: bool) -> None:
    """Refreshing mapping contents cannot erase a source method selected on another branch."""
    receiver = "state if flag else Reader" if mixed else "Reader"
    source = (
        "import subprocess as sp\nfrom dataclasses import dataclass\n"
        "@dataclass(frozen=True)\nclass Reader:\n"
        "    @classmethod\n    def get(cls, key):\n"
        "        sp.run(['branch_probe'])\n        return ['before_probe']\n"
        "state = {'command': ['before_probe']}\n"
        f"selected = {receiver}\nselected.get('command')\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert "branch_probe" in flow.result.executables, flow.result


@pytest.mark.parametrize("detached", [False, True])
@pytest.mark.parametrize("mutating", [False, True])
def test_receiver_method_assignment_preserves_native_custody(
    *, detached: bool, mutating: bool
) -> None:
    """Saving a method retains its receiver; it does not turn a mutation into a pure call."""
    member = "update" if mutating else "get"
    argument = "{'command': ['after_probe']}" if mutating else "'command'"
    operation = (
        f"    method = receiver.{member}\n    method({argument})\n"
        if detached
        else f"    receiver.{member}({argument})\n"
    )
    source = (
        "import subprocess as sp\ndef helper(receiver):\n"
        f"{operation}state = {{'command': ['before_probe']}}\n"
        "helper(state)\nsp.run(state['command'])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert any(item.state == "unknown" for item in flow.result.uncertainties) == mutating
    if not mutating:
        assert flow.result.executables == {"before_probe"}, flow.result


@pytest.mark.parametrize("access", ["saved", "returned", "tuple", "mapping", "getattr"])
@pytest.mark.parametrize("mutating", [False, True])
def test_native_method_transport_preserves_receiver_relationship(
    access: str, *, mutating: bool
) -> None:
    """Assignment, return and container transport retain the same native method contract."""
    member = "update" if mutating else "get"
    argument = "{'command': ['after_probe']}" if mutating else "'command'"
    setup = {
        "saved": f"method = state.{member}\n",
        "returned": (
            f"def select(receiver):\n    return receiver.{member}\nmethod = select(state)\n"
        ),
        "tuple": f"holder = (state.{member},)\nmethod = holder[0]\n",
        "mapping": f"holder = {{'call': state.{member}}}\nmethod = holder['call']\n",
        "getattr": f"method = getattr(state, '{member}')\n",
    }[access]
    source = (
        "import subprocess as sp\nstate = {'command': ['before_probe']}\n"
        f"{setup}method({argument})\nsp.run(state['command'])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert any(item.state == "unknown" for item in flow.result.uncertainties) == mutating
    if not mutating:
        assert flow.result.executables == {"before_probe"}, flow.result


@pytest.mark.parametrize("mutating", [False, True])
def test_native_method_lookup_precedes_arguments_but_reads_current_heap(*, mutating: bool) -> None:
    """A saved receiver is not retargeted; its contents reflect argument-time mutation."""
    mutation = "    state['command'] = ['after_probe']\n" if mutating else ""
    source = (
        "import subprocess as sp\nstate = {'command': ['before_probe']}\n"
        f"def rewrite():\n{mutation}    return 'command'\n"
        "method = state.get\nsp.run(method(rewrite()))\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == ({"after_probe"} if mutating else {"before_probe"}), (
        flow.result
    )
    assert not flow.result.uncertainties, flow.result


def test_opaque_escape_of_saved_native_method_invalidates_only_its_receiver() -> None:
    """A bound method carries receiver custody through an opaque call."""
    source = (
        "import subprocess as sp\nstate = {'command': ['before_probe']}\n"
        "unrelated = {'command': ['unrelated_probe']}\nopaque(state.get)\n"
        "sp.run(state['command'])\nsp.run(unrelated['command'])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == {"unrelated_probe"}, flow.result
    assert any(item.state == "unknown" for item in flow.result.uncertainties), flow.result


@pytest.mark.parametrize(
    ("returned", "selected"),
    [
        ("os.system", "relay_11()"),
        ("(os.system,)", "relay_11()[0]"),
        ("{'invoke': os.system}", "relay_11()['invoke']"),
        ("Record(os.system)", "relay_11().invoke"),
        ("os.system", "choose(False)"),
        ("os.system", "opaque(relay_11())"),
    ],
)
def test_consumed_projection_retains_bounded_source_incompleteness(
    returned: str, selected: str
) -> None:
    """Actual-call coverage cannot rely on a later dormant-body scan to restore a cutoff."""
    source = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\nclass Record:\n    invoke: object\n"
        f"def leaf():\n    import os\n    return {returned}\n"
    )
    for index in range(12):
        target = "leaf" if index == 0 else f"relay_{index - 1}"
        source += f"def relay_{index}(): return {target}()\n"
    source += (
        "def noop(command): return None\n"
        "def choose(flag): return noop if flag else relay_11()\n"
        f"def entry(): {selected}('projection_probe')\nentry()"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == {"projection_probe"} or flow.result.uncertainties


@pytest.mark.parametrize("change", ["none", "argument", "capture"])
def test_pure_leaf_return_reuses_only_equal_bound_inputs(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    """A pure leaf's repeated exact inputs share work; arguments and captures stay distinct."""
    source = (
        "import subprocess as sp\nsuffix = '_before_probe'\n"
        "def select(value='first'): return value + suffix\n"
        "sp.run([select()])\nsp.run([select(value='first')])\n"
    )
    if change == "capture":
        source += "suffix = '_after_probe'\n"
    argument = "'second'" if change == "argument" else "'first'"
    source += f"sp.run([select({argument})])\nsp.run([select({argument})])"
    observed: list[str] = []
    return_values = PythonInvocations.return_values

    def counted(
        owner: PythonInvocations,
        invocation: SourceInvocation,
        observer: PythonReferenceFlow,
        child: BindingScope,
    ) -> BindingValue:
        returned = return_values(owner, invocation, observer, child)
        if not owner.summarizing and invocation.definition.node.name == "select":
            observed.extend(returned.strings)
        return returned

    monkeypatch.setattr(PythonInvocations, "return_values", counted)
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)

    expected = {"first_before_probe"}
    if change != "none":
        expected.add("second_before_probe" if change == "argument" else "first_after_probe")
    assert flow.result.executables == expected, flow.result
    assert not flow.result.uncertainties, flow.result
    assert len(observed) == (1 if change == "none" else 2), observed


@pytest.mark.parametrize("binding", ["capture", "argument"])
def test_leaf_return_observes_current_native_namespace_members(binding: str) -> None:
    """Unchanged lexical identities do not freeze mutable native namespace members."""
    parameters = "" if binding == "capture" else "namespace"
    argument = "" if binding == "capture" else "namespace"
    source = (
        "import subprocess as sp\nimport types as namespace\nnamespace.flag = ''\n"
        f"def read({parameters}): return namespace.flag\n"
        f"sp.run([read({argument})])\nnamespace.flag = 'namespace_probe'\n"
        f"sp.run([read({argument})])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == {"namespace_probe"}, flow.result
    assert not flow.result.uncertainties, flow.result


def test_leaf_answer_reuse_preserves_normalized_return(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reused observation answers equal the normalized first return, not its raw precursor."""
    source = "def read(): return missing\nread()\nread()"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    flow.initialize(tree, source=source)
    definition = next(iter(sources.definitions.values()))
    summary = sources.invocations.summary_for(definition, flow.result, definition.parent)
    summary.returned = BindingValue()

    monkeypatch.setattr(PythonInvocations, "return_values", lambda *_: BindingValue())
    observed = [
        sources.invocations.materialize(index, flow.result)
        for index in range(len(sources.invocations.requests))
    ]

    assert observed == [BindingValue(local=True), BindingValue(local=True)]
