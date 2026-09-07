from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.commit.admission import commit_message_report
from ethos.adapters.repo.commit.admission import commit_range_admission_report
from ethos.adapters.repo.commit.admission import head_commit_policy_report
from ethos.adapters.repo.commit.admission import validate_commit_revisions
from ethos.adapters.repo.git_object import zero_oid
from ethos.repository.policy.commit import CommitPolicy
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _policy(*, signing_required: bool = False) -> str:
    return (
        '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        f"signing_required = {str(signing_required).lower()}\n"
        'signing_format = "ssh"\n'
    )


def _commit(
    repo: Path,
    subject: str,
    name: str,
    *,
    policy: str | None = None,
    signed: bool = False,
) -> str:
    if policy is not None:
        path = repo / ".ethos/workspace.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(policy, encoding="utf-8")
    (repo / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, *(("-c", "commit.gpgsign=true") if signed else ()), "commit", "-m", subject)
    return git(repo, "rev-parse", "HEAD")


def _report(
    repo: Path,
    *,
    proposed: str,
    remote: str,
    target: str = "refs/heads/dev",
    remote_name: str = "origin",
    trusted_baseline: str = "",
) -> dict[str, object]:
    return commit_range_admission_report(
        repo,
        target_ref=target,
        proposed_head=proposed,
        remote_head=remote,
        remote_name=remote_name,
        trusted_baseline=trusted_baseline,
    )


def test_head_report_exposes_current_identity_and_invalid_subject(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    policy = CommitPolicy(
        subject_pattern=r"^fix: .+",
        signing_required=False,
        signing_format="ssh",
    )

    report = head_commit_policy_report(repo, policy)

    assert report["verdict"] == "block"
    assert report["head"] == {
        "object_oid": git(repo, "rev-parse", "HEAD"),
        "subject": "init",
        "author": {"name": "ETHOS Test", "email": "test@example.invalid"},
        "committer": {"name": "ETHOS Test", "email": "test@example.invalid"},
    }
    assert report["signature"] == {
        "verdict": "pass",
        "required": False,
        "state": "not_required",
        "present": False,
        "format": "",
        "required_gaps": [],
    }
    assert report["required_gaps"] == [
        f"commit_subject_invalid:{report['head']['object_oid']}:init"
    ]


def test_head_report_rejects_a_missing_required_signature(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    policy = CommitPolicy(
        subject_pattern=r"^init$",
        signing_required=True,
        signing_format="ssh",
    )

    report = head_commit_policy_report(repo, policy)

    head = git(repo, "rev-parse", "HEAD")
    gap = f"commit_signature_missing:{head}"
    assert report["signature"] == {
        "verdict": "block",
        "required": True,
        "state": "missing",
        "present": False,
        "format": "",
        "required_gaps": [gap],
    }
    assert report["required_gaps"] == [gap]


def test_head_report_rejects_the_wrong_signature_format(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    payload = (
        f"tree {tree}\n"
        "author Test User <test@example.invalid> 0 +0000\n"
        "committer Test User <test@example.invalid> 0 +0000\n"
        "gpgsig -----BEGIN PGP SIGNATURE-----\n"
        " synthetic\n"
        " -----END PGP SIGNATURE-----\n"
        "\n"
        "fix: wrong signing format\n"
    )
    completed = subprocess.run(
        (
            "git",
            "-c",
            "core.hooksPath=.git/test-hooks",
            "hash-object",
            "-t",
            "commit",
            "-w",
            "--stdin",
        ),
        cwd=repo,
        check=True,
        text=True,
        input=payload,
        capture_output=True,
    )
    head = completed.stdout.strip()
    git(repo, "update-ref", "HEAD", head)
    policy = CommitPolicy(
        subject_pattern=r"^fix: .+",
        signing_required=True,
        signing_format="ssh",
    )

    report = head_commit_policy_report(repo, policy)

    gap = f"commit_signature_format_mismatch:{head}:expected=ssh:observed=openpgp"
    assert report["signature"] == {
        "verdict": "block",
        "required": True,
        "state": "format_mismatch",
        "present": True,
        "format": "openpgp",
        "required_gaps": [gap],
    }
    assert report["required_gaps"] == [gap]


def test_head_report_accepts_a_required_ssh_signature(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    key = tmp_path / "signer"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key.as_posix()),
        check=True,
        capture_output=True,
        text=True,
    )
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", key.as_posix())
    head = _commit(repo, "signed target", "target", signed=True)
    policy = CommitPolicy(
        subject_pattern=r"^signed target$",
        signing_required=True,
        signing_format="ssh",
    )

    report = head_commit_policy_report(repo, policy)

    assert report["verdict"] == "pass"
    assert report["signature"] == {
        "verdict": "pass",
        "required": True,
        "state": "present",
        "present": True,
        "format": "ssh",
        "required_gaps": [],
    }
    assert report["head"]["object_oid"] == head


def test_commit_message_rejects_an_unmerged_index_policy(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    policy_path = ".ethos/workspace.toml"
    blobs = []
    for subject in ("base", "ours", "theirs"):
        completed = subprocess.run(
            ("git", "hash-object", "-w", "--stdin"),
            cwd=repo,
            check=True,
            capture_output=True,
            input=_policy().replace("fix", subject),
            text=True,
        )
        blobs.append(completed.stdout.strip())
    subprocess.run(
        ("git", "update-index", "--index-info"),
        cwd=repo,
        check=True,
        capture_output=True,
        input="".join(
            f"100644 {object_id} {stage}\t{policy_path}\n"
            for stage, object_id in enumerate(blobs, start=1)
        ),
        text=True,
    )
    message = repo / ".git/COMMIT_EDITMSG"
    message.write_text("fix: prospective commit\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"^commit_policy_index_unmerged$"):
        commit_message_report(repo, message)


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_fast_forward_range_is_oldest_first_and_excludes_old_history(
    tmp_path: Path,
    object_format: str,
) -> None:
    repo = init_git_repo(tmp_path / object_format, object_format=object_format)
    baseline = git(repo, "rev-parse", "HEAD")
    first = _commit(repo, "fix: first", "first", policy=_policy())
    second = _commit(repo, "fix: second", "second")

    report = _report(repo, proposed=second, remote=baseline)

    assert report["verdict"] == "pass"
    assert report["update_kind"] == "existing"
    assert report["baseline_commit"] == baseline
    assert report["proposed_commit"] == second
    assert report["revisions"] == [first, second]
    assert report["checked_commit_count"] == 2
    assert report["required_gaps"] == []


def test_non_fast_forward_range_is_the_newly_reachable_set(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-b", "remote-line")
    remote = _commit(repo, "legacy remote subject", "remote")
    git(repo, "checkout", "dev")
    assert git(repo, "rev-parse", "HEAD") == baseline
    proposed = _commit(repo, "fix: replacement", "replacement", policy=_policy())

    report = _report(repo, proposed=proposed, remote=remote)

    assert report["verdict"] == "pass"
    assert report["revisions"] == [proposed]


def test_new_proposal_derives_the_remote_accepted_baseline(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/upstream/dev", baseline)
    proposed = _commit(repo, "fix: proposal", "proposal", policy=_policy())

    report = _report(
        repo,
        proposed=proposed,
        remote=zero_oid(repo),
        target="refs/heads/proposal/feature",
        remote_name="upstream",
    )

    assert report["verdict"] == "pass"
    assert report["update_kind"] == "create"
    assert report["baseline_source"] == "declared_remote_accepted_ref"
    assert report["baseline_ref"] == "refs/remotes/upstream/dev"
    assert report["baseline_commit"] == baseline
    assert report["revisions"] == [proposed]


def test_new_proposal_rejects_a_diverged_accepted_baseline(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "checkout", "-b", "remote-line")
    remote = _commit(repo, "remote history", "remote")
    git(repo, "update-ref", "refs/remotes/origin/dev", remote)
    git(repo, "checkout", "dev")
    proposed = _commit(repo, "fix: proposal", "proposal", policy=_policy())

    report = _report(
        repo,
        proposed=proposed,
        remote=zero_oid(repo),
        target="refs/heads/proposal/feature",
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        f"commit_range_trusted_baseline_not_ancestor:{remote}:{proposed}"
    ]
    assert report["checked_commit_count"] == 0


def test_new_non_proposal_ref_requires_an_explicit_trusted_baseline(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    proposed = _commit(repo, "fix: topic", "topic", policy=_policy())

    report = _report(
        repo,
        proposed=proposed,
        remote=zero_oid(repo),
        target="refs/heads/topic",
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["commit_range_trusted_baseline_required:refs/heads/topic"]


def test_new_non_proposal_ref_accepts_an_explicit_trusted_baseline(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "fix: topic", "topic", policy=_policy())

    report = _report(
        repo,
        proposed=proposed,
        remote=zero_oid(repo),
        target="refs/heads/topic",
        trusted_baseline=baseline,
    )

    assert report["verdict"] == "pass"
    assert report["baseline_source"] == "explicit_trusted_baseline"
    assert report["revisions"] == [proposed]


def test_delete_has_no_commit_range(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    remote = git(repo, "rev-parse", "HEAD")

    report = _report(repo, proposed=zero_oid(repo), remote=remote)

    assert report["verdict"] == "pass"
    assert report["state"] == "no_range"
    assert report["update_kind"] == "delete"
    assert report["revisions"] == []
    assert report["checked_commit_count"] == 0


@pytest.mark.parametrize("tagged_endpoint", ["baseline", "proposed"])
def test_annotated_tag_endpoints_are_peeled_to_commits(
    tmp_path: Path,
    tagged_endpoint: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "fix: tagged", "tagged", policy=_policy())
    commit = baseline if tagged_endpoint == "baseline" else proposed
    tag = f"{tagged_endpoint}-tag"
    git(repo, "tag", "-a", "-m", tag, tag, commit)
    tag_object = git(repo, "rev-parse", f"refs/tags/{tag}")

    report = _report(
        repo,
        proposed=tag_object if tagged_endpoint == "proposed" else proposed,
        remote=tag_object if tagged_endpoint == "baseline" else baseline,
    )

    assert report["verdict"] == "pass"
    assert report["baseline_commit"] == baseline
    assert report["proposed_commit"] == proposed
    assert report["revisions"] == [proposed]


def test_absent_tip_policy_adds_no_commit_constraint(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "unconstrained subject", "unconstrained")

    report = _report(repo, proposed=proposed, remote=baseline)

    assert report["verdict"] == "pass"
    assert report["policy"] is None
    assert report["revisions"] == [proposed]


def test_malformed_tip_policy_fails_closed_before_range_admission(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "fix: malformed policy", "malformed", policy="[commit_policy\n")

    report = _report(repo, proposed=proposed, remote=baseline)

    assert report["verdict"] == "block"
    assert report["required_gaps"][0].startswith("commit_policy_toml_invalid:")
    assert report["checked_commit_count"] == 0


def test_unreadable_tip_policy_object_fails_closed_before_range_admission(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "fix: unreadable policy", "unreadable", policy=_policy())
    policy_object = git(repo, "rev-parse", f"{proposed}:.ethos/workspace.toml")
    object_path = repo / ".git" / "objects" / policy_object[:2] / policy_object[2:]
    object_path.unlink()

    report = _report(repo, proposed=proposed, remote=baseline)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [f"commit_policy_projection_unreadable:{proposed}"]
    assert report["checked_commit_count"] == 0


def test_invalid_subject_identifies_the_exact_introduced_commit(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "invalid subject", "invalid", policy=_policy())

    report = _report(repo, proposed=proposed, remote=baseline)

    gap = f"commit_subject_invalid:{proposed}:invalid subject"
    assert report["verdict"] == "block"
    assert report["violations"] == [
        {"commit": proposed, "subject": "invalid subject", "required_gaps": [gap]}
    ]
    assert report["required_gaps"] == [gap]


def test_required_signature_must_be_present(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "fix: unsigned", "unsigned", policy=_policy(signing_required=True))

    report = _report(repo, proposed=proposed, remote=baseline)

    assert report["required_gaps"] == [f"commit_signature_missing:{proposed}"]


def test_required_signature_must_have_the_declared_format(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    path = repo / ".ethos/workspace.toml"
    path.parent.mkdir(parents=True)
    path.write_text(_policy(signing_required=True), encoding="utf-8")
    git(repo, "add", ".ethos/workspace.toml")
    tree = git(repo, "write-tree")
    payload = (
        f"tree {tree}\n"
        f"parent {baseline}\n"
        "author Test User <test@example.invalid> 0 +0000\n"
        "committer Test User <test@example.invalid> 0 +0000\n"
        "gpgsig -----BEGIN PGP SIGNATURE-----\n"
        " synthetic\n"
        " -----END PGP SIGNATURE-----\n"
        "\n"
        "fix: wrong format\n"
    )
    proposed = subprocess.run(
        ("git", "hash-object", "-t", "commit", "-w", "--stdin"),
        cwd=repo,
        check=True,
        capture_output=True,
        input=payload,
        text=True,
    ).stdout.strip()

    report = _report(repo, proposed=proposed, remote=baseline)

    assert report["required_gaps"] == [
        f"commit_signature_format_mismatch:{proposed}:expected=ssh:observed=openpgp"
    ]


def test_required_ssh_signature_shape_is_admitted(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    key = tmp_path / "signer"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key.as_posix()),
        check=True,
        capture_output=True,
        text=True,
    )
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", key.as_posix())
    proposed = _commit(
        repo,
        "fix: signed",
        "signed",
        policy=_policy(signing_required=True),
        signed=True,
    )

    report = _report(repo, proposed=proposed, remote=baseline)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []


def test_operation_specific_trust_uses_the_same_revision_validator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revisions = ("a" * 40, "b" * 40)
    observations = {
        revision: {
            "subject": subject,
            "signature": {"present": True, "format": "ssh"},
            "required_gaps": [],
        }
        for revision, subject in zip(revisions, ("fix: first", "fix: second"), strict=True)
    }
    verified: list[str] = []
    monkeypatch.setattr(
        "ethos.adapters.repo.commit.admission.observe_commit",
        lambda _root, revision: observations[revision],
    )
    monkeypatch.setattr(
        "ethos.adapters.repo.commit.admission.verify_commit_trust",
        lambda _root, revision: verified.append(revision) or {"required_gaps": []},
    )

    violations, gaps = validate_commit_revisions(
        tmp_path,
        revisions,
        policy=CommitPolicy(
            subject_pattern=r"^fix: .+",
            signing_required=True,
            signing_format="ssh",
        ),
        verify_trust=True,
    )

    assert violations == []
    assert gaps == []
    assert verified == list(revisions)


def test_operation_specific_trust_reports_the_exact_failing_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = "a" * 40
    monkeypatch.setattr(
        "ethos.adapters.repo.commit.admission.observe_commit",
        lambda *_args: {
            "subject": "fix: signed",
            "signature": {"present": True, "format": "ssh"},
            "required_gaps": [],
        },
    )
    monkeypatch.setattr(
        "ethos.adapters.repo.commit.admission.verify_commit_trust",
        lambda *_args: {"required_gaps": ["git_signature_untrusted"]},
    )

    violations, gaps = validate_commit_revisions(
        tmp_path,
        (revision,),
        policy=CommitPolicy(
            subject_pattern=r"^fix: .+",
            signing_required=True,
            signing_format="ssh",
        ),
        verify_trust=True,
    )

    assert violations == [
        {
            "commit": revision,
            "subject": "fix: signed",
            "required_gaps": ["git_signature_untrusted"],
        }
    ]
    assert gaps == ["git_signature_untrusted"]


@pytest.mark.parametrize(
    ("coordinate", "expected_gap"),
    [
        ("proposed", "commit_range_proposed_unreadable:missing"),
        ("remote", "commit_range_remote_unreadable:missing"),
    ],
)
def test_unreadable_endpoint_fails_closed(
    tmp_path: Path,
    coordinate: str,
    expected_gap: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    report = _report(
        repo,
        proposed="missing" if coordinate == "proposed" else head,
        remote="missing" if coordinate == "remote" else head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [expected_gap]
