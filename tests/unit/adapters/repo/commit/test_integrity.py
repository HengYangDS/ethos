"""Native commit integrity rejects misleading identity and signature projections."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import pytest

from ethos.adapters.repo.commit.admission import commit_message_report
from ethos.adapters.repo.commit.creation import create_git_commit
from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.adapters.repo.commit.integration import validate_replayed_commits
from ethos.adapters.repo.git import run_git
from ethos.repository.policy.commit import commit_policy_from_text
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import render_branch_policy
from tests.support.governed_repository import write_publication_topology
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.signature import configure_signer

if TYPE_CHECKING:
    from pathlib import Path


_POLICY = (
    '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
    'signing_required = true\nsigning_format = "ssh"\n'
)
_IDENTITY = (
    '[commit_policy.author]\nname = "ETHOS Test"\nemail = "test@example.invalid"\n'
    '[commit_policy.committer]\nname = "ETHOS Test"\nemail = "test@example.invalid"\n'
)


def _repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    configure_signer(repo, tmp_path)
    (repo / ".ethos").mkdir()
    (repo / ".ethos/workspace.toml").write_text(_POLICY)
    git(repo, "add", ".ethos/workspace.toml")
    tree = git(repo, "write-tree")
    baseline = git(repo, "commit-tree", tree, "-m", "fix: baseline")
    return repo, baseline, tree


@pytest.mark.parametrize("case", ["valid", "unsigned", "forged", "weakened", "removed"])
def test_range_requires_real_signature_under_trusted_prestate(tmp_path: Path, case: str) -> None:
    repo, baseline, tree = _repository(tmp_path)
    if case in {"weakened", "removed"}:
        (repo / ".ethos/workspace.toml").write_text(
            "" if case == "removed" else _POLICY.replace("true", "false")
        )
        git(repo, "add", ".ethos/workspace.toml")
        tree = git(repo, "write-tree")
    revision = git(
        repo,
        "commit-tree",
        *(("-S",) if case == "valid" else ()),
        tree,
        "-p",
        baseline,
        "-m",
        "fix: candidate",
    )
    if case == "forged":
        raw = run_git(repo, "cat-file", "commit", revision, text=False).stdout
        header, separator, message = raw.partition(b"\n\n")
        forged = (
            header + b"\ngpgsig -----BEGIN SSH SIGNATURE-----\n invalid-base64"
            b"\n -----END SSH SIGNATURE-----" + separator + message
        )
        revision = (
            run_git(repo, "hash-object", "-w", "-t", "commit", "--stdin", stdin=forged, text=False)
            .stdout.decode()
            .strip()
        )
    report = commit_range_admission_report(
        repo,
        target_ref="refs/heads/proposal/test",
        proposed_head=revision,
        remote_head=baseline,
        remote_name="origin",
    )
    assert report["verdict"] == ("pass" if case == "valid" else "block"), report
    assert report["revisions"] == [revision]


@pytest.mark.parametrize("role", ["author", "committer"])
def test_tracked_identity_rejects_prospective_override(tmp_path, monkeypatch, role):
    repo, _baseline, _tree = _repository(tmp_path)
    (repo / ".ethos/workspace.toml").write_text(_POLICY + _IDENTITY)
    git(repo, "add", ".ethos/workspace.toml")
    message = repo / "message"
    message.write_text("fix: prospective\n")
    monkeypatch.setenv(f"GIT_{role.upper()}_NAME", "Wrong Account")
    report = commit_message_report(repo, message)
    assert report["verdict"] == "block"
    assert any(
        f"commit_{role}_identity_mismatch" in gap
        for gap in cast("list[str]", report["required_gaps"])
    )


@pytest.mark.parametrize("role", ["author", "committer"])
def test_tracked_identity_rejects_signed_object(tmp_path, monkeypatch, role):
    repo, baseline, _tree = _repository(tmp_path)
    (repo / ".ethos/workspace.toml").write_text(_POLICY + _IDENTITY)
    git(repo, "add", ".ethos/workspace.toml")
    tree = git(repo, "write-tree")
    monkeypatch.setenv(f"GIT_{role.upper()}_EMAIL", "wrong@example.invalid")
    revision = git(repo, "commit-tree", "-S", tree, "-p", baseline, "-m", "fix: signed")
    report = commit_range_admission_report(
        repo,
        target_ref="refs/heads/proposal/test",
        proposed_head=revision,
        remote_head=baseline,
        remote_name="origin",
    )
    assert report["verdict"] == "block"
    assert any(
        f"commit_{role}_identity_mismatch" in gap
        for gap in cast("list[str]", report["required_gaps"])
    )


def test_identity_constraints_have_one_strict_compiler():
    policy = commit_policy_from_text(_POLICY + _IDENTITY)
    assert policy is not None
    assert policy.projection()["author"] == {"name": "ETHOS Test", "email": "test@example.invalid"}
    with pytest.raises(ValueError, match="commit_policy_invalid:author"):
        commit_policy_from_text(_POLICY + '[commit_policy.author]\nname="Partial"\n')


@pytest.mark.parametrize("case", ["identity", "subject", "policy_removed"])
def test_prospective_candidate_cannot_waive_incumbent_constraints(tmp_path, monkeypatch, case):
    repo, _baseline, _tree = _repository(tmp_path)
    original = _POLICY + _IDENTITY
    (repo / ".ethos/workspace.toml").write_text(original)
    git(repo, "add", ".ethos/workspace.toml")
    git(repo, "commit", "-m", "fix: declared")
    weakened = "" if case == "policy_removed" else _POLICY
    if case == "subject":
        weakened = weakened.replace('"^fix: .+"', '".*"')
    (repo / ".ethos/workspace.toml").write_text(weakened)
    git(repo, "add", ".ethos/workspace.toml")
    if case != "subject":
        monkeypatch.setenv("GIT_AUTHOR_NAME", "Wrong Account")
    message = repo / "message"
    message.write_text("invalid" if case == "subject" else "fix: cannot self-authorize")
    assert commit_message_report(repo, message)["verdict"] == "block"


@pytest.mark.parametrize("case", ["parent", "target", "identity", "subject", "malformed"])
def test_generated_commit_uses_exact_parent_and_target_not_checkout(tmp_path, case):
    repo, baseline, tree = _repository(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    if case == "identity":
        workspace.write_text(_POLICY + _IDENTITY)
        git(repo, "add", ".ethos/workspace.toml")
        tree = git(repo, "write-tree")
        baseline = git(repo, "commit-tree", tree, "-m", "fix: constrained parent")
    if case in {"parent", "identity"}:
        workspace.write_text("")
    elif case == "malformed":
        workspace.write_text("[commit_policy]\nsigning_required = 42\n")
    git(repo, "add", ".ethos/workspace.toml")
    tree = git(repo, "write-tree")
    # The editable checkout is not the tree passed to commit-tree.
    workspace.write_text("")
    if case == "target":
        baseline = git(repo, "rev-parse", "HEAD")

    def create():
        return create_git_commit(
            repo,
            tree=tree,
            parent=baseline,
            message="invalid subject" if case == "subject" else "fix: generated",
            environment={"GIT_AUTHOR_NAME": "Wrong"} if case == "identity" else None,
        )

    if case in {"identity", "subject", "malformed"}:
        with pytest.raises(
            ValueError, match=r"commit_(author_identity_mismatch|subject_invalid|policy_invalid)"
        ):
            create()
    else:
        result = create()
        assert result.returncode == 0, result.stderr
        assert run_git(repo, "verify-commit", result.stdout.strip(), check=False).returncode == 0


@pytest.mark.parametrize("case", ["identity", "unsigned", "valid"])
def test_native_hooks_reject_commit_or_push_without_parallel_policy(tmp_path, monkeypatch, case):
    repo, _baseline, _tree = _repository(tmp_path)
    write_publication_topology(repo)
    (repo / ".ethos/workspace.toml").write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        )
        + "\n"
        + _POLICY
        + _IDENTITY
    )
    git(repo, "add", ".")
    git(repo, "commit", "-S", "-m", "fix: baseline")
    git(repo, "branch", "topic")
    git(repo, "checkout", "topic")
    baseline = git(repo, "rev-parse", "HEAD")
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "origin", "refs/heads/topic:refs/heads/proposal/test")
    install_fixture_hook_runtime(repo)
    if case == "identity":
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "wrong@example.invalid")
        rejected = git_process(repo, "commit", "--allow-empty", "-S", "-m", "fix: wrong")
        assert rejected.returncode != 0, rejected
        assert "commit_author_identity_mismatch" in rejected.stderr
        assert git(repo, "rev-parse", "HEAD") == baseline
    committed = git_process(
        repo,
        "commit",
        "--no-verify",
        "--allow-empty",
        "--no-gpg-sign" if case == "unsigned" else "-S",
        "-m",
        "fix: exact range",
    )
    assert committed.returncode == 0, committed.stderr
    pushed = git_process(repo, "push", "origin", "refs/heads/topic:refs/heads/proposal/test")
    if case == "valid":
        assert pushed.returncode == 0, pushed.stderr
        assert git(remote, "rev-parse", "refs/heads/proposal/test") == git(
            repo, "rev-parse", "HEAD"
        )
    else:
        assert pushed.returncode != 0, pushed
        expected = (
            "commit_signature_missing" if case == "unsigned" else "commit_author_identity_mismatch"
        )
        assert expected in pushed.stderr
        assert git(remote, "rev-parse", "refs/heads/proposal/test") == baseline


def test_replayed_commits_cannot_waive_trusted_baseline_signatures(tmp_path):
    repo, baseline, tree = _repository(tmp_path)
    revision = git(repo, "commit-tree", tree, "-p", baseline, "-m", "fix: unsigned replay")
    assert validate_replayed_commits(
        repo, baseline_commit=baseline, proposed_commit=revision, policy=None
    ) == [f"commit_signature_missing:{revision}"]
