"""An absorbed-ref retirement preview blocks where the prepared hook would refuse its deletion."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    from pathlib import Path

_LEGACY_TABLE = '[branch_roles]\ncandidate_branch = "integration/dev"\n'


def _retire(repo: Path, branch: str, head: str, *, apply: bool, blocked: bool) -> dict[str, object]:
    command = run_ethos_blocked if blocked else run_ethos
    return command(
        "lane",
        "retire",
        "absorbed-ref",
        "--branch",
        branch,
        "--expect-head",
        head,
        "--accepted-head",
        head,
        "--root",
        repo.as_posix(),
        *(("--authorize", "--confirm-irreversible", "--apply") if apply else ()),
        "--json",
        cwd=repo,
    )


def _legacy_repository(tmp_path: Path) -> tuple[Path, str]:
    """Accept a committed table that names `integration/dev` as the legacy candidate."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    (repo / ".ethos/workspace.toml").write_text(_LEGACY_TABLE, encoding="utf-8")
    head = commit_fixture(repo, "chore: declare a legacy candidate name")
    git(repo, "branch", "integration/dev", head)
    return repo, head


def _refs(repo: Path) -> str:
    return git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads")


def test_a_protected_legacy_role_ref_blocks_the_preview(tmp_path: Path) -> None:
    """Without a successor at its commit, the preview names the hook's refusal and the closeout."""
    repo, head = _legacy_repository(tmp_path)
    before = _refs(repo)

    preview = _retire(repo, "integration/dev", head, apply=False, blocked=False)

    assert (preview["verdict"], preview["required_gaps"]) == (
        "block",
        ["legacy_role_ref_protected"],
    )
    action = preview["next_action"]
    assert isinstance(action, str)
    assert shlex.split(action)[:3] == ["ethos", "land", "--closeout"]
    assert "--apply" not in action
    assert _refs(repo) == before


def test_a_deletion_without_a_governing_policy_blocks_the_preview(tmp_path: Path) -> None:
    """An accepted head without a release binding or valid profile cannot retire a topic ref.

    Its profile keeps the stable identity of an older schema, as an adopter's pre-paradigm head
    does, so only the policy that governs the deletion is missing.
    """
    repo = init_git_repo(tmp_path / "repo")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "fixture-old"\nschema_version = 1\n\n[repository]\nname = "old"\n',
        encoding="utf-8",
    )
    head = commit_fixture(repo, "chore: keep an older profile schema")
    git(repo, "branch", "work/orphaned", head)
    before = _refs(repo)

    preview = _retire(repo, "work/orphaned", head, apply=False, blocked=False)

    assert (preview["verdict"], preview["required_gaps"]) == (
        "block",
        ["ref_move_policy_unavailable"],
    )
    action = preview["next_action"]
    assert isinstance(action, str)
    assert "--apply" not in action
    assert _refs(repo) == before


def test_a_legacy_ref_that_duplicates_its_successor_is_retired(tmp_path: Path) -> None:
    """The deletion alone loses nothing, so the installed hook admits it and nothing else moves."""
    repo, head = _legacy_repository(tmp_path)
    git(repo, "branch", "candidate/dev", head)
    install_fixture_hook_runtime(repo)
    kept = {name: git(repo, "rev-parse", name) for name in ("dev", "candidate/dev")}

    retired = _retire(repo, "integration/dev", head, apply=True, blocked=False)

    assert (retired["verdict"], retired["state"]) == ("pass", "retired_absorbed_ref")
    assert not git(repo, "branch", "--list", "integration/dev")
    assert {name: git(repo, "rev-parse", name) for name in kept} == kept


def test_a_legacy_ref_at_another_commit_than_its_successor_stays_protected(tmp_path: Path) -> None:
    """A successor at a different commit leaves the legacy ref's content unique, so it stays."""
    repo, head = _legacy_repository(tmp_path)
    git(repo, "branch", "candidate/dev", "HEAD~1")
    install_fixture_hook_runtime(repo)

    blocked = _retire(repo, "integration/dev", head, apply=True, blocked=True)

    assert blocked["required_gaps"] == ["legacy_role_ref_protected"]
    assert git(repo, "rev-parse", "integration/dev") == head
