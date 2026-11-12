"""The canonical-text owner acts in `lane format` and in the source-format gate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.gates.formatting import source_format_report
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import write_tree

if TYPE_CHECKING:
    from pathlib import Path


def test_canonical_text_is_checked_and_fixed_like_a_native_format(lane: Path) -> None:
    """Stray blank lines in a hygiene file fail the gate; one fix is canonical and stays so."""
    write_tree(lane, {".gitignore": "\nbuild/\n\n\n*.log\n\n", "VERSION": "0.1.0"})

    refused = source_format_report(lane)
    assert refused["verdict"] == "block", refused
    assert {"source_format_drift:.gitignore", "source_format_drift:VERSION"} <= set(
        refused["required_gaps"]
    )

    root = ("--root", str(lane), "--json")
    apply = ("--apply", "--authorize", "--expect-head", git(lane, "rev-parse", "HEAD"))
    applied = run_ethos("lane", "format", *apply, *root, cwd=lane, full_payload=False)
    assert applied["verdict"] == "pass", applied
    assert (lane / ".gitignore").read_text(encoding="utf-8") == "build/\n\n*.log\n"
    assert (lane / "VERSION").read_text(encoding="utf-8") == "0.1.0\n"
    checked = run_ethos("lane", "format", "--check", *root, cwd=lane, full_payload=False)
    assert checked["verdict"] == "pass", checked
    assert source_format_report(lane)["verdict"] == "pass"
