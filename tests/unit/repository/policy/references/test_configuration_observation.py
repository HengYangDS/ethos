"""Public reference observations reject malformed consumed shapes without effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files

if TYPE_CHECKING:
    from collections.abc import Mapping


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("package.json", '{"scripts": []}'),
        ("package.json", '{"scripts": {"verify": 1}}'),
        ("pyproject.toml", '[project]\nscripts = "abc"'),
        ("pyproject.toml", 'build-system = "x"'),
        ("pyproject.toml", "[project]\noptional-dependencies = []"),
        ("pyproject.toml", '[build-system]\nrequires = "abc"'),
        ("pyproject.toml", '[project]\ndependencies = ["Requests>=2", 42]'),
        (".github/workflows/ci.yml", "jobs: &jobs\n  recursive: *jobs\n"),
        ("src/example/probe.py", "def closure():\n    nonlocal absent\n"),
        ("src/example/probe.py", "def closure(value):\n    global value\n"),
        ("src/example/probe.py", "return\n"),
    ],
)
def test_public_observation_marks_invalid_carrier_unknown(path: str, source: str) -> None:
    """Syntax-valid malformed shapes never invent identities or escape as errors."""
    observation = product_references_from_files({path: source})
    consumption = reference_consumer_sources_from_files({path: source})

    assert observation.unknown_paths == (path,)
    assert consumption.unknown_paths == (path,)
    assert observation.references["executable"] == set()


@pytest.mark.parametrize(
    ("path", "source", "expected"),
    [
        (
            "package.json",
            '{"scripts":{"verify":"probe-tool --check"}}',
            {"executable": {"probe-tool"}},
        ),
        (
            "pyproject.toml",
            ('[project]\nname = "probe-package"\n[project.scripts]\nprobe = "probe.cli:main"'),
            {"distribution": {"probe-package"}, "executable": {"probe"}},
        ),
        (
            ".github/workflows/ci.yml",
            ("first: &step\n  run: probe-tool --check\nsecond: *step\n"),
            {"executable": {"probe-tool"}},
        ),
    ],
)
def test_public_observation_preserves_valid_native_carrier(
    path: str, source: str, expected: Mapping[str, set[str]]
) -> None:
    """Valid aliases, native scripts and owned declarations retain their meaning."""
    observation = product_references_from_files({path: source})

    assert observation.unknown_paths == ()
    for kind, identities in expected.items():
        assert observation.references[kind] == identities
