"""Quality-tool IO adapter — runs an external quality tool and reports its result.

The impure execution layer: shells out to a formatter/linter binary. Domain/surface
receive the structured report and stay free of subprocess concerns.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import git_files
from ethos.repository.policy.layout.report import module_layout_report

if TYPE_CHECKING:
    from pathlib import Path


def _trim_output(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n[trimmed {len(text) - limit} bytes]"


def quality_tool_report(
    *,
    root: Path,
    gate_id: str,
    tool: str,
    command: list[str],
    files: list[str],
) -> dict[str, object]:
    """Run an external quality tool over files and structure its pass/fail result."""
    if not files:
        return {
            "ok": True,
            "id": gate_id,
            "tool": tool,
            "state": "skipped",
            "file_count": 0,
            "required_gaps": [],
        }
    if shutil.which(tool) is None:
        return {
            "ok": False,
            "id": gate_id,
            "tool": tool,
            "state": "missing_tool",
            "file_count": len(files),
            "command": command,
            "required_gaps": [f"quality_tool_missing:{tool}"],
        }
    # Fixed gate command (list form, no shell, no external input).
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "id": gate_id,
        "tool": tool,
        "state": "passed" if completed.returncode == 0 else "failed",
        "file_count": len(files),
        "command": command,
        "exit_code": completed.returncode,
        "stdout": _trim_output(completed.stdout),
        "stderr": _trim_output(completed.stderr),
        "required_gaps": [] if completed.returncode == 0 else [f"quality_gate_failed:{gate_id}"],
    }


def markdown_links_report(root: Path) -> dict[str, object]:
    """Check tracked Markdown links without a command-shaped ETHOS loopback."""
    files = [
        path
        for path in git_files(root, "*.md")
        if not path.startswith(("evidence/", "docs/archive/"))
    ]
    return quality_tool_report(
        root=root,
        gate_id="markdown-links",
        tool="lychee",
        command=[
            "lychee",
            "--config",
            ".config/checks/lychee/lychee.toml",
            "--no-progress",
            *files,
        ],
        files=files,
    )


def module_layout_gate_report(root: Path) -> dict[str, object]:
    """Audit only Git-owned Python carriers through the pure layout policy."""
    files = tuple(root / path for path in git_files(root, "*.py") if (root / path).is_file())
    return module_layout_report(root, files=files)
