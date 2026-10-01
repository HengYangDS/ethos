"""Observe native mapping identity independently of unknown entry contents."""

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
    ("construction", "read", "inputs", "unknown"),
    [
        ("{**opaque, 'key': 'PROBE_INPUT'}", "values['key']", {"PROBE_INPUT"}, False),
        ("{'key': 'PROBE_INPUT', **opaque}", "values['key']", {"PROBE_INPUT"}, True),
        ("{**opaque}", "values.get('key', 'DEFAULT_INPUT')", {"DEFAULT_INPUT"}, True),
        ("{'key': 'PROBE_INPUT'}.copy()", "values['key']", {"PROBE_INPUT"}, False),
        ("dict({'key': 'PROBE_INPUT'})", "values.get('key')", {"PROBE_INPUT"}, False),
        ("dict(**{'key': 'PROBE_INPUT'})", "values['key']", {"PROBE_INPUT"}, False),
    ],
)
def test_native_mapping_keeps_known_overrides_and_unknown_remainders(
    construction: str, read: str, inputs: set[str], *, unknown: bool
) -> None:
    """Unknown expansion can overwrite earlier entries but not later explicit keys."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": f"import os\nvalues={construction}\nos.getenv({read})"}
    )

    assert set(observed.sources["value"]) == inputs
    assert bool(observed.unknown_consumers) is unknown
    assert observed.unknown_paths == ()


@pytest.mark.parametrize(
    "construction", ["{**os.environ}", "os.environ.copy()", "dict(os.environ)"]
)
def test_environment_snapshot_is_a_mapping_not_a_live_environment_owner(construction: str) -> None:
    """Removing a copied key is not an unresolved method on the original environment."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": f"import os\nvalues={construction}\nvalues.pop('REMOVED', None)"}
    )

    assert observed.sources["value"] == {}
    assert observed.unknown_consumers == {}


@pytest.mark.parametrize(
    "construction", ["{**os.environ}", "os.environ.copy()", "dict(os.environ)"]
)
def test_environment_snapshot_reads_retain_their_source_input(construction: str) -> None:
    """A snapshot does not erase the environmental provenance of a returned entry."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": f"import os\nvalues={construction}\nvalues.get('PROBE_INPUT')"}
    )

    assert set(observed.sources["value"]) == {"PROBE_INPUT"}
    assert observed.unknown_consumers == {}


@pytest.mark.parametrize("construction", ["{**opaque}", "{**opaque, 'shell': False}"])
def test_open_mapping_cannot_certify_keyword_argument_completeness(construction: str) -> None:
    """A known dictionary type cannot prove the keys forwarded to a process call."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": f"import subprocess\nsubprocess.run(['git'], **{construction})"}
    )

    assert "executable" in observed.unknown_consumers


def test_copied_mapping_mutation_cannot_invalidate_the_original() -> None:
    """A native copy has its own allocation while nested mutable values remain shared."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/probe.py": (
                "import os\noriginal={'key': 'PROBE_INPUT'}\n"
                "copied=original.copy()\nmutate(copied)\nos.getenv(original['key'])"
            )
        }
    )

    assert set(observed.sources["value"]) == {"PROBE_INPUT"}
    assert observed.unknown_consumers == {}


@pytest.mark.parametrize("construction", ["original.copy()", "dict(original)", "{**original}"])
def test_native_mapping_copy_preserves_nested_mutable_aliases(construction: str) -> None:
    """Copying a dictionary only separates its outer allocation, not nested values."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/probe.py": (
                "import subprocess\noriginal={'args': ['git']}\n"
                f"copied={construction}\nmutate(copied['args'])\n"
                "subprocess.run(**original)"
            )
        }
    )

    assert "executable" in observed.unknown_consumers


def test_environment_snapshot_override_replaces_only_the_selected_entry() -> None:
    """A source-map override cannot invent an environment dependency for that entry."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/probe.py": (
                "import os\nvalues={**os.environ, 'local': 'PROBE_INPUT'}\n"
                "os.getenv(values['local'])\nvalues.get('ORIGINAL_INPUT')"
            )
        }
    )

    assert set(observed.sources["value"]) == {"PROBE_INPUT", "ORIGINAL_INPUT"}
    assert observed.unknown_consumers == {}


def test_later_environment_snapshot_can_replace_an_earlier_explicit_entry() -> None:
    """Potential input provenance survives only the override that can actually supply it."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/probe.py": (
                "import os\nvalues={'earlier': 'local', **os.environ}\nvalues.get('earlier')"
            )
        }
    )

    assert set(observed.sources["value"]) == {"earlier"}
    assert observed.unknown_consumers == {}


@pytest.mark.parametrize("entry", ["os.environ", "getattr(os.environ, method)"])
def test_storing_an_environment_object_does_not_turn_dictionary_keys_into_inputs(
    entry: str,
) -> None:
    """A value's origin does not identify the mapping operation that returned it."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": f"import os\nvalues={{'local': {entry}}}\nvalues.get('local')"}
    )

    assert observed.sources["value"] == {}
    assert observed.unknown_consumers == {}


def test_unknown_environment_mapping_construction_retains_partial_coverage() -> None:
    """Known output type cannot resolve which unknown imported behavior supplied entries."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/probe.py": (
                "import os\nvalues={**getattr(os.environ, operation)}\nvalues.get('PROBE_INPUT')"
            )
        }
    )

    assert "value" in observed.unknown_consumers


def test_public_closure_accepts_known_override_without_claiming_unknown_shape(
    tmp_path: Path,
) -> None:
    """Public ownership closes a resolved read even when unrelated mapping keys are open."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    with (tmp_path / "system/surfaces.toml").open("a") as stream:
        stream.write('\n[runtime]\ninputs=["PROBE_INPUT"]\n')
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import os\nvalues={**opaque, 'key': 'PROBE_INPUT'}\nos.getenv(values['key'])",
    )

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"
