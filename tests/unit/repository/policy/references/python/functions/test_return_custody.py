"""Qualify returned allocation and callback custody across opaque consumers."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.policy.references.python.bindings import BindingValue
    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.functions.invocation import SourceInvocation


@pytest.mark.parametrize(
    ("returned", "unknown"),
    [('{"flag": False}', False), ('{"scope": scope}', True)],
)
def test_public_closure_escapes_only_completed_return_custody(
    tmp_path: Path, returned: str, *, unknown: bool
) -> None:
    """A completed return retains actual aliases, not every historical invocation input."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "def choose(scope):\n"
        f"    return {returned}\n"
        "scope = Scope()\n"
        "external(choose(scope))\n"
        'scope.start(("completed_return_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert (report["coverage"] == "unknown") is unknown, report
    if not unknown:
        assert {item["identity"] for item in report["orphan"]} == {"completed_return_probe"}, report


def test_public_closure_escapes_captures_of_a_returned_callback(tmp_path: Path) -> None:
    """A completed returned callable still exports its own receiver capture."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "def choose(scope):\n"
        "    def launch(command):\n"
        "        return scope.start(command)\n"
        "    return launch\n"
        "scope = Scope()\n"
        "external(choose(scope))\n"
        'scope.start(("returned_callback_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report


@pytest.mark.parametrize("escaped", [False, True])
def test_public_closure_preserves_process_args_custody(tmp_path: Path, *, escaped: bool) -> None:
    """The native process keeps its actual args alias, not the source caller's receiver."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    change = "external(process)\n" if escaped else ""
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        'command = ["retained_process_probe"]\n'
        "process = subprocess.Popen(command)\n"
        f"{change}"
        "subprocess.run(process.args)\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert (report["coverage"] == "unknown") is escaped, report
    assert {item["identity"] for item in report["orphan"]} == {"retained_process_probe"}, report


def test_public_closure_process_escape_does_not_export_source_receiver(tmp_path: Path) -> None:
    """Escaping a created process cannot alias the caller's unrelated method receiver."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "scope = Scope()\n"
        'external(scope.start(("escaped_process_probe",)))\n'
        'scope.start(("independent_receiver_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] != "unknown", report
    assert {item["identity"] for item in report["orphan"]} == {
        "escaped_process_probe",
        "independent_receiver_probe",
    }, report


@pytest.mark.parametrize("unknown_alternative", [False, True])
def test_public_closure_keeps_allocation_identity_after_context_exit(
    tmp_path: Path, *, unknown_alternative: bool
) -> None:
    """An opaque exit may mutate returned state, but cannot invent another successful return."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    returned = "process if condition else external_result" if unknown_alternative else "process"
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        with external_context:\n"
        "            process = subprocess.Popen(command)\n"
        f"            return {returned}\n"
        "scope = Scope()\n"
        'external(scope.start(("context_process_probe",)))\n'
        'scope.start(("context_receiver_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert (report["coverage"] == "unknown") is unknown_alternative, report
    if not unknown_alternative:
        assert {item["identity"] for item in report["orphan"]} == {
            "context_process_probe",
            "context_receiver_probe",
        }, report


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


@pytest.mark.parametrize(
    ("returned", "command"),
    [
        ("'immutable_probe'", "[value]"),
        ("('immutable_probe',)", "value"),
        ("('immutable_probe', ('argument',))", "[value[0]]"),
    ],
)
def test_closed_native_return_keeps_call_time_value_after_escape(
    returned: str, command: str
) -> None:
    """An opaque consumer cannot rewrite a proven native scalar or closed tuple."""
    source = (
        "import subprocess as sp\n"
        f"def choose():\n    return {returned}\n"
        "value = choose()\nexternal(value)\n"
        f"sp.run({command})\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert flow.result.executables == {"immutable_probe"}, flow.result
    assert not any(item.state == "unknown" for item in flow.result.uncertainties), flow.result


@pytest.mark.parametrize(
    ("returned", "command"),
    [
        ("{'key': 'mutable_probe'}", "value['key']"),
        ("({'key': 'mutable_probe'},)", "value[0]['key']"),
    ],
)
def test_returned_mutable_custody_stays_open_after_escape(returned: str, command: str) -> None:
    """An outer native tuple does not make its reachable mutable members immutable."""
    source = (
        "import subprocess as sp\n"
        f"def choose():\n    return {returned}\n"
        "value = choose()\nexternal(value)\n"
        f"sp.run([{command}])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    flow = PythonReferenceFlow("probe.py", {}, sources=sources)

    flow.initialize(tree, source=source)

    assert any(
        item.target == "subprocess.run" and item.state == "unknown"
        for item in flow.result.uncertainties
    ), flow.result
