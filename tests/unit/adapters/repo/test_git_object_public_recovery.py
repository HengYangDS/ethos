"""Exercise native Git object identity, trust and bounded recovery failures."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.git_object as identity
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def _trust_root(tmp_path: Path) -> Path:
    root = tmp_path / "trust"
    root.mkdir(mode=0o700)
    return root


def _configured_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    signed: bool,
) -> tuple[Path, Path, str, str]:
    key = tmp_path / "signer"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        text=True,
    )
    signer = key.with_suffix(".pub")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test User")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "owner@example.com")
    repo = init_git_repo(tmp_path / "repo")
    anchor = _trust_root(tmp_path) / "allowed-signers"
    anchor.write_bytes(b"")
    anchor.chmod(0o600)
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", signer.as_posix())
    git(repo, "config", "user.email", "owner@example.com")
    git(repo, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())
    if signed:
        git(repo, "-c", "commit.gpgsign=true", "commit", "--allow-empty", "-m", "signed target")
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


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
@pytest.mark.parametrize(
    "header",
    [
        b"encoding UTF-8",
        b"encoding UTF-8\r",
        b"x-extra before\rafter",
        b"x-extra preserved\n continuation\r",
        b"x-extra before\rgpgsig -----BEGIN SSH SIGNATURE-----",
    ],
)
def test_signature_equivalence_preserves_every_non_signature_byte(
    tmp_path: Path, object_format: str, header: bytes
) -> None:
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    prefix = (
        f"tree {tree}\nauthor Test <test@example.invalid> 100 +0000\n"
        "committer Test <test@example.invalid> 100 +0000\n"
    ).encode()
    message = b"fix: exact bytes\r\nunchanged\n"
    raw = prefix + header + b"\n\n" + message
    signature = b"gpgsig synthetic\n continuation\ngpgsig-sha256 synthetic\n continuation"

    def store(payload: bytes) -> str:
        completed = identity.run_git(
            repo,
            "hash-object",
            "-w",
            "-t",
            "commit",
            "--stdin",
            stdin=payload,
            text=False,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return completed.stdout.decode().strip()

    old = store(raw)
    signed = store(prefix + signature + b"\n" + header + b"\n\n" + message)
    changed = store(prefix + header + b"\r\n\n" + message)

    assert identity.commit_payload(repo, old) == raw
    assert identity.commit_payload(repo, signed) == raw
    assert identity.equivalent_commit_identity(repo, old, signed)
    assert not identity.equivalent_commit_identity(repo, old, changed)
    assert identity.observe_commit(repo, old)["signature"] == {"present": False, "format": ""}


@pytest.mark.parametrize(
    ("suffix", "gap"),
    [
        (" SHA256:abc=\nadditional verifier detail", ""),
        (" SHA256:abc=\r\nadditional verifier detail", ""),
        ("", "git_object_signature_observation_unavailable"),
    ],
)
def test_git_object_trust_requires_a_portable_terminal_signature_status(
    tmp_path, monkeypatch, suffix, gap
):
    repo, _anchor, target, _digest = _configured_repository(tmp_path, monkeypatch, signed=False)
    native = identity.run_git
    status = f'Good "git" signature for owner@example.com with ED25519 key{suffix}'

    def verify(root, *args, **kwargs):
        return (
            SimpleNamespace(returncode=0, stdout="", stderr=status)
            if "verify-commit" in args
            else native(root, *args, **kwargs)
        )

    monkeypatch.setattr(identity, "run_git", verify)
    report = identity.verify_git_object_trust(repo, target, "commit")
    assert report["verdict"] == ("block" if gap else "pass")
    assert report["required_gaps"] == ([gap] if gap else [])
    assert report["principal"] == ("" if gap else "owner@example.com")
    assert report["fingerprint"] == ("" if gap else "SHA256:abc=")


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("relative", "commit_trust_anchor_not_absolute"),
        ("missing", "commit_trust_anchor_missing"),
        ("absent", "commit_trust_anchor_missing"),
        ("inside", "commit_trust_anchor_inside_repository"),
        ("directory", "commit_trust_anchor_missing"),
        ("unprotected", "commit_trust_anchor_unprotected"),
    ],
)
def test_commit_trust_public_report_rejects_invalid_anchor_location(tmp_path, configured, expected):
    repo = init_git_repo(tmp_path / "repo")
    anchor = (repo if configured == "inside" else _trust_root(tmp_path)) / "allowed-signers"
    if configured == "directory":
        anchor.mkdir()
    elif configured in {"inside", "unprotected"}:
        anchor.write_text("untrusted\n")
        anchor.chmod(0o666)
    value = "relative/allowed-signers" if configured == "relative" else str(anchor)
    if configured != "absent":
        git(repo, "config", "gpg.ssh.allowedSignersFile", value)
    report = identity.verify_commit_trust(repo, git(repo, "rev-parse", "HEAD"))
    assert report["required_gaps"] == [expected]
    action = identity.commit_trust_setup_action(repo, "HEAD")
    assert action == "git config --global gpg.ssh.allowedSignersFile <absolute-owner-only-path>"


def test_signer_authorization_requires_confirmation_before_atomic_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor, target, digest = _configured_repository(tmp_path, monkeypatch, signed=True)

    ready = identity.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=False, authorized=False
    )
    blocked = identity.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=True, authorized=False
    )
    applied = identity.authorize_configured_commit_signer(
        repo, target, expected_anchor_sha256=digest, apply=True, authorized=True
    )

    assert (ready["verdict"], ready["state"]) == ("pass", "ready_to_authorize_signer")
    assert blocked["required_gaps"] == ["authorization_required"]
    assert (applied["verdict"], applied["state"]) == ("pass", "signer_authorized")
    assert identity.verify_commit_trust(repo, target)["verdict"] == "pass"
    assert anchor.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("failure", "gap"),
    [
        ("unsigned", "commit_signature_untrusted"),
        ("not-a-key", "commit_signer_configuration_invalid"),
        ("rsa AAAA", "commit_signer_configuration_invalid"),
        ("ssh-ed25519", "commit_signer_configuration_invalid"),
        ("preflight", "commit_trust_anchor_stale"),
        ("initial-cas", "commit_trust_anchor_stale"),
        ("final-cas", "commit_trust_anchor_stale"),
        ("write", "commit_trust_anchor_write_failed"),
    ],
)
def test_signer_authorization_preserves_anchor_on_public_failure(
    tmp_path, monkeypatch, failure, gap
):
    invalid_key = gap == "commit_signer_configuration_invalid"
    repo, anchor, target, digest = _configured_repository(
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

        def unavailable(*_args, **_kwargs):
            raise OSError

        monkeypatch.setattr(identity.tempfile, "mkstemp", unavailable)
    report = identity.authorize_configured_commit_signer(
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
    assert native_read(anchor) == b""
    assert list(anchor.parent.iterdir()) == [anchor]


@pytest.mark.parametrize("failure", ["status", "status-oid", "status-fields", "raw"])
def test_commit_observation_rejects_incomplete_native_facts(tmp_path, monkeypatch, failure):
    repo = init_git_repo(tmp_path / "repo")
    target = git(repo, "rev-parse", "HEAD")
    observed = identity.observe_commit(repo, target)
    assert observed["verdict"] == "pass"
    native = identity.run_git

    def interrupted(root, *args, **kwargs):
        result = native(root, *args, **kwargs)
        if args[:2] == ("cat-file", "commit") if failure == "raw" else args[0] == "show":
            if failure in {"raw", "status"}:
                result.returncode = 1
            elif failure == "status-oid":
                result.stdout = result.stdout.replace(target, "0" * len(target), 1)
            else:
                result.stdout = result.stdout.split("\x00")[0]
        return result

    monkeypatch.setattr(identity, "run_git", interrupted)
    result = identity.observe_commit(repo, target)
    assert (result["verdict"], result["state"], result["object_oid"]) == (
        "block",
        "unavailable",
        target,
    )
    assert result["required_gaps"] == [f"commit_observation_unavailable:{target}"]
    assert result["signature"] == {"present": False, "format": ""}
    assert result["subject"] == (observed["subject"] if failure == "raw" else "")


@pytest.mark.parametrize(
    ("failure", "gap"),
    [
        ("wrong-kind", "git_object_kind_mismatch"),
        ("tagged-tree", "git_object_peeled_commit_invalid"),
        ("unreadable-tree", "git_object_tree_unreadable"),
    ],
)
def test_object_observation_refuses_incomplete_commit_binding(tmp_path, monkeypatch, failure, gap):
    repo = init_git_repo(tmp_path / "repo")
    target = git(repo, "rev-parse", "HEAD^{tree}" if failure != "unreadable-tree" else "HEAD")
    if failure == "tagged-tree":
        git(repo, "tag", "-a", "tree-tag", target, "-m", "tree target")
        target = git(repo, "rev-parse", "refs/tags/tree-tag")
    elif failure == "unreadable-tree":
        monkeypatch.setattr(identity, "current_tree", lambda *_args: "")
    before = git(repo, "show-ref"), (repo / ".git/index").read_bytes()
    result = identity.observe_git_object(
        repo, target, "annotated-tag" if failure == "tagged-tree" else "commit"
    )
    assert result["required_gaps"] == [gap]
    assert (result["verdict"], result["object_oid"], result["tree_oid"]) == ("block", target, "")
    assert (git(repo, "show-ref"), (repo / ".git/index").read_bytes()) == before
