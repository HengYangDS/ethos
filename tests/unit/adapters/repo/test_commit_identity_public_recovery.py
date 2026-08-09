from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.commit_identity as identity


def test_commit_payload_missing_separator_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        identity,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=b"header-only"),
    )
    assert identity.commit_payload(tmp_path, "revision") == b""


def test_trust_anchor_relative_missing_and_invalid_key_boundaries(tmp_path: Path) -> None:
    assert identity._trust_anchor(  # noqa: SLF001
        tmp_path, "relative/allowed-signers"
    ) == (
        None,
        ["commit_trust_anchor_not_absolute"],
    )
    missing = tmp_path.parent / "missing-allowed-signers"
    resolved, gaps = identity._trust_anchor(  # noqa: SLF001
        tmp_path, missing.as_posix()
    )
    assert resolved is None
    assert gaps == ["commit_trust_anchor_missing"]

    key = tmp_path / "invalid.pub"
    key.write_text("not-a-key\n", encoding="utf-8")
    assert identity._public_key(key) == ""  # noqa: SLF001


def test_signer_authorization_rejects_unverified_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = tmp_path / "allowed-signers"
    anchor.write_bytes(b"")
    monkeypatch.setattr(identity, "_configured_trust_anchor", lambda _root: (anchor, []))
    monkeypatch.setattr(
        identity,
        "_configured_signer",
        lambda _root: ("ssh-ed25519 AAAA", "owner@example.com", []),
    )
    monkeypatch.setattr(identity, "_target_verifies", lambda *_args: False)

    report = identity.authorize_configured_commit_signer(
        tmp_path,
        "revision",
        expected_anchor_sha256=hashlib.sha256(b"").hexdigest(),
        apply=False,
        authorized=False,
    )

    assert report["required_gaps"] == ["commit_signature_untrusted"]


def test_signer_authorization_reports_atomic_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = tmp_path / "allowed-signers"
    anchor.write_bytes(b"")
    monkeypatch.setattr(identity, "_configured_trust_anchor", lambda _root: (anchor, []))
    monkeypatch.setattr(
        identity,
        "_configured_signer",
        lambda _root: ("ssh-ed25519 AAAA", "owner@example.com", []),
    )
    monkeypatch.setattr(identity, "_target_verifies", lambda *_args: True)
    monkeypatch.setattr(
        identity,
        "_replace_anchor",
        lambda *_args: (_ for _ in ()).throw(ValueError("commit_trust_anchor_stale")),
    )

    report = identity.authorize_configured_commit_signer(
        tmp_path,
        "revision",
        expected_anchor_sha256=hashlib.sha256(b"").hexdigest(),
        apply=True,
        authorized=True,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["commit_trust_anchor_stale"]


def test_replace_anchor_rejects_initial_and_final_cas_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anchor = tmp_path / "allowed-signers"
    anchor.write_bytes(b"current")
    with pytest.raises(ValueError, match="commit_trust_anchor_stale"):
        identity._replace_anchor(anchor, b"stale", b"candidate")  # noqa: SLF001

    reads = iter((b"current", b"drift"))
    monkeypatch.setattr(Path, "read_bytes", lambda _path: next(reads))
    with pytest.raises(ValueError, match="commit_trust_anchor_stale"):
        identity._replace_anchor(anchor, b"current", b"candidate")  # noqa: SLF001
