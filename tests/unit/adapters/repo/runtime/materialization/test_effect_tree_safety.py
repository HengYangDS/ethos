"""Runtime tree mutation refuses links that reach outside the generated tree."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as materialization

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("operation", ["seal", "remove"])
def test_runtime_mutation_rejects_hardlinks_without_changing_the_external_inode(
    tmp_path: Path,
    operation: str,
) -> None:
    external = tmp_path / "external"
    external.write_text("shared bytes\n", encoding="utf-8")
    external.chmod(0o644)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    try:
        os.link(external, runtime / "shared")
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")

    effect = (
        vars(materialization)["_seal_runtime_payload"]
        if operation == "seal"
        else materialization.remove_generated_tree
    )
    with pytest.raises(ValueError, match="hook_runtime_generation_hardlink_invalid"):
        effect(runtime)

    assert stat.S_IMODE(external.stat().st_mode) == 0o644
    assert runtime.is_dir()


def test_generated_tree_cleanup_rejects_a_junction_without_touching_its_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = tmp_path / "generated"
    junction = generated / "junction"
    junction.mkdir(parents=True)
    sentinel = junction / "sentinel"
    sentinel.write_text("outside authority\n", encoding="utf-8")
    with monkeypatch.context() as context:
        context.setattr(runtime_filesystem, "is_junction", lambda path: path == junction)
        with pytest.raises(ValueError, match="hook_runtime_generation_tree_invalid"):
            materialization.remove_generated_tree(generated)

    assert generated.is_dir()
    assert sentinel.read_text(encoding="utf-8") == "outside authority\n"
    materialization.remove_generated_tree(generated)
    failed = tmp_path / "failed"
    failed.mkdir()
    monkeypatch.setattr(materialization.shutil, "rmtree", Mock(side_effect=OSError("busy")))
    with pytest.raises(OSError, match="busy"):
        materialization.remove_generated_tree(failed)
    materialization.remove_generated_tree(failed, ignore_errors=True)
