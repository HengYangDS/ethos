from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.commit_identity as identity
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def _trust_root(tmp_path: Path) -> Path:
    root = tmp_path / "trust"
    root.mkdir(mode=0o700)
    return root


def _signer(tmp_path: Path) -> Path:
    key = tmp_path / "signer"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        text=True,
    )
    return key.with_suffix(".pub")


def _configured_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    signed: bool,
) -> tuple[Path, Path, str, str]:
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "owner@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "owner@example.com")
    repo = init_git_repo(tmp_path / "repo")
    signer = _signer(tmp_path)
    anchor = _trust_root(tmp_path) / "allowed-signers"
    anchor.write_bytes(b"")
    anchor.chmod(0o600)
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", signer.as_posix())
    git(repo, "config", "user.email", "owner@example.com")
    git(repo, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())
    if signed:
        (repo / "target.txt").write_text("signed\n", encoding="utf-8")
        git(repo, "add", "target.txt")
        git(repo, "-c", "commit.gpgsign=true", "commit", "-m", "signed target")
    target = git(repo, "rev-parse", "HEAD")
    return repo, anchor, target, hashlib.sha256(anchor.read_bytes()).hexdigest()


def test_commit_payload_missing_separator_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        identity,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=b"header-only"),
    )

    assert identity.commit_payload(tmp_path, "revision") == b""


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("relative/allowed-signers", "commit_trust_anchor_not_absolute"),
        ("missing", "commit_trust_anchor_missing"),
    ],
)
def test_commit_trust_public_report_rejects_invalid_anchor_location(
    tmp_path: Path, configured: str, expected: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    value = (
        (tmp_path.parent / "missing-allowed-signers").as_posix()
        if configured == "missing"
        else configured
    )
    git(repo, "config", "gpg.ssh.allowedSignersFile", value)

    report = identity.verify_commit_trust(repo, git(repo, "rev-parse", "HEAD"))

    assert report["required_gaps"] == [expected]


def test_signer_authorization_rejects_invalid_public_key(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    anchor = _trust_root(tmp_path) / "allowed-signers"
    anchor.write_bytes(b"")
    anchor.chmod(0o600)
    key = tmp_path / "invalid.pub"
    key.write_text("not-a-key\n", encoding="utf-8")
    git(repo, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())
    git(repo, "config", "user.signingkey", key.as_posix())
    git(repo, "config", "user.email", "owner@example.com")

    report = identity.authorize_configured_commit_signer(
        repo,
        git(repo, "rev-parse", "HEAD"),
        expected_anchor_sha256=hashlib.sha256(b"").hexdigest(),
        apply=False,
        authorized=False,
    )

    assert report["required_gaps"] == ["commit_signer_configuration_invalid"]


def test_signer_authorization_rejects_unverified_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _anchor, target, digest = _configured_repository(tmp_path, monkeypatch, signed=False)

    report = identity.authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256=digest,
        apply=False,
        authorized=False,
    )

    assert report["required_gaps"] == ["commit_signature_untrusted"]


def test_signer_authorization_reports_atomic_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor, target, digest = _configured_repository(tmp_path, monkeypatch, signed=True)

    def unavailable(*_args: object, **_kwargs: object) -> tuple[int, str]:
        raise OSError

    monkeypatch.setattr(identity.tempfile, "mkstemp", unavailable)
    report = identity.authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256=digest,
        apply=True,
        authorized=True,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["commit_trust_anchor_write_failed"]
    assert anchor.read_bytes() == b""


@pytest.mark.parametrize("drift_at", ["initial-cas", "final-cas"])
def test_signer_authorization_rejects_anchor_cas_drift_through_public_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift_at: str,
) -> None:
    repo, anchor, target, digest = _configured_repository(tmp_path, monkeypatch, signed=True)
    current = anchor.read_bytes()
    observed = (
        iter((current, b"drift", b"drift"))
        if drift_at == "initial-cas"
        else iter((current, current, b"drift", b"drift"))
    )
    original = Path.read_bytes

    def drifting_read(path: Path) -> bytes:
        return next(observed) if path == anchor else original(path)

    monkeypatch.setattr(Path, "read_bytes", drifting_read)
    report = identity.authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256=digest,
        apply=True,
        authorized=True,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["commit_trust_anchor_stale"]
