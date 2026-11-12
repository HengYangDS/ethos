"""The canonical-text owner acts in `lane format` and in the source-format gate."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.gates.formatting import source_format_report
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import write_tree

if TYPE_CHECKING:
    from pathlib import Path


def _command(root: Path, *arguments: str) -> tuple[int, dict[str, Any]]:
    completed = run_ethos_raw("lane", "format", *arguments, "--root", str(root), "--json", cwd=root)
    assert completed.stdout.startswith("{"), completed.stderr
    return completed.returncode, json.loads(completed.stdout)


def test_canonical_text_is_checked_and_fixed_like_a_native_format(lane: Path) -> None:
    """Stray blank lines in a hygiene file fail the gate; one fix is canonical and stays so."""
    write_tree(lane, {".gitignore": "\nbuild/\n\n\n*.log\n\n", "VERSION": "0.1.0"})

    refused = source_format_report(lane)
    assert refused["verdict"] == "block", refused
    assert {"source_format_drift:.gitignore", "source_format_drift:VERSION"} <= set(
        refused["required_gaps"]
    )

    head = git(lane, "rev-parse", "HEAD")
    code, applied = _command(lane, "--apply", "--authorize", "--expect-head", head)
    assert (code, applied["verdict"]) == (0, "pass"), applied
    assert (lane / ".gitignore").read_text(encoding="utf-8") == "build/\n\n*.log\n"
    assert (lane / "VERSION").read_text(encoding="utf-8") == "0.1.0\n"
    code, checked = _command(lane, "--check")
    assert (code, checked["verdict"]) == (0, "pass"), checked
    assert source_format_report(lane)["verdict"] == "pass"
