"""Lifetime facts come from one exact observation of refs, worktrees and pre-repair objects."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import ethos.adapters.repo.attestation_set as attestation_set
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture
from tests.support.semantic import occurrence_attestation

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation

_START = datetime(2026, 10, 1, tzinfo=UTC)


def _record(predicate: str, commit: str, body: dict[str, object]) -> Attestation:
    return attestation_fixture(
        predicate=predicate,
        verifier="agent:test:lifetime-facts",
        subject=f"git:commit:{commit}",
        issued_at=_START,
        payload_kind=predicate,
        payload_body=body,
        evidence_refs=("evidence:test:lifetime-facts",),
    )


def _removed_by_next_update(repo: Path, members: tuple[Attestation, ...]) -> object:
    attestation_set.record_attestations(repo, members)
    return attestation_set.record_attestations(repo, (occurrence_attestation(6_201),))["removed"]


def test_tags_of_tags_and_detached_worktrees_keep_their_head_records(tmp_path: Path) -> None:
    """A tag of a tag and a detached worktree HEAD select heads; an unselected head ends."""
    repo = init_git_repo(tmp_path / "repo")
    tagged = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-a", "inner", "-m", "inner", tagged)
    git(repo, "tag", "-a", "outer", "-m", "outer", "inner")
    git(repo, "tag", "-d", "inner")
    detached = commit_fixture_file(repo, "second.txt", "second\n", "second")
    git(repo, "worktree", "add", "--detach", (tmp_path / "detached").as_posix(), detached)
    superseded = commit_fixture_file(repo, "third.txt", "third\n", "third")
    commit_fixture_file(repo, "fourth.txt", "fourth\n", "fourth")
    proofs = tuple(
        _record("proof:execution", commit, {"head": commit})
        for commit in (tagged, detached, superseded)
    )

    assert _removed_by_next_update(repo, proofs) == (proofs[2].id,)


def test_repair_lineage_ends_only_for_absent_pre_repair_objects(tmp_path: Path) -> None:
    """A batch object check ends the repair record of a missing commit and keeps a present one."""
    repo = init_git_repo(tmp_path / "repo")
    present = git(repo, "rev-parse", "HEAD")
    absent = "0" * 39 + "1"
    repairs = tuple(
        _record("effect:commit-signature", old, {"coordinates": {"old": old}})
        for old in (present, absent)
    )

    assert _removed_by_next_update(repo, repairs) == (repairs[1].id,)
