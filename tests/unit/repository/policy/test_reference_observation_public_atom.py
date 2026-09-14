from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.references.declarations as reference_declarations
import ethos.repository.policy.references.markdown as reference_markdown
from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.observation import npm_script_commands
from ethos.repository.policy.references.observation import observe_repository_references
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files
from ethos.repository.policy.references.python_syntax import cyclopts_command_owners
from ethos.repository.policy.references.python_syntax import cyclopts_prefixes
from ethos.repository.policy.references.python_syntax import module_name
from tests.support.architecture import declare_reference_package
from tests.support.architecture import write_reference_source

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


def test_cyclopts_observation_resolves_cycles_and_explicit_names() -> None:
    assert cyclopts_prefixes({"src/pkg/cli.py": "App("}) == {}
    prefixes = cyclopts_prefixes(
        {
            "src/pkg/cli.py": (
                "a_app = App(name='alpha')\n"
                "b_app = App(name='beta')\n"
                "a_app.command(b_app)\n"
                "b_app.command(a_app)\n"
            )
        }
    )
    assert prefixes == {("pkg.cli", "a_app"): "beta alpha", ("pkg.cli", "b_app"): "alpha beta"}
    assert module_name("src/pkg/__init__.py") == "pkg"
    tree = ast.parse("@app.command(name='explicit')\ndef default_name(): pass\n")
    assert set(
        cyclopts_command_owners("src/pkg/command.py", tree, {("pkg.command", "app"): "root"})
    ) == {"root explicit"}


@pytest.mark.parametrize(
    ("relative", "content", "carrier"),
    [
        ("docs/reference/commands.md", "Run `ethos status --json`.\n", "docs"),
        ("pyproject.toml", "[project\nname = 'broken'\n", "docs"),
        ("package.json", "{\n", "docs"),
        (".github/workflows/test.yml", "jobs: [\n", "docs"),
        ("src/example/broken.py", "def broken(:\n    pass\n", "src/example"),
    ],
)
def test_repository_reference_closure_reports_unparseable_carrier_as_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
    content: str,
    carrier: str,
) -> None:
    """A selected carrier parser failure cannot disappear as an empty observation."""
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        f"""
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "docs"
carrier = "{carrier}"
""",
    )
    write_reference_source(tmp_path, relative, content)

    if relative.endswith(".md"):
        monkeypatch.setattr(reference_markdown, "markdown_tokens", lambda _text: None)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "unknown"
    assert report["unknown"] == [
        {
            "relation": "carrier",
            "kind": "reference",
            "identity": relative,
            "sources": [relative],
        }
    ]


def test_repository_semantic_closure_parses_each_complete_python_carrier_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One closure invocation shares each complete Python syntax tree."""
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "cli"
carrier = "src/example"
""",
    )
    declare_reference_package(tmp_path, entry_point="example.commands")
    command_text = (
        """
from cyclopts import App

app = App(name="ethos")

@app.command(name="status")
def status() -> None:
    pass
""".strip()
        + "\n"
    )
    plain_text = "def plain() -> None:\n    pass\n"
    write_reference_source(tmp_path, "src/example/commands.py", command_text)
    write_reference_source(tmp_path, "src/example/plain.py", plain_text)
    calls: list[str] = []
    original = reference_declarations.python_references.ast.parse

    def record_parse(source: str) -> object:
        calls.append(source)
        return original(source)

    monkeypatch.setattr(
        reference_declarations.python_references.ast,
        "parse",
        record_parse,
    )
    repository_semantic_closure(tmp_path)

    assert calls.count(command_text) == 1
    assert calls.count(plain_text) == 1


def test_command_owner_observation_skips_python_without_command_syntax(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Command ownership parses only files capable of declaring a command."""
    parsed: list[str] = []
    original = reference_declarations.python_references.python_trees

    def record_parse(text: str) -> object:
        parsed.append(text)
        return original(text)

    monkeypatch.setattr(reference_declarations.python_references, "python_trees", record_parse)

    owners = reference_declarations.command_owner_sources_from_files(
        {
            "src/example/plain.py": "def plain() -> None:\n    pass\n",
            "src/example/commands.py": (
                "from cyclopts import App\n"
                "app = App(name='ethos')\n"
                "@app.command(name='status')\n"
                "def status() -> None:\n"
                "    pass\n"
            ),
        }
    )

    assert "def plain" not in "".join(parsed)
    assert owners["ethos status"] == frozenset({"src/example/commands.py:status"})
