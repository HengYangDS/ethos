from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.observation import npm_script_commands
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_gaps
from ethos.repository.policy.references.observation import repository_product_references
from ethos.repository.policy.references.observation import repository_reference_files

if TYPE_CHECKING:
    from pathlib import Path


def _observed() -> dict[str, set[str]]:
    return {
        "command": set(),
        "distribution": set(),
        "executable": set(),
        "import": set(),
        "reference": set(),
        "value": set(),
    }


def test_repository_public_observation_skips_unreadable_reference_carriers(tmp_path: Path) -> None:
    skill = tmp_path / ".agents/skills/sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("good\n", encoding="utf-8")
    (skill / "bad.md").write_bytes(b"\xff")

    files = repository_reference_files(tmp_path)
    observed = repository_product_references(tmp_path)

    assert files == {".agents/skills/sample/SKILL.md": "good\n"}
    assert observed == _observed()


def test_repository_public_observation_discovers_command_sources_and_skips_unreadable_python(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/ethos"
    source.mkdir(parents=True)
    (source / "app.py").write_text("App()\n", encoding="utf-8")
    (source / "bad.py").write_bytes(b"\xff")

    observed = product_references_from_files({}, root=tmp_path)

    assert observed == _observed()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[project]\nname = 'Valid_Name'\n", {"valid-name"}),
        ("[project]\ndependencies = ['Valid_Name>=1', '-invalid']\n", {"valid-name"}),
        ("[project]\ndependencies = 'not-a-sequence'\n", set()),
        ("[project]\noptional-dependencies = { test = [7] }\n", set()),
    ],
)
def test_pyproject_public_observation_accepts_only_normalizable_requirements(
    text: str, expected: set[str]
) -> None:
    observed = product_references_from_files({"pyproject.toml": text})
    assert observed["distribution"] == expected


def test_npm_public_observation_ignores_invalid_and_non_object_scripts() -> None:
    assert npm_script_commands({"bad.json": "{"}, root=None) == {}
    assert npm_script_commands({"package.json": '{"scripts": []}'}, root=None) == {}
    assert product_references_from_files({"package.json": "[]"}) == _observed()


def test_npm_public_observation_reads_root_manifest_and_skips_unreadable_siblings(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.json").write_text(
        '{"scripts": {"verify": "python -m pytest"}}', encoding="utf-8"
    )
    sibling = tmp_path / "packages/bad/package.json"
    sibling.parent.mkdir(parents=True)
    sibling.write_bytes(b"\xff")

    assert npm_script_commands({}, root=tmp_path) == {"verify": {"python -m pytest"}}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", {"github"}),
        ("./local/action", {"github"}),
        ("docker://alpine:3", {"github", "docker"}),
        ("owner/action@v4", {"github"}),
    ],
)
def test_yaml_public_observation_normalizes_action_references(
    value: str, expected: set[str]
) -> None:
    text = f"jobs:\n  test:\n    steps:\n      - uses: {value!r}\n"
    observed = product_references_from_files({".github/workflows/test.yml": text})
    assert observed["reference"] == expected


def test_markdown_public_observation_ignores_malformed_inline_shell() -> None:
    observed = product_references_from_files(
        {"docs/reference/example.md": "`'unterminated`\n"},
        declared_commands=("ethos status",),
    )
    assert observed == _observed()


def test_reference_gaps_are_sorted_and_ignore_internal_import_roots() -> None:
    observed = _observed()
    observed["import"] = {"ethos", "tests", "tools", "zeta", "alpha"}
    observed["reference"] = {"gitlab", "docker"}

    assert reference_gaps({}, observed) == [
        "product_reference_not_admitted_at_baseline:import:alpha",
        "product_reference_not_admitted_at_baseline:import:zeta",
        "product_reference_not_admitted_at_baseline:reference:docker",
        "product_reference_not_admitted_at_baseline:reference:gitlab",
    ]
