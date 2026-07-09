from __future__ import annotations

from pathlib import Path

from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked


def _start_feature_lane(repo: Path, worktree: Path) -> None:
    run_ethos(
        "lane",
        "start",
        "feature",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--apply",
        "--json",
        cwd=repo,
    )


def _commit(root: Path, message: str) -> None:
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )


def test_lane_refresh_base_resolves_parity_projection_conflict_as_stale_projection(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    worktree = tmp_path / "repo-work-feature"
    _start_feature_lane(repo, worktree)
    projection = Path("evidence/parity/generic-shadow.json")
    (candidate / projection.parent).mkdir(parents=True, exist_ok=True)
    (worktree / projection.parent).mkdir(parents=True, exist_ok=True)
    (candidate / projection).write_text(
        '{"freshness":{"product_head":"candidate"}}\n',
        encoding="utf-8",
    )
    git(candidate, "add", projection.as_posix())
    _commit(candidate, "refresh candidate projection")
    (worktree / projection).write_text(
        '{"freshness":{"product_head":"work"}}\n',
        encoding="utf-8",
    )
    (worktree / "FEATURE.md").write_text("# feature\n", encoding="utf-8")
    git(worktree, "add", projection.as_posix(), "FEATURE.md")
    _commit(worktree, "feature work with stale projection")
    previous_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")

    payload = run_ethos(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous_head,
        "--json",
        cwd=worktree,
    )

    refreshed_head = git(worktree, "rev-parse", "HEAD")
    assert payload["ok"] is True
    assert payload["state"] == "base_refreshed_projection_stale"
    assert payload["required_gaps"] == []
    assert payload["next_actions"] == [
        "ethos parity shadow --adopter generic --target . --execute --write-evidence --json",
        "ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
    ]
    assert payload["data"]["previous_head"] == previous_head
    assert payload["data"]["head"] == refreshed_head
    assert payload["data"]["candidate_head"] == candidate_head
    assert payload["data"]["projection_refresh_required"] is True
    assert payload["data"]["projection_refresh_gaps"] == [
        "projection_regeneration_required:parity:generic"
    ]
    assert payload["data"]["stale_projection_paths"] == [projection.as_posix()]
    assert (worktree / projection).read_text(encoding="utf-8") == (
        candidate / projection
    ).read_text(encoding="utf-8")
    assert (worktree / "FEATURE.md").read_text(encoding="utf-8") == "# feature\n"


def test_lane_refresh_base_keeps_real_content_conflict_blocking(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    worktree = tmp_path / "repo-work-feature"
    _start_feature_lane(repo, worktree)
    (candidate / "README.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    _commit(candidate, "candidate content")
    (worktree / "README.md").write_text("# work\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    _commit(worktree, "work content")
    previous_head = git(worktree, "rev-parse", "HEAD")

    payload = run_ethos_blocked(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous_head,
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["refresh_base_failed"]
    assert payload["data"].get("projection_refresh_required") is None
    assert git(worktree, "rev-parse", "HEAD") == previous_head
