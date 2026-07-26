"""Regression coverage for documentation command validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.registry.docs.health import docs_health_report

if TYPE_CHECKING:
    from pathlib import Path


def write_active_doc(root: Path, command: str) -> None:
    """Write one minimal canonical document containing a shell command example."""
    path = root / "docs" / "reference" / "example.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""\
---
subject: ethos:example
role: reference
state: canonical
relations: none
---

# Example

Status: canonical.

Purpose: exercise the command validator.

See also: none.

```bash
{command}
```
""",
        encoding="utf-8",
    )


def test_docs_health_rejects_deleted_quality_provenance_command(tmp_path: Path) -> None:
    """Deleted quality commands cannot persist in canonical examples."""
    write_active_doc(tmp_path, "ethos quality provenance --json")

    report = docs_health_report(tmp_path)

    assert report["invalid_command_examples"] == [
        "unknown_ethos_command_example:docs/reference/example.md:17:ethos quality provenance"
    ]


def test_docs_health_rejects_unregistered_nested_command(tmp_path: Path) -> None:
    """A nested example must resolve through the live Cyclopts command tree."""
    write_active_doc(tmp_path, "ethos lane lease takeover --json")

    report = docs_health_report(tmp_path)

    assert report["invalid_command_examples"] == [
        "unknown_ethos_command_example:docs/reference/example.md:17:ethos lane lease takeover"
    ]


def test_docs_health_accepts_registered_nested_command(tmp_path: Path) -> None:
    """A live nested Cyclopts operation remains an admitted documentation example."""
    write_active_doc(tmp_path, "uv run --no-sync ethos lane lease renew --json")

    report = docs_health_report(tmp_path)

    assert report["invalid_command_examples"] == []
