"""Preserve current bindings and references across first-party call boundaries."""

from __future__ import annotations

import pytest

from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files
from ethos.repository.policy.references.python.binding import PythonFlow
from ethos.repository.policy.references.python.program import bind_repository_python


@pytest.mark.parametrize("cross_module", [False, True])
def test_function_observes_later_binding_and_conserves_prior_reference(
    *, cross_module: bool
) -> None:
    """Changed source bindings cannot inherit a previous call's accepted identity."""
    prefix = "import subprocess\nNAME='first-binary'\ndef executable():\n return NAME\n"
    calls = "subprocess.run([executable()])"
    files = (
        {
            "src/example/effects.py": prefix,
            "src/example/use.py": (
                "import subprocess\nfrom example.effects import executable\n"
                + calls
                + "\nimport example.effects\nexample.effects.NAME='second-binary'\n"
                + calls
            ),
        }
        if cross_module
        else {"src/example/use.py": prefix + calls + "\nNAME='second-binary'\n" + calls}
    )

    observed = reference_consumer_sources_from_files(files)

    assert "first-binary" in observed.sources["executable"]
    assert (
        "second-binary" in observed.sources["executable"]
        or "executable" in observed.unknown_consumers
    )


def test_repeated_mutating_function_cannot_preserve_a_stale_argument() -> None:
    """Static reuse cannot suppress the alias invalidation owned by a real call."""
    source = (
        "import subprocess\ndef rewrite(argv):\n argv[0]='changed-binary'\n"
        "argv=['first-binary']\nsubprocess.run(argv)\nrewrite(argv)\n"
        "rewrite(argv)\nsubprocess.run(argv)"
    )

    observed = reference_consumer_sources_from_files({"src/example/use.py": source})

    assert "first-binary" in observed.sources["executable"]
    assert "executable" in observed.unknown_consumers


@pytest.mark.parametrize("context_only", [False, True])
def test_patch_consumer_uses_the_same_first_party_binding(*, context_only: bool) -> None:
    """Selecting one changed consumer still includes its actual source dependencies."""
    files = {
        "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
        "src/example/use.py": "from example.effects import launch\nlaunch(['probe-binary'])",
    }
    selected = {"src/example/use.py": files["src/example/use.py"]} if context_only else files

    observed = product_references_from_files(selected, context_files=files)

    assert "probe-binary" in observed["executable"]


def test_function_local_import_observes_a_changed_module_member() -> None:
    """A binding read inside the function is still an input, not a pure literal."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": "NAME='first-binary'",
            "src/example/use.py": (
                "import subprocess\ndef executable():\n"
                " from example.effects import NAME\n return NAME\n"
                "subprocess.run([executable()])\nsubprocess.run([executable()])\n"
                "import example.effects\n"
                "example.effects.NAME='second-binary'\nsubprocess.run([executable()])"
            ),
        }
    )

    assert "first-binary" in observed.sources["executable"]
    assert (
        "second-binary" in observed.sources["executable"]
        or "executable" in observed.unknown_consumers
    )


def test_conditional_shell_cannot_erase_a_known_executable() -> None:
    """Formal control values do not remove concrete identities at the same sink."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/use.py": (
                "import subprocess\ndef launch(shell):\n"
                " subprocess.run(['probe-binary'], shell=shell)"
            )
        }
    )

    assert "probe-binary" in observed.sources["executable"]
    assert observed.requests


def test_unavailable_first_party_source_does_not_leave_caller_evaluated() -> None:
    """A failed source binding affects its caller, not unrelated carriers."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": "import subprocess\ndef launch(",
            "src/example/use.py": "from example.effects import launch\nlaunch(['probe-binary'])",
            "src/example/pure.py": "VALUE=1",
        }
    )

    assert "src/example/effects.py" in observed.unknown_paths
    assert "src/example/use.py" in observed.unknown_consumers.get("reference", ())
    assert "src/example/pure.py" not in observed.unknown_consumers.get("reference", ())


def test_patch_reference_context_evaluates_only_its_actual_dependency_closure(monkeypatch) -> None:
    """Unrelated source context supplies names, not a repeated whole-repository workload."""
    actual = []
    original = PythonFlow.block

    def observe(self, *args, **kwargs):
        actual.append(self.path)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(PythonFlow, "block", observe)
    selected = {
        "src/example/use.py": "from example.effects import launch\nlaunch(['probe-binary'])"
    }
    context = {
        "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
        "src/unrelated/other.py": "import os\nVALUE=os.getenv('UNRELATED_INPUT')",
    }

    observed = product_references_from_files(selected, context_files=context)

    assert "probe-binary" in observed["executable"]
    assert "src/unrelated/other.py" not in actual
    assert "UNRELATED_INPUT" not in observed["value"]


def test_definition_relations_reuse_one_parametric_observation(monkeypatch) -> None:
    """Uncalled wrappers compose one callee meaning, not forty concrete executions."""
    visits = []
    original = PythonFlow.block

    def observe(self, *args, **kwargs):
        if self.current is not None:
            visits.append(self.current.name)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(PythonFlow, "block", observe)
    files = {
        "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
        "src/example/use.py": "from example.effects import launch\n"
        + "\n".join(f"def wrapper{i}(argv):\n launch(argv)" for i in range(40)),
    }

    observed = reference_consumer_sources_from_files(files)

    assert observed.sources["executable"] == {}
    assert observed.requests
    assert visits.count("launch") <= 2


def test_unused_wrapper_preserves_a_fixed_callee_native_identity() -> None:
    """Composing definitions retains fixed inputs even without a top-level invocation."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
            "src/example/use.py": (
                "from example.effects import launch\ndef wrapper():\n launch(['probe-binary'])"
            ),
        }
    )

    assert "probe-binary" in observed.sources["executable"]


def test_definition_summary_preserves_return_and_parameter_relations() -> None:
    """A supported returned input remains substitutable, not a generic UNKNOWN."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/use.py": (
                "import os\ndef identity(value):\n return value\n"
                "def read(name):\n os.getenv(identity(name))\n"
                "def fixed():\n os.getenv(identity('PROBE_INPUT'))"
            )
        }
    )

    assert "PROBE_INPUT" in observed.sources["value"]
    assert observed.requests


def test_source_order_cannot_spend_an_unrelated_callers_analysis_budget() -> None:
    """An independent source call has the same result regardless of inventory order."""
    files = {
        "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
        "src/example/other.py": "from example.effects import launch\n"
        + "\n".join("launch(['other-binary'])" for _ in range(1030)),
        "src/example/use.py": "from example.effects import launch\nlaunch(['probe-binary'])",
    }

    forward = bind_repository_python(files)
    reverse = bind_repository_python(dict(reversed(tuple(files.items()))))

    assert forward["src/example/use.py"] == reverse["src/example/use.py"]
