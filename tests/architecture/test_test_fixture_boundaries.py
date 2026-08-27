from __future__ import annotations

from pathlib import Path

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import start_adopted_work_lane


def test_generic_work_lane_fixture_uses_a_minimal_valid_hook_runtime(tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    common = Path(git_common_dir(fixture.repository))
    selected = current_runtime(common)
    payload_bytes = sum(path.stat().st_size for path in selected.root.rglob("*") if path.is_file())

    assert leases_by_branch(fixture.worktree)["work/feature"]["lease_state"] == "valid"
    assert hook_runtime_binding(fixture.worktree)["required_gaps"] == []
    assert payload_bytes < 1_000_000
