from __future__ import annotations

import subprocess
from pathlib import Path

from ethos_workspace.mutation import MutationRequest, evaluate_mutation


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def test_mutation_requires_authorization_and_expected_head() -> None:
    request = MutationRequest(command="land", apply=True, authorized=False, expect_head=None)

    result = evaluate_mutation(request, root=Path.cwd(), current_head="abc123")

    assert result.ok is False
    assert "authorization_required" in result.gaps
    assert "expect_head_required" in result.gaps


def test_mutation_allows_dry_run_without_authorization() -> None:
    request = MutationRequest(command="land", apply=False, authorized=False, expect_head=None)

    result = evaluate_mutation(request, root=Path.cwd(), current_head="abc123")

    assert result.ok is True
    assert result.state == "dry_run"


def test_mutation_apply_requires_matching_expected_head(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-apply"
    git(repo, "worktree", "add", "-b", "work/apply", worktree.as_posix(), "dev")
    request = MutationRequest(
        command="publish",
        apply=True,
        authorized=True,
        expect_head="abc123",
    )

    result = evaluate_mutation(request, root=worktree, current_head="abc123")

    assert result.ok is True
    assert result.state == "publish_ready"


def test_mutation_apply_rejects_protected_root_even_with_authorization(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    request = MutationRequest(
        command="land",
        apply=True,
        authorized=True,
        expect_head=git(repo, "rev-parse", "HEAD"),
    )

    result = evaluate_mutation(request, root=repo, current_head=request.expect_head or "")

    assert result.ok is False
    assert result.state == "blocked"
    assert "protected_root_mutation" in result.gaps
