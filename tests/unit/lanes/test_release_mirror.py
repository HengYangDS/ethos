from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.core import ref_move_admission_report
from ethos.adapters.mutation.core import apply_candidate_to_accepted
from tests.support.contract_helpers import git
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import init_repo
from tests.unit.lanes.test_apply import seed_proof

if TYPE_CHECKING:
    from pathlib import Path


def test_closeout_mirrors_accepted_to_release(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    policy = repo / ".ethos" / "workspace.toml"
    policy.parent.mkdir(exist_ok=True)
    policy.write_text('[branch_roles]\nrelease_mirror = "accepted_ff"\n', encoding="utf-8")
    git(repo, "add", policy.as_posix())
    git(repo, "-c", "user.name=t", "-c", "user.email=t@e.x", "commit", "-m", "mirror")
    git(repo, "branch", "main", "dev")
    candidate = add_candidate_worktree(repo, tmp_path / "candidate")
    (candidate / "README.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    git(
        candidate,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@e.x",
        "commit",
        "-m",
        "candidate",
    )
    previous, head = git(repo, "rev-parse", "HEAD"), git(candidate, "rev-parse", "HEAD")
    seed_proof(candidate, head)

    result = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=previous)

    assert result["ok"] is True
    assert git(repo, "rev-parse", "dev") == git(repo, "rev-parse", "main") == head
    assert result["release_mirror"]["worktree_sync"] == "not_linked"


def test_ref_move_uses_candidate_mirror_policy(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    git(repo, "branch", "candidate/dev", "dev")
    git(repo, "checkout", "candidate/dev")
    policy = repo / ".ethos" / "workspace.toml"
    policy.parent.mkdir(exist_ok=True)
    policy.write_text('[branch_roles]\nrelease_mirror = "accepted_ff"\n', encoding="utf-8")
    git(repo, "add", policy.as_posix())
    git(repo, "-c", "user.name=t", "-c", "user.email=t@e.x", "commit", "-m", "mirror")
    head = git(repo, "rev-parse", "HEAD")
    old = git(repo, "rev-parse", "main")

    result = ref_move_admission_report(
        root=repo, ref_name="refs/heads/main", old_value=old, new_value=head
    )

    assert "release_mirror_ref_move_no_closeout_intent" in result["required_gaps"]


def test_closeout_syncs_linked_release_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    policy = repo / ".ethos" / "workspace.toml"
    policy.parent.mkdir(exist_ok=True)
    policy.write_text('[branch_roles]\nrelease_mirror = "accepted_ff"\n', encoding="utf-8")
    git(repo, "add", policy.as_posix())
    git(repo, "-c", "user.name=t", "-c", "user.email=t@e.x", "commit", "-m", "mirror")
    git(repo, "branch", "main", "dev")
    release = tmp_path / "release"
    git(repo, "worktree", "add", release.as_posix(), "main")
    candidate = add_candidate_worktree(repo, tmp_path / "candidate")
    (candidate / "README.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    git(
        candidate,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@e.x",
        "commit",
        "-m",
        "candidate",
    )
    previous, head = git(repo, "rev-parse", "HEAD"), git(candidate, "rev-parse", "HEAD")
    seed_proof(candidate, head)

    result = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=previous)

    assert result["ok"] is True
    assert result["release_mirror"]["worktree_sync"] == "synced"
    assert git(release, "rev-parse", "HEAD") == head
    assert git(release, "status", "--short") == ""
