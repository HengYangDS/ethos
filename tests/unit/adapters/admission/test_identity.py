from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.admission.identity import push_identity_policy_report
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "case", ["disabled", "matched", "author", "committer", "missing", "unreadable"]
)
def test_configured_identity_admits_only_the_supplied_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    revision = git(repo, "rev-parse", "HEAD")
    if case != "disabled":
        git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    if case != "missing":
        git(repo, "config", "user.name", "ETHOS Test")
        git(repo, "config", "user.email", "test@example.invalid")
    if case in {"author", "committer"}:
        monkeypatch.setenv(f"GIT_{case.upper()}_NAME", "Other")
        git(repo, "commit", "--allow-empty", "-m", "another object")
        revision = git(repo, "rev-parse", "HEAD")
    revisions = ("missing",) if case in {"missing", "unreadable"} else (revision,)

    report = push_identity_policy_report(repo, revisions)

    gaps = {
        "disabled": [],
        "matched": [],
        "author": [f"pushed_commit_author_not_configured_identity:{revision}"],
        "committer": [f"pushed_commit_committer_not_configured_identity:{revision}"],
        "missing": [
            "push_identity_user_name_missing",
            "push_identity_user_email_missing",
            "push_identity_commit_unreadable:missing",
        ],
        "unreadable": ["push_identity_commit_unreadable:missing"],
    }[case]
    assert report["required_gaps"] == gaps
    assert report["verdict"] == ("block" if gaps else "pass")
    assert report["checked_commit_count"] == (case in {"matched", "author", "committer"})
    assert [item["commit"] for item in report["violations"]] == (list(revisions) if gaps else [])


def test_push_shares_one_introduced_range_between_policy_and_identity(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    remote = git(repo, "rev-parse", "HEAD")
    git(repo, "config", "ethos.pushIdentityPolicy", "configured-user")
    git(repo, "config", "user.name", "ETHOS Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / ".ethos/workspace.toml").write_text(
        '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        'signing_required = false\nsigning_format = "ssh"\n'
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(repo, "commit", "-m", "invalid subject")
    head = git(repo, "rev-parse", "HEAD")

    report = push_admission_report(
        root=repo, target_ref="refs/heads/proposal/identity", pushed_head=head, remote_head=remote
    )

    assert report["commit_policy_admission"]["revisions"] == [head]
    assert report["identity_policy"]["revisions"] == [head]
    assert report["identity_policy"]["checked_commit_count"] == 1
    assert f"commit_subject_invalid:{head}:invalid subject" in report["required_gaps"]
