"""Publication consumes tracked identity policy from the shared commit validator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import pytest

from ethos.adapters.admission.publication import push_admission_report
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("role", ["author", "committer"])
def test_publication_uses_the_declared_identity_and_existing_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    baseline = git(repo, "rev-parse", "HEAD")
    (repo / ".ethos/workspace.toml").write_text(
        '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        'signing_required = false\nsigning_format = "ssh"\n'
        f'[commit_policy.{role}]\nname = "ETHOS Test"\nemail = "test@example.invalid"\n'
    )
    git(repo, "add", ".ethos/workspace.toml")
    monkeypatch.setenv(f"GIT_{role.upper()}_EMAIL", "wrong@example.invalid")
    git(repo, "commit", "-m", "fix: candidate")
    head = git(repo, "rev-parse", "HEAD")
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/proposal/identity",
        pushed_head=head,
        remote_head=baseline,
    )
    assert report["verdict"] == "block"
    assert f"commit_{role}_identity_mismatch:{head}" in cast("list[str]", report["required_gaps"])
    assert cast("dict[str, object]", report["commit_policy_admission"])["revisions"] == [head]
    assert "identity_policy" not in report
