"""Authorize the repository's lifecycle signer into its trust anchor."""

from __future__ import annotations

import hashlib
import os
import shlex
import tempfile
from pathlib import Path
from typing import cast

from ethos.adapters.repo.commit.creation import commit_signer_action
from ethos.adapters.repo.commit.creation import commit_signer_public_key
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from ethos.adapters.repo.trust_anchor.verification import commit_trust_anchor_action
from ethos.adapters.repo.trust_anchor.verification import configured_commit_trust_anchor


def authorize_configured_commit_signer(
    root: Path,
    revision: str,
    *,
    expected_anchor_sha256: str,
    apply: bool,
    authorized: bool,
) -> dict[str, object]:
    """Authorize Git's configured signer for one exact signed commit."""
    anchor, anchor_gaps = configured_commit_trust_anchor(root)
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
        report = _authorization_report(
            revision,
            anchor,
            digest,
            gaps,
            "blocked" if gaps else "ready_to_authorize_signer",
        )
        return report | {
            "next_action": _blocked_action(root, revision, anchor_gaps, signer_gaps, digest)
        }
    anchor = cast("Path", anchor)
    try:
        _replace_anchor(anchor, current, candidate)
    except (OSError, ValueError) as error:
        observed = anchor.read_bytes()
        observed_digest = hashlib.sha256(observed).hexdigest()
        report = _authorization_report(
            revision,
            anchor,
            observed_digest,
            [str(error) or "commit_trust_anchor_write_failed"],
            "blocked",
        )
        return report | {
            "next_action": commit_trust_setup_action(
                root,
                revision,
                observed_anchor_sha256=observed_digest,
            )
        }
    return _authorization_report(
        revision,
        anchor,
        hashlib.sha256(candidate).hexdigest(),
        [],
        "signer_authorized",
    ) | {"next_action": ""}


def commit_trust_setup_action(
    root: Path,
    revision: str,
    *,
    observed_anchor_sha256: str | None = None,
) -> str:
    """Return the exact authorization command for the configured trust anchor."""
    anchor, gaps = configured_commit_trust_anchor(root)
    if anchor is None or gaps:
        return commit_trust_anchor_action(root)
    digest = observed_anchor_sha256 or hashlib.sha256(anchor.read_bytes()).hexdigest()
    return (
        "ethos lane trust-commit-signer "
        f"--target-commit {revision} --expected-anchor-sha256 {digest} "
        "--authorize --apply --json"
    )


def _configured_signer(root: Path) -> tuple[str, str, list[str]]:
    """Read the signer that lifecycle commit creation uses and the principal it trusts."""
    public_key, gap = commit_signer_public_key(root)
    principal = run_git(root, "config", "--get", "user.email", check=False).stdout.strip()
    gaps = [gap] if gap else []
    if not principal:
        gaps.append("commit_signer_principal_missing")
    return " ".join(public_key.split()[:2]), principal, gaps


def _blocked_action(
    root: Path, revision: str, anchor_gaps: list[str], signer_gaps: list[str], digest: str
) -> str:
    """Name the local setting that unblocks authorization before replaying it."""
    if anchor_gaps or not signer_gaps:
        return commit_trust_setup_action(root, revision, observed_anchor_sha256=digest)
    if signer_gaps[0] == "commit_signer_principal_missing":
        return f"git -C {shlex.quote(str(root))} config --local user.email <signer-principal>"
    return commit_signer_action(root, signer_gaps[0])


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
        message = "commit_trust_anchor_stale"
        raise ValueError(message)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{anchor.name}.", dir=anchor.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(candidate)
            stream.flush()
            os.fsync(stream.fileno())
        protect_for_current_identity(temporary)
        if anchor.read_bytes() != expected:
            message = "commit_trust_anchor_stale"
            raise ValueError(message)
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
