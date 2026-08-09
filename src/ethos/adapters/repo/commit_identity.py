"""Exact observation and trust verification for Git commit identity replacement."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import cast

from ethos.adapters.repo.git import run_git

_SIGNATURE_HEADERS = (b"gpgsig ", b"gpgsig-sha256 ")


def commit_payload(root: Path, revision: str) -> bytes:
    """Return canonical commit bytes with only signature headers removed."""
    completed = run_git(root, "cat-file", "commit", revision, check=False, text=False)
    if completed.returncode:
        return b""
    header, separator, message = completed.stdout.partition(b"\n\n")
    if not separator:
        return b""
    unsigned: list[bytes] = []
    skipping_signature = False
    for line in header.splitlines():
        if line.startswith(_SIGNATURE_HEADERS):
            skipping_signature = True
            continue
        if skipping_signature and line.startswith(b" "):
            continue
        skipping_signature = False
        unsigned.append(line)
    return b"\n".join(unsigned) + separator + message


def equivalent_commit_identity(root: Path, old: str, new: str) -> bool:
    """Return whether distinct commits differ only by signature headers."""
    payload = commit_payload(root, old)
    return old != new and bool(payload) and payload == commit_payload(root, new)


def verify_commit_trust(root: Path, revision: str) -> dict[str, object]:
    """Verify one commit against a host-protected, repository-external trust anchor."""
    configured = run_git(
        root,
        "config",
        "--path",
        "--get",
        "gpg.ssh.allowedSignersFile",
        check=False,
    ).stdout.strip()
    resolved, gaps = _trust_anchor(root, configured)
    if gaps:
        return _trust_report(revision, resolved.as_posix() if resolved else configured, gaps)
    resolved = cast("Path", resolved)
    completed = run_git(
        root,
        "-c",
        f"gpg.ssh.allowedSignersFile={resolved}",
        "verify-commit",
        "--raw",
        revision,
        check=False,
    )
    gaps = [] if completed.returncode == 0 else ["commit_signature_untrusted"]
    return {
        **_trust_report(revision, resolved.as_posix(), gaps),
        "status": completed.stderr.strip() or completed.stdout.strip(),
    }


def authorize_configured_commit_signer(
    root: Path,
    revision: str,
    *,
    expected_anchor_sha256: str,
    apply: bool,
    authorized: bool,
) -> dict[str, object]:
    """Authorize Git's configured signer for one exact signed commit."""
    anchor, anchor_gaps = _configured_trust_anchor(root)
    signer, principal, signer_gaps = _configured_signer(root)
    current = anchor.read_bytes() if anchor is not None and anchor.is_file() else b""
    digest = hashlib.sha256(current).hexdigest()
    gaps = [*anchor_gaps, *signer_gaps]
    if digest != expected_anchor_sha256:
        gaps.append("commit_trust_anchor_stale")
    candidate = _candidate_anchor(current, signer, principal)
    if not gaps and not _target_verifies(root, revision, candidate):
        gaps.append("commit_signature_untrusted")
    if apply and not authorized:
        gaps.append("authorization_required")
    if gaps or not apply:
        return _authorization_report(
            revision,
            anchor,
            digest,
            gaps,
            "blocked" if gaps else "ready_to_authorize_signer",
        )
    anchor = cast("Path", anchor)
    try:
        _replace_anchor(anchor, current, candidate)
    except (OSError, ValueError) as error:
        return _authorization_report(
            revision,
            anchor,
            hashlib.sha256(anchor.read_bytes()).hexdigest(),
            [str(error) or "commit_trust_anchor_write_failed"],
            "blocked",
        )
    return _authorization_report(
        revision,
        anchor,
        hashlib.sha256(candidate).hexdigest(),
        [],
        "signer_authorized",
    )


def commit_trust_setup_action(root: Path, revision: str) -> str:
    """Return the exact authorization command for the configured trust anchor."""
    anchor, gaps = _configured_trust_anchor(root)
    if anchor is None or gaps:
        return "git config --global gpg.ssh.allowedSignersFile <absolute-owner-only-path>"
    digest = hashlib.sha256(anchor.read_bytes()).hexdigest()
    return (
        "ethos lane trust-commit-signer "
        f"--target-commit {revision} --expected-anchor-sha256 {digest} "
        "--authorize --apply --json"
    )


def _trust_anchor(root: Path, configured: str) -> tuple[Path | None, list[str]]:
    if not configured:
        return None, ["commit_trust_anchor_missing"]
    anchor = Path(configured).expanduser()
    if not anchor.is_absolute():
        return None, ["commit_trust_anchor_not_absolute"]
    resolved: Path | None = None
    gaps: list[str] = []
    try:
        resolved = anchor.resolve(strict=True)
        resolved.relative_to(root.resolve())
    except FileNotFoundError:
        gaps = ["commit_trust_anchor_missing"]
    except ValueError:
        resolved = anchor.resolve()
    else:
        gaps = ["commit_trust_anchor_inside_repository"]
    if resolved is not None and not gaps:
        gaps = (
            ["commit_trust_anchor_missing"]
            if not resolved.is_file()
            else ["commit_trust_anchor_unprotected"]
            if not _protected_from_current_identity(resolved)
            else []
        )
    return resolved, gaps


def _protected_from_current_identity(path: Path) -> bool:
    target = path.stat()
    parent = path.parent.stat()
    return not target.st_mode & 0o022 and not parent.st_mode & 0o022


def _configured_trust_anchor(root: Path) -> tuple[Path | None, list[str]]:
    configured = run_git(
        root,
        "config",
        "--path",
        "--get",
        "gpg.ssh.allowedSignersFile",
        check=False,
    ).stdout.strip()
    return _trust_anchor(root, configured)


def _configured_signer(root: Path) -> tuple[str, str, list[str]]:
    configured = run_git(
        root, "config", "--path", "--get", "user.signingkey", check=False
    ).stdout.strip()
    principal = run_git(root, "config", "--get", "user.email", check=False).stdout.strip()
    path = Path(configured).expanduser() if configured else None
    key = _public_key(path) if path is not None and path.is_absolute() and path.is_file() else ""
    gaps = [] if key and principal else ["commit_signer_configuration_invalid"]
    return key, principal, gaps


def _public_key(path: Path) -> str:
    fields = path.read_text(encoding="utf-8").strip().split()
    if len(fields) < 2 or not fields[0].startswith("ssh-"):
        return ""
    return " ".join(fields[:2])


def _candidate_anchor(current: bytes, signer: str, principal: str) -> bytes:
    line = f'{principal} namespaces="git" {signer}\n'.encode()
    return current if line in current.splitlines(keepends=True) else current + line


def _target_verifies(root: Path, revision: str, candidate: bytes) -> bool:
    with tempfile.TemporaryDirectory() as directory:
        allowed = Path(directory) / "allowed-signers"
        allowed.write_bytes(candidate)
        completed = run_git(
            root,
            "-c",
            f"gpg.ssh.allowedSignersFile={allowed}",
            "verify-commit",
            "--raw",
            revision,
            check=False,
        )
    return completed.returncode == 0


def _replace_anchor(anchor: Path, expected: bytes, candidate: bytes) -> None:
    if anchor.read_bytes() != expected:
        msg = "commit_trust_anchor_stale"
        raise ValueError(msg)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{anchor.name}.", dir=anchor.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(candidate)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        if anchor.read_bytes() != expected:
            msg = "commit_trust_anchor_stale"
            raise ValueError(msg)
        temporary.replace(anchor)
    finally:
        temporary.unlink(missing_ok=True)


def _authorization_report(
    revision: str,
    anchor: Path | None,
    digest: str,
    gaps: list[str],
    state: str,
) -> dict[str, object]:
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "revision": revision,
        "anchor": anchor.as_posix() if anchor else "",
        "anchor_sha256": digest,
        "required_gaps": gaps,
    }


def _trust_report(revision: str, anchor: str, gaps: list[str]) -> dict[str, object]:
    return {
        "verdict": "block" if gaps else "pass",
        "revision": revision,
        "anchor": anchor,
        "required_gaps": gaps,
    }
