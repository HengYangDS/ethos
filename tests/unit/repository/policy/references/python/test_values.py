"""Observe bounded Python reference meaning through the public closure owner."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.python.bindings import BindingScope
from ethos.repository.policy.references.python.bindings import BindingValue
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("read", "verdict", "orphans"),
    [
        ("if name:\n    os.getenv(name)", "pass", set()),
        ('os.getenv(name) if name else ""', "pass", set()),
        ("name and os.getenv(name)", "pass", set()),
        ("if not name:\n    os.getenv(name)", "block", {""}),
    ],
)
def test_public_closure_preserves_guarded_input_applicability(
    tmp_path: Path, read: str, verdict: str, orphans: set[str]
) -> None:
    """A positive guard excludes empty names only on the path that proves it."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    surface = tmp_path / "system/surfaces.toml"
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        surface.read_text() + '\n[runtime]\ninputs = ["DECLARED_INPUT"]\n',
    )
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import os\nname = "DECLARED_INPUT" if condition else ""\n' + read,
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == verdict, report
    assert {item["identity"] for item in report["orphan"]} == orphans, report


@pytest.mark.parametrize(
    "expression",
    ["str(Path(executable).resolve())", "Path(executable).absolute().as_posix()"],
)
def test_public_closure_preserves_executable_origin_through_native_path(
    tmp_path: Path, expression: str
) -> None:
    """Path presentation cannot erase the executable selected by a native lookup."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import shutil, subprocess\nfrom pathlib import Path\n"
        'executable = shutil.which("binding_probe_binary")\n'
        f'if executable:\n    subprocess.run([{expression}, "--version"])',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"binding_probe_binary"}, report


@pytest.mark.parametrize(
    ("command", "coverage"),
    [
        ('["binding_probe_binary"] if condition else factory()', "unknown"),
        ('["binding_probe_binary", argument]', "evaluated"),
    ],
)
def test_public_closure_preserves_command_container_alternatives(
    tmp_path: Path, command: str, coverage: str
) -> None:
    """Opaque command alternatives differ from unresolved trailing arguments."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    surface = tmp_path / "system/surfaces.toml"
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        surface.read_text() + '\n[runtime]\nexecutables = ["binding_probe_binary"]\n',
    )
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        f"import subprocess\nfrom example import factory\nargs = {command}\nsubprocess.run(args)",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == coverage, report
    assert report["verdict"] == ("unknown" if coverage == "unknown" else "pass"), report
    assert not report["orphan"], report
    assert bool(report["unknown"]) == (coverage == "unknown"), report


@pytest.mark.parametrize(
    ("default", "coverage"),
    [("mutate(data)", "unknown"), ('"example"', "evaluated")],
)
def test_public_closure_reads_bound_receiver_after_argument_effects(
    tmp_path: Path, default: str, coverage: str
) -> None:
    """A bound mapping method reads current contents after its eager arguments."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import importlib\nfrom example import mutate\ndata = {"key": "example"}\n'
        f'value = data.get("key", {default})\nimportlib.import_module(value)',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == coverage, report
    assert report["verdict"] == ("unknown" if coverage == "unknown" else "pass"), report
    assert not report["orphan"], report


@pytest.mark.parametrize(
    ("selected", "verdict", "orphans"),
    [("saved", "block", {"unowned"}), ("current", "pass", set())],
)
def test_public_closure_preserves_prior_allocations_at_recurrent_sites(
    tmp_path: Path, selected: str, verdict: str, orphans: set[str]
) -> None:
    """A later allocation cannot rewrite an earlier object retained by an alias."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import importlib\nsaved = {}\nfor module in ("unowned.module", "example"):\n'
        '    current = {"key": module}\n    saved = saved or current\n'
        f'importlib.import_module({selected}["key"])',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == verdict, report
    assert {item["identity"] for item in report["orphan"]} == orphans, report


@pytest.mark.parametrize(
    "source",
    [
        'mapping = {"key": "unowned.module"}\nimportlib.import_module(mapping[selected])',
        (
            'mapping = {"one": "unowned.module", "two": "example"}\n'
            "for name in tuple(dict.fromkeys(mapping.values())):\n"
            "    importlib.import_module(name)"
        ),
        (
            'mapping = {"one": "unowned.module", "two": "example"}\n'
            "def load(key):\n"
            "    if key in mapping:\n        selected = (mapping[key],)\n"
            "    elif key:\n        selected = ()\n"
            "    else:\n        selected = tuple(dict.fromkeys(mapping.values()))\n"
            "    for name in selected:\n        importlib.import_module(name)"
        ),
    ],
)
def test_public_closure_preserves_bounded_mapping_choices(tmp_path: Path, source: str) -> None:
    """Unknown selection cannot invent values outside a complete finite native mapping."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", "import importlib\n" + source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"unowned"}


@pytest.mark.parametrize(
    ("source", "coverage", "verdict"),
    [
        ('name = "example" or environment.getenv("unowned")', "evaluated", "pass"),
        ('name = "" or "unowned.module"\nimportlib.import_module(name)', "evaluated", "block"),
        (
            (
                'def read(config):\n    name = str(config.get("name") or "DECLARED_INPUT")\n'
                "    return environment.getenv(name)"
            ),
            "partial",
            "pass",
        ),
    ],
)
def test_public_closure_preserves_short_circuit_value_provenance(
    tmp_path: Path, source: str, coverage: str, verdict: str
) -> None:
    """Short-circuit results retain caller provenance without executing impossible effects."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    surface = tmp_path / "system/surfaces.toml"
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        surface.read_text() + '\n[runtime]\ninputs = ["DECLARED_INPUT"]\n',
    )
    write_reference_source(
        tmp_path, "src/example/probe.py", "import importlib\nimport os as environment\n" + source
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == coverage, report
    assert report["verdict"] == verdict, report
    assert not report["unknown"], report


@pytest.mark.parametrize(
    "source",
    [
        (
            'data = {"key": "example"}\nalias = data if condition else factory()\n'
            'importlib.import_module(alias["key"])'
        ),
        'convert = str if condition else factory()\nimportlib.import_module(convert("example"))',
    ],
)
def test_public_closure_retains_unknown_value_alternatives(tmp_path: Path, source: str) -> None:
    """Aggregate refresh and supported returns cannot erase an opaque alternative."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import importlib\nfrom example import factory\n" + source,
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == report["coverage"] == "unknown", report
    assert not report["orphan"], report
    assert any(item["kind"] == "import" for item in report["unknown"]), report


def test_public_closure_preserves_live_mapping_views(tmp_path: Path) -> None:
    """A live view observes mutations before its next yielded value."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import importlib\ndata = {"first": "example", "second": "example"}\n'
        "view = data.values()\nfor name in view:\n"
        '    data["second"] = "unowned.module"\n    importlib.import_module(name)',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"unowned"}


@pytest.mark.parametrize(
    ("source", "executes"),
    [
        ('import shutil\nassert shutil.which("binding_probe_binary") is None', False),
        ('from shutil import which as locate\nlocate("binding_probe_binary")', False),
        (
            (
                "import shutil, subprocess\n"
                'executable = shutil.which("binding_probe_binary")\n'
                'if executable:\n    subprocess.run([executable, "--version"])'
            ),
            True,
        ),
    ],
)
def test_public_closure_distinguishes_executable_lookup_from_use(
    tmp_path: Path, source: str, *, executes: bool
) -> None:
    """A lookup is not execution; its result retains executable identity when used."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == ("block" if executes else "pass"), report
    assert {item["identity"] for item in report["orphan"]} == (
        {"binding_probe_binary"} if executes else set()
    )
    assert report["uncertainties"] == []


@pytest.mark.parametrize(
    "body",
    [
        "subprocess.run([command.as_posix(), '--version'])",
        "module, _, attribute = command.partition(':')\n    importlib.import_module(module)",
        "subprocess.run(command[0])",
        "subprocess.run([str(command), '--version'])",
    ],
)
def test_public_closure_preserves_caller_value_provenance(tmp_path: Path, body: str) -> None:
    """Supported transformations keep caller-owned values deferred, not closed."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        f"import subprocess, importlib\ndef consume(command):\n    {body}",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "partial", report
    assert report["verdict"] == "pass", report
    assert report["orphan"] == []
    assert len(report["uncertainties"]) == 1
    assert report["uncertainties"][0]["state"] == "deferred"


@pytest.mark.parametrize(
    ("source", "verdict", "coverage"),
    [
        (
            (
                'import subprocess\ncommands = (["binding_probe_binary"], ["git"])\n'
                "subprocess.run(commands[0])"
            ),
            "block",
            "evaluated",
        ),
        (
            "import subprocess\nfrom example import factory\nsubprocess.run(factory())",
            "unknown",
            "unknown",
        ),
        (
            (
                "import subprocess\nfrom example import factory\n"
                "def consume(parameter):\n    subprocess.run(factory(parameter))"
            ),
            "unknown",
            "unknown",
        ),
        (
            (
                "import subprocess\ndef factory(ignored):\n"
                '    return ["binding_probe_binary"]\n'
                "def consume(parameter):\n    subprocess.run(factory(parameter))"
            ),
            "block",
            "evaluated",
        ),
    ],
)
def test_public_closure_does_not_defer_closed_unresolved_values(
    tmp_path: Path, source: str, verdict: str, coverage: str
) -> None:
    """Literal selection is exact; an unmodeled factory is not a runtime parameter."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == coverage, report
    assert report["verdict"] == verdict, report
    assert {item["identity"] for item in report["orphan"]} == (
        {"binding_probe_binary"} if verdict == "block" else set()
    )


@pytest.mark.parametrize(
    "body",
    [
        'importlib.import_module(modules["first"])',
        "for module in modules.values():\n    importlib.import_module(module)",
        "for _, module in modules.items():\n    importlib.import_module(module)",
    ],
)
def test_public_closure_observes_finite_mapping_values(tmp_path: Path, body: str) -> None:
    """Literal mappings retain values and ordered iteration without string guessing."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import importlib\nmodules = {"first": "unowned.module", "second": "example"}\n' + body,
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert report["coverage"] == "evaluated", report
    assert report["uncertainties"] == []
    assert {item["identity"] for item in report["orphan"]} == {"unowned"}


def test_public_closure_preserves_mapping_iteration_program_points(tmp_path: Path) -> None:
    """A later mapping value reaches a later iteration, never the first one."""
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
        'import os\nNAME = "DECLARED_INPUT"\n'
        'for name in {"first": "BINDING_PROBE_INPUT", "second": "DECLARED_INPUT"}.values():\n'
        "    os.getenv(NAME)\n    NAME = name",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"BINDING_PROBE_INPUT"}


@pytest.mark.parametrize(
    ("body", "verdict"),
    [
        ('alias = data\nalias["key"] = "unowned.module"', "block"),
        ("from example import mutate\nmutate(data)", "unknown"),
        (
            (
                'other = {"key": "example"}\nalias = data if condition else other\n'
                'alias["key"] = "example"'
            ),
            "block",
        ),
    ],
)
def test_public_closure_preserves_mutable_alias_effects(
    tmp_path: Path, body: str, verdict: str
) -> None:
    """Strong singleton writes, weak may-writes and opaque effects stay distinct."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import importlib\ndata = {"key": "unowned.module"}\n'
        + body
        + '\nimportlib.import_module(data["key"])',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == verdict, report
    assert {item["identity"] for item in report["orphan"]} == (
        {"unowned"} if verdict == "block" else set()
    )
    assert report["coverage"] == ("unknown" if verdict == "unknown" else "evaluated"), report


def test_public_closure_resolves_literal_interpolation(tmp_path: Path) -> None:
    """Formatting a closed literal retains its identity, not generic expression UNKNOWN."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        'import importlib\nname = "unowned"\nimportlib.import_module(f"{name}.module")',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"unowned"}


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


def test_binding_single_continuation_does_not_rejoin_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    """A single already-joined continuation needs custody copying, not another lattice join."""
    branch = BindingScope("branch")
    value = BindingValue(strings=frozenset({"known"}), unknown=True)
    branch.values["selected"] = value
    branch.history["selected"] = value
    branch.members["imported.member"] = value
    branch.member_history["imported.member"] = value
    target = BindingScope("target")

    def unexpected_join(_self: BindingValue, _other: BindingValue) -> BindingValue:
        pytest.fail("A single continuation has no competing fact to join")

    def unexpected_lookup(_self: BindingScope, _name: str, *, later: bool = False) -> BindingValue:
        pytest.fail(f"An already-materialized continuation needs no member lookup: {later}")

    monkeypatch.setattr(BindingValue, "join", unexpected_join)
    monkeypatch.setattr(BindingScope, "member", unexpected_lookup)
    target.merge(branch)

    assert target.values == branch.values
    assert target.history == branch.history
    assert target.members == branch.members
    assert target.member_history == branch.member_history
    assert target.values is not branch.values
    assert target.members is not branch.members


@pytest.mark.parametrize(
    ("literal", "selected"),
    [
        ("True", True),
        ("False", False),
        ("1", True),
        ("0", False),
        ("1.5", True),
        ("0.0", False),
        ("1j", True),
        ("0j", False),
        ("b'x'", True),
        ("b''", False),
        ("None", False),
    ],
)
def test_public_closure_preserves_native_literal_branch(
    tmp_path: Path, literal: str, *, selected: bool
) -> None:
    """Closed primitive truth selects one callback; arbitrary object truth stays open."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess as sp\ndef noop(command): return None\n"
        "def entry(callback, flag):\n"
        "    (callback if flag else noop)(['literal_probe'])\n" + f"entry(sp.run, {literal})\n" * 2,
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "evaluated", report
    assert report["verdict"] == ("block" if selected else "pass"), report
    assert {item["identity"] for item in report["orphan"]} == (
        {"literal_probe"} if selected else set()
    ), report
