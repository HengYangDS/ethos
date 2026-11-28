"""Runtime tree mutation refuses links that reach outside the generated tree."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.materialization.effect as materialization

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("operation", ["seal", "remove"])
def test_runtime_mutation_rejects_hardlinks_without_changing_the_external_inode(
    tmp_path: Path, operation: str
) -> None:
    external = tmp_path / "external"
    external.write_text("shared bytes\n", encoding="utf-8")
    external.chmod(0o644)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    os.link(external, runtime / "shared")

    effect = (
        vars(materialization)["_seal_runtime_payload"]
        if operation == "seal"
        else materialization.remove_generated_tree
    )
    with pytest.raises(ValueError, match="hook_runtime_generation_hardlink_invalid"):
        effect(runtime)

    assert stat.S_IMODE(external.stat().st_mode) == 0o644
    assert runtime.is_dir()
