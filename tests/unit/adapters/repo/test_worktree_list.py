"""Read each Git worktree record whole, from the NUL-terminated listing to lane status."""

from __future__ import annotations

import os
import shutil
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.repo.worktree_effects import worktree_record
from ethos.adapters.repo.worktree_list import listed_worktrees
from ethos.adapters.repo.worktree_list import parse_worktree_list
from ethos.adapters.repo.worktree_list import raw_worktree_records
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path

_HEAD = "a" * 40
_GONE = "gitdir file points to non-existent location"


@pytest.mark.parametrize(
    ("listing", "records"),
    [
        pytest.param("", (), id="empty"),
        pytest.param(
            f"worktree /srv/main\0HEAD {_HEAD}\0branch refs/heads/dev\0\0",
            ({"worktree": "/srv/main", "HEAD": _HEAD, "branch": "refs/heads/dev"},),
            id="branch",
        ),
        pytest.param(
            f"worktree /srv/new\nline lane\0HEAD {_HEAD}\0detached\0locked\0prunable\0\0"
            "worktree /srv/bare\0bare\0\0",
            (
                {
                    "worktree": "/srv/new\nline lane",
                    "HEAD": _HEAD,
                    "detached": "",
                    "locked": "",
                    "prunable": "",
                },
                {"worktree": "/srv/bare", "bare": ""},
            ),
            id="labels-alone",
        ),
        pytest.param(
            f"worktree /srv/held\0HEAD {_HEAD}\0branch refs/heads/work/held\0"
            f"locked on a\nportable disk\0prunable {_GONE}\0\0",
            (
                {
                    "worktree": "/srv/held",
                    "HEAD": _HEAD,
                    "branch": "refs/heads/work/held",
                    "locked": "on a\nportable disk",
                    "prunable": _GONE,
                },
            ),
            id="reasons",
        ),
    ],
)
def test_a_listing_maps_each_record_whole(
    listing: str, records: tuple[dict[str, str], ...]
) -> None:
    """A value keeps its spaces and newlines; a label alone maps to the empty string."""
    assert parse_worktree_list(listing) == records


@pytest.mark.parametrize("gap", [None, "hook_runtime_worktrees_unreadable"])
def test_an_unreadable_listing_is_none_or_the_callers_refusal(
    tmp_path: Path, gap: str | None
) -> None:
    """A listing Git refuses is no record set: lenient callers see None, strict ones their gap."""
    calls = []

    def refused(root: Path, *arguments: str, **options: object) -> SimpleNamespace:
        calls.append((root, arguments, options))
        return SimpleNamespace(returncode=128, stdout="", stderr="fatal: not a git repository")

    selected = {} if gap is None else {"gap": gap}
    with pytest.raises(ValueError, match=f"^{gap or 'worktree_effect_observation_failed'}$"):
        raw_worktree_records(tmp_path, runner=refused, **selected)

    assert listed_worktrees(tmp_path, runner=refused) is None
    listing = (tmp_path, ("worktree", "list", "--porcelain", "-z"), {"check": False, "env": None})
    assert calls == [listing, listing]


@pytest.mark.skipif(os.name == "nt", reason="POSIX paths may hold a newline")
def test_lane_status_reports_each_worktree_as_git_lists_it(tmp_path: Path) -> None:
    """A newline in a path or a lock reason stays in its record, through to the status payload.

    `ethos lane status --json` emits this payload as its `data`. The newline form of the listing
    split the first worktree below into false records and quoted its lock reason.
    """
    repo, _candidate = init_repo_with_candidate(tmp_path)
    split, plain, gone = tmp_path / "split\nlane", tmp_path / "plain", tmp_path / "gone"
    for path in (split, plain, gone):
        git(repo, "worktree", "add", "--detach", path.as_posix(), "dev")
    git(repo, "worktree", "lock", "--reason", "held\nfor review", split.as_posix())
    git(repo, "worktree", "lock", plain.as_posix())
    shutil.rmtree(gone)
    head = git(repo, "rev-parse", "dev")

    status = workspace_status(repo)
    reported = {item["path"].rpartition("/")[2]: item for item in status["worktrees"]}
    fields = ("branch", "head", "locked", "lock_reason", "prunable")

    assert len(raw_worktree_records(repo)) == len(reported) == 5
    assert worktree_record(repo, split)["locked"] == "held\nfor review"
    assert {name: tuple(item[key] for key in fields) for name, item in reported.items()} == {
        "repo": ("dev", head, "false", "", "false"),
        "repo-candidate-dev": ("candidate/dev", head, "false", "", "false"),
        "split\nlane": ("detached", head, "true", "held\nfor review", "false"),
        "plain": ("detached", head, "true", "", "false"),
        "gone": ("detached", head, "false", "", "true"),
    }
    assert {name for name, item in reported.items() if item["prune_reason"]} == {"gone"}
    assert validate_schema_instance("workspace-status.schema.json", status, root=repo) == {
        "verdict": "pass",
        "required_gaps": [],
    }
