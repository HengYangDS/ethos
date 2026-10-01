"""Falsify Python consumer observations through their public repository owner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\nsubprocess.run(['probe-binary'])",
        "import subprocess as sp\nsp.run(['probe-binary'])",
        "from subprocess import run as launch\nlaunch(['probe-binary'])",
        "from subprocess import run\nrun(args=['probe-binary'])",
        "import subprocess\nlaunch = subprocess.run\nlaunch(['probe-binary'])",
    ],
)
def test_import_renaming_preserves_executable_observation(tmp_path: Path, source: str) -> None:
    """A spelling-only rewrite cannot erase the undeclared executable at audit."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "semantic_consumer_orphan:executable:probe-binary:src/example/probe.py"
    ]


@pytest.mark.parametrize(
    "source",
    [
        (
            "class Local:\n def run(self, args): return len(args)\n"
            "subprocess = Local()\nsubprocess.run(['probe-binary'])"
        ),
        "import subprocess\ndef f(subprocess):\n subprocess.run(['probe-binary'])",
        (
            "import subprocess\nclass Local:\n def run(self, args): return len(args)\n"
            "subprocess = Local()\nsubprocess.run(['probe-binary'])"
        ),
        "COMMAND = ['probe-binary']\n",
    ],
)
def test_local_names_and_inert_literals_cannot_invent_effects(source: str) -> None:
    """Imported names must survive lexical shadowing and program-point rebinding."""
    observed = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert observed.sources["executable"] == {}
    assert observed.unknown_paths == ()


@pytest.mark.parametrize(
    "source",
    [
        "import os as environment\nenvironment.getenv('PROBE_INPUT')",
        "from os import getenv as read\nread('PROBE_INPUT')",
        "from os import environ as env\nenv.get('PROBE_INPUT')",
        "import os\nNAME='PROBE_INPUT'\nos.getenv(NAME)\nNAME='UNRELATED'",
        (
            "import os\nNAME='PROBE_INPUT'\ndef read():\n return os.getenv(NAME)\n"
            "def unrelated():\n NAME='UNRELATED'\n return NAME"
        ),
        "import os\nNAME='UNRELATED'\nNAME='PROBE_INPUT'\nos.getenv(NAME)",
        "import os\nPREFIX='PROBE_'\nos.getenv(PREFIX + 'INPUT')",
    ],
)
def test_environment_binding_uses_its_scope_and_call_site(source: str) -> None:
    """Reads resolve their visible definitions rather than a file-wide last write."""
    observed = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert observed.sources["value"] == {"PROBE_INPUT": frozenset({"src/example/probe.py"})}
    assert observed.unknown_paths == ()


@pytest.mark.parametrize("level", [".", ".."])
@pytest.mark.parametrize(
    ("imports", "invocation", "kind"),
    [
        ("subprocess import run as launch", "launch(['probe-binary'])", "executable"),
        (" import subprocess as sp", "sp.run(['probe-binary'])", "executable"),
        ("os import getenv as read", "read('PROBE_INPUT')", "value"),
        (" import os as environment", "environment.getenv('PROBE_INPUT')", "value"),
    ],
)
def test_relative_imports_do_not_acquire_standard_library_identity(
    level: str, imports: str, invocation: str, kind: str
) -> None:
    """A relative binding cannot become an absolute native API by dropping dots."""
    source = f"from {level}{imports}\n{invocation}\n"

    observed = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert observed.sources[kind] == {}
    assert observed.unknown_paths == ()


def test_conditional_values_preserve_each_possible_consumer() -> None:
    """A branch join keeps both obligations instead of choosing the final text."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/probe.py": (
                "import os\nif flag:\n NAME='A'\nelse:\n NAME='B'\nos.getenv(NAME)"
            )
        }
    )

    assert set(observed.sources["value"]) == {"A", "B"}


@pytest.mark.parametrize(
    "source",
    [
        "import os\nos.getenv(compute_name())",
        "import subprocess\ngetattr(subprocess, operation)(['probe-binary'])",
        "import os\nNAME='GLOBAL'\ndef read():\n os.getenv(NAME)\n NAME='LOCAL'",
    ],
)
def test_unknown_semantics_preserve_resolved_sibling_observations(
    tmp_path: Path, source: str
) -> None:
    """Only the affected consumer is unknown; parsing cannot certify it complete."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)
    write_reference_source(tmp_path, "src/example/sibling.py", "VALUE = 'unrelated'")

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "unknown"
    assert report["coverage"] == "unknown"
    assert report["orphan"] == []
    unknown = report["unknown"]
    assert isinstance(unknown, list)
    assert unknown
    assert all(item["relation"] == "consumer" for item in unknown)
    assert all(item["sources"] == ["src/example/probe.py"] for item in unknown)


@pytest.mark.parametrize(
    ("source", "expected", "unresolved"),
    [
        (
            "import subprocess\nsubprocess.run('tool with spaces', shell=False)",
            {"tool with spaces"},
            False,
        ),
        ("import subprocess\nsubprocess.run('tool --version', shell=True)", {"tool"}, False),
        (
            "import subprocess\ngetattr(subprocess, 'run')(['probe-binary'])",
            {"probe-binary"},
            False,
        ),
        (
            "import subprocess\nlookup=getattr\nlookup(subprocess, operation)(['probe-binary'])",
            set(),
            True,
        ),
        (
            (
                "import subprocess\nif flag:\n launch=subprocess.run\nelse:\n launch=unknown\n"
                "launch(['probe-binary'])"
            ),
            {"probe-binary"},
            True,
        ),
        (
            "import subprocess\nif flag:\n launch=subprocess.run\nlaunch(['probe-binary'])",
            {"probe-binary"},
            True,
        ),
    ],
)
def test_call_semantics_preserve_objects_and_unresolved_alternatives(
    tmp_path: Path, source: str, expected: set[str], *, unresolved: bool
) -> None:
    """Shell flags, reaching branches and dynamic lookup have different meanings."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    orphan = report["orphan"]
    assert isinstance(orphan, list)
    assert {item["identity"] for item in orphan} == expected
    assert bool(report["unknown"]) is unresolved
    assert report["coverage"] == ("unknown" if unresolved else "evaluated")


def test_unresolved_value_does_not_discard_known_consumers_in_the_same_file(
    tmp_path: Path,
) -> None:
    """Incomplete value analysis cannot erase resolved evidence or taint other kinds."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import os\nimport subprocess\nos.getenv(compute_name())\nsubprocess.run(['probe-binary'])",
    )

    report = repository_semantic_closure(tmp_path)

    orphan, unknown = report["orphan"], report["unknown"]
    assert isinstance(orphan, list)
    assert isinstance(unknown, list)
    assert {item["identity"] for item in orphan} == {"probe-binary"}
    assert {item["kind"] for item in unknown} == {"value"}


@pytest.mark.parametrize(
    ("source", "executables", "inputs"),
    [
        ("import os\nread=lambda: os.getenv('PROBE')", set(), {"PROBE"}),
        ("import os\nvalues=[os.getenv('PROBE') for os in things]", set(), set()),
        (
            (
                "import subprocess\nsubprocess.run=lambda args: len(args)\n"
                "subprocess.run(['probe-binary'])"
            ),
            set(),
            set(),
        ),
        (
            "import subprocess\nsubprocess.run('first && second', shell=True)",
            {"first", "second"},
            set(),
        ),
        (
            "import subprocess\nsubprocess.run(['display-name'], executable='real-binary')",
            {"real-binary"},
            set(),
        ),
        ("import os\nwhile False:\n os.getenv('UNREACHABLE')", set(), set()),
        (
            (
                "import subprocess\ntry:\n risky()\nexcept Exception as subprocess:\n"
                " subprocess.run(['probe-binary'])"
            ),
            set(),
            set(),
        ),
    ],
)
def test_structured_binding_and_native_effect_distinctions(
    source: str, executables: set[str], inputs: set[str]
) -> None:
    """Binding and call contracts must survive syntax beyond the initial examples."""
    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(report.sources["executable"]) == executables
    assert set(report.sources["value"]) == inputs


def test_deferred_function_does_not_forget_an_earlier_possible_global_value() -> None:
    """A function called before reassignment cannot read only the final source value."""
    report = reference_consumer_sources_from_files(
        {
            "src/example/probe.py": (
                "import os\nNAME='BEFORE'\ndef read():\n os.getenv(NAME)\nread()\nNAME='AFTER'"
            )
        }
    )

    assert "BEFORE" in report.sources["value"] or "value" in report.unknown_consumers


@pytest.mark.parametrize(
    ("source", "executables", "imports", "unknown"),
    [
        ("import subprocess\nsubprocess.run(['git', 'status', *flags])", {"git"}, set(), set()),
        (
            "import subprocess\nsubprocess.run(['python', '-m', name])",
            {"python"},
            set(),
            {"import"},
        ),
        (
            "import subprocess\nsubprocess.run(['python', '-W', option, '-m', 'sample_module'])",
            {"python"},
            {"sample_module"},
            set(),
        ),
        (
            "import subprocess\nsubprocess.run(['uv', 'run', command])",
            {"uv"},
            set(),
            {"executable"},
        ),
        ("import subprocess\nsubprocess.run(['123'])", {"123"}, set(), set()),
        (
            "import subprocess\nsubprocess.run(['tool with spaces'])",
            {"tool with spaces"},
            set(),
            set(),
        ),
    ],
)
def test_unknown_arguments_affect_only_dependent_reference_obligations(
    source: str, executables: set[str], imports: set[str], unknown: set[str]
) -> None:
    """An argument vector is not shell syntax; only identity-relevant words matter."""
    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(report.sources["executable"]) == executables
    assert set(report.sources["import"]) == imports
    assert set(report.unknown_consumers) == unknown


@pytest.mark.parametrize(
    ("source", "inputs"),
    [
        ("import os\nvalues={key: os.environ[key] for key in ('A', 'B')}", {"A", "B"}),
        (
            "import os\nvalues=[os.getenv(key) for group in (('A', 'B'),) for key in group]",
            {"A", "B"},
        ),
        ("import os\nvalues=[os.getenv(key) for key in ()]", set()),
    ],
)
def test_finite_iteration_preserves_values_without_inventing_empty_iteration_effects(
    source: str, inputs: set[str]
) -> None:
    """Comprehension inputs are facts, not discarded parsing intermediates."""
    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(report.sources["value"]) == inputs
    assert report.unknown_consumers == {}


@pytest.mark.parametrize(
    "source",
    [
        "import shutil\nshutil.which('probe-binary')",
        "from shutil import which as locate\nmissing = locate(cmd='probe-binary') is None",
        "import shutil\nshutil.which(dynamic_name)",
        "import shutil as files\ngetattr(files, 'which')('probe-binary')",
        (
            "import shutil\nunavailable = [name for name in ('first', 'second') "
            "if shutil.which(name)]"
        ),
    ],
)
def test_executable_presence_probe_does_not_require_the_executable(
    tmp_path: Path, source: str
) -> None:
    """Checking absence, including forbidden-tool detection, is not execution."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "pass"
    assert report["coverage"] == "evaluated"
    assert report["required_gaps"] == []


@pytest.mark.parametrize(
    ("invocation", "verdict", "executables"),
    [
        ("subprocess.run([located])", "block", {"probe-binary"}),
        ("subprocess.run(['real-binary'])", "block", {"real-binary"}),
    ],
)
def test_presence_probe_does_not_erase_a_subsequent_execution(
    tmp_path: Path, invocation: str, verdict: str, executables: set[str]
) -> None:
    """A lookup result preserves executable identity only when actually invoked."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    source = "import shutil, subprocess\nlocated = shutil.which('probe-binary')\n" + invocation
    write_reference_source(tmp_path, "src/example/probe.py", source)

    report = repository_semantic_closure(tmp_path)
    observed = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert report["verdict"] == verdict
    assert set(observed.sources["executable"]) == executables
    assert bool(observed.unknown_consumers) is (verdict == "unknown")


@pytest.mark.parametrize(
    ("source", "executables", "unknown"),
    [
        (
            "import shutil, subprocess\nsubprocess.run(shutil.which('probe-binary'))",
            {"probe-binary"},
            False,
        ),
        (
            "import shutil, subprocess\nsubprocess.run([shutil.which(dynamic_name)])",
            set(),
            True,
        ),
        (
            "import shutil, subprocess\nsubprocess.run(['python', '-m', shutil.which('module')])",
            {"python"},
            True,
        ),
    ],
)
def test_lookup_paths_are_not_arbitrary_literal_argument_values(
    source: str, executables: set[str], *, unknown: bool
) -> None:
    """Preserve a resolved program identity without fabricating its path text."""
    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(report.sources["executable"]) == executables
    assert bool(report.unknown_consumers) is unknown


@pytest.mark.parametrize(
    ("transform", "executables", "unknown"),
    [
        ("str(Path(located).resolve())", {"probe-binary"}, False),
        ("Path(located).absolute().as_posix()", {"probe-binary"}, False),
        ("Path(located).with_name('replacement')", set(), True),
        ("Path(located).parent", set(), True),
    ],
)
def test_native_path_conversion_preserves_only_the_same_executable(
    transform: str, executables: set[str], *, unknown: bool
) -> None:
    """Native identity-preserving conversions differ from changing the target."""
    source = (
        "import shutil, subprocess\nfrom pathlib import Path\n"
        "located = shutil.which('probe-binary')\n"
        f"subprocess.run([{transform}])"
    )

    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(report.sources["executable"]) == executables
    assert bool(report.unknown_consumers) is unknown


@pytest.mark.parametrize(
    ("definition", "invocation", "executables", "inputs"),
    [
        (
            "def launch(command):\n subprocess.run(command)\n",
            "launch(['probe-binary'])",
            {"probe-binary"},
            set(),
        ),
        (
            "def read(name='DEFAULT', *, other='SECOND'):\n os.getenv(name)\n os.getenv(other)\n",
            "read(other='OVERRIDE')",
            set(),
            {"DEFAULT", "OVERRIDE", "SECOND"},
        ),
        (
            "def make(name, /, *flags):\n return [name, *flags]\n",
            "subprocess.run(make('probe-binary', '--version'))",
            {"probe-binary"},
            set(),
        ),
        (
            "def apply(callback, command):\n callback(command)\n",
            "apply(subprocess.run, ['probe-binary'])",
            {"probe-binary"},
            set(),
        ),
    ],
)
def test_local_calls_preserve_argument_default_callback_and_return_relations(
    definition: str, invocation: str, executables: set[str], inputs: set[str]
) -> None:
    """Known call sites add concrete evidence without erasing open-call uncertainty."""
    source = "import os, subprocess\n" + definition + invocation

    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(report.sources["executable"]) == executables
    assert set(report.sources["value"]) == inputs


def test_recursive_local_call_retains_unknown_without_unbounded_expansion() -> None:
    """A recursive result cannot become a guessed executable or infinite analysis."""
    source = (
        "import subprocess\ndef recurse(value):\n return recurse(value)\n"
        "subprocess.run(recurse(['probe-binary']))"
    )

    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert report.sources["executable"] == {}
    assert "executable" in report.unknown_consumers


def test_local_bare_return_cannot_erase_an_invalid_execution_argument() -> None:
    """Returning None is a value, not an empty analysis set that silently passes."""
    source = "import subprocess\ndef empty():\n return\nsubprocess.run(empty())"

    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert report.sources["executable"] == {}
    assert "executable" in report.unknown_consumers


def test_nested_definition_does_not_return_from_its_enclosing_call() -> None:
    """Deferred child analysis must not add child returns to a parent's result."""
    source = (
        "import subprocess\ndef outer():\n"
        " def child():\n  return ['not-the-result']\n"
        " return ['actual-result']\nsubprocess.run(outer())"
    )

    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(report.sources["executable"]) == {"actual-result"}


def test_decorated_function_does_not_acquire_undecorated_return_identity() -> None:
    """An unknown decorator can replace the callable before any invocation."""
    source = (
        "import subprocess\n@replacement\ndef make():\n return ['not-proven']\n"
        "subprocess.run(make())"
    )

    report = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert report.sources["executable"] == {}
    assert "executable" in report.unknown_consumers


@pytest.mark.parametrize(
    ("module", "unknown"),
    [
        ("shutil", {"executable"}),
        ("os.path", {"value"}),
        ("subprocess", {"executable"}),
        ("os", {"value"}),
    ],
)
def test_unresolved_native_attribute_retains_its_unknown_consumer_scope(
    module: str, unknown: set[str]
) -> None:
    """An unmodeled callee, such as os.path.expandvars, may read native inputs."""
    source = f"import {module}\ngetattr({module}, operation)('probe')"

    observed = reference_consumer_sources_from_files({"src/example/probe.py": source})

    assert set(observed.unknown_consumers) == unknown


@pytest.mark.parametrize("operator", ["=", "+="])
def test_shell_array_storage_does_not_execute_its_literal_elements(operator: str) -> None:
    """Initial and appended argv literals have the same non-executing meaning."""
    source = f"arguments{operator}(--entrypoint /workspace/custom-script.sh)\n"
    workflow = "jobs:\n  check:\n    steps:\n      - run: " + source.strip() + "\n"

    observed = reference_consumer_sources_from_files({".github/workflows/check.yml": workflow})

    assert observed.sources["executable"] == {}
