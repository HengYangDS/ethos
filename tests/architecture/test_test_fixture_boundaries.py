"""Keep runtime fixtures source-bound without copying the dependency tree."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import start_adopted_work_lane


def test_generic_work_lane_fixture_uses_a_minimal_valid_hook_runtime(tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    common = Path(git_common_dir(fixture.repository))
    selected = current_runtime(common)
    files = tuple(path for path in selected.root.rglob("*") if path.is_file())
    source_python = Path(sys.executable).resolve()
    assert selected.python != source_python
    assert selected.python.read_bytes() == source_python.read_bytes()
    assert not selected.python.samefile(source_python)
    source_digest = hashlib.sha256(source_python.read_bytes()).digest()
    assert [
        path for path in files if hashlib.sha256(path.read_bytes()).digest() == source_digest
    ] == [selected.python]
    payload_bytes = sum(path.stat().st_size for path in files if path != selected.python)

    assert leases_by_branch(fixture.worktree)["work/feature"]["lease_state"] == "valid"
    assert hook_runtime_binding(fixture.worktree)["required_gaps"] == []
    assert len(files) <= 5
    assert payload_bytes < 1_000_000
