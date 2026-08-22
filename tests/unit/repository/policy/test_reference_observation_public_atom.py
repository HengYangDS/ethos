from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.observation import npm_script_commands
from ethos.repository.policy.references.observation import observe_repository_references
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files

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

    observation = observe_repository_references(tmp_path)
    observed = product_references_from_files(observation.files)

    assert observation.files == {".agents/skills/sample/SKILL.md": "good\n"}
    assert observation.unreadable_paths == (".agents/skills/sample/bad.md",)
    assert observed == _observed()


def test_repository_public_observation_skips_unreadable_python(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/ethos"
    source.mkdir(parents=True)
    (source / "app.py").write_text("App()\n", encoding="utf-8")
    (source / "bad.py").write_bytes(b"\xff")

    observation = observe_repository_references(tmp_path)
    observed = product_references_from_files(observation.files)

    assert observed == _observed()
    assert observation.unreadable_paths == ("src/ethos/bad.py",)


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
    assert npm_script_commands({"bad.json": "{"}) == {}
    assert npm_script_commands({"package.json": '{"scripts": []}'}) == {}
    assert product_references_from_files({"package.json": "[]"}) == _observed()


def test_npm_public_observation_reads_explicit_manifests() -> None:
    files = {"package.json": '{"scripts": {"verify": "python -m pytest"}}'}

    assert npm_script_commands(files) == {"verify": {"python -m pytest"}}


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


def test_consumer_observation_does_not_recompute_command_declarations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer extraction consumes declared commands without rediscovering owners."""
    calls: list[dict[str, str]] = []

    def record_prefix_scan(files: dict[str, str]) -> dict[tuple[str, str], str]:
        calls.append(files)
        return {}

    monkeypatch.setattr(
        "ethos.repository.policy.references.python_syntax.cyclopts_prefixes",
        record_prefix_scan,
    )

    result = reference_consumer_sources_from_files(
        {"docs/reference/example.md": "Run `ethos status --json`.\n"},
        declared_commands=("ethos status",),
    )

    assert result.sources["command"] == {"ethos status": frozenset({"docs/reference/example.md"})}
    assert result.unknown_paths == ()
    assert calls == []
