"""Push admission evaluates the remote Git names and never assumes one."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.publication import push_admission_report
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path


def test_push_admission_without_a_remote_name_fails_closed(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo, gitlab_remote="gitlab")
    head = git(repo, "rev-parse", "HEAD")

    report = push_admission_report(
        root=repo, target_ref="refs/heads/proposal/topic", pushed_head=head, remote_head=head
    )

    assert report["verdict"] == "block"
    assert "publication_remote_name_missing" in cast("list[str]", report["required_gaps"])
