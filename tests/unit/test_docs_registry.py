from __future__ import annotations

from pathlib import Path

from ethos_repository.docs_registry import (
    build_docs_registry,
    command_examples_report,
    docs_health_report,
)


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
    assert report["document_count"] >= 10


def test_command_examples_do_not_leak_retired_roots() -> None:
    report = command_examples_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert any(example["command"].startswith("ethos ") for example in report["examples"])


def test_command_examples_treat_evidence_as_observational(tmp_path: Path) -> None:
    (tmp_path / "docs" / "evidence").mkdir(parents=True)
    (tmp_path / "README.md").write_text(
        """# Example

```bash
ethos status
```
""",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "evidence" / "run.md").write_text(
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
        example["command"]
        for example in report["examples"]
        if example["path"] == "docs/evidence/run.md"
    } == {
        "openspec validate --all --strict --json",
        "codex --version",
        "TERM=xterm-256color codex doctor --json",
    }
