from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.references.observation as observation

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


def test_repository_reference_files_skips_unreadable_carriers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    good, bad = tmp_path / "good.md", tmp_path / "bad.md"
    good.write_text("good\n", encoding="utf-8")
    bad.write_bytes(b"\xff")
    monkeypatch.setattr(observation, "product_surface_files", lambda _root: [good, bad])
    monkeypatch.setattr(observation, "reference_paths", lambda _root, paths: paths)

    assert observation.repository_reference_files(tmp_path) == {"good.md": "good\n"}


def test_command_source_discovery_skips_unreadable_python(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("App()\n", encoding="utf-8")
    (source / "bad.py").write_bytes(b"\xff")

    assert observation._command_source_files({}, root=tmp_path) == {  # noqa: SLF001
        "src/app.py": "App()\n"
    }


@pytest.mark.parametrize("values", [None, {}, [None, 7, "Valid_Name>=1", "-invalid"]])
def test_requirement_names_accept_only_normalizable_string_sequences(values: object) -> None:
    expected = {"valid-name"} if isinstance(values, list) else set()
    assert observation._requirement_names(values) == expected  # noqa: SLF001


def test_npm_scripts_ignore_invalid_manifests_and_non_object_scripts(tmp_path: Path) -> None:
    package = tmp_path / "package.json"
    package.write_text("[]", encoding="utf-8")
    assert observation.npm_script_commands({"bad.json": "{"}, root=tmp_path) == {}

    assert observation.npm_script_commands({"package.json": '{"scripts": []}'}, root=None) == {}


def test_package_json_non_object_root_does_not_mint_references() -> None:
    observed = _observed()
    observation.package_json_references("[]", {}, observed, declarations=True)
    assert observed == _observed()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", ""),
        ("./local/action", ""),
        ("docker://alpine:3", "docker"),
        ("owner/action@v4", "github"),
    ],
)
def test_github_reference_normalization(value: str, expected: str) -> None:
    assert observation._github_reference(value) == expected  # noqa: SLF001


def test_markdown_observation_ignores_malformed_inline_shell() -> None:
    observed = _observed()
    observation._markdown_references(  # noqa: SLF001
        "docs/reference/example.md",
        "`'unterminated`\n",
        {"ethos status"},
        {},
        observed,
    )
    assert observed == _observed()


def test_reference_gaps_are_sorted_and_ignore_internal_import_roots() -> None:
    observed = _observed()
    observed["import"] = {"ethos", "tests", "tools", "zeta", "alpha"}
    observed["reference"] = {"gitlab", "docker"}

    assert observation.reference_gaps({}, observed) == [
        "product_reference_not_admitted_at_baseline:import:alpha",
        "product_reference_not_admitted_at_baseline:import:zeta",
        "product_reference_not_admitted_at_baseline:reference:docker",
        "product_reference_not_admitted_at_baseline:reference:gitlab",
    ]
