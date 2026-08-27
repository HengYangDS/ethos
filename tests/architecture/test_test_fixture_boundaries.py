from __future__ import annotations

from pathlib import Path

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import apply_accepted_closeout
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_work_lane


def test_generic_work_lane_fixture_uses_a_minimal_valid_hook_runtime(tmp_path: Path) -> None:
    """Generic governance fixtures keep hook semantics without a full runtime copy."""
    fixture = start_adopted_work_lane(tmp_path)
    common = Path(git_common_dir(fixture.repository))
    selected = current_runtime(common)
    payload_bytes = sum(path.stat().st_size for path in selected.root.rglob("*") if path.is_file())

    assert leases_by_branch(fixture.worktree)["work/feature"]["lease_state"] == "valid"
    assert hook_runtime_binding(fixture.worktree)["required_gaps"] == []
    assert payload_bytes < 1_000_000


def test_accepted_closeout_fixture_uses_a_minimal_valid_hook_runtime(tmp_path: Path) -> None:
    """Accepted-CAS fixtures retain real hooks without rebuilding a package runtime."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    accepted_before = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "candidate/dev", accepted_before)
    git(repo, "checkout", "candidate/dev")
    (repo / "candidate.txt").write_text("candidate\n", encoding="utf-8")
    git(repo, "add", "candidate.txt")
    git(repo, "commit", "-m", "feat: prepare candidate")
    candidate_head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, candidate_head)

    apply_accepted_closeout(repo, accepted_before, candidate_head)

    selected = current_runtime(Path(git_common_dir(repo)))
    payload_bytes = sum(path.stat().st_size for path in selected.root.rglob("*") if path.is_file())
    assert git(repo, "rev-parse", "dev") == candidate_head
    assert payload_bytes < 1_000_000
