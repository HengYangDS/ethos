"""Deferred body observation shares summaries independently of callable export support."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ParameterProjection
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.effects import substitute
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.functions.invocation import SourceInvocation
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns
from ethos.repository.policy.references.python.native.scalars import concatenate
from ethos.repository.policy.references.python.native.scalars import native_scalar

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.effects import PythonConsumption


@pytest.mark.parametrize("owner", ["def", "decorated", "async", "lambda"])
@pytest.mark.parametrize("count", [1, 6])
def test_discovery_shares_body_semantics_without_exporting_opaque_callables(
    monkeypatch: pytest.MonkeyPatch, owner: str, count: int
) -> None:
    """A decorator or async boundary must not restart concrete transitive expansion."""
    source = (
        "import subprocess as sp\nimport os\n"
        "def leaf(value):\n    return value\n"
        "def helper(receiver):\n    return tuple(leaf(item) for item in receiver['inputs'])\n"
    )
    calls = ["helper(receiver)"] * count
    effects = ["sp.run(['discovery_probe'])", "os.getenv('DISCOVERY_INPUT')"]
    if owner == "lambda":
        source += "owner = lambda receiver: (" + ", ".join([*calls, *effects]) + ")\n"
    else:
        source += "@opaque\n" if owner == "decorated" else ""
        source += ("async def" if owner == "async" else "def") + " owner(receiver):\n"
        source += "".join("    " + call + "\n" for call in [*calls, *effects])
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observed = []
    evaluate = PythonInvocations.evaluate

    def counted(
        invocations: PythonInvocations, invocation: SourceInvocation, result: PythonConsumption
    ) -> BindingValue:
        observed.append(
            (getattr(invocation.definition.node, "name", "<lambda>"), bool(invocations.summarizing))
        )
        return evaluate(invocations, invocation, result)

    monkeypatch.setattr(PythonInvocations, "evaluate", counted)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.observe(tree, source=source)

    name = "<lambda>" if owner == "lambda" else "owner"
    assert sorted(observed) == sorted([("helper", True), ("leaf", True), (name, True)]), observed
    assert not flow.result.uncertainties, flow.result
    assert flow.result.executables == {"discovery_probe"}
    assert flow.result.inputs == {"DISCOVERY_INPUT"}


@pytest.mark.parametrize("depth", [6, 16])
def test_acyclic_discovery_does_not_invent_executable_uncertainty(depth: int) -> None:
    """An uncalled finite helper chain is not a dynamic executable boundary."""
    source = (
        "import subprocess as sp\n"
        f"def owner(argument):\n    sp.run([layer_{depth - 1}('depth_probe')])\n"
    )
    for index in reversed(range(depth)):
        target = "leaf" if index == 0 else f"layer_{index - 1}"
        source += f"def layer_{index}(value): return {target}(value)\n"
    source += "def leaf(value): return value\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == {"depth_probe"}, result
    assert not result.uncertainties, result


@pytest.mark.parametrize(
    ("kind", "statement", "target"),
    [
        ("executable", "sp.run(value)", "subprocess.run"),
        ("import", "imports.import_module(value)", "importlib.import_module"),
        ("value", "os.getenv(value)", "os.getenv"),
    ],
)
def test_replayed_effect_preserves_its_defining_source_site(
    kind: str, statement: str, target: str
) -> None:
    """Actual arguments may change the finding, never its defining path and scope."""
    files = {
        "helper.py": (
            "import subprocess as sp\nimport importlib as imports\nimport os\n"
            f"def execute(value):\n    {statement}\n"
        ),
        "probe.py": (
            "from helper import execute\ndef consumer(parameter):\n    execute(opaque(parameter))\n"
        ),
    }
    trees = {path: ast.parse(source) for path, source in files.items()}
    sources = PythonSourceReturns(files, trees, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(
        trees["probe.py"], source=files["probe.py"]
    )

    unknowns = [item for item in result.uncertainties if item.state == "unknown"]
    assert unknowns, result
    assert {(item.kind, item.path, item.scope, item.line, item.target) for item in unknowns} == {
        (kind, "helper.py", "<module>.execute", 5, target)
    }, result


@pytest.mark.parametrize("target", [None, "subprocess.run", "importlib.import_module", "os.getenv"])
def test_bounded_return_affects_only_its_native_consumer(target: str | None) -> None:
    """An unresolved value is not an executable obligation before native consumption."""
    source = "def identity(value): return value\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    definition = sources.definitions[next(iter(scope.lookup("identity").targets))]
    node = ast.parse("identity('value')").body[0].value
    invocation = SourceInvocation(
        definition, (BindingValue(strings=frozenset({"value"})),), {}, node, scope, scope
    )
    sources.invocations.demands = 128

    value = sources.invocations.evaluate(invocation, flow.result)

    assert value.unknown
    assert value.context_limited
    assert not flow.result.uncertainties
    if target is not None:
        kind = flow.result.kind(target)
        assert kind is not None
        flow.result.consume(kind, value, node, scope, target)
        assert {item.kind for item in flow.result.uncertainties} == {kind}
        assert {item.reason for item in flow.result.uncertainties} == {"value_not_resolved"}


@pytest.mark.parametrize(
    ("kind", "statement"),
    [
        ("executable", "sp.run(value)"),
        ("import", "imports.import_module(value)"),
        ("value", "os.getenv(value)"),
    ],
)
def test_bounded_effect_keeps_its_actual_obligation(kind: str, statement: str) -> None:
    """An input or import boundary cannot become an executable obligation at a cutoff."""
    source = (
        "import subprocess as sp\nimport importlib as imports\nimport os\n"
        f"def consumer(value):\n    {statement}\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    definition = sources.definitions[next(iter(scope.lookup("consumer").targets))]
    node = ast.parse("consumer(opaque)").body[0].value
    invocation = SourceInvocation(definition, (BindingValue(unknown=True),), {}, node, scope, scope)
    sources.invocations.demands = 128

    value = sources.invocations.evaluate(invocation, flow.result)

    assert value.unknown
    assert {item.kind for item in flow.result.uncertainties if item.state == "unknown"} == {kind}


@pytest.mark.parametrize("opaque", [False, True])
def test_parser_alternatives_preserve_successful_registry_values(*, opaque: bool) -> None:
    """A symbolic parser alternative does not add a missing value to a finite registry."""
    files = {
        "arguments.py": (
            "def parse(arguments):\n    for value in arguments:\n"
            "        return value\n    return ''\n"
        ),
        "probe.py": (
            "import importlib\nfrom arguments import parse\n"
            "mapping = {'one': 'one.module', 'two': 'two.module'}\n"
            + ("opaque(mapping)\n" if opaque else "")
            + "def load(arguments):\n    key = parse(arguments)\n"
            "    if key in mapping:\n        selected = (mapping[key],)\n"
            "    elif key:\n        selected = ()\n"
            "    else:\n        selected = tuple(dict.fromkeys(mapping.values()))\n"
            "    for name in selected:\n        importlib.import_module(name)\n"
        ),
    }
    trees = {path: ast.parse(source) for path, source in files.items()}
    sources = PythonSourceReturns(files, trees, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(
        trees["probe.py"], source=files["probe.py"]
    )

    assert bool([item for item in result.uncertainties if item.state == "unknown"]) == opaque, (
        result
    )
    if not opaque:
        assert result.imports >= {"one", "two"}


@pytest.mark.parametrize("copied", [False, True])
def test_environment_copy_keeps_actual_input_obligation(*, copied: bool) -> None:
    """Copying cannot hide a consumed environment key or make its value statically known."""
    source = (
        "import os\nimport subprocess as sp\n"
        + ("mapping = dict(os.environ)\n" if copied else "mapping = os.environ\n")
        + "sp.run([mapping['ENVIRONMENT_PROBE_COMMAND']])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.inputs == {"ENVIRONMENT_PROBE_COMMAND"}, result
    assert not result.executables, result
    assert {item.state for item in result.uncertainties} == {"deferred"}, result


@pytest.mark.parametrize("environment", [False, True])
def test_native_mapping_copy_keeps_fresh_custody(*, environment: bool) -> None:
    """A native copy reads contents without transferring executable namespace capability."""
    source = (
        "import os\nimport subprocess as sp\n"
        + (
            "original = os.environ\n"
            if environment
            else "original = {'command': ['before_probe']}\n"
        )
        + "copy = dict(original)\ncopy['command'] = ['after_probe']\nsp.run(copy['command'])\n"
        + ("" if environment else "sp.run(original['command'])\n")
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == (
        {"after_probe"} if environment else {"before_probe", "after_probe"}
    ), result
    assert not [item for item in result.uncertainties if item.state == "unknown"], result


@pytest.mark.parametrize("opaque", [False, True])
def test_native_presence_check_retains_opaque_owner_boundary(*, opaque: bool) -> None:
    """A presence predicate on a native module does not transfer its effect capabilities."""
    source = "import os\n" + ("os = opaque(os)\n" if opaque else "") + "hasattr(os, 'fwalk')\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert bool([item for item in result.uncertainties if item.state == "unknown"]) == opaque, (
        result
    )


@pytest.mark.parametrize("operation", ["shutil.which(value)", "str(Path(value) / 'probe')"])
@pytest.mark.parametrize("actual", ["'native_probe'", "opaque()", None])
def test_native_return_operations_keep_their_parameter_dependency(
    operation: str, actual: str | None
) -> None:
    """A native transform discharges its actual slot without hiding an opaque result."""
    source = (
        "from pathlib import Path\nimport shutil\nimport subprocess as sp\n"
        f"def consume(value):\n    sp.run([{operation}])\n"
        + (f"consume({actual})\n" if actual is not None else "")
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    unknowns = [item for item in result.uncertainties if item.state == "unknown"]
    assert bool(unknowns) == (actual == "opaque()"), result
    if actual == "'native_probe'":
        expected = {"native_probe"} if operation.startswith("shutil") else {"probe"}
        assert result.executables == expected, result


@pytest.mark.parametrize("opaque", [False, True])
def test_indexed_input_keeps_parameterized_numeric_iteration(*, opaque: bool) -> None:
    """Count-driven indices are runtime values; an opaque producer remains UNKNOWN."""
    source = (
        "import os\n"
        "def read(count):\n"
        + ("    count = opaque(count)\n" if opaque else "")
        + "    for index in range(int(count)):\n"
        "        os.getenv(f'INDEXED_INPUT_{index}')\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert bool([item for item in result.uncertainties if item.state == "unknown"]) == opaque, (
        result
    )
    assert not result.inputs


@pytest.mark.parametrize(
    "body", ["return os.fspath(value)", "return os", "return os.getenv(value)"]
)
def test_source_callback_exports_only_reachable_effect_capabilities(body: str) -> None:
    """A callback's free namespace is not itself an observable native effect."""
    source = f"import os\ndef callback(value):\n    {body}\nopaque(callback)\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    unknowns = [item for item in result.uncertainties if item.state == "unknown"]
    assert bool(unknowns) == (body != "return os.fspath(value)"), result
    if body == "return os.getenv(value)":
        assert {item.kind for item in unknowns} == {"value"}, result


@pytest.mark.parametrize("kind", ["executable", "value"])
@pytest.mark.parametrize("callback", [False, True])
def test_bounded_source_edge_keeps_transitive_actual_effect(kind: str, *, callback: bool) -> None:
    """A local return budget cannot discard a reached effect behind a source edge."""
    target = "sp.run" if kind == "executable" else "os.getenv"
    signature = "callback, value" if callback else "value"
    callee = "callback" if callback else target
    arguments = f"{target}, value" if callback else "value"
    source = (
        "import subprocess as sp\nimport os\n"
        f"def leaf({signature}): {callee}(value)\n"
        f"def wrapper(value): leaf({arguments})\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    definition = sources.definitions[next(iter(scope.lookup("wrapper").targets))]
    node = ast.parse("wrapper(opaque)").body[0].value
    invocation = SourceInvocation(definition, (BindingValue(unknown=True),), {}, node, scope, scope)
    sources.invocations.demands = 128

    sources.invocations.evaluate(invocation, flow.result)

    unknowns = [item for item in flow.result.uncertainties if item.state == "unknown"]
    assert {item.kind for item in unknowns} == {kind}, flow.result
    native_target = "subprocess.run" if kind == "executable" else "os.getenv"
    assert {item.target for item in unknowns} == {native_target}


@pytest.mark.parametrize("side", ["left", "right"])
def test_symbolic_concatenation_preserves_operand_role(side: str) -> None:
    """A member's operand role is not its other operand's scalar selector."""
    source = ""
    sources = PythonSourceReturns(
        {"probe.py": source}, {"probe.py": ast.parse(source)}, PythonReferenceFlow
    )
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(ast.parse(source), source=source)
    parameter = BindingValue(parameters=frozenset({ParameterProjection("name", owner="probe")}))
    literal = BindingValue(strings=frozenset({"-tool"}))
    value = concatenate(parameter, literal) if side == "left" else concatenate(literal, parameter)

    selected = substitute(
        value,
        {"name": BindingValue(strings=frozenset({"my"}))},
        scope,
        sources,
        flow.result,
        owner="probe",
    )

    assert selected.strings == {"my-tool" if side == "left" else "-toolmy"}


def test_opaque_callback_keeps_default_capability_passed_through_helper() -> None:
    """A default's actual source-call edge cannot erase its callable capability."""
    source = (
        "import subprocess as sp\n"
        "def helper(fn): fn(['probe'])\n"
        "def owner(executor=sp.run): helper(executor)\n"
        "opaque(owner)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert any(
        item.state == "unknown" and item.target == "subprocess.run" for item in result.uncertainties
    ), result


@pytest.mark.timeout(3)
def test_recursive_effect_growth_widens_only_exhausted_contexts() -> None:
    """An infinite family of effect arguments has a finite conservative observation."""
    source = (
        "import os\ndef recur(value):\n    os.getenv(value)\n    return recur('PREFIX_' + value)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)
    scope = flow.initialize(tree, source=source)
    definition = sources.definitions[next(iter(scope.lookup("recur").targets))]
    node = ast.parse("recur('ROOT')").body[0].value
    invocation = SourceInvocation(
        definition, (BindingValue(strings=frozenset({"ROOT"})),), {}, node, scope, scope
    )
    sources.invocations.demands = 128

    sources.invocations.evaluate(invocation, flow.result)

    assert "ROOT" in flow.result.inputs
    assert any(
        item.state == "unknown" and item.target == "os.getenv" for item in flow.result.uncertainties
    )
    assert len(flow.result.inputs) <= 128


@pytest.mark.parametrize("selector", ["'known_probe_module'", "value"])
def test_opaque_callback_preserves_its_bound_reference_selector(selector: str) -> None:
    """Unknown execution cannot erase a fixed module or close an unresolved selector."""
    source = (
        "import importlib as imports\n"
        f"def callback(value): imports.import_module({selector})\n"
        "opaque(callback)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    unknowns = [item for item in result.uncertainties if item.state == "unknown"]
    assert bool(unknowns) == (selector == "value"), result
    if selector != "value":
        assert "known_probe_module" in result.imports


@pytest.mark.parametrize("reader", ["getattr", "opaque", "getattr if selector else opaque"])
@pytest.mark.parametrize("indirect", [False, True])
def test_bound_callback_callee_selects_argument_transfer(reader: str, *, indirect: bool) -> None:
    """A bound call transfers capabilities only through an unresolved callee alternative."""
    statement = "helper(os)" if indirect else "reader(os, 'O_NOFOLLOW', 0)"
    source = (
        f"import os\nreader = {reader}\n"
        "def helper(value): return reader(value, 'O_NOFOLLOW', 0)\n"
        f"def callback(): return {statement}\nopaque(callback)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    transfers = [
        item
        for item in result.uncertainties
        if item.state == "unknown" and item.reason == "opaque_capability_escape"
    ]
    assert bool(transfers) == (reader != "getattr"), result
    if reader != "getattr":
        assert {item.kind for item in transfers} == {"value", "executable"}, result
        assert any(
            item.path == "probe.py"
            and item.scope == ("<module>.helper" if indirect else "<module>.callback")
            for item in transfers
        ), result


@pytest.mark.parametrize("indirect", [False, True])
@pytest.mark.parametrize("opaque", [False, True])
def test_native_list_retains_selected_command_and_opaque_protocol(
    *, indirect: bool, opaque: bool
) -> None:
    """A native list copies a closed sequence, never an unresolved iteration protocol."""
    argument = "opaque()" if opaque else "('list_probe', '--version')"
    source = (
        "import subprocess as sp\n"
        "def copy(value): return list(value)\n"
        f"sp.run({'copy' if indirect else 'list'}({argument}))\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == (set() if opaque else {"list_probe"}), result
    assert any(item.state == "unknown" for item in result.uncertainties) == opaque, result


@pytest.mark.parametrize("reader", ["len", "opaque", "len if selector else opaque"])
@pytest.mark.parametrize("indirect", [False, True])
def test_native_length_keeps_count_separate_from_namespace_transfer(
    reader: str, *, indirect: bool
) -> None:
    """Closed native length reads count; an opaque callee still receives full custody."""
    statement = "helper(os.environ)" if indirect else "reader(os.environ)"
    source = (
        f"import os\nreader = {reader}\n"
        "def helper(value): return reader(value)\n"
        f"def callback(): return str({statement})\nopaque(callback)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    transfers = [item for item in result.uncertainties if item.reason == "opaque_capability_escape"]
    assert bool(transfers) == (reader != "len"), result
    assert not result.inputs, result


def test_native_list_copy_has_fresh_mutation_custody() -> None:
    """Mutation through a list constructor affects the fresh copy, not its source."""
    source = (
        "import subprocess as sp\noriginal = []\ncopied = list(original)\n"
        "copied.append('after_probe')\noriginal.append('before_probe')\n"
        "sp.run(copied)\nsp.run(original)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert result.executables == {"before_probe", "after_probe"}, result
    assert not result.uncertainties, result


@pytest.mark.parametrize(
    ("name", "statement"),
    [("len", "reader(os.environ)"), ("list", "sp.run(reader(('list_probe',)))")],
)
def test_shadowed_native_names_do_not_inherit_builtin_contract(name: str, statement: str) -> None:
    """Local names and custom protocols cannot inherit a same-spelled native contract."""
    source = f"import os\nimport subprocess as sp\n{name} = opaque\nreader = {name}\n{statement}\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    assert any(item.state == "unknown" for item in result.uncertainties), result


@pytest.mark.parametrize("reader", ["len", "opaque", "(len if selector else opaque)"])
def test_native_length_counts_loop_widened_list_without_transferring_contents(reader: str) -> None:
    """A native list count reads topology, not the capabilities retained in its elements."""
    source = (
        "import os\n"
        "def count(*mappings):\n"
        "    entries = []\n"
        "    for mapping in mappings:\n"
        "        for item in opaque():\n"
        "            entries.append((mapping, mapping))\n"
        f"    return str({reader}(entries))\n"
        "count(os.environ)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)

    result = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)

    transfers = [item for item in result.uncertainties if item.reason == "opaque_capability_escape"]
    assert bool(transfers) == (reader != "len"), result
    assert any(item.state == "unknown" for item in result.uncertainties) == (reader != "len"), (
        result
    )
    assert not result.inputs, result


@pytest.mark.parametrize(
    ("value", "proven"),
    [
        (BindingValue(native_kind="list", element=BindingValue(unknown=True)), True),
        (BindingValue(element=BindingValue(unknown=True)), False),
        (BindingValue(native_kind="list", unknown=True), False),
        (BindingValue(native_kind="list", local=True), False),
        (BindingValue(native_kind="list", selection=frozenset({"unresolved"})), False),
        (BindingValue(native_kind="list", targets=frozenset({"custom.Length"})), False),
    ],
)
def test_native_length_requires_proven_receiver_topology(
    value: BindingValue, *, proven: bool
) -> None:
    """Unknown contents do not revoke topology; unknown or custom receivers remain refused."""
    result = native_scalar("builtins.len", (value,), {})

    assert (result is not None) == proven
    if proven:
        assert result == BindingValue(deferred=True)
