"""Authorize the repository's lifecycle signer into its trust anchor."""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest

import ethos.adapters.repo.trust_anchor.authorization as authorization
from ethos.adapters.repo.commit.creation import commit_signer_action
from ethos.adapters.repo.commit.creation import commit_signer_gaps
from ethos.adapters.repo.trust_anchor.verification import verify_commit_trust
from tests.support.governed_repository import git
from tests.support.signature import untrusted_signer_repository


def test_signer_authorization_requires_confirmation_before_atomic_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor, target, digest = untrusted_signer_repository(tmp_path, monkeypatch, signed=True)

    ready = authorization.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=False, authorized=False
    )
    blocked = authorization.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=True, authorized=False
    )
    applied = authorization.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=True, authorized=True
    )

    assert (ready["verdict"], ready["state"]) == ("pass", "ready_to_authorize_signer")
    assert blocked["required_gaps"] == ["authorization_required"]
    assert (applied["verdict"], applied["state"]) == ("pass", "signer_authorized")
    assert verify_commit_trust(repo, target)["verdict"] == "pass"
    assert anchor.stat().st_mode & 0o777 == 0o600


def test_signer_authorization_admits_every_key_type_commit_creation_signs_with(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor, target, digest = untrusted_signer_repository(
        tmp_path, monkeypatch, signed=True, key_type="ecdsa"
    )

    applied = authorization.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=True, authorized=True
    )

    assert (applied["verdict"], applied["state"]) == ("pass", "signer_authorized")
    assert anchor.read_text().startswith('owner@example.com namespaces="git" ecdsa-sha2-')
    assert verify_commit_trust(repo, target)["verdict"] == "pass"


@pytest.mark.parametrize("failure", ["home-relative", "principal"])
def test_signer_authorization_refuses_a_signer_commit_creation_cannot_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """The refusal names the local setting, so replaying authorization cannot loop."""
    repo, anchor, target, digest = untrusted_signer_repository(tmp_path, monkeypatch, signed=True)
    if failure == "home-relative":
        # Git would expand this path, but lifecycle commit creation refuses it.
        monkeypatch.setenv("HOME", str(tmp_path))
        git(repo, "config", "user.signingkey", "~/signer.pub")
        gap = "git_effect_signing_key_invalid"
        assert commit_signer_gaps(repo) == [gap]
        action = commit_signer_action(repo, gap)
    else:
        git(repo, "config", "--unset", "user.email")
        gap = "commit_signer_principal_missing"
        action = f"git -C {shlex.quote(str(repo))} config --local user.email <signer-principal>"

    report = authorization.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=True, authorized=True
    )

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "block",
        "blocked",
        [gap],
    )
    assert report["next_action"] == action
    assert anchor.read_bytes() == b""


@pytest.mark.parametrize(
    ("failure", "gap"),
    [
        ("unsigned", "commit_signature_untrusted"),
        ("not-a-key", "git_effect_signing_key_invalid"),
        ("rsa AAAA", "git_effect_signing_key_invalid"),
        ("ssh-ed25519", "git_effect_signing_key_invalid"),
        ("preflight", "commit_trust_anchor_stale"),
        ("initial-cas", "commit_trust_anchor_stale"),
        ("final-cas", "commit_trust_anchor_stale"),
        ("write", "commit_trust_anchor_write_failed"),
    ],
)
def test_signer_authorization_preserves_anchor_on_public_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str, gap: str
) -> None:
    invalid_key = gap == "git_effect_signing_key_invalid"
    repo, anchor, target, digest = untrusted_signer_repository(
        tmp_path, monkeypatch, signed=failure != "unsigned" and not invalid_key
    )
    native_read = Path.read_bytes
    if invalid_key:
        Path(git(repo, "config", "--get", "user.signingkey")).write_text(failure)
    elif failure in {"initial-cas", "final-cas"}:
        reads = iter([b""] * (1 if failure == "initial-cas" else 2) + [b"drift", b"drift"])
        monkeypatch.setattr(
            Path, "read_bytes", lambda path: next(reads) if path == anchor else native_read(path)
        )
    elif failure == "write":

        def unavailable(*_args: object, **_kwargs: object) -> tuple[int, str]:
            raise OSError

        monkeypatch.setattr(authorization.tempfile, "mkstemp", unavailable)
    report = authorization.authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256="0" * 64 if failure == "preflight" else digest,
        apply=not invalid_key and failure != "unsigned",
        authorized=True,
    )
    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "block",
        "blocked",
        [gap],
    )
    if invalid_key:
        assert report["next_action"] == commit_signer_action(repo, gap)
    assert native_read(anchor) == b""
    assert list(anchor.parent.iterdir()) == [anchor]
