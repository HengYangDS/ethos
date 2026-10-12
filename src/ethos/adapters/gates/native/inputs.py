"""Observe exact native quality inputs and mandatory configuration without formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.release.resources import canonical_resource

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path


def quality_source_files(root: Path, *patterns: str) -> list[str]:
    """Read current authored input through native Git without swallowing inventory failure."""
    return git_files(
        root, "--cached", "--others", "--exclude-standard", "--", *patterns, check=True
    )


def quality_inventory_failure(
    root: Path, gate_id: str, error: GitExecutionError | subprocess.CalledProcessError
) -> dict[str, object]:
    """Unavailable input remains unknown with its original native execution evidence."""
    evidence = (
        error.evidence()
        if isinstance(error, GitExecutionError)
        else {
            "command": list(error.cmd),
            "cwd": str(root),
            "exit_code": error.returncode,
            "stdout": error.stdout.decode(errors="replace")
            if isinstance(error.stdout, bytes)
            else error.stdout or "",
            "stderr": error.stderr.decode(errors="replace")
            if isinstance(error.stderr, bytes)
            else error.stderr or "",
        }
    )
    return {
        "id": gate_id,
        "verdict": "unknown",
        "state": "inventory_unavailable",
        "file_count": 0,
        "required_gaps": [f"quality_input_inventory_unavailable:{gate_id}"],
        "errors": [evidence],
    }


def native_configurations(root: Path, tool: str, shared: str) -> tuple[str, ...]:
    """The shipped policy is mandatory; repository policy is a native increment."""
    common = canonical_resource(shared)
    selected = native_tool_configuration(tuple(quality_source_files(root)), tool)
    if selected:
        path = root / selected
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
            or not path.is_file()
        ):
            message = f"native_tool_configuration_invalid:{tool}"
            raise ValueError(message)
        if path.resolve() != common.resolve():
            return str(common), str(path)
    return (str(common),)
