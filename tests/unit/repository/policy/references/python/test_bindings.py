"""Observe bounded Python reference meaning through the public closure owner."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.python.bindings import BindingValue
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("source", "verdict", "orphans"),
    [
        (
            'selected = importlib.import_module\nselected((selected := "unowned.module"))',
            "block",
            {"unowned"},
        ),
        ('importlib.import_module((importlib := "unowned.module"))', "block", {"unowned"}),
        (
            'selected = importlib.import_module\nselected(name=(selected := "example"))',
            "pass",
            set(),
        ),
    ],
)
def test_public_closure_resolves_callee_before_arguments(
    tmp_path: Path, source: str, verdict: str, orphans: set[str]
) -> None:
    """Argument-side rebinding cannot replace the callable already selected by Python."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", "import importlib\n" + source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == verdict, report
    assert {item["identity"] for item in report["orphan"]} == orphans


@pytest.mark.parametrize(
    "source",
    [
        (
            'import os\nNAME = "BINDING_PROBE_INPUT"\nclass Reader:\n'
            '    NAME = "DECLARED_INPUT"\n    def read(self):\n'
            "        return os.getenv(NAME)"
        ),
        (
            'import os\ndef outer():\n    NAME = "BINDING_PROBE_INPUT"\n'
            '    class Reader:\n        NAME = "DECLARED_INPUT"\n'
            "        def read(self):\n            return os.getenv(NAME)"
        ),
        'import os\n[os.getenv(NAME) for NAME in ["BINDING_PROBE_INPUT"]]',
        (
            'import os\nNAME = "DECLARED_INPUT"\n'
            '[os.getenv(NAME) for NAME in ["BINDING_PROBE_INPUT"]]\n'
            "os.getenv(NAME)"
        ),
        'import os\nfor NAME in ["BINDING_PROBE_INPUT"]:\n    os.getenv(NAME)',
        (
            'import os\ndef outer():\n    NAME = "DECLARED_INPUT"\n'
            "    def inner():\n        nonlocal NAME\n"
            '        NAME = "BINDING_PROBE_INPUT"\n        os.getenv(NAME)'
        ),
    ],
)
def test_public_closure_keeps_lexical_namespaces(tmp_path: Path, source: str) -> None:
    """Class, closure and iteration namespaces preserve the consumed identity."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert any(
        item["kind"] == "value" and item["identity"] == "BINDING_PROBE_INPUT"
        for item in report["orphan"]
    ), report


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        ('import os\ngetattr(os, selector)("BINDING_PROBE_INPUT")', "executable"),
        ('import os\nfrom unknown_module import *\nos.getenv("DECLARED_INPUT")', "value"),
        (
            (
                'import os\nNAME = "DECLARED_INPUT"\ndef read():\n    os.getenv(NAME)\n'
                'def change():\n    global NAME\n    NAME = "BINDING_PROBE_INPUT"'
            ),
            "value",
        ),
        (
            (
                'import os\nNAME = "DECLARED_INPUT"\nwhile condition:\n'
                '    NAME += "x"\n    os.getenv(NAME)'
            ),
            "value",
        ),
    ],
)
def test_public_closure_retains_relevant_unresolved_binding(
    tmp_path: Path, source: str, kind: str
) -> None:
    """Unsupported binding effects cannot claim complete evaluated coverage."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert any(
        item["kind"] == kind and item["state"] == "unknown" for item in report["uncertainties"]
    ), report


@pytest.mark.parametrize(
    "source",
    [
        'import subprocess\nsubprocess.run(["binding_probe_binary"])',
        'import subprocess as sp\nsp.run(["binding_probe_binary"])',
        'from subprocess import run as launch\nlaunch(["binding_probe_binary"])',
        'import subprocess as sp\nlaunch = sp.run\nlaunch(["binding_probe_binary"])',
    ],
)
def test_public_closure_preserves_executable_binding(tmp_path: Path, source: str) -> None:
    """Alias changes preserve the same observed executable consumer."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["orphan"] == [
        {
            "relation": "consumer",
            "kind": "executable",
            "identity": "binding_probe_binary",
            "sources": ["src/example/probe.py"],
        }
    ]


@pytest.mark.parametrize(
    "source",
    [
        (
            "class Local:\n    def run(self, args):\n        return len(args)\n"
            'subprocess = Local()\nsubprocess.run(["binding_probe_binary"])'
        ),
        (
            "import subprocess\nclass Local:\n    def run(self, args):\n"
            "        return len(args)\nsubprocess = Local()\n"
            'subprocess.run(["binding_probe_binary"])'
        ),
        (
            "import subprocess\ndef local(subprocess):\n"
            '    return subprocess.run(["binding_probe_binary"])'
        ),
        'COMMAND = ["binding_probe_binary"]',
        'from pathlib import Path\nPath("/usr/bin/binding_probe_binary")',
    ],
)
def test_public_closure_does_not_invent_execution(tmp_path: Path, source: str) -> None:
    """Names, command-shaped data and pure paths are not execution effects."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "pass", report
    assert report["orphan"] == []


@pytest.mark.parametrize(
    "source",
    [
        'import os\nos.getenv("BINDING_PROBE_INPUT")',
        'import os as environment\nenvironment.getenv("BINDING_PROBE_INPUT")',
        'from os import getenv as read\nread("BINDING_PROBE_INPUT")',
        ('import os\nNAME = "BINDING_PROBE_INPUT"\nos.getenv(NAME)\nNAME = "DECLARED_INPUT"'),
        (
            'import os\nNAME = "BINDING_PROBE_INPUT"\ndef unrelated():\n'
            '    NAME = "UNRELATED"\nos.getenv(NAME)'
        ),
        (
            'import os\ndef read():\n    NAME = "BINDING_PROBE_INPUT"\n'
            '    os.getenv(NAME)\n    NAME = "UNRELATED"'
        ),
    ],
)
def test_public_closure_preserves_environment_scope_and_program_point(
    tmp_path: Path, source: str
) -> None:
    """Only possible values at the real read become runtime input consumers."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert report["orphan"] == [
        {
            "relation": "consumer",
            "kind": "value",
            "identity": "BINDING_PROBE_INPUT",
            "sources": ["src/example/probe.py"],
        }
    ]


@pytest.mark.parametrize(
    ("source", "state", "coverage"),
    [
        (
            'import subprocess as sp\ngetattr(sp, selector)(["probe"])',
            "unknown",
            "unknown",
        ),
        (
            "import subprocess\ndef launch(command):\n    subprocess.run(command)",
            "deferred",
            "partial",
        ),
    ],
)
def test_public_closure_distinguishes_dynamic_coverage(
    tmp_path: Path, source: str, state: str, coverage: str
) -> None:
    """Syntax, unresolved callee and parameterized effects are distinct facts."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == coverage, report
    assert report["verdict"] == ("unknown" if state == "unknown" else "pass")
    residuals = report["uncertainties"]
    assert len(residuals) == 1
    assert residuals[0]["state"] == state
    assert residuals[0]["kind"] == "executable"
    assert residuals[0]["path"] == "src/example/probe.py"
    assert residuals[0]["line"] > 0
    assert report["orphan"] == []


@pytest.mark.parametrize(
    "source",
    [
        (
            "import subprocess\ndef launch(argument):\n"
            '    subprocess.run(["binding_probe_binary", argument])'
        ),
        (
            'import os\nNAME="DECLARED_INPUT"\ndef read():\n'
            '    os.getenv(NAME)\nNAME="BINDING_PROBE_INPUT"'
        ),
    ],
)
def test_public_closure_retains_known_identity_with_later_dynamic_context(
    tmp_path: Path, source: str
) -> None:
    """Known heads survive arguments; function globals are not definition snapshots."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    identities = {finding["identity"] for finding in report["orphan"]}
    assert identities & {"binding_probe_binary", "BINDING_PROBE_INPUT"}


def test_public_closure_joins_conditional_bindings(tmp_path: Path) -> None:
    """Alternative bindings retain both possible environment consumers."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import os\nif condition:\n    NAME="INPUT_A"\nelse:\n    NAME="INPUT_B"\nos.getenv(NAME)',
    )

    report = repository_semantic_closure(tmp_path)

    assert {finding["identity"] for finding in report["orphan"]} == {"INPUT_A", "INPUT_B"}


def test_public_closure_respects_imported_member_rebinding(tmp_path: Path) -> None:
    """Replacing a real module member cannot retain its former effect identity."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import subprocess as sp\nsp.run=lambda args: len(args)\nsp.run(["binding_probe_binary"])',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "pass", report
    assert report["orphan"] == []


@pytest.mark.parametrize(
    "source",
    [
        (
            'import importlib as loader\nmodule = loader.import_module("os")\n'
            'module.getenv("ETHOS_BOUNDARY_UNDECLARED")'
        ),
        (
            'from builtins import __import__ as load\nmodule = load("os")\n'
            'module.getenv("ETHOS_BOUNDARY_UNDECLARED")'
        ),
    ],
)
def test_public_closure_preserves_imported_module_effect(tmp_path: Path, source: str) -> None:
    """A dynamically imported known module retains the same effect contracts."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert any(
        item["kind"] == "value" and item["identity"] == "ETHOS_BOUNDARY_UNDECLARED"
        for item in report["orphan"]
    )


@pytest.mark.parametrize(
    "source",
    [
        (
            'import os\nNAME = "DECLARED_INPUT"\nclass Writer:\n'
            '    global NAME\n    NAME = "BINDING_PROBE_INPUT"\nos.getenv(NAME)'
        ),
        (
            'import os\nGLOBAL_KEY = "DECLARED_INPUT"\ndef outer():\n'
            '    local_key = "DECLARED_INPUT"\n    class Writer:\n'
            "        global GLOBAL_KEY\n        nonlocal local_key\n"
            '        GLOBAL_KEY = local_key = "BINDING_PROBE_INPUT"\n'
            "    os.getenv(local_key)\n    os.getenv(GLOBAL_KEY)"
        ),
    ],
)
def test_public_closure_preserves_immediate_class_outer_writes(tmp_path: Path, source: str) -> None:
    """Class execution writes to the compiler-selected global or enclosing owner."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    surface = tmp_path / "system/surfaces.toml"
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        surface.read_text(encoding="utf-8") + '\n[runtime]\ninputs = ["DECLARED_INPUT"]\n',
    )
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"BINDING_PROBE_INPUT"}


@pytest.mark.parametrize("iterations", [(), (0,), (0, 1)])
def test_public_closure_does_not_close_loop_recurrence(
    tmp_path: Path, iterations: tuple[int, ...]
) -> None:
    """Only iterations that reach the changed binding consume its new identity."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    surface = tmp_path / "system/surfaces.toml"
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        surface.read_text(encoding="utf-8") + '\n[runtime]\ninputs = ["DECLARED_INPUT"]\n',
    )
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        f'import os\nNAME = "DECLARED_INPUT"\nfor _ in {iterations!r}:\n'
        '    os.getenv(NAME)\n    NAME = "ETHOS_BOUNDARY_UNDECLARED"',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == ("block" if len(iterations) > 1 else "pass"), report
    assert {item["identity"] for item in report["orphan"]} == (
        {"ETHOS_BOUNDARY_UNDECLARED"} if len(iterations) > 1 else set()
    )


@pytest.mark.parametrize(
    "source",
    [
        'import os as environment\nenvironment.execv("binding_probe_binary", ["other_argv0"])',
        (
            "from os import execv as replace_process\n"
            'replace_process("binding_probe_binary", ["other_argv0"])'
        ),
    ],
)
def test_public_closure_observes_process_replacement_roles(tmp_path: Path, source: str) -> None:
    """Exec selects its executable separately from the process-visible argv zero."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}


@pytest.mark.parametrize(
    "source",
    [
        'import os\nos.execv = lambda *args: None\nos.execv("binding_probe_binary", ["other"])',
        (
            "class Local:\n    def execv(self, *args):\n        return len(args)\n"
            'os = Local()\nos.execv("binding_probe_binary", ["other"])'
        ),
    ],
)
def test_public_closure_does_not_invent_process_replacement(tmp_path: Path, source: str) -> None:
    """A native-looking name is not evidence of a process-replacement effect."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "pass", report
    assert report["orphan"] == []


@pytest.mark.parametrize(
    "source",
    [
        'import sys, subprocess\nsubprocess.run([sys.executable, "-m", "unowned.module"])',
        'import os, sys\nos.execv(sys.executable, ["display_name", "-m", "unowned.module"])',
    ],
)
def test_public_closure_preserves_native_interpreter_module(tmp_path: Path, source: str) -> None:
    """A proven interpreter origin observes its selected module, not an argv label."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    surface = tmp_path / "system/surfaces.toml"
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        surface.read_text(encoding="utf-8") + '\n[runtime]\nexecutables = ["python"]\n',
    )
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "partial", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"unowned"}


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (BindingValue(truths=frozenset({False})), BindingValue(strings=frozenset({"go"})), None),
        (BindingValue(truths=frozenset({True})), BindingValue(strings=frozenset({""})), None),
        (BindingValue(truths=frozenset({False})), BindingValue(strings=frozenset({""})), False),
        (BindingValue(truths=frozenset({True})), BindingValue(strings=frozenset({"go"})), True),
        (BindingValue(truths=frozenset({False})), BindingValue(items=(BindingValue(),)), None),
        (BindingValue(truths=frozenset({True})), BindingValue(items=()), None),
        (
            BindingValue(truths=frozenset({False})),
            BindingValue(entries=(("key", BindingValue()),)),
            None,
        ),
        (BindingValue(truths=frozenset({True})), BindingValue(entries=()), None),
        (BindingValue(entries=()), BindingValue(entries=(("key", BindingValue()),)), None),
        (
            BindingValue(entries=(("left", BindingValue()),)),
            BindingValue(entries=(("right", BindingValue()),)),
            None,
        ),
        (BindingValue(truths=frozenset({False})), BindingValue(unknown=True), None),
    ],
)
def test_native_truth_join_preserves_every_value_alternative(
    left: BindingValue, right: BindingValue, *, expected: bool | None
) -> None:
    """Native truth is a may-value join, never one carrier's preferred answer."""
    for first, second in ((left, right), (right, left)):
        joined = first.join(second)
        assert joined.truthiness() is expected
        assert joined.join(first).truthiness() is expected
        assert joined.join(second).truthiness() is expected


@pytest.mark.parametrize(
    ("left", "right", "left_truth", "right_truth"),
    [
        ("False", "'go'", False, True),
        ("True", "''", True, False),
        ("False", "''", False, False),
        ("True", "'go'", True, True),
        ("False", "['go']", False, True),
        ("True", "[]", True, False),
        ("{}", "{'key': 'go'}", False, True),
    ],
)
@pytest.mark.parametrize("flag", [False, True])
@pytest.mark.parametrize("in_function", [False, True])
def test_public_closure_preserves_mixed_native_truth_in_module_and_definition(
    tmp_path: Path,
    left: str,
    right: str,
    *,
    left_truth: bool,
    right_truth: bool,
    flag: bool,
    in_function: bool,
) -> None:
    """Closed module effects and deferred definition may-references stay distinct."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    body = f"chosen = {left} if flag else {right}\n"
    body += "if chosen: sp.run(['literal_join_probe'])\n"
    source = "import subprocess as sp\n"
    if in_function:
        source += "def entry(flag):\n"
        source += "".join(f"    {line}\n" for line in body.splitlines())
        source += f"entry({flag})\n" * 2
    else:
        source += f"flag = {flag}\n" + body
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)
    selected = (left_truth or right_truth) if in_function else (left_truth if flag else right_truth)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == ("block" if selected else "pass"), report
    assert {item["identity"] for item in report["orphan"]} == (
        {"literal_join_probe"} if selected else set()
    ), report


@pytest.mark.parametrize(
    "setup",
    [
        "data = {} if opaque else {'key': 'value'}",
        "data = {}\nif opaque: data['key'] = 'value'",
        "data = {} if opaque else {'key': 'value'}\ndata = data.values()",
        "owner = {}\ndata = owner.keys()\nif opaque: owner['key'] = 'value'",
        "owner = {}\ndata = owner.values()\nif opaque: owner['key'] = 'value'",
        "owner = {}\ndata = owner.items()\nif opaque: owner['key'] = 'value'",
    ],
)
def test_public_closure_preserves_every_mapping_shape(tmp_path: Path, setup: str) -> None:
    """Unknown selection keeps both live mapping branches observable."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    source = f"import subprocess as sp\n{setup}\n"
    source += "if data: sp.run(['nonempty_map_probe'])\n"
    source += "else: sp.run(['empty_map_probe'])\n"
    write_reference_source(tmp_path, "src/example/probe.py", source)
    report = repository_semantic_closure(tmp_path)
    assert {item["identity"] for item in report["orphan"]} == {
        "empty_map_probe",
        "nonempty_map_probe",
    }, report


@pytest.mark.parametrize(
    "value",
    [
        BindingValue(),
        BindingValue(strings=frozenset({"known"}), unknown=True, deferred=True),
        BindingValue(items=(BindingValue(strings=frozenset({"known"})),), ordered=True),
        BindingValue(fields=(("member", BindingValue(strings=frozenset({"known"}))),)),
        BindingValue(entries=(("key", BindingValue(local=True, unknown=True)),), ordered=True),
    ],
)
def test_binding_join_reuses_unchanged_immutable_facts(value: BindingValue) -> None:
    """An idempotent may-state join preserves meaning without rebuilding immutable facts."""
    assert value.join(value) is value
    equivalent = replace(value)
    assert value.join(equivalent) is value
