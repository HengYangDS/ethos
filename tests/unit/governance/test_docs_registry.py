from __future__ import annotations

from pathlib import Path

from ethos.repository.registry.docs import DEFAULT_ALLOWED_STATES
from ethos.repository.registry.docs import build_docs_registry
from ethos.repository.registry.docs import command_examples_report
from ethos.repository.registry.docs import docs_health_report
from ethos_core.contracts.docs.topology import STATE_VALUES


def test_default_allowed_states_are_sourced_from_topology_contract() -> None:
    # SSOT: the docs-registry allowed-state vocabulary must be derived from the
    # topology contract's STATE_VALUES, not an independent hand-maintained copy
    # that can silently diverge (add a state to the contract and this stays in lockstep).
    assert frozenset(STATE_VALUES) == DEFAULT_ALLOWED_STATES


def test_docs_registry_indexes_subject_metadata() -> None:
    registry = build_docs_registry(Path.cwd())

    subjects = {entry["subject"] for entry in registry}

    assert "ethos:kernel" in subjects
    assert "ethos:command-plane" in subjects
    assert all(entry["path"].endswith(".md") for entry in registry)


def test_docs_health_report_has_no_missing_metadata() -> None:
    report = docs_health_report(Path.cwd())

    assert report["ok"] is True
    assert report["missing_metadata"] == []
    assert report["invalid_state"] == []
    assert report["duplicate_subjects"] == []
    assert report["document_count"] >= 10


def test_docs_quality_report_enforces_taxonomy_and_visible_sections() -> None:
    from ethos.repository.registry.docs import docs_quality_report

    report = docs_quality_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["style_goals"] == ["faithful", "expressive", "elegant"]
    assert report["checks"]["taxonomy"]["ok"] is True
    assert report["checks"]["visible_structure"]["ok"] is True
    assert report["checks"]["stable_paths"]["ok"] is True
    assert report["checks"]["link_integrity"]["ok"] is True
    assert report["checks"]["glossary"]["ok"] is True


def test_command_examples_do_not_leak_retired_roots() -> None:
    report = command_examples_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert any(example["command"].startswith("ethos ") for example in report["examples"])


def test_command_examples_treat_evidence_as_observational(tmp_path: Path) -> None:
    (tmp_path / "evidence").mkdir(parents=True)
    (tmp_path / "README.md").write_text(
        """# Example

```bash
ethos status
```
""",
        encoding="utf-8",
    )
    (tmp_path / "evidence" / "run.md").write_text(
        """# Evidence

```bash
openspec validate --all --strict --json
codex --version
TERM=xterm-256color codex doctor --json
```
""",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert {
        example["command"] for example in report["examples"] if example["path"] == "evidence/run.md"
    } == {
        "openspec validate --all --strict --json",
        "codex --version",
        "TERM=xterm-256color codex doctor --json",
    }


def test_command_examples_reject_unknown_nested_ethos_commands(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        """# Example

```bash
ethos quality frobnicate --json
ethos lane nope --json
```
""",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is False
    assert (
        "unknown_ethos_command_example:README.md:4:ethos quality frobnicate"
        in report["required_gaps"]
    )
    assert "unknown_ethos_command_example:README.md:5:ethos lane nope" in report["required_gaps"]


def test_command_examples_validate_wrapped_uv_ethos_commands(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        """# Example

```bash
uv run --package ethos ethos quality frobnicate --json
npm run ethos -- --version
```
""",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is False
    assert (
        "unknown_ethos_command_example:README.md:4:ethos quality frobnicate"
        in report["required_gaps"]
    )
    npm_record = next(
        example
        for example in report["examples"]
        if example["command"] == "npm run ethos -- --version"
    )
    assert npm_record["root"] == "npm"


def test_command_examples_join_shell_continuation_lines_before_classification(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        """# Example

```bash
uv run --package ethos ethos lane prewrite \\
  evidence/example.md \\
  packages/ethos/src/ethos/cli.py \\
  --require-editor-root \\
  --editor-root /tmp/ethos-work \\
  --json
```
""",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert [example["command"] for example in report["examples"]] == [
        (
            "uv run --package ethos ethos lane prewrite "
            "evidence/example.md "
            "packages/ethos/src/ethos/cli.py "
            "--require-editor-root "
            "--editor-root /tmp/ethos-work "
            "--json"
        )
    ]


def test_docs_quality_report_rejects_invalid_taxonomy_state(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        """---
subject: ethos:bad
role: reference
state: current
relations:
  see_also: []
---

# Bad

Status: current

Purpose: demonstrate invalid state.

See also: none.
""",
        encoding="utf-8",
    )

    report = docs_health_report(tmp_path)

    assert report["ok"] is False
    assert report["invalid_state"] == ["invalid_state:docs/bad.md:current"]
