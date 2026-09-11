"""Verify policy-bound native commit creation and signature-only replacement."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.commit.creation as creation
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git_object import commit_payload
from ethos.adapters.repo.git_object import verify_commit_trust
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


def _signature_repository(tmp_path: Path, object_format: str) -> Path:
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        'signing_required = true\nsigning_format = "ssh"\n'
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(repo, "commit", "-m", "fix: require trusted signing")
    executable = shutil.which("ssh-keygen")
    assert executable is not None
    key = tmp_path / "signer"
    subprocess.run(
        (executable, "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        timeout=15,
    )
    trust = tmp_path / "trust"
    trust.mkdir(mode=0o700)
    anchor = trust / "allowed-signers"
    public_key = key.with_suffix(".pub").read_text()
    anchor.write_text(f'test@example.invalid namespaces="git" {public_key}')
    anchor.chmod(0o600)
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", executable),
        ("user.signingkey", str(key.with_suffix(".pub"))),
        ("gpg.ssh.allowedSignersFile", str(anchor)),
    ):
        git(repo, "config", name, value)
    return repo


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
@pytest.mark.parametrize("parent_count", [0, 1, 2])
def test_signed_replacement_preserves_native_payload_without_ref_mutation(
    tmp_path: Path, object_format: str, parent_count: int
) -> None:
    repo = _signature_repository(tmp_path, object_format)
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    parents = [git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^")][:parent_count]
    payload = (
        f"tree {tree}\n"
        + "".join(f"parent {parent}\n" for parent in parents)
        + "author Original <original@example.invalid> 100 +0100\n"
        + "committer Original <original@example.invalid> 200 -0700\n"
    ).encode() + b"encoding UTF-8\r\nx-extra preserved\n continuation\r\n\nfix: exact bytes\r\n"
    old = (
        creation.run_git(
            repo, "hash-object", "-t", "commit", "-w", "--stdin", stdin=payload, text=False
        )
        .stdout.decode()
        .strip()
    )
    before = git(repo, "show-ref"), (repo / ".git/index").read_bytes()

    new = creation.create_signed_replacement(repo, old)

    assert new != old
    assert commit_payload(repo, new) == payload
    assert verify_commit_trust(repo, new)["verdict"] == "pass"
    assert (git(repo, "show-ref"), (repo / ".git/index").read_bytes()) == before


@pytest.mark.parametrize("failure", ["signed", "policy-absent", "untrusted", "missing-key"])
def test_signed_replacement_rejects_invalid_source_and_trust(tmp_path: Path, failure: str) -> None:
    repo = _signature_repository(tmp_path, "sha1")
    old = git(repo, "rev-parse", "HEAD")
    if failure == "signed":
        old = creation.create_signed_replacement(repo, old)
    elif failure == "policy-absent":
        old = git(repo, "rev-parse", "HEAD^")
    elif failure == "untrusted":
        (tmp_path / "trust/allowed-signers").write_text("")
    else:
        (tmp_path / "signer.pub").unlink()
    before = git(repo, "show-ref"), (repo / ".git/index").read_bytes()

    gap = {
        "signed": "signature_repair_source_not_unsigned",
        "policy-absent": "signature_repair_policy_required",
        "untrusted": "commit_signature_untrusted",
        "missing-key": "git_effect_signing_key_invalid",
    }[failure]
    with pytest.raises(ValueError, match=gap) as caught:
        creation.create_signed_replacement(repo, old)

    assert (git(repo, "show-ref"), (repo / ".git/index").read_bytes()) == before
    if failure == "untrusted":
        assert isinstance(caught.value, ProcessExecutionError)
        new = str(caught.value.observation["replacement"])
        assert commit_payload(repo, new) == commit_payload(repo, old)
        assert caught.value.observation["refs_changed"] is False


@pytest.mark.parametrize("failure", ["subject", "signer", "object-write"])
def test_signed_replacement_preserves_failure_boundary_and_never_moves_refs(
    tmp_path, monkeypatch, failure
):
    repo = _signature_repository(tmp_path, "sha1")
    if failure == "subject":
        git(repo, "commit", "--allow-empty", "-m", "invalid subject")
    elif failure == "signer":
        git(repo, "config", "gpg.ssh.program", sys.executable)
    old = git(repo, "rev-parse", "HEAD")
    before = git(repo, "show-ref"), (repo / ".git/index").read_bytes()
    native_git = creation.run_git

    def fail_write(root, *args, **kwargs):
        if args[:1] == ("hash-object",):
            return subprocess.CompletedProcess(args, 1, b"", b"object store unavailable")
        return native_git(root, *args, **kwargs)

    if failure == "object-write":
        monkeypatch.setattr(creation, "run_git", fail_write)
    gap = {
        "subject": "commit_subject_invalid",
        "signer": "signature_repair_signing_failed",
        "object-write": "signature_repair_object_failed:object store unavailable",
    }[failure]
    with pytest.raises(ValueError, match=gap):
        creation.create_signed_replacement(repo, old)
    assert (git(repo, "show-ref"), (repo / ".git/index").read_bytes()) == before
    assert list((repo / ".git").glob("ethos-signature-*")) == []


@pytest.mark.parametrize("failure", ["observe", "payload"])
def test_signed_replacement_preserves_created_oid_when_validation_fails(
    tmp_path, monkeypatch, failure
):
    repo = _signature_repository(tmp_path, "sha1")
    old = git(repo, "rev-parse", "HEAD")
    before = git(repo, "show-ref"), (repo / ".git/index").read_bytes()
    native_payload = creation.commit_payload

    def observe(root, revision):
        if revision != old:
            if failure == "observe":
                error = "object observation unavailable"
                raise OSError(error)
            return b"different payload"
        return native_payload(root, revision)

    monkeypatch.setattr(creation, "commit_payload", observe)
    gap = (
        "object observation unavailable"
        if failure == "observe"
        else "signature_repair_payload_changed"
    )
    with pytest.raises(ProcessExecutionError, match=gap) as caught:
        creation.create_signed_replacement(repo, old)
    observed = caught.value.observation
    assert observed["validation_verdict"] == ("unknown" if failure == "observe" else "block")
    assert native_payload(repo, str(observed["replacement"])) == native_payload(repo, old)
    assert (git(repo, "show-ref"), (repo / ".git/index").read_bytes()) == before
    assert list((repo / ".git").glob("ethos-signature-*")) == []
