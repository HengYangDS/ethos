"""Installed production supply exercises each declared native formatter."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.toolchain.mise import native_tool_cache
from ethos.repository.release.resources import canonical_resource
from tools.ci.delivery.acceptance import runtime as runtime_acceptance

if TYPE_CHECKING:
    import pytest


def test_installed_format_probe_uses_current_native_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run every shipped formatter; package smoke separately proves dependency absence."""
    dependency_check = 'assert importlib.util.find_spec("pytest") is None'

    def run(root: Path, command: tuple[str, ...], **kwargs: object) -> object:
        assert dependency_check in command[-1]
        selected = (*command[:-1], command[-1].replace(dependency_check, ""))
        return run_command(root, selected, **kwargs)

    monkeypatch.setattr(runtime_acceptance, "run_command", run)

    # Hosted CI binds prepared supply explicitly; it has no Git-common tool cache.
    supply = native_tool_cache(canonical_resource("pyproject.toml").parent)
    assert runtime_acceptance.require_production_dependencies(
        Path(sys.executable),
        environment={
            "PATH": str(Path(shutil.which("git")).parent),
            "ETHOS_CI_TOOL_CACHE_DIR": supply.as_posix(),
        },
    ) == {
        "state": "passed",
        "excluded": ["pytest"],
        "staged_format": "passed",
        "source_format": "passed",
        "formatters": ["ruff", "prettier", "taplo", "shfmt", "svgo"],
    }
