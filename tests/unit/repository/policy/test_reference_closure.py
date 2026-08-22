"""Repository semantic-reference closure tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.references.declarations as reference_declarations
import ethos.repository.policy.references.observation as reference_observation
from ethos.repository.policy.references.closure import repository_semantic_closure

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def test_repository_reference_closure_preserves_duplicate_command_owners(
    tmp_path: Path,
) -> None:
    """Set reduction must not hide two current owners of one command identity."""
    _write(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "cli"
carrier = "src/example"
""",
    )
    _write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "example"
version = "1"
dependencies = ["cyclopts"]

[project.scripts]
ethos = "example.primary:main"
""",
    )
    _write(
        tmp_path,
        "src/example/application.py",
        """
from cyclopts import App

app = App(name="ethos")
""",
    )
    for module, function in (("primary", "first_status"), ("parallel", "second_status")):
        _write(
            tmp_path,
            f"src/example/{module}.py",
            f"""
from example.application import app


@app.command(name="status")
def {function}() -> None:
    pass
""",
        )
    _write(tmp_path, ".agents/skills/status/SKILL.md", "Run `ethos status --json`.")

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["summary"]["duplicate"] == 1
    assert report["duplicate"] == [
        {
            "relation": "owner",
            "kind": "command",
            "identity": "ethos status",
            "sources": [
                "src/example/parallel.py:second_status",
                "src/example/primary.py:first_status",
            ],
        }
    ]
    assert report["required_gaps"] == [
        (
            "semantic_owner_duplicate:command:ethos status:"
            "src/example/parallel.py:second_status,src/example/primary.py:first_status"
        )
    ]


def test_repository_reference_closure_reports_orphan_consumers(tmp_path: Path) -> None:
    """A consumer without a native owner is one explicit orphan relation."""
    _write(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "runtime"
carrier = "src/example"
""",
    )
    _write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "example"
version = "1"
""",
    )
    _write(tmp_path, "src/example/runtime.py", "import external_sdk")

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["summary"]["orphan"] == 1
    assert report["orphan"] == [
        {
            "relation": "consumer",
            "kind": "import",
            "identity": "external_sdk",
            "sources": ["src/example/runtime.py"],
        }
    ]
    assert report["required_gaps"] == [
        "semantic_consumer_orphan:import:external_sdk:src/example/runtime.py"
    ]


def test_repository_reference_closure_ignores_prohibited_command_examples(
    tmp_path: Path,
) -> None:
    """A negative requirement names a forbidden command without consuming it."""
    _write(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "specs"
carrier = "openspec/specs"
""",
    )
    _write(
        tmp_path,
        "openspec/specs/command-plane/spec.md",
        """
# Command Plane

## Requirements

### Requirement: Retired command vocabulary

ETHOS SHALL reject retired command names.

#### Scenario: Retired command appears

- **WHEN** governed docs contain `ethos retired --json` as a command
- **THEN** the command-surface gate reports a required gap
""",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "pass"
    assert report["summary"]["orphan"] == 0


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
    _write(
        tmp_path,
        "system/surfaces.toml",
        f"""
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "docs"
carrier = "{carrier}"
""",
    )
    _write(tmp_path, relative, content)

    if relative.endswith(".md"):
        monkeypatch.setattr(reference_observation, "markdown_tokens", lambda _text: None)

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
    _write(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "cli"
carrier = "src/example"
""",
    )
    _write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "example"
version = "1"
dependencies = ["cyclopts"]

[project.scripts]
ethos = "example.commands:main"
""",
    )
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
    _write(tmp_path, "src/example/commands.py", command_text)
    _write(tmp_path, "src/example/plain.py", plain_text)
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
