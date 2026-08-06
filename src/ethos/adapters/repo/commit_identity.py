"""Exact observation and trust verification for Git commit identity replacement."""

from __future__ import annotations

import os
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
    return (
        target.st_uid != os.geteuid()
        and parent.st_uid != os.geteuid()
        and not target.st_mode & 0o022
        and not parent.st_mode & 0o022
    )


def _trust_report(revision: str, anchor: str, gaps: list[str]) -> dict[str, object]:
    return {
        "verdict": "block" if gaps else "pass",
        "revision": revision,
        "anchor": anchor,
        "required_gaps": gaps,
    }
