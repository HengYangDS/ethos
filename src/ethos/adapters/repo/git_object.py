"""Observe and verify exact local Git objects through Git and OpenSSH."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from ethos.adapters.repo.trust_anchor.verification import configured_commit_trust_anchor
from ethos.adapters.repo.trust_anchor.verification import verify_git_object_trust

if TYPE_CHECKING:
    from collections.abc import Mapping


GitObjectKind = Literal["commit", "annotated-tag"]

_SIGNATURE_HEADERS = (b"gpgsig ", b"gpgsig-sha256 ")
_SIGNATURE_ARMOR_FORMATS = {
    b"-----BEGIN SSH SIGNATURE-----": "ssh",
    b"-----BEGIN PGP SIGNATURE-----": "openpgp",
    b"-----BEGIN SIGNED MESSAGE-----": "x509",
}


def zero_oid(root: Path) -> str:
    """Return the null object ID at the repository's native hash width."""
    completed = run_git(root, "rev-parse", "--show-object-format", check=False)
    object_format = completed.stdout.strip() if completed.returncode == 0 else ""
    width = {"sha1": 40, "sha256": 64}.get(object_format)
    if width is None:
        message = "git_object_format_unavailable"
        raise ValueError(message)
    return "0" * width


def observe_commit(root: Path, revision: str = "HEAD") -> dict[str, object]:
    """Return immutable identity, subject, and signature facts for one commit."""
    object_oid = _resolve(root, revision)
    if not object_oid or _type(root, object_oid) != "commit":
        gap = f"commit_observation_unavailable:{revision}"
        return {
            "verdict": "block",
            "state": "unavailable",
            "object_oid": object_oid,
            "subject": "",
            "author": {"name": "", "email": ""},
            "committer": {"name": "", "email": ""},
            "signature": {"present": False, "format": ""},
            "required_gaps": [gap],
        }
    completed = run_git(
        root,
        "show",
        "-s",
        "--format=%H%x00%s%x00%an%x00%ae%x00%cn%x00%ce",
        object_oid,
        check=False,
        observation=True,
    )
    parts = completed.stdout.rstrip("\n").split("\x00")
    if completed.returncode or len(parts) != 6 or parts[0] != object_oid:
        gap = f"commit_observation_unavailable:{revision}"
        return {
            "verdict": "block",
            "state": "unavailable",
            "object_oid": object_oid,
            "subject": "",
            "author": {"name": "", "email": ""},
            "committer": {"name": "", "email": ""},
            "signature": {"present": False, "format": ""},
            "required_gaps": [gap],
        }
    raw = _commit_object(root, object_oid)
    if not raw:
        gap = f"commit_observation_unavailable:{revision}"
        return {
            "verdict": "block",
            "state": "unavailable",
            "object_oid": object_oid,
            "subject": parts[1],
            "author": {"name": parts[2], "email": parts[3]},
            "committer": {"name": parts[4], "email": parts[5]},
            "signature": {"present": False, "format": ""},
            "required_gaps": [gap],
        }
    signature_format = _commit_signature_format(raw)
    return {
        "verdict": "pass",
        "state": "current",
        "object_oid": object_oid,
        "subject": parts[1],
        "author": {"name": parts[2], "email": parts[3]},
        "committer": {"name": parts[4], "email": parts[5]},
        "signature": {
            "present": signature_format is not None,
            "format": signature_format or "",
        },
        "required_gaps": [],
    }


def observe_git_object(root: Path, revision: str, kind: GitObjectKind) -> dict[str, object]:
    """Return exact identity and trusted-signature facts for one local Git object."""
    object_oid = _resolve(root, revision)
    actual_type = _type(root, object_oid) if object_oid else ""
    expected_type = "tag" if kind == "annotated-tag" else "commit"
    if actual_type != expected_type:
        return _observation(revision, kind, object_oid, required_gaps=["git_object_kind_mismatch"])
    peeled_commit = _resolve(root, f"{object_oid}^{{}}") if kind == "annotated-tag" else object_oid
    if _type(root, peeled_commit) != "commit":
        return _observation(
            revision,
            kind,
            object_oid,
            peeled_commit=peeled_commit,
            required_gaps=["git_object_peeled_commit_invalid"],
        )
    tree_oid = current_tree(root, peeled_commit)
    if not tree_oid:
        return _observation(
            revision,
            kind,
            object_oid,
            peeled_commit=peeled_commit,
            required_gaps=["git_object_tree_unreadable"],
        )
    trust = verify_git_object_trust(root, object_oid, kind)
    return {
        **_observation(
            revision,
            kind,
            object_oid,
            peeled_commit=peeled_commit,
            tree_oid=tree_oid,
            required_gaps=cast("list[str]", trust["required_gaps"]),
        ),
        "signature": trust,
    }


def commit_payload(root: Path, revision: str) -> bytes:
    """Return canonical commit bytes with only signature headers removed."""
    raw = _commit_object(root, revision)
    if not raw:
        return b""
    return unsigned_commit_payload(raw)


def unsigned_commit_payload(raw: bytes) -> bytes:
    """Remove only native signature headers from exact commit object bytes."""
    header, separator, message = raw.partition(b"\n\n")
    if not separator:
        return b""
    unsigned: list[bytes] = []
    skipping_signature = False
    for line in header.split(b"\n"):
        if line.startswith(_SIGNATURE_HEADERS):
            skipping_signature = True
            continue
        if skipping_signature and line.startswith(b" "):
            continue
        skipping_signature = False
        unsigned.append(line)
    return b"\n".join(unsigned) + separator + message


def _commit_object(root: Path, revision: str) -> bytes:
    completed = run_git(
        root,
        "cat-file",
        "commit",
        revision,
        check=False,
        text=False,
        observation=True,
    )
    return completed.stdout if completed.returncode == 0 else b""


def _commit_signature_format(raw: bytes) -> str | None:
    header = raw.partition(b"\n\n")[0]
    for line in header.split(b"\n"):
        if not line.startswith(_SIGNATURE_HEADERS):
            continue
        armor = line.split(b" ", 1)[1]
        return _SIGNATURE_ARMOR_FORMATS.get(armor, "unknown")
    return None


def equivalent_commit_identity(root: Path, old: str, new: str) -> bool:
    """Return whether distinct commits differ only by signature headers."""
    payload = commit_payload(root, old)
    return old != new and bool(payload) and payload == commit_payload(root, new)


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
            "next_action": commit_trust_setup_action(
                root,
                revision,
                observed_anchor_sha256=digest,
            )
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
        return "git config --global gpg.ssh.allowedSignersFile <absolute-owner-only-path>"
    digest = observed_anchor_sha256 or hashlib.sha256(anchor.read_bytes()).hexdigest()
    return (
        "ethos lane trust-commit-signer "
        f"--target-commit {revision} --expected-anchor-sha256 {digest} "
        "--authorize --apply --json"
    )


def _resolve(root: Path, revision: str) -> str:
    completed = run_git(root, "rev-parse", "--verify", revision, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _type(root: Path, object_oid: str) -> str:
    completed = run_git(root, "cat-file", "-t", object_oid, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


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


def _observation(
    revision: str,
    kind: GitObjectKind,
    object_oid: str,
    *,
    peeled_commit: str = "",
    tree_oid: str = "",
    required_gaps: list[str],
) -> dict[str, object]:
    return {
        "verdict": "block" if required_gaps else "pass",
        "revision": revision,
        "kind": kind,
        "object_oid": object_oid,
        "peeled_commit": peeled_commit,
        "tree_oid": tree_oid,
        "required_gaps": required_gaps,
    }


def read_objects(
    repo: Path,
    object_ids: tuple[str, ...],
    *,
    kind: Literal["blob", "commit"] | tuple[Literal["blob", "commit"], ...] = "blob",
    gap: str = "git_object_batch_invalid",
) -> tuple[bytes, ...]:
    """Read exact typed objects in one native batch with strict frame/identity validation."""
    kinds = (kind,) * len(object_ids) if isinstance(kind, str) else kind
    if len(kinds) != len(object_ids):
        raise ValueError(gap)
    if not object_ids:
        return ()
    result = run_git(
        repo,
        "cat-file",
        "--batch",
        stdin=b"".join(f"{object_id}\n".encode() for object_id in object_ids),
        text=False,
        check=False,
        observation=True,
    )
    if result.returncode != 0:
        raise ValueError(gap)
    payload, offset = result.stdout, 0
    blobs: list[bytes] = []
    try:
        for expected, expected_kind in zip(object_ids, kinds, strict=True):
            header_end = payload.index(b"\n", offset)
            object_id, actual_kind, raw_size = payload[offset:header_end].decode().split(" ")
            size = int(raw_size)
            content_start, content_end = header_end + 1, header_end + 1 + size
            if not (
                object_id == expected
                and actual_kind == expected_kind
                and size >= 0
                and payload[content_end : content_end + 1] == b"\n"
            ):
                break
            blobs.append(payload[content_start:content_end])
            offset = content_end + 1
    except (UnicodeError, ValueError) as error:
        raise ValueError(gap) from error
    if offset != len(payload) or len(blobs) != len(object_ids):
        raise ValueError(gap)
    return tuple(blobs)


def resolve_revisions(
    repo: Path, revisions: tuple[str, ...], *, environment: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Resolve one ordered native batch, separating missing objects from failed observation."""
    queries = tuple(dict.fromkeys(revisions))
    gap = "git_revision_batch_invalid"
    if any(any(character.isspace() or character == "\0" for character in item) for item in queries):
        raise ValueError(gap)
    if not queries:
        return {}
    result = run_git(
        repo,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(rest)",
        stdin="".join(f"{revision} {index}\n" for index, revision in enumerate(queries)),
        check=False,
        env=environment,
    )
    rows = result.stdout.splitlines()
    if result.returncode or len(rows) != len(queries):
        raise ValueError(gap)
    resolved = {}
    for index, (revision, row) in enumerate(zip(queries, rows, strict=True)):
        if row == f"{revision} missing":
            absent = run_git(
                repo,
                "rev-parse",
                "--verify",
                "--quiet",
                "--end-of-options",
                revision,
                check=False,
                env=environment,
            )
            if absent.returncode != 1 or absent.stdout or absent.stderr:
                raise ValueError(gap)
            resolved[revision] = ""
            continue
        fields = row.split(" ")
        if (
            len(fields) != 3
            or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", fields[0])
            or fields[1] not in {"commit", "tree", "tag", "blob"}
            or fields[2] != str(index)
        ):
            raise ValueError(gap)
        resolved[revision] = fields[0]
    return resolved
