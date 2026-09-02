"""Repository semantic-reference closure tests."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.references.declarations as reference_declarations
import ethos.repository.policy.references.markdown as reference_markdown
from ethos.repository.policy.references.closure import repository_semantic_closure

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit_candidate_baseline(root: Path) -> None:
    _git(root, "init", "-b", "dev")
    _git(root, "config", "user.name", "ETHOS Tests")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "test: establish candidate baseline")
    _git(root, "branch", "candidate/dev")
    _git(root, "switch", "-c", "work/reference-closure")


def _commit_current_tree(root: Path) -> None:
    _git(root, "add", "--all")
    _git(root, "commit", "-m", "test: retire reference owner")


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


def test_repository_reference_closure_rejects_deleted_path_consumers(tmp_path: Path) -> None:
    """An active carrier cannot keep consuming a path deleted after candidate."""
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
    _write(tmp_path, "src/example/retired.py", "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "src/example/retired.py").unlink()
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"

    _write(
        tmp_path,
        "docs/reference/runtime.md",
        "Use [the runtime owner](../../src/example/retired.py).",
    )
    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert {
        "relation": "consumer",
        "kind": "path",
        "identity": "src/example/retired.py",
        "sources": ["docs/reference/runtime.md"],
    } in report["superseded"]


def test_repository_reference_closure_does_not_treat_change_intent_as_a_live_consumer(
    tmp_path: Path,
) -> None:
    """OpenSpec migration prose names old paths without consuming them."""
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
    _write(tmp_path, "src/example/retired.py", "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "src/example/retired.py").unlink()
    _write(
        tmp_path,
        "openspec/changes/remove-retired/specs/runtime/spec.md",
        ""
        "## MODIFIED Requirements\n\n"
        "### Requirement: Remove retired module\n\n"
        "The old `src/example/retired.py` path is removed from the runtime.\n",
    )
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"


def test_repository_reference_closure_does_not_treat_negative_guards_as_consumers(
    tmp_path: Path,
) -> None:
    """Policy prose and tests may prove a retired path absent without consuming it."""
    _write(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "docs"
carrier = "docs"
""",
    )
    _write(tmp_path, "docs/index.md", "# Duplicate documentation entrypoint")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "docs/index.md").unlink()
    _write(
        tmp_path,
        "docs/governance/documentation.md",
        "A duplicate `docs/index.md` has no current role.",
    )
    _write(
        tmp_path,
        "tests/architecture/test_documentation.py",
        'assert not (ROOT / "docs/index.md").exists()',
    )
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"


def test_repository_reference_closure_applies_active_removed_requirement(
    tmp_path: Path,
) -> None:
    """An official REMOVED delta defines the current effective specification."""
    retired_path = ".ethos" + "/commitment.toml"
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
    _write(tmp_path, retired_path, "schema_version = 1")
    _write(
        tmp_path,
        "openspec/specs/repository-governance/spec.md",
        f"""
## Requirements

### Requirement: Repository Commitment admission is precise and pre-effect

The current tree reads `{retired_path}` before every effect.

#### Scenario: Commitment exists

- **WHEN** the carrier is present
- **THEN** admission proceeds
""",
    )
    _commit_candidate_baseline(tmp_path)
    (tmp_path / retired_path).unlink()
    _write(
        tmp_path,
        "openspec/changes/remove-commitment/specs/repository-governance/spec.md",
        """
## REMOVED Requirements

### Requirement: Repository Commitment admission is precise and pre-effect

**Reason**: Official OpenSpec is the sole tracked intent.

**Migration**: Compile transient acceptance from the active Change.
""",
    )
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"


def test_repository_reference_closure_does_not_treat_canonical_absence_requirement_as_consumer(
    tmp_path: Path,
) -> None:
    """A canonical absence requirement is normative, not a live path use."""
    retired_path = ".ethos" + "/commitment.toml"
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
    _write(tmp_path, retired_path, "schema_version = 1")
    _write(
        tmp_path,
        "openspec/specs/repository-governance/spec.md",
        f"""
## Requirements

### Requirement: Repository Commitment carrier is absent

The retired `{retired_path}` path SHALL be absent.

#### Scenario: Retired carrier is checked

- **WHEN** repository semantic closure runs
- **THEN** the retired path remains absent
""",
    )
    _commit_candidate_baseline(tmp_path)
    (tmp_path / retired_path).unlink()
    _write(
        tmp_path,
        "openspec/changes/remove-commitment/specs/repository-governance/spec.md",
        """
## REMOVED Requirements

### Requirement: Repository Commitment admission is precise and pre-effect

**Reason**: Official OpenSpec is the sole tracked intent.

**Migration**: Compile transient acceptance from the active Change.
""",
    )
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"


def test_repository_reference_closure_rejects_canonical_spec_link_to_retired_path(
    tmp_path: Path,
) -> None:
    """A navigable canonical-spec link remains a real path consumer."""
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
    _write(tmp_path, "src/example/retired.py", "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "src/example/retired.py").unlink()
    _write(
        tmp_path,
        "openspec/specs/runtime/spec.md",
        """
## Requirements

### Requirement: Runtime owner remains navigable

The [runtime owner](../../../src/example/retired.py) defines execution.

#### Scenario: Runtime ownership is inspected

- **WHEN** the owner is opened
- **THEN** the linked module is available
""",
    )
    _commit_current_tree(tmp_path)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert {
        "relation": "consumer",
        "kind": "path",
        "identity": "src/example/retired.py",
        "sources": ["openspec/specs/runtime/spec.md"],
    } in report["superseded"]


def test_repository_reference_closure_rejects_renamed_module_consumers(tmp_path: Path) -> None:
    """An exact rename cannot leave imports of the old Python module name."""
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
    _write(tmp_path, "src/example/legacy.py", "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    _git(tmp_path, "mv", "src/example/legacy.py", "src/example/current.py")
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"

    _write(tmp_path, "src/example/consumer.py", "from example.legacy import VALUE")
    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert {
        "relation": "consumer",
        "kind": "import",
        "identity": "example.legacy",
        "sources": ["src/example/consumer.py"],
    } in report["superseded"]


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
