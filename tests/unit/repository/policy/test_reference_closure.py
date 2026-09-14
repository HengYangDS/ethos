"""Repository semantic-reference closure tests."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.references.closure as reference_closure
from ethos.repository.policy.references.closure import repository_semantic_closure
from tests.support.architecture import declare_reference_package
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path


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


def _runtime_surface(root: Path) -> None:
    """Declare the shared runtime boundary for reference ownership scenarios."""
    write_reference_source(
        root,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "runtime"
carrier = "src/example"
""",
    )


def test_repository_reference_closure_preserves_duplicate_command_owners(
    tmp_path: Path,
) -> None:
    """Set reduction must not hide two current owners of one command identity."""
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
    declare_reference_package(tmp_path, entry_point="example.primary")
    write_reference_source(
        tmp_path,
        "src/example/application.py",
        """
from cyclopts import App

app = App(name="ethos")
""",
    )
    for module, function in (("primary", "first_status"), ("parallel", "second_status")):
        write_reference_source(
            tmp_path,
            f"src/example/{module}.py",
            f"""
from example.application import app


@app.command(name="status")
def {function}() -> None:
    pass
""",
        )
    write_reference_source(tmp_path, ".agents/skills/status/SKILL.md", "Run `ethos status --json`.")

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    summary = report["summary"]
    assert isinstance(summary, Mapping)
    assert summary["duplicate"] == 1
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
    _runtime_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, "src/example/runtime.py", "import external_sdk")

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    summary = report["summary"]
    assert isinstance(summary, Mapping)
    assert summary["orphan"] == 1
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
    _runtime_surface(tmp_path)
    write_reference_source(tmp_path, "src/example/retired.py", "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "src/example/retired.py").unlink()
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"

    write_reference_source(
        tmp_path,
        "docs/reference/runtime.md",
        "Use [the runtime owner](../../src/example/retired.py).",
    )
    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["superseded"] == [
        {
            "relation": "consumer",
            "kind": "path",
            "identity": "src/example/retired.py",
            "sources": ["docs/reference/runtime.md"],
        }
    ]


@pytest.mark.parametrize("retired_count", [0, 1, 4])
def test_retired_reference_audit_parses_each_carrier_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    retired_count: int,
) -> None:
    """Retirement volume cannot multiply parsing or lose exact consumers."""
    _runtime_surface(tmp_path)
    retired = tuple(f"src/example/retired-{index}.txt" for index in range(retired_count))
    for path in retired:
        write_reference_source(tmp_path, path, "historical content")
    _commit_candidate_baseline(tmp_path)
    for path in retired:
        (tmp_path / path).unlink()
    document = "# Consumers\n" + "".join(
        f"[relative](../../{path}#details) [root]({path}?view=source)\n" for path in retired
    )
    source = f"PATHS = {retired!r}\n"
    write_reference_source(tmp_path, "docs/reference/runtime.md", document)
    write_reference_source(tmp_path, "src/example/runtime.py", source)
    _commit_current_tree(tmp_path)
    parsed: dict[str, list[str]] = {}
    for name in ("_markdown_link_destinations", "_path_literals"):
        original = getattr(reference_closure, name)
        calls: list[str] = []
        parsed[name] = calls

        def record_parse(text: str, parse=original, observed=calls) -> tuple[str, ...]:
            observed.append(text)
            return parse(text)

        monkeypatch.setattr(reference_closure, name, record_parse)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == ("block" if retired else "pass")
    assert report["superseded"] == [
        {
            "relation": "consumer",
            "kind": "path",
            "identity": path,
            "sources": ["docs/reference/runtime.md", "src/example/runtime.py"],
        }
        for path in retired
    ]
    assert parsed["_markdown_link_destinations"].count(document.strip() + "\n") == bool(retired)
    assert parsed["_path_literals"].count(source) == bool(retired)


def test_repository_reference_closure_does_not_treat_change_intent_as_a_live_consumer(
    tmp_path: Path,
) -> None:
    """OpenSpec migration prose names old paths without consuming them."""
    _runtime_surface(tmp_path)
    write_reference_source(tmp_path, "src/example/retired.py", "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "src/example/retired.py").unlink()
    write_reference_source(
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
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "docs"
carrier = "docs"
""",
    )
    write_reference_source(tmp_path, "docs/index.md", "# Duplicate documentation entrypoint")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "docs/index.md").unlink()
    write_reference_source(
        tmp_path,
        "docs/governance/documentation.md",
        "A duplicate `docs/index.md` has no current role.",
    )
    write_reference_source(
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
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "specs"
carrier = "openspec/specs"
""",
    )
    write_reference_source(tmp_path, retired_path, "schema_version = 1")
    write_reference_source(
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
    write_reference_source(
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
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "specs"
carrier = "openspec/specs"
""",
    )
    write_reference_source(tmp_path, retired_path, "schema_version = 1")
    write_reference_source(
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
    write_reference_source(
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
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "specs"
carrier = "openspec/specs"
""",
    )
    write_reference_source(tmp_path, "src/example/retired.py", "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / "src/example/retired.py").unlink()
    write_reference_source(
        tmp_path,
        "openspec/specs/runtime/spec.md",
        """
## Requirements

### Requirement: Runtime owner remains navigable

The [runtime owner](../../../src/example/retired.py), unlike an
[external reference](https://example.test/runtime), defines execution.

#### Scenario: Runtime ownership is inspected

- **WHEN** the owner is opened
- **THEN** the linked module is available
""",
    )
    _commit_current_tree(tmp_path)

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["superseded"] == [
        {
            "relation": "consumer",
            "kind": "path",
            "identity": "src/example/retired.py",
            "sources": ["openspec/specs/runtime/spec.md"],
        }
    ]


@pytest.mark.parametrize("replacement", ["rename", "expand", "collapse"])
def test_repository_reference_closure_resolves_replaced_module_identity(
    tmp_path: Path, replacement: str
) -> None:
    """File retirement removes an import identity only without a current owner."""
    _runtime_surface(tmp_path)
    declare_reference_package(tmp_path)
    source = (
        "src/example/legacy/__init__.py" if replacement == "collapse" else "src/example/legacy.py"
    )
    target = {
        "rename": "src/example/current.py",
        "expand": "src/example/legacy/operation.py",
        "collapse": "src/example/legacy.py",
    }[replacement]
    write_reference_source(tmp_path, source, "VALUE = 1")
    _commit_candidate_baseline(tmp_path)
    (tmp_path / source).unlink()
    write_reference_source(tmp_path, target, "VALUE = 1")
    if replacement == "expand":
        write_reference_source(
            tmp_path, "src/example/legacy/__init__.py", '"""Lease operation namespace."""'
        )
    _commit_current_tree(tmp_path)

    assert repository_semantic_closure(tmp_path)["verdict"] == "pass"

    module = "example.legacy.operation" if replacement == "expand" else "example.legacy"
    write_reference_source(tmp_path, "src/example/consumer.py", f"from {module} import VALUE")
    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == ("block" if replacement == "rename" else "pass")
    assert report["superseded"] == (
        [
            {
                "relation": "consumer",
                "kind": "import",
                "identity": "example.legacy",
                "sources": ["src/example/consumer.py"],
            }
        ]
        if replacement == "rename"
        else []
    )


def test_repository_reference_closure_ignores_prohibited_command_examples(
    tmp_path: Path,
) -> None:
    """A negative requirement names a forbidden command without consuming it."""
    write_reference_source(
        tmp_path,
        "system/surfaces.toml",
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "specs"
carrier = "openspec/specs"
""",
    )
    write_reference_source(
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
    summary = report["summary"]
    assert isinstance(summary, Mapping)
    assert summary["orphan"] == 0
