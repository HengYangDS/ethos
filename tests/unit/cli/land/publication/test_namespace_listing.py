"""One bounded observer lists a peer's exact refs or its namespaces, never echoing its stderr."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.publication.observation as observation
from ethos.adapters.mutation.publication.absorption import absorbed_proposals
from ethos.adapters.mutation.publication.retirement import REVIEW_HEADS
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.publication import PublicationTarget
from ethos.contracts.publication import PublicationUpdate
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.publication import PublicationEffect

# What a peer's stderr may echo; no report may carry it.
ECHO = "fatal: unable to access forge.example.invalid/team/infra/tools"
NAMESPACES = ("refs/heads/*", "refs/tags/*", "refs/ethos/*", *REVIEW_HEADS)


@pytest.fixture
def peer(tmp_path: Path) -> tuple[Path, str, str]:
    """A repository and a bare peer holding refs inside and outside the listed namespaces."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-a", "v1", "-m", "release v1")
    bare = tmp_path / "peer.git"
    git(tmp_path, "init", "--bare", "-q", str(bare))
    git(repo, "remote", "add", "gitlab", str(bare))
    refs = (
        "refs/heads/dev",
        "refs/heads/team/side",
        "refs/ethos/attestations-set",
        "refs/pull/3/head",
        "refs/pull/3/merge",
        "refs/merge-requests/4/head",
        "refs/keep/one",
        "refs/remotes/o/refs/heads/nested",
    )
    git(repo, "push", "-q", "--no-verify", "gitlab", *(f"{head}:{ref}" for ref in refs), "v1")
    return repo, head, git(repo, "rev-parse", "v1")


def test_a_namespace_listing_holds_every_ref_under_its_patterns_and_records_nothing(
    peer: tuple[Path, str, str],
) -> None:
    """Branches, tags with their peeled commit, `refs/ethos/` and review heads, nothing else."""
    repo, head, tag = peer
    before = git(repo, "for-each-ref")

    listed = observation.observe_remote_namespaces(repo, "gitlab", NAMESPACES)

    assert listed.failure is None
    assert dict(listed.refs) == {
        "refs/heads/dev": head,
        "refs/heads/team/side": head,
        "refs/tags/v1": tag,
        "refs/tags/v1^{}": head,
        "refs/ethos/attestations-set": head,
        "refs/pull/3/head": head,
        "refs/merge-requests/4/head": head,
    }
    assert REVIEW_HEADS == ("refs/pull/*/head", "refs/merge-requests/*/head")
    whole = observation.observe_remote_namespaces(repo, "gitlab", ())
    assert {"refs/keep/one", "refs/pull/3/merge"} <= set(whole.refs)
    assert git(repo, "for-each-ref") == before


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        (subprocess.TimeoutExpired(("git", "ls-remote"), 30, stderr=ECHO), "timeout"),
        (subprocess.CompletedProcess(("git", "ls-remote"), 128, "", ECHO), "ls_remote_failed"),
        (subprocess.CompletedProcess(("git", "ls-remote"), 0, "a\tb\na\tb\n", ECHO), "ambiguous"),
    ],
)
def test_a_failed_observation_keeps_its_boundary_and_never_the_peer_stderr(
    peer: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    fault: object,
    reason: str,
) -> None:
    """The exact-ref and the namespace observer both name the command, cwd and exit state."""
    repo, _head, _tag = peer
    monkeypatch.setattr(observation.git, "run_network_git", Mock(side_effect=[fault, fault]))

    listed = observation.observe_remote_namespaces(repo, "gitlab", NAMESPACES)
    exact = observation.observe_remote_ref(repo, "gitlab", "refs/heads/dev")

    assert listed.failure is not None
    assert dict(listed.refs) == {}
    for failure in (dict(listed.failure), exact):
        assert reason in str(failure["reason"])
        assert failure["cwd"] == repo.resolve().as_posix()
        assert failure["command"]
        assert "stderr" not in failure
        assert "forge.example.invalid" not in json.dumps(failure)
    assert exact["state"] == "unavailable"


def test_absorption_lists_a_moved_peers_proposals_through_the_same_observer(
    peer: tuple[Path, str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A preserved proposal is named; an unreadable listing names its peer, not an empty one."""
    repo, head, _tag = peer
    prefix = f"refs/heads/{load_branch_role_policy(repo).proposal_branch_prefix}"
    side = git(repo, "commit-tree", f"{head}^{{tree}}", "-p", head, "-m", "side proposal")
    git(repo, "push", "-q", "--no-verify", "gitlab", f"{head}:{prefix}kept", f"{side}:{prefix}side")
    update = PublicationUpdate(target_ref="refs/heads/dev", expected="0" * 40, desired=head)
    target = PublicationTarget(id="gitlab", remote="gitlab", updates=(update,))
    effect = cast("PublicationEffect", SimpleNamespace(targets=(target,)))

    assert absorbed_proposals(repo, effect) == ({"gitlab": [f"{prefix}kept"]}, [])
    stalled = subprocess.TimeoutExpired(("git", "ls-remote"), 30)
    monkeypatch.setattr(observation.git, "run_network_git", Mock(side_effect=[stalled]))
    assert absorbed_proposals(repo, effect) == ({}, ["gitlab"])
