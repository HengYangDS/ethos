"""Native iteration retains live custody separately from shallow snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("setup", "iterable", "target", "mutation", "verdict"),
    [
        (
            'data = {"first": "example", "second": "example"}',
            "data.values()",
            "name",
            'data["second"] = "unowned.module"',
            "block",
        ),
        (
            'data = {"first": "example", "second": "example"}',
            "tuple(data.values())",
            "name",
            'data["second"] = "unowned.module"',
            "pass",
        ),
        (
            'data = {"first": "example", "second": "example"}',
            "data.items()",
            "_, name",
            'data["second"] = "unowned.module"',
            "block",
        ),
        (
            'data = {"first": "example", "second": "example"}',
            "tuple(data.items())",
            "_, name",
            'data["second"] = "unowned.module"',
            "pass",
        ),
        (
            'data = {"example": "unowned.module", "example.child": "unowned.module"}',
            "data.keys()",
            "name",
            'data["example.child"] = "another.unowned"',
            "pass",
        ),
        (
            'data = {"example": "unowned.module", "example.child": "unowned.module"}',
            "data",
            "name",
            'data["example.child"] = "another.unowned"',
            "pass",
        ),
        (
            (
                'data = {"first": "example", "second": "example"}\nview = data.values()\n'
                'data = {"first": "unowned.module", "second": "unowned.module"}'
            ),
            "view",
            "name",
            'data["second"] = "another.unowned"',
            "pass",
        ),
    ],
)
def test_public_iteration_consumes_current_yields(
    tmp_path: Path, setup: str, iterable: str, target: str, mutation: str, verdict: str
) -> None:
    """View yields are live; tuple slots and iterator identity survive rebinding."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        f"import importlib\n{setup}\nfor {target} in {iterable}:\n"
        f"    {mutation}\n    importlib.import_module(name)",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == verdict, report
    assert {item["identity"] for item in report["orphan"]} == (
        {"unowned"} if verdict == "block" else set()
    ), report


@pytest.mark.parametrize("finalized", [False, True])
def test_public_iteration_topology_loss_retains_coverage(
    tmp_path: Path, *, finalized: bool
) -> None:
    """An unresolved next yield cannot become exact exhaustion or a qualified return."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    body = (
        'data = {"first": "example"}\nfor name in data.values():\n'
        '    data["added"] = "example"\n    importlib.import_module(name)'
    )
    source = (
        "def selected():\n    try:\n"
        + "\n".join("        " + line for line in body.splitlines())
        + '\n    finally:\n        return "example"\nimportlib.import_module(selected())'
        if finalized
        else body
    )
    write_reference_source(tmp_path, "src/example/probe.py", "import importlib\n" + source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report


@pytest.mark.parametrize(
    ("alternative", "coverage"),
    [("data.keys()", "unknown"), ("None", "unknown"), ("data.values()", "evaluated")],
)
def test_public_iteration_preserves_joined_owner_boundaries(
    tmp_path: Path, alternative: str, coverage: str
) -> None:
    """Opaque owners and lost view correlation cannot qualify a finite native plan."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import importlib\ndata = {"example": "example"}\n'
        f"view = data.values() if condition else {alternative}\n"
        "for name in view:\n    importlib.import_module(name)",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == coverage, report
    assert report["verdict"] == ("pass" if coverage == "evaluated" else "unknown"), report


@pytest.mark.parametrize("flag", ["False", "True", "opaque"])
def test_mapping_slot_write_preserves_unresolved_topology(tmp_path: Path, flag: str) -> None:
    """Writing one known slot cannot certify the presence or order of another."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess as sp\ndata = {}\n"
        f"if {flag}: data['early_probe'] = 0\n"
        "data['later_probe'] = 0\nsp.run([tuple(data)[0]])",
    )
    report = repository_semantic_closure(tmp_path)
    if flag == "opaque":
        assert report["coverage"] == "unknown", report
        assert report["verdict"] != "pass", report
    else:
        assert report["coverage"] == "evaluated", report
        assert {item["identity"] for item in report["orphan"]} == {
            "early_probe" if flag == "True" else "later_probe"
        }, report


@pytest.mark.parametrize(
    ("body", "identity"),
    [
        (
            (
                "values = []\nvalues.append('first_probe')\nvalues.append('second_probe')\n"
                "sp.run([values[1]])"
            ),
            "second_probe",
        ),
        (
            "values = []\nvalues.append(sp.run)\nvalues[0](['branch_probe'])",
            "branch_probe",
        ),
        (
            (
                "left, right = [], []\nput = left.append if opaque else right.append\n"
                "put('stored_probe')\nif not left: sp.run(['branch_probe'])"
            ),
            "branch_probe",
        ),
    ],
)
def test_public_native_append_preserves_consumed_effects(
    tmp_path: Path, body: str, identity: str
) -> None:
    """Native writes retain sequence contents and the may-selected receiver's old state."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", "import subprocess as sp\n" + body)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert {item["identity"] for item in report["orphan"]} == {identity}, report


@pytest.mark.parametrize("argument", ["object=sp.run", "**options"])
def test_public_native_append_requires_its_bound_signature(tmp_path: Path, argument: str) -> None:
    """Unsupported calls cannot claim the post-state of one positional native append."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess as sp\nvalues = []\noptions = {'object': sp.run}\n"
        f"values.append({argument})\nfor callback in values: callback(['branch_probe'])",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report


def test_public_native_append_preserves_a_joined_may_element(tmp_path: Path) -> None:
    """Losing exact length does not erase a callback appended before iteration."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess as sp\ndef noop(command): return None\n"
        "values = [] if opaque else [noop]\nvalues.append(sp.run)\n"
        "for callback in values: callback(['branch_probe'])",
    )

    report = repository_semantic_closure(tmp_path)

    assert any(item["identity"] == "branch_probe" for item in report["orphan"]), report
    assert report["verdict"] != "pass", report


@pytest.mark.parametrize("capture", ["lexical", "default"])
def test_public_opaque_source_callback_escape_keeps_its_capability(
    tmp_path: Path, capture: str
) -> None:
    """Handing a source callback to an opaque owner can expose its retained native call."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    callback = (
        "def callback(command): sp.run(command)\n"
        if capture == "lexical"
        else "def callback(command, executor=sp.run): executor(command)\n"
    )
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess as sp\n" + callback + "opaque(callback)",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report


def test_public_internal_source_callable_cutoff_cannot_erase_an_effect(tmp_path: Path) -> None:
    """A local import is not a captured root; consumed limited calls still need refinement."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    source = "def factory():\n    import os\n    return os.system\n"
    for index in range(12):
        target = "factory" if index == 0 else f"relay_{index - 1}"
        source += f"def relay_{index}(): return {target}()\n"
    source += "def fire(): relay_11()('branch_probe')\nfire()"
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] != "pass", report
    assert report["coverage"] == "unknown" or any(
        item["identity"] == "branch_probe" for item in report["orphan"]
    ), report


@pytest.mark.parametrize(
    "invocation",
    [
        "def produce(receiver): receiver.clear()\nproduce(state)",
        "def produce(): state.clear()\nproduce()",
        "def produce(value): opaque(value)\nproduce(sp.run)",
    ],
)
def test_public_opaque_call_retains_actual_shared_custody(tmp_path: Path, invocation: str) -> None:
    """Actual receiver writes and escaped capabilities cannot become pure discarded calls."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess as sp\nstate = ['before_probe']\n" + invocation + "\nsp.run([state[0]])",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report
