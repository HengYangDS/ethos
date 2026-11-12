"""The census counts trailers and peer identity forms by ref class, with no record and no key."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ethos.adapters.repo.commit.rebuild.census import rebuild_census
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.rebuild import F1
from tests.support.rebuild import H1
from tests.support.rebuild import peer_history

if TYPE_CHECKING:
    from pathlib import Path

TRAILER = "Co-Authored-By: Bot <bot@example.com>"


def test_the_census_counts_by_form_and_ref_class_and_writes_nothing(tmp_path: Path) -> None:
    """Each class counts every object its refs reach once; a tag adds its own message."""
    repo, _base = peer_history(tmp_path, bare=True)
    head = commit_fixture_file(
        repo, "docs/more.md", f"ssh git@{H1}:{F1}.git\n", f"docs: more\n\n{TRAILER}"
    )
    git(repo, "tag", "-a", "v1", "-m", f"release via {H1}", head)
    git(repo, "notes", "add", "-m", f"see {F1}", head)
    git(repo, "push", "-q", "--no-verify", "gitlab", "dev")
    before = git(repo, "for-each-ref")

    report = rebuild_census(repo)

    branch = {"host": 1, "path": 2, "scp": 1, "trailer": 1, "url": 1}
    assert (report["verdict"], report["required_gaps"]) == ("pass", [])
    assert report["counts"] == {
        "heads": branch,
        "other": {"path": 1},
        "remotes": branch,
        "tags": branch | {"host": 2},
    }
    assert git(repo, "for-each-ref") == before
    assert H1 not in json.dumps(report)
    assert F1 not in json.dumps(report)


def test_a_feed_the_clone_cannot_know_leaves_the_census_unknown(tmp_path: Path) -> None:
    """Without a protected peer the counts stay, and the census names why they are partial."""
    repo, _base = peer_history(tmp_path, bare=True)
    git(repo, "config", "--unset", "remote.gitlab.forgePrivate")

    report = rebuild_census(repo)

    assert (report["verdict"], report["required_gaps"]) == ("unknown", ["peer_identity_feed_empty"])
    assert report["counts"] == {"heads": {}}
