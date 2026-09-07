from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.commit.creation as creation
from ethos.repository.policy.commit import CommitPolicy
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "case", ["unconfigured", "missing", "invalid", "bad-program", "inline", "program"]
)
def test_signing_environment_requires_valid_explicit_repository_inputs(
    tmp_path: Path, case: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    key = repo / "signing.pub"
    if case != "unconfigured":
        git(repo, "config", "user.signingkey", str(key))
    if case != "missing":
        key.write_text("invalid\n" if case == "invalid" else "ssh-ed25519 AAAATEST fixture\n")
    if case in {"program", "bad-program"}:
        git(repo, "config", "gpg.ssh.program", sys.executable if case == "program" else "relative")
    if case not in {"inline", "program"}:
        gap = (
            "git_effect_signing_program_invalid"
            if case == "bad-program"
            else "git_effect_signing_key_invalid"
        )
        with pytest.raises(ValueError, match=gap):
            creation.commit_environment(repo, None)
        return

    result = creation.commit_environment(repo, {"KEEP": "value"})

    expected = [("commit.gpgSign", "true"), ("gpg.format", "ssh")]
    if case == "program":
        expected.append(("gpg.ssh.program", sys.executable))
    expected.append(
        ("user.signingkey", str(key) if case == "program" else "key::ssh-ed25519 AAAATEST fixture")
    )
    assert [
        (result[f"GIT_CONFIG_KEY_{i}"], result[f"GIT_CONFIG_VALUE_{i}"])
        for i in range(int(result["GIT_CONFIG_COUNT"]))
    ] == expected
    assert result["KEEP"] == "value"


@pytest.mark.parametrize("case", ["signed", "unsigned", "missing", "untrusted", "git-failed"])
def test_creation_obeys_policy_and_rejects_unverified_object_outcomes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    policy = (
        None
        if case == "unsigned"
        else CommitPolicy(subject_pattern=r"^fix: .+", signing_required=True, signing_format="ssh")
    )
    monkeypatch.setattr(creation, "load_commit_policy", lambda _root: policy)
    monkeypatch.setattr(
        creation, "_config", lambda *_args: "true" if case == "unsigned" else "false"
    )
    monkeypatch.setattr(creation, "commit_environment", lambda *_args: {"POLICY_SIGNER": "1"})
    verified = []

    def verify(
        root: Path, selected: CommitPolicy, revision: str, *, verify_trust: bool
    ) -> dict[str, object]:
        verified.append((root, selected, revision, verify_trust))
        return {"required_gaps": ["git_signature_untrusted"] if case == "untrusted" else []}

    monkeypatch.setattr(creation, "commit_policy_report", verify)
    calls = []

    def runner(_root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args,
            2 if case == "git-failed" else 0,
            "" if case == "missing" else "c" * 40 + "\n",
            "git failed" if case == "git-failed" else "",
        )

    result = creation.create_git_commit(
        tmp_path, tree="a" * 40, parent="b" * 40, message="fix: exact subject", runner=runner
    )

    assert result.returncode == (
        2 if case == "git-failed" else 1 if case in {"missing", "untrusted"} else 0
    )
    assert ("-S" in calls[0][0]) is (case != "unsigned")
    assert calls[0][1]["env"] == (None if case == "unsigned" else {"POLICY_SIGNER": "1"})
    assert verified == (
        [(tmp_path, policy, "c" * 40, True)] if case in {"signed", "untrusted"} else []
    )
    assert result.stderr == {
        "missing": "git_effect_signed_commit_missing",
        "untrusted": "git_signature_untrusted",
        "git-failed": "git failed",
    }.get(case, "")


def test_invalid_subject_never_reaches_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = CommitPolicy(subject_pattern=r"^fix: .+", signing_required=False, signing_format="ssh")
    monkeypatch.setattr(creation, "load_commit_policy", lambda _root: policy)
    with pytest.raises(ValueError, match="commit_subject_invalid:bootstrap Commitment v2"):
        creation.create_git_commit(
            tmp_path,
            tree="a" * 40,
            parent="b" * 40,
            message="bootstrap Commitment v2",
            runner=lambda *_a, **_k: pytest.fail("Git must not run"),
        )
